@echo off
title Kerala Election 2026 - Server Startup (AC1 Test Loop)
color 0A

echo.
echo =========================================
echo  Kerala Election 2026 - Starting Servers
echo  Mode: Bihar Test - AC1 Loop
echo =========================================
echo.

set ROOT=%~dp0
set BACKEND=%ROOT%backend
set FRONTEND=%ROOT%frontend

:: ── 1. Django Backend
echo [1/3] Starting Django backend on port 8001...
start "Django Backend" powershell -NoExit -Command "cd '%BACKEND%'; python manage.py runserver 8001"

timeout /t 6 /nobreak >nul

:: ── 2. Frontend (Vite)
echo [2/3] Starting Vite frontend on port 3000...
start "Vite Frontend" powershell -NoExit -Command "cd '%FRONTEND%'; npm run dev"

timeout /t 2 /nobreak >nul

:: ── 3. AC1 Bihar loop
echo [3/3] Starting AC1 test loop (Bihar)...
start "Scraper - AC1 Loop" powershell -NoExit -Command "cd '%BACKEND%'; python manage.py scrape_loop --ac 1 --test --loop"

echo.
echo =========================================
echo  Backend  : http://localhost:8001/admin/
echo  Frontend : http://localhost:3000/
echo  Scraper  : AC1 Bihar looping
echo =========================================
echo.
pause
