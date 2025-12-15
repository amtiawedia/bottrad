#!/usr/bin/env python3
"""
🚀 Paper Trade Bot V4 - BEST SETTINGS FROM BACKTEST!
====================================================
📊 Backtest Results (5 days, 15 coins):
- 201 trades, 47.8% Win Rate
- ROI: +736.9%!

✅ Best Settings Found:
- SL: 1.2% (= -24% at 20x) 
- TP: 1.8% (= +36% at 20x)
- R:R = 1:1.5
- ADX >= 30
- เก็บ Meme Coins ไว้ (Backtest ดี!)
"""

import ccxt
import pandas as pd
import pandas_ta as ta
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.gridspec import GridSpec
import asyncio
import aiohttp
import io
import os
import json
from datetime import datetime, timedelta
from pathlib import Path

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION V4 - ปรับตาม Backtest Results
# ═══════════════════════════════════════════════════════════════════════════════

# 🎯 COINS - เก็บ Meme Coins ไว้ (ผล Backtest ดี!)
COINS = [
    # Major (มั่นคง)
    'BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'XRP/USDT', 'SOL/USDT',
    # Layer 1
    'ADA/USDT', 'AVAX/USDT', 'DOT/USDT', 'NEAR/USDT', 'SUI/USDT',
    # Layer 2 / DeFi
    'ARB/USDT', 'OP/USDT', 'POL/USDT', 'LINK/USDT', 'UNI/USDT',
    # Mid-Cap
    'LTC/USDT', 'ETC/USDT', 'FIL/USDT', 'AAVE/USDT', 'INJ/USDT',
    'RUNE/USDT', 'SEI/USDT', 'STX/USDT', 'IMX/USDT', 'FTM/USDT', 'GRT/USDT',
    # Meme (Backtest บอกว่าดี!)
    'DOGE/USDT', '1000PEPE/USDT', 'WIF/USDT', 'ORDI/USDT',
]

# Trading Settings V4 - BEST FROM BACKTEST!
# Backtest Results: 201 trades, 47.8% WR, +736.9% ROI
INITIAL_BALANCE = 4.50
LEVERAGE = 20  # 20x leverage
SL_PCT = 0.012  # 1.2% SL = -24% at 20x (BEST!)
TP_PCT = 0.018  # 1.8% TP = +36% at 20x, R:R = 1:1.5
TIMEFRAME = '5m'
SCAN_INTERVAL = 30
MAX_POSITIONS = 3
ADX_THRESHOLD = 30  # 30 ดีที่สุดจาก Backtest

# 🎯 Dynamic Position Sizing - Simplified
# ใช้ uniform sizing เพราะ SL/TP ใหม่ดีแล้ว
POSITION_SIZE_MULTIPLIERS = {
    'LOW': 0.8,      # Confidence 50-70: 0.8x
    'MEDIUM': 1.0,   # Confidence 70-85: 1.0x
    'HIGH': 1.2,     # Confidence 85+: 1.2x
}

# Telegram
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '8130246852:AAGR8tzOjabeDaUDt_e8r8KNLXaLgKOH3Rw')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '8254419265')
TELEGRAM_ENABLED = True

# 📊 Live Status & Alert Settings
LIVE_STATUS_INTERVAL = 15
PNL_ALERT_THRESHOLD = 10
CHART_INTERVAL = 60

# ═══════════════════════════════════════════════════════════════════════════════
# TELEGRAM NOTIFIER
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
            import requests
            url = f"{self.base_url}/sendMessage"
            data = {
                'chat_id': self.chat_id,
                'text': text,
                'parse_mode': 'HTML'
            }
            resp = requests.post(url, data=data, timeout=10)
            return resp.status_code == 200
        except Exception as e:
            print(f"Telegram error: {e}")
            return False
    
    def send_photo(self, photo_buffer, caption: str = "") -> bool:
        if not self.enabled:
            return False
        try:
            import requests
            url = f"{self.base_url}/sendPhoto"
            files = {'photo': ('chart.png', photo_buffer, 'image/png')}
            data = {
                'chat_id': self.chat_id,
                'caption': caption,
                'parse_mode': 'HTML'
            }
            resp = requests.post(url, files=files, data=data, timeout=30)
            return resp.status_code == 200
        except Exception as e:
            print(f"Telegram photo error: {e}")
            return False

# ═══════════════════════════════════════════════════════════════════════════════
# TRADINGVIEW PRO CHART
# ═══════════════════════════════════════════════════════════════════════════════

class TradingViewChart:
    """TradingView Pro Style Chart with ICT Concepts"""
    
    @staticmethod
    def create_pro_chart(df: pd.DataFrame, symbol: str, entry_price: float, 
                         sl: float, tp: float, side: str, confidence: int = 75) -> io.BytesIO:
        """สร้างกราฟ TradingView Pro Style"""
        
        COLORS = {
            'bg': '#0d1117',
            'panel': '#161b22',
            'text': '#e6edf3',
            'grid': '#21262d',
            'up': '#00d26a',
            'down': '#ff4757',
            'ema_fast': '#f1c40f',
            'ema_slow': '#3498db',
            'ema_trend': '#9b59b6',
            'premium': '#ff475730',
            'discount': '#00d26a30',
            'fvg_bull': '#00d26a40',
            'fvg_bear': '#ff475740',
            'volume_up': '#00d26a80',
            'volume_down': '#ff475780',
            'entry': '#ffffff',
            'sl': '#ff4757',
            'tp': '#00d26a',
        }
        
        fig = plt.figure(figsize=(14, 10), facecolor=COLORS['bg'])
        gs = GridSpec(4, 1, figure=fig, height_ratios=[3, 0.8, 0.8, 0.8], hspace=0.05)
        
        ax_main = fig.add_subplot(gs[0])
        ax_vol = fig.add_subplot(gs[1], sharex=ax_main)
        ax_rsi = fig.add_subplot(gs[2], sharex=ax_main)
        ax_macd = fig.add_subplot(gs[3], sharex=ax_main)
        
        for ax in [ax_main, ax_vol, ax_rsi, ax_macd]:
            ax.set_facecolor(COLORS['panel'])
            ax.tick_params(colors=COLORS['text'], labelsize=8)
            ax.grid(True, color=COLORS['grid'], alpha=0.3, linestyle='-', linewidth=0.5)
            for spine in ax.spines.values():
                spine.set_color(COLORS['grid'])
        
        df = df.tail(100).copy().reset_index(drop=True)
        x = range(len(df))
        
        df['ema_3'] = ta.ema(df['close'], length=3)
        df['ema_8'] = ta.ema(df['close'], length=8)
        df['ema_20'] = ta.ema(df['close'], length=20)
        df['ema_50'] = ta.ema(df['close'], length=50)
        df['rsi'] = ta.rsi(df['close'], length=14)
        macd = ta.macd(df['close'])
        if macd is not None:
            df['macd'] = macd['MACD_12_26_9']
            df['macd_signal'] = macd['MACDs_12_26_9']
            df['macd_hist'] = macd['MACDh_12_26_9']
        
        # Premium / Discount Zones
        high_20 = df['high'].rolling(20).max()
        low_20 = df['low'].rolling(20).min()
        mid_20 = (high_20 + low_20) / 2
        
        for i in range(20, len(df)):
            ax_main.fill_between([i-1, i], mid_20.iloc[i], high_20.iloc[i], 
                                  color=COLORS['premium'], alpha=0.3)
            ax_main.fill_between([i-1, i], low_20.iloc[i], mid_20.iloc[i], 
                                  color=COLORS['discount'], alpha=0.3)
        
        # FVG
        for i in range(2, len(df)):
            prev_high = df['high'].iloc[i-2]
            curr_low = df['low'].iloc[i]
            prev_low = df['low'].iloc[i-2]
            curr_high = df['high'].iloc[i]
            
            if curr_low > prev_high:
                ax_main.fill_between([i-2, i], prev_high, curr_low, 
                                      color=COLORS['fvg_bull'], alpha=0.5)
            elif curr_high < prev_low:
                ax_main.fill_between([i-2, i], curr_high, prev_low, 
                                      color=COLORS['fvg_bear'], alpha=0.5)
        
        # Candlesticks
        for i in x:
            o, h, l, c = df['open'].iloc[i], df['high'].iloc[i], df['low'].iloc[i], df['close'].iloc[i]
            color = COLORS['up'] if c >= o else COLORS['down']
            ax_main.plot([i, i], [l, h], color=color, linewidth=1)
            ax_main.add_patch(plt.Rectangle((i-0.3, min(o,c)), 0.6, abs(c-o) or 0.0001,
                                             facecolor=color, edgecolor=color, linewidth=1))
        
        # EMAs
        ax_main.plot(x, df['ema_3'], color=COLORS['ema_fast'], linewidth=1, label='EMA 3', alpha=0.9)
        ax_main.plot(x, df['ema_8'], color=COLORS['ema_slow'], linewidth=1, label='EMA 8', alpha=0.9)
        ax_main.plot(x, df['ema_20'], color=COLORS['ema_trend'], linewidth=1.5, label='EMA 20', alpha=0.8)
        ax_main.plot(x, df['ema_50'], color='#ffffff', linewidth=1.5, label='EMA 50', alpha=0.5, linestyle='--')
        
        # Entry / SL / TP Lines
        ax_main.axhline(entry_price, color=COLORS['entry'], linewidth=2, linestyle='-', alpha=0.9)
        ax_main.axhline(sl, color=COLORS['sl'], linewidth=2, linestyle='--', alpha=0.9)
        ax_main.axhline(tp, color=COLORS['tp'], linewidth=2, linestyle='--', alpha=0.9)
        
        ax_main.text(len(df)+1, entry_price, f'Entry ${entry_price:,.4f}', 
                     color=COLORS['entry'], fontsize=9, va='center', fontweight='bold')
        ax_main.text(len(df)+1, sl, f'SL ${sl:,.4f}', 
                     color=COLORS['sl'], fontsize=9, va='center')
        ax_main.text(len(df)+1, tp, f'TP ${tp:,.4f}', 
                     color=COLORS['tp'], fontsize=9, va='center')
        
        # Volume
        vol_colors = [COLORS['volume_up'] if df['close'].iloc[i] >= df['open'].iloc[i] 
                      else COLORS['volume_down'] for i in x]
        ax_vol.bar(x, df['volume'], color=vol_colors, width=0.6)
        ax_vol.set_ylabel('Vol', color=COLORS['text'], fontsize=9)
        
        # RSI with Zones
        rsi = df['rsi'].fillna(50)
        ax_rsi.fill_between(x, 70, 100, color='#ff475720', alpha=0.5)
        ax_rsi.fill_between(x, 0, 30, color='#00d26a20', alpha=0.5)
        ax_rsi.fill_between(x, 30, 70, color='#3498db10', alpha=0.3)
        
        rsi_color = [COLORS['up'] if r > 50 else COLORS['down'] for r in rsi]
        for i in range(1, len(x)):
            ax_rsi.plot([i-1, i], [rsi.iloc[i-1], rsi.iloc[i]], 
                        color=rsi_color[i], linewidth=1.5)
        
        ax_rsi.axhline(70, color='#ff4757', linewidth=1, linestyle='--', alpha=0.5)
        ax_rsi.axhline(30, color='#00d26a', linewidth=1, linestyle='--', alpha=0.5)
        ax_rsi.axhline(50, color=COLORS['text'], linewidth=0.5, linestyle='-', alpha=0.3)
        ax_rsi.set_ylim(0, 100)
        ax_rsi.set_ylabel('RSI', color=COLORS['text'], fontsize=9)
        
        ax_rsi.text(len(df)-1, 75, 'OVERBOUGHT', color='#ff4757', fontsize=8, alpha=0.7)
        ax_rsi.text(len(df)-1, 25, 'OVERSOLD', color='#00d26a', fontsize=8, alpha=0.7)
        
        # MACD
        if 'macd_hist' in df.columns:
            hist = df['macd_hist'].fillna(0)
            hist_colors = [COLORS['up'] if h >= 0 else COLORS['down'] for h in hist]
            ax_macd.bar(x, hist, color=hist_colors, width=0.6, alpha=0.7)
            ax_macd.plot(x, df['macd'].fillna(0), color='#3498db', linewidth=1, label='MACD')
            ax_macd.plot(x, df['macd_signal'].fillna(0), color='#e67e22', linewidth=1, label='Signal')
            ax_macd.axhline(0, color=COLORS['text'], linewidth=0.5, alpha=0.3)
        ax_macd.set_ylabel('MACD', color=COLORS['text'], fontsize=9)
        
        # Title with Confidence Badge
        conf_color = '#00d26a' if confidence >= 85 else '#f1c40f' if confidence >= 70 else '#ff4757'
        conf_text = 'HIGH' if confidence >= 85 else 'MEDIUM' if confidence >= 70 else 'LOW'
        
        side_color = COLORS['up'] if side == 'LONG' else COLORS['down']
        side_emoji = '🟢' if side == 'LONG' else '🔴'
        
        title = f'{side_emoji} {symbol} | {side} | Confidence: {confidence}% [{conf_text}]'
        ax_main.set_title(title, color=COLORS['text'], fontsize=14, fontweight='bold', pad=10)
        
        # Legend
        premium_patch = mpatches.Patch(color=COLORS['premium'], alpha=0.5, label='Premium Zone')
        discount_patch = mpatches.Patch(color=COLORS['discount'], alpha=0.5, label='Discount Zone')
        fvg_bull = mpatches.Patch(color=COLORS['fvg_bull'], alpha=0.5, label='Bullish FVG')
        fvg_bear = mpatches.Patch(color=COLORS['fvg_bear'], alpha=0.5, label='Bearish FVG')
        
        ax_main.legend(handles=[premium_patch, discount_patch, fvg_bull, fvg_bear],
                       loc='upper left', fontsize=8, facecolor=COLORS['panel'],
                       edgecolor=COLORS['grid'], labelcolor=COLORS['text'])
        
        plt.setp(ax_main.get_xticklabels(), visible=False)
        plt.setp(ax_vol.get_xticklabels(), visible=False)
        plt.setp(ax_rsi.get_xticklabels(), visible=False)
        
        plt.tight_layout()
        
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=120, facecolor=COLORS['bg'], 
                    edgecolor='none', bbox_inches='tight')
        buf.seek(0)
        plt.close(fig)
        
        return buf

# ═══════════════════════════════════════════════════════════════════════════════
# PAPER TRADE BOT V4 - Optimized
# ═══════════════════════════════════════════════════════════════════════════════

class PaperTradeBotV4:
    def __init__(self):
        self.exchange = ccxt.binanceusdm({
            'enableRateLimit': True,
            'options': {'defaultType': 'future'}
        })
        
        self.balance = INITIAL_BALANCE
        self.positions = {}
        self.trade_history = []
        self.telegram = TelegramNotifier()
        self.chart = TradingViewChart()
        self.df_cache = {}
        
        self.stats = {
            'total_trades': 0,
            'wins': 0,
            'losses': 0,
            'total_pnl': 0,
            'max_drawdown': 0,
            'peak_balance': INITIAL_BALANCE,
            'by_confidence': {
                'LOW': {'trades': 0, 'wins': 0, 'pnl': 0},
                'MEDIUM': {'trades': 0, 'wins': 0, 'pnl': 0},
                'HIGH': {'trades': 0, 'wins': 0, 'pnl': 0},
            }
        }
        
        self.state_file = Path('paper_state_v4.json')
        self.load_state()
        
    def get_confidence_level(self, confidence: int) -> str:
        if confidence >= 85:
            return 'HIGH'
        elif confidence >= 70:
            return 'MEDIUM'
        else:
            return 'LOW'
    
    def get_position_size(self, confidence: int) -> float:
        """Dynamic Position Sizing - MEDIUM ดีที่สุด!"""
        level = self.get_confidence_level(confidence)
        multiplier = POSITION_SIZE_MULTIPLIERS[level]
        base_size = self.balance / MAX_POSITIONS
        return base_size * multiplier
    
    def save_state(self):
        state = {
            'balance': self.balance,
            'positions': self.positions,
            'trade_history': self.trade_history,
            'stats': self.stats,
            'last_update': datetime.now().isoformat()
        }
        with open(self.state_file, 'w') as f:
            json.dump(state, f, indent=2)
    
    def load_state(self):
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    state = json.load(f)
                self.balance = state.get('balance', INITIAL_BALANCE)
                self.positions = state.get('positions', {})
                self.trade_history = state.get('trade_history', [])
                self.stats = state.get('stats', self.stats)
                print(f"📂 โหลด State V4: Balance ${self.balance:.2f}, Positions: {len(self.positions)}")
            except:
                pass
    
    def get_ohlcv(self, symbol: str) -> pd.DataFrame:
        try:
            ohlcv = self.exchange.fetch_ohlcv(symbol, TIMEFRAME, limit=150)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            return df
        except Exception as e:
            print(f"Error fetching {symbol}: {e}")
            return None
    
    def analyze_signal(self, df: pd.DataFrame) -> dict:
        """วิเคราะห์สัญญาณ - Optimized Confidence"""
        if df is None or len(df) < 50:
            return {'signal': 'NONE'}
        
        df['ema_3'] = ta.ema(df['close'], length=3)
        df['ema_8'] = ta.ema(df['close'], length=8)
        df['ema_20'] = ta.ema(df['close'], length=20)
        df['ema_50'] = ta.ema(df['close'], length=50)
        df['rsi'] = ta.rsi(df['close'], length=14)
        
        macd = ta.macd(df['close'])
        if macd is not None:
            df['macd_hist'] = macd['MACDh_12_26_9']
        
        adx_data = ta.adx(df['high'], df['low'], df['close'], length=14)
        if adx_data is not None:
            df['adx'] = adx_data['ADX_14']
        
        price = df['close'].iloc[-1]
        rsi = df['rsi'].iloc[-1]
        adx = df['adx'].iloc[-1] if 'adx' in df.columns else 0
        macd_hist = df['macd_hist'].iloc[-1] if 'macd_hist' in df.columns else 0
        
        ema_fast = df['ema_3'].iloc[-1]
        ema_slow = df['ema_8'].iloc[-1]
        ema_trend = df['ema_20'].iloc[-1]
        
        trend_up = ema_fast > ema_slow > ema_trend
        trend_down = ema_fast < ema_slow < ema_trend
        
        # Confidence Score (optimized - target MEDIUM range 70-85)
        confidence = 50
        
        # ADX: 30-45 is best (not too high)
        if 30 <= adx <= 45:
            confidence += 25  # Sweet spot
        elif adx > 45:
            confidence += 15  # Too strong = might reverse
        elif adx > 25:
            confidence += min(20, (adx - 25) * 2)
        
        # RSI: 45-55 = neutral = safer entry
        if 45 < rsi < 55:
            confidence += 10
        elif 40 < rsi < 60:
            confidence += 5
            
        # MACD confirmation
        if (trend_up and macd_hist > 0) or (trend_down and macd_hist < 0):
            confidence += 8
        
        confidence = min(95, int(confidence))
        
        # LONG Signal
        if trend_up and adx >= ADX_THRESHOLD and ema_fast > ema_slow and macd_hist > 0:
            if 40 < rsi < 70:
                return {
                    'signal': 'LONG',
                    'price': price,
                    'reason': f'Uptrend | ADX:{adx:.0f} | RSI:{rsi:.0f} | MACD+',
                    'confidence': confidence,
                    'rsi': rsi,
                    'adx': adx
                }
        
        # SHORT Signal
        if trend_down and adx >= ADX_THRESHOLD and ema_fast < ema_slow and macd_hist < 0:
            if 30 < rsi < 60:
                return {
                    'signal': 'SHORT',
                    'price': price,
                    'reason': f'Downtrend | ADX:{adx:.0f} | RSI:{rsi:.0f} | MACD-',
                    'confidence': confidence,
                    'rsi': rsi,
                    'adx': adx
                }
        
        return {'signal': 'NONE', 'price': price}
    
    def open_position(self, symbol: str, side: str, price: float, reason: str, 
                      confidence: int, df: pd.DataFrame):
        """เปิด Position ด้วย Dynamic Position Sizing"""
        if symbol in self.positions or len(self.positions) >= MAX_POSITIONS:
            return False
        
        position_value = self.get_position_size(confidence)
        level = self.get_confidence_level(confidence)
        
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
            'confidence': confidence,
            'confidence_level': level,
            'open_time': datetime.now().isoformat(),
            'reason': reason
        }
        
        self.df_cache[symbol] = df
        
        emoji = "🟢" if side == "LONG" else "🔴"
        conf_emoji = "🔥" if level == "HIGH" else "⚡" if level == "MEDIUM" else "⚠️"
        
        print(f"\n{emoji} [PAPER V4] เปิด {side} {symbol}")
        print(f"   📍 Entry: ${price:,.4f}")
        print(f"   🛡️ SL: ${sl:,.4f} ({SL_PCT*100:.1f}%)")
        print(f"   🎯 TP: ${tp:,.4f} ({TP_PCT*100:.1f}%)")
        print(f"   {conf_emoji} Confidence: {confidence}% [{level}]")
        print(f"   💰 Position Size: ${position_value:.2f} ({POSITION_SIZE_MULTIPLIERS[level]}x)")
        
        multiplier = POSITION_SIZE_MULTIPLIERS[level]
        
        caption = f"""
📝 <b>PAPER TRADE V4 - เปิด {side}!</b>

⚠️ <i>จำลองเท่านั้น - ไม่ใช่เงินจริง!</i>

📊 <b>{symbol}</b>
├ 📍 Entry: <code>${price:,.4f}</code>
├ 🛡️ SL: <code>${sl:,.4f}</code> (-{SL_PCT*100:.1f}%)
├ 🎯 TP: <code>${tp:,.4f}</code> (+{TP_PCT*100:.1f}%)
├ {conf_emoji} Confidence: <b>{confidence}%</b> [{level}]
└ 💰 Size: <code>${position_value:.2f}</code> ({multiplier}x)

📈 R:R = 1:{TP_PCT/SL_PCT:.2f}
💡 เหตุผล: {reason}

🏦 Balance: <code>${self.balance:.2f}</code>
"""
        
        try:
            chart_buf = self.chart.create_pro_chart(df, symbol, price, sl, tp, side, confidence)
            self.telegram.send_photo(chart_buf, caption)
        except Exception as e:
            print(f"Chart error: {e}")
            self.telegram.send_message(caption)
        
        self.save_state()
        return True
    
    def check_position(self, symbol: str, current_price: float) -> dict:
        if symbol not in self.positions:
            return None
        
        pos = self.positions[symbol]
        side = pos['side']
        entry = pos['entry_price']
        sl = pos['sl']
        tp = pos['tp']
        size = pos['size']
        confidence = pos.get('confidence', 75)
        level = pos.get('confidence_level', 'MEDIUM')
        
        result = None
        
        if side == 'LONG':
            if current_price <= sl:
                pnl_pct = (sl - entry) / entry * LEVERAGE * 100
                result = {'type': 'SL', 'pnl_pct': pnl_pct}
            elif current_price >= tp:
                pnl_pct = (tp - entry) / entry * LEVERAGE * 100
                result = {'type': 'TP', 'pnl_pct': pnl_pct}
        else:
            if current_price >= sl:
                pnl_pct = (entry - sl) / entry * LEVERAGE * 100
                result = {'type': 'SL', 'pnl_pct': pnl_pct}
            elif current_price <= tp:
                pnl_pct = (entry - tp) / entry * LEVERAGE * 100
                result = {'type': 'TP', 'pnl_pct': pnl_pct}
        
        if result:
            pnl_usd = size * (result['pnl_pct'] / 100)
            result['pnl_usd'] = pnl_usd
            result['confidence'] = confidence
            result['level'] = level
            result['exit_price'] = sl if result['type'] == 'SL' else tp
            
        return result
    
    def close_position(self, symbol: str, result: dict, current_price: float):
        pos = self.positions[symbol]
        
        pnl_usd = result['pnl_usd']
        self.balance += pnl_usd
        
        self.stats['total_trades'] += 1
        self.stats['total_pnl'] += pnl_usd
        
        level = result.get('level', 'MEDIUM')
        
        if result['type'] == 'TP':
            self.stats['wins'] += 1
            self.stats['by_confidence'][level]['wins'] += 1
            emoji = "🎯"
        else:
            self.stats['losses'] += 1
            emoji = "🛡️"
        
        self.stats['by_confidence'][level]['trades'] += 1
        self.stats['by_confidence'][level]['pnl'] += pnl_usd
        
        if self.balance > self.stats['peak_balance']:
            self.stats['peak_balance'] = self.balance
        drawdown = (self.stats['peak_balance'] - self.balance) / self.stats['peak_balance'] * 100
        self.stats['max_drawdown'] = max(self.stats['max_drawdown'], drawdown)
        
        trade = {
            'symbol': symbol,
            'side': pos['side'],
            'entry': pos['entry_price'],
            'exit': result['exit_price'],
            'pnl_pct': result['pnl_pct'],
            'pnl_usd': pnl_usd,
            'result': result['type'],
            'confidence': result.get('confidence', 75),
            'level': level,
            'close_time': datetime.now().isoformat()
        }
        self.trade_history.append(trade)
        
        win_rate = (self.stats['wins'] / self.stats['total_trades'] * 100) if self.stats['total_trades'] > 0 else 0
        roi = (self.balance - INITIAL_BALANCE) / INITIAL_BALANCE * 100
        
        pnl_emoji = "🟢" if pnl_usd >= 0 else "🔴"
        
        print(f"\n{emoji} [PAPER V4] ปิด {pos['side']} {symbol} - {result['type']}!")
        print(f"   {pnl_emoji} PnL: ${pnl_usd:+.2f} ({result['pnl_pct']:+.1f}%)")
        print(f"   📊 Confidence: {result.get('confidence', 75)}% [{level}]")
        print(f"   💰 Balance: ${self.balance:.2f}")
        print(f"   📈 ROI: {roi:+.1f}% | Win Rate: {win_rate:.1f}%")
        
        msg = f"""
{emoji} <b>PAPER TRADE V4 - ปิด {pos['side']}!</b>

📊 <b>{symbol}</b>
├ 📍 Entry: <code>${pos['entry_price']:,.4f}</code>
├ 🚪 Exit: <code>${result['exit_price']:,.4f}</code>
├ {pnl_emoji} PnL: <code>${pnl_usd:+.2f}</code> ({result['pnl_pct']:+.1f}%)
├ 📊 Confidence: {result.get('confidence', 75)}% [{level}]
└ ✅ ผลลัพธ์: <b>{result['type']}</b>

🏦 <b>สรุป</b>
├ 💰 Balance: <code>${self.balance:.2f}</code>
├ 📈 ROI: <b>{roi:+.1f}%</b>
├ 🎯 Win Rate: {win_rate:.1f}%
└ 📊 Trades: {self.stats['total_trades']} ({self.stats['wins']}W/{self.stats['losses']}L)
"""
        self.telegram.send_message(msg)
        
        del self.positions[symbol]
        if symbol in self.df_cache:
            del self.df_cache[symbol]
        
        self.save_state()
    
    async def scan_markets(self):
        for symbol in COINS:
            if symbol in self.positions:
                continue
            if len(self.positions) >= MAX_POSITIONS:
                break
            
            df = self.get_ohlcv(symbol)
            if df is None:
                continue
            
            signal = self.analyze_signal(df)
            
            if signal['signal'] in ['LONG', 'SHORT']:
                self.open_position(
                    symbol=symbol,
                    side=signal['signal'],
                    price=signal['price'],
                    reason=signal['reason'],
                    confidence=signal.get('confidence', 75),
                    df=df
                )
                await asyncio.sleep(1)
    
    async def monitor_positions(self):
        for symbol in list(self.positions.keys()):
            try:
                ticker = self.exchange.fetch_ticker(symbol)
                current_price = ticker['last']
                
                result = self.check_position(symbol, current_price)
                
                if result:
                    self.close_position(symbol, result, current_price)
                else:
                    pos = self.positions[symbol]
                    if pos['side'] == 'LONG':
                        unrealized_pct = (current_price - pos['entry_price']) / pos['entry_price'] * LEVERAGE * 100
                    else:
                        unrealized_pct = (pos['entry_price'] - current_price) / pos['entry_price'] * LEVERAGE * 100
                    
                    pos['unrealized_pct'] = unrealized_pct
                    pos['current_price'] = current_price
                    
            except Exception as e:
                print(f"Monitor error {symbol}: {e}")
    
    def print_status(self):
        print("\n" + "="*60)
        print("📊 PAPER TRADE BOT V4 - STATUS")
        print("="*60)
        
        total_unrealized = 0
        for symbol, pos in self.positions.items():
            unrealized = pos.get('unrealized_pct', 0)
            total_unrealized += pos['size'] * (unrealized / 100)
            emoji = "🟢" if unrealized >= 0 else "🔴"
            level = pos.get('confidence_level', 'MEDIUM')
            print(f"{emoji} {symbol} {pos['side']} | Entry: ${pos['entry_price']:.4f} | "
                  f"PnL: {unrealized:+.1f}% | Conf: {pos.get('confidence', 75)}% [{level}]")
        
        if not self.positions:
            print("   ไม่มี Position ที่เปิดอยู่")
        
        equity = self.balance + total_unrealized
        roi = (equity - INITIAL_BALANCE) / INITIAL_BALANCE * 100
        
        print(f"\n💰 Balance: ${self.balance:.2f}")
        print(f"💵 Equity: ${equity:.2f}")
        print(f"📈 ROI: {roi:+.1f}%")
        print(f"📊 Trades: {self.stats['total_trades']} ({self.stats['wins']}W/{self.stats['losses']}L)")
        
        print("\n📊 Stats by Confidence:")
        for level in ['LOW', 'MEDIUM', 'HIGH']:
            data = self.stats['by_confidence'][level]
            if data['trades'] > 0:
                wr = data['wins'] / data['trades'] * 100
                print(f"   {level}: {data['trades']} trades, {wr:.0f}% WR, ${data['pnl']:+.2f}")
        
        print("="*60)
    
    async def run(self):
        print("\n" + "="*60)
        print("🚀 PAPER TRADE BOT V4 - Optimized from Backtest")
        print("="*60)
        print(f"💰 Initial Balance: ${INITIAL_BALANCE}")
        print(f"📊 Coins: {len(COINS)} (รวม Meme!)")
        print(f"⚙️ Settings: SL {SL_PCT*100}% | TP {TP_PCT*100}% | R:R 1:{TP_PCT/SL_PCT:.2f}")
        print(f"🎯 ADX Threshold: {ADX_THRESHOLD}")
        print(f"📈 Position Sizing: LOW=0.3x, MEDIUM=1.2x, HIGH=0.8x")
        print("="*60 + "\n")
        
        msg = f"""
🚀 <b>PAPER TRADE BOT V4 เริ่มทำงาน!</b>

⚠️ <i>จำลองเท่านั้น - ไม่ใช่เงินจริง!</i>

📊 <b>การตั้งค่า V4 (Optimized)</b>
├ 💰 Balance: <code>${self.balance:.2f}</code>
├ 📈 Leverage: {LEVERAGE}x
├ 🛡️ SL: {SL_PCT*100}% | 🎯 TP: {TP_PCT*100}%
├ 📊 R:R: 1:{TP_PCT/SL_PCT:.2f}
├ 🎯 ADX Threshold: {ADX_THRESHOLD}
└ 🪙 Coins: {len(COINS)} (รวม Meme!)

🎯 <b>Dynamic Position Sizing (Optimized)</b>
├ ⚠️ LOW (50-70%): 0.3x (ระวัง)
├ ⚡ MEDIUM (70-85%): <b>1.2x</b> (Best!)
└ 🔥 HIGH (85%+): 0.8x (ระวัง)

⏰ Timeframe: {TIMEFRAME}
🔄 Scan Interval: {SCAN_INTERVAL}s
"""
        self.telegram.send_message(msg)
        
        cycle = 0
        status_interval = LIVE_STATUS_INTERVAL * 2
        
        while True:
            try:
                cycle += 1
                print(f"\r🔄 Cycle {cycle} | Positions: {len(self.positions)}/{MAX_POSITIONS}", end="")
                
                await self.monitor_positions()
                await self.scan_markets()
                
                if cycle % status_interval == 0:
                    self.print_status()
                    
                    equity = self.balance + sum(
                        pos['size'] * pos.get('unrealized_pct', 0) / 100 
                        for pos in self.positions.values()
                    )
                    roi = (equity - INITIAL_BALANCE) / INITIAL_BALANCE * 100
                    
                    pos_text = ""
                    for s, p in self.positions.items():
                        u = p.get('unrealized_pct', 0)
                        e = "🟢" if u >= 0 else "🔴"
                        lvl = p.get('confidence_level', 'MED')
                        pos_text += f"\n├ {e} {s.replace('/USDT','')} {p['side']}: {u:+.1f}% [{lvl}]"
                    
                    if not pos_text:
                        pos_text = "\n└ ไม่มี Position"
                    
                    msg = f"""
📊 <b>PAPER BOT V4 - Live Status</b>

💰 Balance: <code>${self.balance:.2f}</code>
💵 Equity: <code>${equity:.2f}</code>
📈 ROI: <b>{roi:+.1f}%</b>
📊 Trades: {self.stats['total_trades']} ({self.stats['wins']}W/{self.stats['losses']}L)

📍 <b>Positions ({len(self.positions)}/{MAX_POSITIONS})</b>{pos_text}

⏰ {datetime.now().strftime('%H:%M:%S')}
"""
                    self.telegram.send_message(msg)
                
                await asyncio.sleep(SCAN_INTERVAL)
                
            except KeyboardInterrupt:
                print("\n\n⏹️ หยุดทำงาน...")
                self.print_status()
                self.save_state()
                break
            except Exception as e:
                print(f"\nError: {e}")
                await asyncio.sleep(5)

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("""
╔═══════════════════════════════════════════════════════════════════╗
║  🚀 PAPER TRADE BOT V4 - OPTIMIZED FROM BACKTEST                 ║
║  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ║
║  ✅ SL 1.8% → TP 2.5% (R:R 1:1.39)                               ║
║  ✅ ADX >= 30 (เหมือนเดิม - ดีอยู่แล้ว!)                          ║
║  ✅ เก็บ Meme Coins (Backtest +40% PnL!)                          ║
║  ✅ MEDIUM confidence = Best (1.2x)                               ║
║  ✅ HIGH/LOW = ระวัง (0.8x/0.3x)                                  ║
╚═══════════════════════════════════════════════════════════════════╝
    """)
    
    bot = PaperTradeBotV4()
    asyncio.run(bot.run())
