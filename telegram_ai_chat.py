#!/usr/bin/env python3
"""
🤖 Telegram AI Chat Bot
พูดคุยกับ Perplexity AI ผ่าน Telegram
ถามเกี่ยวกับ BTC, ตลาด Crypto, หรืออะไรก็ได้!
"""

import requests
import time
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '')
PERPLEXITY_API_KEY = os.environ.get('PERPLEXITY_API_KEY', '')

# Perplexity AI Model - ฉลาดที่สุด!
PERPLEXITY_MODEL = "sonar-pro"  # Pro model - most intelligent

TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"
PERPLEXITY_API = "https://api.perplexity.ai/chat/completions"

# ═══════════════════════════════════════════════════════════════════════════════
# PERPLEXITY AI CHAT
# ═══════════════════════════════════════════════════════════════════════════════

def ask_perplexity(question: str) -> str:
    """ถาม Perplexity AI"""
    try:
        headers = {
            "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
            "Content-Type": "application/json"
        }
        
        # System prompt เพื่อให้ AI เข้าใจบริบท
        system_prompt = """คุณเป็น AI Assistant ผู้เชี่ยวชาญด้าน Cryptocurrency โดยเฉพาะ Bitcoin
คุณตอบเป็นภาษาไทย กระชับ ชัดเจน
ถ้าถูกถามเรื่องราคา ให้หาข้อมูล Real-time
ถ้าถูกถามเรื่องการเทรด ให้วิเคราะห์ Technical + Fundamental
ตอบสั้นกระชับ ไม่เกิน 200 คำ"""

        data = {
            "model": PERPLEXITY_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": question}
            ],
            "temperature": 0.7,
            "max_tokens": 500
        }
        
        response = requests.post(
            PERPLEXITY_API, 
            headers=headers, 
            json=data, 
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            answer = result['choices'][0]['message']['content']
            return answer
        else:
            return f"❌ API Error: {response.status_code}"
            
    except Exception as e:
        return f"❌ Error: {str(e)}"


# ═══════════════════════════════════════════════════════════════════════════════
# TELEGRAM BOT
# ═══════════════════════════════════════════════════════════════════════════════

def send_telegram_message(text: str, chat_id: str = None):
    """ส่งข้อความไป Telegram"""
    try:
        url = f"{TELEGRAM_API}/sendMessage"
        data = {
            "chat_id": chat_id or TELEGRAM_CHAT_ID,
            "text": text,
            "parse_mode": "HTML"
        }
        response = requests.post(url, data=data, timeout=10)
        return response.status_code == 200
    except Exception as e:
        print(f"Error sending message: {e}")
        return False


def get_updates(offset: int = None) -> list:
    """รับข้อความใหม่จาก Telegram"""
    try:
        url = f"{TELEGRAM_API}/getUpdates"
        params = {"timeout": 30}
        if offset:
            params["offset"] = offset
        
        response = requests.get(url, params=params, timeout=35)
        if response.status_code == 200:
            return response.json().get("result", [])
        return []
    except Exception as e:
        print(f"Error getting updates: {e}")
        return []


def process_message(message: dict):
    """ประมวลผลข้อความที่ได้รับ"""
    chat_id = message["chat"]["id"]
    text = message.get("text", "")
    user = message["from"].get("first_name", "User")
    
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {user}: {text}")
    
    # Commands
    if text.startswith("/"):
        handle_command(text, chat_id)
        return
    
    # ถ้าไม่ใช่ command ให้ถาม AI
    if text.strip():
        # ส่งข้อความว่ากำลังคิด
        send_telegram_message("🤔 กำลังคิด...", chat_id)
        
        # ถาม Perplexity AI
        answer = ask_perplexity(text)
        
        # ส่งคำตอบ
        response = f"🤖 <b>AI ตอบ:</b>\n\n{answer}"
        send_telegram_message(response, chat_id)
        
        print(f"[AI] {answer[:100]}...")


def handle_command(command: str, chat_id: str):
    """จัดการ Commands"""
    cmd = command.lower().split()[0]
    
    if cmd == "/start":
        msg = """🤖 <b>สวัสดี! ฉันคือ AI Trading Assistant</b>

ฉันใช้ Perplexity AI (Pro Model) ในการตอบคำถาม

📌 <b>สิ่งที่ทำได้:</b>
• ถามเกี่ยวกับ BTC, Crypto
• วิเคราะห์ตลาด
• ถามข่าวล่าสุด
• ถามอะไรก็ได้!

📝 <b>Commands:</b>
/btc - ราคา BTC ล่าสุด
/news - ข่าว Crypto วันนี้
/analyze - วิเคราะห์ตลาด
/status - สถานะบอท
/help - วิธีใช้งาน

💬 พิมพ์คำถามได้เลย!"""
        send_telegram_message(msg, chat_id)
    
    elif cmd == "/btc":
        send_telegram_message("🔍 กำลังดูราคา BTC...", chat_id)
        answer = ask_perplexity("ราคา Bitcoin ตอนนี้เท่าไหร่? ตอบสั้นๆ")
        send_telegram_message(f"💹 <b>BTC Price:</b>\n\n{answer}", chat_id)
    
    elif cmd == "/news":
        send_telegram_message("📰 กำลังหาข่าว...", chat_id)
        answer = ask_perplexity("ข่าว Bitcoin และ Crypto ที่สำคัญวันนี้มีอะไรบ้าง? สรุปสั้นๆ 3-5 ข้อ")
        send_telegram_message(f"📰 <b>Crypto News วันนี้:</b>\n\n{answer}", chat_id)
    
    elif cmd == "/analyze":
        send_telegram_message("📊 กำลังวิเคราะห์...", chat_id)
        answer = ask_perplexity("""วิเคราะห์ตลาด Bitcoin ตอนนี้:
1. ราคาปัจจุบัน
2. Trend ระยะสั้น (Bullish/Bearish/Sideways)
3. ปัจจัยสำคัญที่ต้องจับตา
4. ควรซื้อหรือขายหรือรอ?
ตอบสั้นกระชับ""")
        send_telegram_message(f"📊 <b>Market Analysis:</b>\n\n{answer}", chat_id)
    
    elif cmd == "/status":
        msg = f"""🤖 <b>Bot Status</b>

✅ AI Chat: Online
🧠 Model: Perplexity Pro (Most Intelligent)
🕐 Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

💬 พิมพ์คำถามได้เลย!"""
        send_telegram_message(msg, chat_id)
    
    elif cmd == "/help":
        msg = """📖 <b>วิธีใช้งาน</b>

<b>1. ถามตรงๆ:</b>
พิมพ์คำถามได้เลย เช่น
• "BTC จะขึ้นหรือลง?"
• "มีข่าวอะไรบ้างวันนี้?"
• "ควรเทรดตอนนี้ไหม?"

<b>2. Commands:</b>
/btc - ดูราคา BTC
/news - ข่าวล่าสุด
/analyze - วิเคราะห์ตลาด
/status - สถานะบอท

<b>3. หมายเหตุ:</b>
• AI อาจใช้เวลา 2-5 วินาทีในการตอบ
• คำตอบมาจาก Real-time search
• ไม่ใช่คำแนะนำการลงทุน!"""
        send_telegram_message(msg, chat_id)
    
    else:
        send_telegram_message("❓ ไม่รู้จัก command นี้\nพิมพ์ /help เพื่อดูวิธีใช้", chat_id)


def run_bot():
    """รัน Telegram Bot"""
    print("=" * 50)
    print("🤖 Telegram AI Chat Bot Started!")
    print(f"🧠 Model: {PERPLEXITY_MODEL}")
    print("=" * 50)
    
    # ส่งข้อความเริ่มต้น
    send_telegram_message("""🤖 <b>AI Chat Bot เริ่มทำงาน!</b>

🧠 Model: Perplexity Pro (ฉลาดที่สุด)
💬 พิมพ์คำถามได้เลย!

📝 พิมพ์ /help เพื่อดูวิธีใช้""")
    
    offset = None
    
    while True:
        try:
            updates = get_updates(offset)
            
            for update in updates:
                offset = update["update_id"] + 1
                
                if "message" in update:
                    message = update["message"]
                    # เฉพาะ chat ที่อนุญาต
                    if str(message["chat"]["id"]) == TELEGRAM_CHAT_ID:
                        process_message(message)
            
            time.sleep(1)
            
        except KeyboardInterrupt:
            print("\n👋 Bot stopped by user")
            send_telegram_message("👋 AI Chat Bot หยุดทำงานแล้ว")
            break
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(5)


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    run_bot()
