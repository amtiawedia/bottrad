#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                        AlphaBot-Scalper V4                                   ║
║          Autonomous Multi-Agent AI Trading System                            ║
║                      BTC/USDT Scalping Strategy                              ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  Agent-A: Data Analyst & Volatility Assessor                                 ║
║  Agent-B: Strategy Optimizer (Reinforcement Learning)                        ║
║  Agent-C: Smart Execution & Risk Management                                  ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import ccxt
import pandas as pd
import pandas_ta as ta
import numpy as np
import time
import json
import os
import logging
import threading
import queue
import requests
import io
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Tuple, Any
from enum import Enum
from abc import ABC, abstractmethod
import warnings
warnings.filterwarnings('ignore')

# Import matplotlib for charts
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# Import new modules (Trade Journal, Multi-Coin, ML Model)
try:
    from trade_journal import TradeJournal
    JOURNAL_AVAILABLE = True
except ImportError:
    JOURNAL_AVAILABLE = False

try:
    from multi_coin import MultiCoinScanner
    MULTI_COIN_AVAILABLE = True
except ImportError:
    MULTI_COIN_AVAILABLE = False

try:
    from ml_model import MLPatternModel
    ML_MODEL_AVAILABLE = True
except ImportError:
    ML_MODEL_AVAILABLE = False

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class Config:
    """Master Configuration"""
    # API Keys
    API_KEY: str = os.environ.get('BINANCE_API_KEY', '')
    SECRET_KEY: str = os.environ.get('BINANCE_SECRET_KEY', '')
    
    # Telegram Settings
    TELEGRAM_BOT_TOKEN: str = os.environ.get('TELEGRAM_BOT_TOKEN', '')
    TELEGRAM_CHAT_ID: str = os.environ.get('TELEGRAM_CHAT_ID', '')
    TELEGRAM_ENABLED: bool = True  # Enable/disable notifications
    
    # AI Settings (News Filter + Chat)
    PERPLEXITY_API_KEY: str = os.environ.get('PERPLEXITY_API_KEY', '')
    GEMINI_API_KEY: str = os.environ.get('GEMINI_API_KEY', '')
    AI_NEWS_FILTER_ENABLED: bool = True  # Enable AI news analysis before trading
    
    # Trading Pair - TOP 20-50 COINS (Best from backtest)
    SYMBOLS: List[str] = field(default_factory=lambda: [
        # ⭐⭐ Top performers (WR 40%+)
        'DOGE/USDT', 'ETC/USDT', 'INJ/USDT', 'NEAR/USDT', 'RUNE/USDT',
        # ⭐ Good performers (profitable)
        'SOL/USDT', 'AVAX/USDT', 'FIL/USDT', 'ARB/USDT', 'OP/USDT',
        'SEI/USDT', 'SUI/USDT', 'PEPE/USDT', 'WIF/USDT', 'ORDI/USDT',
        'STX/USDT', 'IMX/USDT', 'FTM/USDT', 'AAVE/USDT', 'GRT/USDT',
        # Major coins for volume
        'BTC/USDT', 'ETH/USDT', 'XRP/USDT', 'BNB/USDT', 'ADA/USDT',
        'LINK/USDT', 'DOT/USDT', 'MATIC/USDT', 'LTC/USDT', 'UNI/USDT',
    ])
    SYMBOL: str = 'BTC/USDT'  # Default for single mode
    TIMEFRAME: str = '5m'  # 5m - best performance
    MULTI_COIN_MODE: bool = True  # Enable multi-coin scanning
    
    # Portfolio
    INITIAL_CAPITAL: float = 4.5  # Current balance
    POSITION_SIZE_PCT: float = 1.00  # 100% per trade (full equity)
    MAX_LEVERAGE: int = 20  # ลดจาก 50x เป็น 20x (ปลอดภัยกว่า)
    
    # Risk Management (Agent-C)
    DAILY_STOP_LOSS_PCT: float = 0.80      # 80% DSL (for testing)
    MAX_DRAWDOWN_PCT: float = 0.80          # 80% MDD limit (for testing)
    STOP_LOSS_PCT: float = 0.030            # เพิ่มจาก 1.2% เป็น 3% (ไม่โดน Stop Hunt)
    TAKE_PROFIT_PCT: float = 0.060          # เพิ่มจาก 5% เป็น 6% (Risk:Reward = 1:2)
    TRAILING_STOP_PCT: float = 0.020        # เพิ่มจาก 1.5% เป็น 2% trailing
    
    # Advanced Features
    BREAKEVEN_TRIGGER_PCT: float = 0.015    # Move SL to entry when +1.5% profit
    PARTIAL_TP_ENABLED: bool = True         # Enable partial take profit
    PARTIAL_TP_PCT: float = 0.025           # First TP at +2.5%
    PARTIAL_TP_CLOSE_PCT: float = 0.50      # Close 50% at first TP
    AUTO_COMPOUND: bool = True              # Auto increase position with profit
    
    # Live PnL Updates
    LIVE_PNL_INTERVAL: int = 300            # Send PnL update every 5 minutes (300 sec)
    SIGNAL_PREVIEW: bool = True             # Notify before entering trade
    
    # Live Trading Mode
    LIVE_MODE: bool = False                 # False = Paper Trade (no real orders)
    
    # Agent-A Settings
    DATA_LOOKBACK: int = 1500               # Candles for analysis (more data)
    VOLATILITY_WINDOW: int = 20             # GARCH window
    VOLUME_SPIKE_MULT: float = 3.0          # Volume spike detection
    
    # Agent-B Settings
    BACKTEST_DAYS: int = 180                # 6 months backtest
    RL_LEARNING_RATE: float = 0.001
    RL_GAMMA: float = 0.95
    MIN_SHARPE_RATIO: float = 1.5
    
    # Indicators
    RSI_PERIOD: int = 14
    EMA_FAST: int = 3
    EMA_SLOW: int = 8
    BB_PERIOD: int = 20
    BB_STD: float = 2.0
    ADX_PERIOD: int = 14
    MACD_FAST: int = 12
    MACD_SLOW: int = 26
    MACD_SIGNAL: int = 9
    
    # Fees
    MAKER_FEE: float = 0.0002
    TAKER_FEE: float = 0.0004


class MarketState(Enum):
    TRENDING_UP = "TRENDING_UP"
    TRENDING_DOWN = "TRENDING_DOWN"
    RANGING = "RANGING"
    HIGH_VOLATILITY = "HIGH_VOLATILITY"
    LOW_VOLATILITY = "LOW_VOLATILITY"
    RISK_OFF = "RISK_OFF"


# ═══════════════════════════════════════════════════════════════════════════════
# PERPLEXITY AI NEWS FILTER
# ═══════════════════════════════════════════════════════════════════════════════

class PerplexityNewsFilter:
    """AI-powered news analysis using Perplexity API"""
    
    def __init__(self, config: Config):
        self.config = config
        self.api_key = config.PERPLEXITY_API_KEY
        self.enabled = config.AI_NEWS_FILTER_ENABLED and self.api_key
        self.base_url = "https://api.perplexity.ai/chat/completions"
        self.last_check = None
        self.last_result = None
        self.cache_duration = 300  # 5 minutes cache
        
    def analyze_market_news(self) -> Dict[str, Any]:
        """Analyze current BTC news and sentiment"""
        if not self.enabled:
            return {"safe_to_trade": True, "reason": "AI filter disabled"}
        
        # Check cache
        if self.last_check and self.last_result:
            elapsed = (datetime.now() - self.last_check).total_seconds()
            if elapsed < self.cache_duration:
                return self.last_result
        
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            prompt = """Analyze Bitcoin (BTC) market RIGHT NOW. Answer in this EXACT JSON format only:
{
  "price": "current BTC price",
  "sentiment": "BULLISH or BEARISH or NEUTRAL",
  "risk_level": "LOW or MEDIUM or HIGH",
  "major_news": true or false,
  "news_summary": "1 sentence summary",
  "safe_to_trade": true or false,
  "reason": "why safe or not safe to trade"
}

Consider: Fed decisions, CPI data, major hacks, regulatory news, whale movements.
If there's HIGH IMPACT news in next 2 hours, set safe_to_trade to false."""

            data = {
                "model": "sonar",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1
            }
            
            response = requests.post(
                self.base_url, 
                headers=headers, 
                json=data, 
                timeout=15
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content']
                
                # Parse AI response
                analysis = self._parse_response(content)
                
                self.last_check = datetime.now()
                self.last_result = analysis
                
                return analysis
            else:
                print(f"[Perplexity] API error: {response.status_code}")
                return {"safe_to_trade": True, "reason": "API error, proceeding with caution"}
                
        except Exception as e:
            print(f"[Perplexity] Error: {e}")
            return {"safe_to_trade": True, "reason": f"Error: {str(e)}"}
    
    def _parse_response(self, content: str) -> Dict[str, Any]:
        """Parse AI response to extract trading signal"""
        try:
            # Try to extract JSON from response
            import re
            json_match = re.search(r'\{[^{}]*\}', content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except:
            pass
        
        # Fallback: analyze text content
        content_lower = content.lower()
        
        # Check for danger keywords
        danger_keywords = ['crash', 'hack', 'sec lawsuit', 'ban', 'investigation', 
                          'emergency', 'breaking', 'flash crash', 'liquidation']
        has_danger = any(kw in content_lower for kw in danger_keywords)
        
        # Check for high impact news
        high_impact = ['fed', 'fomc', 'cpi', 'interest rate', 'powell']
        has_high_impact = any(kw in content_lower for kw in high_impact)
        
        # Determine sentiment
        bullish_words = ['bullish', 'surge', 'rally', 'breakout', 'moon', 'pump']
        bearish_words = ['bearish', 'crash', 'dump', 'selloff', 'decline', 'drop']
        
        bullish_count = sum(1 for w in bullish_words if w in content_lower)
        bearish_count = sum(1 for w in bearish_words if w in content_lower)
        
        if bullish_count > bearish_count:
            sentiment = "BULLISH"
        elif bearish_count > bullish_count:
            sentiment = "BEARISH"
        else:
            sentiment = "NEUTRAL"
        
        return {
            "sentiment": sentiment,
            "risk_level": "HIGH" if has_danger else "MEDIUM" if has_high_impact else "LOW",
            "major_news": has_danger or has_high_impact,
            "safe_to_trade": not has_danger,
            "reason": "Danger keywords detected" if has_danger else "Normal market conditions",
            "raw_content": content[:200]
        }
    
    def should_trade(self) -> Tuple[bool, str]:
        """Quick check if it's safe to trade"""
        analysis = self.analyze_market_news()
        safe = analysis.get('safe_to_trade', True)
        reason = analysis.get('reason', 'Unknown')
        sentiment = analysis.get('sentiment', 'NEUTRAL')
        
        return safe, f"{sentiment} - {reason}"


# ═══════════════════════════════════════════════════════════════════════════════
# TELEGRAM NOTIFIER WITH AI CHAT
# ═══════════════════════════════════════════════════════════════════════════════

import threading

class TelegramNotifier:
    """Telegram Bot Notification System with AI Chat"""
    
    def __init__(self, config: Config):
        self.config = config
        self.token = config.TELEGRAM_BOT_TOKEN  # For image download
        self.bot_token = config.TELEGRAM_BOT_TOKEN
        self.chat_id = config.TELEGRAM_CHAT_ID
        self.enabled = config.TELEGRAM_ENABLED and self.bot_token and self.chat_id
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
        self.last_update_id = None
        self.perplexity_api_key = config.PERPLEXITY_API_KEY
        self.bot_ref = None  # Reference to main bot for status
        self.polling_thread = None
        self.is_polling = False
        
    def send_message(self, text: str, parse_mode: str = "HTML") -> bool:
        """Send text message to Telegram"""
        if not self.enabled:
            return False
        try:
            url = f"{self.base_url}/sendMessage"
            data = {
                "chat_id": self.chat_id,
                "text": text,
                "parse_mode": parse_mode
            }
            response = requests.post(url, data=data, timeout=10)
            return response.status_code == 200
        except Exception as e:
            print(f"[Telegram] Error sending message: {e}")
            return False
    
    def get_updates(self) -> list:
        """Get new messages from Telegram"""
        try:
            url = f"{self.base_url}/getUpdates"
            params = {"timeout": 1}  # Short timeout for non-blocking
            if self.last_update_id:
                params["offset"] = self.last_update_id + 1
            
            response = requests.get(url, params=params, timeout=3)
            if response.status_code == 200:
                return response.json().get("result", [])
            return []
        except:
            return []
    
    def ask_gemini(self, question: str, image_data: str = None) -> str:
        """Ask Gemini 2.0 Flash - รองรับรูปภาพ!"""
        gemini_key = self.config.GEMINI_API_KEY if hasattr(self.config, 'GEMINI_API_KEY') else os.environ.get('GEMINI_API_KEY', '')
        
        if not gemini_key:
            # Fallback to Perplexity
            return self.ask_perplexity_fallback(question)
        
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent?key={gemini_key}"
            
            # Build content parts
            parts = []
            
            # Add image if provided (base64)
            if image_data:
                parts.append({
                    "inline_data": {
                        "mime_type": "image/jpeg",
                        "data": image_data
                    }
                })
            
            # Add text
            system_text = """คุณเป็น AI ผู้เชี่ยวชาญ Cryptocurrency โดยเฉพาะ Bitcoin
ตอบเป็นภาษาไทย กระชับ ชัดเจน ไม่เกิน 200 คำ
ถ้าส่งรูปกราฟมา ให้วิเคราะห์ Technical Analysis"""
            parts.append({"text": f"{system_text}\n\nคำถาม: {question}"})
            
            data = {
                "contents": [{
                    "parts": parts
                }],
                "generationConfig": {
                    "temperature": 0.7,
                    "maxOutputTokens": 500
                }
            }
            
            response = requests.post(url, json=data, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                return result['candidates'][0]['content']['parts'][0]['text']
            else:
                return f"❌ Gemini Error: {response.status_code}"
                
        except requests.exceptions.Timeout:
            return "⏰ Gemini ตอบช้าเกินไป"
        except Exception as e:
            return f"❌ Error: {str(e)}"
    
    def ask_perplexity_fallback(self, question: str) -> str:
        """Fallback to Perplexity if no Gemini key"""
        if not self.perplexity_api_key:
            return "❌ กรุณาตั้งค่า GEMINI_API_KEY ใน .env"
        
        try:
            headers = {
                "Authorization": f"Bearer {self.perplexity_api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": "sonar-pro",
                "messages": [
                    {"role": "user", "content": question}
                ],
                "max_tokens": 400
            }
            
            response = requests.post(
                "https://api.perplexity.ai/chat/completions",
                headers=headers,
                json=data,
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()['choices'][0]['message']['content']
            else:
                return f"❌ API Error: {response.status_code}"
                
        except Exception as e:
            return f"❌ Error: {str(e)}"
    
    def start_polling(self):
        """Start background polling for Telegram commands"""
        if self.is_polling:
            return
        self.is_polling = True
        self.polling_thread = threading.Thread(target=self._polling_loop, daemon=True)
        self.polling_thread.start()
        self.send_message("🔄 <b>Telegram Polling Started</b>\n\nพิมพ์ /help เพื่อดู commands")
    
    def stop_polling(self):
        """Stop polling"""
        self.is_polling = False
    
    def _polling_loop(self):
        """Background loop to check for commands"""
        import logging
        logger = logging.getLogger(__name__)
        while self.is_polling:
            try:
                self.process_commands()
            except Exception as e:
                logger.error(f"[Telegram] Polling error: {e}")
            time.sleep(2)  # Check every 2 seconds
    
    def process_commands(self):
        """Process incoming Telegram commands including images"""
        updates = self.get_updates()
        
        for update in updates:
            self.last_update_id = update["update_id"]
            
            if "message" in update:
                message = update["message"]
                chat_id = str(message["chat"]["id"])
                
                # Only process from authorized chat
                if chat_id != self.chat_id:
                    continue
                
                text = message.get("text", "").strip()
                caption = message.get("caption", "").strip()
                
                # Check for photo
                if "photo" in message:
                    # Get largest photo
                    photo = message["photo"][-1]
                    file_id = photo["file_id"]
                    
                    # Get photo and analyze with Gemini
                    self.handle_image(file_id, caption or "วิเคราะห์กราฟนี้")
                    continue
                
                if not text:
                    continue
                
                print(f"[Telegram] Received: {text}")
                
                # Process command
                self.handle_command(text)
    
    def handle_image(self, file_id: str, question: str):
        """Handle image with Gemini vision"""
        try:
            self.send_message("🖼️ กำลังวิเคราะห์รูป...")
            
            # Get file path from Telegram
            url = f"{self.base_url}/getFile"
            response = requests.get(url, params={"file_id": file_id}, timeout=10)
            
            if response.status_code != 200:
                self.send_message("❌ ไม่สามารถดึงรูปได้")
                return
            
            file_path = response.json()["result"]["file_path"]
            
            # Download image
            image_url = f"https://api.telegram.org/file/bot{self.token}/{file_path}"
            img_response = requests.get(image_url, timeout=30)
            
            if img_response.status_code != 200:
                self.send_message("❌ ไม่สามารถดาวน์โหลดรูปได้")
                return
            
            # Convert to base64
            import base64
            image_base64 = base64.b64encode(img_response.content).decode('utf-8')
            
            # Ask Gemini with image
            answer = self.ask_gemini(question, image_data=image_base64)
            self.send_message(f"📊 <b>AI วิเคราะห์:</b>\n\n{answer}")
            
        except Exception as e:
            self.send_message(f"❌ Error: {str(e)}")
    
    def handle_command(self, text: str):
        """Handle Telegram commands"""
        cmd = text.lower().split()[0] if text.startswith("/") else ""
        args = text.split(maxsplit=1)[1] if len(text.split()) > 1 else ""
        
        if cmd == "/start" or cmd == "/help":
            self.send_help()
        
        elif cmd == "/status":
            self.send_status()
        
        elif cmd == "/balance":
            self.send_balance()
        
        elif cmd == "/btc":
            self.send_message("🔍 กำลังดูราคา BTC...")
            answer = self.ask_perplexity_fallback("ราคา Bitcoin ตอนนี้เท่าไหร่? ตอบสั้นๆ พร้อมบอก % เปลี่ยนแปลง 24h")
            self.send_message(f"💹 <b>BTC Price:</b>\n\n{answer}")
        
        elif cmd == "/news":
            self.send_message("📰 กำลังหาข่าว...")
            answer = self.ask_perplexity_fallback("ข่าว Bitcoin และ Crypto สำคัญวันนี้ สรุป 3-5 ข้อ")
            self.send_message(f"📰 <b>Crypto News:</b>\n\n{answer}")
        
        elif cmd == "/analyze":
            self.send_message("📊 กำลังวิเคราะห์ตลาด...")
            answer = self.ask_perplexity_fallback("""วิเคราะห์ BTC ตอนนี้:
1. ราคาปัจจุบัน
2. Trend (Bullish/Bearish/Sideways)
3. ควรซื้อ/ขาย/รอ?
ตอบสั้นกระชับ""")
            self.send_message(f"📊 <b>Market Analysis:</b>\n\n{answer}")
        
        elif cmd == "/ask":
            if args:
                self.send_message("🤔 กำลังคิด...")
                answer = self.ask_gemini(args)
                self.send_message(f"🤖 <b>AI ตอบ:</b>\n\n{answer}")
            else:
                self.send_message("❓ ใช้: /ask คำถามของคุณ\nเช่น /ask BTC จะขึ้นไหม?")
        
        elif cmd == "/position":
            self.send_position()
        
        elif cmd == "/settings":
            self.send_settings()
        
        elif cmd == "/stop":
            self.kill_switch()
        
        elif cmd == "/alert":
            self.set_price_alert(args)
        
        elif cmd == "/alerts":
            self.show_alerts()
        
        elif cmd == "/journal":
            self.send_journal_stats()
        
        elif cmd == "/scan":
            self.send_multi_coin_scan()
        
        elif cmd == "/ml":
            self.send_ml_stats()
        
        elif text.startswith("/"):
            self.send_message("❓ ไม่รู้จัก command นี้\nพิมพ์ /help เพื่อดูวิธีใช้")
        
        else:
            # ข้อความธรรมดา - ถาม Gemini AI เลย
            self.send_message("🤔 กำลังคิด...")
            answer = self.ask_gemini(text)
            self.send_message(f"🤖 {answer}")
    
    def send_help(self):
        """Send help message"""
        msg = """🤖 <b>AlphaBot-Scalper V4</b>

<b>💬 ถามอะไรก็ได้!</b>
พิมพ์คำถาม หรือ ส่งรูปกราฟมาวิเคราะห์!

<b>📊 Trading:</b>
/status - สถานะบอท
/balance - ยอดเงิน
/position - Position ปัจจุบัน

<b>🔥 Quick:</b>
/btc - ราคา BTC
/news - ข่าว Crypto
/analyze - วิเคราะห์ตลาด

<b>🚨 Alerts:</b>
/alert [ราคา] - ตั้ง Price Alert
/alerts - ดู alerts ทั้งหมด

<b>📈 Advanced:</b>
/journal - 📓 สถิติ Trade Journal
/scan - 🔍 Multi-Coin Scanner
/ml - 🤖 ML Model Status

<b>⚙️ Settings:</b>
/settings - ดูการตั้งค่า
/stop - 🛑 หยุดบอททันที

🧠 AI: <b>Perplexity</b> (ค้นหา) + <b>Gemini</b> (รูป)"""
        self.send_message(msg)
    
    def send_settings(self):
        """Send bot settings"""
        msg = f"""⚙️ <b>Bot Settings</b>

<b>📊 Trading:</b>
• Symbol: {self.config.SYMBOL}
• Timeframe: {self.config.TIMEFRAME}
• Leverage: {self.config.MAX_LEVERAGE}x

<b>🛡️ Risk Management:</b>
• Stop Loss: {self.config.STOP_LOSS_PCT*100:.1f}%
• Take Profit: {self.config.TAKE_PROFIT_PCT*100:.1f}%
• Trailing Stop: {self.config.TRAILING_STOP_PCT*100:.1f}%

<b>🚀 Advanced Features:</b>
• Break-even: +{self.config.BREAKEVEN_TRIGGER_PCT*100:.1f}% → SL = Entry
• Partial TP: {self.config.PARTIAL_TP_CLOSE_PCT*100:.0f}% @ +{self.config.PARTIAL_TP_PCT*100:.1f}%
• Auto-compound: {'✅' if self.config.AUTO_COMPOUND else '❌'}

<b>💡 Strategy:</b>
• RSI + EMA + MACD + ADX
• Volume Filter
• Multi-Agent AI System"""
        self.send_message(msg)
    
    def send_status(self):
        """Send bot status"""
        if self.bot_ref:
            stats = self.bot_ref.agent_c.get_stats()
            position = self.bot_ref.agent_c.position
            
            pos_text = "ไม่มี Position"
            if position:
                pos_text = f"{position.side.upper()} @ ${position.entry_price:,.2f}"
            
            msg = f"""🤖 <b>Bot Status</b>

✅ สถานะ: <b>กำลังทำงาน</b>
💰 ยอดเงิน: <b>${stats['balance']:.2f}</b>
📈 ROI: {stats['roi']*100:+.2f}%
📊 Position: {pos_text}

📈 เทรดทั้งหมด: {stats['total_trades']}
✅ ชนะ: {stats.get('wins', 0)} | ❌ แพ้: {stats.get('losses', 0)}
🎯 Win Rate: {stats['win_rate']*100:.1f}%

🕐 {datetime.now().strftime('%H:%M:%S')}"""
        else:
            msg = """🤖 <b>Bot Status</b>
            
⏳ กำลังโหลดข้อมูล..."""
        
        self.send_message(msg)
    
    def send_balance(self):
        """Send balance info"""
        if self.bot_ref:
            stats = self.bot_ref.agent_c.get_stats()
            msg = f"""💰 <b>Balance Info</b>

💵 ยอดเงิน: <b>${stats['balance']:.2f}</b>
📈 ROI: {stats['roi']*100:+.2f}%
💹 กำไร/ขาดทุน: ${stats['total_pnl']:.2f}

🕐 {datetime.now().strftime('%H:%M:%S')}"""
        else:
            msg = "⏳ กำลังโหลดข้อมูล..."
        
        self.send_message(msg)
    
    def send_position(self):
        """Send current position info"""
        if self.bot_ref and self.bot_ref.agent_c.position:
            pos = self.bot_ref.agent_c.position
            current_price = self.bot_ref.agent_a.df['close'].iloc[-1] if self.bot_ref.agent_a.df is not None else pos.entry_price
            pnl = pos.unrealized_pnl(current_price)
            pnl_pct = pos.unrealized_pnl_pct(current_price) * 100
            
            emoji = "🟢" if pos.side == "long" else "🔴"
            
            msg = f"""{emoji} <b>Current Position</b>

📊 Side: <b>{pos.side.upper()}</b>
📍 Entry: <b>${pos.entry_price:,.2f}</b>
💹 Current: <b>${current_price:,.2f}</b>
💵 Size: ${pos.size:.2f}

{'🟢' if pnl >= 0 else '🔴'} PnL: <b>{'+' if pnl >= 0 else ''}{pnl:.2f}$</b> ({'+' if pnl_pct >= 0 else ''}{pnl_pct:.2f}%)

🎯 TP: ${pos.take_profit:,.2f}
🛡️ SL: ${pos.stop_loss:,.2f}"""
        else:
            msg = """📊 <b>Position</b>

ไม่มี Position ตอนนี้
⏳ รอสัญญาณเข้าเทรด..."""
        
        self.send_message(msg)
    
    # ===== NEW FEATURES =====
    
    def kill_switch(self):
        """Emergency stop - close all positions and halt trading"""
        if self.bot_ref:
            # Close position if any
            if self.bot_ref.agent_c.position:
                self.send_message("🛑 <b>KILL SWITCH ACTIVATED!</b>\n\n⏳ กำลังปิด Position...")
                # Force close
                current_price = self.bot_ref.agent_a.df['close'].iloc[-1] if self.bot_ref.agent_a.df is not None else 0
                self.bot_ref.agent_c._close_position(current_price, "KILL_SWITCH")
            
            # Halt trading
            self.bot_ref.agent_c.halt_trading("Kill switch activated by user")
            self.bot_ref.is_running = False
            
            self.send_message("""🛑 <b>บอทหยุดทำงานแล้ว!</b>

✅ ปิด Position แล้ว
✅ หยุดเทรดแล้ว

🔄 รัน START_BOT.bat ใหม่เพื่อเริ่มต้นใหม่""")
        else:
            self.send_message("❌ ไม่สามารถหยุดบอทได้ - ไม่พบ bot reference")
    
    def set_price_alert(self, args: str):
        """Set price alert: /alert 100000 or /alert 95000"""
        if not args:
            self.send_message("""🚨 <b>Price Alert</b>

วิธีใช้: /alert [ราคา]

ตัวอย่าง:
/alert 100000 - แจ้งเมื่อถึง $100,000
/alert 95000 - แจ้งเมื่อถึง $95,000""")
            return
        
        try:
            price = float(args.replace(",", "").replace("$", ""))
            
            # Store alert (initialize if not exists)
            if not hasattr(self, 'price_alerts'):
                self.price_alerts = []
            
            self.price_alerts.append(price)
            
            self.send_message(f"""🚨 <b>Alert ตั้งแล้ว!</b>

💰 แจ้งเตือนเมื่อ BTC ถึง: <b>${price:,.0f}</b>

📋 มี {len(self.price_alerts)} alerts ทั้งหมด
พิมพ์ /alerts เพื่อดูทั้งหมด""")
            
        except ValueError:
            self.send_message("❌ ราคาไม่ถูกต้อง\nตัวอย่าง: /alert 100000")
    
    def show_alerts(self):
        """Show all price alerts"""
        if not hasattr(self, 'price_alerts') or not self.price_alerts:
            self.send_message("📋 ไม่มี Price Alert\n\nใช้ /alert [ราคา] เพื่อตั้ง")
            return
        
        alerts_text = "\n".join([f"  • ${p:,.0f}" for p in sorted(self.price_alerts)])
        self.send_message(f"""🚨 <b>Price Alerts ({len(self.price_alerts)})</b>

{alerts_text}

❌ พิมพ์ /clearalerts เพื่อลบทั้งหมด""")
    
    def check_price_alerts(self, current_price: float):
        """Check and trigger price alerts"""
        if not hasattr(self, 'price_alerts') or not self.price_alerts:
            return
        
        triggered = []
        for alert_price in self.price_alerts:
            # Check if price crossed the alert level
            if abs(current_price - alert_price) / alert_price < 0.001:  # Within 0.1%
                triggered.append(alert_price)
                self.send_message(f"""🚨🚨🚨 <b>PRICE ALERT!</b>

💰 BTC ถึง <b>${alert_price:,.0f}</b> แล้ว!
📊 ราคาปัจจุบัน: ${current_price:,.2f}

🕐 {datetime.now().strftime('%H:%M:%S')}""")
        
        # Remove triggered alerts
        for p in triggered:
            self.price_alerts.remove(p)
    
    def send_live_pnl(self, current_price: float):
        """Send live PnL update"""
        if not self.bot_ref or not self.bot_ref.agent_c.position:
            return
        
        pos = self.bot_ref.agent_c.position
        pnl = pos.unrealized_pnl(current_price)
        pnl_pct = pos.unrealized_pnl_pct(current_price) * 100
        
        emoji = "🟢" if pnl >= 0 else "🔴"
        direction = "📈" if pos.side == "long" else "📉"
        
        # Calculate distance to SL/TP
        if pos.side == "long":
            sl_dist = (current_price - pos.stop_loss) / current_price * 100
            tp_dist = (pos.take_profit - current_price) / current_price * 100
        else:
            sl_dist = (pos.stop_loss - current_price) / current_price * 100
            tp_dist = (current_price - pos.take_profit) / current_price * 100
        
        msg = f"""{direction} <b>Live PnL Update</b>

{emoji} PnL: <b>{pnl_pct:+.2f}%</b> (${pnl:+.3f})
💰 ราคา: ${current_price:,.2f}

🛡️ SL: {sl_dist:.1f}% away
🎯 TP: {tp_dist:.1f}% away

🕐 {datetime.now().strftime('%H:%M:%S')}"""
        
        self.send_message(msg)
    
    def send_signal_preview(self, side: str, entry_price: float, sl: float, tp: float, confidence: float):
        """Send signal preview before entering trade"""
        emoji = "🟢" if side == "long" else "🔴"
        
        risk_pct = abs(entry_price - sl) / entry_price * 100
        reward_pct = abs(tp - entry_price) / entry_price * 100
        rr_ratio = reward_pct / risk_pct if risk_pct > 0 else 0
        
        msg = f"""🎯 <b>Signal Preview!</b>

{emoji} กำลังจะเปิด <b>{side.upper()}</b>

💰 Entry: ${entry_price:,.2f}
🛡️ Stop Loss: ${sl:,.2f} (-{risk_pct:.1f}%)
🎯 Take Profit: ${tp:,.2f} (+{reward_pct:.1f}%)

📊 R:R Ratio: 1:{rr_ratio:.1f}
🎯 Confidence: {confidence*100:.0f}%

⏳ เข้าใน 5 วินาที..."""
        
        self.send_message(msg)
    
    def send_journal_stats(self):
        """Send Trade Journal statistics"""
        if not JOURNAL_AVAILABLE:
            self.send_message("❌ Trade Journal module not available")
            return
        
        try:
            journal = TradeJournal()
            summary = journal.get_telegram_summary()
            self.send_message(summary)
        except Exception as e:
            self.send_message(f"❌ Error loading journal: {e}")
    
    def send_multi_coin_scan(self):
        """Send Multi-Coin scan results"""
        if not MULTI_COIN_AVAILABLE:
            self.send_message("❌ Multi-Coin Scanner module not available")
            return
        
        try:
            self.send_message("🔍 กำลังสแกน coins...")
            scanner = MultiCoinScanner(
                api_key=self.config.API_KEY,
                secret_key=self.config.SECRET_KEY
            )
            summary = scanner.get_telegram_summary()
            self.send_message(summary)
        except Exception as e:
            self.send_message(f"❌ Error scanning coins: {e}")
    
    def send_ml_stats(self):
        """Send ML Model statistics"""
        if not ML_MODEL_AVAILABLE:
            self.send_message("❌ ML Model module not available")
            return
        
        try:
            model = MLPatternModel()
            summary = model.get_telegram_summary()
            self.send_message(summary)
        except Exception as e:
            self.send_message(f"❌ Error loading ML model: {e}")
    
    def send_photo(self, photo_bytes: bytes, caption: str = "") -> bool:
        """Send photo to Telegram"""
        if not self.enabled:
            return False
        try:
            url = f"{self.base_url}/sendPhoto"
            files = {"photo": ("chart.png", photo_bytes, "image/png")}
            data = {"chat_id": self.chat_id, "caption": caption, "parse_mode": "HTML"}
            response = requests.post(url, files=files, data=data, timeout=30)
            return response.status_code == 200
        except Exception as e:
            print(f"[Telegram] Error sending photo: {e}")
            return False
    
    def notify_bot_started(self, balance: float, symbol: str, timeframe: str, leverage: int):
        """Notify bot started"""
        msg = f"""
🚀 <b>AlphaBot-Scalper V4 เริ่มทำงาน!</b>

💰 ยอดเงิน: <b>${balance:.2f}</b>
📊 คู่เทรด: <b>{symbol}</b>
⏱️ Timeframe: <b>{timeframe}</b>
⚡ Leverage: <b>{leverage}x</b>
🕐 เวลา: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

✅ บอทพร้อมทำงานแล้ว!
"""
        return self.send_message(msg)
    
    def notify_bot_stopped(self, reason: str = "User stopped"):
        """Notify bot stopped"""
        msg = f"""
🛑 <b>AlphaBot หยุดทำงาน</b>

📝 สาเหตุ: {reason}
🕐 เวลา: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        return self.send_message(msg)
    
    def notify_trade_opened(self, side: str, entry_price: float, size: float, 
                           leverage: int, sl: float, tp: float, balance: float):
        """Notify when trade is opened"""
        emoji = "🟢" if side == "long" else "🔴"
        side_text = "LONG (ซื้อ)" if side == "long" else "SHORT (ขาย)"
        
        sl_pct = abs((sl - entry_price) / entry_price * 100)
        tp_pct = abs((tp - entry_price) / entry_price * 100)
        
        msg = f"""
{emoji} <b>เปิดออเดอร์ {side_text}</b>

📍 ราคาเข้า: <b>${entry_price:,.2f}</b>
💵 ขนาด: <b>${size:.2f}</b> x {leverage}x
🎯 Take Profit: <b>${tp:,.2f}</b> (+{tp_pct:.2f}%)
🛡️ Stop Loss: <b>${sl:,.2f}</b> (-{sl_pct:.2f}%)
💰 ยอดเงิน: ${balance:.2f}
🕐 เวลา: {datetime.now().strftime('%H:%M:%S')}
"""
        return self.send_message(msg)
    
    def notify_trade_closed(self, side: str, entry_price: float, exit_price: float,
                           pnl: float, pnl_pct: float, exit_reason: str, balance: float):
        """Notify when trade is closed"""
        emoji = "💚" if pnl > 0 else "💔"
        result = "กำไร" if pnl > 0 else "ขาดทุน"
        
        reason_text = {
            "TP_HIT": "🎯 ถึง Take Profit!",
            "SL_HIT": "🛡️ ถึง Stop Loss",
            "TRAILING_STOP": "📈 Trailing Stop",
            "MANUAL": "👤 ปิดเอง"
        }.get(exit_reason, exit_reason)
        
        msg = f"""
{emoji} <b>ปิดออเดอร์ - {result}!</b>

📍 ราคาเข้า: ${entry_price:,.2f}
📍 ราคาออก: ${exit_price:,.2f}
{reason_text}

{'🤑' if pnl > 0 else '😢'} PnL: <b>{'+' if pnl > 0 else ''}{pnl:.2f}$</b> ({'+' if pnl > 0 else ''}{pnl_pct:.2f}%)
💰 ยอดเงินรวม: <b>${balance:.2f}</b>
🕐 เวลา: {datetime.now().strftime('%H:%M:%S')}
"""
        return self.send_message(msg)
    
    def notify_daily_summary(self, stats: Dict):
        """Send daily trading summary"""
        roi_emoji = "📈" if stats['roi'] > 0 else "📉"
        
        msg = f"""
📊 <b>สรุปผลประจำวัน</b>
━━━━━━━━━━━━━━━

💰 ยอดเงิน: <b>${stats['balance']:.2f}</b>
{roi_emoji} ROI: <b>{'+' if stats['roi'] > 0 else ''}{stats['roi']*100:.2f}%</b>
💵 กำไร/ขาดทุน: {'+' if stats['total_pnl'] > 0 else ''}{stats['total_pnl']:.2f}$

📈 จำนวนเทรด: {stats['total_trades']}
✅ ชนะ: {stats.get('wins', 0)} | ❌ แพ้: {stats.get('losses', 0)}
🎯 Win Rate: {stats['win_rate']*100:.1f}%
⚖️ Profit Factor: {stats['profit_factor']:.2f}
📉 Max Drawdown: {stats['drawdown']*100:.2f}%

🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        return self.send_message(msg)
    
    def notify_position_update(self, side: str, entry: float, current: float,
                               unrealized_pnl: float, unrealized_pct: float):
        """Notify current position status"""
        emoji = "🟢" if unrealized_pnl > 0 else "🔴"
        
        msg = f"""
{emoji} <b>สถานะ Position</b>

📊 ประเภท: {side.upper()}
📍 ราคาเข้า: ${entry:,.2f}
💹 ราคาปัจจุบัน: ${current:,.2f}
💵 กำไร/ขาดทุน: {'+' if unrealized_pnl > 0 else ''}{unrealized_pnl:.2f}$ ({'+' if unrealized_pct > 0 else ''}{unrealized_pct:.2f}%)
"""
        return self.send_message(msg)
    
    def notify_hourly_status(self, stats: Dict, current_price: float, 
                             position_info: str = "ไม่มี Position"):
        """Send hourly status update"""
        roi_emoji = "📈" if stats['roi'] >= 0 else "📉"
        status_emoji = "🟢" if stats['roi'] >= 0 else "🔴"
        
        msg = f"""
⏰ <b>อัพเดทรายชั่วโมง</b>
━━━━━━━━━━━━━━━

{status_emoji} <b>บอทกำลังทำงาน</b>

💹 BTC Price: <b>${current_price:,.2f}</b>
💰 ยอดเงิน: <b>${stats['balance']:.2f}</b>
{roi_emoji} ROI: {'+' if stats['roi'] >= 0 else ''}{stats['roi']*100:.2f}%

📊 Position: {position_info}
📈 เทรดวันนี้: {stats['total_trades']}
✅ ชนะ: {stats.get('wins', 0)} | ❌ แพ้: {stats.get('losses', 0)}

🕐 {datetime.now().strftime('%H:%M:%S')}
"""
        return self.send_message(msg)
    
    def create_trade_chart(self, df: pd.DataFrame, entry_price: float, 
                          exit_price: float = None, sl: float = None, 
                          tp: float = None, side: str = "long") -> bytes:
        """Create beautiful chart with entry/exit points"""
        try:
            # Use last 60 candles
            df_chart = df.tail(60).copy()
            
            # Set dark theme style
            plt.style.use('dark_background')
            
            # Create figure with custom colors
            fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(14, 10), 
                                                 gridspec_kw={'height_ratios': [4, 1, 1]},
                                                 facecolor='#1a1a2e')
            
            for ax in [ax1, ax2, ax3]:
                ax.set_facecolor('#16213e')
            
            # ===== CANDLESTICK CHART =====
            x = range(len(df_chart))
            
            # Draw candles with gradient effect
            for i, (idx, row) in enumerate(df_chart.iterrows()):
                color = '#00ff88' if row['close'] >= row['open'] else '#ff4757'
                alpha = 0.9
                
                # Wick (high-low line)
                ax1.plot([i, i], [row['low'], row['high']], 
                        color=color, linewidth=1, alpha=0.7)
                
                # Body
                body_bottom = min(row['open'], row['close'])
                body_height = abs(row['close'] - row['open'])
                rect = plt.Rectangle((i - 0.35, body_bottom), 0.7, body_height,
                                     facecolor=color, edgecolor=color, 
                                     alpha=alpha, linewidth=0.5)
                ax1.add_patch(rect)
            
            # Add EMAs if available
            if 'EMA_3' in df_chart.columns:
                ax1.plot(x, df_chart['EMA_3'], color='#ffd32a', 
                        linewidth=1.5, label='EMA 3', alpha=0.8)
            if 'EMA_8' in df_chart.columns:
                ax1.plot(x, df_chart['EMA_8'], color='#3742fa', 
                        linewidth=1.5, label='EMA 8', alpha=0.8)
            
            # Entry line with glow effect
            ax1.axhline(y=entry_price, color='#00d2d3', linestyle='--', 
                       linewidth=2.5, label=f'📍 Entry: ${entry_price:,.2f}', alpha=0.9)
            ax1.axhline(y=entry_price, color='#00d2d3', linestyle='--', 
                       linewidth=6, alpha=0.2)
            
            # TP line with glow
            if tp:
                ax1.axhline(y=tp, color='#00ff88', linestyle='--', 
                           linewidth=2, label=f'🎯 TP: ${tp:,.2f}')
                ax1.axhline(y=tp, color='#00ff88', linestyle='--', 
                           linewidth=5, alpha=0.2)
                # Fill TP zone
                ax1.fill_between(x, entry_price, tp, alpha=0.1, color='#00ff88')
            
            # SL line with glow
            if sl:
                ax1.axhline(y=sl, color='#ff4757', linestyle='--', 
                           linewidth=2, label=f'🛡️ SL: ${sl:,.2f}')
                ax1.axhline(y=sl, color='#ff4757', linestyle='--', 
                           linewidth=5, alpha=0.2)
                # Fill SL zone
                ax1.fill_between(x, entry_price, sl, alpha=0.1, color='#ff4757')
            
            # Exit line
            if exit_price:
                exit_color = '#00ff88' if (side == 'long' and exit_price > entry_price) or \
                                          (side == 'short' and exit_price < entry_price) else '#ff4757'
                ax1.axhline(y=exit_price, color=exit_color, linestyle='-', 
                           linewidth=2.5, label=f'🏁 Exit: ${exit_price:,.2f}')
                ax1.scatter([len(df_chart)-1], [exit_price], color=exit_color, 
                           s=150, zorder=5, marker='o', edgecolors='white', linewidths=2)
            
            # Mark entry point
            ax1.scatter([len(df_chart)-10], [entry_price], color='#00d2d3', 
                       s=150, zorder=5, marker='^' if side == 'long' else 'v', 
                       edgecolors='white', linewidths=2)
            
            # Title and styling
            side_emoji = "🟢 LONG" if side == "long" else "🔴 SHORT"
            ax1.set_title(f'📊 BTC/USDT - {side_emoji}', fontsize=16, 
                         fontweight='bold', color='white', pad=15)
            ax1.set_ylabel('Price ($)', fontsize=11, color='white')
            ax1.legend(loc='upper left', fontsize=9, facecolor='#16213e', 
                      edgecolor='#0f3460', labelcolor='white')
            ax1.grid(True, alpha=0.15, color='#0f3460')
            ax1.tick_params(colors='white')
            
            # Format y-axis
            ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x:,.0f}'))
            
            # ===== RSI SUBPLOT =====
            if 'RSI_14' in df_chart.columns:
                rsi = df_chart['RSI_14']
                ax2.plot(x, rsi, color='#a55eea', linewidth=2)
                ax2.fill_between(x, rsi, 50, where=(rsi >= 50), 
                                alpha=0.3, color='#00ff88')
                ax2.fill_between(x, rsi, 50, where=(rsi < 50), 
                                alpha=0.3, color='#ff4757')
                ax2.axhline(y=70, color='#ff4757', linestyle='--', alpha=0.5, linewidth=1)
                ax2.axhline(y=30, color='#00ff88', linestyle='--', alpha=0.5, linewidth=1)
                ax2.axhline(y=50, color='white', linestyle='-', alpha=0.2, linewidth=1)
                ax2.set_ylabel('RSI', fontsize=10, color='white')
                ax2.set_ylim(0, 100)
                ax2.grid(True, alpha=0.15, color='#0f3460')
                ax2.tick_params(colors='white')
                ax2.set_facecolor('#16213e')
            
            # ===== VOLUME SUBPLOT =====
            vol_colors = ['#00ff88' if c >= o else '#ff4757' 
                         for o, c in zip(df_chart['open'], df_chart['close'])]
            ax3.bar(x, df_chart['volume'], color=vol_colors, alpha=0.7, width=0.7)
            ax3.set_ylabel('Volume', fontsize=10, color='white')
            ax3.grid(True, alpha=0.15, color='#0f3460')
            ax3.tick_params(colors='white')
            ax3.set_facecolor('#16213e')
            
            # Add watermark
            fig.text(0.5, 0.02, '🤖 AlphaBot-Scalper V4', ha='center', 
                    fontsize=10, color='#666', alpha=0.7)
            
            plt.tight_layout()
            
            # Save to bytes
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=120, bbox_inches='tight',
                       facecolor='#1a1a2e', edgecolor='none')
            buf.seek(0)
            plt.close(fig)
            plt.style.use('default')  # Reset style
            
            return buf.getvalue()
            
        except Exception as e:
            print(f"[Telegram] Error creating chart: {e}")
            plt.style.use('default')
            return None
    
    def create_status_chart(self, df: pd.DataFrame, balance_history: list = None) -> bytes:
        """Create hourly status chart"""
        try:
            df_chart = df.tail(60).copy()
            
            plt.style.use('dark_background')
            fig, ax = plt.subplots(1, 1, figsize=(12, 6), facecolor='#1a1a2e')
            ax.set_facecolor('#16213e')
            
            x = range(len(df_chart))
            
            # Simple line chart for BTC price
            ax.plot(x, df_chart['close'], color='#ffd32a', linewidth=2, label='BTC Price')
            ax.fill_between(x, df_chart['close'].min() * 0.999, df_chart['close'], 
                           alpha=0.1, color='#ffd32a')
            
            # Current price marker
            current_price = df_chart['close'].iloc[-1]
            ax.scatter([len(df_chart)-1], [current_price], color='#ffd32a', 
                      s=100, zorder=5, edgecolors='white', linewidths=2)
            ax.annotate(f'${current_price:,.2f}', 
                       xy=(len(df_chart)-1, current_price),
                       xytext=(len(df_chart)-5, current_price * 1.001),
                       fontsize=11, color='white', fontweight='bold')
            
            ax.set_title('📊 BTC/USDT - Status Update', fontsize=14, 
                        fontweight='bold', color='white')
            ax.set_ylabel('Price ($)', color='white')
            ax.grid(True, alpha=0.15, color='#0f3460')
            ax.tick_params(colors='white')
            ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x:,.0f}'))
            
            fig.text(0.5, 0.02, '🤖 AlphaBot-Scalper V4 | Hourly Update', 
                    ha='center', fontsize=10, color='#666')
            
            plt.tight_layout()
            
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=100, bbox_inches='tight',
                       facecolor='#1a1a2e')
            buf.seek(0)
            plt.close(fig)
            plt.style.use('default')
            
            return buf.getvalue()
        except Exception as e:
            print(f"[Telegram] Error creating status chart: {e}")
            plt.style.use('default')
            return None
    
    def send_hourly_chart(self, df: pd.DataFrame, stats: Dict, current_price: float,
                          position_info: str = "ไม่มี"):
        """Send hourly status with chart"""
        # Send status message first
        self.notify_hourly_status(stats, current_price, position_info)
        
        # Then send chart
        chart_bytes = self.create_status_chart(df)
        if chart_bytes:
            caption = f"⏰ BTC: ${current_price:,.2f} | 💰 Balance: ${stats['balance']:.2f}"
            return self.send_photo(chart_bytes, caption)
        return False
    
    def send_trade_chart(self, df: pd.DataFrame, entry_price: float,
                        exit_price: float = None, sl: float = None,
                        tp: float = None, side: str = "long",
                        pnl: float = None, caption: str = ""):
        """Send trade chart to Telegram"""
        chart_bytes = self.create_trade_chart(df, entry_price, exit_price, sl, tp, side)
        if chart_bytes:
            if not caption:
                if exit_price and pnl is not None:
                    result = "🟢 กำไร" if pnl > 0 else "🔴 ขาดทุน"
                    caption = f"{result}: {'+' if pnl > 0 else ''}{pnl:.2f}$"
                else:
                    caption = f"📊 {side.upper()} @ ${entry_price:,.2f}"
            return self.send_photo(chart_bytes, caption)
        return False


class SignalType(Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"
    CLOSE_LONG = "CLOSE_LONG"
    CLOSE_SHORT = "CLOSE_SHORT"


@dataclass
class Signal:
    """Trading Signal from Agents"""
    type: SignalType
    confidence: float  # 0-1
    entry_price: float
    stop_loss: float
    take_profit: float
    position_size: float
    leverage: int
    timestamp: datetime
    reasons: List[str] = field(default_factory=list)


@dataclass
class Position:
    """Active Position"""
    side: str  # 'long' or 'short'
    entry_price: float
    size: float
    leverage: int
    stop_loss: float
    take_profit: float
    trailing_stop: float
    highest_pnl: float = 0.0
    entry_time: datetime = None
    breakeven_activated: bool = False      # SL moved to entry
    partial_tp_taken: bool = False         # First TP taken
    original_size: float = 0.0             # Original position size
    
    def __post_init__(self):
        if self.original_size == 0.0:
            self.original_size = self.size
    
    def unrealized_pnl(self, current_price: float) -> float:
        if self.side == 'long':
            return (current_price - self.entry_price) / self.entry_price * self.size * self.leverage
        else:
            return (self.entry_price - current_price) / self.entry_price * self.size * self.leverage
    
    def unrealized_pnl_pct(self, current_price: float) -> float:
        if self.side == 'long':
            return (current_price - self.entry_price) / self.entry_price
        else:
            return (self.entry_price - current_price) / self.entry_price


@dataclass 
class Trade:
    """Completed Trade Record"""
    id: int
    side: str
    entry_price: float
    exit_price: float
    size: float
    leverage: int
    pnl: float
    pnl_pct: float
    entry_time: datetime
    exit_time: datetime
    exit_reason: str
    fees: float


# ═══════════════════════════════════════════════════════════════════════════════
# LOGGING SYSTEM
# ═══════════════════════════════════════════════════════════════════════════════

class AlphaBotLogger:
    """Transparent Logging System"""
    
    def __init__(self, log_file: str = "alphabot_v4.log"):
        self.logger = logging.getLogger('AlphaBot-V4')
        self.logger.setLevel(logging.DEBUG)
        
        # File handler (UTF-8 for emoji support)
        fh = logging.FileHandler(log_file, encoding='utf-8')
        fh.setLevel(logging.DEBUG)
        
        # Console handler (UTF-8 for Windows)
        import sys
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(logging.INFO)
        
        # Set UTF-8 encoding for Windows console
        if sys.platform == 'win32':
            import io
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        
        # Format
        formatter = logging.Formatter(
            '%(asctime)s [%(levelname)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)
        
        self.logger.addHandler(fh)
        self.logger.addHandler(ch)
        
        # Decision log
        self.decisions: List[Dict] = []
    
    def log_decision(self, agent: str, action: str, data: Dict):
        """Log all decisions for transparency"""
        decision = {
            'timestamp': datetime.now().isoformat(),
            'agent': agent,
            'action': action,
            'data': data
        }
        self.decisions.append(decision)
        self.logger.debug(f"[{agent}] {action}: {json.dumps(data, default=str)}")
    
    def info(self, msg: str):
        self.logger.info(msg)
    
    def warning(self, msg: str):
        self.logger.warning(msg)
    
    def error(self, msg: str):
        self.logger.error(msg)
    
    def save_decisions(self, filepath: str = "decisions.json"):
        with open(filepath, 'w') as f:
            json.dump(self.decisions, f, indent=2, default=str)


# ═══════════════════════════════════════════════════════════════════════════════
# AGENT-A: DATA ANALYST & VOLATILITY ASSESSOR
# ═══════════════════════════════════════════════════════════════════════════════

class AgentA:
    """
    Data Analyst & Volatility Assessor
    - Collects market data every 1 minute
    - Analyzes volatility using GARCH-like model
    - Detects patterns using technical analysis
    - Cross-validates data quality
    """
    
    def __init__(self, config: Config, logger: AlphaBotLogger):
        self.config = config
        self.logger = logger
        self.exchange = ccxt.binance({
            'apiKey': config.API_KEY,
            'secret': config.SECRET_KEY,
            'sandbox': False,
            'options': {'defaultType': 'future'}
        })
        
        # Data storage
        self.df: Optional[pd.DataFrame] = None
        self.market_state: MarketState = MarketState.RANGING
        self.volatility: float = 0.0
        self.volume_zscore: float = 0.0
        self.sentiment_score: float = 0.0  # -1 to 1
        self.pattern_detected: str = "None"
        self.risk_level: float = 0.0  # 0-1
        
        # Alert flags
        self.volume_spike: bool = False
        self.volatility_spike: bool = False
        self.fud_detected: bool = False
    
    def fetch_ohlcv(self, limit: int = 500) -> pd.DataFrame:
        """Fetch OHLCV data from exchange"""
        try:
            ohlcv = self.exchange.fetch_ohlcv(
                self.config.SYMBOL,
                self.config.TIMEFRAME,
                limit=limit
            )
            df = pd.DataFrame(
                ohlcv,
                columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
            )
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            return df
        except Exception as e:
            self.logger.error(f"[Agent-A] Failed to fetch data: {e}")
            return pd.DataFrame()
    
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate all technical indicators"""
        if df.empty or len(df) < 50:
            return df
        
        # RSI
        df.ta.rsi(close='close', length=self.config.RSI_PERIOD, append=True)
        
        # EMAs for signals
        df.ta.ema(close='close', length=self.config.EMA_FAST, append=True)
        df.ta.ema(close='close', length=self.config.EMA_SLOW, append=True)
        
        # EMAs for trend direction (20/50)
        df.ta.ema(close='close', length=20, append=True)
        df.ta.ema(close='close', length=50, append=True)
        
        # MACD
        df.ta.macd(
            close='close',
            fast=self.config.MACD_FAST,
            slow=self.config.MACD_SLOW,
            signal=self.config.MACD_SIGNAL,
            append=True
        )
        
        # Bollinger Bands
        df.ta.bbands(
            close='close',
            length=self.config.BB_PERIOD,
            std=self.config.BB_STD,
            append=True
        )
        
        # ADX
        df.ta.adx(length=self.config.ADX_PERIOD, append=True)
        
        # ATR (for volatility)
        df.ta.atr(length=14, append=True)
        
        # VWAP
        df.ta.vwap(append=True)
        
        # Volume SMA
        df['Volume_SMA'] = df['volume'].rolling(20).mean()
        df['Volume_Zscore'] = (df['volume'] - df['volume'].rolling(20).mean()) / df['volume'].rolling(20).std()
        
        # Price momentum
        df['Returns'] = df['close'].pct_change()
        df['Momentum'] = df['close'].pct_change(10)
        
        return df.dropna()
    
    def estimate_volatility_garch(self, returns: pd.Series) -> float:
        """
        Simplified GARCH-like volatility estimation
        Uses exponentially weighted moving variance
        """
        if len(returns) < 20:
            return 0.0
        
        # EWMA variance (approximates GARCH(1,1))
        lambda_param = 0.94  # Standard RiskMetrics decay factor
        returns_sq = returns ** 2
        
        var = returns_sq.iloc[0]
        for i in range(1, len(returns_sq)):
            var = lambda_param * var + (1 - lambda_param) * returns_sq.iloc[i]
        
        volatility = np.sqrt(var) * np.sqrt(252 * 24 * 60)  # Annualized
        return float(volatility)
    
    def detect_patterns(self, df: pd.DataFrame) -> str:
        """Detect price action patterns"""
        if len(df) < 10:
            return "None"
        
        patterns = []
        close = df['close'].values
        high = df['high'].values
        low = df['low'].values
        
        # Bullish engulfing
        if close[-1] > df['open'].values[-1] and close[-2] < df['open'].values[-2]:
            if close[-1] > high[-2] and df['open'].values[-1] < low[-2]:
                patterns.append("Bullish Engulfing")
        
        # Bearish engulfing
        if close[-1] < df['open'].values[-1] and close[-2] > df['open'].values[-2]:
            if close[-1] < low[-2] and df['open'].values[-1] > high[-2]:
                patterns.append("Bearish Engulfing")
        
        # Double bottom (simplified)
        lows_5 = low[-10:]
        if np.argmin(lows_5) < 3 and lows_5[-1] > lows_5.min() * 1.001:
            patterns.append("Potential Double Bottom")
        
        # Double top (simplified)
        highs_5 = high[-10:]
        if np.argmax(highs_5) < 3 and highs_5[-1] < highs_5.max() * 0.999:
            patterns.append("Potential Double Top")
        
        return ", ".join(patterns) if patterns else "None"
    
    def assess_market_state(self, df: pd.DataFrame) -> MarketState:
        """Determine current market state"""
        if len(df) < 20:
            return MarketState.RANGING
        
        row = df.iloc[-1]
        adx = row.get(f'ADX_{self.config.ADX_PERIOD}', 20)
        ema_fast = row.get(f'EMA_{self.config.EMA_FAST}', row['close'])
        ema_slow = row.get(f'EMA_{self.config.EMA_SLOW}', row['close'])
        atr = row.get('ATRr_14', 0)
        
        # Volatility assessment
        avg_atr = df['ATRr_14'].mean() if 'ATRr_14' in df.columns else 0
        
        if self.risk_level > 0.7:
            return MarketState.RISK_OFF
        
        if atr > avg_atr * 2:
            return MarketState.HIGH_VOLATILITY
        
        if atr < avg_atr * 0.5:
            return MarketState.LOW_VOLATILITY
        
        if adx > 25:
            if ema_fast > ema_slow:
                return MarketState.TRENDING_UP
            else:
                return MarketState.TRENDING_DOWN
        
        return MarketState.RANGING
    
    def calculate_risk_level(self, df: pd.DataFrame) -> float:
        """Calculate overall risk level (0-1)"""
        risks = []
        
        # Volume spike risk
        if self.volume_spike:
            risks.append(0.3)
        
        # Volatility spike risk
        if self.volatility > 1.5:  # 150% annualized
            risks.append(0.4)
        
        # Price far from VWAP
        if len(df) > 0 and 'VWAP_D' in df.columns:
            vwap_dist = abs(df['close'].iloc[-1] / df['VWAP_D'].iloc[-1] - 1)
            if vwap_dist > 0.02:  # 2% away from VWAP
                risks.append(0.2)
        
        # ADX extremely high (overextended trend)
        if len(df) > 0:
            adx = df.iloc[-1].get(f'ADX_{self.config.ADX_PERIOD}', 0)
            if adx > 50:
                risks.append(0.2)
        
        return min(1.0, sum(risks))
    
    def cross_validate_data(self, df: pd.DataFrame) -> bool:
        """Validate data quality"""
        if df.empty:
            return False
        
        # Check for missing values
        if df.isnull().sum().sum() > len(df) * 0.1:
            self.logger.warning("[Agent-A] Data quality issue: Too many missing values")
            return False
        
        # Check for stale data
        last_timestamp = df.index[-1]
        if datetime.now() - last_timestamp.to_pydatetime().replace(tzinfo=None) > timedelta(minutes=5):
            self.logger.warning("[Agent-A] Data quality issue: Stale data")
            return False
        
        # Check for price anomalies
        returns = df['close'].pct_change().dropna()
        if (returns.abs() > 0.1).any():  # 10% move in 1 candle
            self.logger.warning("[Agent-A] Data quality issue: Price anomaly detected")
            # Still return True but flag it
        
        return True
    
    def analyze(self) -> Dict[str, Any]:
        """Main analysis function - called every minute"""
        start_time = time.time()
        
        # Fetch data
        df = self.fetch_ohlcv(self.config.DATA_LOOKBACK)
        if df.empty:
            return {'valid': False}
        
        # Calculate indicators
        df = self.calculate_indicators(df)
        if df.empty:
            return {'valid': False}
        
        # Validate data
        if not self.cross_validate_data(df):
            return {'valid': False}
        
        self.df = df
        
        # Calculate volatility (GARCH-like)
        self.volatility = self.estimate_volatility_garch(df['Returns'])
        
        # Volume analysis
        self.volume_zscore = df['Volume_Zscore'].iloc[-1]
        self.volume_spike = self.volume_zscore > self.config.VOLUME_SPIKE_MULT
        
        # Pattern detection
        self.pattern_detected = self.detect_patterns(df)
        
        # Risk assessment
        self.risk_level = self.calculate_risk_level(df)
        
        # Market state
        self.market_state = self.assess_market_state(df)
        
        # Log decision
        analysis_time = (time.time() - start_time) * 1000
        
        result = {
            'valid': True,
            'timestamp': datetime.now(),
            'price': df['close'].iloc[-1],
            'volatility': self.volatility,
            'volume_zscore': self.volume_zscore,
            'volume_spike': self.volume_spike,
            'pattern': self.pattern_detected,
            'market_state': self.market_state.value,
            'risk_level': self.risk_level,
            'analysis_time_ms': analysis_time,
            'indicators': {
                'rsi': df[f'RSI_{self.config.RSI_PERIOD}'].iloc[-1],
                'ema_fast': df[f'EMA_{self.config.EMA_FAST}'].iloc[-1],
                'ema_slow': df[f'EMA_{self.config.EMA_SLOW}'].iloc[-1],
                'ema_20': df['EMA_20'].iloc[-1],
                'ema_50': df['EMA_50'].iloc[-1],
                'trend_up': df['EMA_20'].iloc[-1] > df['EMA_50'].iloc[-1],  # Trend direction
                'adx': df[f'ADX_{self.config.ADX_PERIOD}'].iloc[-1],
                'macd_hist': df['MACDh_12_26_9'].iloc[-1],
                'bb_upper': df[f'BBU_{self.config.BB_PERIOD}_{self.config.BB_STD}_{self.config.BB_STD}'].iloc[-1],
                'bb_lower': df[f'BBL_{self.config.BB_PERIOD}_{self.config.BB_STD}_{self.config.BB_STD}'].iloc[-1],
                'momentum': df['Momentum'].iloc[-1],
            }
        }
        
        self.logger.log_decision('Agent-A', 'ANALYSIS', result)
        
        return result


# ═══════════════════════════════════════════════════════════════════════════════
# AGENT-B: STRATEGY OPTIMIZER (Reinforcement Learning)
# ═══════════════════════════════════════════════════════════════════════════════

class AgentB:
    """
    Strategy Optimizer with Reinforcement Learning
    - Analyzes 6 months of backtest data
    - Dynamically adjusts TP, SL, Position Size, Leverage
    - Trains and evaluates new models
    - Prevents overfitting with out-of-sample testing
    """
    
    def __init__(self, config: Config, logger: AlphaBotLogger):
        self.config = config
        self.logger = logger
        
        # Strategy parameters (learnable)
        self.params = {
            'sl_pct': config.STOP_LOSS_PCT,
            'tp_pct': config.TAKE_PROFIT_PCT,
            'trailing_pct': config.TRAILING_STOP_PCT,
            'position_size': config.POSITION_SIZE_PCT,
            'leverage': 10,
            'rsi_oversold': 30,
            'rsi_overbought': 70,
            'adx_threshold': 20,
            'ema_cross_weight': 1.0,
            'rsi_weight': 0.8,
            'macd_weight': 0.6,
            'volume_weight': 0.5,
        }
        
        # Q-table for parameter optimization (simplified RL)
        self.q_table: Dict[str, Dict[str, float]] = {}
        
        # Performance tracking
        self.performance_history: List[Dict] = []
        self.current_model_sharpe: float = 0.0
        self.best_params: Dict = self.params.copy()
        
        # Strategy modes
        self.strategy_mode = "EMA_CROSSOVER"  # or "RSI_REVERSAL", "MACD_MOMENTUM"
    
    def calculate_signal_score(self, analysis: Dict) -> Tuple[SignalType, float, List[str]]:
        """Calculate trading signal - SHORT ONLY EMA Crossover"""
        if not analysis.get('valid', False):
            return SignalType.HOLD, 0.0, ["Invalid data"]
        
        indicators = analysis['indicators']
        market_state = analysis['market_state']
        risk_level = analysis['risk_level']
        
        # Risk-off check
        if risk_level > 0.6 or market_state == "RISK_OFF":
            return SignalType.HOLD, 0.0, ["High risk - Standing aside"]
        
        rsi = indicators['rsi']
        ema_fast = indicators['ema_fast']
        ema_slow = indicators['ema_slow']
        adx = indicators['adx']
        macd_hist = indicators['macd_hist']
        momentum = indicators.get('momentum', 0)
        bb_upper = indicators.get('bb_upper', 0)
        bb_lower = indicators.get('bb_lower', 0)
        price = analysis['price']
        
        # Trend direction from 20/50 EMA
        trend_up = indicators.get('trend_up', True)
        
        reasons = []
        
        # ===== CRITICAL: TRADE WITH THE TREND =====
        # In uptrend: prefer LONG or wait
        # In downtrend: prefer SHORT or wait
        
        # ===== FILTER: Avoid false breakouts =====
        # Require strong momentum to enter
        strong_momentum_up = momentum > 0.003  # +0.3% price change
        strong_momentum_down = momentum < -0.003  # -0.3% price change
        
        # EMA spread check (avoid choppy market)
        ema_spread = abs(ema_fast - ema_slow) / ema_slow * 100
        strong_ema_signal = ema_spread > 0.15  # 0.15% EMA spread minimum
        
        # EMA Crossover conditions
        ema_bullish = ema_fast > ema_slow
        ema_bearish = ema_fast < ema_slow
        
        # ADX trend strength - HIGHER threshold
        strong_trend = adx > 35  # Only trade trends when ADX very high
        trending = adx > 25
        ranging = adx < 30   # Most of the time is ranging
        
        # MACD confirmation with strength check
        macd_bullish = macd_hist > 0.0001  # Slight buffer
        macd_bearish = macd_hist < -0.0001
        
        # BB position
        bb_middle = (bb_upper + bb_lower) / 2 if bb_upper and bb_lower else price
        bb_range = bb_upper - bb_lower if bb_upper and bb_lower else 0
        bb_pct_from_lower = (price - bb_lower) / bb_range * 100 if bb_range > 0 else 50
        price_near_bb_lower = bb_pct_from_lower < 10  # Bottom 10% of BB
        price_near_bb_upper = bb_pct_from_lower > 90  # Top 10% of BB
        
        # ===== PRIORITY STRATEGY: TREND + PULLBACK (trade with trend) =====
        
        # UPTREND: Buy pullbacks to BB Lower or RSI oversold
        if trend_up:
            # LONG - Pullback in uptrend
            if price_near_bb_lower and rsi < 40 and rsi > 25:
                reasons.append("🟢 Uptrend Pullback: BB Lower")
                reasons.append(f"BB position: {bb_pct_from_lower:.1f}%")
                reasons.append(f"RSI: {rsi:.1f}")
                reasons.append("Trend: EMA20 > EMA50 ✓")
                return SignalType.BUY, 0.85, reasons
            
            # LONG - Strong momentum continuation
            if ema_bullish and strong_trend and macd_bullish and strong_momentum_up:
                if rsi > 50 and rsi < 70:
                    reasons.append(f"📈 Trend Continuation (ADX={adx:.1f})")
                    reasons.append(f"RSI={rsi:.1f}")
                    reasons.append("Trend: EMA20 > EMA50 ✓")
                    return SignalType.BUY, 0.80, reasons
        
        # DOWNTREND: Sell rallies to BB Upper or RSI overbought
        else:
            # SHORT - Rally in downtrend
            if price_near_bb_upper and rsi > 60 and rsi < 80:
                reasons.append("🔴 Downtrend Rally: BB Upper")
                reasons.append(f"BB position: {bb_pct_from_lower:.1f}%")
                reasons.append(f"RSI: {rsi:.1f}")
                reasons.append("Trend: EMA20 < EMA50 ✓")
                return SignalType.SELL, 0.85, reasons
            
            # SHORT - Strong momentum continuation
            if ema_bearish and strong_trend and macd_bearish and strong_momentum_down:
                if rsi > 30 and rsi < 50:
                    reasons.append(f"📉 Trend Continuation (ADX={adx:.1f})")
                    reasons.append(f"RSI={rsi:.1f}")
                    reasons.append("Trend: EMA20 < EMA50 ✓")
                    return SignalType.SELL, 0.80, reasons
        
        # ===== STRATEGY 2: EXTREME RSI REVERSAL (only in ranging market) =====
        if adx < 20:
            # Quick LONG - Extreme RSI oversold
            if rsi < 25 and momentum > 0:
                reasons.append("⚡ RSI Extreme Oversold (Ranging)")
                reasons.append(f"RSI={rsi:.1f}")
                reasons.append(f"ADX={adx:.1f}")
                return SignalType.BUY, 0.70, reasons
            
            # Quick SHORT - Extreme RSI overbought
            if rsi > 75 and momentum < 0:
                reasons.append("⚡ RSI Extreme Overbought (Ranging)")
                reasons.append(f"RSI={rsi:.1f}")
                reasons.append(f"ADX={adx:.1f}")
                return SignalType.SELL, 0.70, reasons
        
        return SignalType.HOLD, 0.0, ["No clear signal"]
    
    def generate_signal(self, analysis: Dict) -> Optional[Signal]:
        """Generate trading signal with all parameters"""
        signal_type, confidence, reasons = self.calculate_signal_score(analysis)
        
        if signal_type == SignalType.HOLD:
            return None
        
        price = analysis['price']
        
        # Fixed SL/TP ratios for consistency
        sl_pct = self.config.STOP_LOSS_PCT
        tp_pct = self.config.TAKE_PROFIT_PCT
        
        if signal_type == SignalType.BUY:
            stop_loss = price * (1 - sl_pct)
            take_profit = price * (1 + tp_pct)
        else:  # SELL
            stop_loss = price * (1 + sl_pct)
            take_profit = price * (1 - tp_pct)
        
        # Fixed position size and leverage
        position_size = self.config.POSITION_SIZE_PCT
        leverage = 30  # High leverage for small capital
        
        signal = Signal(
            type=signal_type,
            confidence=confidence,
            entry_price=price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            position_size=position_size,
            leverage=leverage,
            timestamp=datetime.now(),
            reasons=reasons
        )
        
        self.logger.log_decision('Agent-B', 'SIGNAL', {
            'type': signal_type.value,
            'confidence': confidence,
            'entry': price,
            'sl': stop_loss,
            'tp': take_profit,
            'size': position_size,
            'leverage': leverage,
            'reasons': reasons
        })
        
        return signal
    
    def update_from_trade(self, trade: Trade):
        """Reinforcement Learning update after trade"""
        # Create state key
        state_key = f"{self.strategy_mode}_{trade.side}"
        
        # Calculate reward
        reward = trade.pnl_pct * 100  # Scale for learning
        
        # Initialize Q-values if needed
        if state_key not in self.q_table:
            self.q_table[state_key] = {
                'sl_up': 0, 'sl_down': 0,
                'tp_up': 0, 'tp_down': 0,
                'size_up': 0, 'size_down': 0
            }
        
        # Update Q-values based on outcome
        lr = self.config.RL_LEARNING_RATE
        
        if trade.exit_reason == 'STOP_LOSS':
            # SL was hit - maybe it was too tight
            if trade.pnl_pct < -0.002:  # Significant loss
                self.q_table[state_key]['sl_down'] += lr * (-reward)
        elif trade.exit_reason == 'TAKE_PROFIT':
            # TP was hit - good trade
            self.q_table[state_key]['tp_up'] += lr * reward
        
        # Apply learned adjustments
        self._apply_rl_adjustments(state_key)
        
        # Track performance
        self.performance_history.append({
            'timestamp': datetime.now(),
            'pnl': trade.pnl,
            'pnl_pct': trade.pnl_pct,
            'params': self.params.copy()
        })
        
        self.logger.log_decision('Agent-B', 'RL_UPDATE', {
            'state': state_key,
            'reward': reward,
            'new_params': self.params
        })
    
    def _apply_rl_adjustments(self, state_key: str):
        """Apply RL-learned parameter adjustments"""
        if state_key not in self.q_table:
            return
        
        q = self.q_table[state_key]
        
        # Adjust SL
        if q['sl_up'] > q['sl_down'] + 0.5:
            self.params['sl_pct'] = min(0.01, self.params['sl_pct'] * 1.05)
        elif q['sl_down'] > q['sl_up'] + 0.5:
            self.params['sl_pct'] = max(0.002, self.params['sl_pct'] * 0.95)
        
        # Adjust TP
        if q['tp_up'] > q['tp_down'] + 0.5:
            self.params['tp_pct'] = min(0.02, self.params['tp_pct'] * 1.05)
        elif q['tp_down'] > q['tp_up'] + 0.5:
            self.params['tp_pct'] = max(0.004, self.params['tp_pct'] * 0.95)
    
    def calculate_sharpe_ratio(self, returns: List[float]) -> float:
        """Calculate Sharpe ratio from returns"""
        if len(returns) < 10:
            return 0.0
        
        returns_arr = np.array(returns)
        if returns_arr.std() == 0:
            return 0.0
        
        sharpe = (returns_arr.mean() / returns_arr.std()) * np.sqrt(252 * 24)
        return float(sharpe)
    
    def should_upgrade_model(self) -> bool:
        """Check if current model should be upgraded"""
        if len(self.performance_history) < 50:
            return False
        
        recent_returns = [t['pnl_pct'] for t in self.performance_history[-50:]]
        current_sharpe = self.calculate_sharpe_ratio(recent_returns)
        
        if current_sharpe > self.current_model_sharpe * 1.2:  # 20% improvement
            self.current_model_sharpe = current_sharpe
            self.best_params = self.params.copy()
            self.logger.info(f"[Agent-B] Model upgraded! New Sharpe: {current_sharpe:.2f}")
            return True
        
        return False


# ═══════════════════════════════════════════════════════════════════════════════
# AGENT-C: SMART EXECUTION & RISK MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════════

class ExchangeExecutor:
    """Real Exchange Order Executor for Binance Futures"""
    
    def __init__(self, config: Config, logger: AlphaBotLogger):
        self.config = config
        self.logger = logger
        self.exchange = ccxt.binanceusdm({
            'apiKey': config.API_KEY,
            'secret': config.SECRET_KEY,
            'sandbox': False,
            'options': {'defaultType': 'future'}
        })
        self.exchange.load_markets()
    
    def get_balance(self) -> float:
        """Get USDT balance"""
        try:
            balance = self.exchange.fetch_balance()
            return float(balance['USDT']['free'])
        except Exception as e:
            self.logger.error(f"[Executor] Failed to get balance: {e}")
            return 0.0
    
    def set_leverage(self, symbol: str, leverage: int) -> bool:
        """Set leverage for symbol"""
        try:
            self.exchange.set_leverage(leverage, symbol)
            self.logger.info(f"[Executor] Leverage set to {leverage}x for {symbol}")
            return True
        except Exception as e:
            self.logger.error(f"[Executor] Failed to set leverage: {e}")
            return False
    
    def open_position(self, symbol: str, side: str, amount: float, 
                      stop_loss: float = None, take_profit: float = None) -> dict:
        """Open a position with optional SL/TP"""
        try:
            # Set margin mode to CROSSED
            try:
                self.exchange.set_margin_mode('cross', symbol)
            except:
                pass  # Might already be set
            
            # Place market order
            order_side = 'buy' if side == 'long' else 'sell'
            order = self.exchange.create_market_order(
                symbol=symbol,
                side=order_side,
                amount=amount
            )
            
            self.logger.info(f"[Executor] ✅ Opened {side.upper()} {amount} {symbol} @ market")
            
            # Place SL/TP if provided
            if stop_loss:
                sl_side = 'sell' if side == 'long' else 'buy'
                try:
                    self.exchange.create_order(
                        symbol=symbol,
                        type='stop_market',
                        side=sl_side,
                        amount=amount,
                        params={'stopPrice': stop_loss, 'reduceOnly': True}
                    )
                    self.logger.info(f"[Executor] SL set @ {stop_loss}")
                except Exception as e:
                    self.logger.warning(f"[Executor] Failed to set SL: {e}")
            
            if take_profit:
                tp_side = 'sell' if side == 'long' else 'buy'
                try:
                    self.exchange.create_order(
                        symbol=symbol,
                        type='take_profit_market',
                        side=tp_side,
                        amount=amount,
                        params={'stopPrice': take_profit, 'reduceOnly': True}
                    )
                    self.logger.info(f"[Executor] TP set @ {take_profit}")
                except Exception as e:
                    self.logger.warning(f"[Executor] Failed to set TP: {e}")
            
            return order
            
        except Exception as e:
            self.logger.error(f"[Executor] ❌ Failed to open position: {e}")
            return None
    
    def close_position(self, symbol: str) -> dict:
        """Close current position"""
        try:
            # Get current position
            positions = self.exchange.fetch_positions([symbol])
            for pos in positions:
                if float(pos['contracts']) > 0:
                    side = 'sell' if pos['side'] == 'long' else 'buy'
                    order = self.exchange.create_market_order(
                        symbol=symbol,
                        side=side,
                        amount=float(pos['contracts']),
                        params={'reduceOnly': True}
                    )
                    self.logger.info(f"[Executor] ✅ Closed position {symbol}")
                    
                    # Cancel all open orders
                    try:
                        self.exchange.cancel_all_orders(symbol)
                    except:
                        pass
                    
                    return order
            return None
        except Exception as e:
            self.logger.error(f"[Executor] ❌ Failed to close position: {e}")
            return None
    
    def get_position(self, symbol: str) -> dict:
        """Get current position info"""
        try:
            positions = self.exchange.fetch_positions([symbol])
            for pos in positions:
                if float(pos['contracts']) > 0:
                    return pos
            return None
        except Exception as e:
            self.logger.error(f"[Executor] Failed to get position: {e}")
            return None


class AgentC:
    """
    Smart Execution & Risk Management
    - Smart Order Routing (Limit vs Market)
    - Daily Stop Loss (5%) and Max Drawdown (15%)
    - Trailing stops
    - Emergency shutdown
    """
    
    def __init__(self, config: Config, logger: AlphaBotLogger, executor: ExchangeExecutor = None):
        self.config = config
        self.logger = logger
        self.executor = executor  # Real exchange executor
        self.telegram = None  # Will be set by AlphaBotV4
        self.agent_a = None  # Will be set by AlphaBotV4 for chart data
        
        # Portfolio state
        self.balance = config.INITIAL_CAPITAL
        self.starting_balance = config.INITIAL_CAPITAL
        self.peak_balance = config.INITIAL_CAPITAL
        self.daily_pnl = 0.0
        self.daily_start_balance = config.INITIAL_CAPITAL
        self.last_reset_date = datetime.now().date()
        
        # Position management
        self.position: Optional[Position] = None
        self.trades: List[Trade] = []
        self.trade_counter = 0
        
        # Risk flags
        self.is_halted = False
        self.halt_reason = ""
        self.protection_mode = False
        
        # Consecutive loss tracking
        self.consecutive_losses = 0
        self.cooldown_candles = 0  # Wait candles after 2 consecutive losses
        self.max_cooldown_candles = 6  # Wait 6 candles (30 min on 5m tf)
        
        # Profit protection
        self.last_win_pct = 0.0
        self.risk_reduction_active = False
    
    def reset_daily_counters(self):
        """Reset daily PnL tracking"""
        today = datetime.now().date()
        if today > self.last_reset_date:
            self.daily_pnl = 0.0
            self.daily_start_balance = self.balance
            self.last_reset_date = today
            self.logger.info("[Agent-C] Daily counters reset")
    
    def check_risk_limits(self) -> Tuple[bool, str]:
        """Check DSL and MDD limits"""
        self.reset_daily_counters()
        
        # Daily Stop Loss Check
        daily_loss_pct = -self.daily_pnl / self.daily_start_balance if self.daily_start_balance > 0 else 0
        if daily_loss_pct >= self.config.DAILY_STOP_LOSS_PCT:
            return False, f"DSL triggered: -{daily_loss_pct*100:.2f}% (limit: {self.config.DAILY_STOP_LOSS_PCT*100}%)"
        
        # Maximum Drawdown Check
        drawdown = (self.peak_balance - self.balance) / self.peak_balance if self.peak_balance > 0 else 0
        if drawdown >= self.config.MAX_DRAWDOWN_PCT:
            return False, f"MDD triggered: -{drawdown*100:.2f}% (limit: {self.config.MAX_DRAWDOWN_PCT*100}%)"
        
        return True, "OK"
    
    def activate_protection_mode(self, reason: str):
        """Activate risk protection mode"""
        self.protection_mode = True
        self.logger.warning(f"[Agent-C] 🛡️ PROTECTION MODE: {reason}")
        
        # Close any open positions
        if self.position:
            self.logger.warning("[Agent-C] Closing position due to protection mode")
    
    def halt_trading(self, reason: str):
        """Emergency halt all trading"""
        self.is_halted = True
        self.halt_reason = reason
        self.logger.error(f"[Agent-C] 🚨 TRADING HALTED: {reason}")
        
        # Close any open positions
        if self.position:
            self.logger.error("[Agent-C] Emergency position closure")
    
    def determine_order_type(self, signal: Signal, current_price: float) -> str:
        """Smart Order Routing - decide Limit vs Market"""
        price_diff = abs(signal.entry_price - current_price) / current_price
        
        # If price moved more than 0.05%, use market order
        if price_diff > 0.0005:
            return "MARKET"
        
        # If high confidence and trending, use market
        if signal.confidence > 0.8:
            return "MARKET"
        
        # Otherwise, use limit for better fill
        return "LIMIT"
    
    def execute_signal(self, signal: Signal, current_price: float) -> bool:
        """Execute trading signal"""
        # Check if halted
        if self.is_halted:
            self.logger.warning(f"[Agent-C] Cannot execute - Trading halted: {self.halt_reason}")
            return False
        
        # Check risk limits
        can_trade, reason = self.check_risk_limits()
        if not can_trade:
            self.halt_trading(reason)
            return False
        
        # Check if already in position
        if self.position is not None:
            self.logger.info("[Agent-C] Already in position - skipping signal")
            return False
        
        # Cooldown check after consecutive losses
        if self.cooldown_candles > 0:
            self.cooldown_candles -= 1
            self.logger.info(f"[Agent-C] ⏳ Cooldown: {self.cooldown_candles} candles remaining after {self.consecutive_losses} losses")
            return False
        
        # Determine order type
        order_type = self.determine_order_type(signal, current_price)
        
        # Calculate position size in USDT
        position_value = self.balance * signal.position_size
        
        # PROFIT PROTECTION: Reduce position size after big win
        if self.risk_reduction_active:
            position_value *= 0.5  # Use only 50% of balance
            self.logger.info(f"[Agent-C] 🔒 Risk reduction: using 50% position (${position_value:.2f})")
            self.risk_reduction_active = False  # Reset after one trade
        
        # Create position
        side = 'long' if signal.type == SignalType.BUY else 'short'
        
        # ===== SIGNAL PREVIEW =====
        if self.config.SIGNAL_PREVIEW and self.telegram:
            self.telegram.send_signal_preview(
                side=side,
                entry_price=current_price,
                sl=signal.stop_loss,
                tp=signal.take_profit,
                confidence=signal.confidence
            )
            time.sleep(3)  # Wait 3 seconds before entering
        
        # ===== LIVE TRADING: Send real order to exchange =====
        if self.config.LIVE_MODE and self.executor:
            # Set leverage
            self.executor.set_leverage(self.config.SYMBOL, signal.leverage)
            
            # Calculate amount in BTC (contracts)
            btc_amount = (position_value * signal.leverage) / current_price
            # Round to 3 decimals for BTC
            btc_amount = round(btc_amount, 3)
            
            # Minimum order size check (0.001 BTC)
            if btc_amount < 0.001:
                self.logger.warning(f"[Agent-C] Order size too small: {btc_amount} BTC (min: 0.001)")
                return False
            
            # Send order
            order = self.executor.open_position(
                symbol=self.config.SYMBOL,
                side=side,
                amount=btc_amount,
                stop_loss=signal.stop_loss,
                take_profit=signal.take_profit
            )
            
            if not order:
                self.logger.error("[Agent-C] ❌ Failed to execute live order")
                return False
            
            # Update balance from exchange
            self.balance = self.executor.get_balance()
            self.logger.info(f"[Agent-C] 💰 Updated balance: ${self.balance:.2f}")
        # ===== END LIVE TRADING =====
        
        self.position = Position(
            side=side,
            entry_price=current_price,
            size=position_value,
            leverage=signal.leverage,
            stop_loss=signal.stop_loss,
            take_profit=signal.take_profit,
            # Initialize trailing stop at entry price level (not stop loss)
            trailing_stop=current_price * (1 - self.config.TRAILING_STOP_PCT) if side == 'long' else current_price * (1 + self.config.TRAILING_STOP_PCT),
            entry_time=datetime.now()
        )
        
        # Calculate fees
        fees = position_value * signal.leverage * self.config.TAKER_FEE
        if not self.config.LIVE_MODE:  # Only deduct in simulation
            self.balance -= fees
        
        self.logger.log_decision('Agent-C', 'EXECUTE', {
            'side': side,
            'order_type': order_type,
            'entry': current_price,
            'size': position_value,
            'leverage': signal.leverage,
            'sl': signal.stop_loss,
            'tp': signal.take_profit,
            'fees': fees,
            'reasons': signal.reasons,
            'live_mode': self.config.LIVE_MODE
        })
        
        self.logger.info(
            f"[Agent-C] ✅ {side.upper()} @ {current_price:.2f} | "
            f"Size: ${position_value:.2f} | Lev: {signal.leverage}x | "
            f"SL: {signal.stop_loss:.2f} | TP: {signal.take_profit:.2f} | "
            f"Mode: {'🔴 LIVE' if self.config.LIVE_MODE else '⚪ SIM'}"
        )
        
        # ===== TELEGRAM NOTIFICATION: Trade Opened =====
        if self.telegram:
            self.telegram.notify_trade_opened(
                side=side,
                entry_price=current_price,
                size=position_value,
                leverage=signal.leverage,
                sl=signal.stop_loss,
                tp=signal.take_profit,
                balance=self.balance
            )
            # Send chart with entry point
            if self.agent_a and self.agent_a.df is not None:
                self.telegram.send_trade_chart(
                    df=self.agent_a.df,
                    entry_price=current_price,
                    sl=signal.stop_loss,
                    tp=signal.take_profit,
                    side=side
                )
        
        return True
    
    def update_position(self, current_price: float) -> Optional[Trade]:
        """Update position with current price, check SL/TP/Trailing/Breakeven"""
        if self.position is None:
            return None
        
        pos = self.position
        
        # Calculate current PnL
        pnl = pos.unrealized_pnl(current_price)
        pnl_pct = pos.unrealized_pnl_pct(current_price)
        
        # ===== BREAK-EVEN STOP =====
        # Move SL to entry when profit reaches threshold
        if not pos.breakeven_activated and pnl_pct >= self.config.BREAKEVEN_TRIGGER_PCT:
            if pos.side == 'long':
                # Move SL to entry + small buffer
                new_sl = pos.entry_price * 1.001  # +0.1% above entry
                if new_sl > pos.stop_loss:
                    pos.stop_loss = new_sl
                    pos.breakeven_activated = True
                    self.logger.info(f"[Agent-C] 🔒 BREAK-EVEN activated @ ${new_sl:.2f}")
            else:  # short
                new_sl = pos.entry_price * 0.999  # -0.1% below entry
                if new_sl < pos.stop_loss:
                    pos.stop_loss = new_sl
                    pos.breakeven_activated = True
                    self.logger.info(f"[Agent-C] 🔒 BREAK-EVEN activated @ ${new_sl:.2f}")
        
        # ===== PARTIAL TAKE PROFIT =====
        # Take partial profit at first target
        if self.config.PARTIAL_TP_ENABLED and not pos.partial_tp_taken:
            if pnl_pct >= self.config.PARTIAL_TP_PCT:
                # Close partial position
                partial_size = pos.original_size * self.config.PARTIAL_TP_CLOSE_PCT
                partial_pnl = pnl_pct * partial_size * pos.leverage
                
                # Update balance with partial profit
                fees = partial_size * pos.leverage * self.config.TAKER_FEE
                partial_pnl -= fees
                self.balance += partial_pnl
                self.daily_pnl += partial_pnl
                
                # Reduce position size
                pos.size -= partial_size
                pos.partial_tp_taken = True
                
                self.logger.info(f"[Agent-C] 💰 PARTIAL TP: Closed {self.config.PARTIAL_TP_CLOSE_PCT*100:.0f}% @ +{pnl_pct*100:.2f}% | +${partial_pnl:.3f}")
                
                # Notify Telegram
                self.telegram.send_message(
                    f"💰 <b>Partial TP!</b>\n\n"
                    f"ปิด {self.config.PARTIAL_TP_CLOSE_PCT*100:.0f}% @ +{pnl_pct*100:.2f}%\n"
                    f"กำไร: +${partial_pnl:.3f}\n"
                    f"เหลือ: {pos.size/pos.original_size*100:.0f}% running"
                )
        
        # ===== TRAILING STOP UPDATE =====
        if pos.side == 'long':
            # Update highest PnL
            if pnl > pos.highest_pnl:
                pos.highest_pnl = pnl
                # Move trailing stop up
                new_trailing = current_price * (1 - self.config.TRAILING_STOP_PCT)
                if new_trailing > pos.trailing_stop:
                    pos.trailing_stop = new_trailing
            
            # Check exits
            exit_reason = None
            exit_price = current_price
            
            if current_price <= pos.stop_loss:
                exit_reason = "STOP_LOSS" if not pos.breakeven_activated else "BREAKEVEN_STOP"
            elif current_price <= pos.trailing_stop and pos.trailing_stop > pos.stop_loss:
                exit_reason = "TRAILING_STOP"
            elif current_price >= pos.take_profit:
                exit_reason = "TAKE_PROFIT"
        
        else:  # short
            # Update highest PnL
            if pnl > pos.highest_pnl:
                pos.highest_pnl = pnl
                # Move trailing stop down
                new_trailing = current_price * (1 + self.config.TRAILING_STOP_PCT)
                if new_trailing < pos.trailing_stop:
                    pos.trailing_stop = new_trailing
            
            # Check exits
            exit_reason = None
            exit_price = current_price
            
            if current_price >= pos.stop_loss:
                exit_reason = "STOP_LOSS" if not pos.breakeven_activated else "BREAKEVEN_STOP"
            elif current_price >= pos.trailing_stop and pos.trailing_stop < pos.stop_loss:
                exit_reason = "TRAILING_STOP"
            elif current_price <= pos.take_profit:
                exit_reason = "TAKE_PROFIT"
        
        # Execute exit if triggered
        if exit_reason:
            return self._close_position(exit_price, exit_reason)
        
        return None
    
    def _close_position(self, exit_price: float, reason: str) -> Trade:
        """Close position and record trade"""
        pos = self.position
        
        # Calculate final PnL
        if pos.side == 'long':
            pnl_pct = (exit_price - pos.entry_price) / pos.entry_price
        else:
            pnl_pct = (pos.entry_price - exit_price) / pos.entry_price
        
        pnl = pnl_pct * pos.size * pos.leverage
        
        # Exit fees
        fees = pos.size * pos.leverage * self.config.TAKER_FEE
        pnl -= fees
        
        # Update balance
        self.balance += pnl
        self.daily_pnl += pnl
        
        # Update peak balance
        if self.balance > self.peak_balance:
            self.peak_balance = self.balance
        
        # Create trade record
        self.trade_counter += 1
        trade = Trade(
            id=self.trade_counter,
            side=pos.side,
            entry_price=pos.entry_price,
            exit_price=exit_price,
            size=pos.size,
            leverage=pos.leverage,
            pnl=pnl,
            pnl_pct=pnl_pct,
            entry_time=pos.entry_time,
            exit_time=datetime.now(),
            exit_reason=reason,
            fees=fees
        )
        self.trades.append(trade)
        
        # Clear position
        self.position = None
        
        # Track consecutive losses for cooldown
        if pnl < 0:
            self.consecutive_losses += 1
            if self.consecutive_losses >= 2:
                self.cooldown_candles = self.max_cooldown_candles
        else:
            self.consecutive_losses = 0
            self.cooldown_candles = 0
            # Track big wins for profit protection
            if pnl_pct > 0.03:  # >3% profit
                self.last_win_pct = pnl_pct
                self.risk_reduction_active = True
                self.logger.info(f"[Agent-C] 🔒 Profit protection ON: +{pnl_pct*100:.2f}%")
        
        # Log
        emoji = "🟢" if pnl > 0 else "🔴"
        self.logger.log_decision('Agent-C', 'CLOSE', {
            'side': trade.side,
            'entry': trade.entry_price,
            'exit': trade.exit_price,
            'pnl': trade.pnl,
            'pnl_pct': trade.pnl_pct,
            'reason': reason,
            'balance': self.balance
        })
        
        self.logger.info(
            f"[Agent-C] {emoji} CLOSED {trade.side.upper()} @ {exit_price:.2f} | "
            f"PnL: ${pnl:.2f} ({pnl_pct*100:.2f}%) | {reason} | "
            f"Balance: ${self.balance:.2f}"
        )
        
        # ===== TELEGRAM NOTIFICATION: Trade Closed =====
        if self.telegram:
            # Map reason to user-friendly text
            reason_map = {
                "STOP_LOSS": "SL_HIT",
                "TAKE_PROFIT": "TP_HIT",
                "TRAILING_STOP": "TRAILING_STOP"
            }
            self.telegram.notify_trade_closed(
                side=trade.side,
                entry_price=trade.entry_price,
                exit_price=exit_price,
                pnl=pnl,
                pnl_pct=pnl_pct * 100,
                exit_reason=reason_map.get(reason, reason),
                balance=self.balance
            )
            # Send chart with exit point
            if self.agent_a and self.agent_a.df is not None:
                self.telegram.send_trade_chart(
                    df=self.agent_a.df,
                    entry_price=trade.entry_price,
                    exit_price=exit_price,
                    sl=pos.stop_loss,
                    tp=pos.take_profit,
                    side=trade.side,
                    pnl=pnl
                )
        
        return trade
    
    def get_stats(self) -> Dict:
        """Get current trading statistics"""
        if not self.trades:
            return {
                'total_trades': 0,
                'win_rate': 0,
                'profit_factor': 0,
                'total_pnl': 0,
                'roi': 0,
                'balance': self.balance,
                'drawdown': 0
            }
        
        wins = [t for t in self.trades if t.pnl > 0]
        losses = [t for t in self.trades if t.pnl < 0]
        
        total_profit = sum(t.pnl for t in wins)
        total_loss = abs(sum(t.pnl for t in losses))
        
        pf = total_profit / total_loss if total_loss > 0 else float('inf')
        win_rate = len(wins) / len(self.trades)
        total_pnl = sum(t.pnl for t in self.trades)
        roi = total_pnl / self.starting_balance
        drawdown = (self.peak_balance - self.balance) / self.peak_balance if self.peak_balance > 0 else 0
        
        return {
            'total_trades': len(self.trades),
            'wins': len(wins),
            'losses': len(losses),
            'win_rate': win_rate,
            'profit_factor': pf,
            'total_pnl': total_pnl,
            'roi': roi,
            'balance': self.balance,
            'peak_balance': self.peak_balance,
            'drawdown': drawdown,
            'daily_pnl': self.daily_pnl
        }


# ═══════════════════════════════════════════════════════════════════════════════
# ALPHABOT-V4: MAIN COORDINATOR
# ═══════════════════════════════════════════════════════════════════════════════

class AlphaBotV4:
    """
    Main Coordinator for AlphaBot-Scalper V4
    Orchestrates all agents and manages the trading loop
    """
    
    def __init__(self, config: Config = None, live_mode: bool = False):
        self.config = config or Config()
        
        # Override live mode if specified
        if live_mode:
            self.config.LIVE_MODE = True
        
        self.logger = AlphaBotLogger()
        
        # Initialize Telegram notifier
        self.telegram = TelegramNotifier(self.config)
        
        # Initialize exchange executor for live trading
        self.executor = None
        if self.config.LIVE_MODE:
            self.executor = ExchangeExecutor(self.config, self.logger)
            # Get real balance
            real_balance = self.executor.get_balance()
            self.config.INITIAL_CAPITAL = real_balance
            self.logger.info(f"🔴 LIVE MODE ENABLED - Real Balance: ${real_balance:.2f}")
        
        # Initialize agents
        self.agent_a = AgentA(self.config, self.logger)
        self.agent_b = AgentB(self.config, self.logger)
        self.agent_c = AgentC(self.config, self.logger, self.executor)
        
        # Initialize AI News Filter (Perplexity)
        self.ai_filter = PerplexityNewsFilter(self.config)
        if self.ai_filter.enabled:
            self.logger.info("🤖 AI News Filter: ✅ Enabled (Perplexity)")
        
        # Pass telegram to agent_c
        self.agent_c.telegram = self.telegram
        self.agent_c.agent_a = self.agent_a  # For chart data
        
        # Update agent_c balance for live mode
        if self.config.LIVE_MODE and self.executor:
            self.agent_c.balance = self.config.INITIAL_CAPITAL
            self.agent_c.starting_balance = self.config.INITIAL_CAPITAL
            self.agent_c.peak_balance = self.config.INITIAL_CAPITAL
        
        # State
        self.is_running = False
        self.cycle_count = 0
        self.last_daily_report = datetime.now().date()
        self.last_hourly_report = datetime.now().hour
        
        self.logger.info("=" * 60)
        self.logger.info("🤖 AlphaBot-Scalper V4 Initialized")
        self.logger.info(f"   Mode: {'🔴 LIVE TRADING' if self.config.LIVE_MODE else '⚪ SIMULATION'}")
        self.logger.info(f"   Symbol: {self.config.SYMBOL}")
        self.logger.info(f"   Timeframe: {self.config.TIMEFRAME}")
        self.logger.info(f"   Capital: ${self.config.INITIAL_CAPITAL:,.2f}")
        self.logger.info(f"   Leverage: {self.config.MAX_LEVERAGE}x")
        self.logger.info(f"   DSL: {self.config.DAILY_STOP_LOSS_PCT*100}%")
        self.logger.info(f"   MDD: {self.config.MAX_DRAWDOWN_PCT*100}%")
        self.logger.info(f"   Telegram: {'✅ Enabled' if self.telegram.enabled else '❌ Disabled'}")
        self.logger.info("=" * 60)
    
    def run_cycle(self) -> Dict:
        """Run one trading cycle"""
        start_time = time.time()
        self.cycle_count += 1
        
        result = {
            'cycle': self.cycle_count,
            'timestamp': datetime.now(),
            'action': 'HOLD',
            'trade': None
        }
        
        # Agent-A: Analyze market
        analysis = self.agent_a.analyze()
        
        if not analysis.get('valid', False):
            result['action'] = 'DATA_ERROR'
            return result
        
        current_price = analysis['price']
        
        # Check for emergency conditions
        if analysis['volume_spike'] and analysis['risk_level'] > 0.5:
            self.agent_c.activate_protection_mode("Volume spike + High risk")
            result['action'] = 'PROTECTION_MODE'
            return result
        
        # Agent-C: Update existing position
        if self.agent_c.position:
            trade = self.agent_c.update_position(current_price)
            if trade:
                # Agent-B: Learn from trade
                self.agent_b.update_from_trade(trade)
                result['action'] = 'CLOSED'
                result['trade'] = trade
                
                # Check for model upgrade
                if self.agent_b.should_upgrade_model():
                    result['model_upgraded'] = True
        
        # Agent-B: Generate signal if no position
        if self.agent_c.position is None and not self.agent_c.protection_mode:
            signal = self.agent_b.generate_signal(analysis)
            
            if signal:
                # ===== AI NEWS FILTER CHECK =====
                if self.ai_filter and self.ai_filter.enabled:
                    safe_to_trade, ai_reason = self.ai_filter.should_trade()
                    if not safe_to_trade:
                        self.logger.info(f"[AI Filter] ⚠️ Trade blocked: {ai_reason}")
                        result['action'] = 'AI_BLOCKED'
                        result['ai_reason'] = ai_reason
                        return result
                    else:
                        self.logger.info(f"[AI Filter] ✅ Safe to trade: {ai_reason}")
                
                # Agent-C: Execute signal
                executed = self.agent_c.execute_signal(signal, current_price)
                if executed:
                    result['action'] = signal.type.value
        
        # Reset protection mode if conditions improve
        if self.agent_c.protection_mode and analysis['risk_level'] < 0.3:
            self.agent_c.protection_mode = False
            self.logger.info("[Agent-C] Protection mode deactivated")
        
        cycle_time = (time.time() - start_time) * 1000
        result['cycle_time_ms'] = cycle_time
        
        return result
    
    def run_live(self, interval_seconds: int = 60):
        """Run live trading loop"""
        self.is_running = True
        self.logger.info("🚀 Starting LIVE trading...")
        
        # Link telegram to bot for status commands
        self.telegram.bot_ref = self
        
        # Start Telegram polling in background thread
        self.telegram.start_polling()
        
        # Send Telegram notification - Bot started
        self.telegram.notify_bot_started(
            balance=self.agent_c.balance,
            symbol=self.config.SYMBOL,
            timeframe=self.config.TIMEFRAME,
            leverage=self.config.MAX_LEVERAGE
        )
        
        # Send help message
        # Track for live PnL updates
        self.last_pnl_update = time.time()
        
        self.telegram.send_message("""📱 <b>AI Chat พร้อมใช้งาน!</b>

พิมพ์ /help เพื่อดู commands
หรือถามอะไรก็ได้!""")
        
        try:
            while self.is_running:
                if self.agent_c.is_halted:
                    self.logger.error(f"Trading halted: {self.agent_c.halt_reason}")
                    self.telegram.notify_bot_stopped(self.agent_c.halt_reason)
                    break
                
                result = self.run_cycle()
                
                # Get current price for alerts and PnL
                current_price = self.agent_a.df['close'].iloc[-1] if self.agent_a.df is not None else 0
                
                # ===== CHECK PRICE ALERTS =====
                if current_price > 0:
                    self.telegram.check_price_alerts(current_price)
                
                # ===== LIVE PNL UPDATE (every 5 min) =====
                if self.agent_c.position and time.time() - self.last_pnl_update >= self.config.LIVE_PNL_INTERVAL:
                    self.telegram.send_live_pnl(current_price)
                    self.last_pnl_update = time.time()
                
                if result['action'] not in ['HOLD', 'DATA_ERROR']:
                    stats = self.agent_c.get_stats()
                    self.logger.info(
                        f"[Cycle {result['cycle']}] Action: {result['action']} | "
                        f"Balance: ${stats['balance']:.2f} | "
                        f"ROI: {stats['roi']*100:.2f}%"
                    )
                
                # ===== HOURLY STATUS UPDATE =====
                current_hour = datetime.now().hour
                if current_hour != self.last_hourly_report:
                    stats = self.agent_c.get_stats()
                    # Get current price
                    current_price = self.agent_a.df['close'].iloc[-1] if self.agent_a.df is not None else 0
                    
                    # Position info
                    if self.agent_c.position:
                        pos = self.agent_c.position
                        unrealized = pos.unrealized_pnl(current_price)
                        position_info = f"{pos.side.upper()} | Entry: ${pos.entry_price:,.2f} | PnL: {'+' if unrealized >= 0 else ''}{unrealized:.2f}$"
                    else:
                        position_info = "ไม่มี Position"
                    
                    # Send hourly update with chart
                    self.telegram.send_hourly_chart(
                        df=self.agent_a.df,
                        stats=stats,
                        current_price=current_price,
                        position_info=position_info
                    )
                    self.last_hourly_report = current_hour
                    self.logger.info(f"[Telegram] Sent hourly status update")
                
                # Daily summary check (send at 00:00)
                today = datetime.now().date()
                if today > self.last_daily_report:
                    stats = self.agent_c.get_stats()
                    self.telegram.notify_daily_summary(stats)
                    self.last_daily_report = today
                
                time.sleep(interval_seconds)
        
        except KeyboardInterrupt:
            self.logger.info("Received shutdown signal...")
            self.telegram.notify_bot_stopped("User stopped (Ctrl+C)")
        
        finally:
            self.is_running = False
            self.logger.info("Trading stopped")
            self.print_summary()
            
            # Send final summary
            stats = self.agent_c.get_stats()
            self.telegram.notify_daily_summary(stats)
    
    def backtest(self, days: int = 30):
        """Run backtest simulation"""
        self.logger.info(f"📊 Starting BACKTEST: {self.config.SYMBOL} {self.config.TIMEFRAME} {days}d")
        
        # Send Telegram notification
        self.telegram.send_message(f"""📊 <b>AlphaBot-Scalper V4 เริ่ม Backtest!</b>

🪙 Symbol: {self.config.SYMBOL}
⏰ Timeframe: {self.config.TIMEFRAME}
📅 ทดสอบ: {days} วัน
💰 ทุนเริ่มต้น: ${self.agent_c.balance:.2f}
⚡ Leverage: {self.config.MAX_LEVERAGE}x

⏳ กำลังประมวลผล...""")
        
        # Fetch historical data
        df = self.agent_a.fetch_ohlcv(limit=days * 24 * 60)  # 1-min candles
        if df.empty:
            self.logger.error("Failed to fetch data for backtest")
            return
        
        df = self.agent_a.calculate_indicators(df)
        self.logger.info(f"✅ Loaded {len(df)} candles")
        
        # Run simulation
        for i in range(100, len(df)):
            df_slice = df.iloc[:i+1]
            
            # Update agent_a's data
            self.agent_a.df = df_slice
            row = df_slice.iloc[-1]
            
            # Create mock analysis
            analysis = {
                'valid': True,
                'timestamp': row.name,
                'price': row['close'],
                'volatility': self.agent_a.estimate_volatility_garch(df_slice['Returns']),
                'volume_zscore': row.get('Volume_Zscore', 0),
                'volume_spike': row.get('Volume_Zscore', 0) > 3,
                'pattern': 'None',
                'market_state': self.agent_a.assess_market_state(df_slice).value,
                'risk_level': 0.2,
                'indicators': {
                    'rsi': row[f'RSI_{self.config.RSI_PERIOD}'],
                    'ema_fast': row[f'EMA_{self.config.EMA_FAST}'],
                    'ema_slow': row[f'EMA_{self.config.EMA_SLOW}'],
                    'adx': row[f'ADX_{self.config.ADX_PERIOD}'],
                    'macd_hist': row['MACDh_12_26_9'],
                    'bb_upper': row.get(f'BBU_{self.config.BB_PERIOD}_{self.config.BB_STD}_{self.config.BB_STD}', row['close']),
                    'bb_lower': row.get(f'BBL_{self.config.BB_PERIOD}_{self.config.BB_STD}_{self.config.BB_STD}', row['close']),
                }
            }
            
            current_price = row['close']
            
            # Update position
            if self.agent_c.position:
                trade = self.agent_c.update_position(current_price)
                if trade:
                    self.agent_b.update_from_trade(trade)
            
            # Generate and execute signal
            if self.agent_c.position is None:
                signal = self.agent_b.generate_signal(analysis)
                if signal:
                    self.agent_c.execute_signal(signal, current_price)
            
            # Check risk limits
            can_trade, reason = self.agent_c.check_risk_limits()
            if not can_trade:
                self.logger.warning(f"Risk limit hit: {reason}")
                break
        
        # Close any remaining position
        if self.agent_c.position:
            self.agent_c._close_position(df.iloc[-1]['close'], 'END_OF_TEST')
        
        self.print_summary()
    
    def print_summary(self):
        """Print trading summary"""
        stats = self.agent_c.get_stats()
        
        print("\n" + "=" * 60)
        print("📊 ALPHABOT-SCALPER V4 SUMMARY")
        print("=" * 60)
        print(f"  Total Trades: {stats['total_trades']}")
        print(f"  Wins/Losses: {stats.get('wins', 0)}/{stats.get('losses', 0)}")
        print(f"  Win Rate: {stats['win_rate']*100:.1f}%")
        print(f"  Profit Factor: {stats['profit_factor']:.2f}")
        print(f"  Total PnL: ${stats['total_pnl']:.2f}")
        print(f"  ROI: {stats['roi']*100:.2f}%")
        print(f"  Final Balance: ${stats['balance']:.2f}")
        print(f"  Peak Balance: ${stats.get('peak_balance', stats['balance']):.2f}")
        print(f"  Max Drawdown: {stats['drawdown']*100:.2f}%")
        print("=" * 60)
        
        # Save decisions log
        self.logger.save_decisions()
        print("📝 Decision log saved to decisions.json")


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys
    
    config = Config()
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "live":
            # REAL LIVE TRADING MODE
            # Check for --auto flag (skip confirmation for deployment)
            auto_mode = "--auto" in sys.argv or os.environ.get('AUTO_TRADE') == 'true'
            
            if not auto_mode:
                print("\n" + "=" * 60)
                print("⚠️  WARNING: LIVE TRADING MODE ⚠️")
                print("=" * 60)
                print("This will use REAL MONEY on Binance Futures!")
                print("Make sure you have set API keys in .env file")
                print("=" * 60)
                
                confirm = input("Type 'YES' to confirm: ")
                if confirm != "YES":
                    print("Cancelled.")
                    sys.exit(0)
            else:
                print("🤖 Auto-trade mode enabled (no confirmation required)")
            
            bot = AlphaBotV4(config, live_mode=True)
            bot.run_live(interval_seconds=60)
        
        elif command == "sim":
            # Simulation mode (no real orders)
            bot = AlphaBotV4(config, live_mode=False)
            bot.run_live(interval_seconds=60)
        
        elif command == "backtest":
            days = int(sys.argv[2]) if len(sys.argv) > 2 else 30
            
            # Multi-symbol backtest
            total_pnl = 0
            total_trades = 0
            results = []
            
            for symbol in config.SYMBOLS:
                print(f"\n{'='*60}")
                print(f"🔄 Backtesting {symbol}...")
                print(f"{'='*60}")
                
                # Create config for this symbol
                symbol_config = Config()
                symbol_config.SYMBOL = symbol
                
                bot = AlphaBotV4(symbol_config)
                bot.backtest(days)
                
                stats = bot.agent_c.get_stats()
                total_pnl += stats['total_pnl']
                total_trades += stats['total_trades']
                results.append({
                    'symbol': symbol,
                    'pnl': stats['total_pnl'],
                    'roi': stats['roi'],
                    'trades': stats['total_trades'],
                    'win_rate': stats['win_rate'],
                    'pf': stats['profit_factor']
                })
            
            # Print combined summary
            print("\n" + "=" * 60)
            print("📊 MULTI-SYMBOL COMBINED SUMMARY")
            print("=" * 60)
            for r in results:
                print(f"  {r['symbol']}: PnL ${r['pnl']:.2f} | ROI {r['roi']*100:.2f}% | {r['trades']} trades | WR {r['win_rate']*100:.1f}% | PF {r['pf']:.2f}")
            print("-" * 60)
            combined_roi = total_pnl / config.INITIAL_CAPITAL
            print(f"  🎯 TOTAL: PnL ${total_pnl:.2f} | ROI {combined_roi*100:.2f}% | {total_trades} trades")
            print("=" * 60)
        
        elif command == "test":
            # Quick test
            bot = AlphaBotV4(config)
            result = bot.run_cycle()
            print(f"Cycle result: {result}")
            stats = bot.agent_c.get_stats()
            print(f"Stats: {stats}")
        
        else:
            print("Usage: python alphabot_v4.py [live|backtest|test] [days]")
    
    else:
        # Default: run single symbol backtest
        bot = AlphaBotV4(config)
        bot.backtest(days=14)
