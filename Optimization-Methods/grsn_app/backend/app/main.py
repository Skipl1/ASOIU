"""АС ГРСН — REST API (FastAPI). Документация OpenAPI: /api/docs."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.config import get_settings
from app.db import engine
from app.middleware import RejectNulMiddleware
from app.routers import admin, auth, ingredients, profile, recipes, reports, restrictions
from app.services.llm.gigachat_provider import start_keepalive

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

API_PREFIX = "/api/v1"

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    start_keepalive()
    yield


app = FastAPI(
    title="АС ГРСН API",
    version="1.0.0",
    description="REST API автоматизированной системы генерации персонализированных рецептов спортивного питания.",
    docs_url="/api/docs",
    redoc_url=None,
    openapi_url=f"{API_PREFIX}/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(RejectNulMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

FIELD_NAMES = {
    "email": "E-mail", "password": "Пароль", "name": "Имя", "weightKg": "Вес", "heightCm": "Рост", "age": "Возраст",
    "gender": "Пол", "activityLevel": "Уровень активности", "goalId": "Фитнес-ориентир", "variantsCount": "Количество вариантов",
    "mealShare": "Доля суточной нормы", "score": "Оценка", "dateFrom": "Начало периода", "dateTo": "Конец периода",
    "format": "Формат", "sourceText": "Название запрета", "protein100g": "Белки", "fat100g": "Жиры", "carbs100g": "Углеводы",
    "calories100g": "Калорийность", "comment": "Комментарий", "massG": "Масса",
}


def _translate(err: dict) -> str:
    loc = [str(x) for x in err.get("loc", []) if x not in ("body", "query", "path")]
    field = FIELD_NAMES.get(loc[-1], loc[-1]) if loc else "Запрос"
    t, ctx = err.get("type", ""), err.get("ctx") or {}
    messages = {
        "missing": "обязательное поле",
        "value_error": str(ctx.get("error", err.get("msg", ""))).removeprefix("Value error, "),
        "string_too_short": f"не менее {ctx.get('min_length')} символов",
        "string_too_long": f"не более {ctx.get('max_length')} символов",
        "greater_than_equal": f"значение должно быть не меньше {ctx.get('ge')}",
        "greater_than": f"значение должно быть больше {ctx.get('gt')}",
        "less_than_equal": f"значение должно быть не больше {ctx.get('le')}",
        "less_than": f"значение должно быть меньше {ctx.get('lt')}",
        "literal_error": f"допустимые значения: {ctx.get('expected')}",
        "uuid_parsing": "некорректный идентификатор",
        "date_from_datetime_parsing": "некорректная дата",
        "date_parsing": "некорректная дата",
        "int_parsing": "ожидается целое число",
        "float_parsing": "ожидается число",
        "too_short": "список слишком короткий",
        "too_long": "список слишком длинный",
    }
    msg = messages.get(t, err.get("msg", "некорректное значение"))
    if "email" in t or (loc and loc[-1] == "email" and t == "value_error"):
        msg = "некорректный адрес электронной почты"
    return f"{field}: {msg}"


@app.exception_handler(RequestValidationError)
async def validation_handler(_: Request, exc: RequestValidationError):
    errors = [_translate(e) for e in exc.errors()]
    return JSONResponse(status_code=422, content={"detail": "; ".join(errors), "errors": errors})


for module in (auth, profile, restrictions, ingredients, recipes, reports, admin):
    app.include_router(module.router, prefix=API_PREFIX)


@app.get(f"{API_PREFIX}/health", tags=["service"], summary="Проверка доступности API и базы данных")
def health():
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return {"status": "ok", "llmProvider": settings.llm_provider, "llmModel": settings.gigachat_model}
