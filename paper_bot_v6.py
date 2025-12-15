#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                    PAPER BOT V6 - BINANCE STYLE DISPLAY                       ║
║                     แสดงผลเหมือน Binance Futures จริง!                          ║
╚═══════════════════════════════════════════════════════════════════════════════╝

Settings (Best from Backtest):
- SL: 1.0% | TP: 1.2% | ADX >= 20
- Backtest: 653 trades, 48.7% WR, +290% ROI
"""

import ccxt
import pandas as pd
import pandas_ta as ta
import asyncio
import aiohttp
import json
import os
import io
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, field, asdict
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

TELEGRAM_TOKEN = "8130246852:AAGR8tzOjabeDaUDt_e8r8KNLXaLgKOH3Rw"
TELEGRAM_CHAT_ID = "8254419265"

# Trading Settings - BEST from Backtest
INITIAL_BALANCE = 4.5          # Starting balance USDT
LEVERAGE = 20                   # 20x leverage
POSITION_SIZE_PCT = 0.3         # 30% per position
MAX_POSITIONS = 3
SL_PERCENT = 1.0               # Stop Loss 1.0%
TP_PERCENT = 1.2               # Take Profit 1.2%
ADX_THRESHOLD = 20             # ADX >= 20

# Coins to trade (Binance Futures format: SYMBOL/USDT:USDT)
SYMBOLS = [
    'BTC/USDT:USDT', 'ETH/USDT:USDT', 'BNB/USDT:USDT', 'SOL/USDT:USDT', 'XRP/USDT:USDT',
    'DOGE/USDT:USDT', 'ADA/USDT:USDT', 'AVAX/USDT:USDT', 'LINK/USDT:USDT', 'DOT/USDT:USDT',
    'POL/USDT:USDT', 'UNI/USDT:USDT', 'ATOM/USDT:USDT', 'LTC/USDT:USDT', 'FIL/USDT:USDT',
    'APT/USDT:USDT', 'ARB/USDT:USDT', 'OP/USDT:USDT', 'INJ/USDT:USDT', 'SUI/USDT:USDT'
]

STATE_FILE = 'paper_state_v6.json'

# ═══════════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class Position:
    symbol: str
    side: str              # 'LONG' or 'SHORT'
    entry_price: float
    size: float            # Size in USDT (notional value)
    quantity: float        # Quantity of coin
    margin: float          # Margin used
    sl_price: float
    tp_price: float
    entry_time: str
    leverage: int = LEVERAGE
    
    def calculate_pnl(self, current_price: float) -> tuple:
        """Calculate PnL and ROI"""
        if self.side == 'LONG':
            pnl = (current_price - self.entry_price) * self.quantity
            price_change_pct = ((current_price - self.entry_price) / self.entry_price) * 100
        else:  # SHORT
            pnl = (self.entry_price - current_price) * self.quantity
            price_change_pct = ((self.entry_price - current_price) / self.entry_price) * 100
        
        roi = price_change_pct * self.leverage  # ROI = price change * leverage
        return pnl, roi
    
    def calculate_liq_price(self) -> float:
        """Calculate liquidation price (simplified)"""
        # Liq price = Entry * (1 - 1/leverage) for LONG
        # Liq price = Entry * (1 + 1/leverage) for SHORT
        margin_ratio = 1 / self.leverage
        if self.side == 'LONG':
            return self.entry_price * (1 - margin_ratio * 0.9)  # 90% of margin
        else:
            return self.entry_price * (1 + margin_ratio * 0.9)

@dataclass 
class BotState:
    balance: float = INITIAL_BALANCE
    positions: Dict = field(default_factory=dict)
    closed_trades: List = field(default_factory=list)
    total_pnl: float = 0.0
    wins: int = 0
    losses: int = 0

# ═══════════════════════════════════════════════════════════════════════════════
# TELEGRAM
# ═══════════════════════════════════════════════════════════════════════════════

async def send_telegram(message: str, image: io.BytesIO = None):
    try:
        async with aiohttp.ClientSession() as session:
            if image:
                url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
                data = aiohttp.FormData()
                data.add_field('chat_id', TELEGRAM_CHAT_ID)
                data.add_field('caption', message, content_type='text/plain')
                data.add_field('parse_mode', 'HTML')
                data.add_field('photo', image, filename='chart.png')
                await session.post(url, data=data)
            else:
                url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
                await session.post(url, json={
                    'chat_id': TELEGRAM_CHAT_ID,
                    'text': message,
                    'parse_mode': 'HTML'
                })
    except Exception as e:
        print(f"Telegram error: {e}")

# ═══════════════════════════════════════════════════════════════════════════════
# SIMPLE CHART
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
# BINANCE STYLE DISPLAY
# ═══════════════════════════════════════════════════════════════════════════════

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def display_binance_style(state: BotState, current_prices: Dict[str, float], cycle: int):
    """Display positions like Binance Futures interface"""
    clear_screen()
    
    # Header
    print("=" * 80)
    print("                    📊 PAPER TRADING BOT V6 - BINANCE STYLE")
    print("=" * 80)
    print(f"  💰 Balance: ${state.balance:.2f} USDT    |    ⏰ {datetime.now().strftime('%H:%M:%S')}")
    print(f"  📈 Cycle: {cycle}    |    🎯 Trades: {state.wins + state.losses} (W:{state.wins} L:{state.losses})")
    print("=" * 80)
    
    # Calculate total unrealized PnL
    total_unrealized_pnl = 0.0
    total_margin = 0.0
    
    if state.positions:
        print(f"\n  📋 Positions ({len(state.positions)})                                              ")
        print("-" * 80)
        
        for symbol, pos_dict in state.positions.items():
            pos = Position(**pos_dict) if isinstance(pos_dict, dict) else pos_dict
            current_price = current_prices.get(symbol, pos.entry_price)
            pnl, roi = pos.calculate_pnl(current_price)
            liq_price = pos.calculate_liq_price()
            
            total_unrealized_pnl += pnl
            total_margin += pos.margin
            
            # Side indicator
            if pos.side == 'LONG':
                side_icon = "🟢 B"
                side_color = "LONG"
            else:
                side_icon = "🔴 S"
                side_color = "SHORT"
            
            # PnL color
            pnl_sign = "+" if pnl >= 0 else ""
            roi_sign = "+" if roi >= 0 else ""
            
            # Display like Binance
            symbol_display = symbol.replace('/', '')
            print(f"\n  {side_icon} {symbol_display}  Perp  Cross {pos.leverage}X")
            print(f"  {'─' * 70}")
            
            # Row 1: PNL and ROI
            pnl_str = f"{pnl_sign}{pnl:.2f}"
            roi_str = f"{roi_sign}{roi:.2f}%"
            if pnl >= 0:
                print(f"  PNL (USDT)                                                      ROI")
                print(f"  \033[92m{pnl_str}\033[0m                                                        \033[92m{roi_str}\033[0m")
            else:
                print(f"  PNL (USDT)                                                      ROI")
                print(f"  \033[91m{pnl_str}\033[0m                                                       \033[91m{roi_str}\033[0m")
            
            # Row 2: Size, Margin, Margin Ratio
            margin_ratio = (pos.margin / state.balance) * 100 if state.balance > 0 else 0
            print(f"\n  Size (USDT)         Margin (USDT)                    Margin Ratio")
            print(f"  {pos.size:.4f}             {pos.margin:.2f}                            {margin_ratio:.2f}%")
            
            # Row 3: Entry, Mark, Liq Price
            print(f"\n  Entry Price         Mark Price                       Liq.Price (USDT)")
            print(f"  {pos.entry_price:.4f}            {current_price:.4f}                        {liq_price:.4f}")
            
            # Row 4: TP/SL
            print(f"\n  TP/SL  {pos.tp_price:.4f} / {pos.sl_price:.4f}")
            
            print(f"  {'─' * 70}")
    else:
        print("\n  📭 No open positions")
        print("-" * 80)
    
    # Summary
    print("\n" + "=" * 80)
    print("  📊 SUMMARY")
    print("-" * 80)
    
    equity = state.balance + total_unrealized_pnl
    total_roi = ((equity - INITIAL_BALANCE) / INITIAL_BALANCE) * 100
    
    if total_unrealized_pnl >= 0:
        print(f"  Unrealized PnL: \033[92m+${total_unrealized_pnl:.2f}\033[0m")
    else:
        print(f"  Unrealized PnL: \033[91m${total_unrealized_pnl:.2f}\033[0m")
    
    print(f"  Total Margin:   ${total_margin:.2f}")
    print(f"  Equity:         ${equity:.2f}")
    print(f"  Total PnL:      ${state.total_pnl:.2f}")
    
    if total_roi >= 0:
        print(f"  Total ROI:      \033[92m+{total_roi:.2f}%\033[0m")
    else:
        print(f"  Total ROI:      \033[91m{total_roi:.2f}%\033[0m")
    
    if state.wins + state.losses > 0:
        win_rate = (state.wins / (state.wins + state.losses)) * 100
        print(f"  Win Rate:       {win_rate:.1f}%")
    
    print("=" * 80)
    print("  Press Ctrl+C to stop bot")
    print("=" * 80)

# ═══════════════════════════════════════════════════════════════════════════════
# PAPER TRADE BOT V6
# ═══════════════════════════════════════════════════════════════════════════════

class PaperTradeBotV6:
    def __init__(self):
        self.exchange = ccxt.binanceusdm({'enableRateLimit': True})
        self.state = self.load_state()
        
    def load_state(self) -> BotState:
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, 'r') as f:
                    data = json.load(f)
                    return BotState(**data)
            except:
                pass
        return BotState()
    
    def save_state(self):
        with open(STATE_FILE, 'w') as f:
            json.dump(asdict(self.state), f, indent=2, default=str)
    
    def get_ohlcv(self, symbol: str) -> Optional[pd.DataFrame]:
        try:
            ohlcv = self.exchange.fetch_ohlcv(symbol, '5m', limit=100)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            return df
        except:
            return None
    
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        df['ema3'] = ta.ema(df['close'], length=3)
        df['ema8'] = ta.ema(df['close'], length=8)
        df['ema20'] = ta.ema(df['close'], length=20)
        df['rsi'] = ta.rsi(df['close'], length=14)
        
        macd = ta.macd(df['close'], fast=12, slow=26, signal=9)
        df['macd'] = macd['MACD_12_26_9']
        df['macd_signal'] = macd['MACDs_12_26_9']
        
        adx = ta.adx(df['high'], df['low'], df['close'], length=14)
        df['adx'] = adx['ADX_14']
        
        return df
    
    def check_signal(self, df: pd.DataFrame) -> Optional[str]:
        if len(df) < 25:
            return None
            
        c = df.iloc[-1]
        p = df.iloc[-2]
        
        # ADX filter
        if pd.isna(c['adx']) or c['adx'] < ADX_THRESHOLD:
            return None
        
        # LONG Signal
        if (c['ema3'] > c['ema8'] > c['ema20'] and
            30 <= c['rsi'] <= 70 and
            c['macd'] > c['macd_signal'] and
            p['macd'] <= p['macd_signal']):
            return 'LONG'
        
        # SHORT Signal
        if (c['ema3'] < c['ema8'] < c['ema20'] and
            30 <= c['rsi'] <= 70 and
            c['macd'] < c['macd_signal'] and
            p['macd'] >= p['macd_signal']):
            return 'SHORT'
        
        return None
    
    async def open_position(self, symbol: str, side: str, price: float, df: pd.DataFrame):
        # Calculate position size
        position_value = self.state.balance * POSITION_SIZE_PCT
        margin = position_value  # Margin = position value / leverage, but we use full value for paper
        size = position_value * LEVERAGE  # Notional value
        quantity = size / price
        
        # Calculate SL/TP
        if side == 'LONG':
            sl_price = price * (1 - SL_PERCENT / 100)
            tp_price = price * (1 + TP_PERCENT / 100)
        else:
            sl_price = price * (1 + SL_PERCENT / 100)
            tp_price = price * (1 - TP_PERCENT / 100)
        
        # Create position
        pos = Position(
            symbol=symbol,
            side=side,
            entry_price=price,
            size=size,
            quantity=quantity,
            margin=margin,
            sl_price=sl_price,
            tp_price=tp_price,
            entry_time=datetime.now().isoformat(),
            leverage=LEVERAGE
        )
        
        self.state.positions[symbol] = asdict(pos)
        self.state.balance -= margin  # Deduct margin
        self.save_state()
        
        # Telegram notification
        side_emoji = "🟢" if side == "LONG" else "🔴"
        roi_if_tp = TP_PERCENT * LEVERAGE
        roi_if_sl = -SL_PERCENT * LEVERAGE
        
        msg = f"""
{side_emoji} <b>[V6] OPEN {side}</b> {symbol}

💵 Entry: <code>${price:.4f}</code>
📊 Size: <code>${size:.2f}</code> ({LEVERAGE}x)
💰 Margin: <code>${margin:.2f}</code>

🎯 TP: <code>${tp_price:.4f}</code> (+{roi_if_tp:.0f}% ROI)
🛑 SL: <code>${sl_price:.4f}</code> ({roi_if_sl:.0f}% ROI)

⏰ {datetime.now().strftime('%H:%M:%S')}
"""
        
        chart = SimpleChart.create_chart(df, symbol, price, sl_price, tp_price, side)
        await send_telegram(msg.strip(), chart)
        
        print(f"{side_emoji} [V6] OPEN {side} {symbol} @ ${price:.4f}")
        print(f"   Size: ${size:.2f} | Margin: ${margin:.2f}")
        print(f"   SL: ${sl_price:.4f} ({SL_PERCENT}%) | TP: ${tp_price:.4f} ({TP_PERCENT}%)")
    
    async def check_positions(self, current_prices: Dict[str, float]):
        closed = []
        
        for symbol, pos_dict in list(self.state.positions.items()):
            pos = Position(**pos_dict)
            current_price = current_prices.get(symbol)
            
            if not current_price:
                continue
            
            pnl, roi = pos.calculate_pnl(current_price)
            hit_tp = hit_sl = False
            
            if pos.side == 'LONG':
                hit_tp = current_price >= pos.tp_price
                hit_sl = current_price <= pos.sl_price
            else:
                hit_tp = current_price <= pos.tp_price
                hit_sl = current_price >= pos.sl_price
            
            if hit_tp or hit_sl:
                # Calculate final PnL
                exit_price = pos.tp_price if hit_tp else pos.sl_price
                final_pnl, final_roi = pos.calculate_pnl(exit_price)
                
                # Update state
                self.state.balance += pos.margin + final_pnl  # Return margin + PnL
                self.state.total_pnl += final_pnl
                
                if final_pnl >= 0:
                    self.state.wins += 1
                    emoji = "✅"
                    result = "WIN"
                else:
                    self.state.losses += 1
                    emoji = "❌"
                    result = "LOSS"
                
                closed.append(symbol)
                
                # Record trade
                self.state.closed_trades.append({
                    'symbol': symbol,
                    'side': pos.side,
                    'entry': pos.entry_price,
                    'exit': exit_price,
                    'pnl': final_pnl,
                    'roi': final_roi,
                    'result': result,
                    'time': datetime.now().isoformat()
                })
                
                # Telegram notification
                pnl_sign = "+" if final_pnl >= 0 else ""
                roi_sign = "+" if final_roi >= 0 else ""
                
                msg = f"""
{emoji} <b>[V6] CLOSE {pos.side}</b> {symbol}

💵 Entry: <code>${pos.entry_price:.4f}</code>
💵 Exit: <code>${exit_price:.4f}</code>

📊 PnL: <code>{pnl_sign}${final_pnl:.2f}</code>
📈 ROI: <code>{roi_sign}{final_roi:.2f}%</code>

💰 Balance: <code>${self.state.balance:.2f}</code>
📊 Total PnL: <code>${self.state.total_pnl:.2f}</code>
🎯 W/L: {self.state.wins}/{self.state.losses}

⏰ {datetime.now().strftime('%H:%M:%S')}
"""
                await send_telegram(msg.strip())
                
                print(f"{emoji} [V6] CLOSE {pos.side} {symbol} | PnL: {pnl_sign}${final_pnl:.2f} | ROI: {roi_sign}{final_roi:.2f}%")
        
        # Remove closed positions
        for symbol in closed:
            del self.state.positions[symbol]
        
        self.save_state()
    
    async def get_current_prices(self) -> Dict[str, float]:
        """Get current prices for all symbols"""
        prices = {}
        try:
            tickers = self.exchange.fetch_tickers(SYMBOLS)
            for symbol in SYMBOLS:
                if symbol in tickers:
                    prices[symbol] = tickers[symbol]['last']
        except:
            pass
        return prices
    
    async def run(self):
        # Startup message
        startup_msg = f"""
🚀 <b>Paper Bot V6 Started!</b>
━━━━━━━━━━━━━━━━━━━━━━━

📊 <b>Settings:</b>
• SL: {SL_PERCENT}% | TP: {TP_PERCENT}%
• Leverage: {LEVERAGE}x
• ADX Filter: ≥ {ADX_THRESHOLD}
• Max Positions: {MAX_POSITIONS}

💰 <b>Balance:</b> ${self.state.balance:.2f}
📈 <b>Total PnL:</b> ${self.state.total_pnl:.2f}

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        await send_telegram(startup_msg.strip())
        
        cycle = 0
        while True:
            try:
                cycle += 1
                
                # Get current prices
                current_prices = await self.get_current_prices()
                
                # Check existing positions
                await self.check_positions(current_prices)
                
                # Display Binance style
                display_binance_style(self.state, current_prices, cycle)
                
                # Look for new signals if we have room
                if len(self.state.positions) < MAX_POSITIONS:
                    for symbol in SYMBOLS:
                        if symbol in self.state.positions:
                            continue
                        if len(self.state.positions) >= MAX_POSITIONS:
                            break
                        
                        df = self.get_ohlcv(symbol)
                        if df is None:
                            continue
                        
                        df = self.calculate_indicators(df)
                        signal = self.check_signal(df)
                        
                        if signal:
                            price = df['close'].iloc[-1]
                            await self.open_position(symbol, signal, price, df)
                            # Update display after opening
                            current_prices[symbol] = price
                            display_binance_style(self.state, current_prices, cycle)
                
                await asyncio.sleep(30)
                
            except KeyboardInterrupt:
                print("\n\n⏹️ Bot stopped by user")
                break
            except Exception as e:
                print(f"Error: {e}")
                await asyncio.sleep(10)

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("🚀 Starting Paper Bot V6 - Binance Style...")
    bot = PaperTradeBotV6()
    asyncio.run(bot.run())
