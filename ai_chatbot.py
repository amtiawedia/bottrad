#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                          🤖 AI CHATBOT TELEGRAM                              ║
║                    ตอบได้ทุกเรื่อง 24/7 - ใช้ Llama ฟรี!                       ║
╚══════════════════════════════════════════════════════════════════════════════╝

✨ Features:
   - 💬 ตอบทุกคำถาม ภาษาไทย/อังกฤษ
   - 🧠 จำบทสนทนาได้
   - ⚡ ตอบเร็วมาก (Groq API)
   - 💻 ช่วยเขียนโค้ด
   - 🌍 แปลภาษา
   - 📝 เขียนบทความ
   - 🎨 ช่วยคิด idea
   - 🆓 ฟรี 100%!

📝 วิธีใช้:
   1. สมัคร Groq API ฟรีที่: https://console.groq.com
   2. ใส่ GROQ_API_KEY ใน .env
   3. รัน: python ai_chatbot.py
"""

import os
import json
import asyncio
import aiohttp
import re
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

# Telegram Bot
TELEGRAM_BOT_TOKEN = os.environ.get('AI_BOT_TOKEN', '')
ALLOWED_USERS = []  # ใส่ chat_id ที่อนุญาต (ว่าง = ทุกคนใช้ได้)

# Groq API (ฟรี!) - https://console.groq.com
GROQ_API_KEY = os.environ.get('GROQ_API_KEY', '')
GROQ_MODEL = "llama-3.3-70b-versatile"  # Llama 3.3 70B - ดีมาก!

# Bot Settings
BOT_NAME = "AI Assistant"
MAX_HISTORY = 20  # จำบทสนทนากี่ข้อความ
DATA_FILE = "chat_history.json"

# ═══════════════════════════════════════════════════════════════════════════════
# REAL-TIME DATA FETCHER - ดึงข้อมูลสดจาก Internet!
# ═══════════════════════════════════════════════════════════════════════════════

class RealTimeData:
    """ดึงข้อมูล real-time จาก APIs ต่างๆ"""
    
    @staticmethod
    async def get_crypto_price(symbol: str = "BTC") -> dict:
        """ดึงราคา Crypto real-time จาก Binance"""
        try:
            symbol = symbol.upper().replace("/", "").replace("USDT", "")
            url = f"https://api.binance.com/api/v3/ticker/24hr?symbol={symbol}USDT"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=5) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return {
                            "symbol": f"{symbol}/USDT",
                            "price": float(data['lastPrice']),
                            "change_24h": float(data['priceChangePercent']),
                            "high_24h": float(data['highPrice']),
                            "low_24h": float(data['lowPrice']),
                            "volume_24h": float(data['quoteVolume']),
                        }
        except:
            pass
        return None
    
    @staticmethod
    async def get_top_cryptos() -> list:
        """ดึง Top 10 Crypto"""
        try:
            url = "https://api.binance.com/api/v3/ticker/24hr"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        # Filter USDT pairs and sort by volume
                        usdt_pairs = [d for d in data if d['symbol'].endswith('USDT')]
                        sorted_pairs = sorted(usdt_pairs, key=lambda x: float(x['quoteVolume']), reverse=True)
                        return sorted_pairs[:10]
        except:
            pass
        return []
    
    @staticmethod
    async def get_weather(city: str = "Bangkok") -> dict:
        """ดึงข้อมูลสภาพอากาศ (ใช้ wttr.in ฟรี)"""
        try:
            url = f"https://wttr.in/{city}?format=j1"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=5) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        current = data['current_condition'][0]
                        return {
                            "city": city,
                            "temp_c": current['temp_C'],
                            "feels_like": current['FeelsLikeC'],
                            "humidity": current['humidity'],
                            "description": current['weatherDesc'][0]['value'],
                        }
        except:
            pass
        return None

# ═══════════════════════════════════════════════════════════════════════════════
# COMMAND DETECTOR - ตรวจจับคำสั่งพิเศษ
# ═══════════════════════════════════════════════════════════════════════════════

async def process_special_commands(text: str) -> str:
    """ตรวจจับและตอบคำสั่งพิเศษที่ต้องการข้อมูล real-time"""
    text_lower = text.lower()
    
    # ตรวจจับคำถามเกี่ยวกับราคา Crypto
    crypto_keywords = ['ราคา', 'price', 'btc', 'eth', 'bitcoin', 'ethereum', 'crypto', 'คริปโต', 'บิทคอย', 'อีเธอ']
    crypto_pattern = r'(btc|eth|sol|xrp|bnb|ada|doge|avax|link|dot|ltc|bitcoin|ethereum)'
    
    if any(kw in text_lower for kw in crypto_keywords):
        # หา symbol จากข้อความ
        match = re.search(crypto_pattern, text_lower)
        symbol = match.group(1) if match else "BTC"
        
        # แปลงชื่อเต็มเป็น symbol
        name_map = {"bitcoin": "BTC", "ethereum": "ETH"}
        symbol = name_map.get(symbol, symbol.upper())
        
        data = await RealTimeData.get_crypto_price(symbol)
        if data:
            emoji = "📈" if data['change_24h'] > 0 else "📉"
            return f"""
{emoji} *ราคา {data['symbol']} (Real-time)*

💰 ราคาปัจจุบัน: *${data['price']:,.2f}*
📊 เปลี่ยนแปลง 24h: {'+' if data['change_24h'] > 0 else ''}{data['change_24h']:.2f}%
📈 สูงสุด 24h: ${data['high_24h']:,.2f}
📉 ต่ำสุด 24h: ${data['low_24h']:,.2f}
💹 Volume 24h: ${data['volume_24h']:,.0f}

🕐 อัพเดท: {datetime.now().strftime('%H:%M:%S')}
"""
    
    # ตรวจจับคำถามเกี่ยวกับ Top Crypto
    if any(kw in text_lower for kw in ['top crypto', 'top 10', 'อันดับ', 'เหรียญไหนดี']):
        cryptos = await RealTimeData.get_top_cryptos()
        if cryptos:
            result = "🏆 *Top 10 Crypto (Volume 24h)*\n\n"
            for i, c in enumerate(cryptos[:10], 1):
                symbol = c['symbol'].replace('USDT', '')
                price = float(c['lastPrice'])
                change = float(c['priceChangePercent'])
                emoji = "🟢" if change > 0 else "🔴"
                result += f"{i}. {emoji} *{symbol}*: ${price:,.2f} ({'+' if change > 0 else ''}{change:.1f}%)\n"
            result += f"\n🕐 อัพเดท: {datetime.now().strftime('%H:%M:%S')}"
            return result
    
    # ตรวจจับคำถามเกี่ยวกับสภาพอากาศ
    weather_keywords = ['อากาศ', 'weather', 'ฝน', 'แดด', 'หนาว', 'ร้อน']
    if any(kw in text_lower for kw in weather_keywords):
        # หาชื่อเมือง
        cities = ['bangkok', 'กรุงเทพ', 'chiang mai', 'เชียงใหม่', 'phuket', 'ภูเก็ต', 'pattaya', 'พัทยา']
        city = "Bangkok"
        for c in cities:
            if c in text_lower:
                city = c.replace('กรุงเทพ', 'Bangkok').replace('เชียงใหม่', 'Chiang Mai')
                break
        
        data = await RealTimeData.get_weather(city)
        if data:
            return f"""
🌤️ *สภาพอากาศ {data['city']}*

🌡️ อุณหภูมิ: *{data['temp_c']}°C*
🤒 รู้สึกเหมือน: {data['feels_like']}°C
💧 ความชื้น: {data['humidity']}%
☁️ สภาพ: {data['description']}

🕐 อัพเดท: {datetime.now().strftime('%H:%M:%S')}
"""
    
    # ไม่ใช่คำสั่งพิเศษ
    return None

# ═══════════════════════════════════════════════════════════════════════════════
# BOT PERSONALITY - ปรับ personality ได้ตามใจ!
# ═══════════════════════════════════════════════════════════════════════════════

SYSTEM_PROMPT = """คุณคือ AI Assistant ผู้ช่วยอัจฉริยะที่ชื่อ "AlphaBot"

🎯 บุคลิกของคุณ:
- เป็นกันเอง พูดคุยเหมือนเพื่อน
- ตอบตรงประเด็น กระชับ ไม่เยิ่นเย้อ
- ใช้ emoji ให้เหมาะสม
- มีอารมณ์ขัน แต่ professional
- พูดภาษาไทยเป็นหลัก แต่สลับอังกฤษได้

💪 สิ่งที่คุณทำได้:
- ตอบคำถามทุกเรื่อง
- ช่วยเขียนโค้ด (Python, JavaScript, etc.)
- แปลภาษา
- เขียนบทความ/content
- ให้คำแนะนำ
- ช่วยคิด idea
- อธิบายเรื่องยากให้เข้าใจง่าย
- และอื่นๆ อีกมากมาย!

📝 กฎ:
- ไม่แนะนำสิ่งผิดกฎหมาย
- ไม่สร้าง content ที่เป็นอันตราย
- ถ้าไม่แน่ใจ ให้บอกตรงๆ ว่าไม่รู้"""

# ═══════════════════════════════════════════════════════════════════════════════
# CHAT MEMORY
# ═══════════════════════════════════════════════════════════════════════════════

class ChatMemory:
    def __init__(self):
        self.history = {}
        self.load()
    
    def load(self):
        try:
            if os.path.exists(DATA_FILE):
                with open(DATA_FILE, 'r', encoding='utf-8') as f:
                    self.history = json.load(f)
        except:
            self.history = {}
    
    def save(self):
        try:
            with open(DATA_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.history, f, ensure_ascii=False, indent=2)
        except:
            pass
    
    def add(self, chat_id: str, role: str, content: str):
        chat_id = str(chat_id)
        if chat_id not in self.history:
            self.history[chat_id] = []
        
        self.history[chat_id].append({
            "role": role,
            "content": content,
            "time": datetime.now().isoformat()
        })
        
        # จำกัดจำนวน
        if len(self.history[chat_id]) > MAX_HISTORY * 2:
            self.history[chat_id] = self.history[chat_id][-MAX_HISTORY * 2:]
        
        self.save()
    
    def get(self, chat_id: str) -> list:
        chat_id = str(chat_id)
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        
        if chat_id in self.history:
            for msg in self.history[chat_id][-MAX_HISTORY:]:
                messages.append({"role": msg["role"], "content": msg["content"]})
        
        return messages
    
    def clear(self, chat_id: str):
        chat_id = str(chat_id)
        if chat_id in self.history:
            del self.history[chat_id]
            self.save()

# ═══════════════════════════════════════════════════════════════════════════════
# GROQ AI (Llama)
# ═══════════════════════════════════════════════════════════════════════════════

class GroqAI:
    def __init__(self):
        self.api_key = GROQ_API_KEY
        self.url = "https://api.groq.com/openai/v1/chat/completions"
    
    async def ask(self, messages: list) -> str:
        if not self.api_key:
            return "❌ ยังไม่ได้ตั้งค่า GROQ_API_KEY\n\n📝 สมัครฟรีที่: https://console.groq.com"
        
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": GROQ_MODEL,
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 2048,
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(self.url, headers=headers, json=payload, timeout=30) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data['choices'][0]['message']['content']
                    else:
                        return f"❌ API Error: {resp.status}"
        
        except asyncio.TimeoutError:
            return "⏰ หมดเวลา กรุณาลองใหม่"
        except Exception as e:
            return f"❌ Error: {str(e)}"

# ═══════════════════════════════════════════════════════════════════════════════
# TELEGRAM BOT
# ═══════════════════════════════════════════════════════════════════════════════

class TelegramBot:
    def __init__(self):
        self.token = TELEGRAM_BOT_TOKEN
        self.base_url = f"https://api.telegram.org/bot{self.token}"
        self.memory = ChatMemory()
        self.ai = GroqAI()
        self.offset = 0
    
    async def send(self, chat_id: int, text: str):
        """ส่งข้อความ"""
        try:
            # ตัดข้อความถ้ายาวเกินไป
            if len(text) > 4000:
                text = text[:4000] + "...\n\n(ข้อความถูกตัดเนื่องจากยาวเกินไป)"
            
            url = f"{self.base_url}/sendMessage"
            payload = {
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "Markdown"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, timeout=10) as resp:
                    if resp.status != 200:
                        # ลองส่งแบบไม่มี parse_mode
                        payload["parse_mode"] = None
                        await session.post(url, json=payload, timeout=10)
        except:
            pass
    
    async def typing(self, chat_id: int):
        """แสดงกำลังพิมพ์"""
        try:
            url = f"{self.base_url}/sendChatAction"
            payload = {"chat_id": chat_id, "action": "typing"}
            async with aiohttp.ClientSession() as session:
                await session.post(url, json=payload, timeout=5)
        except:
            pass
    
    async def get_updates(self) -> list:
        """ดึงข้อความใหม่"""
        try:
            url = f"{self.base_url}/getUpdates"
            params = {"offset": self.offset + 1, "timeout": 30}
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=35) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data.get('result', [])
        except:
            pass
        return []
    
    async def handle(self, message: dict):
        """จัดการข้อความ"""
        chat_id = message['chat']['id']
        text = message.get('text', '')
        user = message.get('from', {})
        name = user.get('first_name', 'User')
        
        if not text:
            return
        
        # Check permission
        if ALLOWED_USERS and chat_id not in ALLOWED_USERS:
            await self.send(chat_id, "❌ คุณไม่มีสิทธิ์ใช้งาน Bot นี้")
            return
        
        print(f"💬 [{name}]: {text[:50]}...")
        
        # Commands
        if text == '/start':
            welcome = f"""
🤖 *สวัสดี {name}!*

ฉันคือ *{BOT_NAME}* ผู้ช่วย AI อัจฉริยะ!

✨ *สิ่งที่ฉันทำได้:*
• ตอบคำถามทุกเรื่อง 🧠
• ช่วยเขียนโค้ด 💻
• แปลภาษา 🌍
• เขียนบทความ 📝
• ช่วยคิด idea 💡
• และอื่นๆ อีกมากมาย!

*คำสั่ง:*
/start - เริ่มใหม่
/clear - ล้างความจำ
/help - วิธีใช้

พิมพ์อะไรก็ได้เลย! 😊
"""
            await self.send(chat_id, welcome)
            self.memory.clear(chat_id)
            return
        
        if text == '/clear':
            self.memory.clear(chat_id)
            await self.send(chat_id, "🧹 ล้างความจำแล้ว! เริ่มคุยใหม่ได้เลย 😊")
            return
        
        if text == '/help':
            help_text = """
📚 *วิธีใช้ AI Assistant*

1️⃣ *ถามคำถาม*
   พิมพ์คำถามได้เลย ไทย/อังกฤษ

2️⃣ *ตัวอย่าง:*
   • "อธิบาย AI ให้หน่อย"
   • "เขียนโค้ด Python บวกเลข"
   • "แปลประโยคนี้เป็นอังกฤษ"
   • "ช่วยคิดชื่อร้านอาหาร"
   • "เขียน caption IG ให้หน่อย"

3️⃣ *Tips:*
   • ถามต่อเนื่องได้ ฉันจำบทสนทนา
   • ถ้าฉันตอบผิดทาง พิมพ์ /clear
   • ยิ่งถามละเอียด ยิ่งตอบดี

พร้อมแล้ว ถามมาเลย! 🚀
"""
            await self.send(chat_id, help_text)
            return
        
        # AI Response
        await self.typing(chat_id)
        
        # เพิ่มลง memory
        self.memory.add(chat_id, "user", text)
        
        # ถาม AI
        context = self.memory.get(chat_id)
        response = await self.ai.ask(context)
        
        # เพิ่มคำตอบลง memory
        self.memory.add(chat_id, "assistant", response)
        
        # ส่งคำตอบ
        await self.send(chat_id, response)
        print(f"🤖 [AI]: {response[:50]}...")
    
    async def run(self):
        """รัน Bot"""
        print(f"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                          🤖 {BOT_NAME} ONLINE!                            ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  🧠 Model: {GROQ_MODEL:<54} ║
║  💬 Memory: {MAX_HISTORY} messages                                            ║
║  ⚡ Powered by: Groq (เร็วมาก!)                                             ║
╚══════════════════════════════════════════════════════════════════════════════╝
        """)
        
        print("📡 รอข้อความ... (Ctrl+C หยุด)\n")
        
        while True:
            try:
                updates = await self.get_updates()
                
                for update in updates:
                    self.offset = update['update_id']
                    if 'message' in update:
                        await self.handle(update['message'])
                
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
    print("🚀 เริ่ม AI Chatbot...")
    
    if not TELEGRAM_BOT_TOKEN:
        print("""
❌ ไม่พบ TELEGRAM_BOT_TOKEN!

📝 วิธีแก้:
1. สร้าง Bot ที่ @BotFather บน Telegram
2. คัดลอก Token
3. เพิ่มใน .env:
   TELEGRAM_BOT_TOKEN=your_token_here
""")
        exit(1)
    
    if not GROQ_API_KEY:
        print("""
⚠️ ไม่พบ GROQ_API_KEY!

📝 วิธีแก้:
1. สมัครฟรีที่: https://console.groq.com
2. สร้าง API Key
3. เพิ่มใน .env:
   GROQ_API_KEY=gsk_xxxxxxxxxxxx

🔄 รัน Bot ต่อ... (จะแจ้งเตือนเมื่อใช้งาน)
""")
    
    bot = TelegramBot()
    asyncio.run(bot.run())
