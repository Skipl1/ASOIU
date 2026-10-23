"""Провайдер GigaChat с подменённым клиентом: разбор JSON, повтор при ошибке, резервный генератор."""

import json
import types

import pytest

from app.config import get_settings
from app.services.llm import gigachat_provider as gp
from app.services.llm.base import ContextIngredient, GenerationContext, LLMError


def _completion(content: str, finish="stop"):
    message = types.SimpleNamespace(content=content)
    return types.SimpleNamespace(choices=[types.SimpleNamespace(message=message, finish_reason=finish)])


class FakeClient:
    def __init__(self, replies):
        self.replies = list(replies)
        self.payloads = []

    def chat(self, payload):
        self.payloads.append(payload)
        return _completion(self.replies.pop(0))


def _ctx() -> GenerationContext:
    import uuid

    items = [
        ContextIngredient("I1", uuid.uuid4(), "Куриная грудка", "cat_protein", "Белковые", 23, 2, 0, 110, 500),
        ContextIngredient("I2", uuid.uuid4(), "Бурый рис", "cat_grains", "Крупы", 7, 2, 72, 350, None),
    ]
    return GenerationContext("goal_gain", "Набор массы", "", {"calories": 800, "protein": 50, "fat": 22, "carbs": 100},
                             {"protein": 25, "fat": 25, "carbs": 50}, 1, None, "без лука", items)


VALID = {"recipes": [{"name": "Курица с рисом", "servings": 1,
                      "ingredients": [{"code": "I1", "massG": 200}, {"code": "I2", "massG": 100}],
                      "steps": ["Отварить рис", "Запечь курицу", "Подать"], "difficulty": "low"}]}


@pytest.fixture()
def provider(monkeypatch):
    monkeypatch.setattr(get_settings(), "gigachat_credentials", "dGVzdDp0ZXN0")
    p = gp.GigaChatProvider()
    return p


def test_prompt_contains_context():
    prompt = gp.build_user_prompt(_ctx())
    # продукты в промпте перечислены по названиям, без внутренних кодов
    assert "Куриная грудка | Белковые | 23/2/0 | 110" in prompt and "I1 |" not in prompt
    assert "800 ккал" in prompt and "без лука" in prompt


def test_parses_fenced_json(provider, monkeypatch):
    fake = FakeClient(["```json\n" + json.dumps(VALID, ensure_ascii=False) + "\n```"])
    monkeypatch.setattr(provider, "_get_client", lambda: fake)
    recipes = provider.generate(_ctx())
    assert recipes[0].name == "Курица с рисом" and recipes[0].ingredients[0].massG == 200
    assert fake.payloads[0]["response_format"]["type"] == "json_schema"


def test_retry_on_invalid_json_then_fail(provider, monkeypatch):
    fake = FakeClient(["не JSON", json.dumps(VALID)])
    monkeypatch.setattr(provider, "_get_client", lambda: fake)
    assert provider.generate(_ctx())[0].name == "Курица с рисом"
    assert len(fake.payloads) == 2 and fake.payloads[1]["messages"][-1]["role"] == "user"

    fake = FakeClient(["{}", '{"recipes": []}'])
    monkeypatch.setattr(provider, "_get_client", lambda: fake)
    with pytest.raises(LLMError):
        provider.generate(_ctx())


def test_missing_credentials(monkeypatch):
    monkeypatch.setattr(get_settings(), "gigachat_credentials", None)
    with pytest.raises(LLMError):
        gp.GigaChatProvider()


class FlakyClient(FakeClient):
    """Первый запрос с response_format отклоняется (400), второй — без него — успешен."""

    def chat(self, payload):
        from gigachat.exceptions import BadRequestError

        self.payloads.append(dict(payload))
        if "response_format" in payload:
            raise BadRequestError("https://gigachat/chat", 400, b"response_format unsupported", None)
        return _completion(self.replies.pop(0))


class DownClient(FakeClient):
    def chat(self, payload):
        raise ConnectionError("connection refused")


def test_response_format_rejected_then_retry(provider, monkeypatch):
    monkeypatch.setattr(gp.GigaChatProvider, "_json_schema_supported", True)
    fake = FlakyClient([json.dumps(VALID)])
    monkeypatch.setattr(provider, "_get_client", lambda: fake)
    assert provider.generate(_ctx())[0].name == "Курица с рисом"
    assert len(fake.payloads) == 2 and "response_format" not in fake.payloads[1]


def test_network_error_becomes_llm_error(provider, monkeypatch):
    monkeypatch.setattr(provider, "_get_client", lambda: DownClient([]))
    with pytest.raises(LLMError, match="недоступен"):
        provider.generate(_ctx())


class StaleConnectionClient(FakeClient):
    """Первый запрос падает на разорванном keep-alive соединении, повтор успешен."""

    def chat(self, payload):
        import httpx

        self.payloads.append(dict(payload))
        if len(self.payloads) == 1:
            raise httpx.ReadError("[SSL: UNEXPECTED_EOF_WHILE_READING] EOF occurred in violation of protocol")
        return _completion(self.replies.pop(0))


def test_stale_connection_is_retried_once(provider, monkeypatch):
    fake = StaleConnectionClient([json.dumps(VALID)])
    monkeypatch.setattr(provider, "_get_client", lambda: fake)
    assert provider.generate(_ctx())[0].name == "Курица с рисом"
    assert len(fake.payloads) == 2


def test_placeholder_steps_are_dropped():
    from app.services.generation import _clean_text, _meaningful

    steps = ["...", "…", "1. Разогрейте духовку до 200 °C.", "Шаг 2: Отварите рис 15 минут.", " "]
    assert [_clean_text(s) for s in steps if _meaningful(s)] == ["Разогрейте духовку до 200 °C.", "Отварите рис 15 минут."]
