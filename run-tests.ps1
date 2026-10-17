# Runs backend tests and a frontend type-check/build
Set-Location "$PSScriptRoot\backend"
.\.venv\Scripts\python.exe -m pytest -q
Set-Location "$PSScriptRoot\frontend"
npm run build
