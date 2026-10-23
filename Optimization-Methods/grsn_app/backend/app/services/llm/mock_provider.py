"""Локальный (резервный) генератор рецептов.

Используется, когда GigaChat недоступен или не настроен. Состав подбирается по правилам
(источник белка + источник углеводов + овощи/фрукты + источник жиров), а массы ингредиентов —
решением задачи оптимизации:

    min_x  Σ_k w_k · (A_k · x − b_k)²,   lo_i ≤ x_i ≤ hi_i,

где x_i — масса i-го ингредиента (в сотнях грамм), строки A — калорийность и БЖУ на 100 г,
b — целевые калории и БЖУ приёма пищи, w_k — веса значимости, нормированные на b_k².
Задача решается методом проекции градиента на брус ограничений. Для каждого варианта
перебирается несколько сочетаний продуктов и выбирается сочетание с минимальной невязкой.
"""

import random

from app.services.llm.base import ContextIngredient, GenerationContext, LLMRecipe, LLMRecipeItem
from app.services.llm.cooking_steps import compose

ROW_WEIGHTS = {"calories": 4.0, "protein": 2.0, "fat": 1.0, "carbs": 1.0}
KEYS = ("calories", "protein", "fat", "carbs")


def solve_masses(
    columns: list[tuple[float, float, float, float]],
    target: dict,
    lower: list[float],
    upper: list[float],
    iterations: int = 3000,
) -> list[float]:
    """Проекция градиента для взвешенной задачи наименьших квадратов с ограничениями-коридорами.

    columns — (ккал, Б, Ж, У) на 100 г; lower/upper — границы в сотнях грамм; возвращает массы в граммах.
    """
    b = [max(target[k], 1.0) for k in KEYS]
    w = [ROW_WEIGHTS[k] / (bk * bk) for k, bk in zip(KEYS, b)]
    n = len(columns)
    a = [[columns[i][k] for i in range(n)] for k in range(4)]  # 4 × n

    # Константа Липшица градиента: L ≤ 2·||Aᵀ W A||_F
    h = [[sum(w[k] * a[k][i] * a[k][j] for k in range(4)) for j in range(n)] for i in range(n)]
    lipschitz = 2 * sum(v * v for row in h for v in row) ** 0.5 or 1.0
    step = 1.0 / lipschitz

    x = [(lo + hi) / 2 for lo, hi in zip(lower, upper)]
    for _ in range(iterations):
        residual = [sum(a[k][i] * x[i] for i in range(n)) - b[k] for k in range(4)]
        grad = [2 * sum(w[k] * a[k][i] * residual[k] for k in range(4)) for i in range(n)]
        x_new = [min(max(x[i] - step * grad[i], lower[i]), upper[i]) for i in range(n)]
        if max(abs(x_new[i] - x[i]) for i in range(n)) < 1e-7:
            x = x_new
            break
        x = x_new
    return [v * 100 for v in x]


def _share(value: float, kcal_per_g: int, calories: float) -> float:
    return value * kcal_per_g / calories if calories > 0 else 0.0


def _is_protein(i: ContextIngredient) -> bool:
    return i.protein >= 8 and _share(i.protein, 4, i.calories) >= 0.3


def _is_carb(i: ContextIngredient) -> bool:
    if i.category_code == "cat_vegetables":
        return i.carbs >= 12  # картофель, батат
    return _share(i.carbs, 4, i.calories) >= 0.6 and i.calories >= 40


def _is_veg(i: ContextIngredient) -> bool:
    return i.category_code == "cat_vegetables" and i.carbs < 12


def _is_fat(i: ContextIngredient) -> bool:
    return _share(i.fat, 9, i.calories) >= 0.6


def _is_breakfast_protein(i: ContextIngredient) -> bool:
    return i.category_code == "cat_dairy" or "протеин" in i.name.lower()


def _lower_first(text: str) -> str:
    return text[:1].lower() + text[1:] if text else text


def _unique(chosen: list[tuple[str, ContextIngredient]]) -> list[tuple[str, ContextIngredient]]:
    seen: set[str] = set()
    return [(role, i) for role, i in chosen if not (i.code in seen or seen.add(i.code))]


class MockProvider:
    """Детерминированный локальный генератор (резервная модель генерации).

    Стиль блюда определяется приёмом пищи: обед/ужин — горячее с гарниром, завтрак — омлет или каша,
    перекус — простое сочетание без сложной готовки. Без указания приёма пищи чередуются горячее и каша.
    """

    name = "mock"

    def generate(self, context: GenerationContext) -> list[LLMRecipe]:
        rng = random.Random(context.seed)
        pool = list(context.ingredients)
        proteins = [i for i in pool if _is_protein(i)]
        carbs = [i for i in pool if _is_carb(i)]
        vegs = [i for i in pool if _is_veg(i)]
        fats = [i for i in pool if _is_fat(i) and i not in proteins]
        for group in (proteins, carbs, vegs, fats):
            rng.shuffle(group)

        def has(i, *keys):
            return any(k in i.name.lower() for k in keys)

        g = {
            "hot_proteins": [p for p in proteins if not _is_breakfast_protein(p) and not has(p, "батончик", "хумус")] or proteins,
            "soft_proteins": [p for p in proteins if _is_breakfast_protein(p) or has(p, "батончик", "хумус", "тофу")],
            "eggs": [p for p in proteins if has(p, "яйц", "яичн")],
            "porridge": [c for c in carbs if c.category_code == "cat_grains" and has(c, "хлопь", "гречк", "рис", "киноа", "гранола")
                         and not has(c, "хлеб")],
            "fruits": [c for c in carbs if c.category_code == "cat_fruits"],
            "breads": [c for c in carbs if has(c, "хлеб")],
            "vegs": vegs,
            "raw_vegs": [v for v in vegs if has(v, "огур", "помидор", "перец", "морков")],
            "fats": fats,
            "nuts": [f for f in fats if not has(f, "масло")],
            "oils": [f for f in fats if has(f, "масло")],
        }
        g["main_carbs"] = ([c for c in carbs if c.category_code != "cat_fruits" and not has(c, "хлопь", "гранола", "хлеб")]
                           or [c for c in carbs if c.category_code != "cat_fruits"] or carbs)
        g["hot_proteins"] = [p for p in g["hot_proteins"] if not has(p, "яйц", "яичн")] or g["hot_proteins"]

        meal = context.meal_type
        if meal == "breakfast":
            styles = [s for s, ok in (("omelette", bool(g["eggs"])), ("porridge", bool(g["porridge"] or g["fruits"]))) if ok]
        elif meal == "snack":
            styles = ["snack"]
        elif meal in ("lunch", "dinner"):
            styles = ["hot"]
        else:
            styles = ["hot"] + (["porridge"] if g["soft_proteins"] and (g["porridge"] or g["fruits"]) else [])
        styles = styles or ["hot"]
        recipes = self._run(context, styles, g, proteins, carbs)
        if not recipes and styles != ["hot"]:  # из набора не собрать блюдо этого стиля — горячее блюдо
            recipes = self._run(context, ["hot"], g, proteins, carbs)
        return recipes

    def _run(self, context: GenerationContext, styles: list[str], g: dict, proteins, carbs) -> list[LLMRecipe]:
        recipes: list[LLMRecipe] = []
        used: set[tuple[str, ...]] = set()
        used_main: set[str] = set()
        for v in range(context.variants * 4):
            if len(recipes) >= context.variants:
                break
            style = styles[v % len(styles)]
            # Перебор сочетаний продуктов: выбирается сочетание с минимальной невязкой целевой функции
            best: tuple[float, list] | None = None
            for candidate in self._candidates(v, style, g):
                if len(candidate) < 2 or tuple(sorted(i.code for _, i in candidate)) in used:
                    continue
                solved = self._solve(context, candidate)
                if solved:
                    repeats = sum(1 for r, i, _ in solved[1] if r in ("protein", "egg", "carb") and i.code in used_main)
                    solved = (solved[0] + 0.05 * repeats, solved[1])
                if solved and (best is None or solved[0] < best[0]):
                    best = solved
            if best is None:
                continue
            used.add(tuple(sorted(i.code for _, i, _ in best[1])))
            used_main.update(i.code for r, i, _ in best[1] if r in ("protein", "egg", "carb"))
            recipes.append(self._build(best[1], style, proteins, carbs))
        return recipes

    @staticmethod
    def _candidates(v: int, style: str, g: dict):
        def pick(items, k):
            return items[k % len(items)] if items else None

        if style == "hot":
            fat = [("fat", pick(g["fats"], v))] if g["fats"] else []
            hp, mc, vegs = g["hot_proteins"], g["main_carbs"], g["vegs"]
            veg = []
            if vegs:
                veg = [("veg", vegs[v % len(vegs)])] + ([("veg", vegs[(v + 1) % len(vegs)])] if len(vegs) > 1 else [])
            for pi in range(min(3, len(hp))):
                for ci in range(max(1, min(3, len(mc)))):
                    chosen = [("protein", hp[(v + pi) % len(hp)])]
                    if mc:
                        chosen.append(("carb", mc[(v + ci) % len(mc)]))
                    yield _unique(chosen + veg + fat)
        elif style == "omelette":
            vegs = [x for x in g["vegs"] if not any(k in x.name.lower() for k in ("картоф", "батат", "тыкв", "огур"))]
            for ei in range(min(2, len(g["eggs"]))):
                for vi in range(max(1, min(3, len(vegs)))):
                    chosen = [("egg", g["eggs"][(v + ei) % len(g["eggs"])])]
                    if vegs:
                        chosen.append(("veg", vegs[(v + vi) % len(vegs)]))
                        if len(vegs) > 1:
                            chosen.append(("veg", vegs[(v + vi + 1) % len(vegs)]))
                    if g["breads"]:
                        chosen.append(("carb", pick(g["breads"], v)))
                    elif g["fruits"]:
                        chosen.append(("carb2", pick(g["fruits"], v)))
                    if g["oils"]:
                        chosen.append(("fat", pick(g["oils"], v)))
                    yield _unique(chosen)
        elif style == "porridge":
            bases = g["porridge"] or g["fruits"]
            for bi in range(min(3, len(bases))):
                base = bases[(v + bi) % len(bases)]
                chosen = [("carb", base)]
                fruits = [f for f in g["fruits"] if f is not base]
                if fruits:
                    chosen.append(("carb2", pick(fruits, v)))
                soft = [p for p in g["soft_proteins"] if "хумус" not in p.name.lower()]
                if soft:
                    chosen.append(("protein", pick(soft, v + bi)))
                if g["nuts"]:
                    chosen.append(("fat", pick(g["nuts"], v)))
                yield _unique(chosen)
        else:  # перекус
            fruit, nut = pick(g["fruits"], v), pick(g["nuts"], v)
            soft = g["soft_proteins"] + g["eggs"]
            for pi in range(max(1, min(3, len(soft)))):
                protein = soft[(v + pi) % len(soft)] if soft else None
                if fruit:  # фрукт + белок + орехи
                    yield _unique([x for x in (("carb2", fruit), ("protein", protein), ("fat", nut)) if x[1]])
                bread, raw = pick(g["breads"], v + pi), pick(g["raw_vegs"], v + pi)
                if bread or raw:  # хлебцы/хлеб + белок + свежие овощи
                    yield _unique([x for x in (("carb", bread), ("protein", protein), ("veg", raw)) if x[1]])

    @staticmethod
    def _bounds(role: str, item: ContextIngredient, scale: float, small: float) -> tuple[float, float]:
        lo, hi = {
            "protein": (50, 250),
            "egg": (55, 220),
            "carb": (30, 150),
            "carb2": (30, 150),
            "veg": (60, 250),
            "fat": (0, 20),
        }[role]
        lo *= small  # небольшой приём пищи (перекус) — меньшие минимальные порции
        if role != "veg":
            hi *= scale  # крупный приём пищи — более широкие коридоры масс
        if item.calories > 500:  # орехи, масла — малые порции
            hi = min(hi, 40)
        if "протеин" in item.name.lower():
            lo, hi = 20 * small, 45
        if item.available_g:
            hi = min(hi, item.available_g)
            lo = min(lo, hi)
        return lo / 100, hi / 100

    def _solve(self, ctx: GenerationContext, chosen) -> tuple[float, list] | None:
        kcal = ctx.meal_target["calories"]
        scale, small = max(1.0, kcal / 700), min(1.0, kcal / 500)
        columns = [(i.calories, i.protein, i.fat, i.carbs) for _, i in chosen]
        bounds = [self._bounds(role, i, scale, small) for role, i in chosen]
        masses = solve_masses(columns, ctx.meal_target, [b[0] for b in bounds], [b[1] for b in bounds], iterations=1500)

        items: list[tuple[str, ContextIngredient, float]] = []
        for (role, ingredient), mass, (lo, hi) in zip(chosen, masses, bounds):
            rounded = min(max(round(mass / 5) * 5, lo * 100), hi * 100)
            rounded = (rounded // 5) * 5  # кратно 5 г и не выше верхней границы
            if rounded >= 5:
                items.append((role, ingredient, float(rounded)))
        if len(items) < 2:
            return None
        score = 0.0
        for col, key in enumerate(KEYS):
            value = sum(m / 100 * (i.calories, i.protein, i.fat, i.carbs)[col] for _, i, m in items)
            target = max(ctx.meal_target[key], 1.0)
            score += ROW_WEIGHTS[key] * ((value - target) / target) ** 2
        return score, items

    @staticmethod
    def _build(items: list[tuple[str, ContextIngredient, float]], style: str, proteins, carbs) -> LLMRecipe:
        steps, cooking_time = compose(items, style)
        names = [_lower_first(i.name) for _, i, _ in items if "масло" not in i.name.lower()]
        main = next((i for r, i, _ in items if r in ("protein", "egg")), items[0][1])
        if style == "omelette":
            name = "Омлет: " + ", ".join(names)
        elif style == "porridge":
            name = "Каша: " + ", ".join(names)
        elif style == "snack":
            name = "Перекус: " + ", ".join(names)
        else:
            side = [_lower_first(i.name) for r, i, _ in items if r in ("carb", "veg")]
            name = main.name + (" с гарниром: " + ", ".join(side) if side else "")

        used = {i.code for _, i, _ in items}
        tips: list[str] = []
        alt_protein = next((p for p in proteins if p.code not in used and p.category_code == main.category_code
                            and _is_breakfast_protein(p) == _is_breakfast_protein(main)), None)
        if alt_protein and style != "omelette":
            tips.append(f"Можно заменить «{main.name}» на «{alt_protein.name}» с пересчётом массы.")
        first_carb = next((i for r, i, _ in items if r == "carb"), None)
        if first_carb is not None:
            alt_carb = next((c for c in carbs if c.code not in used and c.category_code == first_carb.category_code), None)
            if alt_carb:
                tips.append(f"Вместо «{first_carb.name}» подойдёт «{alt_carb.name}».")

        difficulty = "low" if cooking_time <= 30 else "medium" if cooking_time <= 60 else "high"
        return LLMRecipe(
            name=name[:200],
            servings=1,
            ingredients=[LLMRecipeItem(code=i.code, massG=m) for _, i, m in items],
            steps=steps,
            cookingTimeMin=cooking_time,
            difficulty=difficulty,
            tips=tips,
        )
