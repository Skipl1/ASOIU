#!/bin/sh
# Ежедневная полная резервная копия PostgreSQL (ТЗ 4.3): pg_dump по расписанию cron, хранение 30 дней.
set -e
FILE="/backups/grsn_$(date +%Y%m%d_%H%M%S)_auto.dump"
pg_dump -h "${PGHOST:-db}" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc -f "$FILE"
chown 1001:1001 "$FILE" 2>/dev/null || true  # файл доступен API для восстановления; на папке Windows chown не поддерживается
find /backups -name 'grsn_*.dump' -mtime +"${BACKUP_RETENTION_DAYS:-30}" -delete
echo "$(date '+%F %T') резервная копия создана: $FILE"
