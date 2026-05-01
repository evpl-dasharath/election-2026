# Kerala Election 2026 - Development Environment Starter
# Starts Django (port 8001) and Vite (port 3000) in separate windows

Write-Host 'Starting Development Environment...' -ForegroundColor Cyan

# Backend
Write-Host 'Starting Backend on http://localhost:8001 ...' -ForegroundColor Yellow
$BackendDir = Join-Path $PSScriptRoot 'backend'
Start-Process powershell -ArgumentList '-NoExit', '-Command', "cd '$BackendDir'; python manage.py runserver 8001"

# Frontend
Write-Host 'Starting Frontend on http://localhost:3000 ...' -ForegroundColor Yellow
$FrontendDir = Join-Path $PSScriptRoot 'frontend'
Start-Process powershell -ArgumentList '-NoExit', '-Command', "cd '$FrontendDir'; npm run dev"

Write-Host ''
Write-Host 'Both servers starting in separate windows.' -ForegroundColor Green
Write-Host '  Backend  : http://localhost:8001/admin/'
Write-Host '  Frontend : http://localhost:3000/'
