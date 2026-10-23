"""ORM-модели. Соответствуют физической модели данных ТП АС ГРСН.

Дополнительно к 14 таблицам ТП введены:
  parameter_history     — история замеров (эндпоинт /profile/parameter-history, анализ динамики);
  ingredient_components — состав составного ингредиента (правило ТЗ 4.7.2, п. 3);
  audit_log             — журнал действий и событий входа (логи администратора, неудачные входы).
"""

import uuid
from datetime import date, datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

JsonType = JSON().with_variant(JSONB(), "postgresql")


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def as_utc(value: datetime | None) -> datetime | None:
    """SQLite возвращает naive-datetime; приводим к UTC для корректных сравнений."""
    if value is not None and value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def Num(precision: int = 8, scale: int = 2) -> Numeric:
    return Numeric(precision, scale, asdecimal=False)


def Ts() -> DateTime:
    return DateTime(timezone=True)


ACTIVITY_LEVELS = (1.2, 1.375, 1.55, 1.725, 1.9)

# recipes.generation_status: сгенерирован (только в истории) / включён пользователем в рацион (идёт в отчёты и анализ)
RECIPE_GENERATED = "generated"
RECIPE_ACCEPTED = "accepted"


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("role IN ('user', 'admin')", name="ck_users_role"),
        CheckConstraint("status IN ('active', 'blocked', 'deleted')", name="ck_users_status"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="user")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    registered_at: Mapped[datetime] = mapped_column(Ts(), nullable=False, default=utcnow)
    last_login_at: Mapped[datetime | None] = mapped_column(Ts())
    failed_login_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(Ts())
    token_version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    profile: Mapped["UserProfile | None"] = relationship(back_populates="user", uselist=False, cascade="all, delete-orphan")


class FitnessGoal(Base):
    __tablename__ = "fitness_goals"

    fitness_goal_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(40), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    calorie_correction: Mapped[float] = mapped_column(Num(), nullable=False, default=0)
    description: Mapped[str | None] = mapped_column(Text)
    calc_rule: Mapped[str | None] = mapped_column(Text)
    protein_pct: Mapped[float] = mapped_column(Num(5, 2), nullable=False, default=20)
    fat_pct: Mapped[float] = mapped_column(Num(5, 2), nullable=False, default=30)
    carb_pct: Mapped[float] = mapped_column(Num(5, 2), nullable=False, default=50)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class UserProfile(Base):
    __tablename__ = "user_profiles"
    __table_args__ = (
        CheckConstraint("weight_kg BETWEEN 30 AND 300", name="ck_profile_weight"),
        CheckConstraint("height_cm BETWEEN 100 AND 250", name="ck_profile_height"),
        CheckConstraint("age BETWEEN 14 AND 100", name="ck_profile_age"),
        CheckConstraint("sex IN ('male', 'female')", name="ck_profile_sex"),
        CheckConstraint("activity_level BETWEEN 1.2 AND 1.9", name="ck_profile_activity"),
    )

    profile_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, unique=True)
    fitness_goal_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("fitness_goals.fitness_goal_id", ondelete="SET NULL"))
    weight_kg: Mapped[float] = mapped_column(Num(5, 1), nullable=False)
    height_cm: Mapped[float] = mapped_column(Num(5, 1), nullable=False)
    age: Mapped[int] = mapped_column(Integer, nullable=False)
    sex: Mapped[str] = mapped_column(String(10), nullable=False)
    activity_level: Mapped[float] = mapped_column(Num(4, 3), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(Ts(), nullable=False, default=utcnow, onupdate=utcnow)

    user: Mapped[User] = relationship(back_populates="profile")
    goal: Mapped[FitnessGoal | None] = relationship()


class ParameterHistory(Base):
    __tablename__ = "parameter_history"

    record_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    weight_kg: Mapped[float] = mapped_column(Num(5, 1), nullable=False)
    height_cm: Mapped[float] = mapped_column(Num(5, 1), nullable=False)
    age: Mapped[int] = mapped_column(Integer, nullable=False)
    activity_level: Mapped[float] = mapped_column(Num(4, 3), nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(Ts(), nullable=False, default=utcnow)


class IngredientCategory(Base):
    __tablename__ = "ingredient_categories"

    category_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    code: Mapped[str | None] = mapped_column(String(40), unique=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text)


class Allergen(Base):
    __tablename__ = "allergens"

    allergen_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    code: Mapped[str | None] = mapped_column(String(40), unique=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text)
    synonyms: Mapped[list] = mapped_column(JsonType, nullable=False, default=list)


class IngredientAllergen(Base):
    __tablename__ = "ingredient_allergens"

    ingredient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("ingredients.ingredient_id", ondelete="CASCADE"), primary_key=True)
    allergen_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("allergens.allergen_id", ondelete="CASCADE"), primary_key=True)


class IngredientComponent(Base):
    __tablename__ = "ingredient_components"
    __table_args__ = (CheckConstraint("composite_id <> component_id", name="ck_component_not_self"),)

    composite_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("ingredients.ingredient_id", ondelete="CASCADE"), primary_key=True)
    component_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("ingredients.ingredient_id", ondelete="CASCADE"), primary_key=True)


class Ingredient(Base):
    __tablename__ = "ingredients"
    __table_args__ = (
        CheckConstraint(
            "protein_per_100g >= 0 AND fat_per_100g >= 0 AND carb_per_100g >= 0 AND calories_per_100g >= 0",
            name="ck_ingredient_non_negative",
        ),
        CheckConstraint("protein_per_100g + fat_per_100g + carb_per_100g <= 100", name="ck_ingredient_macro_sum"),
    )

    ingredient_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    code: Mapped[str | None] = mapped_column(String(60), unique=True)
    category_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("ingredient_categories.category_id", ondelete="SET NULL"))
    name: Mapped[str] = mapped_column(String(160), nullable=False, unique=True)
    protein_per_100g: Mapped[float] = mapped_column(Num(6, 2), nullable=False)
    fat_per_100g: Mapped[float] = mapped_column(Num(6, 2), nullable=False)
    carb_per_100g: Mapped[float] = mapped_column(Num(6, 2), nullable=False)
    calories_per_100g: Mapped[float] = mapped_column(Num(7, 2), nullable=False)
    is_composite: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    name_synonyms: Mapped[list] = mapped_column(JsonType, nullable=False, default=list)
    composition_description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(Ts(), nullable=False, default=utcnow)

    category: Mapped[IngredientCategory | None] = relationship(lazy="joined")
    allergens: Mapped[list[Allergen]] = relationship(secondary="ingredient_allergens", lazy="selectin", order_by=Allergen.name)
    components: Mapped[list["Ingredient"]] = relationship(
        secondary="ingredient_components",
        primaryjoin="Ingredient.ingredient_id == IngredientComponent.composite_id",
        secondaryjoin="Ingredient.ingredient_id == IngredientComponent.component_id",
        lazy="selectin",
        join_depth=3,
    )


class AvailableIngredient(Base):
    __tablename__ = "available_ingredients"
    __table_args__ = (CheckConstraint("available_amount_g IS NULL OR available_amount_g > 0", name="ck_available_amount"),)

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.user_id", ondelete="CASCADE"), primary_key=True)
    ingredient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("ingredients.ingredient_id", ondelete="CASCADE"), primary_key=True)
    available_amount_g: Mapped[float | None] = mapped_column(Num(8, 1))
    updated_at: Mapped[datetime] = mapped_column(Ts(), nullable=False, default=utcnow)

    ingredient: Mapped[Ingredient] = relationship(lazy="joined")


class UserRestriction(Base):
    __tablename__ = "user_restrictions"
    __table_args__ = (
        CheckConstraint("restriction_type IN ('ingredient', 'allergen', 'substance')", name="ck_restriction_type"),
        CheckConstraint(
            "(restriction_type = 'ingredient' AND ingredient_id IS NOT NULL AND allergen_id IS NULL) OR "
            "(restriction_type = 'allergen' AND allergen_id IS NOT NULL AND ingredient_id IS NULL) OR "
            "(restriction_type = 'substance' AND ingredient_id IS NULL AND allergen_id IS NULL)",
            name="ck_restriction_target",
        ),
    )

    restriction_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    ingredient_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("ingredients.ingredient_id", ondelete="CASCADE"))
    allergen_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("allergens.allergen_id", ondelete="CASCADE"))
    original_name: Mapped[str] = mapped_column(String(160), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(160), nullable=False)
    restriction_type: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(Ts(), nullable=False, default=utcnow)

    ingredient: Mapped[Ingredient | None] = relationship(lazy="joined")
    allergen: Mapped[Allergen | None] = relationship(lazy="joined")


class GenerationRequest(Base):
    __tablename__ = "generation_requests"
    __table_args__ = (
        CheckConstraint("variant_count BETWEEN 1 AND 3", name="ck_generation_variants"),
        CheckConstraint("daily_norm_share > 0 AND daily_norm_share <= 1", name="ck_generation_share"),
        CheckConstraint("status IN ('created', 'processing', 'completed', 'rejected')", name="ck_generation_status"),
    )

    generation_request_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    fitness_goal_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("fitness_goals.fitness_goal_id", ondelete="SET NULL"))
    variant_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    daily_norm_share: Mapped[float] = mapped_column(Num(4, 3), nullable=False)
    difficulty: Mapped[str | None] = mapped_column(String(10))
    comment: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="created")
    rejection_reason: Mapped[str | None] = mapped_column(Text)
    recommended_ingredients: Mapped[list] = mapped_column(JsonType, nullable=False, default=list)
    conflicts: Mapped[list] = mapped_column(JsonType, nullable=False, default=list)
    provider: Mapped[str | None] = mapped_column(String(30))
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    requested_at: Mapped[datetime] = mapped_column(Ts(), nullable=False, default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(Ts())


class Recipe(Base):
    __tablename__ = "recipes"
    __table_args__ = (CheckConstraint("servings >= 1", name="ck_recipe_servings"),)

    recipe_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    generation_request_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("generation_requests.generation_request_id", ondelete="SET NULL")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    fitness_goal_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("fitness_goals.fitness_goal_id", ondelete="SET NULL"))
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    generation_status: Mapped[str] = mapped_column(String(20), nullable=False, default=RECIPE_GENERATED)
    matches_restrictions: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    mismatch_reasons: Mapped[list] = mapped_column(JsonType, nullable=False, default=list)
    protein_total_g: Mapped[float] = mapped_column(Num(8, 1), nullable=False)
    fat_total_g: Mapped[float] = mapped_column(Num(8, 1), nullable=False)
    carb_total_g: Mapped[float] = mapped_column(Num(8, 1), nullable=False)
    calories_kcal: Mapped[float] = mapped_column(Num(8, 1), nullable=False)
    servings: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    cooking_instruction: Mapped[list] = mapped_column(JsonType, nullable=False, default=list)
    cooking_time_min: Mapped[int | None] = mapped_column(Integer)
    difficulty: Mapped[str | None] = mapped_column(String(10))
    tips: Mapped[list] = mapped_column(JsonType, nullable=False, default=list)
    meal_share: Mapped[float | None] = mapped_column(Num(4, 3))
    target_calories: Mapped[float | None] = mapped_column(Num(8, 1))
    source: Mapped[str | None] = mapped_column(String(30))
    created_at: Mapped[datetime] = mapped_column(Ts(), nullable=False, default=utcnow, index=True)
    updated_at: Mapped[datetime | None] = mapped_column(Ts())

    goal: Mapped[FitnessGoal | None] = relationship(lazy="joined")
    generation_request: Mapped[GenerationRequest | None] = relationship(lazy="joined")
    items: Mapped[list["RecipeIngredient"]] = relationship(
        back_populates="recipe", cascade="all, delete-orphan", order_by="RecipeIngredient.list_order", lazy="selectin"
    )
    ratings: Mapped[list["RecipeRating"]] = relationship(cascade="all, delete-orphan", lazy="selectin")


class RecipeIngredient(Base):
    __tablename__ = "recipe_ingredients"
    __table_args__ = (CheckConstraint("mass_g > 0", name="ck_recipe_ingredient_mass"),)

    recipe_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("recipes.recipe_id", ondelete="CASCADE"), primary_key=True)
    ingredient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("ingredients.ingredient_id", ondelete="RESTRICT"), primary_key=True)
    mass_g: Mapped[float] = mapped_column(Num(8, 1), nullable=False)
    list_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    recipe: Mapped[Recipe] = relationship(back_populates="items")
    ingredient: Mapped[Ingredient] = relationship(lazy="joined")


class RecipeRating(Base):
    __tablename__ = "recipe_ratings"
    __table_args__ = (
        CheckConstraint("score BETWEEN 1 AND 5", name="ck_rating_score"),
        UniqueConstraint("user_id", "recipe_id", name="uq_rating_user_recipe"),
    )

    rating_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    recipe_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("recipes.recipe_id", ondelete="CASCADE"), nullable=False, index=True)
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    comment: Mapped[str | None] = mapped_column(Text)
    rated_at: Mapped[datetime] = mapped_column(Ts(), nullable=False, default=utcnow)


class NutritionReport(Base):
    __tablename__ = "nutrition_reports"
    __table_args__ = (
        CheckConstraint("export_format IN ('pdf', 'xlsx', 'csv')", name="ck_report_format"),
        CheckConstraint("period_end >= period_start", name="ck_report_period"),
    )

    report_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    fitness_goal_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("fitness_goals.fitness_goal_id", ondelete="SET NULL"))
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    export_format: Mapped[str] = mapped_column(String(10), nullable=False)
    total_calories: Mapped[float] = mapped_column(Num(10, 1), nullable=False, default=0)
    average_calories: Mapped[float] = mapped_column(Num(10, 1), nullable=False, default=0)
    total_protein_g: Mapped[float] = mapped_column(Num(10, 1), nullable=False, default=0)
    total_fat_g: Mapped[float] = mapped_column(Num(10, 1), nullable=False, default=0)
    total_carb_g: Mapped[float] = mapped_column(Num(10, 1), nullable=False, default=0)
    recipes_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    file_name: Mapped[str | None] = mapped_column(String(255))
    formed_at: Mapped[datetime] = mapped_column(Ts(), nullable=False, default=utcnow)

    goal: Mapped[FitnessGoal | None] = relationship(lazy="joined")


class AuditLog(Base):
    __tablename__ = "audit_log"

    log_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.user_id", ondelete="SET NULL"), index=True)
    action: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    entity: Mapped[str | None] = mapped_column(String(64))
    entity_id: Mapped[str | None] = mapped_column(String(64))
    details: Mapped[dict] = mapped_column(JsonType, nullable=False, default=dict)
    ip: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(Ts(), nullable=False, default=utcnow, index=True)
