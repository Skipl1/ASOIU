<#
.SYNOPSIS
  Показывает ресурсы, выделенные контейнерам АС ГРСН (в сумме 2 ядра и 4 ГБ — минимальный сервер из ТЗ). Windows PowerShell 5.1+.

.DESCRIPTION
  Лимиты читаются из запущенных контейнеров (docker inspect), текущее потребление — из docker stats.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File scripts\show_limits.ps1
#>
$ErrorActionPreference = "Continue"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

function Fail([string]$text) { Write-Host ""; Write-Host "ОШИБКА: $text" -ForegroundColor Red; exit 1 }

$ids = @(docker compose ps -q 2>$null | Where-Object { $_ })
if ($ids.Count -eq 0) { Fail "Система не запущена. Сначала: powershell -ExecutionPolicy Bypass -File scripts\setup.ps1" }

$usage = @{}
foreach ($line in (docker stats --no-stream --format "{{.Name}}|{{.CPUPerc}}|{{.MemUsage}}" $ids)) {
    $p = $line -split "\|"
    $usage[$p[0]] = @{ Cpu = $p[1]; Mem = ($p[2] -split " / ")[0] }
}

$rows = @()
$totalCpu = 0.0
$totalMem = 0.0
foreach ($id in $ids) {
    $p = (docker inspect --format "{{.Name}}|{{.HostConfig.NanoCpus}}|{{.HostConfig.Memory}}" $id) -split "\|"
    $name = $p[0].TrimStart("/")
    $cpu = [double]$p[1] / 1e9
    $memMb = [double]$p[2] / 1MB
    $totalCpu += $cpu
    $totalMem += $memMb
    $rows += [pscustomobject]@{
        "Контейнер"          = $name
        "Лимит CPU, ядер"    = "{0:0.##}" -f $cpu
        "Лимит ОЗУ, МБ"      = "{0:0}" -f $memMb
        "Сейчас CPU"         = $usage[$name].Cpu
        "Сейчас ОЗУ"         = $usage[$name].Mem
    }
}

Write-Host ""
Write-Host "Ресурсы контейнеров АС ГРСН (лимиты из docker-compose.yml)" -ForegroundColor Cyan
$rows | Sort-Object "Контейнер" | Format-Table -AutoSize | Out-String -Width 200 | Write-Host

$totalGb = $totalMem / 1024
Write-Host ("Итого выделено системе: {0:0.##} ядра, {1:0.##} ГБ ОЗУ" -f $totalCpu, $totalGb) -ForegroundColor Cyan
Write-Host "Сейчас CPU: 100 % = одно полное ядро. ОЗУ «сейчас» — фактическое потребление в пределах лимита."
Write-Host "Наблюдать нагрузку вживую: docker stats   (столбец MEM USAGE / LIMIT показывает лимит памяти)"
