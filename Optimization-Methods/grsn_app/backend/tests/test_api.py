"""Сквозные сценарии функциональной проверки (ТЗ 7.1) и проверки безопасности (ТЗ 7.3)."""

from datetime import date, timedelta

from sqlalchemy import select

from app.models import User
from conftest import auth

API = "/api/v1"


def _goal(client, token, code="goal_gain"):
    goals = client.get(f"{API}/goals", headers=auth(token)).json()
    return next(g for g in goals if g["code"] == code)


def _ingredients(client, token):
    return {i["code"]: i for i in client.get(f"{API}/ingredients", headers=auth(token)).json()}


def _fill_profile(client, token, goal_code="goal_gain"):
    goal = _goal(client, token, goal_code)
    r = client.put(f"{API}/profile", headers=auth(token), json={
        "weightKg": 78, "heightCm": 182, "age": 21, "gender": "male", "activityLevel": 1.55, "goalId": goal["id"]})
    assert r.status_code == 200, r.text
    return goal, r.json()


def test_registration_validation(client):
    weak = client.post(f"{API}/auth/register", json={"name": "A", "email": "weak@test.ru", "password": "onlyletters"})
    assert weak.status_code == 422 and "буквы и цифры" in weak.json()["detail"]
    bad_email = client.post(f"{API}/auth/register", json={"name": "A", "email": "not-email", "password": "Passw0rd1"})
    assert bad_email.status_code == 422
    ok = client.post(f"{API}/auth/register", json={"name": "A", "email": "dup@test.ru", "password": "Passw0rd1"})
    assert ok.status_code == 201
    assert ok.json()["expiresIn"] == 1800
    dup = client.post(f"{API}/auth/register", json={"name": "B", "email": "DUP@test.ru", "password": "Passw0rd1"})
    assert dup.status_code == 409


def test_password_stored_as_bcrypt_hash(client, db):
    client.post(f"{API}/auth/register", json={"name": "H", "email": "hash@test.ru", "password": "Passw0rd1"})
    user = db.scalar(select(User).where(User.email == "hash@test.ru"))
    assert user.password_hash.startswith("$2") and "Passw0rd1" not in user.password_hash


def test_bruteforce_lockout(client):
    client.post(f"{API}/auth/register", json={"name": "L", "email": "lock@test.ru", "password": "Passw0rd1"})
    codes = [client.post(f"{API}/auth/login", json={"email": "lock@test.ru", "password": "wrong1234"}).status_code for _ in range(5)]
    assert codes == [401, 401, 401, 401, 423]
    # даже правильный пароль не принимается во время блокировки
    r = client.post(f"{API}/auth/login", json={"email": "lock@test.ru", "password": "Passw0rd1"})
    assert r.status_code == 423 and "Повторите через" in r.json()["detail"]


def test_auth_required_and_logout(client, user_token):
    assert client.get(f"{API}/profile").status_code == 401
    assert client.get(f"{API}/profile", headers=auth("garbage")).status_code == 401
    assert client.get(f"{API}/profile", headers=auth(user_token)).status_code == 200
    assert client.post(f"{API}/auth/logout", headers=auth(user_token)).status_code == 204
    assert client.get(f"{API}/profile", headers=auth(user_token)).status_code == 401


def test_profile_targets(client, user_token):
    empty = client.get(f"{API}/profile", headers=auth(user_token)).json()
    assert empty["isComplete"] is False
    goal, profile = _fill_profile(client, user_token)
    assert profile["bmr"] == 1887.5
    assert profile["targetCalories"] == round(1887.53 * 1.55 + 300, 1)
    assert profile["goal"]["code"] == "goal_gain"
    history = client.get(f"{API}/profile/parameter-history", headers=auth(user_token)).json()
    assert len(history) == 1 and history[0]["weightKg"] == 78
    bad = client.put(f"{API}/profile", headers=auth(user_token), json={
        "weightKg": 78, "heightCm": 182, "age": 21, "gender": "male", "activityLevel": 1.4, "goalId": goal["id"]})
    assert bad.status_code == 422 and "Уровень активности" in bad.json()["detail"]


def test_restrictions_normalization_flow(client, user_token):
    h = auth(user_token)
    # однозначное соответствие по синониму
    r = client.post(f"{API}/restrictions", headers=h, json={"sourceText": "Овсянка"})
    assert r.status_code == 201 and r.json()["type"] == "ingredient" and r.json()["targetName"] == "Овсяные хлопья"
    # неоднозначное — система предлагает выбор
    r = client.post(f"{API}/restrictions", headers=h, json={"sourceText": "арахис"})
    assert r.status_code == 409 and len(r.json()["candidates"]) >= 2
    allergen = next(c for c in r.json()["candidates"] if c["type"] == "allergen")
    r = client.post(f"{API}/restrictions", headers=h, json={"sourceText": "арахис", "allergenId": allergen["id"]})
    assert r.status_code == 201 and r.json()["type"] == "allergen"
    # нет в справочниках — контроль по названию
    r = client.post(f"{API}/restrictions", headers=h, json={"sourceText": "Кунжут"})
    assert r.status_code == 201 and r.json()["type"] == "substance"
    # дубликат
    assert client.post(f"{API}/restrictions", headers=h, json={"sourceText": "Овсянка"}).status_code == 409
    items = client.get(f"{API}/restrictions", headers=h).json()
    assert len(items) == 3
    # каталог маркирует недопустимые ингредиенты
    catalog = _ingredients(client, user_token)
    assert catalog["ing_oatmeal"]["isAllowed"] is False
    assert catalog["ing_peanut_butter"]["isAllowed"] is False
    assert catalog["ing_protein_bar"]["isAllowed"] is False  # составной: овсянка и арахисовая паста
    assert catalog["ing_chicken_breast"]["isAllowed"] is True
    assert client.delete(f"{API}/restrictions/{items[0]['id']}", headers=h).status_code == 204


def test_generation_success_history_rating(client, user_token):
    h = auth(user_token)
    goal, profile = _fill_profile(client, user_token)
    r = client.post(f"{API}/restrictions", headers=h, json={"sourceText": "молоко"})
    assert r.status_code == 409  # совпадает и с аллергеном, и с ингредиентом — выбор пользователя
    lactose = next(c for c in r.json()["candidates"] if c["type"] == "allergen")
    client.post(f"{API}/restrictions", headers=h, json={"sourceText": "молоко", "allergenId": lactose["id"]})
    catalog = _ingredients(client, user_token)
    # запрещённый ингредиент нельзя добавить в набор
    r = client.put(f"{API}/available-ingredients", headers=h, json={"items": [{"ingredientId": catalog["ing_cottage_cheese"]["id"]}]})
    assert r.status_code == 422
    items = [{"ingredientId": catalog[c]["id"], "availableQtyG": q} for c, q in
             [("ing_chicken_breast", 500), ("ing_brown_rice", 300), ("ing_broccoli", 400), ("ing_olive_oil", 100), ("ing_banana", 200)]]
    assert client.put(f"{API}/available-ingredients", headers=h, json={"items": items}).status_code == 200

    r = client.post(f"{API}/recipes/generate", headers=h, json={"goalId": goal["id"], "variantsCount": 2, "mealShare": 0.333})
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["status"] == "generated" and 1 <= len(body["recipes"]) <= 2
    recipe = body["recipes"][0]
    assert recipe["isAllowed"] is True and len(recipe["instructions"]) >= 3
    meal_target = profile["targetCalories"] * 0.333
    assert abs(recipe["caloriesTotal"] - meal_target) / meal_target < 0.15
    # итоговые значения соответствуют формулам 4.6 (сумма по ингредиентам)
    assert abs(sum(i["calories"] for i in recipe["ingredients"]) - recipe["caloriesTotal"]) < 1
    assert {c["indicator"] for c in recipe["checks"]} == {"БЖУ", "Калорийность", "Запреты"}
    for i in recipe["ingredients"]:
        assert i["massG"] <= next(x["availableQtyG"] for x in items if x["ingredientId"] == i["ingredientId"])

    history = client.get(f"{API}/recipes", headers=h).json()
    assert len(history) == len(body["recipes"])
    r = client.post(f"{API}/recipes/{recipe['id']}/rating", headers=h, json={"score": 5, "comment": "Отлично"})
    assert r.status_code == 201
    card = client.get(f"{API}/recipes/{recipe['id']}", headers=h).json()
    assert card["myRating"]["score"] == 5 and card["rating"] == 5

    # редактирование: изменение массы пересчитывает БЖУ
    edit = [{"ingredientId": i["ingredientId"], "massG": i["massG"] * 2} for i in card["ingredients"]]
    edited = client.patch(f"{API}/recipes/{recipe['id']}", headers=h, json={"ingredients": edit}).json()
    assert abs(edited["caloriesTotal"] - 2 * card["caloriesTotal"]) < 2


def test_generation_insufficient_ingredients(client, user_token):
    h = auth(user_token)
    goal, _ = _fill_profile(client, user_token, "goal_loss")
    catalog = _ingredients(client, user_token)
    client.put(f"{API}/available-ingredients", headers=h, json={"items": [{"ingredientId": catalog["ing_banana"]["id"]}]})
    body = client.post(f"{API}/recipes/generate", headers=h, json={"goalId": goal["id"], "variantsCount": 1, "mealShare": 0.333}).json()
    assert body["status"] == "failed" and body["recipes"] == []
    assert body["conflicts"] and len(body["recommendedIngredients"]) >= 3 and body["suggestions"]


def test_user_cannot_access_foreign_recipe(client, user_token):
    h = auth(user_token)
    goal, _ = _fill_profile(client, user_token)
    catalog = _ingredients(client, user_token)
    items = [{"ingredientId": catalog[c]["id"]} for c in ("ing_turkey", "ing_buckwheat", "ing_tomato")]
    client.put(f"{API}/available-ingredients", headers=h, json={"items": items})
    recipe = client.post(f"{API}/recipes/generate", headers=h, json={"goalId": goal["id"], "variantsCount": 1, "mealShare": 0.4}).json()["recipes"][0]
    other = client.post(f"{API}/auth/register", json={"name": "O", "email": "other@test.ru", "password": "Passw0rd1"}).json()["accessToken"]
    assert client.get(f"{API}/recipes/{recipe['id']}", headers=auth(other)).status_code == 404


def test_reports_and_analysis(client, user_token):
    h = auth(user_token)
    goal, _ = _fill_profile(client, user_token)
    catalog = _ingredients(client, user_token)
    items = [{"ingredientId": catalog[c]["id"]} for c in ("ing_salmon", "ing_quinoa", "ing_spinach", "ing_avocado")]
    client.put(f"{API}/available-ingredients", headers=h, json={"items": items})
    ids = []
    for share in (0.3, 0.4, 0.3):
        r = client.post(f"{API}/recipes/generate", headers=h, json={"goalId": goal["id"], "variantsCount": 1, "mealShare": share})
        ids.append(r.json()["recipes"][0]["id"])
        assert r.json()["recipes"][0]["inDiet"] is False

    today = date.today()
    params = {"dateFrom": (today - timedelta(days=6)).isoformat(), "dateTo": today.isoformat()}
    # сгенерированные, но не включённые в рацион рецепты в отчёт не попадают
    assert client.get(f"{API}/reports/nutrition", headers=h, params=params).json()["recipesCount"] == 0
    for rid in ids:
        assert client.post(f"{API}/recipes/{rid}/diet", headers=h).json()["inDiet"] is True
    report = client.get(f"{API}/reports/nutrition", headers=h, params=params).json()
    assert report["recipesCount"] == 3 and len(report["dailyCalories"]) == 7 and report["averageCalories"] > 0
    # убранный из рациона рецепт остаётся в истории, но исчезает из отчёта
    assert client.delete(f"{API}/recipes/{ids[0]}/diet", headers=h).json()["inDiet"] is False
    assert client.get(f"{API}/reports/nutrition", headers=h, params=params).json()["recipesCount"] == 2
    assert len(client.get(f"{API}/recipes", headers=h).json()) == 3
    assert len(client.get(f"{API}/recipes", headers=h, params={"inDiet": "true"}).json()) == 2
    client.post(f"{API}/recipes/{ids[0]}/diet", headers=h)

    for fmt in ("pdf", "xlsx", "csv"):
        r = client.post(f"{API}/reports/nutrition/export", headers=h, json={**params, "format": fmt})
        assert r.status_code == 200, r.text
        file = client.get(r.json()["downloadUrl"], headers=h)
        assert file.status_code == 200 and len(file.content) > 100
    assert file.content.startswith(b"\xef\xbb\xbf")  # CSV в UTF-8 с BOM для Excel
    saved = client.get(f"{API}/reports", headers=h).json()
    assert len(saved) == 3 and all(s["fileAvailable"] for s in saved)

    analysis = client.get(f"{API}/analysis/nutrition", headers=h, params=params).json()
    assert analysis["recipesAnalyzed"] == 3 and analysis["recommendations"]
    assert len(analysis["calculatedWeightTrend"]) == 7
    bad = client.get(f"{API}/reports/nutrition", headers=h, params={"dateFrom": "2026-05-10", "dateTo": "2026-05-01"})
    assert bad.status_code == 422


def test_admin_permissions_and_crud(client, user_token, admin_token):
    assert client.get(f"{API}/admin/users", headers=auth(user_token)).status_code == 403
    ha = auth(admin_token)
    stats = client.get(f"{API}/admin/stats", headers=ha).json()
    assert stats["ingredients"] >= 60 and stats["allergens"] == 7
    assert client.get(f"{API}/admin/integrity", headers=ha).status_code == 200

    cats = client.get(f"{API}/categories", headers=ha).json()
    allergens = client.get(f"{API}/allergens", headers=ha).json()
    payload = {"name": "Сыр тофу копчёный", "categoryId": cats[0]["id"], "protein100g": 15, "fat100g": 9,
               "carbs100g": 2, "calories100g": 150, "allergenIds": [allergens[0]["id"]], "synonyms": ["копчёный тофу"]}
    created = client.post(f"{API}/admin/ingredients", headers=ha, json=payload)
    assert created.status_code == 201, created.text
    assert client.post(f"{API}/admin/ingredients", headers=ha, json=payload).status_code == 409
    bad = client.post(f"{API}/admin/ingredients", headers=ha, json={**payload, "name": "X", "protein100g": 60, "fat100g": 50})
    assert bad.status_code == 422
    ing_id = created.json()["id"]
    updated = client.put(f"{API}/admin/ingredients/{ing_id}", headers=ha, json={**payload, "calories100g": 155})
    assert updated.json()["calories100g"] == 155
    assert client.delete(f"{API}/admin/ingredients/{ing_id}", headers=ha).status_code == 204

    a = client.post(f"{API}/admin/allergens", headers=ha, json={"name": "Кунжут", "synonyms": ["сезам"]})
    assert a.status_code == 201
    assert client.delete(f"{API}/admin/allergens/{a.json()['id']}", headers=ha).status_code == 204

    users = client.get(f"{API}/admin/users", headers=ha).json()
    target = next(u for u in users if u["role"] == "user")
    blocked = client.patch(f"{API}/admin/users/{target['id']}", headers=ha, json={"status": "blocked"})
    assert blocked.json()["status"] == "blocked"
    login = client.post(f"{API}/auth/login", json={"email": target["email"], "password": "Passw0rd1"})
    assert login.status_code == 403
    client.patch(f"{API}/admin/users/{target['id']}", headers=ha, json={"status": "active"})
    me = next(u for u in users if u["email"] == "admin@grsn.local")
    assert client.patch(f"{API}/admin/users/{me['id']}", headers=ha, json={"status": "blocked"}).status_code == 409

    logs = client.get(f"{API}/admin/logs", headers=ha, params={"action": "admin_user_update"}).json()
    assert logs and logs[0]["actionTitle"].startswith("Админ")


def test_allergen_in_use_cannot_be_deleted(client, user_token, admin_token):
    allergens = client.get(f"{API}/allergens", headers=auth(admin_token)).json()
    fish = next(a for a in allergens if a["code"] == "allergen_fish")
    client.post(f"{API}/restrictions", headers=auth(user_token), json={"sourceText": "рыба", "allergenId": fish["id"]})
    r = client.delete(f"{API}/admin/allergens/{fish['id']}", headers=auth(admin_token))
    assert r.status_code == 409 and "запретах" in r.json()["detail"]


def test_meal_type_breakfast_and_snack(client, user_token):
    h = auth(user_token)
    goal, _ = _fill_profile(client, user_token, "goal_maintain")
    catalog = _ingredients(client, user_token)
    codes = ["ing_chicken_breast", "ing_turkey", "ing_egg", "ing_oatmeal", "ing_banana", "ing_tomato", "ing_spinach",
             "ing_wholegrain_bread", "ing_almond", "ing_brown_rice", "ing_broccoli"]
    client.put(f"{API}/available-ingredients", headers=h, json={"items": [{"ingredientId": catalog[c]["id"]} for c in codes]})
    meat = {catalog["ing_chicken_breast"]["id"], catalog["ing_turkey"]["id"]}

    body = client.post(f"{API}/recipes/generate", headers=h, json={
        "goalId": goal["id"], "variantsCount": 2, "mealShare": 0.25, "mealType": "breakfast"}).json()
    assert body["status"] == "generated"
    for recipe in body["recipes"]:
        assert recipe["mealType"] == "breakfast"
        assert not meat & {i["ingredientId"] for i in recipe["ingredients"]}  # мясо на завтрак не передаётся модели
        assert recipe["name"].startswith(("Омлет", "Каша"))

    snack = client.post(f"{API}/recipes/generate", headers=h, json={
        "goalId": goal["id"], "variantsCount": 1, "mealShare": 0.1, "mealType": "snack"}).json()["recipes"][0]
    assert snack["name"].startswith("Перекус") and snack["caloriesTotal"] < 450

    lunch = client.post(f"{API}/recipes/generate", headers=h, json={
        "goalId": goal["id"], "variantsCount": 1, "mealShare": 0.35, "mealType": "lunch"}).json()["recipes"][0]
    assert meat & {i["ingredientId"] for i in lunch["ingredients"]}
    history = client.get(f"{API}/recipes", headers=h).json()
    assert {r["mealType"] for r in history} == {"breakfast", "snack", "lunch"}


def test_meal_type_falls_back_to_full_set(client, user_token):
    h = auth(user_token)
    goal, _ = _fill_profile(client, user_token, "goal_maintain")
    catalog = _ingredients(client, user_token)
    codes = ["ing_chicken_breast", "ing_brown_rice", "ing_broccoli"]  # для завтрака подходит слишком мало
    client.put(f"{API}/available-ingredients", headers=h, json={"items": [{"ingredientId": catalog[c]["id"]} for c in codes]})
    body = client.post(f"{API}/recipes/generate", headers=h, json={
        "goalId": goal["id"], "variantsCount": 1, "mealShare": 0.25, "mealType": "breakfast"}).json()
    assert body["status"] == "generated"
    assert any("мало подходящих продуктов" in w for w in body["warnings"])


def test_forbidden_products_removed_from_instruction_text(client, user_token, monkeypatch):
    """Модель упомянула творог в шаге у пользователя с запретом на молочное — шаг должен быть удалён."""
    from app.services import generation
    from app.services.llm.base import LLMRecipe

    class TalkativeModel:
        name = "gigachat"

        def generate(self, ctx):
            codes = [i.code for i in ctx.ingredients[:3]]
            return [LLMRecipe(name="Каша с бананом", ingredients=[{"code": c, "massG": 100} for c in codes], steps=[
                "Промойте гречку и залейте водой в соотношении 1:2.",
                "Варите под крышкой на слабом огне 15–18 минут до впитывания воды.",
                "Добавьте в кашу творог и разомните вилкой.",
                "Нарежьте банан кружками и выложите поверх каши.",
            ], tips=["Можно полить молоком."])]

    monkeypatch.setattr(generation, "get_primary_provider", lambda: TalkativeModel())
    h = auth(user_token)
    goal, _ = _fill_profile(client, user_token, "goal_maintain")
    r = client.post(f"{API}/restrictions", headers=h, json={"sourceText": "молоко"})
    lactose = next(c for c in r.json()["candidates"] if c["type"] == "allergen")
    client.post(f"{API}/restrictions", headers=h, json={"sourceText": "молоко", "allergenId": lactose["id"]})
    catalog = _ingredients(client, user_token)
    items = [{"ingredientId": catalog[c]["id"]} for c in ("ing_buckwheat", "ing_banana", "ing_egg")]
    client.put(f"{API}/available-ingredients", headers=h, json={"items": items})

    body = client.post(f"{API}/recipes/generate", headers=h, json={"goalId": goal["id"], "variantsCount": 1, "mealShare": 0.25}).json()
    recipe = body["recipes"][0]
    text = " ".join(recipe["instructions"] + recipe["tips"]).lower()
    assert "творог" not in text and "молок" not in text
    assert any("удалены шаги" in w and "творог" in w for w in body["warnings"])


def test_measured_trend_ignores_measurements_minutes_apart(client, user_token):
    h = auth(user_token)
    _fill_profile(client, user_token)  # замер 78 кг
    client.post(f"{API}/profile/parameter-history", headers=h,
                json={"weightKg": 77.5, "heightCm": 182, "age": 21, "activityLevel": 1.55})
    today = date.today()
    a = client.get(f"{API}/analysis/nutrition", headers=h,
                   params={"dateFrom": (today - timedelta(days=6)).isoformat(), "dateTo": today.isoformat()}).json()
    assert a["measuredTrendKgPerWeek"] is None
    assert len(a["measuredWeights"]) == 1 and a["measuredWeights"][0]["weightKg"] == 77.5
