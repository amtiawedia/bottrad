@echo off
title Paper Trade Bot V2
color 0A
cls

echo.
echo  ╔═══════════════════════════════════════════════════════════╗
echo  ║          📝 PAPER TRADE BOT V2                            ║
echo  ╠═══════════════════════════════════════════════════════════╣
echo  ║  ✅ ไม่ใช้เงินจริง - Paper Trade                           ║
echo  ║  ✅ สแกน 30 เหรียญ Long + Short                           ║
echo  ║  ✅ Leverage 50x, SL 1.2%%, TP 5.0%%                        ║
echo  ╚═══════════════════════════════════════════════════════════╝
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python not found!
    echo    Download: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo 🚀 Starting Bot...
echo.
echo กด Ctrl+C เพื่อหยุด
echo.

python bot.py

pause
