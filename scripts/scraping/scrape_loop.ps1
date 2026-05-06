param(
    [switch]$TestMode,
    [int]$CooldownSecs = 10
)

$BaseUrl = "http://localhost:8001/api/scraper"
$BodyAll = if ($TestMode) { '{"ac_number":"all","test_mode":true}' } else { '{"ac_number":"all","test_mode":false}' }
$Mode    = if ($TestMode) { "BIHAR TEST" } else { "KERALA LIVE" }

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host " Kerala Election 2026 - Continuous Scrape" -ForegroundColor Cyan
Write-Host " Mode: $Mode" -ForegroundColor Cyan
Write-Host " Cooldown: $CooldownSecs sec between cycles" -ForegroundColor Cyan
Write-Host " Press Ctrl+C to stop" -ForegroundColor Yellow
Write-Host "=========================================" -ForegroundColor Cyan

Write-Host "Waiting for Django..." -ForegroundColor Yellow
Start-Sleep 6

$cycle = 0

while ($true) {
    $cycle++
    $startTime = Get-Date
    Write-Host ""
    Write-Host "--- Cycle $cycle started at $($startTime.ToString('HH:mm:ss')) ---" -ForegroundColor Magenta

    try {
        Invoke-WebRequest -Uri "$BaseUrl/run/" -Method POST -ContentType "application/json" -Body $BodyAll -UseBasicParsing | Out-Null
        Write-Host "  Scrape triggered - 6 browsers running..." -ForegroundColor Yellow
    } catch {
        Write-Host "  ERROR: $_" -ForegroundColor Red
        Write-Host "  Retrying in 30s..." -ForegroundColor Yellow
        Start-Sleep 30
        continue
    }

    Start-Sleep 10

    $prevCommitted = 0
    $stallCount = 0
    $maxStall = 20
    $polling = $true

    while ($polling) {
        Start-Sleep 15

        try {
            $raw = Invoke-WebRequest -Uri "$BaseUrl/status/" -UseBasicParsing | Select-Object -ExpandProperty Content
            $status = $raw | ConvertFrom-Json
            $committed = $status.committed
            $total = $status.total
            $elapsed = ((Get-Date) - $startTime).ToString('mm\:ss')
            Write-Host "  [$elapsed] Committed: $committed / $total" -ForegroundColor Gray

            if ($committed -eq $total) {
                Write-Host "  All $total done" -ForegroundColor Green
                $polling = $false
            } elseif ($committed -eq $prevCommitted) {
                $stallCount++
                if ($stallCount -ge $maxStall) {
                    Write-Host "  No progress for 5 min - moving on" -ForegroundColor Yellow
                    $polling = $false
                }
            } else {
                $stallCount = 0
            }

            $prevCommitted = $committed
        } catch {
            Write-Host "  WARNING: status check failed - $_" -ForegroundColor Yellow
        }
    }

    $elapsed = ((Get-Date) - $startTime).ToString('mm\:ss')
    Write-Host "  Cycle $cycle done in $elapsed" -ForegroundColor Cyan
    Write-Host "  Cooldown $CooldownSecs sec..." -ForegroundColor Gray
    Start-Sleep $CooldownSecs
}
