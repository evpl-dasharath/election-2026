# Kerala Election 2026 — Production Deploy Script
# Usage: .\deploy.ps1
#
# Steps:
#   1. Exports full current DB state to JSON (meta, constituencies + VOTES, results/*, historical, parties)
#      These JSON files act as the live fallback cache — if RTDB goes down, users see last known data.
#   2. Builds the Vite frontend
#   3. Deploys to Firebase Hosting

param(
    [switch]$SkipJsonExport  # Pass -SkipJsonExport to skip step 1 (if backend is not running)
)

$ErrorActionPreference = "Stop"
$Root       = $PSScriptRoot
$BackendDir = Join-Path $Root 'backend'
$FrontendDir= Join-Path $Root 'frontend'
$DataDir    = Join-Path $FrontendDir 'public\data'

Write-Host ""
Write-Host "Kerala Election 2026 - Production Deploy" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# --- Step 1: Export full DB snapshot to JSON ----------------------------------
if (-not $SkipJsonExport) {
    Write-Host "[1/3] Exporting full DB snapshot to JSON (votes, status, candidates)..." -ForegroundColor Yellow

    # Verify backend is reachable
    try {
        $null = Invoke-WebRequest -Uri "http://localhost:8001/api/constituencies/?format=json&limit=1" -UseBasicParsing -TimeoutSec 5
    } catch {
        Write-Host "  ERROR: Django backend is not running on port 8001." -ForegroundColor Red
        Write-Host "  Start it with: python manage.py runserver 8001" -ForegroundColor Red
        Write-Host "  Or skip JSON export with: .\deploy.ps1 -SkipJsonExport" -ForegroundColor Yellow
        exit 1
    }

    # export_json writes: meta.json (with real tallies + generated_at), constituencies.json (with
    # status/leader/votes), results/NNN.json (per-constituency candidate details), historical.json,
    # history_all.json, parties.json.  These become the offline fallback when RTDB is unavailable.
    Set-Location $BackendDir
    python manage.py export_json --output "$DataDir"
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  ERROR: JSON export failed." -ForegroundColor Red
        exit 1
    }

    # Stamp generated_at into meta.json so the frontend can show how old the snapshot is
    $MetaPath = Join-Path $DataDir 'meta.json'
    $MetaObj  = Get-Content $MetaPath -Raw | ConvertFrom-Json
    $GeneratedAt = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    $MetaObj | Add-Member -NotePropertyName generated_at -NotePropertyValue $GeneratedAt -Force
    $MetaObj | ConvertTo-Json -Depth 10 -Compress | `
        ForEach-Object { [System.IO.File]::WriteAllText($MetaPath, $_, [System.Text.UTF8Encoding]::new($false)) }

    Write-Host "  JSON export OK (generated_at: $GeneratedAt)" -ForegroundColor Green
    Write-Host "  Fallback snapshot includes: meta, constituencies (with votes), results/*, historical, parties" -ForegroundColor DarkGray
} else {
    Write-Host "[1/3] Skipping JSON export (-SkipJsonExport flag set)." -ForegroundColor DarkGray
}

# ─── Step 2: Build frontend ───────────────────────────────────────────────────
Write-Host "[2/3] Building frontend (Vite production build)..." -ForegroundColor Yellow
Set-Location $FrontendDir
npm run build
if ($LASTEXITCODE -ne 0) {
    Write-Host "  ERROR: Vite build failed." -ForegroundColor Red
    exit 1
}
Write-Host "  Build OK." -ForegroundColor Green

# ─── Step 3: Deploy to Firebase Hosting ──────────────────────────────────────
Write-Host "[3/3] Deploying to Firebase Hosting..." -ForegroundColor Yellow
Set-Location $Root
# Use npx to resolve firebase-tools from the current user's npm global
# (avoids EPERM errors when the system 'firebase' cmd points to another user's AppData)
npx firebase deploy --only hosting
if ($LASTEXITCODE -ne 0) {
    Write-Host "  ERROR: Firebase deploy failed." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Deployment complete!" -ForegroundColor Green
Write-Host "  Primary: Firebase RTDB (live streaming)" -ForegroundColor DarkGray
Write-Host "  Fallback: Static JSON snapshot from $GeneratedAt" -ForegroundColor DarkGray
