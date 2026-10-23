"""Общий контракт модели генерации рецептов."""

import uuid
from dataclasses import dataclass, field
from typing import Literal, Protocol

from pydantic import BaseModel, Field, field_validator, model_validator


class LLMError(Exception):
    """Модель генерации недоступна или вернула некорректный ответ."""


class LLMBusyError(LLMError):
    """Очередь к модели переполнена (Freemium GigaChat — один поток)."""


@dataclass(frozen=True)
class ContextIngredient:
    code: str  # короткий код для промпта: I1, I2, ...
    id: uuid.UUID
    name: str
    category_code: str | None
    category: str | None
    protein: float
    fat: float
    carbs: float
    calories: float
    available_g: float | None


@dataclass
class GenerationContext:
    goal_code: str
    goal_name: str
    goal_description: str
    meal_target: dict  # calories, protein, fat, carbs — для одного приёма пищи
    macro_pct: dict  # protein, fat, carbs — целевые доли, %
    variants: int
    difficulty: str | None
    comment: str | None
    ingredients: list[ContextIngredient]
    forbidden: list[str] = field(default_factory=list)
    liked: list[str] = field(default_factory=list)
    disliked: list[str] = field(default_factory=list)
    seed: int = 0
    meal_type: str | None = None  # breakfast | lunch | dinner | snack
    recent: list[str] = field(default_factory=list)  # последние рецепты пользователя — не повторять


DIFFICULTY_SYNONYMS = {
    "low": ("easy", "simple", "низкая", "лёгкая", "легкая", "простая", "низкий"),
    "medium": ("normal", "moderate", "average", "средняя", "средний", "умеренная"),
    "high": ("hard", "difficult", "complex", "высокая", "высокий", "сложная"),
}


class LLMRecipeItem(BaseModel):
    """Ингредиент рецепта: по названию из списка (GigaChat) или по внутреннему коду (локальный генератор)."""

    code: str | None = Field(default=None, description="Внутренний код ингредиента, например I3")
    name: str | None = Field(default=None, description="Название ингредиента из списка")
    massG: float = Field(gt=0, description="Масса в граммах")

    @model_validator(mode="after")
    def _has_identifier(self):
        if not (self.code or self.name):
            raise ValueError("у ингредиента не указано название")
        return self


class LLMRecipe(BaseModel):
    name: str = Field(min_length=3, max_length=200)
    servings: int = Field(default=1, ge=1, le=10)
    ingredients: list[LLMRecipeItem] = Field(min_length=1, max_length=12)
    steps: list[str] = Field(min_length=1, max_length=15)
    cookingTimeMin: int | None = Field(default=None, ge=1, le=600)
    difficulty: Literal["low", "medium", "high"] | None = None
    tips: list[str] = Field(default_factory=list, max_length=6)

    @field_validator("difficulty", mode="before")
    @classmethod
    def normalize_difficulty(cls, value):
        """Модель иногда пишет «easy», «средняя» и т. п. — приводим к коду или отбрасываем."""
        if value is None:
            return None
        v = str(value).strip().lower()
        for code, words in DIFFICULTY_SYNONYMS.items():
            if v == code or v in words:
                return code
        return None


class LLMResponse(BaseModel):
    recipes: list[LLMRecipe] = Field(min_length=1, max_length=3)


class RecipeProvider(Protocol):
    name: str

    def generate(self, context: GenerationContext) -> list[LLMRecipe]: ...
