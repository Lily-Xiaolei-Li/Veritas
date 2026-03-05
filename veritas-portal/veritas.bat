@echo off
setlocal
cd /d "C:\Users\thene\projects\veritas-cli"
call .venv\Scripts\activate.bat
python main.py %*
endlocal
