"""Генерация персонализированного рецепта (ТЗ 4.1.1, 4.7, 5.3, 5.4; ТП — To-Be, DFD и диаграмма последовательности генерации).

Порядок: контекст (профиль, цель, запреты, доступные ингредиенты, оценки) → модель генерации →
постпроверка (сопоставление с каталогом, пересчёт БЖУ по формулам 4.6, коррекция массы,
проверка запретов по правилу 4.7.2) → сохранение в generation_requests / recipes / recipe_ingredients.
"""

import logging
import random
import re
import time
import uuid
from dataclasses import dataclass, field

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import (
    AvailableIngredient,
    FitnessGoal,
    GenerationRequest,
    Ingredient,
    Recipe,
    RecipeIngredient,
    RecipeRating,
    User,
    utcnow,
)
from app.services import nutrition
from app.services.llm import GenerationContext, LLMError, LLMRecipe, MockProvider, get_primary_provider
from app.services.llm.base import ContextIngredient
from app.services.llm.mock_provider import solve_masses
from app.services.meals import MEAL_GENITIVE, MIN_SUITABLE, comment_with_meal, suits_meal
from app.services.profile import energy_for, get_profile
from app.services.restrictions import (
    ForbiddenSet,
    _match_score,
    check_ingredients,
    forbidden_terms,
    load_forbidden,
    normalize_text,
    text_mentions,
)

logger = logging.getLogger("grsn.generation")

MIN_ALLOWED_INGREDIENTS = 3
MIN_PROTEIN_SOURCE = 8.0  # г белка на 100 г
MAX_INGREDIENT_MASS = 1000.0
# Реалистичная масса ингредиента в одной порции при коррекции рецепта модели, г
CATEGORY_MASS_CAP = {"cat_vegetables": 300.0, "cat_fruits": 250.0, "cat_grains": 200.0, "cat_protein": 350.0,
                     "cat_dairy": 400.0, "cat_nuts": 40.0}
OIL_MASS_CAP = 30.0
DEFAULT_MASS_CAP = 300.0


def _mass_cap(ingredient: Ingredient) -> float:
    if "масло" in ingredient.name.lower():
        return OIL_MASS_CAP
    code = ingredient.category.code if ingredient.category else None
    return CATEGORY_MASS_CAP.get(code, DEFAULT_MASS_CAP)

STORAGE_STEP = ("Хранение: если готовите впрок, остудите блюдо, разложите по контейнерам и храните в холодильнике "
                "до 3 суток; разогревайте 2–3 минуты в микроволновой печи.")

SUGGESTIONS = [
    "Добавьте в набор доступных ингредиентов рекомендованные продукты",
    "Выберите другой набор доступных ингредиентов",
    "Измените фитнес-цель или долю суточной нормы",
]


@dataclass
class BuiltRecipe:
    name: str
    servings: int
    steps: list[str]
    items: list[tuple[Ingredient, float]]
    totals: nutrition.Totals
    cooking_time_min: int | None
    difficulty: str | None
    tips: list[str]


@dataclass
class GenerationOutcome:
    request: GenerationRequest
    recipes: list[Recipe] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)


def _round5(value: float) -> float:
    return max(5.0, round(value / 5) * 5)


def _recommend_missing(db: Session, forbidden: ForbiddenSet, have: set[uuid.UUID], need_protein: bool) -> list[str]:
    """Не менее трёх допустимых ингредиентов каталога, которых нет в наборе пользователя (ТЗ 5.4)."""
    catalog = db.scalars(select(Ingredient).order_by(Ingredient.name)).all()
    allowed = [i for i in catalog if i.ingredient_id not in have and check_ingredients([i], forbidden)[0]]

    def pick(pred, limit):
        return [i for i in allowed if pred(i)][:limit]

    chosen: list[Ingredient] = []
    if need_protein:
        chosen += sorted(pick(lambda i: i.protein_per_100g >= 18 and not i.is_composite, 20), key=lambda i: -i.protein_per_100g)[:2]
    chosen += pick(lambda i: i.category and i.category.code == "cat_grains" and not i.is_composite, 2)
    chosen += pick(lambda i: i.category and i.category.code == "cat_vegetables", 2)
    seen: set[uuid.UUID] = set()
    result = [i.name for i in chosen if not (i.ingredient_id in seen or seen.add(i.ingredient_id))]
    for i in allowed:
        if len(result) >= 3:
            break
        if i.name not in result:
            result.append(i.name)
    return result[:6]


_STEP_NUMBER = re.compile(r"^\s*(?:шаг\s*)?\d+\s*[.):-]\s*", re.IGNORECASE)


def _clean_text(text: str) -> str:
    """Убирает нумерацию («1.», «Шаг 2:»), которую модель иногда добавляет сама."""
    return _STEP_NUMBER.sub("", text.strip()).strip()


def _meaningful(text: str | None) -> bool:
    """Отбрасывает пустые строки и заглушки вроде «...», которые модель может скопировать из образца."""
    if not text:
        return False
    core = _clean_text(text).strip(" .…-—")
    return len(core) >= 8 and sum(ch.isalpha() for ch in core) >= 5


def _fat_share(ingredient: Ingredient) -> float:
    kcal = ingredient.calories_per_100g
    return ingredient.fat_per_100g * nutrition.KCAL_PER_G_FAT / kcal if kcal else 0.0


def _fat_source_step(ingredient: Ingredient, mass: float) -> str:
    name = ingredient.name.lower()
    if "масло" in name:
        return f"{ingredient.name} ({mass:.0f} г, около {max(1, round(mass / 5))} ч. л.): заправьте готовое блюдо перед подачей."
    if "авокадо" in name:
        return f"{ingredient.name} ({mass:.0f} г): разрежьте, удалите косточку, нарежьте ломтиками и добавьте перед подачей."
    return f"{ingredient.name} ({mass:.0f} г): обжарьте 2–3 минуты на сухой сковороде, измельчите и посыпьте блюдо перед подачей."


def _optimize_masses(
    order: list[Ingredient],
    masses: dict[uuid.UUID, float],
    code_map: dict[str, tuple[Ingredient, float | None]],
    meal_target: dict,
) -> tuple[dict[uuid.UUID, float], Ingredient | None]:
    """Коррекция масс рецепта модели: взвешенный МНК по калориям и БЖУ (метод проекции градиента).

    Массы, предложенные моделью, могут уменьшаться не более чем до 0,4 исходного значения и расти до доступного количества, но не выше реалистичной порции для категории продукта и не превышают доступное
    количество. Если модель не включила источник жиров, а доля жиров ниже цели, из набора пользователя
    добавляется источник жиров (масло, орехи, авокадо) с массой от 0 г.
    """
    available = {e[0].ingredient_id: e[1] for e in code_map.values()}
    items = list(order)
    lower, upper = [], []
    for ing in items:
        m = masses[ing.ingredient_id]
        limit = available.get(ing.ingredient_id) or MAX_INGREDIENT_MASS
        hi = min(limit, _mass_cap(ing))
        lower.append(min(max(5.0, 0.4 * m), hi) / 100)
        upper.append(hi / 100)

    totals = nutrition.recipe_totals([
        nutrition.NutrientRow(masses[i.ingredient_id], i.protein_per_100g, i.fat_per_100g, i.carb_per_100g, i.calories_per_100g)
        for i in items
    ])
    fat_goal = meal_target["fat"] * nutrition.KCAL_PER_G_FAT / meal_target["calories"]
    fat_now = totals.fat * nutrition.KCAL_PER_G_FAT / totals.calories if totals.calories else 0
    added = None
    if fat_now < fat_goal - 0.08 and not any(_fat_share(i) >= 0.6 for i in items):
        sources = [ing for ing, _ in code_map.values() if ing not in items and _fat_share(ing) >= 0.6]
        sources.sort(key=lambda i: ("масло" not in i.name.lower(), i.name))
        if sources:
            added = sources[0]
            items.append(added)
            lower.append(0.0)
            upper.append(min(available.get(added.ingredient_id) or 30.0, 30.0) / 100)

    columns = [(i.calories_per_100g, i.protein_per_100g, i.fat_per_100g, i.carb_per_100g) for i in items]
    solved = solve_masses(columns, meal_target, lower, upper, iterations=2000)
    result: dict[uuid.UUID, float] = {}
    for ing, mass, hi in zip(items, solved, upper):
        rounded = min(round(mass / 5) * 5, hi * 100)
        rounded = (rounded // 5) * 5
        if rounded >= 5:
            result[ing.ingredient_id] = float(rounded)
    if added is not None and added.ingredient_id not in result:
        added = None
    for ing in order:  # ингредиенты модели не удаляются из рецепта
        result.setdefault(ing.ingredient_id, 5.0)
    return result, added


def _resolve_item(item, code_map: dict, name_index: dict):
    """Ингредиент из ответа модели → запись набора пользователя: по коду, точному названию или близкому названию."""
    if item.code and (entry := code_map.get(item.code.strip().upper())):
        return entry
    key = normalize_text(item.name or "")
    if not key:
        return None
    if key in name_index:
        return name_index[key]
    scored = sorted(((max(_match_score(key, k), 0), k) for k in name_index), reverse=True)
    if scored and scored[0][0] >= 2 and (len(scored) == 1 or scored[1][0] < scored[0][0]):
        return name_index[scored[0][1]]
    return None


def _title_from_composition(items: list[tuple[Ingredient, float]]) -> str:
    """Название по фактическому составу: «Главный продукт с гарниром: …»."""
    body = [(i, m) for i, m in items if "масло" not in i.name.lower()] or items
    main = max(body, key=lambda x: x[0].protein_per_100g * x[1])[0]
    side = [i.name.lower() for i, _ in sorted(body, key=lambda x: -x[1]) if i is not main][:3]
    return main.name + (" с гарниром: " + ", ".join(side) if side else "")


_WITHOUT = re.compile(r"\bбез\s+\w+")
MAX_WISHED = 3
WISH_MASS = 50.0  # начальная масса продукта из пожеланий, если модель его не включила, г
# Продукты, которых нет в каталоге: пожелание на них учесть нельзя, а упоминание в названии или шагах — ошибка модели
EXTRA_FOODS = ["креветки", "кальмары", "мидии", "бекон", "пельмени", "пицца", "бургер", "шоколад", "конфеты", "мороженое",
               "майонез", "кетчуп", "сметана", "сливки", "сгущёнка", "печенье", "торт", "сухарики", "чипсы", "сало"]


def _label_terms(ingredient: Ingredient) -> list[str]:
    return [t for label in (ingredient.name, *(ingredient.name_synonyms or []))
            if (t := " ".join(w for w in normalize_text(label).split() if w.isalpha() and len(w) >= 3))]


def _wished_ingredients(
    comment: str | None, catalog: list[Ingredient], forbidden: ForbiddenSet, own_ids: set[uuid.UUID]
) -> tuple[list[Ingredient], list[str], list[str]]:
    """Продукты, названные в пожеланиях пользователя («хочу с колбасой»).

    Возвращает: продукты, которые есть в наборе пользователя (они обязательны в составе); названия продуктов,
    которых в наборе нет (рецепт составляется без них, модели запрещено их упоминать); пояснения для пользователя.
    Продукт после «без» не считается пожеланием. Если названию соответствует несколько продуктов («колбаса»),
    берётся тот, что есть в наборе."""
    if not comment:
        return [], [], []
    text = _WITHOUT.sub(" ", normalize_text(comment))
    groups: dict[str, list[Ingredient]] = {}
    for ing in catalog:
        for term in _label_terms(ing):
            if text_mentions(text, [term]):
                groups.setdefault(term, []).append(ing)
    wished: list[Ingredient] = []
    missing: list[str] = []
    notes: list[str] = []
    chosen: set[uuid.UUID] = set()
    for term, ings in sorted(groups.items(), key=lambda kv: (-len(kv[0].split()), kv[0])):
        if any(i.ingredient_id in chosen for i in ings):
            continue
        chosen.update(i.ingredient_id for i in ings)
        ok = [i for i in ings if check_ingredients([i], forbidden)[0]]
        if not ok:
            notes.append(f"Пожелание «{term}» не учтено: продукт запрещён вашими ограничениями")
            continue
        in_set = sorted((i for i in ok if i.ingredient_id in own_ids), key=lambda i: i.name)
        if in_set:
            wished.append(in_set[0])
        else:
            missing.append(term)
            notes.append(f"Продукта «{term}» нет в вашем наборе доступных ингредиентов — рецепт составлен без него. "
                         "Добавьте продукт на странице «Ингредиенты» и повторите генерацию.")
    for term in text_mentions(text, EXTRA_FOODS):
        missing.append(term)
        notes.append(f"Продукта «{term}» нет в каталоге — рецепт составлен без него (администратор может добавить продукт в каталог).")
    return wished[:MAX_WISHED], missing, notes


def _excluded_by_wish(comment: str | None, catalog: list[Ingredient]) -> tuple[set[uuid.UUID], list[str]]:
    """Продукты, которые пользователь исключил пожеланием («без колбасы»): их id и названия."""
    if not comment:
        return set(), []
    ids: set[uuid.UUID] = set()
    terms: list[str] = []
    for phrase in _WITHOUT.findall(normalize_text(comment)):
        word = phrase.split(None, 1)[1]
        for ing in catalog:
            for term in _label_terms(ing):
                if text_mentions(word, [term]):
                    ids.add(ing.ingredient_id)
                    if term not in terms:
                        terms.append(term)
    return ids, terms


def _foreign_terms(catalog: list[Ingredient], order: list[Ingredient]) -> list[str]:
    """Названия продуктов, которых нет в составе рецепта: их нельзя упоминать в названии и шагах.
    Термины, совпадающие с названиями продуктов состава («рис» при буром рисе), исключаются."""
    in_order = {i.ingredient_id for i in order}
    own = [t for i in order for t in _label_terms(i)]
    terms: set[str] = set(EXTRA_FOODS)
    for ing in catalog:
        if ing.ingredient_id in in_order or "масло" in ing.name.lower():
            continue
        terms.update(t for t in _label_terms(ing) if len(t) >= 4)
    return sorted(t for t in terms if not any(text_mentions(o, [t]) or text_mentions(t, [o]) for o in own))


def _wish_step(ingredient: Ingredient, mass: float) -> str:
    return (f"{ingredient.name} ({mass:.0f} г): нарежьте небольшими кусочками, при необходимости прогрейте 2–3 минуты "
            "на сковороде и добавьте в блюдо перед подачей.")


def _post_process(
    raw: LLMRecipe,
    code_map: dict[str, tuple[Ingredient, float | None]],
    meal_target: dict,
    warnings: list[str],
    optimize: bool = True,
    banned_terms: list[str] | None = None,
    name_index: dict | None = None,
    must_have: list[Ingredient] | None = None,
    catalog: list[Ingredient] | None = None,
) -> tuple[BuiltRecipe | None, str | None]:
    masses: dict[uuid.UUID, float] = {}
    order: list[Ingredient] = []
    unknown: list[str] = []
    name_index = name_index or {}
    for item in raw.ingredients:
        entry = _resolve_item(item, code_map, name_index)
        if entry is None:
            unknown.append(item.name or item.code or "?")
            continue
        ingredient, _ = entry
        if ingredient.ingredient_id not in masses:
            order.append(ingredient)
            masses[ingredient.ingredient_id] = 0.0
        masses[ingredient.ingredient_id] += item.massG
    if unknown:
        warnings.append(f"Модель указала ингредиенты вне доступного набора ({', '.join(unknown[:5])}) — они исключены")
    # Продукт из пожеланий обязан быть в составе: если модель его пропустила, он добавляется
    forced = [i for i in (must_have or []) if i.ingredient_id not in masses]
    for ingredient in forced:
        order.append(ingredient)
        masses[ingredient.ingredient_id] = WISH_MASS
    optimize = optimize or bool(forced)

    available = {e[0].ingredient_id: e[1] for e in code_map.values()}

    def clamp(ingredient_id: uuid.UUID, mass: float) -> float:
        limit = available.get(ingredient_id) or MAX_INGREDIENT_MASS
        return min(_round5(mass), max(5.0, limit))

    masses = {k: clamp(k, v) for k, v in masses.items()}
    if len(order) < 2:
        return None, f"«{raw.name}»: в составе меньше двух допустимых ингредиентов"
    if banned_terms and (hits := text_mentions(raw.name, banned_terms)):
        return None, f"«{raw.name}»: в названии запрещённый продукт ({', '.join(hits)}) — рецепт отклонён"
    steps = [_clean_text(s) for s in raw.steps if _meaningful(s)]
    # Модель может упомянуть запрещённый продукт в тексте шага, даже если его нет в составе
    mentioned: set[str] = set()
    if banned_terms:
        safe_steps = []
        for step in steps:
            hits = text_mentions(step, banned_terms)
            mentioned.update(hits)
            if not hits:
                safe_steps.append(step)
        if mentioned:
            warnings.append(f"Из инструкции «{raw.name}» удалены шаги с упоминанием запрещённых продуктов: {', '.join(sorted(mentioned))}")
        steps = safe_steps
    # Шаги не должны упоминать продукты набора, которых нет в составе рецепта (кроме масла и специй)
    foreign_terms = _foreign_terms(catalog or [i for i, _ in code_map.values()], order)
    foreign_dropped = [s for s in steps if text_mentions(s, foreign_terms)]
    if foreign_dropped:
        steps = [s for s in steps if s not in foreign_dropped]
        warnings.append(f"Из инструкции «{raw.name}» удалены шаги с продуктами, которых нет в составе: {len(foreign_dropped)}")
    if len(steps) < 3:
        return None, f"«{raw.name}»: инструкция содержит меньше трёх шагов"

    def totals_for(m: dict[uuid.UUID, float]) -> nutrition.Totals:
        return nutrition.recipe_totals([
            nutrition.NutrientRow(m[i.ingredient_id], i.protein_per_100g, i.fat_per_100g, i.carb_per_100g, i.calories_per_100g)
            for i in order
        ])

    totals = totals_for(masses)
    tips = [_clean_text(t) for t in raw.tips if _meaningful(t) and not (banned_terms and text_mentions(t, banned_terms))]
    if totals.calories <= 0:
        return None, f"«{raw.name}»: нулевая калорийность"
    if optimize:
        before = dict(masses)
        masses, added = _optimize_masses(order, masses, code_map, meal_target)
        if added is not None:
            order.append(added)
            steps.insert(max(len(steps) - 1, 0), _fat_source_step(added, masses[added.ingredient_id]))
            tips.append(f"Для баланса БЖУ добавлен источник жиров из вашего набора: «{added.name}»")
        for ingredient in forced:
            steps.insert(max(len(steps) - 1, 0), _wish_step(ingredient, masses[ingredient.ingredient_id]))
            tips.append(f"Продукт из вашего пожелания «{ingredient.name}» добавлен в рецепт автоматически")
        if any(abs(masses[k] - v) > max(10.0, 0.1 * v) for k, v in before.items()):
            tips.append("Массы ингредиентов оптимизированы под целевые калорийность и БЖУ приёма пищи")
        totals = totals_for(masses)
        # Модель не указывает массы в шагах: добавляем подготовку с точным составом и рекомендации по хранению
        composition = ", ".join(f"{i.name.lower()} — {masses[i.ingredient_id]:.0f} г" for i in order)
        steps.insert(0, f"Подготовка: отмерьте продукты по составу ({composition}), вымойте овощи и подготовьте посуду.")
        if not any("хран" in s.lower() for s in steps):
            steps.append(STORAGE_STEP)

    # Название должно соответствовать итоговому составу: упоминание продукта, которого нет в рецепте, — ошибка модели
    final_items = [(i, masses[i.ingredient_id]) for i in order]
    final_name = raw.name.strip()
    if text_mentions(final_name, foreign_terms):
        final_name = _title_from_composition(final_items)
        warnings.append(f"Название «{raw.name.strip()}» не соответствовало составу и заменено на «{final_name}»")
    return BuiltRecipe(
        name=final_name,
        servings=raw.servings,
        steps=steps,
        items=[(i, masses[i.ingredient_id]) for i in order],
        totals=totals,
        cooking_time_min=raw.cookingTimeMin,
        difficulty=raw.difficulty,
        tips=tips[:6],
    ), None


def _reject(db: Session, request: GenerationRequest, reason: str, conflicts: list[str], recommended: list[str], started: float) -> None:
    request.status = "rejected"
    request.rejection_reason = reason
    request.conflicts = conflicts
    request.recommended_ingredients = recommended
    request.completed_at = utcnow()
    request.duration_ms = int((time.perf_counter() - started) * 1000)
    db.commit()


def generate_recipes(
    db: Session,
    user: User,
    goal_id: uuid.UUID,
    variants: int,
    meal_share: float,
    difficulty: str | None,
    comment: str | None,
    provider=None,
    meal_type: str | None = None,
) -> GenerationOutcome:
    started = time.perf_counter()
    settings = get_settings()

    goal = db.get(FitnessGoal, goal_id)
    if goal is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Фитнес-ориентир не найден")
    profile = get_profile(db, user.user_id)
    if profile is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Заполните профиль: вес, рост, возраст, пол и уровень активности")

    energy = energy_for(profile, goal)
    meal_kcal = meal_share * energy.target
    meal_target = nutrition.macro_targets_g(meal_kcal, goal.protein_pct, goal.fat_pct, goal.carb_pct)

    request = GenerationRequest(
        user_id=user.user_id,
        fitness_goal_id=goal.fitness_goal_id,
        variant_count=variants,
        daily_norm_share=meal_share,
        difficulty=difficulty,
        comment=comment_with_meal(meal_type, comment),
        status="created",
    )
    db.add(request)
    db.commit()
    outcome = GenerationOutcome(request=request)

    # 1. Доступные ингредиенты минус запреты
    forbidden = load_forbidden(db, user.user_id)
    banned_terms = forbidden_terms(db, forbidden)
    available = db.scalars(select(AvailableIngredient).where(AvailableIngredient.user_id == user.user_id)).all()
    allowed: list[AvailableIngredient] = []
    conflicts: list[str] = []
    for a in available:
        ok, reasons = check_ingredients([a.ingredient], forbidden)
        if ok:
            allowed.append(a)
        else:
            conflicts += reasons
    if not available:
        conflicts.append("Не выбран набор доступных ингредиентов")
    has_protein = any(a.ingredient.protein_per_100g >= MIN_PROTEIN_SOURCE for a in allowed)
    if available and len(allowed) < MIN_ALLOWED_INGREDIENTS:
        conflicts.append(f"После применения запретов допустимо ингредиентов: {len(allowed)} (нужно не менее {MIN_ALLOWED_INGREDIENTS})")
    if available and not has_protein:
        conflicts.append(f"Среди допустимых ингредиентов нет источника белка (не менее {MIN_PROTEIN_SOURCE:g} г белка на 100 г)")
    if len(allowed) < MIN_ALLOWED_INGREDIENTS or not has_protein:
        have = {a.ingredient_id for a in available}
        recommended = _recommend_missing(db, forbidden, have, need_protein=not has_protein)
        _reject(db, request, "Рецепт не сформирован: доступных ингредиентов недостаточно с учётом запретов", conflicts, recommended, started)
        outcome.suggestions = SUGGESTIONS
        return outcome

    # Продукты, исключённые пожеланием («без колбасы»), не передаются модели и не упоминаются в рецепте
    catalog = list(db.scalars(select(Ingredient)))
    excluded_ids, excluded_terms = _excluded_by_wish(comment, catalog)
    if excluded_ids:
        kept = [a for a in allowed if a.ingredient_id not in excluded_ids]
        if len(kept) >= MIN_ALLOWED_INGREDIENTS and any(a.ingredient.protein_per_100g >= MIN_PROTEIN_SOURCE for a in kept):
            allowed = kept
        else:
            excluded_terms = []
            outcome.warnings.append("Пожелание «без …» не учтено: без этих продуктов в наборе не хватает ингредиентов для рецепта")

    # 2. Контекст для модели генерации
    code_map: dict[str, tuple[Ingredient, float | None]] = {}
    ctx_items: list[ContextIngredient] = []
    # Для завтрака и перекуса модели передаются только подходящие продукты
    context_allowed = allowed
    if meal_type in MIN_SUITABLE:
        suitable = [a for a in allowed if suits_meal(a.ingredient, meal_type)]
        if len(suitable) >= MIN_SUITABLE[meal_type]:
            context_allowed = suitable
        else:
            outcome.warnings.append(
                f"Для {MEAL_GENITIVE[meal_type]} в наборе мало подходящих продуктов — использован весь набор доступных ингредиентов")
    for n, a in enumerate(sorted(context_allowed, key=lambda a: a.ingredient.name), start=1):
        ing = a.ingredient
        code = f"I{n}"
        code_map[code] = (ing, a.available_amount_g)
        ctx_items.append(ContextIngredient(
            code=code, id=ing.ingredient_id, name=ing.name,
            category_code=ing.category.code if ing.category else None,
            category=ing.category.name if ing.category else None,
            protein=ing.protein_per_100g, fat=ing.fat_per_100g, carbs=ing.carb_per_100g, calories=ing.calories_per_100g,
            available_g=a.available_amount_g,
        ))

    # Продукты из пожеланий («хочу с колбасой»): из набора пользователя — обязательны в составе;
    # которых в наборе нет — в рецепт не попадают, пользователь получает пояснение
    wished, missing_wishes, wish_notes = _wished_ingredients(comment, catalog, forbidden, {a.ingredient_id for a in allowed})
    outcome.warnings.extend(wish_notes)
    in_context = {ing.ingredient_id for ing, _ in code_map.values()}
    for n, a in enumerate((a for a in allowed if a.ingredient in wished and a.ingredient_id not in in_context), start=1):
        ing = a.ingredient  # продукт из пожеланий мог быть отсеян по приёму пищи — возвращаем его в контекст
        code = f"W{n}"
        code_map[code] = (ing, a.available_amount_g)
        ctx_items.append(ContextIngredient(
            code=code, id=ing.ingredient_id, name=ing.name,
            category_code=ing.category.code if ing.category else None,
            category=ing.category.name if ing.category else None,
            protein=ing.protein_per_100g, fat=ing.fat_per_100g, carbs=ing.carb_per_100g, calories=ing.calories_per_100g,
            available_g=a.available_amount_g,
        ))

    # Индекс для разрешения ингредиентов из ответа модели по названию (включая синонимы)
    name_index: dict[str, tuple[Ingredient, float | None]] = {}
    for ing, qty in code_map.values():
        for label in (ing.name, *(ing.name_synonyms or [])):
            name_index.setdefault(normalize_text(label), (ing, qty))
    recent = list(db.scalars(
        select(Recipe.name).where(Recipe.user_id == user.user_id).order_by(Recipe.created_at.desc()).limit(6)
    ))

    rated = db.execute(
        select(Recipe.name, RecipeRating.score)
        .join(RecipeRating, RecipeRating.recipe_id == Recipe.recipe_id)
        .where(RecipeRating.user_id == user.user_id)
        .order_by(RecipeRating.rated_at.desc())
        .limit(30)
    ).all()
    context = GenerationContext(
        goal_code=goal.code,
        goal_name=goal.name,
        goal_description=goal.calc_rule or goal.description or "",
        meal_target=meal_target,
        macro_pct={"protein": goal.protein_pct, "fat": goal.fat_pct, "carbs": goal.carb_pct},
        variants=variants,
        difficulty=difficulty,
        comment=comment,
        ingredients=ctx_items,
        forbidden=forbidden.describe(),
        liked=[name for name, score in rated if score >= 4],
        disliked=[name for name, score in rated if score <= 2],
        seed=random.randrange(1 << 30),
        meal_type=meal_type,
        recent=recent,
        must_include=[ing.name for ing in wished],
        unavailable=[*missing_wishes, *excluded_terms],
    )

    request.status = "processing"
    db.commit()

    # 3. Обращение к модели генерации (с резервом на локальный генератор)
    def run(provider) -> list[BuiltRecipe]:
        raw_recipes = provider.generate(context)
        built: list[BuiltRecipe] = []
        for raw in raw_recipes:
            recipe, problem = _post_process(raw, code_map, meal_target, outcome.warnings, optimize=provider.name != "mock",
                                            banned_terms=banned_terms, name_index=name_index, must_have=wished, catalog=catalog)
            if recipe is None:
                outcome.warnings.append(problem)
                continue
            ok, reasons = check_ingredients([i for i, _ in recipe.items], forbidden)
            if not ok:  # недопустимый рецепт пользователю не выдаётся
                conflicts.extend(reasons)
                continue
            built.append(recipe)
        return built

    provider_name = None
    built: list[BuiltRecipe] = []
    try:
        primary = provider or get_primary_provider()
        provider_name = primary.name
        if provider is None and settings.llm_provider == "gigachat" and primary.name == "mock":
            outcome.warnings.append("GigaChat не настроен (не задан ключ GIGACHAT_CREDENTIALS) — рецепт сформирован локальным генератором")
        built = run(primary)
    except LLMError as exc:
        logger.warning("Ошибка модели генерации: %s", exc)
        outcome.warnings.append(f"Модель генерации недоступна: {exc}")
        if not settings.llm_fallback_to_mock:
            request.provider = provider_name
            _reject(db, request, f"Модель генерации недоступна: {exc}", conflicts, [], started)
            return outcome
    if not built and provider_name != "mock" and settings.llm_fallback_to_mock:
        outcome.warnings.append("Использован резервный локальный генератор рецептов")
        provider_name = "mock"
        built = run(MockProvider())

    request.provider = provider_name
    if not built:
        have = {a.ingredient_id for a in available}
        recommended = _recommend_missing(db, forbidden, have, need_protein=False)
        _reject(db, request, "Не удалось сформировать рецепт, удовлетворяющий запретам и требованиям к составу", conflicts, recommended, started)
        outcome.suggestions = SUGGESTIONS
        return outcome

    # 4. Сохранение
    for b in built:
        allowed_ok, reasons = check_ingredients([i for i, _ in b.items], forbidden)
        recipe = Recipe(
            generation_request_id=request.generation_request_id,
            user_id=user.user_id,
            fitness_goal_id=goal.fitness_goal_id,
            name=b.name,
            generation_status="generated",
            matches_restrictions=allowed_ok,
            mismatch_reasons=reasons,
            protein_total_g=round(b.totals.protein, 1),
            fat_total_g=round(b.totals.fat, 1),
            carb_total_g=round(b.totals.carbs, 1),
            calories_kcal=round(b.totals.calories, 1),
            servings=b.servings,
            cooking_instruction=b.steps,
            cooking_time_min=b.cooking_time_min,
            difficulty=b.difficulty,
            tips=b.tips,
            meal_share=meal_share,
            target_calories=round(meal_kcal, 1),
            source=provider_name,
        )
        recipe.items = [
            RecipeIngredient(ingredient_id=ing.ingredient_id, ingredient=ing, mass_g=mass, list_order=pos)
            for pos, (ing, mass) in enumerate(b.items, start=1)
        ]
        recipe.goal = goal
        db.add(recipe)
        outcome.recipes.append(recipe)

    request.status = "completed"
    request.completed_at = utcnow()
    request.duration_ms = int((time.perf_counter() - started) * 1000)
    db.commit()
    return outcome
