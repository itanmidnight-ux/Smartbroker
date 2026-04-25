$ErrorActionPreference = "Stop"

if (-Not (Test-Path .\.venv\Scripts\Activate.ps1)) {
  throw "No existe entorno virtual. Ejecuta .\\install.ps1 primero."
}

.\.venv\Scripts\Activate.ps1
pip install pyinstaller
pyinstaller --onefile --name SmartBrokerAPI .\python\src\services\api.py
Write-Host "Ejecutable generado en .\\dist\\SmartBrokerAPI.exe"
