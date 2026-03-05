@echo off
chcp 65001 >nul
cd /d "C:\Users\thene\projects\tt"
call .venv\Scripts\activate.bat
python welcome.py
prompt (TT) ❯$S
rem The next line is for interactive use only
rem cmd /k
