"""Мониторинг корректности и целостности справочных данных (модуль администрирования)."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import schemas
from app.models import Allergen, Ingredient, IngredientAllergen, IngredientCategory, UserRestriction
from app.services.nutrition import KCAL_PER_G_CARB, KCAL_PER_G_FAT, KCAL_PER_G_PROTEIN

ATWATER_TOLERANCE = 0.2


def check_integrity(db: Session) -> list[schemas.IntegrityIssue]:
    issues: list[schemas.IntegrityIssue] = []
    I = schemas.IntegrityIssue

    for ing in db.scalars(select(Ingredient)):
        if ing.category_id is None:
            issues.append(I(severity="warning", entity="ingredients", entity_id=str(ing.ingredient_id),
                            message=f"«{ing.name}»: не указана категория"))
        macro_sum = ing.protein_per_100g + ing.fat_per_100g + ing.carb_per_100g
        if macro_sum > 100:
            issues.append(I(severity="error", entity="ingredients", entity_id=str(ing.ingredient_id),
                            message=f"«{ing.name}»: сумма БЖУ {macro_sum:.1f} г превышает 100 г"))
        atwater = KCAL_PER_G_PROTEIN * ing.protein_per_100g + KCAL_PER_G_FAT * ing.fat_per_100g + KCAL_PER_G_CARB * ing.carb_per_100g
        if ing.calories_per_100g > 0 and abs(atwater - ing.calories_per_100g) / ing.calories_per_100g > ATWATER_TOLERANCE:
            issues.append(I(severity="warning", entity="ingredients", entity_id=str(ing.ingredient_id),
                            message=f"«{ing.name}»: калорийность {ing.calories_per_100g:.0f} ккал расходится с расчётом по Атуотеру ({atwater:.0f} ккал)"))
        if ing.is_composite and not ing.components:
            issues.append(I(severity="error", entity="ingredients", entity_id=str(ing.ingredient_id),
                            message=f"«{ing.name}»: отмечен как составной, но состав не задан"))
        if not ing.is_composite and ing.components:
            issues.append(I(severity="warning", entity="ingredients", entity_id=str(ing.ingredient_id),
                            message=f"«{ing.name}»: задан состав, но продукт не отмечен как составной"))

    for cat in db.scalars(select(IngredientCategory)):
        if not db.scalar(select(Ingredient.ingredient_id).where(Ingredient.category_id == cat.category_id).limit(1)):
            issues.append(I(severity="warning", entity="ingredient_categories", entity_id=str(cat.category_id),
                            message=f"Категория «{cat.name}» не содержит ингредиентов"))

    linked = set(db.scalars(select(IngredientAllergen.allergen_id).distinct()))
    for allergen in db.scalars(select(Allergen)):
        if allergen.allergen_id not in linked:
            issues.append(I(severity="warning", entity="allergens", entity_id=str(allergen.allergen_id),
                            message=f"Аллерген «{allergen.name}» не привязан ни к одному ингредиенту"))

    orphan = db.scalar(
        select(UserRestriction.restriction_id).where(
            UserRestriction.restriction_type != "substance",
            UserRestriction.ingredient_id.is_(None),
            UserRestriction.allergen_id.is_(None),
        ).limit(1)
    )
    if orphan:
        issues.append(I(severity="error", entity="user_restrictions", entity_id=str(orphan),
                        message="Есть запреты пользователей без ссылки на справочник"))
    return issues
