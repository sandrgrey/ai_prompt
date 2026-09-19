@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Run setup_windows.bat first.
    exit /b 1
)
call .venv\Scripts\activate.bat
python app.py
if errorlevel 1 (
    echo Application failed. See logs\app.log and README.md.
    pause
    exit /b 1
)
