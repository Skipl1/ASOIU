#!/bin/sh
set -e

# Миграции и наполнение справочников выполняются под владельцем БД,
# запросы пользователей обрабатываются под ограниченной ролью (ТЗ 4.3).
OWNER_URL="${OWNER_DATABASE_URL:-$DATABASE_URL}"

echo "Применение миграций базы данных..."
DATABASE_URL="$OWNER_URL" alembic upgrade head

echo "Настройка ограниченной учётной записи приложения..."
python -m app.db_roles

echo "Начальное наполнение справочников..."
DATABASE_URL="$OWNER_URL" python -m app.seed

echo "Запуск API (workers: ${API_WORKERS:-2})..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 \
    --workers "${API_WORKERS:-2}" --proxy-headers --forwarded-allow-ips="*"
