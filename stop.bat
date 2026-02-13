@echo off
title Agent-B Stopper

echo =============================================
echo        STOPPING AGENT-B
echo =============================================
echo.

echo Stopping Agent-B processes...
powershell -ExecutionPolicy Bypass -File "%~dp0cleanup.ps1"

echo.
echo =============================================
echo        Agent-B stopped!
echo =============================================
echo.
pause
