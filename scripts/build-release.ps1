# BiziBox v2.1.0 — build-release.ps1
# Полный цикл сборки релиза: фронтенд → гейты → PyInstaller (portable exe).
# Запуск из корня репозитория:
#   powershell -ExecutionPolicy Bypass -File scripts\build-release.ps1
# Требования: Node.js 20+, Python 3.13 (backend\.venv), PyInstaller в venv.

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot

function Invoke-Step([string]$Name, [scriptblock]$Action) {
    Write-Host "=== $Name ===" -ForegroundColor Cyan
    & $Action
    if ($LASTEXITCODE -ne 0) { throw "Шаг '$Name' завершился с кодом $LASTEXITCODE" }
}

Invoke-Step "frontend: npm ci" {
    Push-Location "$RepoRoot\frontend"
    npm ci
    Pop-Location
}

Invoke-Step "frontend: npm run build" {
    Push-Location "$RepoRoot\frontend"
    npm run build
    Pop-Location
}

Invoke-Step "backend gates: ruff" {
    Push-Location "$RepoRoot\backend"
    & .\.venv\Scripts\python.exe -m ruff check app/
    Pop-Location
}

Invoke-Step "backend gates: mypy" {
    Push-Location $RepoRoot
    & .\backend\.venv\Scripts\python.exe -m mypy backend/
    Pop-Location
}

Invoke-Step "backend gates: pytest" {
    Push-Location "$RepoRoot\backend"
    & .\.venv\Scripts\python.exe -m pytest tests/ -q
    Pop-Location
}

Invoke-Step "frontend gates: lint + test" {
    Push-Location "$RepoRoot\frontend"
    npm run lint
    if ($LASTEXITCODE -ne 0) { throw "lint failed" }
    npm test
    Pop-Location
}

Invoke-Step "PyInstaller: BiziBox.spec" {
    Push-Location "$RepoRoot\backend"
    & .\.venv\Scripts\python.exe -m PyInstaller BiziBox.spec --noconfirm
    Pop-Location
}

Write-Host "Сборка завершена: $RepoRoot\backend\dist\BiziBox.exe" -ForegroundColor Green
