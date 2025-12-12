@echo off
title AlphaBot V4 - Live Trading
color 0C
cls

echo ╔══════════════════════════════════════════════════════════════════╗
echo ║          🚀 ALPHABOT V4 - LIVE TRADING                           ║
echo ║                                                                  ║
echo ║  ⚠️  WARNING: ใช้เงินจริง! Real Money!                            ║
echo ║  ⚠️  ต้อง API Key มี Permission Futures                          ║
echo ╚══════════════════════════════════════════════════════════════════╝
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python not found! Please install Python 3.10+
    pause
    exit /b 1
)

REM Check if .env exists
if not exist ".env" (
    echo ❌ .env file not found!
    pause
    exit /b 1
)

echo ⚠️  คุณกำลังจะเทรดด้วยเงินจริง!
echo.
set /p confirm="พิมพ์ YES เพื่อยืนยัน: "
if /i not "%confirm%"=="YES" (
    echo ❌ Cancelled
    pause
    exit /b 0
)

echo.
echo 🚀 Starting AlphaBot V4 Live...
echo.

python alphabot_v4.py

pause
