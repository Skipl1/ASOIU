#!/bin/sh
set -e

echo "Применение миграций базы данных..."
alembic upgrade head

echo "Начальное наполнение справочников..."
python -m app.seed

echo "Запуск API (workers: ${API_WORKERS:-2})..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 \
    --workers "${API_WORKERS:-2}" --proxy-headers --forwarded-allow-ips="*"
