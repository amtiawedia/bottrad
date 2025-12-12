@echo off
title Backtest Tool
color 0B
cls

echo ╔══════════════════════════════════════════════════════════════════╗
echo ║          📊 BACKTEST TOOL - Test Strategy                        ║
echo ╚══════════════════════════════════════════════════════════════════╝
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python not found!
    pause
    exit /b 1
)

echo 🔬 Starting Backtest UI...
echo.

python backtester_ui.py

pause
