<#
.SYNOPSIS
  Скачивает и готовит старые браузеры для проверки совместимости АС ГРСН (ТЗ 4.4): Chromium 90 и Firefox 88.

.DESCRIPTION
  Браузеры не хранятся в git (файлы больше 100 МБ GitHub не принимает), поэтому на новом компьютере их
  нужно скачать этим скриптом. Источники официальные:
    Chromium 90.0.4430.0 — снапшот 857947 из chromium-browser-snapshots (Google);
    Firefox 88.0 (ru)    — ftp.mozilla.org, подпись Mozilla проверяется перед распаковкой.
  Результат — те же папки, что ожидают Chromium 90.bat и Firefox 88.bat:
    chromium90\chrome-win\chrome.exe, firefox88\core\firefox.exe, profiles\chromium90, profiles\firefox88.
  Автообновление Firefox отключено (firefox88\core\distribution\policies.json), у Chromium-снапшота его нет.
  Повторный запуск безопасен: уже установленные браузеры пропускаются (ключ -Force — переустановить).

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File brouser\install_browsers.ps1
#>
param(
    [switch]$Force
)

$ErrorActionPreference = "Stop"
$D = $PSScriptRoot
$downloads = Join-Path $D "_downloads"
$tar = Join-Path $env:SystemRoot "System32\tar.exe"
$chromeUrl = "https://storage.googleapis.com/chromium-browser-snapshots/Win_x64/857947/chrome-win.zip"
$firefoxUrl = "https://ftp.mozilla.org/pub/firefox/releases/88.0/win64/ru/Firefox%20Setup%2088.0.exe"

function Step([string]$text) { Write-Host ""; Write-Host "==> $text" -ForegroundColor Cyan }

if (-not (Test-Path $tar)) { throw "Не найден $tar (нужна Windows 10 1803 или новее)." }
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$ProgressPreference = "SilentlyContinue"   # без индикатора загрузка в PowerShell 5.1 идёт в разы быстрее
New-Item -ItemType Directory -Force $downloads | Out-Null

# ------------------------------------------------------------------ Chromium 90
$chromeExe = Join-Path $D "chromium90\chrome-win\chrome.exe"
if ((Test-Path $chromeExe) -and -not $Force) {
    Step "Chromium 90 уже установлен — пропуск"
} else {
    Step "Chromium 90: загрузка (~150 МБ)"
    $zip = Join-Path $downloads "chrome-win.zip"
    Invoke-WebRequest -Uri $chromeUrl -OutFile $zip -UseBasicParsing
    if (Test-Path (Join-Path $D "chromium90")) { Remove-Item -Recurse -Force (Join-Path $D "chromium90") }
    New-Item -ItemType Directory -Force (Join-Path $D "chromium90") | Out-Null
    & $tar -xf $zip -C (Join-Path $D "chromium90")
    if (-not (Test-Path $chromeExe)) { throw "Chromium не распакован" }
    Write-Host ("Chromium: версия " + (Get-Item $chromeExe).VersionInfo.ProductVersion) -ForegroundColor Green
}

# ------------------------------------------------------------------ Firefox 88
$firefoxExe = Join-Path $D "firefox88\core\firefox.exe"
if ((Test-Path $firefoxExe) -and -not $Force) {
    Step "Firefox 88 уже установлен — пропуск"
} else {
    Step "Firefox 88: загрузка (~55 МБ)"
    $setup = Join-Path $downloads "Firefox Setup 88.0.exe"
    Invoke-WebRequest -Uri $firefoxUrl -OutFile $setup -UseBasicParsing
    $sig = Get-AuthenticodeSignature $setup
    if ($sig.Status -ne "Valid" -or $sig.SignerCertificate.Subject -notmatch "Mozilla") {
        throw "Подпись установщика Firefox не подтверждена ($($sig.Status)) — файл не распакован."
    }
    if (Test-Path (Join-Path $D "firefox88")) { Remove-Item -Recurse -Force (Join-Path $D "firefox88") }
    New-Item -ItemType Directory -Force (Join-Path $D "firefox88") | Out-Null
    & $tar -xf $setup -C (Join-Path $D "firefox88")   # установщик — 7z-архив, распаковка без установки в систему
    if (-not (Test-Path $firefoxExe)) { throw "Firefox не распакован" }
    $ver = (Get-Content (Join-Path $D "firefox88\core\application.ini") | Where-Object { $_ -match '^Version=' }) -join ""
    Write-Host "Firefox: $ver" -ForegroundColor Green
}

# ------------------------------------------------------------------ Настройка
Step "Отключение автообновления Firefox и профили"
$utf8 = New-Object System.Text.UTF8Encoding $false
New-Item -ItemType Directory -Force (Join-Path $D "firefox88\core\distribution"), (Join-Path $D "profiles\chromium90"), (Join-Path $D "profiles\firefox88") | Out-Null
[IO.File]::WriteAllText((Join-Path $D "firefox88\core\distribution\policies.json"),
    '{"policies": {"DisableAppUpdate": true, "DontCheckDefaultBrowser": true}}', $utf8)

Remove-Item -Recurse -Force $downloads
Write-Host ""
Write-Host "Готово. Запуск: «Chromium 90.bat» и «Firefox 88.bat» в этой папке (открывают http://localhost:8080)." -ForegroundColor Green
Write-Host "Для другого адреса откройте .bat в Блокноте и замените адрес в конце строки." -ForegroundColor Green
