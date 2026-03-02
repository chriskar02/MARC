# ───────────────────────────────────────────────────────────────
# MARC Launcher  -  starts backend (FastAPI) + frontend (Vite)
# Usage:  .\launch.ps1        (or right-click > Run with PowerShell)
# ───────────────────────────────────────────────────────────────

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Definition

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  MARC - MATEL Automated Robot Control"  -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# ── Backend ──────────────────────────────────────────────────
$backendDir    = Join-Path $root "backend"
$venvActivate  = Join-Path $backendDir ".venv\Scripts\Activate.ps1"

if (-not (Test-Path $venvActivate)) {
    Write-Host "[Backend] Creating virtual environment..." -ForegroundColor Yellow
    Push-Location $backendDir
    python -m venv .venv
    & $venvActivate
    pip install -r requirements.txt
    Pop-Location
}

# Write a small temp launcher so we avoid quoting issues with Start-Process
$backendLauncher = Join-Path $root ".run_backend.ps1"
@"
Set-Location "$backendDir"
& "$venvActivate"
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
"@ | Set-Content -Path $backendLauncher -Encoding UTF8

Write-Host "[Backend] Starting FastAPI on http://127.0.0.1:8000 ..." -ForegroundColor Green
$backendJob = Start-Process powershell -ArgumentList "-NoExit", "-File", $backendLauncher -PassThru

# ── Frontend ─────────────────────────────────────────────────
$frontendDir = Join-Path $root "frontend"
$nodeModules = Join-Path $frontendDir "node_modules"

if (-not (Test-Path $nodeModules)) {
    Write-Host "[Frontend] Installing npm packages..." -ForegroundColor Yellow
    Push-Location $frontendDir
    npm install
    Pop-Location
}

$frontendLauncher = Join-Path $root ".run_frontend.ps1"
@"
Set-Location "$frontendDir"
npm run dev
"@ | Set-Content -Path $frontendLauncher -Encoding UTF8

Write-Host "[Frontend] Starting Vite dev server on http://localhost:5173 ..." -ForegroundColor Green
$frontendJob = Start-Process powershell -ArgumentList "-NoExit", "-File", $frontendLauncher -PassThru

# ── Wait / Cleanup ───────────────────────────────────────────
Write-Host ""
Write-Host "Both servers are running." -ForegroundColor Cyan
Write-Host "  Backend  : http://127.0.0.1:8000" -ForegroundColor White
Write-Host "  Frontend : http://localhost:5173" -ForegroundColor White
Write-Host ""
Write-Host "Press Ctrl+C here (or close this window) to stop both." -ForegroundColor Yellow
Write-Host ""

try {
    # Keep this script alive so the user can Ctrl+C to kill everything
    while ($true) { Start-Sleep -Seconds 2 }
} finally {
    Write-Host "`nShutting down..." -ForegroundColor Red
    if ($backendJob  -and -not $backendJob.HasExited)  { Stop-Process -Id $backendJob.Id  -Force -ErrorAction SilentlyContinue }
    if ($frontendJob -and -not $frontendJob.HasExited) { Stop-Process -Id $frontendJob.Id -Force -ErrorAction SilentlyContinue }
    Write-Host "Done." -ForegroundColor Green
}
