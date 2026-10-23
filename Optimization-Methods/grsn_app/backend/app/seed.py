"""Начальное наполнение НСИ (по «Шаблонам справочников и НСИ» ТП), администратор и демо-пользователь.

Запуск: python -m app.seed   (идемпотентно — повторный запуск обновляет справочники по кодам).
"""

import logging
import random
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import SessionLocal
from app.models import (
    RECIPE_ACCEPTED,
    Allergen,
    AvailableIngredient,
    FitnessGoal,
    Ingredient,
    IngredientCategory,
    ParameterHistory,
    Recipe,
    RecipeRating,
    User,
    UserProfile,
    UserRestriction,
    utcnow,
)
from app.security import hash_password
from app.services.llm import MockProvider
from app.services.restrictions import normalize_text

logger = logging.getLogger("grsn.seed")

GOALS = [
    # code, name, Δ, description, calc_rule, P%, F%, C%
    ("goal_loss", "Снижение веса", -500, "Уменьшение массы тела за счёт контроля калорийности",
     "Умеренный дефицит калорий относительно TDEE (−500 ккал) и повышенная доля белка", 30, 25, 45),
    ("goal_gain", "Набор мышечной массы", 300, "Увеличение мышечной массы при достатке белка и энергии",
     "Повышенная калорийность (+300 ккал) и достаточное количество белка", 25, 25, 50),
    ("goal_maintain", "Поддержание формы", 0, "Сохранение текущих параметров пользователя",
     "Калорийность около расчётной нормы TDEE", 20, 30, 50),
    ("goal_endurance", "Повышение выносливости", 200, "Поддержка продолжительных тренировок",
     "Умеренная прибавка энергии (+200 ккал) и увеличенная доля сложных углеводов", 15, 25, 60),
]

CATEGORIES = [
    ("cat_protein", "Белковые продукты", "Мясо, птица, рыба, яйца и другие источники белка"),
    ("cat_grains", "Крупы и зерновые", "Крупы, макаронные изделия, хлебцы, злаки"),
    ("cat_vegetables", "Овощи", "Свежие, тушёные и замороженные овощи"),
    ("cat_fruits", "Фрукты и ягоды", "Фрукты, ягоды, сухофрукты"),
    ("cat_dairy", "Молочные продукты", "Молоко, творог, йогурт, сыр"),
    ("cat_nuts", "Орехи и семена", "Орехи, семена, пасты, масла"),
]

ALLERGENS = [
    ("allergen_gluten", "Глютен", "Белки злаковых культур (пшеница, рожь, ячмень, овёс)",
     ["клейковина", "пшеница", "рожь", "ячмень", "злаки"]),
    ("allergen_lactose", "Лактоза / молочные компоненты", "Компоненты молочных продуктов",
     ["лактоза", "молоко", "молочные продукты", "молочка", "казеин", "молочный белок"]),
    ("allergen_nuts", "Орехи", "Орехи и продукты их переработки",
     ["орех", "миндаль", "фундук", "грецкий орех", "кешью", "фисташки"]),
    ("allergen_egg", "Яйцо", "Яичный белок и желток", ["яйца", "яичный белок", "желток", "куриное яйцо"]),
    ("allergen_fish", "Рыба", "Рыба и продукты её переработки", ["морская рыба", "рыбные продукты"]),
    ("allergen_soy", "Соя", "Соевые бобы и продукты на их основе", ["соевый белок", "соевый"]),
    ("allergen_peanut", "Арахис", "Арахис и продукты его переработки", ["земляной орех", "арахисовая паста", "арахисовое масло"]),
]

# code, category, name, P, F, C, kcal (на 100 г), allergens, synonyms
INGREDIENTS = [
    # Белковые продукты
    ("ing_chicken_breast", "cat_protein", "Куриная грудка", 23, 2, 0, 110, [], ["курица", "куриное филе"]),
    ("ing_turkey", "cat_protein", "Филе индейки", 21, 1.5, 0, 98, [], ["индейка"]),
    ("ing_beef_lean", "cat_protein", "Говядина постная", 20.2, 7, 0, 144, [], ["говядина", "телятина"]),
    ("ing_pork_tenderloin", "cat_protein", "Свиная вырезка", 19.4, 7.1, 0, 142, [], ["свинина"]),
    ("ing_egg", "cat_protein", "Яйцо куриное", 12.7, 11.5, 0.7, 157, ["allergen_egg"], ["яйцо", "яйца"]),
    ("ing_egg_white", "cat_protein", "Яичный белок", 11.1, 0.2, 0.7, 52, ["allergen_egg"], ["белок яйца"]),
    ("ing_salmon", "cat_protein", "Лосось", 20, 13.4, 0, 203, ["allergen_fish"], ["сёмга", "семга", "красная рыба"]),
    ("ing_tuna_canned", "cat_protein", "Тунец консервированный в собственном соку", 23.5, 0.7, 0, 101, ["allergen_fish"], ["тунец"]),
    ("ing_pollock", "cat_protein", "Минтай", 15.9, 0.9, 0, 72, ["allergen_fish"], ["белая рыба"]),
    ("ing_cod", "cat_protein", "Треска", 17.7, 0.7, 0, 78, ["allergen_fish"], []),
    ("ing_tofu", "cat_protein", "Тофу", 12, 5, 2, 101, ["allergen_soy"], ["соевый творог"]),
    ("ing_red_lentils", "cat_protein", "Чечевица красная", 24, 1.5, 48, 300, [], ["чечевица"]),
    ("ing_chickpeas", "cat_protein", "Нут", 19.3, 6, 60.7, 364, [], ["турецкий горох"]),
    ("ing_whey", "cat_protein", "Протеин сывороточный", 75, 5, 8, 377, ["allergen_lactose"], ["протеин", "сывороточный белок", "whey"]),
    # Крупы и зерновые
    ("ing_brown_rice", "cat_grains", "Бурый рис", 7, 2, 72, 350, [], ["коричневый рис"]),
    ("ing_white_rice", "cat_grains", "Рис белый", 6.7, 0.7, 78.9, 344, [], ["рис"]),
    ("ing_buckwheat", "cat_grains", "Гречка", 12.6, 3.3, 62.1, 313, [], ["гречневая крупа", "ядрица"]),
    ("ing_oatmeal", "cat_grains", "Овсяные хлопья", 12, 6, 60, 370, ["allergen_gluten"], ["овсянка", "геркулес"]),
    ("ing_quinoa", "cat_grains", "Киноа", 14.1, 6.1, 57.2, 368, [], ["кинва"]),
    ("ing_bulgur", "cat_grains", "Булгур", 12.3, 1.3, 57.6, 342, ["allergen_gluten"], []),
    ("ing_pasta", "cat_grains", "Макароны из твёрдых сортов", 13, 1.5, 71, 350, ["allergen_gluten"], ["паста", "спагетти", "макароны"]),
    ("ing_wholegrain_bread", "cat_grains", "Хлеб цельнозерновой", 13, 3.4, 41, 247, ["allergen_gluten"], ["хлеб"]),
    ("ing_rice_cakes", "cat_grains", "Хлебцы рисовые", 8, 2.8, 80, 381, [], ["хлебцы"]),
    # Овощи
    ("ing_broccoli", "cat_vegetables", "Брокколи", 3, 0.4, 5.2, 34, [], []),
    ("ing_spinach", "cat_vegetables", "Шпинат", 2.9, 0.3, 2, 23, [], []),
    ("ing_tomato", "cat_vegetables", "Помидор", 0.9, 0.2, 3.9, 18, [], ["томат", "помидоры"]),
    ("ing_cucumber", "cat_vegetables", "Огурец", 0.8, 0.1, 2.5, 14, [], ["огурцы"]),
    ("ing_bell_pepper", "cat_vegetables", "Перец болгарский", 1, 0.3, 6, 27, [], ["сладкий перец"]),
    ("ing_carrot", "cat_vegetables", "Морковь", 0.9, 0.2, 9.6, 41, [], []),
    ("ing_cauliflower", "cat_vegetables", "Цветная капуста", 2.5, 0.3, 4.2, 30, [], []),
    ("ing_zucchini", "cat_vegetables", "Кабачок", 1.2, 0.3, 3.1, 17, [], ["цукини"]),
    ("ing_green_beans", "cat_vegetables", "Фасоль стручковая", 2, 0.2, 3.6, 24, [], []),
    ("ing_onion", "cat_vegetables", "Лук репчатый", 1.1, 0.1, 9.3, 40, [], ["лук"]),
    ("ing_mushrooms", "cat_vegetables", "Шампиньоны", 4.3, 1, 0.1, 27, [], ["грибы"]),
    ("ing_pumpkin", "cat_vegetables", "Тыква", 1, 0.1, 4.4, 22, [], []),
    ("ing_potato", "cat_vegetables", "Картофель", 2, 0.4, 16.3, 77, [], ["картошка"]),
    ("ing_sweet_potato", "cat_vegetables", "Батат", 1.6, 0.1, 20.1, 86, [], ["сладкий картофель"]),
    # Фрукты и ягоды
    ("ing_banana", "cat_fruits", "Банан", 1, 0, 23, 96, [], ["бананы"]),
    ("ing_apple", "cat_fruits", "Яблоко", 0.3, 0.2, 13.8, 52, [], ["яблоки"]),
    ("ing_blueberry", "cat_fruits", "Черника", 0.7, 0.3, 14.5, 57, [], []),
    ("ing_strawberry", "cat_fruits", "Клубника", 0.7, 0.3, 7.7, 32, [], []),
    ("ing_orange", "cat_fruits", "Апельсин", 0.9, 0.1, 11.8, 47, [], []),
    ("ing_raisins", "cat_fruits", "Изюм", 3.1, 0.5, 79, 299, [], []),
    ("ing_dates", "cat_fruits", "Финики сушёные", 2.5, 0.4, 75, 282, [], ["финики"]),
    ("ing_avocado", "cat_fruits", "Авокадо", 2, 14.7, 8.5, 160, [], []),
    # Молочные продукты
    ("ing_cottage_cheese", "cat_dairy", "Творог", 16, 5, 3, 120, ["allergen_lactose"], ["творожный продукт"]),
    ("ing_milk", "cat_dairy", "Молоко 2,5 %", 2.9, 2.5, 4.8, 54, ["allergen_lactose"], ["молоко"]),
    ("ing_kefir", "cat_dairy", "Кефир 1 %", 3, 1, 4, 40, ["allergen_lactose"], ["кефир"]),
    ("ing_greek_yogurt", "cat_dairy", "Йогурт греческий 2 %", 10, 2, 3.6, 73, ["allergen_lactose"], ["греческий йогурт", "йогурт"]),
    ("ing_mozzarella", "cat_dairy", "Сыр моцарелла", 22.2, 22.4, 2.2, 300, ["allergen_lactose"], ["моцарелла"]),
    ("ing_hard_cheese", "cat_dairy", "Сыр твёрдый", 25, 27, 0, 343, ["allergen_lactose"], ["сыр"]),
    # Орехи и семена
    ("ing_peanut", "cat_nuts", "Арахис", 26, 49, 16, 567, ["allergen_nuts", "allergen_peanut"], ["земляной орех"]),
    ("ing_almond", "cat_nuts", "Миндаль", 21.2, 49.9, 21.6, 579, ["allergen_nuts"], []),
    ("ing_walnut", "cat_nuts", "Грецкий орех", 15.2, 65.2, 13.7, 654, ["allergen_nuts"], ["грецкие орехи"]),
    ("ing_peanut_butter", "cat_nuts", "Арахисовая паста", 25, 50, 20, 588, ["allergen_nuts", "allergen_peanut"], ["арахисовое масло"]),
    ("ing_chia", "cat_nuts", "Семена чиа", 16.5, 30.7, 42, 486, [], ["чиа"]),
    ("ing_flax", "cat_nuts", "Семена льна", 18.3, 42.2, 28.9, 534, [], ["льняное семя", "лён"]),
    ("ing_olive_oil", "cat_nuts", "Масло оливковое", 0, 99.8, 0, 898, [], ["оливковое масло"]),
]

# Составные продукты: аллергены определяются через компоненты (ТЗ 4.7.2, п. 3)
COMPOSITES = [
    ("ing_granola", "cat_grains", "Гранола с орехами", 9, 15, 62, 419,
     ["ing_oatmeal", "ing_almond", "ing_dates"], "Овсяные хлопья, миндаль, финики", ["гранола", "мюсли"]),
    ("ing_hummus", "cat_protein", "Хумус", 7.9, 9.6, 14.3, 177,
     ["ing_chickpeas", "ing_olive_oil"], "Нут, оливковое масло, специи", []),
    ("ing_protein_bar", "cat_protein", "Протеиновый батончик", 20, 12, 40, 348,
     ["ing_whey", "ing_oatmeal", "ing_peanut_butter"], "Сывороточный протеин, овсяные хлопья, арахисовая паста",
     ["батончик", "протеиновый бар"]),
]


def upsert_dictionaries(db: Session) -> None:
    for n, (code, name, delta, desc, rule, p, f, c) in enumerate(GOALS):
        goal = db.scalar(select(FitnessGoal).where(FitnessGoal.code == code)) or FitnessGoal(code=code)
        goal.name, goal.calorie_correction, goal.description, goal.calc_rule = name, delta, desc, rule
        goal.protein_pct, goal.fat_pct, goal.carb_pct, goal.sort_order = p, f, c, n
        db.add(goal)

    cats = {}
    for code, name, desc in CATEGORIES:
        cat = db.scalar(select(IngredientCategory).where(IngredientCategory.code == code)) or IngredientCategory(code=code)
        cat.name, cat.description = name, desc
        db.add(cat)
        cats[code] = cat

    allergens = {}
    for code, name, desc, synonyms in ALLERGENS:
        a = db.scalar(select(Allergen).where(Allergen.code == code)) or Allergen(code=code)
        a.name, a.description, a.synonyms = name, desc, synonyms
        db.add(a)
        allergens[code] = a
    db.flush()

    ingredients = {}
    for code, cat, name, p, f, c, kcal, alg, syn in INGREDIENTS:
        ing = db.scalar(select(Ingredient).where(Ingredient.code == code)) or Ingredient(code=code)
        ing.category_id = cats[cat].category_id
        ing.name, ing.protein_per_100g, ing.fat_per_100g, ing.carb_per_100g, ing.calories_per_100g = name, p, f, c, kcal
        ing.is_composite, ing.name_synonyms = False, syn
        ing.allergens = [allergens[a] for a in alg]
        db.add(ing)
        ingredients[code] = ing
    db.flush()
    for code, cat, name, p, f, c, kcal, components, composition, syn in COMPOSITES:
        ing = db.scalar(select(Ingredient).where(Ingredient.code == code)) or Ingredient(code=code)
        ing.category_id = cats[cat].category_id
        ing.name, ing.protein_per_100g, ing.fat_per_100g, ing.carb_per_100g, ing.calories_per_100g = name, p, f, c, kcal
        ing.is_composite, ing.name_synonyms, ing.composition_description = True, syn, composition
        ing.allergens = []
        ing.components = [ingredients[x] for x in components]
        db.add(ing)
    db.commit()


def ensure_admin(db: Session) -> User:
    s = get_settings()
    admin = db.scalar(select(User).where(User.email == s.admin_email.lower()))
    if admin is None:
        admin = User(name=s.admin_name, email=s.admin_email.lower(), password_hash=hash_password(s.admin_password), role="admin")
        db.add(admin)
        db.commit()
        logger.info("Создан администратор %s", admin.email)
    return admin


DEMO_EMAIL = "demo@grsn.local"
DEMO_PASSWORD = "Demo12345"


def ensure_demo(db: Session) -> None:
    """Демо-пользователь с профилем, запретами, набором ингредиентов и историей рецептов за неделю."""
    if db.scalar(select(User).where(User.email == DEMO_EMAIL)):
        return
    from app.services.generation import generate_recipes

    goals = {g.code: g for g in db.scalars(select(FitnessGoal))}
    ings = {i.code: i for i in db.scalars(select(Ingredient))}
    allergens = {a.code: a for a in db.scalars(select(Allergen))}

    user = User(name="Дмитрий (демо)", email=DEMO_EMAIL, password_hash=hash_password(DEMO_PASSWORD))
    db.add(user)
    db.flush()
    db.add(UserProfile(user_id=user.user_id, fitness_goal_id=goals["goal_gain"].fitness_goal_id,
                       weight_kg=78, height_cm=182, age=21, sex="male", activity_level=1.55))
    now = utcnow()
    for weeks_ago, weight in ((4, 76.4), (3, 76.9), (2, 77.3), (1, 77.6), (0, 78.0)):
        db.add(ParameterHistory(user_id=user.user_id, weight_kg=weight, height_cm=182, age=21, activity_level=1.55,
                                recorded_at=now - timedelta(days=7 * weeks_ago, hours=1)))
    lactose = allergens["allergen_lactose"]
    db.add(UserRestriction(user_id=user.user_id, allergen_id=lactose.allergen_id, original_name="Молочные продукты",
                           normalized_name=normalize_text("Молочные продукты"), restriction_type="allergen"))
    db.add(UserRestriction(user_id=user.user_id, ingredient_id=ings["ing_peanut"].ingredient_id, original_name="Арахис",
                           normalized_name="арахис", restriction_type="ingredient"))
    for code, qty in [("ing_chicken_breast", 1500), ("ing_brown_rice", 1000), ("ing_banana", 600), ("ing_buckwheat", 1000),
                      ("ing_oatmeal", 800), ("ing_broccoli", 800), ("ing_tomato", 600), ("ing_salmon", 600),
                      ("ing_egg", 600), ("ing_spinach", 300), ("ing_olive_oil", 250), ("ing_turkey", 1000),
                      ("ing_sweet_potato", 800), ("ing_blueberry", 300), ("ing_almond", 200), ("ing_bell_pepper", 500)]:
        db.add(AvailableIngredient(user_id=user.user_id, ingredient_id=ings[code].ingredient_id, available_amount_g=qty))
    db.commit()

    rng = random.Random(42)
    provider = MockProvider()
    for day in range(7, 0, -1):
        for meal, hour in ((0.3, 8), (0.4, 13), (0.3, 19)):
            outcome = generate_recipes(db, user, goals["goal_gain"].fitness_goal_id, 1, meal, None, None, provider=provider)
            for recipe in outcome.recipes:
                recipe.generation_status = RECIPE_ACCEPTED
                recipe.created_at = (now - timedelta(days=day)).replace(hour=hour - 3, minute=rng.randint(0, 50))
                if rng.random() < 0.7:
                    db.add(RecipeRating(user_id=user.user_id, recipe_id=recipe.recipe_id, score=rng.choice([3, 4, 4, 5, 5]),
                                        rated_at=recipe.created_at + timedelta(hours=1)))
            db.commit()
    logger.info("Создан демо-пользователь %s (%s рецептов)", DEMO_EMAIL,
                len(db.scalars(select(Recipe).where(Recipe.user_id == user.user_id)).all()))


def run() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    with SessionLocal() as db:
        upsert_dictionaries(db)
        ensure_admin(db)
        if get_settings().seed_demo:
            ensure_demo(db)
    logger.info("Начальное наполнение завершено")


if __name__ == "__main__":
    run()
