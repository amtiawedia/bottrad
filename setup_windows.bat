@echo off
title Setup AIBot
color 0B

echo.
echo ╔══════════════════════════════════════════════════════════════╗
echo ║              🔧 Setup AIBot - First Time                    ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.

REM สร้าง folder
echo 📁 สร้าง folder D:\AIBot...
D:
if not exist "D:\AIBot" mkdir "D:\AIBot"
cd /d "D:\AIBot"

REM Clone repo
echo.
echo 📥 กำลัง Clone repository...
if exist "bottrad" (
    echo ⚠️  folder bottrad มีอยู่แล้ว - กำลัง pull update...
    cd bottrad
    git pull
) else (
    git clone https://github.com/amtiawedia/bottrad.git
    cd bottrad
)

REM Install dependencies
echo.
echo 📦 กำลังติดตั้ง Python packages...
pip install python-dotenv aiohttp ccxt pandas pandas_ta requests matplotlib

REM สร้าง .env ถ้ายังไม่มี
if not exist ".env" (
    echo.
    echo 📝 สร้างไฟล์ .env...
    (
        echo # Telegram Bot ^(AI Chatbot^)
        echo AI_BOT_TOKEN=YOUR_AI_BOT_TOKEN_HERE
        echo.
        echo # Groq API ^(Llama - ฟรี!^)
        echo GROQ_API_KEY=YOUR_GROQ_API_KEY_HERE
        echo.
        echo # Perplexity API ^(Web Search Real-time^)
        echo PERPLEXITY_API_KEY=YOUR_PERPLEXITY_API_KEY_HERE
        echo.
        echo # Telegram Bot ^(Trading^)
        echo TELEGRAM_BOT_TOKEN=YOUR_TELEGRAM_BOT_TOKEN_HERE
        echo TELEGRAM_CHAT_ID=YOUR_CHAT_ID_HERE
        echo.
        echo # Binance API
        echo BINANCE_API_KEY=YOUR_BINANCE_API_KEY_HERE
        echo BINANCE_SECRET_KEY=YOUR_BINANCE_SECRET_KEY_HERE
    ) > .env
    echo ✅ สร้าง .env เรียบร้อย!
    echo.
    echo ⚠️  กรุณาแก้ไข .env ใส่ API Keys จริง!
    echo    เปิดไฟล์: D:\AIBot\bottrad\.env
    echo.
) else (
    echo ✅ มี .env อยู่แล้ว
)

echo.
echo ╔══════════════════════════════════════════════════════════════╗
echo ║                    ✅ Setup เสร็จสิ้น!                       ║
echo ╠══════════════════════════════════════════════════════════════╣
echo ║  📁 Location: D:\AIBot\bottrad                              ║
echo ║                                                              ║
echo ║  🚀 วิธีรัน:                                                 ║
echo ║     - AI Bot:      ดับเบิ้ลคลิก run_ai_bot.bat              ║
echo ║     - Paper Bot:   ดับเบิ้ลคลิก run_paper_bot.bat           ║
echo ║                                                              ║
echo ║  หรือพิมพ์:                                                  ║
echo ║     python ai_realtime_bot.py                               ║
echo ║     python paper_bot_full.py                                ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.

pause
