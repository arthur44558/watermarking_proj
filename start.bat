@echo off
setlocal enabledelayedexpansion

title JND-Guided Frequency-Domain Watermarking Web App

echo =====================================================================
echo  JND-Guided Frequency-Domain Image Watermarking Studio
echo  Python 3.14 + Flask + OpenCV DCT + Perceptual JND Engine
echo =====================================================================
echo.

cd /d "%~dp0"

:: 1. Check or initialize Python 3.14 virtual environment
if not exist ".venv\Scripts\python.exe" (
    echo [*] Initializing virtual environment with Python 3.14...
    py -3.14 -m venv .venv
    if errorlevel 1 (
        echo [!] Python 3.14 launcher failed. Attempting system python...
        python -m venv .venv
    )
)

:: 2. Activate virtual environment
if exist ".venv\Scripts\activate.bat" (
    echo [*] Activating Python 3.14 virtual environment...
    call .venv\Scripts\activate.bat
) else (
    echo [!] ERROR: Could not find virtual environment activation script.
    pause
    exit /b 1
)

:: 3. Verify and install dependencies
echo [*] Checking required dependencies...
.venv\Scripts\python.exe -m pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo [!] Warning: Some packages could not be installed. Check your network or pip.
)

:: 4. Ensure runtime directories exist
if not exist "uploads" mkdir uploads
if not exist "output" mkdir output

:: 5. Open browser in background after 2 seconds
echo [*] Launching web browser at http://localhost:5000 ...
start "" cmd /c "timeout /t 2 /nobreak >nul & start http://localhost:5000"

:: 6. Start the web application server
echo.
echo =====================================================================
echo  Server is listening on http://localhost:5000
echo  Press Ctrl+C in this window to stop the server.
echo =====================================================================
echo.

set PYTHONPATH=src
.venv\Scripts\python.exe src\web\app.py

if errorlevel 1 (
    echo.
    echo [!] Server exited with an error.
    pause
)
