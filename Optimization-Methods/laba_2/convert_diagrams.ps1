$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$drawio = "C:\Program Files\draw.io\draw.io.exe"
$mmdc = "C:\Users\kreck\AppData\Roaming\npm\mmdc.cmd"
$imagesDir = Join-Path $root 'images'
New-Item -ItemType Directory -Force -Path $imagesDir | Out-Null

$mermaidMap = @{
    'diagrams/C4/01_C4_Context_AS_GRSN.mmd'                               = 'c4-context.png'
    'diagrams/C4/02_C4_Container_AS_GRSN.mmd'                             = 'c4-container.png'
    'diagrams/C4/03_C4_Component_Backend_API.mmd'                         = 'c4-component.png'
    'diagrams/Posledovatelnost/01_Регистрация_и_авторизация.mmd'          = 'seq-auth.png'
    'diagrams/Posledovatelnost/02_Профиль_и_целевая_калорийность.mmd'     = 'seq-profile.png'
    'diagrams/Posledovatelnost/03_Управление_запретами_и_аллергенами.mmd' = 'seq-restrictions.png'
    'diagrams/Posledovatelnost/04_Каталог_и_доступные_ингредиенты.mmd'    = 'seq-ingredients.png'
    'diagrams/Posledovatelnost/05_Генерация_персонализированного_рецепта.mmd' = 'seq-generate.png'
    'diagrams/Posledovatelnost/06_История_рецептов_и_оценка.mmd'          = 'seq-history.png'
    'diagrams/Posledovatelnost/07_Отчёт_о_пищевой_ценности.mmd'           = 'seq-reports.png'
    'diagrams/Posledovatelnost/08_Анализ_соответствия_рациона_цели.mmd'   = 'seq-analysis.png'
    'diagrams/Posledovatelnost/09_Администрирование.mmd'                  = 'seq-admin.png'
}

$drawioMap = @{
    'diagrams/Модель_сущность-связь.drawio'                                       = 'data-er.png'
    'diagrams/Модель_структуры_интерфейса.drawio'                                  = 'ui-structure.png'
    'diagrams/Bd/Концептуальная_модель_данных_PostgreSQL.drawio'                  = 'data-conceptual.png'
    'diagrams/Bd/Логическая_модель_данных_PostgreSQL.drawio'                      = 'data-logical.png'
    'diagrams/To-Be/To-Be_Регистрация_и_авторизация_BPMN.drawio'                  = 'tobe-auth.png'
    'diagrams/To-Be/To-Be_Ведение_профиля_и_расчёт_целевой_калорийности_BPMN.drawio' = 'tobe-profile.png'
    'diagrams/To-Be/To-Be_Управление_запретами_и_аллергенами_BPMN.drawio'         = 'tobe-restrictions.png'
    'diagrams/To-Be/To-Be_Каталог_и_доступные_ингредиенты_BPMN.drawio'            = 'tobe-ingredients.png'
    'diagrams/To-Be/To-Be_Генерация_персонализированного_рецепта_BPMN.drawio'     = 'tobe-generate.png'
    'diagrams/To-Be/To-Be_История_рецептов_оценка.drawio'                          = 'tobe-history.png'
    'diagrams/To-Be/To-Be_Формирование_отчёта_о_пищевой_ценности_BPMN.drawio'     = 'tobe-reports.png'
    'diagrams/To-Be/To-Be_Анализ_соответствия_рациона_цели_BPMN.drawio'           = 'tobe-analysis.png'
    'diagrams/To-Be/To-Be_Администрирование_BPMN.drawio'                          = 'tobe-admin.png'
    'diagrams/Potoki/01_Регистрация_и_авторизация.drawio'                          = 'dfd-auth.png'
    'diagrams/Potoki/02_Профиль_и_целевая_калорийность.drawio'                     = 'dfd-profile.png'
    'diagrams/Potoki/03_Управление_запретами_и_аллергенами.drawio'                 = 'dfd-restrictions.png'
    'diagrams/Potoki/04_Каталог_и_доступные_ингредиенты.drawio'                    = 'dfd-ingredients.png'
    'diagrams/Potoki/05_Генерация_персонализированного_рецепта.drawio'             = 'dfd-generate.png'
    'diagrams/Potoki/06_История_рецептов_и_оценка.drawio'                          = 'dfd-history.png'
    'diagrams/Potoki/07_Отчёт_о_пищевой_ценности.drawio'                           = 'dfd-reports.png'
    'diagrams/Potoki/08_Анализ_соответствия_рациона_цели.drawio'                   = 'dfd-analysis.png'
    'diagrams/Potoki/09_Администрирование.drawio'                                  = 'dfd-admin.png'
}

$ok = 0; $fail = 0; $missing = @()

foreach ($entry in $mermaidMap.GetEnumerator()) {
    $src = Join-Path $root $entry.Key
    $dst = Join-Path $imagesDir $entry.Value
    if (-not (Test-Path -LiteralPath $src)) {
        Write-Host "MISSING SRC: $src" -ForegroundColor Yellow
        $missing += $src
        continue
    }
    Write-Host ("MMD -> {0}" -f $entry.Value) -ForegroundColor Cyan
    & $mmdc -i $src -o $dst -s 2 -b white --quiet 2>&1 | Out-Null
    if (Test-Path -LiteralPath $dst) { $ok++ } else { $fail++; Write-Host "  FAIL" -ForegroundColor Red }
}

foreach ($entry in $drawioMap.GetEnumerator()) {
    $src = Join-Path $root $entry.Key
    $dst = Join-Path $imagesDir $entry.Value
    if (-not (Test-Path -LiteralPath $src)) {
        Write-Host "MISSING SRC: $src" -ForegroundColor Yellow
        $missing += $src
        continue
    }
    Write-Host ("DRAWIO -> {0}" -f $entry.Value) -ForegroundColor Green
    & $drawio --export --format png --scale 2 --border 10 --output $dst $src 2>&1 | Out-Null
    if (Test-Path -LiteralPath $dst) { $ok++ } else { $fail++; Write-Host "  FAIL" -ForegroundColor Red }
}

Write-Host ("`nDONE. ok={0} fail={1} missing={2}" -f $ok, $fail, $missing.Count) -ForegroundColor Magenta
if ($missing.Count -gt 0) { $missing | ForEach-Object { Write-Host "  $_" } }
