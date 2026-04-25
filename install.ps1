Param(
  [string]$PythonExe = "python"
)

$ErrorActionPreference = "Stop"

Write-Host "[1/7] Verificando Python..."
& $PythonExe --version

Write-Host "[2/7] Creando entorno virtual..."
& $PythonExe -m venv .venv

Write-Host "[3/7] Activando entorno virtual..."
.\.venv\Scripts\Activate.ps1

Write-Host "[4/7] Instalando dependencias..."
pip install --upgrade pip
pip install -r .\python\requirements.txt

Write-Host "[5/7] Preparando carpetas de ejecución..."
New-Item -ItemType Directory -Force -Path .\logs\python | Out-Null
New-Item -ItemType Directory -Force -Path .\logs\mt5 | Out-Null
New-Item -ItemType Directory -Force -Path .\data\raw | Out-Null
New-Item -ItemType Directory -Force -Path .\data\processed | Out-Null
New-Item -ItemType Directory -Force -Path .\data | Out-Null

if (-Not (Test-Path .\.env)) {
  Copy-Item .\.env.example .\.env
  Write-Host "Archivo .env creado desde .env.example"
}

Write-Host "[6/7] Bootstrap rápido (agente + modelos base)..."
$env:PYTHONPATH = ".\python\src"
python .\python\tools\bootstrap_project.py

Write-Host "[7/7] Self-test del sistema..."
python .\python\tools\self_test.py

Write-Host "Instalación y configuración finalizadas."
