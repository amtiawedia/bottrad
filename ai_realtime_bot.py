#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    🤖 AI CHATBOT - REAL-TIME DATA                            ║
║              ตอบได้ทุกเรื่อง + ข้อมูล Real-time จาก Internet!                  ║
╚══════════════════════════════════════════════════════════════════════════════╝

✨ Features:
   - 💬 ตอบทุกคำถาม ภาษาไทย/อังกฤษ
   - 🌐 ค้นหาข้อมูล Real-time จาก Internet
   - 📊 ราคา Crypto Real-time
   - 🌤️ สภาพอากาศ Real-time
   - 📰 ข่าวล่าสุด
   - 🧠 จำบทสนทนาได้
   - ⚡ ตอบเร็วมาก
   - 🆓 ฟรี 100%!

📝 วิธีใช้:
   python ai_realtime_bot.py
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

# Groq API (Llama - ฟรี!)
GROQ_API_KEY = os.environ.get('GROQ_API_KEY', '')
GROQ_MODEL = "llama-3.3-70b-versatile"

# Perplexity API (สำหรับ Web Search Real-time)
PERPLEXITY_API_KEY = os.environ.get('PERPLEXITY_API_KEY', '')

# Bot Settings
BOT_NAME = "AlphaBot AI"
MAX_HISTORY = 15
DATA_FILE = "realtime_chat_history.json"

# ═══════════════════════════════════════════════════════════════════════════════
# REAL-TIME DATA FETCHER
# ═══════════════════════════════════════════════════════════════════════════════

class RealTimeSearch:
    """ค้นหาข้อมูล Real-time จาก Internet"""
    
    def __init__(self):
        self.perplexity_key = PERPLEXITY_API_KEY
    
    async def search_web(self, query: str) -> str:
        """ค้นหาข้อมูลจาก Internet ด้วย Perplexity API"""
        if not self.perplexity_key:
            return None
        
        try:
            url = "https://api.perplexity.ai/chat/completions"
            headers = {
                "Authorization": f"Bearer {self.perplexity_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": "llama-3.1-sonar-small-128k-online",  # Online model ค้นหา real-time
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a helpful assistant. Answer in Thai language. ตอบเป็นภาษาไทย กระชับ ตรงประเด็น ใช้ข้อมูลล่าสุดจาก internet"
                    },
                    {
                        "role": "user",
                        "content": query
                    }
                ],
                "temperature": 0.2,
                "max_tokens": 1024
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload, timeout=30) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data['choices'][0]['message']['content']
                    else:
                        error = await resp.text()
                        print(f"⚠️ Perplexity API Error: {resp.status} - {error}")
        except Exception as e:
            print(f"⚠️ Search error: {e}")
        
        return None
    
    async def get_crypto_price(self, symbol: str = "BTC") -> dict:
        """ดึงราคา Crypto Real-time จาก Binance"""
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
    
    async def get_top_cryptos(self, limit: int = 10) -> list:
        """ดึง Top Crypto ตาม Volume"""
        try:
            url = "https://api.binance.com/api/v3/ticker/24hr"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        usdt_pairs = [d for d in data if d['symbol'].endswith('USDT') and 
                                     not any(x in d['symbol'] for x in ['UP', 'DOWN', 'BEAR', 'BULL'])]
                        sorted_pairs = sorted(usdt_pairs, key=lambda x: float(x['quoteVolume']), reverse=True)
                        return sorted_pairs[:limit]
        except:
            pass
        return []
    
    async def get_weather(self, city: str = "Bangkok") -> dict:
        """ดึงข้อมูลสภาพอากาศ Real-time"""
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
                            "wind_kmph": current['windspeedKmph'],
                        }
        except:
            pass
        return None
    
    async def get_gold_price(self) -> dict:
        """ดึงราคาทอง"""
        try:
            # ใช้ Perplexity ค้นหาราคาทองล่าสุด
            result = await self.search_web("ราคาทองคำวันนี้ ราคาทองรูปพรรณ ทองแท่ง ล่าสุด")
            if result:
                return {"info": result}
        except:
            pass
        return None
    
    async def get_exchange_rate(self, from_cur: str = "USD", to_cur: str = "THB") -> dict:
        """ดึงอัตราแลกเปลี่ยน"""
        try:
            url = f"https://api.exchangerate-api.com/v4/latest/{from_cur}"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=5) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        rate = data['rates'].get(to_cur)
                        if rate:
                            return {
                                "from": from_cur,
                                "to": to_cur,
                                "rate": rate,
                                "date": data['date']
                            }
        except:
            pass
        return None

# ═══════════════════════════════════════════════════════════════════════════════
# COMMAND PROCESSOR - ตรวจจับและตอบคำถาม Real-time
# ═══════════════════════════════════════════════════════════════════════════════

async def process_realtime_query(text: str, searcher: RealTimeSearch) -> str:
    """ตรวจจับคำถามที่ต้องการข้อมูล real-time และตอบกลับ"""
    text_lower = text.lower()
    now = datetime.now().strftime('%H:%M:%S %d/%m/%Y')
    
    # ═══ 1. ราคา Crypto ═══
    crypto_keywords = ['ราคา', 'price', 'btc', 'eth', 'bitcoin', 'ethereum', 'crypto', 'คริปโต', 'บิทคอย']
    crypto_pattern = r'(btc|eth|sol|xrp|bnb|ada|doge|avax|link|dot|ltc|sui|near|bitcoin|ethereum|solana)'
    
    if any(kw in text_lower for kw in crypto_keywords):
        match = re.search(crypto_pattern, text_lower)
        if match:
            symbol = match.group(1)
            name_map = {"bitcoin": "BTC", "ethereum": "ETH", "solana": "SOL"}
            symbol = name_map.get(symbol, symbol.upper())
            
            data = await searcher.get_crypto_price(symbol)
            if data:
                emoji = "📈" if data['change_24h'] > 0 else "📉"
                change_emoji = "🟢" if data['change_24h'] > 0 else "🔴"
                return f"""
{emoji} *ราคา {data['symbol']} Real-time*

💰 ราคาปัจจุบัน: *${data['price']:,.2f}*
{change_emoji} เปลี่ยนแปลง 24h: *{'+' if data['change_24h'] > 0 else ''}{data['change_24h']:.2f}%*
📈 สูงสุด 24h: ${data['high_24h']:,.2f}
📉 ต่ำสุด 24h: ${data['low_24h']:,.2f}
💹 Volume 24h: ${data['volume_24h']:,.0f}

🕐 อัพเดท: {now}
📡 แหล่งข้อมูล: Binance
"""
    
    # ═══ 2. Top Crypto ═══
    if any(kw in text_lower for kw in ['top crypto', 'top 10', 'อันดับ crypto', 'เหรียญไหนดี', 'crypto ยอดนิยม']):
        cryptos = await searcher.get_top_cryptos(10)
        if cryptos:
            result = "🏆 *Top 10 Crypto (Volume 24h) Real-time*\n\n"
            for i, c in enumerate(cryptos[:10], 1):
                symbol = c['symbol'].replace('USDT', '')
                price = float(c['lastPrice'])
                change = float(c['priceChangePercent'])
                emoji = "🟢" if change > 0 else "🔴"
                result += f"{i}. {emoji} *{symbol}*: ${price:,.2f} ({'+' if change > 0 else ''}{change:.1f}%)\n"
            result += f"\n🕐 อัพเดท: {now}"
            return result
    
    # ═══ 3. สภาพอากาศ ═══
    weather_keywords = ['อากาศ', 'weather', 'ฝน', 'แดด', 'หนาว', 'ร้อน', 'พยากรณ์']
    if any(kw in text_lower for kw in weather_keywords):
        cities = {
            'กรุงเทพ': 'Bangkok', 'bangkok': 'Bangkok',
            'เชียงใหม่': 'Chiang+Mai', 'chiang mai': 'Chiang+Mai',
            'ภูเก็ต': 'Phuket', 'phuket': 'Phuket',
            'พัทยา': 'Pattaya', 'pattaya': 'Pattaya',
            'ขอนแก่น': 'Khon+Kaen', 'หาดใหญ่': 'Hat+Yai',
        }
        city = "Bangkok"
        for thai, eng in cities.items():
            if thai in text_lower:
                city = eng
                break
        
        data = await searcher.get_weather(city)
        if data:
            return f"""
🌤️ *สภาพอากาศ {data['city'].replace('+', ' ')} Real-time*

🌡️ อุณหภูมิ: *{data['temp_c']}°C*
🤒 รู้สึกเหมือน: {data['feels_like']}°C
💧 ความชื้น: {data['humidity']}%
💨 ลม: {data['wind_kmph']} km/h
☁️ สภาพ: {data['description']}

🕐 อัพเดท: {now}
"""
    
    # ═══ 4. อัตราแลกเปลี่ยน ═══
    exchange_keywords = ['แลกเปลี่ยน', 'exchange', 'usd', 'thb', 'ดอลลาร์', 'บาท', 'เงิน', 'ค่าเงิน']
    if any(kw in text_lower for kw in exchange_keywords):
        data = await searcher.get_exchange_rate("USD", "THB")
        if data:
            return f"""
💱 *อัตราแลกเปลี่ยน Real-time*

🇺🇸 1 USD = 🇹🇭 *{data['rate']:.2f} THB*

📅 วันที่: {data['date']}
🕐 อัพเดท: {now}
"""
    
    # ═══ 5. ราคาทอง ═══
    gold_keywords = ['ทอง', 'gold', 'ราคาทอง', 'ทองคำ', 'ทองแท่ง', 'ทองรูปพรรณ']
    if any(kw in text_lower for kw in gold_keywords):
        # ใช้ Perplexity ค้นหา
        result = await searcher.search_web("ราคาทองคำวันนี้ ทองแท่ง ทองรูปพรรณ สมาคมค้าทองคำ")
        if result:
            return f"🥇 *ราคาทอง Real-time*\n\n{result}\n\n🕐 อัพเดท: {now}"
    
    # ═══ 6. ข่าว / เหตุการณ์ปัจจุบัน ═══
    news_keywords = ['ข่าว', 'news', 'เหตุการณ์', 'วันนี้', 'ล่าสุด', 'ตอนนี้', 'ปัจจุบัน', 'อัพเดท', 
                     'เกิดอะไร', 'สถานการณ์', 'การเมือง', 'เศรษฐกิจ', 'หุ้น', 'set', 'ตลาดหุ้น',
                     'นายก', 'รัฐบาล', 'โควิด', 'น้ำท่วม', 'แผ่นดินไหว', 'สงคราม']
    
    if any(kw in text_lower for kw in news_keywords):
        result = await searcher.search_web(text)
        if result:
            return f"📰 *ข้อมูล Real-time*\n\n{result}\n\n🕐 อัพเดท: {now}\n📡 แหล่งข้อมูล: Internet Search"
    
    # ═══ 7. คำถามทั่วไปที่อาจต้องการข้อมูลล่าสุด ═══
    realtime_indicators = ['วันนี้', 'ตอนนี้', 'ล่าสุด', 'ปัจจุบัน', 'เมื่อกี้', '2024', '2025', 
                          'ใหม่ล่าสุด', 'อัพเดท', 'real-time', 'realtime', 'เรียลไทม์']
    
    if any(kw in text_lower for kw in realtime_indicators):
        result = await searcher.search_web(text)
        if result:
            return f"🌐 *ข้อมูล Real-time จาก Internet*\n\n{result}\n\n🕐 อัพเดท: {now}"
    
    # ไม่ใช่คำถาม real-time
    return None

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
        
        if len(self.history[chat_id]) > MAX_HISTORY * 2:
            self.history[chat_id] = self.history[chat_id][-MAX_HISTORY * 2:]
        
        self.save()
    
    def get(self, chat_id: str) -> list:
        chat_id = str(chat_id)
        system_prompt = f"""คุณคือ {BOT_NAME} ผู้ช่วย AI อัจฉริยะ

🎯 บุคลิก:
- เป็นกันเอง พูดคุยเหมือนเพื่อน
- ตอบตรงประเด็น กระชับ
- ใช้ emoji ให้เหมาะสม
- พูดภาษาไทยเป็นหลัก

💪 ความสามารถ:
- ตอบคำถามทุกเรื่อง
- ช่วยเขียนโค้ด
- แปลภาษา
- ให้คำแนะนำ
- คิด idea

📝 หมายเหตุ: วันที่ปัจจุบันคือ {datetime.now().strftime('%d/%m/%Y')}"""
        
        messages = [{"role": "system", "content": system_prompt}]
        
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
            return "❌ ยังไม่ได้ตั้งค่า GROQ_API_KEY"
        
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
        self.searcher = RealTimeSearch()
        self.offset = 0
    
    async def send(self, chat_id: int, text: str):
        try:
            if len(text) > 4000:
                text = text[:4000] + "...\n\n(ข้อความถูกตัด)"
            
            url = f"{self.base_url}/sendMessage"
            payload = {
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "Markdown"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, timeout=10) as resp:
                    if resp.status != 200:
                        payload["parse_mode"] = None
                        await session.post(url, json=payload, timeout=10)
        except:
            pass
    
    async def typing(self, chat_id: int):
        try:
            url = f"{self.base_url}/sendChatAction"
            payload = {"chat_id": chat_id, "action": "typing"}
            async with aiohttp.ClientSession() as session:
                await session.post(url, json=payload, timeout=5)
        except:
            pass
    
    async def get_updates(self) -> list:
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
        chat_id = message['chat']['id']
        text = message.get('text', '')
        user = message.get('from', {})
        name = user.get('first_name', 'User')
        
        if not text:
            return
        
        print(f"💬 [{name}]: {text[:60]}...")
        
        # Commands
        if text == '/start':
            welcome = f"""
🤖 *สวัสดี {name}!*

ฉันคือ *{BOT_NAME}* ผู้ช่วย AI พร้อมข้อมูล Real-time!

✨ *สิ่งที่ฉันทำได้:*
• 🌐 ค้นหาข้อมูล Real-time จาก Internet
• 📊 ราคา Crypto Real-time
• 🌤️ สภาพอากาศ Real-time
• 💱 อัตราแลกเปลี่ยน
• 📰 ข่าวสาร/เหตุการณ์ปัจจุบัน
• 🥇 ราคาทอง
• 💬 ตอบคำถามทั่วไป
• 💻 ช่วยเขียนโค้ด

*คำสั่ง:*
/btc - ราคา Bitcoin
/eth - ราคา Ethereum  
/top10 - Top 10 Crypto
/weather - สภาพอากาศ
/usd - อัตราแลกเปลี่ยน
/clear - ล้างความจำ

พิมพ์อะไรก็ได้เลย! 🚀
"""
            await self.send(chat_id, welcome)
            self.memory.clear(chat_id)
            return
        
        # Quick commands
        if text.lower() in ['/btc', '/bitcoin']:
            await self.typing(chat_id)
            data = await self.searcher.get_crypto_price("BTC")
            if data:
                emoji = "📈" if data['change_24h'] > 0 else "📉"
                await self.send(chat_id, f"{emoji} *BTC*: ${data['price']:,.2f} ({'+' if data['change_24h'] > 0 else ''}{data['change_24h']:.2f}%)")
            return
        
        if text.lower() in ['/eth', '/ethereum']:
            await self.typing(chat_id)
            data = await self.searcher.get_crypto_price("ETH")
            if data:
                emoji = "📈" if data['change_24h'] > 0 else "📉"
                await self.send(chat_id, f"{emoji} *ETH*: ${data['price']:,.2f} ({'+' if data['change_24h'] > 0 else ''}{data['change_24h']:.2f}%)")
            return
        
        if text.lower() == '/top10':
            await self.typing(chat_id)
            response = await process_realtime_query("top 10 crypto", self.searcher)
            if response:
                await self.send(chat_id, response)
            return
        
        if text.lower() in ['/weather', '/อากาศ']:
            await self.typing(chat_id)
            response = await process_realtime_query("อากาศ กรุงเทพ", self.searcher)
            if response:
                await self.send(chat_id, response)
            return
        
        if text.lower() in ['/usd', '/แลกเปลี่ยน']:
            await self.typing(chat_id)
            response = await process_realtime_query("อัตราแลกเปลี่ยน usd thb", self.searcher)
            if response:
                await self.send(chat_id, response)
            return
        
        if text == '/clear':
            self.memory.clear(chat_id)
            await self.send(chat_id, "🧹 ล้างความจำแล้ว!")
            return
        
        if text == '/help':
            help_text = """
📚 *วิธีใช้ AlphaBot AI*

🌐 *ข้อมูล Real-time:*
• "ราคา BTC" - ราคา Bitcoin
• "ราคา ETH วันนี้" - ราคา Ethereum
• "Top 10 Crypto" - เหรียญยอดนิยม
• "อากาศ กรุงเทพ" - พยากรณ์อากาศ
• "USD เท่าไหร่" - อัตราแลกเปลี่ยน
• "ราคาทองวันนี้" - ราคาทองคำ
• "ข่าววันนี้" - ข่าวล่าสุด
• "นายกคนปัจจุบัน" - ข้อมูล real-time

💬 *คำถามทั่วไป:*
• "เขียนโค้ด Python"
• "แปลเป็นอังกฤษ"
• "อธิบาย AI"

⚡ *Tips:* ใส่คำว่า "วันนี้" "ล่าสุด" "ตอนนี้" 
เพื่อให้ค้นหาข้อมูล real-time จาก internet
"""
            await self.send(chat_id, help_text)
            return
        
        # Process message
        await self.typing(chat_id)
        
        # 1. ลองค้นหา real-time ก่อน
        realtime_response = await process_realtime_query(text, self.searcher)
        
        if realtime_response:
            # มีข้อมูล real-time
            await self.send(chat_id, realtime_response)
            self.memory.add(chat_id, "user", text)
            self.memory.add(chat_id, "assistant", realtime_response)
            print(f"🌐 [Real-time]: {realtime_response[:50]}...")
        else:
            # ใช้ AI ตอบ
            self.memory.add(chat_id, "user", text)
            context = self.memory.get(chat_id)
            response = await self.ai.ask(context)
            self.memory.add(chat_id, "assistant", response)
            await self.send(chat_id, response)
            print(f"🤖 [AI]: {response[:50]}...")
    
    async def run(self):
        print(f"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    🤖 {BOT_NAME} - REAL-TIME ONLINE!                      ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  🧠 AI Model: {GROQ_MODEL:<52} ║
║  🌐 Web Search: Perplexity API                                               ║
║  📊 Crypto: Binance API                                                      ║
║  ⚡ Status: Ready!                                                           ║
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
    print("🚀 เริ่ม AI Chatbot Real-time...")
    
    if not TELEGRAM_BOT_TOKEN:
        print("❌ ไม่พบ AI_BOT_TOKEN ใน .env")
        exit(1)
    
    if not GROQ_API_KEY:
        print("⚠️ ไม่พบ GROQ_API_KEY - AI จะไม่ทำงาน")
    
    if not PERPLEXITY_API_KEY:
        print("⚠️ ไม่พบ PERPLEXITY_API_KEY - Web Search จะไม่ทำงาน")
    else:
        print("✅ Perplexity API พร้อมใช้งาน - Web Search Real-time!")
    
    bot = TelegramBot()
    asyncio.run(bot.run())
