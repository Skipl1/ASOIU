FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# postgresql-client — pg_dump/pg_restore для резервного копирования; fonts-dejavu — кириллица в PDF-отчётах
RUN apt-get update \
    && apt-get install -y --no-install-recommends postgresql-client fonts-dejavu-core ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY alembic.ini .
COPY alembic ./alembic
COPY app ./app
COPY certs ./certs
COPY docker-entrypoint.sh .
RUN chmod +x docker-entrypoint.sh \
    && useradd --system --uid 1001 grsn \
    && mkdir -p /data/storage /data/backups \
    && chown -R grsn /data

USER grsn
EXPOSE 8000
ENTRYPOINT ["./docker-entrypoint.sh"]
