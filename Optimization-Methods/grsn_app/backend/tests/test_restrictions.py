"""Нормализация запретов и правило проверки ТЗ 4.7.2."""

from sqlalchemy import select

from app.models import Allergen, Ingredient
from app.services.restrictions import ForbiddenSet, check_ingredient, find_matches, normalize_text, resolve_unique


def test_normalize_text():
    assert normalize_text("  АРАХИСА!!  ") == "арахиса"
    assert normalize_text("Сёмга,   копчёная") == "семга копченая"


def test_synonym_and_wordform_matching(db):
    matches = find_matches(db, "овсянка")
    assert matches and matches[0].name == "Овсяные хлопья"
    assert resolve_unique(matches).type == "ingredient"
    # словоформа: «арахиса» -> и ингредиент, и аллерген «Арахис» — неоднозначно
    ambiguous = find_matches(db, "арахиса")
    assert {m.type for m in ambiguous if m.score >= 2} == {"ingredient", "allergen"}
    assert resolve_unique(ambiguous) is None


def test_rule_ingredient_allergen_and_composite(db):
    granola = db.scalar(select(Ingredient).where(Ingredient.code == "ing_granola"))
    almond = db.scalar(select(Ingredient).where(Ingredient.code == "ing_almond"))
    nuts = db.scalar(select(Allergen).where(Allergen.code == "allergen_nuts"))
    gluten = db.scalar(select(Allergen).where(Allergen.code == "allergen_gluten"))

    assert check_ingredient(granola, ForbiddenSet()) == []
    # 1) совпадение по ID
    assert check_ingredient(almond, ForbiddenSet(ingredient_ids={almond.ingredient_id: "Миндаль"}))
    # 2) аллерген у самого ингредиента
    assert check_ingredient(almond, ForbiddenSet(allergen_ids={nuts.allergen_id: "Орехи"}))
    # 3) составной продукт: аллерген найден в компонентах (овсяные хлопья -> глютен)
    reasons = check_ingredient(granola, ForbiddenSet(allergen_ids={gluten.allergen_id: "Глютен"}))
    assert reasons and "компонент «Овсяные хлопья»" in reasons[0]
    # запрет компонента по ID тоже делает составной продукт недопустимым
    assert check_ingredient(granola, ForbiddenSet(ingredient_ids={almond.ingredient_id: "Миндаль"}))
    # свободное вещество по описанию состава
    assert check_ingredient(granola, ForbiddenSet(substances=["финики"]))


def test_text_mentions_handles_word_forms():
    from app.services.restrictions import text_mentions

    terms = ["творог", "молоко", "греческий йогурт", "арахис"]
    assert text_mentions("Подаём творожную массу с бананом", terms) == ["творог"]
    assert text_mentions("Добавьте молочные продукты по вкусу", terms) == ["молоко"]
    assert text_mentions("Полейте греческим йогуртом", terms) == ["греческий йогурт"]
    assert text_mentions("Посыпьте арахисом", terms) == ["арахис"]
    assert text_mentions("Отварите гречку и нарежьте банан", terms) == []

