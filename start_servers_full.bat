@echo off
title Kerala Election 2026 - ELECTION DAY
color 0E

echo.
echo =========================================
echo  Kerala Election 2026 - ELECTION DAY
echo  Continuous scrape - All 140 seats
echo =========================================
echo.

set ROOT=%~dp0
set BACKEND=%ROOT%backend

:: ── 1. Django Backend
echo [1/2] Starting Django backend on port 8001...
start "Django Backend" powershell -NoExit -Command "cd '%BACKEND%'; python manage.py runserver 8001"

timeout /t 6 /nobreak >nul

:: ── 2. Scrape loop - Kerala LIVE - loops until all seats declared
echo [2/2] Starting scrape loop (Kerala live)...
start "Scraper - LIVE LOOP" powershell -NoExit -Command "cd '%BACKEND%'; python manage.py scrape_loop"

echo.
echo =========================================
echo  ELECTION DAY MODE ACTIVE
echo  Backend : http://localhost:8001/admin/
echo  Scraper : Looping - skips declared seats
echo.
echo  If a window crashes double-click this
echo  file again to restart everything
echo =========================================
echo.
pause
