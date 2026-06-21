param(
  [switch]$SkipRootCopy
)

$ErrorActionPreference = "Stop"

function Assert-StepSuccess([string]$stepName) {
  if ($LASTEXITCODE -ne 0) {
    throw "$stepName завершился с ошибкой: $LASTEXITCODE"
  }
}

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$venvPath = Join-Path $projectRoot ".venv"
$venvPython = Join-Path $venvPath "Scripts\\python.exe"
$requirementsPath = Join-Path $projectRoot "requirements-build.txt"

if (-not (Test-Path $requirementsPath)) {
  $requirementsPath = Join-Path $projectRoot "requirements.txt"
}

if (-not (Test-Path $venvPython)) {
  Write-Host "Creating local virtual environment..."
  python -m venv $venvPath
  Assert-StepSuccess "Создание виртуального окружения"
}

Write-Host "Installing dependencies in .venv..."
& $venvPython -m pip install --upgrade pip
Assert-StepSuccess "Обновление pip"
& $venvPython -m pip install -r $requirementsPath
Assert-StepSuccess "Установка зависимостей"

Write-Host "Cleaning previous build artifacts..."
Remove-Item -LiteralPath (Join-Path $projectRoot "build") -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath (Join-Path $projectRoot "dist") -Recurse -Force -ErrorAction SilentlyContinue

$rootExe = Join-Path $projectRoot "FileOpener.exe"

Write-Host "Building one-file exe..."
& $venvPython -m PyInstaller `
  --noconfirm `
  --clean `
  --onefile `
  --windowed `
  --exclude-module PyQt6 `
  --exclude-module PyQt5 `
  --exclude-module PySide2 `
  --name FileOpener `
  (Join-Path $projectRoot "main.py")
Assert-StepSuccess "PyInstaller"

$distExe = Join-Path $projectRoot "dist\\FileOpener.exe"
if (-not (Test-Path $distExe)) {
  throw "Файл сборки не найден: $distExe"
}

Write-Host "Build completed:"
Write-Host " - $distExe"

if (-not $SkipRootCopy) {
  Copy-Item -LiteralPath $distExe -Destination $rootExe -Force
  Write-Host " - $rootExe"
}
