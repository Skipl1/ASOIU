# Проект API АС ГРСН

API реализован как REST API версии `/api/v1` (FastAPI) с передачей данных в формате JSON.
Авторизация выполняется по JWT-токену в заголовке `Authorization: Bearer <token>`.
Спецификация `openapi.yaml` (OpenAPI 3.1) выгружена из реализации; интерактивная документация — Swagger UI по адресу `/api/docs`.

## Группы эндпоинтов

| Раздел интерфейса | Группа API | Эндпоинты |
|---|---|---|
| Авторизация и регистрация | `auth` | `POST /auth/register`, `POST /auth/login`, `POST /auth/refresh`, `POST /auth/logout`, `GET /auth/me` |
| Профиль пользователя | `profile` | `GET /profile`, `PUT /profile`, `GET /profile/parameter-history`, `POST /profile/parameter-history`, `GET /goals`, `GET /activity-levels` |
| Запреты и аллергены | `restrictions` | `GET /restrictions`, `POST /restrictions`, `DELETE /restrictions`, `DELETE /restrictions/{restriction_id}`, `GET /restrictions/match`, `GET /restrictions/check-available` |
| Каталог ингредиентов | `ingredients` | `GET /ingredients`, `GET /ingredients/{ingredient_id}`, `GET /categories`, `GET /allergens`, `GET /available-ingredients`, `PUT /available-ingredients` |
| Генерация, история и рацион | `recipes` | `POST /recipes/generate`, `GET /recipes`, `GET /recipes/{recipe_id}`, `PATCH /recipes/{recipe_id}`, `DELETE /recipes/{recipe_id}`, `POST /recipes/{recipe_id}/diet`, `DELETE /recipes/{recipe_id}/diet`, `POST /recipes/{recipe_id}/rating` |
| Отчёты | `reports` | `GET /reports/nutrition`, `POST /reports/nutrition/export`, `GET /reports`, `GET /reports/{report_id}/download` |
| Анализ рациона | `analysis` | `GET /analysis/nutrition` |
| Администрирование | `admin` | `GET /admin/stats`, `GET /admin/users`, `PATCH /admin/users/{user_id}`, `DELETE /admin/users/{user_id}`, `GET /admin/logs`, `GET /admin/users/{user_id}/activity`, `POST/PUT/DELETE /admin/ingredients`, `POST/PUT/DELETE /admin/allergens`, `POST/PUT/DELETE /admin/categories`, `GET /admin/integrity`, `GET /admin/backups`, `POST /admin/backups`, `POST /admin/backups/restore` |
| Служебные | `service` | `GET /health` |

## Связь со страницами приложения

- `/login`, `/register` используют `auth`.
- `/profile` использует `profile`.
- `/restrictions` использует `restrictions` и справочник `allergens`.
- `/ingredients` использует `ingredients`.
- `/generate` использует `recipes/generate` и `recipes/{recipe_id}/diet`.
- `/history` использует `recipes`.
- `/reports` использует `reports`.
- `/analysis` использует `analysis`.
- `/admin` использует `admin`.

Полная спецификация находится в файле `openapi.yaml`.
