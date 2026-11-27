$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
if (-not (Test-Path '.venv\Scripts\python.exe')) {
    python -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Unable to create Python environment. Install Python 3.11 or later.' }
}
& .\.venv\Scripts\python.exe -m ensurepip --upgrade
if ($LASTEXITCODE -ne 0) { throw 'Unable to initialize pip.' }
& .\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
Write-Host 'Open http://127.0.0.1:8765 in your browser. Press Ctrl+C to stop.'
& .\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8765
