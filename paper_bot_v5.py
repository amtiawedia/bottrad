#!/usr/bin/env python3
"""
🚀 Paper Trade Bot V5 - BEST: กำไร + เทรดเยอะ!
===============================================
📊 Backtest Results (5 days, 20 coins):
- 653 trades
- 48.7% Win Rate  
- ROI: +290%!
- Balance: $4.50 → $17.55

✅ Best Settings:
- SL: 1.0% (= -20% at 20x)
- TP: 1.2% (= +24% at 20x)
- R:R = 1:1.2
- ADX >= 20 (เอา trend อ่อนๆ ด้วย = เทรดเยอะ!)
"""

import ccxt
import pandas as pd
import pandas_ta as ta
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.gridspec import GridSpec
import asyncio
import io
import os
import json
from datetime import datetime
from pathlib import Path

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION V5 - BEST: กำไร + เทรดเยอะ
# ═══════════════════════════════════════════════════════════════════════════════

# 🎯 20 COINS - รวม Meme ด้วย (Binance Futures format)
COINS = [
    'BTC/USDT:USDT', 'ETH/USDT:USDT', 'BNB/USDT:USDT', 'XRP/USDT:USDT', 'SOL/USDT:USDT',
    'ADA/USDT:USDT', 'AVAX/USDT:USDT', 'DOT/USDT:USDT', 'NEAR/USDT:USDT', 'SUI/USDT:USDT',
    'ARB/USDT:USDT', 'OP/USDT:USDT', 'LINK/USDT:USDT', 'UNI/USDT:USDT',
    'LTC/USDT:USDT', 'ETC/USDT:USDT', 'FIL/USDT:USDT', 'AAVE/USDT:USDT', 'INJ/USDT:USDT',
    'DOGE/USDT:USDT',
]

# 🏆 BEST SETTINGS FROM BACKTEST
INITIAL_BALANCE = 4.50
LEVERAGE = 20
SL_PCT = 0.010  # 1.0% SL = -20% at 20x
TP_PCT = 0.012  # 1.2% TP = +24% at 20x, R:R = 1:1.2
TIMEFRAME = '5m'
SCAN_INTERVAL = 20  # เร็วขึ้น เพราะ SL/TP แคบ
MAX_POSITIONS = 3
ADX_THRESHOLD = 20  # ต่ำลง = เทรดเยอะขึ้น!
MIN_BARS_BETWEEN_TRADES = 3  # รอน้อยลง = เทรดเยอะ

# Telegram
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '8130246852:AAGR8tzOjabeDaUDt_e8r8KNLXaLgKOH3Rw')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '8254419265')
TELEGRAM_ENABLED = True

LIVE_STATUS_INTERVAL = 10

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
            data = {'chat_id': self.chat_id, 'text': text, 'parse_mode': 'HTML'}
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
            data = {'chat_id': self.chat_id, 'caption': caption, 'parse_mode': 'HTML'}
            resp = requests.post(url, files=files, data=data, timeout=30)
            return resp.status_code == 200
        except Exception as e:
            print(f"Telegram photo error: {e}")
            return False

# ═══════════════════════════════════════════════════════════════════════════════
# SIMPLE CHART (Fast)
# ═══════════════════════════════════════════════════════════════════════════════

class SimpleChart:
    @staticmethod
    def create_chart(df: pd.DataFrame, symbol: str, entry: float, sl: float, tp: float, side: str) -> io.BytesIO:
        df = df.tail(60).copy().reset_index(drop=True)
        
        fig, ax = plt.subplots(figsize=(10, 6), facecolor='#0d1117')
        ax.set_facecolor('#161b22')
        
        # Candlesticks
        for i in range(len(df)):
            o, h, l, c = df['open'].iloc[i], df['high'].iloc[i], df['low'].iloc[i], df['close'].iloc[i]
            color = '#00d26a' if c >= o else '#ff4757'
            ax.plot([i, i], [l, h], color=color, linewidth=1)
            ax.add_patch(plt.Rectangle((i-0.3, min(o,c)), 0.6, abs(c-o) or 0.0001, facecolor=color))
        
        # Entry/SL/TP
        ax.axhline(entry, color='white', linewidth=2)
        ax.axhline(sl, color='#ff4757', linewidth=2, linestyle='--')
        ax.axhline(tp, color='#00d26a', linewidth=2, linestyle='--')
        
        side_marker = '[LONG]' if side == 'LONG' else '[SHORT]'
        side_color = '#00d26a' if side == 'LONG' else '#ff4757'
        ax.set_title(f'{side_marker} {symbol}', color=side_color, fontsize=14, fontweight='bold')
        ax.tick_params(colors='white')
        ax.grid(True, color='#21262d', alpha=0.3)
        
        plt.tight_layout()
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=100, facecolor='#0d1117')
        buf.seek(0)
        plt.close(fig)
        return buf

# ═══════════════════════════════════════════════════════════════════════════════
# PAPER TRADE BOT V5
# ═══════════════════════════════════════════════════════════════════════════════

class PaperTradeBotV5:
    def __init__(self):
        self.exchange = ccxt.binanceusdm({
            'enableRateLimit': True,
            'options': {'defaultType': 'future'}
        })
        
        self.balance = INITIAL_BALANCE
        self.positions = {}
        self.trade_history = []
        self.telegram = TelegramNotifier()
        self.chart = SimpleChart()
        self.last_trade_time = {}  # Track last trade per symbol
        
        self.stats = {
            'total_trades': 0,
            'wins': 0,
            'losses': 0,
            'total_pnl': 0,
            'peak_balance': INITIAL_BALANCE,
        }
        
        self.state_file = Path('paper_state_v5.json')
        self.load_state()
    
    def save_state(self):
        state = {
            'balance': self.balance,
            'positions': self.positions,
            'trade_history': self.trade_history[-50:],  # Keep last 50
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
                print(f"📂 Load V5: Balance ${self.balance:.2f}, {len(self.positions)} positions")
            except:
                pass
    
    def get_ohlcv(self, symbol: str) -> pd.DataFrame:
        try:
            ohlcv = self.exchange.fetch_ohlcv(symbol, TIMEFRAME, limit=100)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            return df
        except:
            return None
    
    def analyze_signal(self, df: pd.DataFrame) -> dict:
        if df is None or len(df) < 50:
            return {'signal': 'NONE'}
        
        df['ema_3'] = ta.ema(df['close'], length=3)
        df['ema_8'] = ta.ema(df['close'], length=8)
        df['ema_20'] = ta.ema(df['close'], length=20)
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
        
        if pd.isna(adx) or pd.isna(rsi):
            return {'signal': 'NONE', 'price': price}
        
        trend_up = ema_fast > ema_slow > ema_trend
        trend_down = ema_fast < ema_slow < ema_trend
        
        # LONG Signal
        if trend_up and adx >= ADX_THRESHOLD and macd_hist > 0 and 40 < rsi < 70:
            return {
                'signal': 'LONG',
                'price': price,
                'reason': f'Uptrend|ADX:{adx:.0f}|RSI:{rsi:.0f}',
                'adx': adx,
                'rsi': rsi
            }
        
        # SHORT Signal
        if trend_down and adx >= ADX_THRESHOLD and macd_hist < 0 and 30 < rsi < 60:
            return {
                'signal': 'SHORT',
                'price': price,
                'reason': f'Downtrend|ADX:{adx:.0f}|RSI:{rsi:.0f}',
                'adx': adx,
                'rsi': rsi
            }
        
        return {'signal': 'NONE', 'price': price}
    
    def open_position(self, symbol: str, side: str, price: float, reason: str, df: pd.DataFrame):
        if symbol in self.positions or len(self.positions) >= MAX_POSITIONS:
            return False
        
        # Check min bars between trades
        now = datetime.now()
        if symbol in self.last_trade_time:
            elapsed = (now - self.last_trade_time[symbol]).total_seconds()
            if elapsed < MIN_BARS_BETWEEN_TRADES * 5 * 60:  # 5m per bar
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
            'open_time': now.isoformat(),
            'reason': reason
        }
        
        self.last_trade_time[symbol] = now
        
        emoji = "🟢" if side == "LONG" else "🔴"
        print(f"\n{emoji} [V5] OPEN {side} {symbol} @ ${price:.4f}")
        print(f"   SL: ${sl:.4f} ({SL_PCT*100:.1f}%) | TP: ${tp:.4f} ({TP_PCT*100:.1f}%)")
        
        # Telegram
        caption = f"""
{emoji} <b>PAPER V5 - OPEN {side}</b>

📊 <b>{symbol}</b>
├ Entry: <code>${price:,.4f}</code>
├ SL: <code>${sl:,.4f}</code> (-{SL_PCT*100:.1f}%)
├ TP: <code>${tp:,.4f}</code> (+{TP_PCT*100:.1f}%)
└ Size: <code>${position_value:.2f}</code>

💡 {reason}
"""
        try:
            chart_buf = self.chart.create_chart(df, symbol, price, sl, tp, side)
            self.telegram.send_photo(chart_buf, caption)
        except:
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
        
        result = None
        
        if side == 'LONG':
            if current_price <= sl:
                pnl_pct = (sl - entry) / entry * LEVERAGE * 100
                result = {'type': 'SL', 'pnl_pct': pnl_pct, 'exit_price': sl}
            elif current_price >= tp:
                pnl_pct = (tp - entry) / entry * LEVERAGE * 100
                result = {'type': 'TP', 'pnl_pct': pnl_pct, 'exit_price': tp}
        else:
            if current_price >= sl:
                pnl_pct = (entry - sl) / entry * LEVERAGE * 100
                result = {'type': 'SL', 'pnl_pct': pnl_pct, 'exit_price': sl}
            elif current_price <= tp:
                pnl_pct = (entry - tp) / entry * LEVERAGE * 100
                result = {'type': 'TP', 'pnl_pct': pnl_pct, 'exit_price': tp}
        
        if result:
            result['pnl_usd'] = pos['size'] * (result['pnl_pct'] / 100)
            
        return result
    
    def close_position(self, symbol: str, result: dict):
        pos = self.positions[symbol]
        
        pnl_usd = result['pnl_usd']
        self.balance += pnl_usd
        
        self.stats['total_trades'] += 1
        self.stats['total_pnl'] += pnl_usd
        
        if result['type'] == 'TP':
            self.stats['wins'] += 1
            emoji = "🎯"
        else:
            self.stats['losses'] += 1
            emoji = "🛡️"
        
        if self.balance > self.stats['peak_balance']:
            self.stats['peak_balance'] = self.balance
        
        trade = {
            'symbol': symbol,
            'side': pos['side'],
            'entry': pos['entry_price'],
            'exit': result['exit_price'],
            'pnl_pct': result['pnl_pct'],
            'pnl_usd': pnl_usd,
            'result': result['type'],
            'time': datetime.now().isoformat()
        }
        self.trade_history.append(trade)
        
        win_rate = (self.stats['wins'] / self.stats['total_trades'] * 100) if self.stats['total_trades'] > 0 else 0
        roi = (self.balance - INITIAL_BALANCE) / INITIAL_BALANCE * 100
        
        pnl_emoji = "🟢" if pnl_usd >= 0 else "🔴"
        
        print(f"\n{emoji} [V5] CLOSE {pos['side']} {symbol} - {result['type']}")
        print(f"   {pnl_emoji} PnL: ${pnl_usd:+.2f} ({result['pnl_pct']:+.1f}%)")
        print(f"   💰 Balance: ${self.balance:.2f} | ROI: {roi:+.1f}%")
        print(f"   📊 {self.stats['total_trades']} trades ({self.stats['wins']}W/{self.stats['losses']}L) {win_rate:.1f}% WR")
        
        msg = f"""
{emoji} <b>PAPER V5 - CLOSE {pos['side']}</b>

📊 <b>{symbol}</b>
├ Entry: <code>${pos['entry_price']:,.4f}</code>
├ Exit: <code>${result['exit_price']:,.4f}</code>
├ {pnl_emoji} PnL: <code>${pnl_usd:+.2f}</code> ({result['pnl_pct']:+.1f}%)
└ Result: <b>{result['type']}</b>

🏦 Balance: <code>${self.balance:.2f}</code>
📈 ROI: <b>{roi:+.1f}%</b>
📊 Trades: {self.stats['total_trades']} ({self.stats['wins']}W/{self.stats['losses']}L)
🎯 Win Rate: {win_rate:.1f}%
"""
        self.telegram.send_message(msg)
        
        del self.positions[symbol]
        self.save_state()
    
    async def scan_markets(self):
        for symbol in COINS:
            if symbol in self.positions or len(self.positions) >= MAX_POSITIONS:
                continue
            
            df = self.get_ohlcv(symbol)
            if df is None:
                continue
            
            signal = self.analyze_signal(df)
            
            if signal['signal'] in ['LONG', 'SHORT']:
                self.open_position(
                    symbol=symbol,
                    side=signal['signal'],
                    price=signal['price'],
                    reason=signal.get('reason', ''),
                    df=df
                )
                await asyncio.sleep(0.5)
    
    async def monitor_positions(self):
        for symbol in list(self.positions.keys()):
            try:
                ticker = self.exchange.fetch_ticker(symbol)
                current_price = ticker['last']
                
                result = self.check_position(symbol, current_price)
                
                if result:
                    self.close_position(symbol, result)
                else:
                    pos = self.positions[symbol]
                    if pos['side'] == 'LONG':
                        unrealized = (current_price - pos['entry_price']) / pos['entry_price'] * LEVERAGE * 100
                    else:
                        unrealized = (pos['entry_price'] - current_price) / pos['entry_price'] * LEVERAGE * 100
                    pos['unrealized_pct'] = unrealized
                    pos['current_price'] = current_price
                    
            except Exception as e:
                pass
    
    def print_status(self):
        print("\n" + "="*50)
        print("📊 PAPER BOT V5 - STATUS")
        print("="*50)
        
        total_unrealized = 0
        for symbol, pos in self.positions.items():
            unrealized = pos.get('unrealized_pct', 0)
            total_unrealized += pos['size'] * (unrealized / 100)
            emoji = "🟢" if unrealized >= 0 else "🔴"
            print(f"{emoji} {symbol} {pos['side']}: {unrealized:+.1f}%")
        
        if not self.positions:
            print("   No positions")
        
        equity = self.balance + total_unrealized
        roi = (equity - INITIAL_BALANCE) / INITIAL_BALANCE * 100
        wr = (self.stats['wins'] / self.stats['total_trades'] * 100) if self.stats['total_trades'] > 0 else 0
        
        print(f"\n💰 Balance: ${self.balance:.2f}")
        print(f"💵 Equity: ${equity:.2f}")
        print(f"📈 ROI: {roi:+.1f}%")
        print(f"📊 Trades: {self.stats['total_trades']} ({self.stats['wins']}W/{self.stats['losses']}L) {wr:.1f}%")
        print("="*50)
    
    async def run(self):
        print("\n" + "="*60)
        print("🚀 PAPER BOT V5 - กำไร + เทรดเยอะ!")
        print("="*60)
        print(f"💰 Balance: ${INITIAL_BALANCE}")
        print(f"⚙️ SL: {SL_PCT*100}% | TP: {TP_PCT*100}% | R:R: 1:{TP_PCT/SL_PCT:.1f}")
        print(f"📊 ADX >= {ADX_THRESHOLD} | Coins: {len(COINS)}")
        print("="*60 + "\n")
        
        msg = f"""
🚀 <b>PAPER BOT V5 เริ่มทำงาน!</b>

⚠️ <i>Paper Trade - ไม่ใช่เงินจริง!</i>

📊 <b>Settings (Best from Backtest!)</b>
├ Balance: <code>${self.balance:.2f}</code>
├ Leverage: {LEVERAGE}x
├ SL: {SL_PCT*100}% | TP: {TP_PCT*100}%
├ R:R: 1:{TP_PCT/SL_PCT:.1f}
├ ADX: >= {ADX_THRESHOLD}
└ Coins: {len(COINS)}

🏆 <b>Backtest Results:</b>
├ 653 trades
├ 48.7% Win Rate
└ +290% ROI!
"""
        self.telegram.send_message(msg)
        
        cycle = 0
        status_interval = LIVE_STATUS_INTERVAL * 3
        
        while True:
            try:
                cycle += 1
                print(f"\r🔄 Cycle {cycle} | Pos: {len(self.positions)}/{MAX_POSITIONS} | Trades: {self.stats['total_trades']}", end="")
                
                await self.monitor_positions()
                await self.scan_markets()
                
                if cycle % status_interval == 0:
                    self.print_status()
                    
                    equity = self.balance + sum(
                        pos['size'] * pos.get('unrealized_pct', 0) / 100 
                        for pos in self.positions.values()
                    )
                    roi = (equity - INITIAL_BALANCE) / INITIAL_BALANCE * 100
                    wr = (self.stats['wins'] / self.stats['total_trades'] * 100) if self.stats['total_trades'] > 0 else 0
                    
                    pos_text = ""
                    for s, p in self.positions.items():
                        u = p.get('unrealized_pct', 0)
                        e = "🟢" if u >= 0 else "🔴"
                        pos_text += f"\n├ {e} {s.replace('/USDT','')} {p['side']}: {u:+.1f}%"
                    if not pos_text:
                        pos_text = "\n└ No positions"
                    
                    msg = f"""
📊 <b>V5 Live Status</b>

💰 Balance: <code>${self.balance:.2f}</code>
💵 Equity: <code>${equity:.2f}</code>
📈 ROI: <b>{roi:+.1f}%</b>
📊 Trades: {self.stats['total_trades']} ({self.stats['wins']}W/{self.stats['losses']}L)
🎯 Win Rate: {wr:.1f}%

📍 <b>Positions ({len(self.positions)}/{MAX_POSITIONS})</b>{pos_text}

⏰ {datetime.now().strftime('%H:%M:%S')}
"""
                    self.telegram.send_message(msg)
                
                await asyncio.sleep(SCAN_INTERVAL)
                
            except KeyboardInterrupt:
                print("\n\n⏹️ Stopping...")
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
║  🚀 PAPER BOT V5 - BEST: กำไร + เทรดเยอะ!                        ║
║  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ║
║  📊 Backtest: 653 trades, 48.7% WR, +290% ROI                    ║
║  ⚙️ SL 1.0% / TP 1.2% / ADX >= 20                                 ║
╚═══════════════════════════════════════════════════════════════════╝
    """)
    
    bot = PaperTradeBotV5()
    asyncio.run(bot.run())
