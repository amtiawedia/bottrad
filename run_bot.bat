@echo off
echo ========================================
echo   AlphaBot-Scalper V4 - Live Trading
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found! Please install Python 3.10+
    pause
    exit /b 1
)

REM Check if .env exists
if not exist .env (
    echo [ERROR] .env file not found!
    echo Please copy .env.example to .env and add your API keys
    pause
    exit /b 1
)

REM Install dependencies if needed
echo Installing dependencies...
pip install -r requirements.txt -q

echo.
echo Starting Bot in LIVE MODE...
echo Press Ctrl+C to stop
echo.

python alphabot_v4.py live --auto

pause
