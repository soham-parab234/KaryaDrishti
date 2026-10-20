$ErrorActionPreference = "Stop"

# Resolve the project root from this script's location
$ProjectRoot = $PSScriptRoot
$BackendPython = Join-Path $ProjectRoot "backend\.venv\Scripts\python.exe"
$FrontendFolder = Join-Path $ProjectRoot "frontend"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   LMIS Forecasting Engine Launcher" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Validate the required files and folders
if (-not (Test-Path $BackendPython)) {
    Write-Host "ERROR: Backend Python environment not found:" -ForegroundColor Red
    Write-Host $BackendPython
    Write-Host "Check whether backend\.venv exists."
    Read-Host "Press Enter to exit"
    exit 1
}

if (-not (Test-Path (Join-Path $FrontendFolder "package.json"))) {
    Write-Host "ERROR: Frontend package.json not found." -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# Check whether the frontend dependencies are installed
if (-not (Test-Path (Join-Path $FrontendFolder "node_modules"))) {
    Write-Host "ERROR: Frontend dependencies are missing." -ForegroundColor Red
    Write-Host "Open a terminal in the frontend folder and run npm install."
    Read-Host "Press Enter to exit"
    exit 1
}

# Start the backend in its own terminal.
# PYTHONPATH points to the project root so that
# imports beginning with "backend.app..." resolve correctly.
$BackendCommand = @'
Set-Location -LiteralPath "__ROOT__"
$env:PYTHONPATH = "__ROOT__"
& "__PYTHON__" -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
if ($LASTEXITCODE -ne 0) {
    Write-Host "Backend stopped with an error." -ForegroundColor Red
}
'@

$BackendCommand = $BackendCommand.Replace("__ROOT__", $ProjectRoot)
$BackendCommand = $BackendCommand.Replace("__PYTHON__", $BackendPython)

# Start the frontend in its own terminal.
$FrontendCommand = @'
Set-Location -LiteralPath "__FRONTEND__"
npm run dev
'@

$FrontendCommand = $FrontendCommand.Replace("__FRONTEND__", $FrontendFolder)

Write-Host "Starting backend..." -ForegroundColor Yellow

Start-Process powershell.exe -ArgumentList @(
    "-NoExit",
    "-ExecutionPolicy", "Bypass",
    "-Command", $BackendCommand
)

Start-Sleep -Seconds 2

Write-Host "Starting frontend..." -ForegroundColor Yellow

Start-Process powershell.exe -ArgumentList @(
    "-NoExit",
    "-ExecutionPolicy", "Bypass",
    "-Command", $FrontendCommand
)

Write-Host ""
Write-Host "Startup commands launched." -ForegroundColor Green
Write-Host "Frontend: http://localhost:5173/" -ForegroundColor Cyan
Write-Host "Backend:  http://127.0.0.1:8000/docs" -ForegroundColor Cyan
Write-Host ""
Write-Host "Keep both terminal windows open while using LMIS."