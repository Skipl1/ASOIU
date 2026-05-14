# Проект API АС ГРСН

API спроектирован как REST API версии `/api/v1` с передачей данных в формате JSON.
Авторизация выполняется по JWT-токену в заголовке `Authorization: Bearer <token>`.

## Группы эндпоинтов

| Раздел интерфейса | Группа API | Основные эндпоинты |
|---|---|---|
| Авторизация и регистрация | `auth` | `POST /auth/register`, `POST /auth/login`, `POST /auth/logout` |
| Профиль пользователя | `profile` | `GET /profile`, `PUT /profile`, `GET /goals`, `POST /profile/parameter-history` |
| Запреты и аллергены | `restrictions` | `GET /restrictions`, `POST /restrictions`, `DELETE /restrictions/{restrictionId}` |
| Каталог ингредиентов | `ingredients` | `GET /ingredients`, `GET /ingredients/{ingredientId}`, `PUT /available-ingredients` |
| Генерация и история рецептов | `recipes` | `POST /recipes/generate`, `GET /recipes`, `GET /recipes/{recipeId}`, `POST /recipes/{recipeId}/rating` |
| Отчёты | `reports` | `GET /reports/nutrition`, `POST /reports/nutrition/export` |
| Анализ рациона | `analysis` | `GET /analysis/nutrition` |
| Администрирование | `admin` | `GET /admin/users`, `PATCH /admin/users/{userId}`, `POST /admin/ingredients`, `PUT /admin/ingredients/{ingredientId}`, `POST /admin/allergens`, `POST /admin/backups` |

## Связь с макетами

- `index.html`, `register.html` используют `auth`.
- `profile.html` использует `profile` и `goals`.
- `restrictions.html` использует `restrictions`.
- `ingredients.html` использует `ingredients` и `available-ingredients`.
- `generate.html` использует `recipes/generate`.
- `history.html` использует `recipes` и `rating`.
- `reports.html` использует `reports`.
- `analysis.html` использует `analysis`.
- `admin.html` использует `admin`.

Полная спецификация находится в файле `openapi.yaml`.
