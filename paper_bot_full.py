#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                     📝 PAPER TRADE BOT - FULL VERSION                        ║
║              เหมือน Bot เงินจริงทุกอย่าง - ส่งกราฟ + แจ้งเตือน                 ║
║              แค่ไม่เปิด Order จริง (เงินปลอม)                                  ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import ccxt
import pandas as pd
import pandas_ta as ta
import numpy as np
import os
import time
import json
import requests
import io
from datetime import datetime
from dotenv import load_dotenv

# Matplotlib สำหรับส่งกราฟ
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

load_dotenv()

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

# Top 30 coins
COINS = [
    'DOGE/USDT', 'ETC/USDT', 'INJ/USDT', 'NEAR/USDT', 'RUNE/USDT',
    'SOL/USDT', 'AVAX/USDT', 'FIL/USDT', 'ARB/USDT', 'OP/USDT',
    'SEI/USDT', 'SUI/USDT', '1000PEPE/USDT', 'WIF/USDT', 'ORDI/USDT',
    'STX/USDT', 'IMX/USDT', 'FTM/USDT', 'AAVE/USDT', 'GRT/USDT',
    'BTC/USDT', 'ETH/USDT', 'XRP/USDT', 'BNB/USDT', 'ADA/USDT',
    'LINK/USDT', 'DOT/USDT', 'POL/USDT', 'LTC/USDT', 'UNI/USDT',
]

# Trading Settings - Option A: Scalping เร็ว
INITIAL_BALANCE = 4.50
LEVERAGE = 20  # 20x leverage
SL_PCT = 0.015  # 1.5% SL (= -30% ที่ 20x leverage)
TP_PCT = 0.020  # 2% TP (= +40% ที่ 20x leverage) Risk:Reward = 1:1.33
TIMEFRAME = '5m'
SCAN_INTERVAL = 30
MAX_POSITIONS = 3

# Telegram
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '')
TELEGRAM_ENABLED = True

# 📊 Live Status & Alert Settings
LIVE_STATUS_INTERVAL = 15  # ส่ง Live Status ทุก 15 นาที
PNL_ALERT_THRESHOLD = 10   # แจ้งเตือนเมื่อ PnL เกิน ±10%
CHART_INTERVAL = 60        # ส่งกราฟ positions ทุก 60 นาที

# ═══════════════════════════════════════════════════════════════════════════════
# TELEGRAM NOTIFIER - ส่งกราฟ + ข้อความเหมือน Bot จริง
# ═══════════════════════════════════════════════════════════════════════════════

class TelegramNotifier:
    def __init__(self):
        self.token = TELEGRAM_BOT_TOKEN
        self.chat_id = TELEGRAM_CHAT_ID
        self.enabled = TELEGRAM_ENABLED and self.token and self.chat_id
        self.base_url = f"https://api.telegram.org/bot{self.token}"
        
    def send_message(self, text: str) -> bool:
        if not self.enabled:
            return False
        try:
            url = f"{self.base_url}/sendMessage"
            data = {"chat_id": self.chat_id, "text": text, "parse_mode": "HTML"}
            response = requests.post(url, data=data, timeout=10)
            return response.status_code == 200
        except Exception as e:
            print(f"⚠️ Telegram error: {e}")
            return False
    
    def send_photo(self, photo_bytes: bytes, caption: str = "") -> bool:
        if not self.enabled:
            return False
        try:
            url = f"{self.base_url}/sendPhoto"
            files = {"photo": ("chart.png", photo_bytes, "image/png")}
            data = {"chat_id": self.chat_id, "caption": caption, "parse_mode": "HTML"}
            response = requests.post(url, files=files, data=data, timeout=30)
            return response.status_code == 200
        except Exception as e:
            print(f"⚠️ Telegram photo error: {e}")
            return False
    
    def create_chart(self, df: pd.DataFrame, symbol: str, entry_price: float,
                     sl: float, tp: float, side: str, exit_price: float = None) -> bytes:
        """สร้างกราฟสวยๆ เหมือน Bot จริง"""
        try:
            df_chart = df.tail(60).copy()
            
            plt.style.use('dark_background')
            fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(14, 10),
                                                 gridspec_kw={'height_ratios': [4, 1, 1]},
                                                 facecolor='#1a1a2e')
            for ax in [ax1, ax2, ax3]:
                ax.set_facecolor('#16213e')
            
            x = range(len(df_chart))
            
            # Candlestick
            for i, (idx, row) in enumerate(df_chart.iterrows()):
                color = '#00ff88' if row['close'] >= row['open'] else '#ff4757'
                ax1.plot([i, i], [row['low'], row['high']], color=color, linewidth=1, alpha=0.7)
                body_bottom = min(row['open'], row['close'])
                body_height = abs(row['close'] - row['open'])
                rect = plt.Rectangle((i - 0.35, body_bottom), 0.7, body_height,
                                     facecolor=color, edgecolor=color, alpha=0.9)
                ax1.add_patch(rect)
            
            # EMAs
            if 'ema_fast' in df_chart.columns:
                ax1.plot(x, df_chart['ema_fast'], color='#ffd32a', linewidth=1.5, label='EMA 3', alpha=0.8)
            if 'ema_slow' in df_chart.columns:
                ax1.plot(x, df_chart['ema_slow'], color='#3742fa', linewidth=1.5, label='EMA 8', alpha=0.8)
            
            # Entry line
            ax1.axhline(y=entry_price, color='#00d2d3', linestyle='--', linewidth=2.5, 
                       label=f'📍 Entry: ${entry_price:,.4f}')
            
            # TP line
            ax1.axhline(y=tp, color='#00ff88', linestyle='--', linewidth=2, 
                       label=f'🎯 TP: ${tp:,.4f}')
            ax1.fill_between(x, entry_price, tp, alpha=0.1, color='#00ff88')
            
            # SL line
            ax1.axhline(y=sl, color='#ff4757', linestyle='--', linewidth=2, 
                       label=f'🛡️ SL: ${sl:,.4f}')
            ax1.fill_between(x, entry_price, sl, alpha=0.1, color='#ff4757')
            
            # Exit line
            if exit_price:
                exit_color = '#00ff88' if (side == 'LONG' and exit_price > entry_price) or \
                                          (side == 'SHORT' and exit_price < entry_price) else '#ff4757'
                ax1.axhline(y=exit_price, color=exit_color, linestyle='-', linewidth=2.5,
                           label=f'🏁 Exit: ${exit_price:,.4f}')
                ax1.scatter([len(df_chart)-1], [exit_price], color=exit_color,
                           s=150, zorder=5, marker='o', edgecolors='white', linewidths=2)
            
            # Entry marker
            ax1.scatter([len(df_chart)-10], [entry_price], color='#00d2d3',
                       s=150, zorder=5, marker='^' if side == 'LONG' else 'v',
                       edgecolors='white', linewidths=2)
            
            side_emoji = "🟢 LONG" if side == "LONG" else "🔴 SHORT"
            ax1.set_title(f'📝 PAPER TRADE | {symbol} - {side_emoji}', fontsize=16,
                         fontweight='bold', color='white', pad=15)
            ax1.set_ylabel('Price ($)', fontsize=11, color='white')
            ax1.legend(loc='upper left', fontsize=9, facecolor='#16213e')
            ax1.grid(True, alpha=0.15, color='#0f3460')
            ax1.tick_params(colors='white')
            
            # RSI
            if 'rsi' in df_chart.columns:
                rsi = df_chart['rsi']
                ax2.plot(x, rsi, color='#a55eea', linewidth=2)
                ax2.fill_between(x, rsi, 50, where=(rsi >= 50), alpha=0.3, color='#00ff88')
                ax2.fill_between(x, rsi, 50, where=(rsi < 50), alpha=0.3, color='#ff4757')
                ax2.axhline(y=70, color='#ff4757', linestyle='--', alpha=0.5)
                ax2.axhline(y=30, color='#00ff88', linestyle='--', alpha=0.5)
                ax2.set_ylabel('RSI', fontsize=10, color='white')
                ax2.set_ylim(0, 100)
                ax2.grid(True, alpha=0.15)
                ax2.tick_params(colors='white')
            
            # Volume
            vol_colors = ['#00ff88' if c >= o else '#ff4757' 
                         for o, c in zip(df_chart['open'], df_chart['close'])]
            ax3.bar(x, df_chart['volume'], color=vol_colors, alpha=0.7, width=0.7)
            ax3.set_ylabel('Volume', fontsize=10, color='white')
            ax3.grid(True, alpha=0.15)
            ax3.tick_params(colors='white')
            
            # Watermark
            fig.text(0.5, 0.02, '📝 PAPER TRADE - จำลองเท่านั้น ไม่ใช่เงินจริง!', 
                    ha='center', fontsize=11, color='#ff6b6b', fontweight='bold')
            
            plt.tight_layout()
            
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=120, bbox_inches='tight',
                       facecolor='#1a1a2e', edgecolor='none')
            buf.seek(0)
            plt.close(fig)
            plt.style.use('default')
            
            return buf.getvalue()
            
        except Exception as e:
            print(f"⚠️ Chart error: {e}")
            plt.style.use('default')
            return None


# ═══════════════════════════════════════════════════════════════════════════════
# PAPER TRADE BOT - ทำงานเหมือน Bot จริงทุกอย่าง
# ═══════════════════════════════════════════════════════════════════════════════

class PaperTradeBotFull:
    def __init__(self):
        print("🔄 เชื่อมต่อ Binance Futures...")
        self.exchange = ccxt.binanceusdm({
            'enableRateLimit': True,
            'options': {'defaultType': 'future'}
        })
        
        self.telegram = TelegramNotifier()
        self.balance = INITIAL_BALANCE
        self.positions = {}
        self.trade_history = []
        self.df_cache = {}  # Cache dataframes for charts
        self.stats = {
            'total_trades': 0,
            'wins': 0,
            'losses': 0,
            'total_pnl': 0.0,
            'best_trade': 0.0,
            'worst_trade': 0.0,
            'long_wins': 0,
            'long_losses': 0,
            'short_wins': 0,
            'short_losses': 0,
        }
        
        # Tracking for Live Status & Alerts
        # ตั้งค่าเป็น 0 เพื่อส่งทันทีตอนเริ่มรัน
        self.last_live_status = 0
        self.last_chart_update = 0
        self.last_pnl_alert = {}  # Track per-position alerts
        
        try:
            self.exchange.load_markets()
            print(f"✅ โหลด {len(self.exchange.markets)} ตลาด")
        except Exception as e:
            print(f"⚠️ Warning: {e}")
        
        # ส่งข้อความเริ่มต้น
        self.notify_bot_started()
    
    def notify_bot_started(self):
        """แจ้งเตือน Bot เริ่มทำงาน - เหมือน Bot จริง"""
        msg = f"""
🚀 <b>📝 PAPER TRADE BOT เริ่มทำงาน!</b>

⚠️ <i>จำลองเท่านั้น - ไม่ใช่เงินจริง!</i>

💰 เงินจำลอง: <b>${INITIAL_BALANCE:.2f}</b>
📊 เหรียญ: <b>{len(COINS)} เหรียญ</b>
⏱️ Timeframe: <b>{TIMEFRAME}</b>
⚡ Leverage: <b>{LEVERAGE}x</b>
🛡️ SL: {SL_PCT*100}% | 🎯 TP: {TP_PCT*100}%
📊 Max Positions: {MAX_POSITIONS}
🕐 เวลา: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

✅ บอทพร้อมจำลองการเทรดแล้ว!
"""
        self.telegram.send_message(msg)
    
    def get_data_with_indicators(self, symbol: str) -> pd.DataFrame:
        """ดึงข้อมูลพร้อม Indicators"""
        try:
            ohlcv = self.exchange.fetch_ohlcv(symbol, TIMEFRAME, limit=100)
            if len(ohlcv) < 60:
                return None
            
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            
            # Calculate indicators
            df['rsi'] = ta.rsi(df['close'], length=14)
            df['ema_fast'] = ta.ema(df['close'], length=3)
            df['ema_slow'] = ta.ema(df['close'], length=8)
            df['ema_20'] = ta.ema(df['close'], length=20)
            df['ema_50'] = ta.ema(df['close'], length=50)
            
            adx_df = ta.adx(df['high'], df['low'], df['close'], length=14)
            df['adx'] = adx_df['ADX_14'] if 'ADX_14' in adx_df.columns else 25
            
            macd = ta.macd(df['close'], fast=12, slow=26, signal=9)
            df['macd_hist'] = macd['MACDh_12_26_9']
            
            return df
            
        except Exception as e:
            print(f"⚠️ Error getting data for {symbol}: {e}")
            return None
    
    def get_signal(self, df: pd.DataFrame) -> dict:
        """วิเคราะห์สัญญาณ"""
        row = df.iloc[-1]
        
        rsi = float(row['rsi']) if pd.notna(row['rsi']) else 50
        adx = float(row['adx']) if pd.notna(row['adx']) else 25
        ema_fast = float(row['ema_fast']) if pd.notna(row['ema_fast']) else 0
        ema_slow = float(row['ema_slow']) if pd.notna(row['ema_slow']) else 0
        ema_20 = float(row['ema_20']) if pd.notna(row['ema_20']) else 0
        ema_50 = float(row['ema_50']) if pd.notna(row['ema_50']) else 0
        macd_hist = float(row['macd_hist']) if pd.notna(row['macd_hist']) else 0
        price = float(row['close'])
        
        trend_up = ema_20 > ema_50
        
        # LONG Signal
        if trend_up and adx > 30 and ema_fast > ema_slow and macd_hist > 0:
            if 45 < rsi < 70:
                return {
                    'signal': 'LONG',
                    'price': price,
                    'reason': f'Uptrend | ADX:{adx:.0f} | RSI:{rsi:.0f} | MACD+',
                    'confidence': min(90, 50 + adx),
                    'rsi': rsi,
                    'adx': adx
                }
        
        # SHORT Signal
        if not trend_up and adx > 30 and ema_fast < ema_slow and macd_hist < 0:
            if 30 < rsi < 55:
                return {
                    'signal': 'SHORT',
                    'price': price,
                    'reason': f'Downtrend | ADX:{adx:.0f} | RSI:{rsi:.0f} | MACD-',
                    'confidence': min(90, 50 + adx),
                    'rsi': rsi,
                    'adx': adx
                }
        
        return {'signal': 'NONE', 'price': price}
    
    def open_position(self, symbol: str, side: str, price: float, reason: str, df: pd.DataFrame):
        """เปิด Position + ส่งกราฟ + แจ้งเตือน - เหมือน Bot จริง"""
        if symbol in self.positions or len(self.positions) >= MAX_POSITIONS:
            return False
        
        position_value = self.balance / MAX_POSITIONS
        
        if side == 'LONG':
            sl = price * (1 - SL_PCT)
            tp = price * (1 + TP_PCT)
        else:
            sl = price * (1 + SL_PCT)
            tp = price * (1 - TP_PCT)
        
        self.positions[symbol] = {
            'side': side,
            'entry_price': price,
            'size': position_value,
            'sl': sl,
            'tp': tp,
            'open_time': datetime.now().isoformat(),
            'reason': reason
        }
        
        self.df_cache[symbol] = df  # Save for chart
        
        # Print
        emoji = "🟢" if side == "LONG" else "🔴"
        print(f"\n{emoji} [PAPER] เปิด {side} {symbol}")
        print(f"   📍 Entry: ${price:,.4f}")
        print(f"   🛡️ SL: ${sl:,.4f} | 🎯 TP: ${tp:,.4f}")
        
        # ส่งกราฟ + ข้อความ Telegram - เหมือน Bot จริง!
        sl_pct = abs((sl - price) / price * 100)
        tp_pct = abs((tp - price) / price * 100)
        
        caption = f"""
📝 <b>PAPER TRADE - เปิด {side}!</b>

⚠️ <i>จำลองเท่านั้น - ไม่ใช่เงินจริง!</i>

{emoji} <b>{symbol}</b>
📍 ราคาเข้า: <b>${price:,.4f}</b>
💵 ขนาด: <b>${position_value:.2f}</b> x {LEVERAGE}x
🎯 Take Profit: <b>${tp:,.4f}</b> (+{tp_pct:.2f}%)
🛡️ Stop Loss: <b>${sl:,.4f}</b> (-{sl_pct:.2f}%)

📊 เหตุผล: {reason}
💰 เงินจำลอง: ${self.balance:.2f}
🕐 เวลา: {datetime.now().strftime('%H:%M:%S')}
"""
        
        # สร้างและส่งกราฟ
        chart = self.telegram.create_chart(df, symbol, price, sl, tp, side)
        if chart:
            self.telegram.send_photo(chart, caption)
        else:
            self.telegram.send_message(caption)
        
        return True
    
    def check_positions(self):
        """เช็ค SL/TP + ส่งกราฟเมื่อปิด - เหมือน Bot จริง"""
        closed = []
        
        for symbol, pos in self.positions.items():
            try:
                df = self.get_data_with_indicators(symbol)
                if df is None:
                    continue
                
                current_price = float(df.iloc[-1]['close'])
                
                hit_sl = False
                hit_tp = False
                
                if pos['side'] == 'LONG':
                    hit_sl = current_price <= pos['sl']
                    hit_tp = current_price >= pos['tp']
                else:
                    hit_sl = current_price >= pos['sl']
                    hit_tp = current_price <= pos['tp']
                
                if hit_sl or hit_tp:
                    exit_price = pos['tp'] if hit_tp else pos['sl']
                    
                    # Calculate PnL
                    if pos['side'] == 'LONG':
                        pnl_pct = (exit_price - pos['entry_price']) / pos['entry_price']
                    else:
                        pnl_pct = (pos['entry_price'] - exit_price) / pos['entry_price']
                    
                    pnl_leveraged = pnl_pct * LEVERAGE
                    pnl_usd = pos['size'] * pnl_leveraged
                    
                    # Update balance
                    self.balance += pnl_usd
                    
                    # Update stats
                    self.stats['total_trades'] += 1
                    self.stats['total_pnl'] += pnl_usd
                    
                    if pnl_usd > 0:
                        self.stats['wins'] += 1
                        if pos['side'] == 'LONG':
                            self.stats['long_wins'] += 1
                        else:
                            self.stats['short_wins'] += 1
                        if pnl_usd > self.stats['best_trade']:
                            self.stats['best_trade'] = pnl_usd
                    else:
                        self.stats['losses'] += 1
                        if pos['side'] == 'LONG':
                            self.stats['long_losses'] += 1
                        else:
                            self.stats['short_losses'] += 1
                        if pnl_usd < self.stats['worst_trade']:
                            self.stats['worst_trade'] = pnl_usd
                    
                    # Log trade
                    self.trade_history.append({
                        'symbol': symbol,
                        'side': pos['side'],
                        'entry': pos['entry_price'],
                        'exit': exit_price,
                        'pnl_usd': round(pnl_usd, 4),
                        'pnl_pct': round(pnl_leveraged * 100, 2),
                        'exit_reason': 'TP' if hit_tp else 'SL',
                        'time': datetime.now().isoformat()
                    })
                    
                    # Print
                    exit_type = "🎯 TP HIT" if hit_tp else "🛡️ SL HIT"
                    emoji = "💚" if pnl_usd > 0 else "💔"
                    result = "กำไร" if pnl_usd > 0 else "ขาดทุน"
                    
                    print(f"\n{emoji} [PAPER] ปิด {pos['side']} {symbol}")
                    print(f"   📍 Entry: ${pos['entry_price']:,.4f} → Exit: ${exit_price:,.4f}")
                    print(f"   💰 PnL: {'+' if pnl_usd > 0 else ''}{pnl_usd:.4f} USD")
                    
                    # ส่งกราฟ + ข้อความ - เหมือน Bot จริง!
                    win_rate = (self.stats['wins'] / self.stats['total_trades'] * 100) if self.stats['total_trades'] > 0 else 0
                    roi = ((self.balance - INITIAL_BALANCE) / INITIAL_BALANCE) * 100
                    
                    side_emoji = "🟢" if pos['side'] == 'LONG' else "🔴"
                    
                    caption = f"""
{emoji} <b>📝 PAPER TRADE - ปิด {pos['side']} - {result}!</b>

⚠️ <i>จำลองเท่านั้น - ไม่ใช่เงินจริง!</i>

{side_emoji} <b>{symbol}</b>
{exit_type}

📍 ราคาเข้า: ${pos['entry_price']:,.4f}
📍 ราคาออก: ${exit_price:,.4f}

{'🤑' if pnl_usd > 0 else '😢'} PnL: <b>{'+' if pnl_usd > 0 else ''}{pnl_usd:.4f}$</b> ({'+' if pnl_leveraged > 0 else ''}{pnl_leveraged*100:.1f}%)

💰 เงินจำลองรวม: <b>${self.balance:.4f}</b>
📈 ROI: {'+' if roi > 0 else ''}{roi:.2f}%
📊 Win Rate: {win_rate:.1f}% ({self.stats['wins']}W/{self.stats['losses']}L)
🕐 เวลา: {datetime.now().strftime('%H:%M:%S')}
"""
                    
                    # สร้างและส่งกราฟ
                    chart = self.telegram.create_chart(df, symbol, pos['entry_price'], 
                                                       pos['sl'], pos['tp'], pos['side'], exit_price)
                    if chart:
                        self.telegram.send_photo(chart, caption)
                    else:
                        self.telegram.send_message(caption)
                    
                    closed.append(symbol)
                    
            except Exception as e:
                print(f"⚠️ Error checking {symbol}: {e}")
        
        for symbol in closed:
            del self.positions[symbol]
            if symbol in self.df_cache:
                del self.df_cache[symbol]
    
    def scan_and_trade(self):
        """สแกนเหรียญและเปิด Position"""
        print(f"\n🔍 สแกน {len(COINS)} เหรียญ...")
        
        signals_found = []
        
        for symbol in COINS:
            if symbol in self.positions:
                continue
            
            df = self.get_data_with_indicators(symbol)
            if df is None:
                continue
            
            signal = self.get_signal(df)
            
            if signal['signal'] in ['LONG', 'SHORT']:
                signals_found.append({
                    'symbol': symbol,
                    'signal': signal['signal'],
                    'price': signal['price'],
                    'reason': signal['reason'],
                    'confidence': signal.get('confidence', 50),
                    'df': df
                })
            
            time.sleep(0.1)
        
        signals_found.sort(key=lambda x: x['confidence'], reverse=True)
        
        if signals_found:
            long_count = len([s for s in signals_found if s['signal'] == 'LONG'])
            short_count = len([s for s in signals_found if s['signal'] == 'SHORT'])
            print(f"\n📡 พบ {len(signals_found)} สัญญาณ (🟢 {long_count} LONG | 🔴 {short_count} SHORT)")
            
            for sig in signals_found[:5]:
                emoji = "🟢" if sig['signal'] == "LONG" else "🔴"
                print(f"   {emoji} {sig['signal']} {sig['symbol']}: ${sig['price']:.4f}")
            
            for sig in signals_found:
                if len(self.positions) >= MAX_POSITIONS:
                    break
                self.open_position(sig['symbol'], sig['signal'], sig['price'], 
                                  sig['reason'], sig['df'])
        else:
            print("   ⏳ ไม่พบสัญญาณ")
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # 📊 LIVE STATUS & ALERTS - ฟีเจอร์ใหม่!
    # ═══════════════════════════════════════════════════════════════════════════════
    
    def send_live_status(self):
        """📊 ส่ง Live Status ทุก 15 นาที"""
        if not self.telegram.enabled:
            return
        
        win_rate = (self.stats['wins'] / self.stats['total_trades'] * 100) if self.stats['total_trades'] > 0 else 0
        roi = ((self.balance - INITIAL_BALANCE) / INITIAL_BALANCE) * 100
        
        # คำนวณ Total Unrealized PnL
        total_unrealized = 0
        positions_text = ""
        
        for symbol, pos in self.positions.items():
            df = self.get_data_with_indicators(symbol)
            if df is not None:
                current = float(df.iloc[-1]['close'])
                if pos['side'] == 'LONG':
                    pnl_pct = (current - pos['entry_price']) / pos['entry_price'] * LEVERAGE * 100
                else:
                    pnl_pct = (pos['entry_price'] - current) / pos['entry_price'] * LEVERAGE * 100
                
                total_unrealized += pnl_pct
                emoji = "🟢" if pos['side'] == 'LONG' else "🔴"
                status = "📈" if pnl_pct > 0 else "📉"
                positions_text += f"\n  {emoji} {symbol}: {status} <b>{pnl_pct:+.1f}%</b>"
        
        if not positions_text:
            positions_text = "\n  🔒 ไม่มี Position เปิด"
        
        msg = f"""📊 <b>PAPER BOT - LIVE STATUS</b>
━━━━━━━━━━━━━━━━━━━━
🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

💵 Balance: <b>${self.balance:.2f}</b>
📈 ROI: <b>{roi:+.2f}%</b>
📊 Trades: {self.stats['total_trades']} (✅{self.stats['wins']} ❌{self.stats['losses']})
🎯 Win Rate: {win_rate:.1f}%

<b>🔓 Positions ({len(self.positions)}):</b>{positions_text}

💹 Unrealized: <b>{total_unrealized:+.1f}%</b>
━━━━━━━━━━━━━━━━━━━━
⚙️ SL: {SL_PCT*100}% | TP: {TP_PCT*100}% | {LEVERAGE}x
📝 <i>Paper Trade - จำลองเท่านั้น</i>"""
        
        self.telegram.send_message(msg)
        print("📤 ส่ง Live Status ไป Telegram แล้ว")
    
    def check_pnl_alerts(self):
        """🔔 แจ้งเตือนเมื่อ PnL เกิน ±10%"""
        if not self.telegram.enabled:
            return
        
        for symbol, pos in self.positions.items():
            df = self.get_data_with_indicators(symbol)
            if df is None:
                continue
            
            current = float(df.iloc[-1]['close'])
            if pos['side'] == 'LONG':
                pnl_pct = (current - pos['entry_price']) / pos['entry_price'] * LEVERAGE * 100
            else:
                pnl_pct = (pos['entry_price'] - current) / pos['entry_price'] * LEVERAGE * 100
            
            # เช็คว่าเกิน threshold และยังไม่เคยแจ้ง
            alert_key = f"{symbol}_{int(pnl_pct / PNL_ALERT_THRESHOLD) * PNL_ALERT_THRESHOLD}"
            
            if abs(pnl_pct) >= PNL_ALERT_THRESHOLD and alert_key not in self.last_pnl_alert:
                self.last_pnl_alert[alert_key] = time.time()
                
                emoji = "🚀" if pnl_pct > 0 else "⚠️"
                side_emoji = "🟢" if pos['side'] == 'LONG' else "🔴"
                
                msg = f"""{emoji} <b>PnL ALERT!</b>

{side_emoji} <b>{symbol}</b> ({pos['side']})
📍 Entry: ${pos['entry_price']:.4f}
📍 Current: ${current:.4f}
{'🤑' if pnl_pct > 0 else '😰'} PnL: <b>{pnl_pct:+.1f}%</b>

{'🎯 ใกล้ถึง TP แล้ว!' if pnl_pct > 30 else ''}{'🛡️ ระวัง SL!' if pnl_pct < -20 else ''}
━━━━━━━━━━━━━━━━━━━━
📝 <i>Paper Trade Alert</i>"""
                
                self.telegram.send_message(msg)
                print(f"🔔 ส่ง PnL Alert: {symbol} {pnl_pct:+.1f}%")
    
    def send_positions_chart(self):
        """📈 ส่งกราฟ Professional Trading Terminal"""
        if not self.telegram.enabled or not self.positions:
            return
        
        try:
            for symbol, pos in self.positions.items():
                self._send_pro_chart(symbol, pos)
                time.sleep(1)
            
        except Exception as e:
            print(f"⚠️ Chart error: {e}")
    
    def _send_pro_chart(self, symbol: str, pos: dict):
        """📊 Professional Trading Terminal Chart with MACD"""
        try:
            df = self.get_data_with_indicators(symbol)
            if df is None:
                return
            
            df_chart = df.tail(60).copy()
            current = float(df.iloc[-1]['close'])
            
            # คำนวณ PnL
            if pos['side'] == 'LONG':
                pnl_pct = (current - pos['entry_price']) / pos['entry_price'] * LEVERAGE * 100
                pnl_usd = (current - pos['entry_price']) * pos['size']
            else:
                pnl_pct = (pos['entry_price'] - current) / pos['entry_price'] * LEVERAGE * 100
                pnl_usd = (pos['entry_price'] - current) * pos['size']
            
            # ═══════════════════════════════════════════════════════
            # 🎨 PROFESSIONAL CHART SETUP (with MACD)
            # ═══════════════════════════════════════════════════════
            
            fig = plt.figure(figsize=(14, 12), facecolor='#131722')
            
            # Layout: Header, Main Chart, MACD, RSI, Volume, Footer
            gs = fig.add_gridspec(6, 1, height_ratios=[0.5, 3.5, 0.8, 0.8, 0.7, 0.3], hspace=0.02)
            
            ax_header = fig.add_subplot(gs[0])
            ax_main = fig.add_subplot(gs[1])
            ax_macd = fig.add_subplot(gs[2], sharex=ax_main)
            ax_rsi = fig.add_subplot(gs[3], sharex=ax_main)
            ax_vol = fig.add_subplot(gs[4], sharex=ax_main)
            ax_footer = fig.add_subplot(gs[5])
            
            # Theme
            for ax in [ax_header, ax_main, ax_macd, ax_rsi, ax_vol, ax_footer]:
                ax.set_facecolor('#131722')
                ax.tick_params(colors='#787b86', labelsize=8)
                for spine in ax.spines.values():
                    spine.set_color('#2a2e39')
            
            ax_header.axis('off')
            ax_footer.axis('off')
            
            x = range(len(df_chart))
            
            # ═══════════════════════════════════════════════════════
            # 🏷️ HEADER - PROFESSIONAL STYLE
            # ═══════════════════════════════════════════════════════
            
            is_profit = pnl_pct > 0
            main_color = '#26a69a' if is_profit else '#ef5350'
            side_color = '#26a69a' if pos['side'] == 'LONG' else '#ef5350'
            
            # Background gradient effect
            ax_header.axhspan(0, 1, facecolor='#1e222d', alpha=0.8)
            
            # Left side - Symbol info
            coin_name = symbol.replace('/USDT', '')
            ax_header.text(0.02, 0.7, f"●", fontsize=16, color=side_color, 
                          transform=ax_header.transAxes, va='center', fontweight='bold')
            ax_header.text(0.05, 0.7, coin_name, fontsize=20, color='#d1d4dc', 
                          transform=ax_header.transAxes, va='center', fontweight='bold',
                          fontfamily='monospace')
            ax_header.text(0.05, 0.25, 'USDT Perpetual', fontsize=9, color='#787b86', 
                          transform=ax_header.transAxes, va='center')
            
            # Center - Price
            ax_header.text(0.35, 0.7, f"${current:.4f}", fontsize=22, color=main_color, 
                          transform=ax_header.transAxes, va='center', fontweight='bold',
                          fontfamily='monospace')
            
            # PnL Badge
            pnl_text = f"{'+' if pnl_pct > 0 else ''}{pnl_pct:.2f}%"
            ax_header.text(0.55, 0.7, pnl_text, fontsize=18, color=main_color, 
                          transform=ax_header.transAxes, va='center', fontweight='bold',
                          bbox=dict(boxstyle='round,pad=0.3', facecolor='#131722', 
                                   edgecolor=main_color, linewidth=2, alpha=0.9))
            
            # Right side - Position info
            side_text = "LONG" if pos['side'] == 'LONG' else "SHORT"
            ax_header.text(0.75, 0.7, side_text, fontsize=12, color=side_color, 
                          transform=ax_header.transAxes, va='center', fontweight='bold',
                          bbox=dict(boxstyle='round,pad=0.4', facecolor=side_color, 
                                   edgecolor='none', alpha=0.15))
            
            ax_header.text(0.88, 0.7, f"{LEVERAGE}×", fontsize=11, color='#ffa726', 
                          transform=ax_header.transAxes, va='center', fontweight='bold',
                          bbox=dict(boxstyle='round,pad=0.3', facecolor='#3d2e0a', 
                                   edgecolor='#ffa726', linewidth=1))
            
            # ═══════════════════════════════════════════════════════
            # 📈 MAIN CHART - CANDLESTICKS
            # ═══════════════════════════════════════════════════════
            
            # Price range for scaling
            price_min = df_chart['low'].min()
            price_max = df_chart['high'].max()
            price_range = price_max - price_min
            
            for i, (idx, row) in enumerate(df_chart.iterrows()):
                is_green = row['close'] >= row['open']
                color = '#26a69a' if is_green else '#ef5350'
                
                # Wick
                ax_main.plot([i, i], [row['low'], row['high']], 
                            color=color, linewidth=1.2)
                
                # Body
                body_bottom = min(row['open'], row['close'])
                body_height = abs(row['close'] - row['open'])
                if body_height < price_range * 0.002:
                    body_height = price_range * 0.002
                
                rect = plt.Rectangle((i - 0.4, body_bottom), 0.8, body_height,
                                     facecolor=color, edgecolor=color, linewidth=0.5)
                ax_main.add_patch(rect)
            
            # EMAs with smooth lines
            if 'ema_fast' in df_chart.columns:
                ax_main.plot(x, df_chart['ema_fast'], color='#f7931a', 
                            linewidth=1.8, label='EMA 3', alpha=0.9)
            if 'ema_slow' in df_chart.columns:
                ax_main.plot(x, df_chart['ema_slow'], color='#627eea', 
                            linewidth=1.8, label='EMA 8', alpha=0.9)
            if 'ema_20' in df_chart.columns:
                ax_main.plot(x, df_chart['ema_20'], color='#26a69a', 
                            linewidth=1.2, label='EMA 20', alpha=0.6, linestyle='--')
            
            # Entry Line with label
            ax_main.axhline(y=pos['entry_price'], color='#2196f3', linestyle='-', 
                           linewidth=2, alpha=0.9)
            ax_main.text(len(df_chart)+0.5, pos['entry_price'], f" Entry ${pos['entry_price']:.4f}", 
                        fontsize=8, color='#2196f3', va='center', fontweight='bold')
            
            # TP Line with zone
            ax_main.axhline(y=pos['tp'], color='#26a69a', linestyle='--', linewidth=1.5)
            ax_main.fill_between(x, pos['entry_price'], pos['tp'], 
                                alpha=0.05, color='#26a69a')
            ax_main.text(len(df_chart)+0.5, pos['tp'], f" TP ${pos['tp']:.4f}", 
                        fontsize=8, color='#26a69a', va='center')
            
            # SL Line with zone
            ax_main.axhline(y=pos['sl'], color='#ef5350', linestyle='--', linewidth=1.5)
            ax_main.fill_between(x, pos['entry_price'], pos['sl'], 
                                alpha=0.05, color='#ef5350')
            ax_main.text(len(df_chart)+0.5, pos['sl'], f" SL ${pos['sl']:.4f}", 
                        fontsize=8, color='#ef5350', va='center')
            
            # Current price dot with pulse effect
            ax_main.scatter([len(df_chart)-1], [current], color='#2196f3', 
                           s=100, zorder=10, edgecolors='white', linewidths=2)
            ax_main.scatter([len(df_chart)-1], [current], color='#2196f3', 
                           s=250, zorder=9, alpha=0.2)
            
            # Subtle grid
            ax_main.grid(True, alpha=0.08, color='#363a45', linestyle='-')
            ax_main.set_ylabel('Price', fontsize=9, color='#787b86')
            ax_main.legend(loc='upper left', fontsize=8, facecolor='#1e222d', 
                          edgecolor='#363a45', labelcolor='#d1d4dc', framealpha=0.9)
            
            # Set y-axis limits with padding
            ax_main.set_ylim(price_min - price_range*0.05, price_max + price_range*0.15)
            
            # ═══════════════════════════════════════════════════════
            # 📊 MACD - Moving Average Convergence Divergence
            # ═══════════════════════════════════════════════════════
            
            if 'macd' in df_chart.columns:
                macd = df_chart['macd']
                signal = df_chart['macd_signal'] if 'macd_signal' in df_chart.columns else macd.ewm(span=9).mean()
                hist = macd - signal
                
                # Histogram bars with gradient colors
                colors_hist = []
                for i, h in enumerate(hist):
                    if h >= 0:
                        colors_hist.append('#26a69a' if i == 0 or h >= hist.iloc[i-1] else '#1a7a6e')
                    else:
                        colors_hist.append('#ef5350' if i == 0 or h <= hist.iloc[i-1] else '#b33d3a')
                
                ax_macd.bar(x, hist, color=colors_hist, alpha=0.7, width=0.7)
                ax_macd.plot(x, macd, color='#2962ff', linewidth=1.5, label='MACD')
                ax_macd.plot(x, signal, color='#ff6d00', linewidth=1.5, label='Signal')
                ax_macd.axhline(y=0, color='#363a45', linewidth=0.8, alpha=0.5)
                
                # Current value label
                current_macd = macd.iloc[-1]
                macd_color = '#26a69a' if current_macd > 0 else '#ef5350'
                ax_macd.text(len(df_chart)+0.5, current_macd, f' {current_macd:.4f}', 
                           fontsize=8, color=macd_color, va='center', fontweight='bold')
                
                ax_macd.legend(loc='upper left', fontsize=7, facecolor='#1e222d', 
                              edgecolor='#363a45', labelcolor='#d1d4dc')
                ax_macd.set_ylabel('MACD', fontsize=8, color='#787b86')
                ax_macd.grid(True, alpha=0.05, color='#363a45')
            
            # ═══════════════════════════════════════════════════════
            # 📊 RSI
            # ═══════════════════════════════════════════════════════
            
            if 'rsi' in df_chart.columns:
                rsi = df_chart['rsi']
                
                # RSI line with gradient
                ax_rsi.plot(x, rsi, color='#ab47bc', linewidth=1.8)
                
                # Overbought/Oversold zones
                ax_rsi.fill_between(x, 70, 100, alpha=0.1, color='#ef5350')
                ax_rsi.fill_between(x, 0, 30, alpha=0.1, color='#26a69a')
                
                # Current RSI fill
                ax_rsi.fill_between(x, 50, rsi, where=(rsi >= 50), alpha=0.15, color='#26a69a')
                ax_rsi.fill_between(x, 50, rsi, where=(rsi < 50), alpha=0.15, color='#ef5350')
                
                ax_rsi.axhline(y=70, color='#ef5350', linestyle='--', alpha=0.4, linewidth=0.8)
                ax_rsi.axhline(y=50, color='#363a45', linestyle='-', alpha=0.5, linewidth=0.8)
                ax_rsi.axhline(y=30, color='#26a69a', linestyle='--', alpha=0.4, linewidth=0.8)
                
                # RSI value label
                current_rsi = rsi.iloc[-1]
                rsi_color = '#ef5350' if current_rsi > 70 else '#26a69a' if current_rsi < 30 else '#ab47bc'
                ax_rsi.text(len(df_chart)+0.5, current_rsi, f' {current_rsi:.1f}', 
                           fontsize=9, color=rsi_color, va='center', fontweight='bold')
                
                ax_rsi.set_ylim(0, 100)
                ax_rsi.set_ylabel('RSI', fontsize=8, color='#787b86')
                ax_rsi.grid(True, alpha=0.05, color='#363a45')
            
            # ═══════════════════════════════════════════════════════
            # 📊 VOLUME
            # ═══════════════════════════════════════════════════════
            
            vol_colors = ['#26a69a' if c >= o else '#ef5350' 
                         for o, c in zip(df_chart['open'], df_chart['close'])]
            ax_vol.bar(x, df_chart['volume'], color=vol_colors, alpha=0.5, width=0.7)
            
            # Volume MA
            vol_ma = df_chart['volume'].rolling(20).mean()
            ax_vol.plot(x, vol_ma, color='#ffa726', linewidth=1.2, alpha=0.8)
            
            ax_vol.set_ylabel('Vol', fontsize=8, color='#787b86')
            ax_vol.grid(True, alpha=0.05, color='#363a45')
            
            # ═══════════════════════════════════════════════════════
            # 📋 FOOTER
            # ═══════════════════════════════════════════════════════
            
            ax_footer.axhspan(0, 1, facecolor='#1e222d', alpha=0.5)
            
            ax_footer.text(0.02, 0.5, '📝 PAPER TRADE', fontsize=10, color='#ffa726', 
                          transform=ax_footer.transAxes, va='center', fontweight='bold')
            
            ax_footer.text(0.22, 0.5, f'💰 ${self.balance:.2f}', fontsize=10, color='#d1d4dc', 
                          transform=ax_footer.transAxes, va='center')
            
            roi = ((self.balance - INITIAL_BALANCE) / INITIAL_BALANCE) * 100
            roi_color = '#26a69a' if roi >= 0 else '#ef5350'
            ax_footer.text(0.40, 0.5, f'ROI: {roi:+.2f}%', fontsize=10, color=roi_color, 
                          transform=ax_footer.transAxes, va='center', fontweight='bold')
            
            ax_footer.text(0.60, 0.5, f'⏰ {datetime.now().strftime("%H:%M:%S")}', fontsize=9, 
                          color='#787b86', transform=ax_footer.transAxes, va='center')
            
            ax_footer.text(0.98, 0.5, '🤖 AlphaBot Scalper V4', fontsize=9, color='#787b86', 
                          transform=ax_footer.transAxes, va='center', ha='right', 
                          style='italic', fontfamily='monospace')
            
            # ═══════════════════════════════════════════════════════
            # 🏷️ WATERMARK
            # ═══════════════════════════════════════════════════════
            
            # Semi-transparent watermark in the center of main chart
            ax_main.text(0.5, 0.5, 'ALPHABOT', transform=ax_main.transAxes,
                        fontsize=60, color='#ffffff', alpha=0.03, ha='center', va='center',
                        fontweight='bold', fontfamily='monospace', rotation=0)
            
            # Remove x-axis labels except on volume
            plt.setp(ax_main.get_xticklabels(), visible=False)
            plt.setp(ax_macd.get_xticklabels(), visible=False)
            plt.setp(ax_rsi.get_xticklabels(), visible=False)
            
            plt.tight_layout()
            plt.subplots_adjust(hspace=0.02)
            
            # Save high quality
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=200, bbox_inches='tight', 
                       facecolor='#131722', edgecolor='none', pad_inches=0.1)
            buf.seek(0)
            plt.close()
            
            # Caption
            side_emoji = "🟢 LONG" if pos['side'] == 'LONG' else "🔴 SHORT"
            pnl_emoji = "📈" if pnl_pct > 0 else "📉"
            
            caption = f"""<b>{coin_name}/USDT</b> • Perpetual
━━━━━━━━━━━━━━━━━━
{side_emoji} <b>{pos['side']}</b> @ {LEVERAGE}× Leverage

💵 Entry: <code>${pos['entry_price']:.4f}</code>
💰 Mark: <code>${current:.4f}</code>
{pnl_emoji} PnL: <b>{pnl_pct:+.2f}%</b> (<code>${pnl_usd:+.4f}</code>)

🎯 TP: <code>${pos['tp']:.4f}</code>
🛡 SL: <code>${pos['sl']:.4f}</code>
━━━━━━━━━━━━━━━━━━
📝 Paper Trade • ⏱ Hourly"""
            
            self.telegram.send_photo(buf.getvalue(), caption)
            print(f"📊 ส่งกราฟ {symbol} (Pro) ไป Telegram แล้ว")
            
        except Exception as e:
            print(f"⚠️ Chart error for {symbol}: {e}")
    
    def check_live_updates(self):
        """ตรวจสอบและส่ง Live Updates"""
        now = time.time()
        
        # 📊 ส่ง Live Status ทุก 15 นาที
        if now - self.last_live_status >= LIVE_STATUS_INTERVAL * 60:
            self.send_live_status()
            self.last_live_status = now
        
        # 🔔 เช็ค PnL Alerts
        self.check_pnl_alerts()
        
        # 📈 ส่งกราฟทุกชั่วโมง
        if now - self.last_chart_update >= CHART_INTERVAL * 60:
            self.send_positions_chart()
            self.last_chart_update = now
    
    def print_status(self):
        """แสดงสถานะ"""
        win_rate = (self.stats['wins'] / self.stats['total_trades'] * 100) if self.stats['total_trades'] > 0 else 0
        roi = ((self.balance - INITIAL_BALANCE) / INITIAL_BALANCE) * 100
        
        print(f"\n{'═'*70}")
        print(f"📊 PAPER TRADE STATUS - {datetime.now().strftime('%H:%M:%S')}")
        print(f"{'═'*70}")
        print(f"💰 Balance: ${self.balance:.4f} | ROI: {roi:+.2f}%")
        print(f"📈 Trades: {self.stats['total_trades']} | ✅ {self.stats['wins']}W / ❌ {self.stats['losses']}L | WR: {win_rate:.1f}%")
        
        if self.positions:
            print(f"\n📊 Positions ({len(self.positions)}/{MAX_POSITIONS}):")
            for symbol, pos in self.positions.items():
                df = self.get_data_with_indicators(symbol)
                if df is not None:
                    current = float(df.iloc[-1]['close'])
                    if pos['side'] == 'LONG':
                        pnl_pct = (current - pos['entry_price']) / pos['entry_price'] * LEVERAGE * 100
                    else:
                        pnl_pct = (pos['entry_price'] - current) / pos['entry_price'] * LEVERAGE * 100
                    
                    emoji = "📈" if pnl_pct > 0 else "📉"
                    side_emoji = "🟢" if pos['side'] == 'LONG' else "🔴"
                    print(f"   {side_emoji} {pos['side']} {symbol}: ${pos['entry_price']:.4f} → ${current:.4f} | {emoji} {pnl_pct:+.1f}%")
        
        print(f"{'═'*70}\n")
    
    def save_state(self):
        """บันทึก state"""
        state = {
            'balance': self.balance,
            'stats': self.stats,
            'positions': self.positions,
            'trades': self.trade_history,
            'last_update': datetime.now().isoformat()
        }
        with open('paper_trades.json', 'w') as f:
            json.dump(state, f, indent=2)
        
        # บันทึกสถานะสำหรับ check_status.py
        self.save_status_file()
    
    def save_status_file(self):
        """บันทึกสถานะลงไฟล์สำหรับเช็คสถานะ"""
        try:
            # เตรียมข้อมูล open positions
            open_positions = []
            for symbol, pos in self.positions.items():
                df = self.get_data_with_indicators(symbol)
                current_price = float(df.iloc[-1]['close']) if df is not None else pos['entry_price']
                
                open_positions.append({
                    'symbol': symbol,
                    'side': pos['side'].lower(),
                    'entry_price': pos['entry_price'],
                    'current_price': current_price,
                    'sl': pos['sl'],
                    'tp': pos['tp'],
                    'size': pos['size'],
                    'open_time': pos['open_time']
                })
            
            # เตรียมประวัติเทรด
            trade_history = []
            for trade in self.trade_history[-20:]:  # เก็บ 20 รายการล่าสุด
                trade_history.append({
                    'symbol': trade['symbol'],
                    'side': trade['side'].lower(),
                    'pnl': trade['pnl_pct'],
                    'exit_reason': trade['exit_reason'],
                    'time': trade['time']
                })
            
            status = {
                'last_update': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'initial_balance': INITIAL_BALANCE,
                'current_balance': self.balance,
                'total_trades': self.stats['total_trades'],
                'wins': self.stats['wins'],
                'losses': self.stats['losses'],
                'total_pnl': self.stats['total_pnl'],
                'open_positions': open_positions,
                'trade_history': trade_history
            }
            
            with open('paper_trade_status.json', 'w') as f:
                json.dump(status, f, indent=2)
        except Exception as e:
            print(f"⚠️ Error saving status file: {e}")
    
    def load_state(self):
        """โหลด state"""
        try:
            if os.path.exists('paper_trades.json'):
                with open('paper_trades.json', 'r') as f:
                    state = json.load(f)
                self.balance = state.get('balance', INITIAL_BALANCE)
                self.stats = state.get('stats', self.stats)
                self.positions = state.get('positions', {})
                self.trade_history = state.get('trades', [])
                print(f"📂 โหลด state: ${self.balance:.4f} | {self.stats['total_trades']} เทรด")
                return True
        except:
            pass
        return False
    
    def run(self):
        """Main loop"""
        print(f"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                     📝 PAPER TRADE BOT - FULL VERSION                        ║
║                  ส่งกราฟ + แจ้งเตือน เหมือน Bot เงินจริง!                     ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  ⚠️  จำลองเท่านั้น - ไม่ใช่เงินจริง!                                          ║
║  🎯 เป้าหมาย: $4.50 → $50.00                                                 ║
║  📊 เหรียญ: {len(COINS)} เหรียญ | ⚡ Leverage: {LEVERAGE}x                                   ║
║  🛡️ SL: {SL_PCT*100}% | 🎯 TP: {TP_PCT*100}%                                                 ║
╚══════════════════════════════════════════════════════════════════════════════╝
        """)
        
        self.load_state()
        
        iteration = 0
        
        try:
            while True:
                iteration += 1
                
                if self.positions:
                    self.check_positions()
                
                self.scan_and_trade()
                
                # 🔔 Live Updates: Status, PnL Alert, Chart
                self.check_live_updates()
                
                if iteration % 3 == 0:
                    self.print_status()
                
                self.save_state()
                
                if self.balance >= 50.0:
                    msg = """
🎉🎉🎉 <b>ถึงเป้าหมาย $50 แล้ว!</b> 🎉🎉🎉

📝 PAPER TRADE จำลอง
💰 $4.50 → $50.00
📈 ROI: +1,011%

⚠️ นี่คือผลจำลอง ไม่ใช่เงินจริง!
"""
                    self.telegram.send_message(msg)
                    self.print_status()
                    break
                
                if self.balance < 0.50:
                    msg = """
💀 <b>หมดตัว!</b> 💀

📝 PAPER TRADE จำลอง
💰 Balance ต่ำกว่า $0.50

⚠️ นี่คือผลจำลอง ไม่ใช่เงินจริง!
"""
                    self.telegram.send_message(msg)
                    self.print_status()
                    break
                
                print(f"⏳ รอ {SCAN_INTERVAL} วินาที... (Ctrl+C หยุด)")
                time.sleep(SCAN_INTERVAL)
                
        except KeyboardInterrupt:
            print("\n\n🛑 หยุด Bot")
            self.print_status()
            self.save_state()
            
            roi = ((self.balance - INITIAL_BALANCE) / INITIAL_BALANCE) * 100
            msg = f"""
🛑 <b>📝 PAPER TRADE BOT หยุดทำงาน</b>

⚠️ <i>จำลองเท่านั้น - ไม่ใช่เงินจริง!</i>

💰 เริ่ม: ${INITIAL_BALANCE}
💵 จบ: ${self.balance:.4f}
📈 ROI: {roi:+.2f}%
📊 เทรด: {self.stats['total_trades']}
✅ ชนะ: {self.stats['wins']} | ❌ แพ้: {self.stats['losses']}
"""
            self.telegram.send_message(msg)


if __name__ == "__main__":
    bot = PaperTradeBotFull()
    bot.run()
