@echo off
title Paper Trade Bot - Multi Coin
color 0A
cls

echo ╔══════════════════════════════════════════════════════════════════╗
echo ║          📝 PAPER TRADE BOT - Multi Coin Scanner                 ║
echo ║                                                                  ║
echo ║  ✅ ไม่ใช้เงินจริง (Paper Trade)                                   ║
echo ║  ✅ สแกน 30 เหรียญ ทั้ง Long และ Short                            ║
echo ║  ✅ Leverage 50x, SL 1.2%%, TP 5.0%%                               ║
echo ╚══════════════════════════════════════════════════════════════════╝
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python not found! Please install Python 3.10+
    echo    Download from: https://www.python.org/downloads/
    pause
    exit /b 1
)

REM Check if .env exists
if not exist ".env" (
    echo ⚠️  .env file not found!
    echo    Please create .env file with your API keys.
    echo.
    echo    Copy .env.example to .env and fill in your keys.
    pause
    exit /b 1
)

echo 🚀 Starting Paper Trade Bot...
echo.
echo กด Ctrl+C เพื่อหยุด
echo.

python bots/paper_trade_bot.py

pause
