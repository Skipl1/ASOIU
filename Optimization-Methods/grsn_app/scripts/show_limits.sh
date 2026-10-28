#!/usr/bin/env bash
# Показывает ресурсы, выделенные контейнерам АС ГРСН, и сравнивает их с требованиями ТЗ к серверу
# (процессор от 2 ядер, оперативная память от 4 ГБ). Linux / macOS / Git Bash.
#
#   bash scripts/show_limits.sh
set -u
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

IDS="$(docker compose ps -q 2>/dev/null)"
[ -n "$IDS" ] || { echo "ОШИБКА: система не запущена. Сначала: bash scripts/setup.sh" >&2; exit 1; }

echo
echo "Ресурсы контейнеров АС ГРСН (лимиты из docker-compose.yml)"
echo "Контейнер           Лимит CPU, ядер  Лимит ОЗУ, МБ  Сейчас CPU   Сейчас ОЗУ"  # printf считает байты, а не буквы
STATS="$(docker stats --no-stream --format '{{.Name}}|{{.CPUPerc}}|{{.MemUsage}}' $IDS)"
for id in $IDS; do
  IFS='|' read -r name nano mem <<<"$(docker inspect --format '{{.Name}}|{{.HostConfig.NanoCpus}}|{{.HostConfig.Memory}}' "$id")"
  name="${name#/}"
  usage="$(printf '%s\n' "$STATS" | grep "^$name|")"
  cpu_now="$(echo "$usage" | cut -d'|' -f2)"; mem_now="$(echo "$usage" | cut -d'|' -f3 | sed 's| / .*||')"
  printf '%-18s %16s %14s %11s %12s\n' "$name" "$(awk "BEGIN{printf \"%.2f\", $nano/1e9}")" "$((mem / 1048576))" "$cpu_now" "$mem_now"
done | sort

TOTAL_NANO=0; TOTAL_MEM=0
for id in $IDS; do
  IFS='|' read -r nano mem <<<"$(docker inspect --format '{{.HostConfig.NanoCpus}}|{{.HostConfig.Memory}}' "$id")"
  TOTAL_NANO=$((TOTAL_NANO + nano)); TOTAL_MEM=$((TOTAL_MEM + mem))
done
CPU_TOTAL="$(awk "BEGIN{printf \"%.2f\", $TOTAL_NANO/1e9}")"
MEM_TOTAL="$(awk "BEGIN{printf \"%.2f\", $TOTAL_MEM/1073741824}")"
echo
echo "Итого выделено системе: $CPU_TOTAL ядра, $MEM_TOTAL ГБ ОЗУ   (ТЗ: процессор от 2 ядер, память от 4 ГБ)"
echo "Сейчас CPU: 100 % = одно полное ядро. Наблюдать вживую: docker stats (столбец MEM USAGE / LIMIT)."
