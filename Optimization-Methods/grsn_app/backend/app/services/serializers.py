"""Преобразование ORM-объектов в схемы API и общие проверки рецепта."""

import uuid

from app import schemas
from app.models import RECIPE_ACCEPTED, FitnessGoal, Ingredient, Recipe, User, UserRestriction
from app.services import nutrition
from app.services.meals import meal_from_comment
from app.services.restrictions import ForbiddenSet, check_ingredients, effective_allergens

MACRO_TOLERANCE_PP = 10  # допустимое отклонение доли макронутриента, процентные пункты
CALORIE_OK = 0.10  # |δ| / цель ≤ 10 % — в диапазоне
CALORIE_WARN = 0.20  # ≤ 20 % — предупреждение

MACRO_RU = {"protein": "белков", "fat": "жиров", "carbs": "углеводов"}


def user_out(user: User) -> schemas.UserOut:
    return schemas.UserOut(id=user.user_id, name=user.name, email=user.email, role=user.role, status=user.status)


def goal_out(goal: FitnessGoal) -> schemas.FitnessGoalOut:
    return schemas.FitnessGoalOut(
        id=goal.fitness_goal_id,
        code=goal.code,
        name=goal.name,
        calorie_delta=goal.calorie_correction,
        description=goal.description,
        calc_rule=goal.calc_rule,
        protein_pct=goal.protein_pct,
        fat_pct=goal.fat_pct,
        carb_pct=goal.carb_pct,
    )


def ingredient_out(ingredient: Ingredient, forbidden: ForbiddenSet | None = None) -> schemas.IngredientOut:
    is_allowed, reasons = (None, [])
    if forbidden is not None:
        is_allowed, reasons = check_ingredients([ingredient], forbidden)
    return schemas.IngredientOut(
        id=ingredient.ingredient_id,
        code=ingredient.code,
        name=ingredient.name,
        category_id=ingredient.category_id,
        category_name=ingredient.category.name if ingredient.category else None,
        protein100g=ingredient.protein_per_100g,
        fat100g=ingredient.fat_per_100g,
        carbs100g=ingredient.carb_per_100g,
        calories100g=ingredient.calories_per_100g,
        is_composite=ingredient.is_composite,
        synonyms=list(ingredient.name_synonyms or []),
        composition_description=ingredient.composition_description,
        allergen_ids=[a.allergen_id for a in ingredient.allergens],
        allergens=[schemas.AllergenShort(id=a.allergen_id, name=a.name) for a in ingredient.allergens],
        effective_allergens=[schemas.AllergenShort(id=a.allergen_id, name=a.name) for a in effective_allergens(ingredient)],
        components=[schemas.IngredientShort(id=c.ingredient_id, name=c.name) for c in ingredient.components],
        is_allowed=is_allowed,
        violation_reasons=reasons,
    )


def restriction_out(r: UserRestriction) -> schemas.UserRestrictionOut:
    target = r.ingredient.name if r.ingredient else r.allergen.name if r.allergen else None
    return schemas.UserRestrictionOut(
        id=r.restriction_id,
        source_text=r.original_name,
        normalized_name=r.normalized_name,
        type=r.restriction_type,
        ingredient_id=r.ingredient_id,
        allergen_id=r.allergen_id,
        target_name=target,
        created_at=r.created_at,
    )


def build_checks(
    macro_pct: dict,
    goal: FitnessGoal | None,
    calories: float,
    meal_target: float | None,
    allowed: bool,
    reasons: list[str],
) -> list[schemas.RecipeCheck]:
    checks: list[schemas.RecipeCheck] = []

    if goal is not None:
        targets = {"protein": goal.protein_pct, "fat": goal.fat_pct, "carbs": goal.carb_pct}
        diffs = {k: macro_pct[k] - targets[k] for k in targets}
        worst = max(diffs, key=lambda k: abs(diffs[k]))
        if abs(diffs[worst]) <= MACRO_TOLERANCE_PP:
            checks.append(schemas.RecipeCheck(
                indicator="БЖУ", status="ok", label="в норме",
                comment=f"Доли Б/Ж/У {macro_pct['protein']:.0f}/{macro_pct['fat']:.0f}/{macro_pct['carbs']:.0f} % "
                        f"соответствуют цели {targets['protein']:.0f}/{targets['fat']:.0f}/{targets['carbs']:.0f} %",
            ))
        else:
            checks.append(schemas.RecipeCheck(
                indicator="БЖУ", status="warn", label="отклонение",
                comment=f"Доля {MACRO_RU[worst]} {macro_pct[worst]:.0f} % при цели {targets[worst]:.0f} %",
            ))

    if meal_target:
        rel = (calories - meal_target) / meal_target
        status = "ok" if abs(rel) <= CALORIE_OK else "warn" if abs(rel) <= CALORIE_WARN else "bad"
        label = {"ok": "в диапазоне", "warn": "отклонение", "bad": "вне диапазона"}[status]
        checks.append(schemas.RecipeCheck(
            indicator="Калорийность", status=status, label=label,
            comment=f"{calories:.0f} ккал при цели {meal_target:.0f} ккал (δ = {calories - meal_target:+.0f} ккал, {rel * 100:+.0f} %)",
        ))

    if allowed:
        checks.append(schemas.RecipeCheck(
            indicator="Запреты", status="ok", label="не нарушены",
            comment="Запрещённые ингредиенты и аллергены не найдены",
        ))
    else:
        checks.append(schemas.RecipeCheck(indicator="Запреты", status="bad", label="нарушены", comment="; ".join(reasons)))
    return checks


def _current_violations(recipe: Recipe, forbidden: ForbiddenSet | None) -> tuple[bool, list[str]]:
    reasons = list(recipe.mismatch_reasons or [])
    allowed = recipe.matches_restrictions
    if forbidden is not None:
        ok_now, now_reasons = check_ingredients([i.ingredient for i in recipe.items], forbidden)
        if not ok_now:
            allowed = False
            reasons += [r for r in now_reasons if r not in reasons]
    return allowed, reasons


def _user_rating(recipe: Recipe, user_id: uuid.UUID):
    return next((r for r in recipe.ratings if r.user_id == user_id), None)


def recipe_summary(recipe: Recipe, user_id: uuid.UUID, forbidden: ForbiddenSet | None = None) -> schemas.RecipeSummary:
    allowed, _ = _current_violations(recipe, forbidden)
    rating = _user_rating(recipe, user_id)
    return schemas.RecipeSummary(
        id=recipe.recipe_id,
        name=recipe.name,
        goal_id=recipe.fitness_goal_id,
        goal_name=recipe.goal.name if recipe.goal else None,
        calories_total=recipe.calories_kcal,
        protein_total=recipe.protein_total_g,
        fat_total=recipe.fat_total_g,
        carbs_total=recipe.carb_total_g,
        is_allowed=allowed,
        created_at=recipe.created_at,
        rating=rating.score if rating else None,
        source=recipe.source,
        in_diet=recipe.generation_status == RECIPE_ACCEPTED,
        meal_type=meal_from_comment(recipe.generation_request.comment) if recipe.generation_request else None,
    )


def recipe_out(recipe: Recipe, user_id: uuid.UUID, forbidden: ForbiddenSet | None = None) -> schemas.RecipeOut:
    allowed, reasons = _current_violations(recipe, forbidden)
    rating = _user_rating(recipe, user_id)
    pct = nutrition.macro_percent(recipe.protein_total_g, recipe.fat_total_g, recipe.carb_total_g, recipe.calories_kcal)
    items = []
    for item in recipe.items:
        ing = item.ingredient
        k = item.mass_g / 100
        items.append(schemas.RecipeIngredientOut(
            ingredient_id=ing.ingredient_id,
            name=ing.name,
            category_name=ing.category.name if ing.category else None,
            mass_g=item.mass_g,
            position=item.list_order,
            protein=round(ing.protein_per_100g * k, 1),
            fat=round(ing.fat_per_100g * k, 1),
            carbs=round(ing.carb_per_100g * k, 1),
            calories=round(ing.calories_per_100g * k, 1),
        ))
    total_mass = sum(i.mass_g for i in recipe.items)
    deviation = recipe.calories_kcal - recipe.target_calories if recipe.target_calories else None
    summary = recipe_summary(recipe, user_id, forbidden)
    return schemas.RecipeOut(
        **summary.model_dump(),
        request_id=recipe.generation_request_id,
        servings=recipe.servings,
        serving_mass_g=round(total_mass / max(recipe.servings, 1), 1),
        instructions=list(recipe.cooking_instruction or []),
        ingredients=items,
        violation_reasons=reasons,
        cooking_time_min=recipe.cooking_time_min,
        difficulty=recipe.difficulty,
        tips=list(recipe.tips or []),
        meal_share=recipe.meal_share,
        target_calories=recipe.target_calories,
        deviation_kcal=round(deviation, 1) if deviation is not None else None,
        macro_percent=schemas.NutritionTotals(calories=recipe.calories_kcal, **pct),
        checks=build_checks(pct, recipe.goal, recipe.calories_kcal, recipe.target_calories, allowed, reasons),
        my_rating=schemas.RatingOut(
            id=rating.rating_id, recipe_id=rating.recipe_id, score=rating.score, comment=rating.comment, created_at=rating.rated_at
        ) if rating else None,
        updated_at=recipe.updated_at,
    )
