@echo off
chcp 65001 >nul
cd /d "C:\Users\thene\projects\tt"
if exist .venv\Scripts\activate.bat (
    call .venv\Scripts\activate.bat
)
python welcome.py
prompt (TT) $G$S
cmd /k
