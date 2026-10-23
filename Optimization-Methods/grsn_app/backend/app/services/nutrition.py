"""Математическая модель расчёта пищевой ценности (ТЗ, раздел 4.6)."""

from dataclasses import dataclass

ACTIVITY_LEVELS: dict[float, str] = {
    1.2: "Сидячий образ жизни, отсутствие тренировок",
    1.375: "Лёгкая активность, тренировки 1–3 раза в неделю",
    1.55: "Средняя активность, тренировки 3–5 раз в неделю",
    1.725: "Высокая активность, тренировки 6–7 раз в неделю",
    1.9: "Экстремальная активность, тяжёлые физические нагрузки",
}

KCAL_PER_G_PROTEIN = 4
KCAL_PER_G_FAT = 9
KCAL_PER_G_CARB = 4
KCAL_PER_KG_BODY_WEIGHT = 7700  # энергетический эквивалент 1 кг массы тела


def bmr(sex: str, weight_kg: float, height_cm: float, age: int) -> float:
    """Основной обмен по формуле Харриса–Бенедикта."""
    if sex == "male":
        return 88.362 + 13.397 * weight_kg + 4.799 * height_cm - 5.677 * age
    return 447.593 + 9.247 * weight_kg + 3.098 * height_cm - 4.330 * age


def tdee(bmr_value: float, activity_k: float) -> float:
    """Суточная энергетическая потребность: TDEE = BMR · k."""
    return bmr_value * activity_k


def target_calories(tdee_value: float, delta: float) -> float:
    """Целевая потребность: E_target = TDEE + Δ."""
    return tdee_value + delta


@dataclass(frozen=True)
class NutrientRow:
    """Ингредиент рецепта: масса m_i и пищевая ценность на 100 г."""

    mass_g: float
    protein: float
    fat: float
    carbs: float
    calories: float


@dataclass(frozen=True)
class Totals:
    protein: float
    fat: float
    carbs: float
    calories: float  # по формуле E_total = Σ m_i·E_i / 100
    calories_by_macros: float  # E_total = 4·P + 9·F + 4·C

    def as_dict(self) -> dict:
        return {
            "protein": round(self.protein, 1),
            "fat": round(self.fat, 1),
            "carbs": round(self.carbs, 1),
            "calories": round(self.calories, 1),
        }


def recipe_totals(rows: list[NutrientRow]) -> Totals:
    p = sum(r.mass_g * r.protein / 100 for r in rows)
    f = sum(r.mass_g * r.fat / 100 for r in rows)
    c = sum(r.mass_g * r.carbs / 100 for r in rows)
    e = sum(r.mass_g * r.calories / 100 for r in rows)
    e_macro = KCAL_PER_G_PROTEIN * p + KCAL_PER_G_FAT * f + KCAL_PER_G_CARB * c
    return Totals(p, f, c, e, e_macro)


def deviation(e_total: float, meal_share: float, e_target: float) -> float:
    """Отклонение калорийности рецепта от целевой для приёма пищи: δ = E_total − w·E_target."""
    return e_total - meal_share * e_target


def macro_percent(protein: float, fat: float, carbs: float, e_total: float) -> dict[str, float]:
    """Доли макронутриентов в процентах от общей калорийности."""
    if e_total <= 0:
        return {"protein": 0.0, "fat": 0.0, "carbs": 0.0}
    return {
        "protein": round(KCAL_PER_G_PROTEIN * protein / e_total * 100, 1),
        "fat": round(KCAL_PER_G_FAT * fat / e_total * 100, 1),
        "carbs": round(KCAL_PER_G_CARB * carbs / e_total * 100, 1),
    }


def macro_targets_g(calories: float, protein_pct: float, fat_pct: float, carb_pct: float) -> dict[str, float]:
    """Целевые граммы БЖУ для заданной калорийности и долей цели."""
    return {
        "calories": round(calories, 1),
        "protein": round(calories * protein_pct / 100 / KCAL_PER_G_PROTEIN, 1),
        "fat": round(calories * fat_pct / 100 / KCAL_PER_G_FAT, 1),
        "carbs": round(calories * carb_pct / 100 / KCAL_PER_G_CARB, 1),
    }


@dataclass(frozen=True)
class EnergyProfile:
    bmr: float
    tdee: float
    target: float


def energy_profile(sex: str, weight_kg: float, height_cm: float, age: int, activity_k: float, delta: float) -> EnergyProfile:
    b = bmr(sex, weight_kg, height_cm, age)
    t = tdee(b, activity_k)
    return EnergyProfile(round(b, 1), round(t, 1), round(target_calories(t, delta), 1))
