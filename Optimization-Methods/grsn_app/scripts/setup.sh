#!/usr/bin/env bash
# Установка и запуск АС ГРСН в Docker одной командой (Linux / macOS / Git Bash).
#
#   bash scripts/setup.sh                       обычная установка
#   bash scripts/setup.sh --gigachat-key "<ключ>"   с ключом GigaChat
#   bash scripts/setup.sh --https               включить HTTPS (самоподписанный сертификат)
#   bash scripts/setup.sh --no-browser          не открывать браузер
#   bash scripts/setup.sh --reset               удалить контейнеры и ВСЕ данные и установить заново
#
# Что делает: проверяет Docker, создаёт .env (случайные пароль БД и секрет JWT, свободные порты),
# собирает и запускает контейнеры, ждёт готовности и показывает адрес сайта.
# Повторный запуск безопасен: существующий .env и данные не затрагиваются.
set -u

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

GIGACHAT_KEY="${GIGACHAT_CREDENTIALS:-}"
HTTPS=0; NO_BROWSER=0; RESET=0
while [ $# -gt 0 ]; do
  case "$1" in
    --gigachat-key) GIGACHAT_KEY="${2:-}"; shift 2 ;;
    --https) HTTPS=1; shift ;;
    --no-browser) NO_BROWSER=1; shift ;;
    --reset) RESET=1; shift ;;
    -h|--help) sed -n '2,13p' "$0"; exit 0 ;;
    *) echo "Неизвестный параметр: $1" >&2; exit 2 ;;
  esac
done

step() { printf '\n\033[36m==> %s\033[0m\n' "$1"; }
fail() { printf '\n\033[31mОШИБКА: %s\033[0m\n' "$1" >&2; exit 1; }

port_busy() { (exec 3<>"/dev/tcp/127.0.0.1/$1") 2>/dev/null && return 0 || return 1; }
free_port() {  # free_port <начало> [исключения...]
  local p="$1"; shift
  local limit=$((p + 200))
  while [ "$p" -lt "$limit" ]; do
    local skip=0
    for x in "$@"; do [ "$x" = "$p" ] && skip=1; done
    if [ "$skip" = 0 ] && ! port_busy "$p"; then echo "$p"; return 0; fi
    p=$((p + 1))
  done
  fail "Не найден свободный порт, начиная с $1."
}
secret() { LC_ALL=C tr -dc 'a-zA-HJ-NP-Z2-9' </dev/urandom | head -c "$1"; echo; }

# Заменяет значение ключа в .env (или добавляет строку). Значения не содержат символа '|'.
set_env() {  # set_env <ключ> <значение>
  local key="$1" value="$2"
  if grep -q "^${key}=" .env; then
    sed -i.bak "s|^${key}=.*|${key}=${value}|" .env && rm -f .env.bak
  else
    printf '%s=%s\n' "$key" "$value" >> .env
  fi
}
get_env() { grep "^$1=" .env | head -1 | cut -d= -f2- | tr -d '\r'; }

# ---------------------------------------------------------------- 1. Docker
step "Проверка Docker"
command -v docker >/dev/null 2>&1 || fail "Docker не найден. Установите Docker (https://docs.docker.com/get-docker/) и повторите."
docker info >/dev/null 2>&1 || fail "Docker не запущен. Запустите Docker (Docker Desktop или демон) и повторите."
docker compose version >/dev/null 2>&1 || fail "Не найден плагин «docker compose». Обновите Docker."
echo "Docker готов."

# ---------------------------------------------------------------- 2. Сброс
if [ "$RESET" = 1 ]; then
  step "Удаление контейнеров и данных (--reset)"
  docker compose down -v --remove-orphans
fi

# ---------------------------------------------------------------- 3. .env
step "Настройка файла .env"
if [ -f .env ]; then
  sed -i.bak 's/\r$//' .env && rm -f .env.bak
  echo ".env уже существует — секреты и порты сохранены."
else
  [ -f .env.example ] || fail "Не найден .env.example. Запускайте скрипт из клона репозитория (папка grsn_app)."
  tr -d '\r' < .env.example > .env
  HTTP_P="$(free_port 8080)"
  HTTPS_P="$(free_port 8443 "$HTTP_P")"
  DB_P="$(free_port 5432 "$HTTP_P" "$HTTPS_P")"
  set_env POSTGRES_PASSWORD "$(secret 24)"
  set_env JWT_SECRET "$(secret 64)"
  set_env APP_DB_PASSWORD "$(secret 24)"
  set_env HTTP_PORT "$HTTP_P"
  set_env HTTPS_PORT "$HTTPS_P"
  set_env DB_PORT "$DB_P"
  echo "Создан .env: случайные пароль БД и секрет JWT, порты: сайт $HTTP_P, HTTPS $HTTPS_P, БД $DB_P."
fi
if [ -n "$GIGACHAT_KEY" ]; then set_env GIGACHAT_CREDENTIALS "$(echo "$GIGACHAT_KEY" | tr -d '[:space:]')"; echo "Ключ GigaChat записан в .env."; fi
[ "$HTTPS" = 1 ] && set_env ENABLE_HTTPS true

HTTP_PORT="$(get_env HTTP_PORT)"; HTTP_PORT="${HTTP_PORT:-8080}"
HTTPS_PORT="$(get_env HTTPS_PORT)"; HTTPS_PORT="${HTTPS_PORT:-8443}"
SITE="http://localhost:$HTTP_PORT"
[ "$(get_env ENABLE_HTTPS)" = "true" ] && SITE="https://localhost:$HTTPS_PORT"
HAS_KEY="$(get_env GIGACHAT_CREDENTIALS)"

# ---------------------------------------------------------------- 4. Сборка и запуск
step "Сборка и запуск контейнеров (первый раз 5–15 минут: загружаются образы и зависимости)"
docker compose up -d --build || fail "docker compose up завершился с ошибкой (см. вывод выше). Частые причины: нет интернета, занят порт, мало места на диске."

# ---------------------------------------------------------------- 5. Ожидание готовности
step "Ожидание готовности системы"
READY=0
for _ in $(seq 1 100); do
  if [ "$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 "http://localhost:$HTTP_PORT/api/v1/health")" = "200" ]; then READY=1; break; fi
  printf '.'; sleep 3
done
echo
if [ "$READY" = 0 ]; then
  docker compose ps; docker compose logs --tail 40 backend
  fail "Система не ответила за 5 минут. Журнал backend выведен выше."
fi

LOGIN="$(curl -s -o /dev/null -w '%{http_code}' --max-time 20 -X POST "http://localhost:$HTTP_PORT/api/v1/auth/login" \
  -H 'Content-Type: application/json' -d '{"email":"demo@grsn.local","password":"Demo12345"}')"

printf '\n\033[32m==================================================================\n'
printf ' АС ГРСН запущена:  %s\n' "$SITE"
printf '==================================================================\033[0m\n'
echo " Демо-пользователь:  demo@grsn.local   / Demo12345"
echo " Администратор:      admin@grsn.local  / Admin12345"
echo " Документация API:   http://localhost:$HTTP_PORT/api/docs"
[ "$(get_env ENABLE_HTTPS)" = "true" ] && echo " HTTPS самоподписанный: браузер предупредит — «Дополнительно» → «Перейти»."
[ -z "$HAS_KEY" ] && echo " Ключ GigaChat не задан: рецепты составляет локальный генератор (ключ: .env → GIGACHAT_CREDENTIALS)."
[ "$LOGIN" != "200" ] && echo " Внимание: вход демо-пользователя не подтверждён (код $LOGIN) — docker compose logs backend"
echo
echo " Остановить:  docker compose stop      Запустить снова:  docker compose up -d"
echo " (команды docker compose выполняйте в папке: $ROOT)"

if [ "$NO_BROWSER" = 0 ]; then
  if command -v xdg-open >/dev/null 2>&1; then xdg-open "$SITE" >/dev/null 2>&1 &
  elif command -v open >/dev/null 2>&1; then open "$SITE" >/dev/null 2>&1 &
  elif command -v cmd.exe >/dev/null 2>&1; then cmd.exe /c start "" "$SITE" >/dev/null 2>&1 &
  fi
fi
exit 0
