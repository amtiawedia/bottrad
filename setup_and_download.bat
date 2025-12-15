@echo off
chcp 65001 >nul
title Setup Bot - Download from GitHub

echo.
echo ╔═══════════════════════════════════════════════════════════════════╗
echo ║  📥 SETUP BOT - Download from GitHub                             ║
echo ╚═══════════════════════════════════════════════════════════════════╝
echo.

REM Create folder
if not exist "D:\AIBot" mkdir "D:\AIBot"
cd /d D:\AIBot

echo 📂 Working in: %CD%
echo.

REM Check Git
git --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Git not found! Installing via winget...
    winget install Git.Git
    echo.
    echo ⚠️  Please restart this script after Git installs.
    pause
    exit
)

echo ✅ Git found
echo.

REM Clone or Pull repo
if exist "bottrad" (
    echo 📂 Folder exists, pulling latest...
    cd bottrad
    git pull
) else (
    echo 📥 Cloning repository...
    git clone https://github.com/amtiawedia/bottrad.git
    cd bottrad
)

echo.
echo ✅ Download complete!
echo 📂 Location: D:\AIBot\bottrad
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python not found! Please install Python from:
    echo    https://www.python.org/downloads/
    echo.
    echo ⚠️  Remember to check "Add Python to PATH" during install!
    pause
    exit
)

echo ✅ Python found
echo.

REM Install packages
echo 📦 Installing required packages...
pip install ccxt pandas pandas_ta matplotlib requests aiohttp --quiet

echo.
echo ═══════════════════════════════════════════════════════════════════
echo ✅ SETUP COMPLETE!
echo ═══════════════════════════════════════════════════════════════════
echo.
echo 📁 Bot location: D:\AIBot\bottrad
echo.
echo 🚀 To run Paper Bot V5:
echo    Double-click: run_v5.bat
echo.
echo    Or in Command Prompt:
echo    cd D:\AIBot\bottrad
echo    python paper_bot_v5.py
echo.
echo ═══════════════════════════════════════════════════════════════════
echo.

pause
