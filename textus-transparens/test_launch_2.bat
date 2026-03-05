@echo off
cd /d "C:\Users\thene\projects\tt"
if exist .venv\Scripts\activate.bat (
    call .venv\Scripts\activate.bat
)
python welcome.py
