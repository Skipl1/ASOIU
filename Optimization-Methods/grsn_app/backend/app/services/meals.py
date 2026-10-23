"""Приём пищи (завтрак / обед / ужин / перекус): отбор подходящих продуктов и условия для модели генерации.

Отдельного поля в БД нет: приём пищи записывается в начало комментария запроса генерации
(«Приём пищи: завтрак. …») и восстанавливается из него при показе рецепта.
"""

from app.models import Ingredient

MEAL_TYPES = {"breakfast": "завтрак", "lunch": "обед", "dinner": "ужин", "snack": "перекус"}
MEAL_GENITIVE = {"breakfast": "завтрака", "lunch": "обеда", "dinner": "ужина", "snack": "перекуса"}
MEAL_PREFIX = "Приём пищи: "

# Минимум подходящих продуктов, чтобы ограничить набор для модели; иначе используется весь набор
MIN_SUITABLE = {"breakfast": 3, "snack": 2}

PROMPT_RULES = {
    "breakfast": "Приём пищи — ЗАВТРАК. Блюдо должно быть типичным для завтрака: каша, омлет или яйца, творог, йогурт, "
                 "тосты, фрукты. Никаких мясных и рыбных горячих блюд с гарниром и супов. Время готовки — не более 20 минут.",
    "lunch": "Приём пищи — ОБЕД. Полноценное горячее блюдо: белковая часть, гарнир и овощи.",
    "dinner": "Приём пищи — УЖИН. Горячее блюдо из белковой части и овощей, гарнира умеренно, без сладкого.",
    "snack": "Приём пищи — ПЕРЕКУС. Простое блюдо без сложной готовки (не более 10 минут), которое удобно взять с собой: "
             "фрукты, орехи, йогурт, творог, хлебцы, яйца, свежие овощи.",
}


def comment_with_meal(meal_type: str | None, comment: str | None) -> str | None:
    if not meal_type:
        return comment
    head = MEAL_PREFIX + MEAL_TYPES[meal_type]
    return f"{head}. {comment}" if comment else head


def meal_from_comment(comment: str | None) -> str | None:
    if not comment or not comment.startswith(MEAL_PREFIX):
        return None
    label = comment[len(MEAL_PREFIX):].split(".", 1)[0].strip()
    return next((code for code, name in MEAL_TYPES.items() if name == label), None)


def _has(name: str, *keys: str) -> bool:
    n = name.lower()
    return any(k in n for k in keys)


def suits_meal(ingredient: Ingredient, meal_type: str | None) -> bool:
    """Подходит ли продукт для приёма пищи. Для обеда и ужина подходит всё."""
    if meal_type not in ("breakfast", "snack"):
        return True
    name = ingredient.name
    cat = ingredient.category.code if ingredient.category else None
    if meal_type == "breakfast":
        if cat in ("cat_dairy", "cat_fruits", "cat_nuts"):
            return True
        if cat == "cat_grains":
            return not _has(name, "макарон", "булгур")
        if cat == "cat_vegetables":
            return not _has(name, "картоф", "батат", "тыкв", "фасоль", "лук")
        if cat == "cat_protein":
            return _has(name, "яйц", "яичн", "протеин", "тофу", "хумус", "батончик")
        return False
    # перекус
    if cat in ("cat_dairy", "cat_fruits"):
        return True
    if cat == "cat_nuts":
        return not _has(name, "масло")
    if cat == "cat_grains":
        return _has(name, "хлеб", "гранола", "хлопь")
    if cat == "cat_vegetables":
        return _has(name, "огур", "помидор", "перец", "морков")
    if cat == "cat_protein":
        return _has(name, "яйц", "протеин", "хумус", "батончик", "тофу")
    return False
