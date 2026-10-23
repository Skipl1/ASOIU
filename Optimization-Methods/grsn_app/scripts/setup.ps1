<#
.SYNOPSIS
  Установка и запуск АС ГРСН в Docker одной командой (Windows PowerShell 5.1+).

.DESCRIPTION
  1. проверяет Docker и при необходимости запускает Docker Desktop;
  2. создаёт файл .env: случайные пароль БД и секрет JWT, свободные порты;
  3. собирает и запускает контейнеры (docker compose up -d --build);
  4. ждёт готовности системы и открывает сайт в браузере.
  Повторный запуск безопасен: существующий .env и данные не затрагиваются.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File scripts\setup.ps1

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File scripts\setup.ps1 -GigaChatKey "<Authorization Key из developers.sber.ru>"

.PARAMETER GigaChatKey
  Ключ авторизации GigaChat. Без него рецепты составляет локальный генератор (всё остальное работает).
.PARAMETER Https
  Включить HTTPS с самоподписанным сертификатом (https://localhost:<порт>).
.PARAMETER NoBrowser
  Не открывать браузер по окончании.
.PARAMETER Reset
  Удалить контейнеры и ВСЕ данные (база, отчёты, копии) и установить заново.
#>
param(
    [string]$GigaChatKey = $env:GIGACHAT_CREDENTIALS,
    [switch]$Https,
    [switch]$NoBrowser,
    [switch]$Reset
)

# Ошибки нативных команд (docker) проверяем по коду возврата, а не исключениями
$ErrorActionPreference = "Continue"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

function Step([string]$text) { Write-Host ""; Write-Host "==> $text" -ForegroundColor Cyan }
function Fail([string]$text) { Write-Host ""; Write-Host "ОШИБКА: $text" -ForegroundColor Red; exit 1 }

function Get-ListeningPorts {
    try {
        return @([System.Net.NetworkInformation.IPGlobalProperties]::GetIPGlobalProperties().GetActiveTcpListeners() | ForEach-Object { $_.Port })
    } catch { return @() }
}

function Test-PortFree([int]$port) {
    # Список слушаемых портов: пробный слушатель на «всех адресах» ошибается, если порт уже занят на 127.0.0.1 (так делает Docker)
    if ((Get-ListeningPorts) -contains $port) { return $false }
    try {
        $listener = New-Object System.Net.Sockets.TcpListener([System.Net.IPAddress]::Any, $port)
        $listener.Start(); $listener.Stop(); return $true
    } catch { return $false }
}

function Get-FreePort([int]$start, [int[]]$exclude = @()) {
    for ($p = $start; $p -lt $start + 200; $p++) {
        if (($exclude -notcontains $p) -and (Test-PortFree $p)) { return $p }
    }
    Fail "Не найден свободный порт, начиная с $start."
}

function New-Secret([int]$length) {
    $chars = "abcdefghijkmnopqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    $bytes = New-Object byte[] $length
    [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
    -join ($bytes | ForEach-Object { $chars[$_ % $chars.Length] })
}

function Set-EnvValue([string]$text, [string]$key, [string]$value) {
    $pattern = "(?m)^" + [regex]::Escape($key) + "=.*$"
    $line = "$key=$value"
    if ($text -match $pattern) {
        return [regex]::Replace($text, $pattern, [System.Text.RegularExpressions.MatchEvaluator] { param($m) $line })
    }
    return $text.TrimEnd("`n") + "`n" + $line + "`n"
}

function Get-EnvValue([string]$text, [string]$key, [string]$default) {
    $m = [regex]::Match($text, "(?m)^" + [regex]::Escape($key) + "=(.*)$")
    if ($m.Success -and $m.Groups[1].Value.Trim()) { return $m.Groups[1].Value.Trim() }
    return $default
}

function Write-Utf8Lf([string]$path, [string]$text) {
    $clean = $text -replace "`r`n", "`n"
    [System.IO.File]::WriteAllText($path, $clean, (New-Object System.Text.UTF8Encoding($false)))
}

function Test-DockerReady { docker info *> $null; return ($LASTEXITCODE -eq 0) }

# ---------------------------------------------------------------- 1. Docker
Step "Проверка Docker"
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Fail ("Docker не найден. Установите Docker Desktop: https://www.docker.com/products/docker-desktop/ " +
          "(или: winget install -e --id Docker.DockerDesktop), перезагрузите компьютер и запустите скрипт снова.")
}
if (-not (Test-DockerReady)) {
    Write-Host "Docker не запущен, запускаю Docker Desktop..."
    $candidates = @(
        (Join-Path $env:ProgramFiles "Docker\Docker\Docker Desktop.exe"),
        (Join-Path $env:LOCALAPPDATA "Programs\DockerDesktop\Docker Desktop.exe")
    )
    $exe = $candidates | Where-Object { Test-Path $_ } | Select-Object -First 1
    if (-not $exe) { Fail "Docker Desktop не найден. Запустите его вручную, дождитесь «Engine running» и повторите." }
    Start-Process $exe
    $deadline = (Get-Date).AddMinutes(4)
    while (-not (Test-DockerReady)) {
        if ((Get-Date) -gt $deadline) { Fail "Docker не запустился за 4 минуты. Откройте Docker Desktop вручную и повторите." }
        Start-Sleep -Seconds 5; Write-Host -NoNewline "."
    }
    Write-Host ""
}
docker compose version *> $null
if ($LASTEXITCODE -ne 0) { Fail "Не найден плагин «docker compose». Обновите Docker Desktop до актуальной версии." }
Write-Host "Docker готов." -ForegroundColor Green

# ---------------------------------------------------------------- 2. Сброс (по запросу)
if ($Reset) {
    Step "Удаление контейнеров и данных (-Reset)"
    docker compose down -v --remove-orphans
}

# ---------------------------------------------------------------- 3. .env
Step "Настройка файла .env"
$envPath = Join-Path $root ".env"
if (Test-Path $envPath) {
    $envText = [System.IO.File]::ReadAllText($envPath, [System.Text.Encoding]::UTF8) -replace "`r`n", "`n"
    Write-Host ".env уже существует — секреты и порты сохранены."
} else {
    $examplePath = Join-Path $root ".env.example"
    if (-not (Test-Path $examplePath)) { Fail "Не найден .env.example. Запускайте скрипт из клона репозитория (папка grsn_app)." }
    $envText = [System.IO.File]::ReadAllText($examplePath, [System.Text.Encoding]::UTF8) -replace "`r`n", "`n"
    $http = Get-FreePort 8080
    $httpsPort = Get-FreePort 8443 @($http)
    $db = Get-FreePort 5432 @($http, $httpsPort)
    $envText = Set-EnvValue $envText "POSTGRES_PASSWORD" (New-Secret 24)
    $envText = Set-EnvValue $envText "JWT_SECRET" (New-Secret 64)
    $envText = Set-EnvValue $envText "APP_DB_PASSWORD" (New-Secret 24)
    $envText = Set-EnvValue $envText "HTTP_PORT" $http
    $envText = Set-EnvValue $envText "HTTPS_PORT" $httpsPort
    $envText = Set-EnvValue $envText "DB_PORT" $db
    Write-Host "Создан .env: случайные пароль БД и секрет JWT, порты: сайт $http, HTTPS $httpsPort, БД $db."
}
if ($GigaChatKey) {
    $envText = Set-EnvValue $envText "GIGACHAT_CREDENTIALS" $GigaChatKey.Trim()
    Write-Host "Ключ GigaChat записан в .env."
}
if ($Https) { $envText = Set-EnvValue $envText "ENABLE_HTTPS" "true" }
Write-Utf8Lf $envPath $envText

$httpPort = Get-EnvValue $envText "HTTP_PORT" "8080"
$httpsPort = Get-EnvValue $envText "HTTPS_PORT" "8443"
$useHttps = (Get-EnvValue $envText "ENABLE_HTTPS" "false") -eq "true"
$hasKey = [bool](Get-EnvValue $envText "GIGACHAT_CREDENTIALS" "")

# ---------------------------------------------------------------- 4. Сборка и запуск
Step "Сборка и запуск контейнеров (первый раз 5–15 минут: загружаются образы и зависимости)"
docker compose up -d --build
if ($LASTEXITCODE -ne 0) { Fail "docker compose up завершился с ошибкой (см. вывод выше). Частые причины: нет интернета, занят порт, мало места на диске." }

# ---------------------------------------------------------------- 5. Ожидание готовности
Step "Ожидание готовности системы"
$healthUrl = "http://localhost:$httpPort/api/v1/health"
$deadline = (Get-Date).AddMinutes(5)
$ready = $false
while ((Get-Date) -lt $deadline) {
    try {
        $r = Invoke-WebRequest -Uri $healthUrl -UseBasicParsing -TimeoutSec 5
        if ($r.StatusCode -eq 200) { $ready = $true; break }
    } catch { }
    Start-Sleep -Seconds 3; Write-Host -NoNewline "."
}
Write-Host ""
if (-not $ready) {
    docker compose ps
    docker compose logs --tail 40 backend
    Fail "Система не ответила за 5 минут. Журнал backend выведен выше."
}

# Проверка входа демо-пользователя
try {
    $body = '{"email":"demo@grsn.local","password":"Demo12345"}'
    $login = Invoke-WebRequest -Uri "http://localhost:$httpPort/api/v1/auth/login" -Method Post -Body $body -ContentType "application/json" -UseBasicParsing -TimeoutSec 20
    $loginOk = ($login.StatusCode -eq 200)
} catch { $loginOk = $false }

$siteUrl = "http://localhost:$httpPort"
if ($useHttps) { $siteUrl = "https://localhost:$httpsPort" }

Write-Host ""
Write-Host "==================================================================" -ForegroundColor Green
Write-Host " АС ГРСН запущена:  $siteUrl" -ForegroundColor Green
Write-Host "==================================================================" -ForegroundColor Green
Write-Host " Демо-пользователь:  demo@grsn.local   / Demo12345"
Write-Host " Администратор:      admin@grsn.local  / Admin12345"
Write-Host " Документация API:   http://localhost:$httpPort/api/docs"
if ($useHttps) { Write-Host " HTTPS самоподписанный: браузер предупредит — нажмите «Дополнительно» → «Перейти»." -ForegroundColor Yellow }
if (-not $hasKey) { Write-Host " Ключ GigaChat не задан: рецепты составляет локальный генератор (ключ: .env → GIGACHAT_CREDENTIALS)." -ForegroundColor Yellow }
if (-not $loginOk) { Write-Host " Внимание: вход демо-пользователя не подтверждён — проверьте журнал: docker compose logs backend" -ForegroundColor Yellow }
Write-Host ""
Write-Host " Остановить:  docker compose stop      Запустить снова:  docker compose up -d"
Write-Host " (команды docker compose выполняйте в папке: $root)"

if (-not $NoBrowser) { Start-Process $siteUrl }
exit 0
