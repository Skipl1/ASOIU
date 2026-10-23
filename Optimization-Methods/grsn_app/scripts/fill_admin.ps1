<#
.SYNOPSIS
  Заполняет учётную запись администратора историей за месяц (для проверки и показа). Windows PowerShell 5.1+.

.DESCRIPTION
  Система должна быть уже запущена (scripts\setup.ps1). Скрипт добавляет администратору профиль, запрет на орехи,
  набор продуктов, ежедневные замеры веса и около 120 рецептов за 30 дней (часть в рационе, часть с оценками),
  как будто он месяц пользуется системой. Данные администратора как пользователя заменяются; повторный запуск безопасен.
  Остальные пользователи и справочники не затрагиваются.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File scripts\fill_admin.ps1

.PARAMETER Demo
  Заодно пересоздать историю демо-пользователя (demo@grsn.local) относительно сегодняшней даты.
#>
param(
    [switch]$Demo
)

$ErrorActionPreference = "Continue"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

function Step([string]$text) { Write-Host ""; Write-Host "==> $text" -ForegroundColor Cyan }
function Fail([string]$text) { Write-Host ""; Write-Host "ОШИБКА: $text" -ForegroundColor Red; exit 1 }

Step "Проверка Docker и системы"
docker info *> $null
if ($LASTEXITCODE -ne 0) { Fail "Docker не запущен. Запустите Docker Desktop и повторите." }

$state = (docker compose ps backend --format "{{.State}}" 2>$null | Out-String).Trim()
if ($state -ne "running") {
    Fail "Система не запущена. Сначала выполните: powershell -ExecutionPolicy Bypass -File scripts\setup.ps1 (папка: $root)"
}

# Ждём готовности backend (после запуска контейнера миграции и наполнение занимают до минуты)
$ready = $false
for ($i = 0; $i -lt 60; $i++) {
    $health = (docker compose ps backend --format "{{.Health}}" 2>$null | Out-String).Trim()
    if ($health -eq "healthy") { $ready = $true; break }
    Start-Sleep -Seconds 3
}
if (-not $ready) { Fail "Backend не стал готовым за 3 минуты. Проверьте: docker compose logs backend" }
Write-Host "Система работает."

Step "Заполнение учётной записи администратора (около 20 секунд)"
$seedArgs = @("--fill-admin")
if ($Demo) { $seedArgs += "--refresh-demo" }
# Через cmd: журнал Python пишется в stderr, а PowerShell 5.1 показал бы его красными «ошибками»
cmd.exe /c "docker compose exec -T backend python -m app.seed $($seedArgs -join ' ') 2>&1"
if ($LASTEXITCODE -ne 0) { Fail "Заполнение не удалось (см. вывод выше)." }

$port = "8080"
if (Test-Path ".env") {
    $line = Get-Content ".env" | Where-Object { $_ -match "^HTTP_PORT=" } | Select-Object -First 1
    if ($line) { $port = ($line -split "=", 2)[1].Trim() }
}

Write-Host ""
Write-Host "==================================================================" -ForegroundColor Green
Write-Host " Готово. Откройте http://localhost:$port" -ForegroundColor Green
Write-Host "==================================================================" -ForegroundColor Green
Write-Host " Администратор:  admin@grsn.local / Admin12345"
Write-Host "   профиль, замеры веса, набор продуктов, около 120 рецептов за 30 дней"
if ($Demo) { Write-Host " Демо-пользователь:  demo@grsn.local / Demo12345  (история пересоздана)" }
