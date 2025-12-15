@echo off
chcp 65001 >nul
title Paper Bot V6 - Binance Style

echo.
echo ╔══════════════════════════════════════════════════════════════╗
echo ║        PAPER BOT V6 - BINANCE STYLE DISPLAY                  ║
echo ║        แสดงผลเหมือน Binance Futures จริง!                      ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.

cd /d D:\AIBot\bottrad

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found! Please install Python first.
    pause
    exit /b 1
)

REM Install packages if needed
echo [*] Checking packages...
pip show ccxt >nul 2>&1 || pip install ccxt pandas pandas_ta matplotlib aiohttp --quiet

echo.
echo [*] Starting Paper Bot V6...
echo [*] Press Ctrl+C to stop
echo.

python paper_bot_v6.py

pause
