"""Проверка производительности (ТЗ 7.2): N одновременных пользователей.

Каждый виртуальный пользователь открывает каталог ингредиентов, профиль и историю рецептов,
а часть пользователей запускает генерацию рецепта. Выводится время отклика (медиана, p95, максимум)
и сравнивается с требованиями ТЗ 7.2: каталог ≤ 5 с, генерация ≤ 60 с (одновременные запросы).

Запуск (из каталога backend, нужен httpx):
    .venv/Scripts/python ../scripts/load_test.py --base http://localhost:8080 --users 100
"""

import argparse
import asyncio
import statistics
import time

import httpx

LIMITS = {"GET /ingredients": 5.0, "POST /recipes/generate": 60.0}  # ТЗ 7.2


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://localhost:8080")
    parser.add_argument("--users", type=int, default=100)
    parser.add_argument("--generators", type=int, default=10, help="сколько пользователей запускают генерацию")
    parser.add_argument("--email", default="demo@grsn.local")
    parser.add_argument("--password", default="Demo12345")
    args = parser.parse_args()

    api = args.base.rstrip("/") + "/api/v1"
    limits = httpx.Limits(max_connections=args.users, max_keepalive_connections=args.users)
    async with httpx.AsyncClient(verify=False, timeout=60, limits=limits) as client:
        r = await client.post(f"{api}/auth/login", json={"email": args.email, "password": args.password})
        r.raise_for_status()
        headers = {"Authorization": f"Bearer {r.json()['accessToken']}"}
        goals = (await client.get(f"{api}/goals", headers=headers)).json()
        goal_id = goals[0]["id"]

        timings: dict[str, list[float]] = {}
        errors: list[str] = []

        async def call(name: str, method: str, path: str, **kw) -> None:
            start = time.perf_counter()
            try:
                resp = await client.request(method, f"{api}{path}", headers=headers, **kw)
                if resp.status_code >= 400:
                    errors.append(f"{name}: HTTP {resp.status_code}")
            except httpx.HTTPError as exc:
                errors.append(f"{name}: {exc!r}")
            timings.setdefault(name, []).append(time.perf_counter() - start)

        async def user(n: int) -> None:
            await call("GET /ingredients", "GET", "/ingredients")
            await call("GET /profile", "GET", "/profile")
            await call("GET /recipes", "GET", "/recipes")
            if n < args.generators:
                await call("POST /recipes/generate", "POST", "/recipes/generate",
                           json={"goalId": goal_id, "variantsCount": 1, "mealShare": 0.333})

        started = time.perf_counter()
        await asyncio.gather(*(user(n) for n in range(args.users)))
        total = time.perf_counter() - started

    print(f"Одновременных пользователей: {args.users}, общее время: {total:.1f} с, ошибок: {len(errors)}")
    print(f"{'Запрос':28} {'кол-во':>7} {'медиана':>9} {'p95':>8} {'макс':>8}  требование")
    ok = not errors
    for name, values in timings.items():
        values.sort()
        p95 = values[max(0, int(len(values) * 0.95) - 1)]
        limit = LIMITS.get(name)
        verdict = ""
        if limit:
            passed = p95 <= limit
            ok &= passed
            verdict = f"≤ {limit:g} с — {'выполнено' if passed else 'НЕ выполнено'}"
        print(f"{name:28} {len(values):7} {statistics.median(values):8.2f}с {p95:7.2f}с {values[-1]:7.2f}с  {verdict}")
    for e in errors[:10]:
        print("  ошибка:", e)
    print("ИТОГ:", "требования ТЗ 7.2 выполнены" if ok else "есть нарушения")


if __name__ == "__main__":
    asyncio.run(main())
