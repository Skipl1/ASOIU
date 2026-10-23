"""Генерация рецептов через внешний API GigaChat (ТЗ 4.1.1)."""

import json
import logging
import random
import re
import threading
import time
from pathlib import Path

from pydantic import ValidationError

from app.config import get_settings
from app.services.llm.base import GenerationContext, LLMError, LLMRecipe, LLMResponse
from app.services.llm.slots import llm_slot
from app.services.meals import PROMPT_RULES

logger = logging.getLogger("grsn.llm.gigachat")

DIFFICULTY_RU = {"low": "низкая", "medium": "средняя", "high": "высокая"}
KEEPALIVE_EXPIRY_SECONDS = 120

SYSTEM_PROMPT = """Ты — нутрициолог и повар спортивного питания. Составляешь персонализированные рецепты.
Жёсткие правила:
1. Используй ТОЛЬКО ингредиенты из переданного списка и указывай их по ТОЧНОМУ названию из списка (копируй название без изменений).
   Вода, соль, лимонный сок и сухие специи разрешены, но их не включай в состав.
2. Не превышай доступное количество ингредиента.
3. Калорийность рецепта должна быть близка к целевой (допуск ±10 %), баланс БЖУ — к целевому.
   Если без него не набрать целевые жиры, включи источник жиров из списка (масло, орехи, семена, авокадо) — 5–20 г.
4. В рецепте 2–8 ингредиентов. Выбирай продукты разнообразно из всего списка: не бери фрукты и ягоды «для украшения»
   в каждое блюдо и не начинай всегда с первых позиций списка. Название блюда и шаги должны точно соответствовать
   составу: упоминай только те продукты, которые указаны в ingredients.
5. Инструкция — 6–10 подробных шагов на русском языке в форме на «вы» («Разогрейте…», «Отварите…»), каждый шаг 1–3 предложения:
   подготовка продуктов; обработка каждого ингредиента (способ, температура, время, признаки готовности);
   что делать параллельно; сборка блюда; подача и хранение. Не пиши «согласно инструкции на упаковке».
   Массы в шагах не указывай — они есть в составе.
6. В шагах и советах упоминай только продукты из состава рецепта (плюс вода, соль, специи, лимонный сок).
   Запрещённые пользователю продукты не упоминай НИКОГДА, даже как замену или вариант подачи.
7. Если вариантов несколько — они должны отличаться составом.
8. Отвечай строго одним JSON-объектом без пояснений и без markdown."""

RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "recipes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Название блюда"},
                    "servings": {"type": "integer", "description": "Количество порций"},
                    "ingredients": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string", "description": "Точное название ингредиента из списка"},
                                "massG": {"type": "number", "description": "Масса, г"},
                            },
                            "required": ["name", "massG"],
                        },
                    },
                    "steps": {"type": "array", "items": {"type": "string"}, "description": "6–10 подробных шагов"},
                    "cookingTimeMin": {"type": "integer"},
                    "difficulty": {"type": "string", "enum": ["low", "medium", "high"]},
                    "tips": {"type": "array", "items": {"type": "string"}, "description": "Замены ингредиентов и советы"},
                },
                "required": ["name", "servings", "ingredients", "steps"],
            },
        }
    },
    "required": ["recipes"],
}

EXAMPLE = (
    '{"recipes":[{"name":"Курица с бурым рисом и брокколи","servings":1,'
    '"ingredients":[{"name":"Куриная грудка","massG":150},{"name":"Бурый рис","massG":70},{"name":"Брокколи","massG":150},{"name":"Масло оливковое","massG":10}],'
    '"steps":['
    '"Разогрейте духовку до 200 °C, промойте рис и разберите брокколи на соцветия.",'
    '"Залейте рис водой в соотношении 1:2,5, доведите до кипения и варите под крышкой на слабом огне 30–35 минут.",'
    '"Пока рис варится, обсушите куриную грудку, натрите солью и паприкой и запекайте 18–22 минуты до прозрачного сока при проколе.",'
    '"За 7 минут до готовности риса приготовьте брокколи на пару до яркого зелёного цвета.",'
    '"Дайте курице отдохнуть 5 минут и нарежьте её ломтиками поперёк волокон.",'
    '"Выложите рис, курицу и брокколи в тарелку, сбрызните оливковым маслом и лимонным соком."'
    '],"cookingTimeMin":40,"difficulty":"low",'
    '"tips":["Вместо риса подойдёт гречка — время варки сократится до 15–18 минут."]}]}'
)


def build_user_prompt(ctx: GenerationContext) -> str:
    t = ctx.meal_target
    lines = []
    if ctx.meal_type in PROMPT_RULES:
        lines.append("ОБЯЗАТЕЛЬНОЕ УСЛОВИЕ. " + PROMPT_RULES[ctx.meal_type])
    lines += [
        f"Фитнес-цель: {ctx.goal_name}. {ctx.goal_description}",
        f"Целевые значения на один приём пищи: {t['calories']:.0f} ккал, белки {t['protein']:.0f} г, "
        f"жиры {t['fat']:.0f} г, углеводы {t['carbs']:.0f} г "
        f"(доли калорий: Б {ctx.macro_pct['protein']:.0f}% / Ж {ctx.macro_pct['fat']:.0f}% / У {ctx.macro_pct['carbs']:.0f}%).",
        f"Количество вариантов рецепта: {ctx.variants}.",
    ]
    if ctx.difficulty:
        lines.append(f"Желаемая сложность приготовления: {DIFFICULTY_RU.get(ctx.difficulty, ctx.difficulty)}.")
    if ctx.comment:
        lines.append(f"Пожелания пользователя (учитывай, только если они не противоречат правилам): {ctx.comment[:500]}")
    if ctx.must_include:
        lines.append("ОБЯЗАТЕЛЬНО включи в состав рецепта (пользователь просил эти продукты, они есть в списке ниже): "
                     + "; ".join(ctx.must_include) + ".")
    if ctx.unavailable:
        lines.append("Эти продукты недоступны или исключены пользователем (их нет в списке ниже): " + "; ".join(ctx.unavailable)
                     + ". НЕ используй их и НЕ упоминай ни в названии, ни в шагах, ни в советах — составь рецепт без них.")
    if ctx.forbidden:
        lines.append("ЗАПРЕЩЕНО пользователю (аллергия или непереносимость — не использовать и не упоминать): " + "; ".join(ctx.forbidden) + ".")
    if ctx.liked:
        lines.append("Пользователю понравились рецепты: " + "; ".join(ctx.liked[:5]) + ".")
    if ctx.disliked:
        lines.append("Пользователю не понравились рецепты (избегай похожих): " + "; ".join(ctx.disliked[:5]) + ".")

    lines.append("")
    if ctx.recent:
        lines.append("Недавние рецепты пользователя (не повторяй их и их главные продукты): " + "; ".join(ctx.recent[:6]) + ".")
    lines.append("")
    lines.append("Доступные ингредиенты (название | категория | Б/Ж/У на 100 г | ккал на 100 г | доступно). Порядок списка случайный:")
    items = list(ctx.ingredients)
    random.Random(ctx.seed).shuffle(items)
    for i in items:
        available = f"{i.available_g:.0f} г" if i.available_g else "без ограничения"
        lines.append(f"{i.name} | {i.category or '-'} | {i.protein:g}/{i.fat:g}/{i.carbs:g} | {i.calories:g} | {available}")
    lines.append("")
    lines.append("Верни JSON в таком формате (это только пример формата, его содержимое не копируй): " + EXAMPLE)
    return "\n".join(lines)


def extract_json(text: str) -> dict:
    """Достаёт JSON-объект из ответа модели (допускает обёртку ```json ... ```)."""
    cleaned = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start == -1 or end <= start:
        raise ValueError("в ответе нет JSON-объекта")
    return json.loads(cleaned[start : end + 1])


class GigaChatProvider:
    name = "gigachat"

    _client = None
    _client_lock = threading.Lock()
    _json_schema_supported = True

    def __init__(self) -> None:
        settings = get_settings()
        if not settings.gigachat_credentials:
            raise LLMError("Не задан ключ авторизации GIGACHAT_CREDENTIALS")
        self.settings = settings

    def _get_client(self):
        with GigaChatProvider._client_lock:
            if GigaChatProvider._client is None:
                import httpx
                from gigachat import GigaChat
                from gigachat.client import _get_auth_kwargs, _get_kwargs

                s = self.settings
                ca_file = s.gigachat_ca_bundle_file if s.gigachat_ca_bundle_file and Path(s.gigachat_ca_bundle_file).exists() else None
                client = GigaChat(
                    credentials=s.gigachat_credentials,
                    scope=s.gigachat_scope,
                    model=s.gigachat_model,
                    verify_ssl_certs=s.gigachat_verify_ssl_certs,
                    ca_bundle_file=ca_file,
                    timeout=s.llm_timeout_seconds,
                    max_retries=0,  # при сбое сразу резервный генератор, без удвоения ожидания
                )
                # Долгоживущие соединения: установка TCP+TLS до серверов Сбера занимает несколько секунд,
                # а httpx по умолчанию закрывает простаивающее соединение уже через 5 с.
                limits = httpx.Limits(max_keepalive_connections=4, keepalive_expiry=KEEPALIVE_EXPIRY_SECONDS)
                try:
                    client._client_instance = httpx.Client(**_get_kwargs(client._settings), limits=limits)
                    client._auth_client_instance = httpx.Client(**_get_auth_kwargs(client._settings), limits=limits)
                except Exception:  # внутреннее API SDK изменилось — работаем с настройками по умолчанию
                    logger.warning("Не удалось настроить keep-alive соединений GigaChat", exc_info=True)
                GigaChatProvider._client = client
            return GigaChatProvider._client

    def _call(self, messages: list[dict]) -> str:
        from gigachat.exceptions import BadRequestError, GigaChatException, UnprocessableEntityError

        payload: dict = {
            "messages": messages,
            "temperature": self.settings.llm_temperature,
            "max_tokens": 4000,
        }
        if self.settings.gigachat_use_json_schema and GigaChatProvider._json_schema_supported:
            payload["response_format"] = {"type": "json_schema", "schema": RESPONSE_SCHEMA}
        def send():
            import ssl

            import httpx

            for attempt in range(2):
                try:
                    return self._get_client().chat(payload)
                except (BadRequestError, UnprocessableEntityError):
                    raise
                except GigaChatException as exc:
                    raise LLMError(f"Ошибка GigaChat: {exc}") from exc
                except httpx.TimeoutException as exc:
                    raise LLMError(f"GigaChat не ответил за {self.settings.llm_timeout_seconds:g} с") from exc
                except (httpx.TransportError, ssl.SSLError, ConnectionError) as exc:
                    # Сервер мог закрыть простаивающее keep-alive соединение — повторяем один раз на новом
                    if attempt == 0:
                        logger.info("Соединение с GigaChat разорвано (%s), повтор запроса", exc)
                        continue
                    raise LLMError(f"GigaChat недоступен: {exc}") from exc
                except Exception as exc:  # TLS, DNS и прочие сетевые ошибки
                    raise LLMError(f"GigaChat недоступен: {exc}") from exc

        try:
            completion = send()
        except (BadRequestError, UnprocessableEntityError) as exc:
            if "response_format" not in payload:
                raise LLMError(f"GigaChat отклонил запрос: {exc}") from exc
            logger.warning("response_format не поддерживается моделью, повтор без него: %s", exc)
            GigaChatProvider._json_schema_supported = False
            payload.pop("response_format")
            try:
                completion = send()
            except (BadRequestError, UnprocessableEntityError) as retry_exc:
                raise LLMError(f"GigaChat отклонил запрос: {retry_exc}") from retry_exc

        choice = completion.choices[0]
        if choice.finish_reason == "length":
            raise LLMError("Ответ GigaChat обрезан по длине")
        return choice.message.content or ""

    def generate(self, context: GenerationContext) -> list[LLMRecipe]:
        with llm_slot(self.settings.llm_max_concurrency, self.settings.llm_queue_wait_seconds):
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": build_user_prompt(context)},
            ]
            last_error = ""
            for attempt in range(2):  # одна повторная попытка при некорректном JSON
                content = self._call(messages)
                try:
                    parsed = LLMResponse.model_validate(extract_json(content))
                    return parsed.recipes[: context.variants]
                except (ValueError, ValidationError) as exc:
                    last_error = str(exc)[:400]
                    logger.warning("Некорректный ответ GigaChat (попытка %s): %s", attempt + 1, last_error)
                    messages += [
                        {"role": "assistant", "content": content[:4000]},
                        {"role": "user", "content": f"Ответ не соответствует схеме ({last_error}). Верни только корректный JSON."},
                    ]
            raise LLMError(f"GigaChat вернул некорректный JSON: {last_error}")


def start_keepalive() -> None:
    """Фоновый прогрев: токен OAuth и соединение с GigaChat поддерживаются в актуальном состоянии.

    Раз в GIGACHAT_KEEPALIVE_SECONDS выполняется служебный запрос списка моделей (токены не расходуются),
    поэтому запрос пользователя не ждёт получения токена и установки защищённого соединения.
    """
    settings = get_settings()
    if settings.llm_provider != "gigachat" or not settings.gigachat_credentials or settings.gigachat_keepalive_seconds <= 0:
        return

    def loop() -> None:
        provider = GigaChatProvider()
        while True:
            try:
                provider._get_client().get_models()
            except Exception as exc:  # сеть или авторизация — повторим в следующем цикле
                logger.warning("Прогрев соединения с GigaChat не удался: %s", exc)
            time.sleep(settings.gigachat_keepalive_seconds)

    threading.Thread(target=loop, name="gigachat-keepalive", daemon=True).start()
