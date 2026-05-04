@echo off
echo Starting Election 2026 Servers...

REM Make sure we are in the backend directory
cd /d "%~dp0"

REM Activate conda or venv if you have one.
REM We assume the user has miniconda or venv configured.
REM If using a specific conda env: call conda activate election-env
REM If using venv: call venv\Scripts\activate

REM 1. Start Django server in a new window
start "Django Server" cmd /k "python manage.py runserver"

REM 2. Open browser to the admin panel or frontend
timeout /t 3 >nul
start http://localhost:5173
start http://localhost:8001/admin

echo Servers started in new windows.
