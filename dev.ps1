# Windows PowerShell dev script
# Runs uvicorn in background or monitors with nodemon if installed

if (Test-Path ".\.venv\Scripts\activate.ps1") {
    & .\.venv\Scripts\Activate.ps1
}

$hasNodemon = Get-Command nodemon -ErrorAction SilentlyContinue

if (-not $hasNodemon) {
    Write-Host "[dev] nodemon not found. Install with: npm install -g nodemon"
    Write-Host "[dev] Starting uvicorn --reload only (manual browser refresh)..."
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
    exit
}

Write-Host "[dev] Starting uvicorn background process..."
$uvProcess = Start-Process -FilePath "uvicorn" -ArgumentList "app.main:app --reload --host 0.0.0.0 --port 8000" -PassThru

try {
    Write-Host "[dev] Starting nodemon file watcher for app/static..."
    nodemon --watch app/static --ext html,css,js --exec "python frontend/dev-reload.py trigger"
} finally {
    if ($uvProcess -and -not $uvProcess.HasExited) {
        Stop-Process -Id $uvProcess.Id -Force
    }
}

