@echo off
setlocal
cd /d "%~dp0"
echo Image to Prompt - Windows setup
echo Python 3.11 and current NVIDIA driver are recommended.
if exist ".venv\Scripts\python.exe" goto check_venv
py -3.11 -c "import sys; assert sys.version_info[:2] == (3,11)" >nul 2>&1
if not errorlevel 1 (
    py -3.11 -m venv .venv
    if errorlevel 1 goto failed
    goto check_venv
)
python -c "import sys; assert sys.version_info[:2] == (3,11)" >nul 2>&1
if not errorlevel 1 (
    python -m venv .venv
    if errorlevel 1 goto failed
    goto check_venv
)
echo Python 3.11 was not found. Install it from python.org and enable the Python launcher.
echo Then run setup_windows.bat again. See README.md for the uv alternative.
exit /b 1

:check_venv
".venv\Scripts\python.exe" -c "import sys; assert sys.version_info[:2] == (3,11), 'This project needs Python 3.11'"
if errorlevel 1 goto failed
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
if errorlevel 1 goto failed
if not defined TORCH_INDEX_URL set "TORCH_INDEX_URL=https://download.pytorch.org/whl/cu126"
python -m pip install torch==2.10.0 --index-url "%TORCH_INDEX_URL%"
if errorlevel 1 goto failed
python -m pip install -r requirements.txt
if errorlevel 1 goto failed
python -m pip install -r requirements-4bit.txt
if errorlevel 1 echo WARNING: bitsandbytes is unavailable; AUTO will use BF16 or CPU.
if not exist .env copy /y .env.example .env >nul
python -m pip check
if errorlevel 1 goto failed
python scripts\check_gpu.py
if errorlevel 1 goto failed
echo.
echo Setup complete. Next steps:
echo 1. Install and start Ollama from https://ollama.com/download/windows
echo 2. Run: ollama pull qwen3:4b
echo 3. Optional preload: .venv\Scripts\python.exe scripts\download_model.py
echo 4. Run start.bat and open http://127.0.0.1:7860
echo JoyCaption downloads on first analysis if not preloaded. Reserve 20 GB for model cache.
exit /b 0

:failed
echo.
echo Setup failed. Read the error above and README.md Troubleshooting.
echo No drivers or CUDA Toolkit were installed by this script.
exit /b 1
