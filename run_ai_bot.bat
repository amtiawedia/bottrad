@echo off
title AlphaBot AI - Real-time Chatbot
color 0A

echo.
echo ╔══════════════════════════════════════════════════════════════╗
echo ║            🤖 AlphaBot AI - Real-time Chatbot               ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.

REM เปลี่ยนไปที่ Drive D
D:
cd /d "D:\AIBot\bottrad"

REM ตรวจสอบว่ามี folder หรือไม่
if not exist "D:\AIBot\bottrad" (
    echo ❌ ไม่พบ folder D:\AIBot\bottrad
    echo.
    echo 📝 กรุณารันคำสั่งนี้ก่อน:
    echo    D:
    echo    mkdir D:\AIBot
    echo    cd D:\AIBot
    echo    git clone https://github.com/amtiawedia/bottrad.git
    echo.
    pause
    exit
)

REM ตรวจสอบว่ามี .env หรือไม่
if not exist ".env" (
    echo ❌ ไม่พบไฟล์ .env
    echo.
    echo 📝 กรุณาสร้างไฟล์ .env ใน D:\AIBot\bottrad
    echo.
    pause
    exit
)

echo ✅ พบ folder และ .env แล้ว
echo.
echo 🚀 กำลังเริ่ม AI Bot Real-time...
echo.

python ai_realtime_bot.py

pause
