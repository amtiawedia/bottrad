@echo off
title Paper Trade Bot
color 0E

echo.
echo ╔══════════════════════════════════════════════════════════════╗
echo ║              📝 Paper Trade Bot - 30 Coins                  ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.

D:
cd /d "D:\AIBot\bottrad"

if not exist "D:\AIBot\bottrad" (
    echo ❌ ไม่พบ folder D:\AIBot\bottrad
    pause
    exit
)

echo 🚀 กำลังเริ่ม Paper Trade Bot...
echo.

python paper_bot_full.py

pause
