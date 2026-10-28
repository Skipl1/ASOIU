"""Проверка формул раздела 4.6 ТЗ."""

import pytest

from app.services import nutrition as n
from app.services.llm.mock_provider import solve_masses


def test_bmr_harris_benedict():
    # 88.362 + 13.397·78 + 4.799·182 − 5.677·21
    assert n.bmr("male", 78, 182, 21) == pytest.approx(1887.53, abs=0.01)
    # 447.593 + 9.247·60 + 3.098·165 − 4.330·25
    assert n.bmr("female", 60, 165, 25) == pytest.approx(1405.333, abs=0.01)


def test_tdee_and_target():
    e = n.energy_profile("male", 78, 182, 21, 1.55, 300)
    assert e.tdee == pytest.approx(1887.53 * 1.55, abs=0.1)
    assert e.target == pytest.approx(e.tdee + 300, abs=0.1)


def test_recipe_totals_and_atwater():
    rows = [n.NutrientRow(150, 23, 2, 0, 110), n.NutrientRow(70, 7, 2, 72, 350)]
    t = n.recipe_totals(rows)
    assert t.protein == pytest.approx(150 * 23 / 100 + 70 * 7 / 100)
    assert t.fat == pytest.approx(3 + 1.4)
    assert t.carbs == pytest.approx(50.4)
    assert t.calories == pytest.approx(165 + 245)
    assert t.calories_by_macros == pytest.approx(4 * t.protein + 9 * t.fat + 4 * t.carbs)


def test_deviation_and_percent():
    assert n.deviation(800, 1 / 3, 2700) == pytest.approx(-100)
    pct = n.macro_percent(50, 20, 100)  # 4·50 + 9·20 + 4·100 = 780 ккал
    assert pct == {"protein": round(200 / 780 * 100, 1), "fat": round(180 / 780 * 100, 1), "carbs": round(400 / 780 * 100, 1)}
    assert n.macro_percent(0, 0, 0)["protein"] == 0
    # доли считаются от 4P + 9F + 4C, а не от калорийности по каталогу, поэтому в сумме дают 100 %
    pct = n.macro_percent(20.5, 6.0, 29.9)
    assert sum(pct.values()) == pytest.approx(100, abs=0.2)


def test_projected_gradient_hits_target():
    # курица, рис, брокколи; цель — 700 ккал, Б 45, Ж 20, У 85
    columns = [(110, 23, 2, 0), (350, 7, 2, 72), (34, 3, 0.4, 5.2)]
    target = {"calories": 700, "protein": 45, "fat": 20, "carbs": 85}
    masses = solve_masses(columns, target, [0.5, 0.3, 0.8], [3.0, 2.0, 2.5])
    kcal = sum(m / 100 * c[0] for m, c in zip(masses, columns))
    assert kcal == pytest.approx(700, rel=0.08)
    for m, lo, hi in zip(masses, [50, 30, 80], [300, 200, 250]):
        assert lo - 1e-6 <= m <= hi + 1e-6
