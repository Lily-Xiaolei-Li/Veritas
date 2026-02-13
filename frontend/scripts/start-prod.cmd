@echo off
setlocal
set PORT=3011
if not "%1"=="" set PORT=%1
cd /d %~dp0\..
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\start-prod.ps1 -Port %PORT%
endlocal
