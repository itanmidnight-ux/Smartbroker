$ErrorActionPreference = "Stop"

if (-Not (Test-Path .\.venv\Scripts\Activate.ps1)) {
  throw "No existe entorno virtual. Ejecuta .\install.ps1 primero."
}

.\.venv\Scripts\Activate.ps1

Write-Host "Iniciando SmartBroker API en localhost..."
python .\python\src\services\api.py
