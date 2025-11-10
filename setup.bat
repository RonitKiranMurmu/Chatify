@echo off
echo ╔═══════════════════════════════════════════╗
echo ║    Chatify - Quick Setup Script          ║
echo ╚═══════════════════════════════════════════╝
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH
    echo Please install Python 3.9+ from https://www.python.org/
    pause
    exit /b 1
)

echo [1/4] Checking Python installation...
python --version
echo.

REM Check if virtual environment exists
if not exist "venv" (
    echo [2/4] Creating virtual environment...
    python -m venv venv
    echo     Virtual environment created!
) else (
    echo [2/4] Virtual environment already exists
)
echo.

REM Activate virtual environment
echo [3/4] Activating virtual environment...
call venv\Scripts\activate.bat
echo.

REM Install dependencies
echo [4/4] Installing dependencies...
echo     This may take a few minutes...
pip install -r requirements.txt
echo.

echo ════════════════════════════════════════════
echo   Setup Complete! ✓
echo ════════════════════════════════════════════
echo.
echo Next steps:
echo   1. Make sure MongoDB is running
echo   2. Run: python app.py
echo   3. Open browser: http://localhost:5000
echo.
echo For MongoDB setup, see SETUP.md
echo.
pause
