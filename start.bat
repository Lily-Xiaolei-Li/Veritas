@echo off
title Agent-B Launcher

echo =============================================
echo           AGENT-B RESEARCH
echo =============================================
echo.

REM ============================================
REM STEP 0: Clean up using PowerShell script
REM ============================================
echo [0/4] Cleaning up old processes...
powershell -ExecutionPolicy Bypass -File "%~dp0cleanup.ps1"
echo.

REM ============================================
REM STEP 1: Start PostgreSQL
REM ============================================
echo [1/4] Checking PostgreSQL...
net start postgresql-x64-16 2>nul
if %errorlevel%==0 (
    echo      PostgreSQL started
) else (
    echo      PostgreSQL already running
)
echo.

REM ============================================
REM STEP 2: Start Backend
REM ============================================
echo [2/4] Starting Backend...
cd /d "%~dp0backend"
start "Agent-B Backend" cmd /k "call venv\Scripts\activate && python -m uvicorn app.main:app --reload --port 8001"
echo      Backend starting on http://localhost:8001
echo.

REM ============================================
REM STEP 3: Wait for backend
REM ============================================
echo [3/4] Waiting for backend to initialize...
timeout /t 5 /nobreak >nul
echo.

REM ============================================
REM STEP 4: Start Frontend
REM ============================================
echo [4/4] Starting Frontend...
cd /d "%~dp0frontend"
start "Agent-B Frontend" cmd /k "npm run dev -- -p 3011"
echo      Frontend starting on http://localhost:3011
echo.

echo =============================================
echo      Agent-B Research is starting up!
echo      Backend:  http://localhost:8001
echo      Frontend: http://localhost:3011
echo =============================================
echo.
echo Press any key to open the app in browser...
pause >nul

start http://localhost:3011
