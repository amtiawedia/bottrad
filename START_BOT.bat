@echo off
chcp 65001 >nul
title AlphaBot-Scalper V4 - Live Trading
color 0A

echo.
echo  ╔══════════════════════════════════════════════════════════╗
echo  ║           AlphaBot-Scalper V4 - Live Trading             ║
echo  ║                   BTC/USDT Scalping                      ║
echo  ╚══════════════════════════════════════════════════════════╝
echo.

REM ===== CHECK PYTHON =====
python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python not found!
    echo  Please install Python from: https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)
echo  [OK] Python found

REM ===== CREATE .ENV IF NOT EXISTS =====
if not exist .env (
    echo  [INFO] Creating .env file...
    echo  [WARNING] Please edit .env file and add your API keys!
    (
        echo BINANCE_API_KEY=your_binance_api_key_here
        echo BINANCE_SECRET_KEY=your_binance_secret_key_here
        echo TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
        echo TELEGRAM_CHAT_ID=your_telegram_chat_id_here
        echo PERPLEXITY_API_KEY=your_perplexity_api_key_here
    ) > .env
    echo  [OK] .env template created
    echo.
    echo  ════════════════════════════════════════════════════════════
    echo   IMPORTANT: Edit .env file with your real API keys!
    echo  ════════════════════════════════════════════════════════════
    pause
    exit /b 1
)
echo  [OK] .env file ready

REM ===== INSTALL DEPENDENCIES =====
echo.
echo  [INFO] Installing dependencies...
pip install ccxt pandas pandas_ta python-dotenv matplotlib requests -q
echo  [OK] Dependencies installed

REM ===== START BOT =====
echo.
echo  ════════════════════════════════════════════════════════════
echo   Starting AlphaBot-Scalper V4 in LIVE MODE...
echo   Press Ctrl+C to stop
echo  ════════════════════════════════════════════════════════════
echo.

python alphabot_v4.py live --auto

echo.
echo  Bot stopped.
pause
