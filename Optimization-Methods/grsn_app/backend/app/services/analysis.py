"""Модуль анализа и прогнозирования (ТЗ 4.1.1): соответствие рациона цели, тренд веса, рекомендации."""

from datetime import date, datetime, time, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import schemas
from app.models import ParameterHistory, RecipeRating, User, UserRestriction, as_utc
from app.services import nutrition
from app.services.profile import daily_targets, energy_for, get_profile
from app.services.reports import build_report, local_date, tz
from app.services.restrictions import check_ingredients, load_forbidden

MIN_TREND_SPAN_DAYS = 3  # фактическая динамика веса считается по замерам минимум за 3 дня
MIN_TREND_DAYS = 3  # расчётный тренд и прогноз — только если рецепты в рационе есть минимум за 3 дня
PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}
KEYS = ("calories", "protein", "fat", "carbs")


def _linear_slope(points: list[tuple[float, float]]) -> float | None:
    """Наклон линейной регрессии y = a + b·x методом наименьших квадратов."""
    if len(points) < 2:
        return None
    n = len(points)
    mx = sum(p[0] for p in points) / n
    my = sum(p[1] for p in points) / n
    sxx = sum((p[0] - mx) ** 2 for p in points)
    if sxx == 0:
        return None
    return sum((p[0] - mx) * (p[1] - my) for p in points) / sxx


def analyze(db: Session, user: User, date_from: date, date_to: date) -> schemas.NutritionAnalysis:
    profile = get_profile(db, user.user_id)
    if profile is None or profile.goal is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Для анализа заполните профиль и выберите фитнес-ориентир")
    goal = profile.goal
    data = build_report(db, user, date_from, date_to)
    report, recipes = data.out, data.recipes
    energy = energy_for(profile, goal)
    target = daily_targets(energy.target, goal)

    n_days = report.days_with_data
    totals = {"calories": report.total_calories, "protein": report.total_protein, "fat": report.total_fat, "carbs": report.total_carbs}
    actual = {k: round(totals[k] / n_days, 1) if n_days else 0.0 for k in KEYS}
    deviation = {k: round(actual[k] - target[k], 1) for k in KEYS}
    deviation_pct = {k: round(deviation[k] / target[k] * 100, 1) if target[k] and n_days else 0.0 for k in KEYS}

    # --- Динамика веса ---
    period_start = datetime.combine(date_from, time.min, tzinfo=tz()).astimezone(timezone.utc)
    period_end = datetime.combine(date_to + timedelta(days=1), time.min, tzinfo=tz()).astimezone(timezone.utc)
    history = list(db.scalars(select(ParameterHistory).where(ParameterHistory.user_id == user.user_id).order_by(ParameterHistory.recorded_at)))
    before = [h for h in history if as_utc(h.recorded_at) < period_start]
    inside = [h for h in history if period_start <= as_utc(h.recorded_at) < period_end]

    # Один замер на день (последний): несколько замеров за минуты не должны давать «тренд» в тысячи кг/нед
    per_day: dict[date, float] = {}
    for h in ([before[-1]] if before else []) + inside:
        per_day[local_date(h.recorded_at)] = h.weight_kg
    # Начало расчётной линии — первый замер периода, чтобы линия и точки замеров начинались с одного значения
    start_weight = per_day[min(per_day)] if per_day else profile.weight_kg

    # Расчётный тренд: вес += (съедено − TDEE) / 7700 по дням, для которых есть рецепты в рационе.
    # Дни без данных считаются нейтральными (вес не меняется) — они не «досчитываются» средним.
    trend_sufficient = n_days >= MIN_TREND_DAYS
    trend: list[schemas.WeightPoint] = []
    end_weight = weight_change = forecast_30 = None
    if trend_sufficient:
        weight = start_weight
        for i, day in enumerate(report.daily_calories, start=1):
            if day.recipes:
                weight += (day.calories - energy.tdee) / nutrition.KCAL_PER_KG_BODY_WEIGHT
            trend.append(schemas.WeightPoint(day=i, date=day.date, weight_kg=round(weight, 2)))
        end_weight = trend[-1].weight_kg
        weight_change = round(end_weight - start_weight, 2)
        forecast_30 = round(end_weight + 30 * (actual["calories"] - energy.tdee) / nutrition.KCAL_PER_KG_BODY_WEIGHT, 2)
    measured = [
        schemas.WeightPoint(day=(d - date_from).days + 1, date=d, weight_kg=w) for d, w in sorted(per_day.items())
    ]
    measured_trend = None
    if len(per_day) >= 2 and (max(per_day) - min(per_day)).days >= MIN_TREND_SPAN_DAYS:
        slope = _linear_slope([((d - date_from).days, w) for d, w in per_day.items()])
        measured_trend = round(slope * 7, 2) if slope is not None else None

    # --- Запреты и оценки ---
    forbidden = load_forbidden(db, user.user_id)
    violations = sum(1 for r in recipes if not check_ingredients([i.ingredient for i in r.items], forbidden)[0])
    restrictions_count = db.query(UserRestriction).filter(UserRestriction.user_id == user.user_id).count()
    recipe_ids = [r.recipe_id for r in recipes]
    scores = list(db.scalars(select(RecipeRating.score).where(RecipeRating.user_id == user.user_id, RecipeRating.recipe_id.in_(recipe_ids)))) if recipe_ids else []
    avg_rating = round(sum(scores) / len(scores), 2) if scores else None

    compliance = 0.0
    if n_days:
        penalty = 0.5 * abs(deviation_pct["calories"]) + 0.2 * abs(deviation_pct["protein"]) + 0.15 * abs(deviation_pct["fat"]) + 0.15 * abs(deviation_pct["carbs"])
        compliance = round(max(0.0, 100 - penalty), 1)

    recs = _recommendations(goal.code, n_days, deviation_pct, weight_change or 0.0, measured_trend, violations, avg_rating, restrictions_count)

    return schemas.NutritionAnalysis(
        date_from=date_from,
        date_to=date_to,
        goal_name=goal.name,
        target_calories_day=energy.target,
        target=schemas.NutritionTotals(**target),
        actual=schemas.NutritionTotals(**actual),
        deviation=schemas.NutritionTotals(**deviation),
        deviation_percent=schemas.NutritionTotals(**deviation_pct),
        recipes_analyzed=len(recipes),
        days_with_data=n_days,
        restrictions_count=restrictions_count,
        violations_found=violations,
        average_rating=avg_rating,
        ratings_count=len(scores),
        compliance_score=compliance,
        start_weight_kg=round(start_weight, 2),
        end_weight_kg=end_weight,
        weight_change_kg=weight_change,
        forecast_weight_30d_kg=forecast_30,
        trend_sufficient=trend_sufficient,
        measured_trend_kg_per_week=measured_trend,
        calculated_weight_trend=trend,
        measured_weights=measured,
        recommendations=recs,
    )


def _recommendations(
    goal_code: str,
    n_days: int,
    dev: dict,
    weight_change: float,
    measured_trend: float | None,
    violations: int,
    avg_rating: float | None,
    restrictions_count: int,
) -> list[schemas.AnalysisRecommendation]:
    R = schemas.AnalysisRecommendation
    out: list[R] = []
    if not n_days:
        return [R(priority="high", text="Добавьте рецепты в рацион за выбранный период",
                  reason="За период нет рецептов, включённых в рацион, — фактическое питание оценить невозможно.")]

    cal = dev["calories"]
    if cal < -10:
        out.append(R(priority="high" if goal_code in ("goal_gain", "goal_endurance", "goal_maintain") else "medium",
                     text="Добавить более калорийные разрешённые ингредиенты или увеличить порции",
                     reason=f"Средняя калорийность рациона ниже целевого значения на {abs(cal):.0f} %."))
    elif cal > 10:
        out.append(R(priority="high" if goal_code in ("goal_loss", "goal_maintain") else "medium",
                     text="Уменьшить порции или выбрать менее калорийные ингредиенты",
                     reason=f"Средняя калорийность рациона выше целевого значения на {cal:.0f} %."))
    elif abs(cal) > 5:
        out.append(R(priority="low", text="Слегка скорректировать размер порций",
                     reason=f"Калорийность отличается от цели на {cal:+.0f} % (в пределах допуска 10 %)."))

    if dev["protein"] < -10:
        out.append(R(priority="high" if goal_code == "goal_gain" else "medium",
                     text="Увеличить долю белковых продуктов",
                     reason=f"Белка в рационе на {abs(dev['protein']):.0f} % меньше целевой нормы."))
    if abs(dev["carbs"]) > 15:
        more = dev["carbs"] < 0
        out.append(R(priority="high" if goal_code == "goal_endurance" and more else "medium",
                     text="Скорректировать порцию сложных углеводов" + (" (увеличить)" if more else " (уменьшить)"),
                     reason=f"Отклонение углеводов {dev['carbs']:+.0f} % относительно выбранной цели."))
    if dev["fat"] > 15:
        out.append(R(priority="medium", text="Снизить долю жиров: меньше масла, орехов и жирных сортов",
                     reason=f"Жиров в рационе на {dev['fat']:.0f} % больше нормы."))

    trend = measured_trend if measured_trend is not None else weight_change
    basis = "по фактическим замерам" if measured_trend is not None else "по калорийности рецептов"
    if goal_code == "goal_loss" and trend > 0.05:
        out.append(R(priority="high", text="Тренд веса не соответствует цели снижения веса",
                     reason=f"Вес растёт {basis} ({trend:+.2f} кг) — нужен дефицит калорий."))
    if goal_code == "goal_gain" and trend < -0.05:
        out.append(R(priority="high", text="Тренд веса не соответствует цели набора массы",
                     reason=f"Вес снижается {basis} ({trend:+.2f} кг) — нужен профицит калорий."))

    if avg_rating is not None and avg_rating < 3.5:
        out.append(R(priority="medium", text="Уточнить пожелания или набор ингредиентов при генерации",
                     reason=f"Средняя оценка рецептов за период {avg_rating:.1f} из 5."))

    if violations:
        out.append(R(priority="high", text="Исключить из рациона рецепты с запрещёнными ингредиентами",
                     reason=f"Найдено рецептов, нарушающих текущие запреты: {violations}."))
    elif restrictions_count:
        out.append(R(priority="low", text="Сохранить текущий контроль аллергенов",
                     reason="При анализе не выявлены запрещённые ингредиенты."))

    if not out:
        out.append(R(priority="low", text="Рацион соответствует цели — продолжайте в том же режиме",
                     reason="Отклонения калорийности и БЖУ в пределах допуска."))
    return sorted(out, key=lambda r: PRIORITY_ORDER[r.priority])
