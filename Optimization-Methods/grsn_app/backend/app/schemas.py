"""Pydantic-схемы REST API. Имена полей в JSON — camelCase, как в api/openapi.yaml."""

import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
from pydantic.alias_generators import to_camel

from app.models import ACTIVITY_LEVELS


class Schema(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)


# ---------- auth ----------


class RegisterRequest(Schema):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=64)

    @field_validator("name")
    @classmethod
    def _strip_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Имя не может быть пустым")
        return v


class LoginRequest(Schema):
    # при входе формат не валидируется строго: служебные учётные записи используют домен .local
    email: str = Field(min_length=3, max_length=255, pattern=r"^[^@\s]+@[^@\s]+$")
    password: str = Field(min_length=1, max_length=128)


class UserOut(Schema):
    id: uuid.UUID
    name: str
    email: str
    role: str
    status: str


class AuthResponse(Schema):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserOut


# ---------- profile ----------


class FitnessGoalOut(Schema):
    id: uuid.UUID
    code: str
    name: str
    calorie_delta: float
    description: str | None = None
    calc_rule: str | None = None
    protein_pct: float
    fat_pct: float
    carb_pct: float


class ActivityLevelOut(Schema):
    value: float
    description: str


def _check_activity(v: float) -> float:
    if not any(abs(v - level) < 1e-6 for level in ACTIVITY_LEVELS):
        raise ValueError("Допустимые коэффициенты активности: " + ", ".join(str(x) for x in ACTIVITY_LEVELS))
    return v


class ProfileUpdate(Schema):
    weight_kg: float = Field(ge=30, le=300)
    height_cm: float = Field(ge=100, le=250)
    age: int = Field(ge=14, le=100)
    gender: Literal["male", "female"]
    activity_level: float
    goal_id: uuid.UUID

    @field_validator("activity_level")
    @classmethod
    def validate_activity(cls, v: float) -> float:
        return _check_activity(v)


class NutritionTotals(Schema):
    calories: float
    protein: float
    fat: float
    carbs: float


class ProfileOut(Schema):
    id: uuid.UUID | None = None
    user_id: uuid.UUID
    is_complete: bool
    weight_kg: float | None = None
    height_cm: float | None = None
    age: int | None = None
    gender: str | None = None
    activity_level: float | None = None
    goal: FitnessGoalOut | None = None
    bmr: float | None = None
    tdee: float | None = None
    target_calories: float | None = None
    daily_targets: NutritionTotals | None = None
    updated_at: datetime | None = None


class ParameterHistoryCreate(Schema):
    weight_kg: float = Field(ge=30, le=300)
    height_cm: float = Field(ge=100, le=250)
    age: int = Field(ge=14, le=100)
    activity_level: float

    @field_validator("activity_level")
    @classmethod
    def validate_activity(cls, v: float) -> float:
        return _check_activity(v)


class ParameterHistoryItem(ParameterHistoryCreate):
    id: uuid.UUID
    recorded_at: datetime


# ---------- dictionaries ----------


class CategoryInput(Schema):
    code: str | None = Field(default=None, max_length=40)
    name: str = Field(min_length=1, max_length=120)
    description: str | None = None


class CategoryOut(CategoryInput):
    id: uuid.UUID
    ingredients_count: int = 0


class AllergenInput(Schema):
    code: str | None = Field(default=None, max_length=40)
    name: str = Field(min_length=1, max_length=120)
    description: str | None = None
    synonyms: list[str] = Field(default_factory=list)


class AllergenOut(AllergenInput):
    id: uuid.UUID


class AllergenShort(Schema):
    id: uuid.UUID
    name: str


class IngredientInput(Schema):
    code: str | None = Field(default=None, max_length=60)
    name: str = Field(min_length=1, max_length=160)
    category_id: uuid.UUID | None = None
    protein100g: float = Field(ge=0, le=100, alias="protein100g")
    fat100g: float = Field(ge=0, le=100, alias="fat100g")
    carbs100g: float = Field(ge=0, le=100, alias="carbs100g")
    calories100g: float = Field(ge=0, le=950, alias="calories100g")
    is_composite: bool = False
    synonyms: list[str] = Field(default_factory=list)
    allergen_ids: list[uuid.UUID] = Field(default_factory=list)
    component_ids: list[uuid.UUID] = Field(default_factory=list)
    composition_description: str | None = None


class IngredientShort(Schema):
    id: uuid.UUID
    name: str


class IngredientOut(Schema):
    id: uuid.UUID
    code: str | None = None
    name: str
    category_id: uuid.UUID | None = None
    category_name: str | None = None
    protein100g: float = Field(alias="protein100g")
    fat100g: float = Field(alias="fat100g")
    carbs100g: float = Field(alias="carbs100g")
    calories100g: float = Field(alias="calories100g")
    is_composite: bool
    synonyms: list[str]
    composition_description: str | None = None
    allergen_ids: list[uuid.UUID] = Field(default_factory=list)
    allergens: list[AllergenShort]
    effective_allergens: list[AllergenShort]
    components: list[IngredientShort] = Field(default_factory=list)
    is_allowed: bool | None = None
    violation_reasons: list[str] = Field(default_factory=list)


# ---------- restrictions ----------


class RestrictionCreate(Schema):
    source_text: str = Field(min_length=1, max_length=160)
    ingredient_id: uuid.UUID | None = None
    allergen_id: uuid.UUID | None = None
    as_substance: bool = False


class UserRestrictionOut(Schema):
    id: uuid.UUID
    source_text: str
    normalized_name: str
    type: Literal["ingredient", "allergen", "substance"]
    ingredient_id: uuid.UUID | None = None
    allergen_id: uuid.UUID | None = None
    target_name: str | None = None
    created_at: datetime


class MatchCandidateOut(Schema):
    type: Literal["ingredient", "allergen"]
    id: uuid.UUID
    name: str
    matched_by: str
    exact: bool


class MatchResult(Schema):
    query: str
    normalized: str
    unique: MatchCandidateOut | None = None
    candidates: list[MatchCandidateOut]


class AvailableCheckItem(Schema):
    ingredient_id: uuid.UUID
    name: str
    allergens: list[str]
    result: Literal["allowed", "excluded"]
    reasons: list[str]


# ---------- available ingredients ----------


class AvailableIngredientInput(Schema):
    ingredient_id: uuid.UUID
    available_qty_g: float | None = Field(default=None, gt=0, le=100000)


class AvailableIngredientsUpdate(Schema):
    items: list[AvailableIngredientInput] = Field(max_length=300)


class AvailableIngredientOut(Schema):
    ingredient_id: uuid.UUID
    available_qty_g: float | None
    ingredient: IngredientOut
    updated_at: datetime


# ---------- recipes ----------


class GenerateRecipeRequest(Schema):
    goal_id: uuid.UUID
    variants_count: int = Field(default=1, ge=1, le=3)
    meal_share: float = Field(gt=0, le=1)
    difficulty: Literal["low", "medium", "high"] | None = None
    comment: str | None = Field(default=None, max_length=500)
    meal_type: Literal["breakfast", "lunch", "dinner", "snack"] | None = None


class RecipeIngredientOut(Schema):
    ingredient_id: uuid.UUID
    name: str
    category_name: str | None = None
    mass_g: float
    position: int
    protein: float
    fat: float
    carbs: float
    calories: float


class RecipeCheck(Schema):
    indicator: str
    status: Literal["ok", "warn", "bad"]
    label: str
    comment: str


class RecipeSummary(Schema):
    id: uuid.UUID
    name: str
    goal_id: uuid.UUID | None = None
    goal_name: str | None = None
    calories_total: float
    protein_total: float
    fat_total: float
    carbs_total: float
    is_allowed: bool
    created_at: datetime
    rating: int | None = None
    source: str | None = None
    in_diet: bool = False
    meal_type: str | None = None


class RatingOut(Schema):
    id: uuid.UUID
    recipe_id: uuid.UUID
    score: int
    comment: str | None = None
    created_at: datetime


class RecipeOut(RecipeSummary):
    request_id: uuid.UUID | None = None
    servings: int
    serving_mass_g: float
    instructions: list[str]
    ingredients: list[RecipeIngredientOut]
    violation_reasons: list[str]
    cooking_time_min: int | None = None
    difficulty: str | None = None
    tips: list[str]
    meal_share: float | None = None
    target_calories: float | None = None
    deviation_kcal: float | None = None
    macro_percent: NutritionTotals | None = None
    checks: list[RecipeCheck]
    my_rating: RatingOut | None = None
    updated_at: datetime | None = None


class GenerateRecipeResponse(Schema):
    request_id: uuid.UUID
    status: Literal["generated", "failed"]
    provider: str | None = None
    duration_ms: int | None = None
    recipes: list[RecipeOut]
    failure_reason: str | None = None
    conflicts: list[str] = Field(default_factory=list)
    recommended_ingredients: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class RecipeItemUpdate(Schema):
    ingredient_id: uuid.UUID
    mass_g: float = Field(gt=0, le=5000)


class RecipeUpdate(Schema):
    name: str | None = Field(default=None, min_length=3, max_length=200)
    servings: int | None = Field(default=None, ge=1, le=20)
    ingredients: list[RecipeItemUpdate] | None = Field(default=None, min_length=1, max_length=20)
    instructions: list[str] | None = Field(default=None, min_length=3, max_length=20)


class RatingCreate(Schema):
    score: int = Field(ge=1, le=5)
    comment: str | None = Field(default=None, max_length=1000)


# ---------- reports & analysis ----------


class DailyNutrition(Schema):
    date: date
    calories: float
    protein: float
    fat: float
    carbs: float
    recipes: int


class NutritionReportOut(Schema):
    report_id: uuid.UUID | None = None
    date_from: date
    date_to: date
    goal_name: str | None = None
    recipes_count: int
    days_with_data: int
    average_calories: float
    total_calories: float
    total_protein: float
    total_fat: float
    total_carbs: float
    macro_percent: NutritionTotals
    target_calories: float | None = None
    deviation_calories: float | None = None
    deviation_status: str | None = None
    daily_calories: list[DailyNutrition]


class ReportExportRequest(Schema):
    date_from: date
    date_to: date
    format: Literal["pdf", "xlsx", "csv"]
    goal_id: uuid.UUID | None = None


class ReportExportResponse(Schema):
    report_id: uuid.UUID
    download_url: str
    file_name: str


class SavedReportOut(Schema):
    report_id: uuid.UUID
    date_from: date
    date_to: date
    format: str
    goal_name: str | None = None
    formed_at: datetime
    average_calories: float
    total_protein: float
    total_fat: float
    total_carbs: float
    recipes_count: int
    file_available: bool


class WeightPoint(Schema):
    day: int
    date: date
    weight_kg: float


class AnalysisRecommendation(Schema):
    priority: Literal["high", "medium", "low"]
    text: str
    reason: str


class NutritionAnalysis(Schema):
    date_from: date
    date_to: date
    goal_name: str | None
    target_calories_day: float
    target: NutritionTotals
    actual: NutritionTotals
    deviation: NutritionTotals
    deviation_percent: NutritionTotals
    recipes_analyzed: int
    days_with_data: int
    restrictions_count: int
    violations_found: int
    average_rating: float | None
    ratings_count: int
    compliance_score: float
    start_weight_kg: float
    end_weight_kg: float | None
    weight_change_kg: float | None
    forecast_weight_30d_kg: float | None = Field(alias="forecastWeight30dKg")
    trend_sufficient: bool
    measured_trend_kg_per_week: float | None
    calculated_weight_trend: list[WeightPoint]
    measured_weights: list[WeightPoint]
    recommendations: list[AnalysisRecommendation]


# ---------- admin ----------


class AdminUserOut(UserOut):
    created_at: datetime
    last_login_at: datetime | None = None
    recipes_count: int = 0
    failed_login_count: int = 0
    locked_until: datetime | None = None


class AdminUserUpdate(Schema):
    role: Literal["user", "admin"] | None = None
    status: Literal["active", "blocked", "deleted"] | None = None


class AuditLogOut(Schema):
    id: uuid.UUID
    user_id: uuid.UUID | None
    user_email: str | None = None
    action: str
    action_title: str
    entity: str | None = None
    entity_id: str | None = None
    details: dict
    ip: str | None = None
    created_at: datetime


class IntegrityIssue(Schema):
    severity: Literal["error", "warning"]
    entity: str
    entity_id: str | None = None
    message: str


class AdminStats(Schema):
    users: int
    active_users: int
    blocked_users: int
    ingredients: int
    allergens: int
    categories: int
    recipes: int
    data_errors: int
    data_warnings: int
    failed_logins_7d: int = Field(alias="failedLogins7d")
    last_backup: datetime | None = None


class BackupInfo(Schema):
    file_name: str
    size_bytes: int
    created_at: datetime


class BackupRestoreRequest(Schema):
    file_name: str = Field(min_length=1, max_length=255)


class TaskAccepted(Schema):
    status: str
    message: str
    file_name: str | None = None
