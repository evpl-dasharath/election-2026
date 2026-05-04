Write-Host "Waiting for Django to start..." -ForegroundColor Yellow
Start-Sleep 6

Write-Host "Scraping Constituency 1 (Bihar test data)..." -ForegroundColor Cyan
Invoke-WebRequest -Uri "http://localhost:8001/api/scraper/run/" -Method POST `
    -ContentType "application/json" `
    -Body '{"ac_number":1,"test_mode":true}' `
    -UseBasicParsing | Select-Object -ExpandProperty Content

Write-Host ""
Write-Host "Done. Check Firebase RTDB console for /live/1" -ForegroundColor Green
Read-Host "Press Enter to close"
