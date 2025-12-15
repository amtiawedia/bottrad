@echo off
chcp 65001 >nul
title Paper Bot V5 - กำไร + เทรดเยอะ!

echo.
echo ╔═══════════════════════════════════════════════════════════════════╗
echo ║  🚀 PAPER BOT V5 - BEST: กำไร + เทรดเยอะ!                        ║
echo ║  📊 Backtest: 653 trades, 48.7%% WR, +290%% ROI                   ║
echo ║  ⚙️  SL 1.0%% / TP 1.2%% / ADX ^>= 20                              ║
echo ╚═══════════════════════════════════════════════════════════════════╝
echo.

cd /d D:\AIBot\bottrad

echo 📂 Folder: %CD%
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python not found! Please install Python first.
    pause
    exit
)

echo ✅ Python found
echo.

REM Check/Install packages
echo 📦 Checking packages...
pip install ccxt pandas pandas_ta matplotlib requests --quiet

echo.
echo 🚀 Starting Paper Bot V5...
echo ⚠️  Press Ctrl+C to stop
echo.

python paper_bot_v5.py

pause
