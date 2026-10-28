# АС ГРСН — автоматизированная система генерации персонализированных рецептов спортивного питания

Реализация по техническому заданию (`../lab2 copy/…_лаба_1_тз`) и техническому проекту (`../laba_2/…_лаба_2_тп`).

| Слой | Технологии |
|---|---|
| Клиент | React 18.2, Vite, React Router, Recharts; адаптивная вёрстка по макетам `laba_2/mockups` |
| Сервер | Python 3.12, FastAPI, Pydantic, SQLAlchemy 2, Alembic, JWT, bcrypt |
| БД | PostgreSQL 15 |
| Модель генерации | GigaChat API, модель **GigaChat-2 (Lite)**; резервный локальный генератор |
| Отчёты | PDF (ReportLab), XLSX (openpyxl), CSV |
| Инфраструктура | Docker Compose, Nginx (обратный прокси, HTTP или HTTPS), cron + `pg_dump` |

## Быстрый запуск (Docker)

Нужны только **Git** и **Docker Desktop** (Windows / macOS) или Docker Engine (Linux). Всё остальное делает скрипт установки: создаёт `.env` со случайными паролем БД и секретом JWT, подбирает свободные порты, собирает контейнеры, ждёт готовности и открывает сайт.

```bash
git clone --branch 2.0mb_norm --single-branch https://github.com/Skipl1/ASOIU.git
cd ASOIU/Optimization-Methods/grsn_app

# Windows (PowerShell)
powershell -ExecutionPolicy Bypass -File scripts\setup.ps1
# Linux / macOS / Git Bash
bash scripts/setup.sh
```

С ключом GigaChat: `scripts\setup.ps1 -GigaChatKey "<ключ>"` или `bash scripts/setup.sh --gigachat-key "<ключ>"`. Без ключа всё работает, рецепты составляет локальный генератор. Первая сборка занимает 5–15 минут. Для автоматической установки помощником Claude есть отдельная пошаговая инструкция: [SETUP_FOR_CLAUDE.md](SETUP_FOR_CLAUDE.md).

Данные для проверки: `scripts\fill_admin.bat` (двойной щелчок) или `powershell -ExecutionPolicy Bypass -File scripts\fill_admin.ps1` (Linux/macOS: `bash scripts/fill_admin.sh`) заполняют аккаунт администратора историей за месяц (профиль, замеры веса, около 120 рецептов). Ключ `-Demo` (`--demo`) заодно пересоздаёт историю демо-пользователя. Запускать после установки, повторный запуск безопасен.

Вручную (то же самое без скрипта):

```bash
cp .env.example .env        # задайте POSTGRES_PASSWORD, JWT_SECRET, GIGACHAT_CREDENTIALS
docker compose up -d --build
```

Откройте **http://localhost:8080**.

По умолчанию HTTPS отключён (`ENABLE_HTTPS=false`), сертификат не нужен. Для приёмки по ТЗ 7.3 задайте в `.env` `ENABLE_HTTPS=true` и выполните `docker compose up -d frontend`. Сайт станет доступен на https://localhost:8443, а HTTP будет перенаправлять на HTTPS. Если в `frontend/nginx/certs` нет `server.crt` и `server.key`, создаётся самоподписанный сертификат, и браузер покажет предупреждение.

| Учётная запись | Логин | Пароль |
|---|---|---|
| Администратор | `admin@grsn.local` | `Admin12345` (меняется в `.env`) |
| Демо-пользователь с историей за неделю | `demo@grsn.local` | `Demo12345` |

Документация API (Swagger UI): http://localhost:8080/api/docs.

Контейнеры:

- `db` — PostgreSQL;
- `backend` — API, при старте применяет миграции и наполняет НСИ;
- `frontend` — Nginx со статикой и `/api`-прокси;
- `backup` — cron, ежедневный `pg_dump` в 03:00, копии старше 30 дней удаляются.

## Подключение GigaChat

1. Зарегистрируйтесь на [developers.sber.ru](https://developers.sber.ru) и создайте проект GigaChat API для физических лиц (тариф Freemium).
2. В настройках проекта получите **ключ авторизации** (Authorization key) и запишите его в `.env`: `GIGACHAT_CREDENTIALS=...`.
3. Модель задаётся `GIGACHAT_MODEL=GigaChat-2` (Lite). Корневой сертификат Минцифры уже лежит в `backend/certs`.
4. Перезапустите backend: `docker compose up -d backend`.

Особенности:

- **Один поток.** Freemium допускает только один запрос к модели одновременно. Ограничение действует во всех процессах и контейнерах через advisory lock PostgreSQL (`app/services/llm/slots.py`). Остальные запросы ждут до `LLM_QUEUE_WAIT_SECONDS`.
- **Контроль ответа модели.** Ответ модели проверяется по JSON-схеме. Ингредиенты сопоставляются с каталогом, БЖУ и калорийность **пересчитываются на сервере** по формулам ТЗ 4.6, запреты проверяются по правилу ТЗ 4.7.2.
- **Коррекция масс.** Состав, предложенный моделью, сохраняется, а массы подбирает оптимизатор (тот же метод проекции градиента) под целевые калорийность и БЖУ приёма пищи. Если модель не взяла источник жиров, а он есть в наборе пользователя, сервер добавляет его отдельным шагом.
- **Приём пищи.** Завтрак, обед, ужин или перекус. Для завтрака и перекуса модели передаются только подходящие продукты (без мяса и гарниров), приём пищи становится обязательным условием в промпте (`app/services/meals.py`).
- **Безопасность текста.** Шаги и советы модели проверяются на упоминание запрещённых продуктов, их синонимов и аллергенов. Такие шаги удаляются, и пользователь видит предупреждение. Если после удаления шагов осталось меньше трёх, рецепт отбраковывается.
- **Подробная инструкция.** Модель просят дать 6–10 шагов в форме на «вы»: способ, температура, время, признаки готовности. Сервер добавляет в начало шаг «Подготовка» с точными массами, а в конец — «Хранение».
- **Время ответа.** TCP- и TLS-соединение с серверами Сбера и получение OAuth-токена занимают от нескольких до 15–20 секунд. Поэтому каждый процесс API при старте и затем раз в `GIGACHAT_KEEPALIVE_SECONDS` (30 с) делает служебный запрос списка моделей: токены он не расходует, а соединение и токен остаются «прогретыми». Если сервер всё же закрыл соединение, запрос один раз повторяется на новом. API запускается в 2 процессах (`API_WORKERS=2`): этого хватает для 100 одновременных пользователей, а служебных запросов к Сберу остаётся около 40 за 10 минут.
- **Резервный генератор.** Если ключ не задан или модель недоступна, рецепт формирует локальный генератор (`LLM_FALLBACK_TO_MOCK=true`), и пользователь видит предупреждение. Массы ингредиентов в нём подбираются задачей оптимизации: взвешенный МНК с ограничениями-коридорами, решаемый методом проекции градиента (`app/services/llm/mock_provider.py`).

## Ресурсы сервера (требования ТЗ)

ТЗ требует сервер от 2 ядер и от 4 ГБ ОЗУ. В `docker-compose.yml` контейнерам выделено в сумме ровно столько, то есть система работает в границах минимального сервера:

| Контейнер | CPU, ядер | ОЗУ |
|---|---|---|
| db (PostgreSQL) | 0,75 | 1,5 ГБ |
| backend (FastAPI) | 1 | 1,75 ГБ |
| frontend (Nginx) | 0,15 | 256 МБ |
| backup (cron + pg_dump) | 0,1 | 512 МБ |
| **Итого** | **2** | **4 ГБ** |

Как показать:

- `powershell -ExecutionPolicy Bypass -File scripts\show_limits.ps1` (Linux/macOS: `bash scripts/show_limits.sh`) выводит лимиты каждого контейнера, текущее потребление и сумму;
- `docker stats` показывает нагрузку вживую, а в столбце `MEM USAGE / LIMIT` виден лимит памяти;
- `docker inspect grsn-backend-1 --format "{{.HostConfig.NanoCpus}} {{.HostConfig.Memory}}"` выводит лимит в «сырых» единицах: 1000000000 = 1 ядро, байты.

Значения меняются переменными `*_CPUS` и `*_MEMORY` в `.env`. Частоту процессора (от 2 ГГц), диск (от 20 ГБ) и скорость сети Docker не ограничивает, это характеристики самого компьютера.

## Права в базе данных (ТЗ 4.3)

Приложение подключается к PostgreSQL **отдельной ограниченной учётной записью `grsn_app`**, а не владельцем базы:

- у неё только `SELECT`, `INSERT`, `UPDATE`, `DELETE` в схеме `public`, а создавать, изменять и удалять таблицы, очищать их (`TRUNCATE`), управлять ролями и базой нельзя; таблица `alembic_version` ей недоступна;
- миграции, наполнение справочников, резервное копирование и восстановление выполняются под владельцем (`OWNER_DATABASE_URL`): при старте backend сам создаёт роль (`app/db_roles.py`, идемпотентно), права на таблицы, создаваемые позже (миграции, `pg_restore`), выдаются автоматически;
- пароль роли задаётся `APP_DB_PASSWORD` в `.env`, а если он не задан, выводится из `POSTGRES_PASSWORD`.

Проверка: `docker compose exec -e PGPASSWORD=<пароль роли> db psql -h 127.0.0.1 -U grsn_app -d grsn -c "DROP TABLE users"` → `must be owner of table users`.

## Локальная разработка

```bash
# PostgreSQL для разработки
docker run -d --name grsn-dev-db -e POSTGRES_USER=grsn -e POSTGRES_PASSWORD=grsn_dev_pass -e POSTGRES_DB=grsn -p 5433:5432 postgres:15-alpine

# Backend
cd backend
python -m venv .venv && .venv/Scripts/pip install -r requirements-dev.txt   # Linux/macOS: .venv/bin/...
.venv/Scripts/alembic upgrade head
.venv/Scripts/python -m app.seed                       # + --refresh-demo (история демо заново), --fill-admin (месяц истории у администратора)
.venv/Scripts/uvicorn app.main:app --reload --port 8000

# Frontend (прокси /api -> 127.0.0.1:8000)
cd frontend
npm install
npm run dev            # http://localhost:5173
```

Настройки читаются из `.env` в корне `grsn_app` или в `backend` (см. `backend/app/config.py`).

## Тесты

```bash
cd backend
.venv/Scripts/python -m pytest -q                     # 43 теста: формулы 4.6, правило 4.7.2, сценарии ТЗ 7.1 и 7.3, пожелания к рецепту, GigaChat
.venv/Scripts/python ../scripts/load_test.py --base http://localhost:8080 --users 100   # нагрузочная проверка ТЗ 7.2
```

Результат нагрузочного теста на стенде Docker Desktop (локальный генератор):

- 100 одновременных пользователей, 0 ошибок;
- каталог: p95 = 1,5 с (требование ≤ 3 с);
- генерация: p95 = 1,3 с (требование ≤ 5 с).

С GigaChat время генерации определяется ответом модели, а параллельные запросы встают в очередь.

## Структура

```
backend/app/
  main.py              приложение FastAPI, обработчик ошибок валидации
  config.py, db.py     настройки и подключение к БД
  models.py            17 таблиц (14 из ТП + parameter_history, ingredient_components, audit_log)
  schemas.py           схемы запросов и ответов (camelCase, как в openapi.yaml)
  security.py, deps.py bcrypt, JWT, проверка прав
  routers/             auth, profile, restrictions, ingredients, recipes, reports(+analysis), admin
  services/
    nutrition.py       математическая модель ТЗ 4.6 (BMR, TDEE, БЖУ, δ, доли)
    restrictions.py    нормализация, синонимы, правило ТЗ 4.7.2 (включая составные продукты)
    generation.py      генерация: контекст → модель → постпроверка → сохранение
    llm/               GigaChat, локальный генератор, ограничение потоков
    reports.py         агрегация за период, экспорт PDF/XLSX/CSV
    analysis.py        анализ и прогноз: отклонения, тренд веса, рекомендации
    backup.py          pg_dump / pg_restore
    integrity.py       мониторинг корректности справочников
  seed.py              НСИ: 4 цели, 6 категорий, 7 аллергенов, 65 ингредиентов (3 составных)
backend/alembic/       миграции
frontend/src/pages/    10 экранов: вход, регистрация, профиль, запреты, ингредиенты, генерация,
                       история, отчёты, анализ, администрирование
scripts/               backup.sh (cron), load_test.py
docs/openapi.json      спецификация API, сгенерированная приложением
```

## Отклонения от ТП (внести в документацию)

Реализация следует ТП. Ниже решения, принятые там, где документы расходились между собой или чего-то не хватало:

1. **`users.name`** — добавлено поле имени. Его требует `RegisterRequest` в API, но в физической модели БД его не было.
2. **Уровень активности** — 5 коэффициентов k (1,2 / 1,375 / 1,55 / 1,725 / 1,9) по ТЗ 4.6. В классификаторе ТП было 3 значения (`low`/`medium`/`high`). Хранится число.
3. **Статусы генерации** — в БД используются статусы классификатора ТП (`created`/`processing`/`completed`/`rejected`), в API — `generated`/`failed` по `openapi.yaml`.
4. **Новые таблицы:**
   - `parameter_history` — для `/profile/parameter-history` и анализа динамики веса;
   - `ingredient_components` — состав составного продукта для правила 4.7.2, п. 3;
   - `audit_log` — журнал событий, неудачные входы, логи администратора.
5. **Блокировка подбора пароля** — поля `failed_login_count` и `locked_until` в `users`. Выход и блокировка аннулируют токены через `token_version`.
6. **Справочники** — в НСИ добавлены коды (`code`) и синонимы аллергенов для нормализации запретов. В `fitness_goals` добавлены целевые доли БЖУ, к целям из ТП добавлены аллергены «Соя» и «Арахис» (примеры из ТЗ 4.7.1).
7. **Новые эндпоинты:**
   - `auth/refresh`, `auth/me`;
   - `activity-levels`, `categories`, `allergens`;
   - `restrictions/match`, `restrictions/check-available`, `DELETE /restrictions`;
   - `PATCH`/`DELETE /recipes/{id}` (редактирование, ТЗ 4.1.1);
   - `GET /reports`, `reports/{id}/download`;
   - `admin/stats`, `admin/logs`, `admin/users/{id}/activity`, `DELETE admin/users/{id}`;
   - CRUD `admin/categories`;
   - `admin/integrity`;
   - `GET admin/backups`, `admin/backups/restore` (кнопка «Восстановить» в макете);
   - `health`.
8. **Модель генерации** — GigaChat-2 (Lite) через официальный SDK, резервный локальный генератор. Лимит Freemium — один поток.
9. **Отчёты** — формат XLSX добавлен в классификатор форматов (в шаблоне НСИ были только PDF и CSV; в ТП и макетах есть XLSX).
10. **Рацион** — поле `recipes.generation_status` из физической модели ТП получило значения:
    - `generated` — рецепт сгенерирован и лежит в истории;
    - `accepted` — пользователь включил рецепт в рацион.

    Отчёты и анализ строятся только по рецептам рациона, поэтому отвергнутые и лишние варианты в расчёт не попадают. Новых полей нет. Эндпоинты `POST`/`DELETE /recipes/{id}/diet`, кнопка «Добавить в рацион» на генерации и в истории. В ТП нужно дополнить классификатор статусов рецепта и описание процессов «Генерация» и «Отчёт».
11. **Приём пищи** — в `POST /recipes/generate` добавлено необязательное поле `mealType` (`breakfast` / `lunch` / `dinner` / `snack`). Отдельной колонки в БД нет: приём пищи записывается в начало `generation_requests.comment` («Приём пищи: завтрак. …») и возвращается в рецептах как `mealType`.
