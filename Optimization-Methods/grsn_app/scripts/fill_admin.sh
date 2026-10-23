#!/usr/bin/env bash
# Заполняет учётную запись администратора историей за месяц (для проверки и показа). Linux / macOS / Git Bash.
#
#   bash scripts/fill_admin.sh          только администратор
#   bash scripts/fill_admin.sh --demo   заодно пересоздать историю демо-пользователя
#
# Система должна быть уже запущена (scripts/setup.sh). Данные администратора как пользователя заменяются,
# остальные пользователи и справочники не затрагиваются. Повторный запуск безопасен.
set -u

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

ARGS=(--fill-admin)
[ "${1:-}" = "--demo" ] && ARGS+=(--refresh-demo)

fail() { printf '\n\033[31mОШИБКА: %s\033[0m\n' "$1" >&2; exit 1; }

docker info >/dev/null 2>&1 || fail "Docker не запущен. Запустите Docker и повторите."
[ "$(docker compose ps backend --format '{{.State}}' 2>/dev/null)" = "running" ] \
  || fail "Система не запущена. Сначала выполните: bash scripts/setup.sh (папка: $ROOT)"

printf '\n\033[36m==> Ожидание готовности системы\033[0m\n'
READY=0
for _ in $(seq 1 60); do
  if [ "$(docker compose ps backend --format '{{.Health}}' 2>/dev/null)" = "healthy" ]; then READY=1; break; fi
  sleep 3
done
[ "$READY" = 1 ] || fail "Backend не стал готовым за 3 минуты. Проверьте: docker compose logs backend"

printf '\n\033[36m==> Заполнение учётной записи администратора (около 20 секунд)\033[0m\n'
docker compose exec -T backend python -m app.seed "${ARGS[@]}" || fail "Заполнение не удалось (см. вывод выше)."

PORT="$(grep '^HTTP_PORT=' .env 2>/dev/null | head -1 | cut -d= -f2- | tr -d '\r')"
printf '\n\033[32m==================================================================\n'
printf ' Готово. Откройте http://localhost:%s\n' "${PORT:-8080}"
printf '==================================================================\033[0m\n'
echo " Администратор:  admin@grsn.local / Admin12345"
echo "   профиль, замеры веса, набор продуктов, около 120 рецептов за 30 дней"
[ "${1:-}" = "--demo" ] && echo " Демо-пользователь:  demo@grsn.local / Demo12345  (история пересоздана)"
exit 0
