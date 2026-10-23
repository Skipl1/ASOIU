import logging

from app.config import get_settings
from app.services.llm.base import (
    GenerationContext,
    LLMBusyError,
    LLMError,
    LLMRecipe,
    RecipeProvider,
)
from app.services.llm.mock_provider import MockProvider

logger = logging.getLogger("grsn.llm")

__all__ = [
    "GenerationContext",
    "LLMBusyError",
    "LLMError",
    "LLMRecipe",
    "MockProvider",
    "RecipeProvider",
    "get_primary_provider",
]


def get_primary_provider() -> RecipeProvider:
    """Основная модель генерации согласно настройке LLM_PROVIDER."""
    settings = get_settings()
    if settings.llm_provider == "gigachat":
        try:
            from app.services.llm.gigachat_provider import GigaChatProvider

            return GigaChatProvider()
        except LLMError as exc:
            if not settings.llm_fallback_to_mock:
                raise
            logger.warning("GigaChat не настроен (%s), используется локальный генератор", exc)
    return MockProvider()
