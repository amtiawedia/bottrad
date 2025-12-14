#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                     🤖 TELEGRAM AI CHATBOT                                   ║
║              ใช้ Llama 4 Maverick ผ่าน Groq API (ฟรี!)                        ║
║              ตอบโต้สนทนาได้ทุกเรื่อง 24/7                                      ║
╚══════════════════════════════════════════════════════════════════════════════╝

วิธีใช้:
1. ไปสร้าง Groq API Key ฟรีที่: https://console.groq.com
2. ใส่ GROQ_API_KEY ใน .env
3. รัน: python telegram_ai_bot.py

Features:
- 💬 ตอบทุกคำถาม (ภาษาไทย/อังกฤษ)
- 🧠 จำบทสนทนาได้ (context memory)
- ⚡ ตอบเร็วมาก (Groq = เร็วที่สุดในโลก)
- 🆓 ฟรี 100%!
"""

import os
import json
import asyncio
import aiohttp
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

# Telegram
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '')

# Groq API (ฟรี!) - สมัครได้ที่ https://console.groq.com
GROQ_API_KEY = os.environ.get('GROQ_API_KEY', '')
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

# Model - Llama 4 Maverick หรือ alternatives
# GROQ_MODEL = "meta-llama/llama-4-maverick-17b-128e-instruct"  # Llama 4 (ถ้ามี)
GROQ_MODEL = "llama-3.3-70b-versatile"  # Llama 3.3 70B (ใช้ได้เลย, ดีมาก!)
# GROQ_MODEL = "llama-3.1-8b-instant"  # เล็กกว่า เร็วกว่า
# GROQ_MODEL = "mixtral-8x7b-32768"  # Mixtral

# Bot Personality
BOT_NAME = "AlphaBot AI"
BOT_PERSONALITY = """คุณคือ AlphaBot AI ผู้ช่วยอัจฉริยะที่:
- ตอบคำถามได้ทุกเรื่อง ทั้งภาษาไทยและอังกฤษ
- เชี่ยวชาญเรื่อง Crypto, Trading, การลงทุน
- ให้คำแนะนำที่เป็นประโยชน์และตรงประเด็น
- มีอารมณ์ขัน เป็นกันเอง แต่ professional
- ตอบสั้นกระชับ ไม่เยิ่นเย้อ
- ใช้ emoji ให้เหมาะสม 😊

สิ่งที่คุณทำได้:
- ตอบคำถามทั่วไป
- วิเคราะห์ตลาด Crypto
- ให้คำแนะนำการเทรด (ไม่ใช่คำแนะนำทางการเงิน)
- ช่วยเขียนโค้ด
- แปลภาษา
- และอื่นๆ อีกมากมาย!

หมายเหตุ: คุณเป็นส่วนหนึ่งของ Trading Bot ที่ช่วยวิเคราะห์ตลาด"""

# Memory settings
MAX_CONTEXT_MESSAGES = 20  # จำบทสนทนาล่าสุดกี่ข้อความ
CONVERSATION_FILE = "conversation_history.json"

# ═══════════════════════════════════════════════════════════════════════════════
# CONVERSATION MEMORY
# ═══════════════════════════════════════════════════════════════════════════════

class ConversationMemory:
    """จัดการหน่วยความจำบทสนทนา"""
    
    def __init__(self):
        self.history = {}  # chat_id -> list of messages
        self.load_history()
    
    def load_history(self):
        """โหลดประวัติจากไฟล์"""
        try:
            if os.path.exists(CONVERSATION_FILE):
                with open(CONVERSATION_FILE, 'r', encoding='utf-8') as f:
                    self.history = json.load(f)
                print(f"📂 โหลดประวัติสนทนา: {len(self.history)} chats")
        except Exception as e:
            print(f"⚠️ ไม่สามารถโหลดประวัติ: {e}")
            self.history = {}
    
    def save_history(self):
        """บันทึกประวัติลงไฟล์"""
        try:
            with open(CONVERSATION_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"⚠️ ไม่สามารถบันทึกประวัติ: {e}")
    
    def add_message(self, chat_id: str, role: str, content: str):
        """เพิ่มข้อความลงประวัติ"""
        chat_id = str(chat_id)
        if chat_id not in self.history:
            self.history[chat_id] = []
        
        self.history[chat_id].append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
        
        # จำกัดจำนวนข้อความ
        if len(self.history[chat_id]) > MAX_CONTEXT_MESSAGES * 2:
            self.history[chat_id] = self.history[chat_id][-MAX_CONTEXT_MESSAGES * 2:]
        
        self.save_history()
    
    def get_context(self, chat_id: str) -> list:
        """ดึง context สำหรับ AI"""
        chat_id = str(chat_id)
        messages = [{"role": "system", "content": BOT_PERSONALITY}]
        
        if chat_id in self.history:
            for msg in self.history[chat_id][-MAX_CONTEXT_MESSAGES:]:
                messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
        
        return messages
    
    def clear_history(self, chat_id: str):
        """ล้างประวัติ"""
        chat_id = str(chat_id)
        if chat_id in self.history:
            del self.history[chat_id]
            self.save_history()

# ═══════════════════════════════════════════════════════════════════════════════
# GROQ AI CLIENT (Llama 4)
# ═══════════════════════════════════════════════════════════════════════════════

class GroqAI:
    """เรียก Llama 4 ผ่าน Groq API"""
    
    def __init__(self):
        self.api_key = GROQ_API_KEY
        self.api_url = GROQ_API_URL
        self.model = GROQ_MODEL
        
        if not self.api_key:
            print("⚠️ ไม่พบ GROQ_API_KEY!")
            print("📝 สมัครฟรีที่: https://console.groq.com")
    
    async def chat(self, messages: list) -> str:
        """ส่งข้อความไป AI และรับคำตอบ"""
        if not self.api_key:
            return "❌ ไม่มี Groq API Key - สมัครฟรีที่ https://console.groq.com"
        
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": self.model,
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 2048,
                "top_p": 0.9,
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(self.api_url, headers=headers, json=payload, timeout=30) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data['choices'][0]['message']['content']
                    else:
                        error = await response.text()
                        print(f"❌ Groq API Error: {response.status} - {error}")
                        return f"❌ ขออภัย เกิดข้อผิดพลาด: {response.status}"
        
        except asyncio.TimeoutError:
            return "⏰ หมดเวลา กรุณาลองใหม่"
        except Exception as e:
            print(f"❌ Error: {e}")
            return f"❌ ขออภัย เกิดข้อผิดพลาด: {str(e)}"

# ═══════════════════════════════════════════════════════════════════════════════
# TELEGRAM BOT
# ═══════════════════════════════════════════════════════════════════════════════

class TelegramAIBot:
    """Telegram Bot ที่ใช้ AI ตอบโต้"""
    
    def __init__(self):
        self.token = TELEGRAM_BOT_TOKEN
        self.base_url = f"https://api.telegram.org/bot{self.token}"
        self.memory = ConversationMemory()
        self.ai = GroqAI()
        self.last_update_id = 0
        
        if not self.token:
            print("❌ ไม่พบ TELEGRAM_BOT_TOKEN!")
    
    async def send_message(self, chat_id: int, text: str, parse_mode: str = "HTML") -> bool:
        """ส่งข้อความไป Telegram"""
        try:
            url = f"{self.base_url}/sendMessage"
            payload = {
                "chat_id": chat_id,
                "text": text,
                "parse_mode": parse_mode
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, timeout=10) as response:
                    return response.status == 200
        except Exception as e:
            print(f"❌ Send error: {e}")
            return False
    
    async def send_typing(self, chat_id: int):
        """แสดงสถานะกำลังพิมพ์"""
        try:
            url = f"{self.base_url}/sendChatAction"
            payload = {"chat_id": chat_id, "action": "typing"}
            
            async with aiohttp.ClientSession() as session:
                await session.post(url, json=payload, timeout=5)
        except:
            pass
    
    async def get_updates(self) -> list:
        """ดึงข้อความใหม่จาก Telegram"""
        try:
            url = f"{self.base_url}/getUpdates"
            params = {
                "offset": self.last_update_id + 1,
                "timeout": 30,
                "allowed_updates": ["message"]
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=35) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get('result', [])
        except Exception as e:
            print(f"⚠️ Get updates error: {e}")
        return []
    
    async def process_message(self, message: dict):
        """ประมวลผลข้อความ"""
        chat_id = message['chat']['id']
        text = message.get('text', '')
        user = message.get('from', {})
        username = user.get('first_name', 'User')
        
        if not text:
            return
        
        print(f"\n💬 [{username}]: {text}")
        
        # Special commands
        if text.lower() == '/start':
            welcome = f"""
🤖 <b>สวัสดี {username}!</b>

ฉันคือ <b>{BOT_NAME}</b> ผู้ช่วย AI อัจฉริยะ!

🎯 <b>สิ่งที่ฉันทำได้:</b>
• ตอบคำถามทุกเรื่อง 🧠
• วิเคราะห์ตลาด Crypto 📊
• ช่วยเขียนโค้ด 💻
• แปลภาษา 🌍
• และอื่นๆ อีกมากมาย!

💡 <b>คำสั่ง:</b>
/start - เริ่มต้นใหม่
/clear - ล้างประวัติสนทนา
/help - ดูวิธีใช้

พิมพ์อะไรก็ได้เลยครับ! 😊
"""
            await self.send_message(chat_id, welcome)
            self.memory.clear_history(chat_id)
            return
        
        if text.lower() == '/clear':
            self.memory.clear_history(chat_id)
            await self.send_message(chat_id, "🧹 ล้างประวัติสนทนาแล้ว! เริ่มใหม่ได้เลย 😊")
            return
        
        if text.lower() == '/help':
            help_text = f"""
📚 <b>วิธีใช้ {BOT_NAME}</b>

1️⃣ <b>ถามอะไรก็ได้</b>
   พิมพ์คำถามเป็นภาษาไทยหรืออังกฤษ

2️⃣ <b>ตัวอย่างคำถาม:</b>
   • "BTC จะขึ้นหรือลง?"
   • "เขียนโค้ด Python ให้หน่อย"
   • "อธิบาย RSI ให้หน่อย"
   • "แปลประโยคนี้เป็นอังกฤษ"

3️⃣ <b>คำสั่ง:</b>
   /start - เริ่มต้นใหม่
   /clear - ล้างประวัติ (ถ้า AI สับสน)
   /help - ดูวิธีใช้

💡 ฉันจำบทสนทนาได้ ถามต่อเนื่องได้เลย!
"""
            await self.send_message(chat_id, help_text)
            return
        
        # AI Response
        await self.send_typing(chat_id)
        
        # เพิ่มข้อความผู้ใช้ลง memory
        self.memory.add_message(chat_id, "user", text)
        
        # ดึง context และถาม AI
        context = self.memory.get_context(chat_id)
        response = await self.ai.chat(context)
        
        # เพิ่มคำตอบ AI ลง memory
        self.memory.add_message(chat_id, "assistant", response)
        
        # ส่งคำตอบ
        await self.send_message(chat_id, response, parse_mode="Markdown")
        print(f"🤖 [{BOT_NAME}]: {response[:100]}...")
    
    async def run(self):
        """รัน Bot"""
        print(f"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                     🤖 {BOT_NAME} - STARTED!                              ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  🧠 Model: {GROQ_MODEL:<54} ║
║  💬 Memory: {MAX_CONTEXT_MESSAGES} messages                                            ║
║  ⚡ API: Groq (เร็วที่สุด!)                                                 ║
╚══════════════════════════════════════════════════════════════════════════════╝
        """)
        
        # ส่งข้อความเริ่มต้น
        if TELEGRAM_CHAT_ID:
            await self.send_message(
                int(TELEGRAM_CHAT_ID),
                f"🤖 <b>{BOT_NAME} Online!</b>\n\nพร้อมตอบคำถามแล้ว! พิมพ์อะไรก็ได้เลย 😊"
            )
        
        print("📡 กำลังรอข้อความ... (Ctrl+C หยุด)")
        
        while True:
            try:
                updates = await self.get_updates()
                
                for update in updates:
                    self.last_update_id = update['update_id']
                    
                    if 'message' in update:
                        await self.process_message(update['message'])
                
                await asyncio.sleep(0.5)
                
            except KeyboardInterrupt:
                print("\n\n🛑 หยุด Bot")
                break
            except Exception as e:
                print(f"⚠️ Error: {e}")
                await asyncio.sleep(5)

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("🚀 เริ่ม Telegram AI Bot...")
    
    # Check requirements
    if not TELEGRAM_BOT_TOKEN:
        print("❌ ไม่พบ TELEGRAM_BOT_TOKEN ใน .env")
        print("   เพิ่ม: TELEGRAM_BOT_TOKEN=your_token")
        exit(1)
    
    if not GROQ_API_KEY:
        print("⚠️ ไม่พบ GROQ_API_KEY ใน .env")
        print("   สมัครฟรีที่: https://console.groq.com")
        print("   เพิ่ม: GROQ_API_KEY=your_key")
        print("")
        print("🔄 รัน Bot ต่อ... (จะแจ้งเตือนเมื่อใช้งาน AI)")
    
    bot = TelegramAIBot()
    asyncio.run(bot.run())
