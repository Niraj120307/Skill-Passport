# One-time setup for Windows PowerShell. Run from the skill-passport folder:  .\setup.ps1
$ErrorActionPreference = "Stop"
Write-Host "== Backend ==" -ForegroundColor Cyan
Set-Location backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
Set-Location ..
Write-Host "== Frontend ==" -ForegroundColor Cyan
Set-Location frontend
npm install
Set-Location ..
Write-Host "Setup complete. Start with .\start-backend.ps1 and .\start-frontend.ps1 (two terminals)." -ForegroundColor Green
