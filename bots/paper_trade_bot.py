#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                     📝 PAPER TRADE BOT                                       ║
║               Long + Short | Top 30 Coins | ไม่ใช้เงินจริง                    ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  ✅ ปลอดภัย - ไม่เสียเงินจริง                                                  ║
║  ✅ สแกน 30 เหรียญ ทั้ง Long และ Short                                        ║
║  ✅ บันทึกผลลงไฟล์ paper_trades.json                                          ║
╚══════════════════════════════════════════════════════════════════════════════╝

วิธีรัน:
  Windows: ดับเบิ้ลคลิก RUN_PAPER_TRADE.bat
  หรือ: python bots/paper_trade_bot.py
"""

import ccxt
import pandas as pd
import pandas_ta as ta
import os
import sys
import time
import json
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from dotenv import load_dotenv
    load_dotenv()
except:
    pass

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION - แก้ไขได้ตามต้องการ
# ═══════════════════════════════════════════════════════════════════════════════

# Top 30 coins จาก backtest (เหรียญที่ดีที่สุด)
COINS = [
    # ⭐⭐ Top performers (WR 40%+)
    'DOGE/USDT', 'ETC/USDT', 'INJ/USDT', 'NEAR/USDT', 'RUNE/USDT',
    # ⭐ Good performers (profitable)
    'SOL/USDT', 'AVAX/USDT', 'FIL/USDT', 'ARB/USDT', 'OP/USDT',
    'SEI/USDT', 'SUI/USDT', 'PEPE/USDT', 'WIF/USDT', 'ORDI/USDT',
    'STX/USDT', 'IMX/USDT', 'FTM/USDT', 'AAVE/USDT', 'GRT/USDT',
    # Major coins
    'BTC/USDT', 'ETH/USDT', 'XRP/USDT', 'BNB/USDT', 'ADA/USDT',
    'LINK/USDT', 'DOT/USDT', 'MATIC/USDT', 'LTC/USDT', 'UNI/USDT',
]

# ตั้งค่าการเทรด
INITIAL_BALANCE = 4.50      # ยอดเริ่มต้น (USD)
LEVERAGE = 50               # Leverage 50x
SL_PCT = 0.012              # Stop Loss 1.2%
TP_PCT = 0.050              # Take Profit 5.0%
TIMEFRAME = '5m'            # Timeframe 5 นาที
SCAN_INTERVAL = 30          # สแกนทุก 30 วินาที
MAX_POSITIONS = 3           # เปิดได้สูงสุด 3 positions

# ═══════════════════════════════════════════════════════════════════════════════
# PAPER TRADING ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class PaperTradeBot:
    def __init__(self):
        print("\n" + "="*70)
        print("📝 PAPER TRADE BOT - Initializing...")
        print("="*70)
        
        self.exchange = ccxt.binanceusdm({
            'apiKey': os.environ.get('BINANCE_API_KEY', ''),
            'secret': os.environ.get('BINANCE_SECRET_KEY', ''),
            'sandbox': False,
            'options': {'defaultType': 'future'}
        })
        
        self.balance = INITIAL_BALANCE
        self.positions = {}
        self.trade_history = []
        self.stats = {
            'total_trades': 0,
            'wins': 0,
            'losses': 0,
            'total_pnl': 0.0,
            'best_trade': 0.0,
            'worst_trade': 0.0,
        }
        
        print("🔄 Loading Binance markets...")
        self.exchange.load_markets()
        print(f"✅ Loaded {len(self.exchange.markets)} markets")
        
    def get_signal(self, symbol: str) -> dict:
        """วิเคราะห์เหรียญและส่งสัญญาณ LONG/SHORT/NONE"""
        try:
            ohlcv = self.exchange.fetch_ohlcv(symbol, TIMEFRAME, limit=100)
            if len(ohlcv) < 60:
                return {'signal': 'NONE', 'reason': 'Not enough data'}
            
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
                        'reason': f'Uptrend+ADX{adx:.0f}+RSI{rsi:.0f}+MACD+',
                        'confidence': min(90, 50 + adx)
                    }
            
            # SHORT Signal
            if not trend_up and adx > 30 and ema_fast < ema_slow and macd_hist < 0:
                if 30 < rsi < 55:
                    return {
                        'signal': 'SHORT',
                        'price': price,
                        'reason': f'Downtrend+ADX{adx:.0f}+RSI{rsi:.0f}+MACD-',
                        'confidence': min(90, 50 + adx)
                    }
            
            return {'signal': 'NONE', 'price': price, 'reason': 'No signal'}
            
        except Exception as e:
            return {'signal': 'ERROR', 'reason': str(e)}
    
    def open_position(self, symbol: str, side: str, price: float, reason: str):
        """เปิด position (Paper Trade)"""
        if symbol in self.positions:
            return False
        
        if len(self.positions) >= MAX_POSITIONS:
            print(f"  ⚠️ Max positions ({MAX_POSITIONS}) reached")
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
            'open_time': datetime.now(),
            'reason': reason
        }
        
        emoji = "🟢" if side == "LONG" else "🔴"
        print(f"\n{emoji} OPENED {side} on {symbol}")
        print(f"   📍 Entry: ${price:,.4f}")
        print(f"   🛡️ SL: ${sl:,.4f} | 🎯 TP: ${tp:,.4f}")
        print(f"   💰 Size: ${position_value:.2f} x {LEVERAGE}x")
        print(f"   📝 Reason: {reason}")
        
        return True
    
    def check_positions(self):
        """ตรวจสอบ SL/TP ของทุก position"""
        closed = []
        
        for symbol, pos in self.positions.items():
            try:
                ticker = self.exchange.fetch_ticker(symbol)
                current_price = ticker['last']
                
                hit_sl = False
                hit_tp = False
                
                if pos['side'] == 'LONG':
                    hit_sl = current_price <= pos['sl']
                    hit_tp = current_price >= pos['tp']
                else:
                    hit_sl = current_price >= pos['sl']
                    hit_tp = current_price <= pos['tp']
                
                if hit_sl or hit_tp:
                    if pos['side'] == 'LONG':
                        pnl_pct = (current_price - pos['entry_price']) / pos['entry_price']
                    else:
                        pnl_pct = (pos['entry_price'] - current_price) / pos['entry_price']
                    
                    pnl_leveraged = pnl_pct * LEVERAGE
                    pnl_usd = pos['size'] * pnl_leveraged
                    
                    exit_reason = "TP ✅" if hit_tp else "SL ❌"
                    
                    self.balance += pnl_usd
                    
                    self.stats['total_trades'] += 1
                    self.stats['total_pnl'] += pnl_usd
                    
                    if pnl_usd > 0:
                        self.stats['wins'] += 1
                        if pnl_usd > self.stats['best_trade']:
                            self.stats['best_trade'] = pnl_usd
                    else:
                        self.stats['losses'] += 1
                        if pnl_usd < self.stats['worst_trade']:
                            self.stats['worst_trade'] = pnl_usd
                    
                    self.trade_history.append({
                        'symbol': symbol,
                        'side': pos['side'],
                        'entry': pos['entry_price'],
                        'exit': current_price,
                        'pnl': pnl_usd,
                        'pnl_pct': pnl_leveraged * 100,
                        'exit_reason': exit_reason,
                        'time': datetime.now().isoformat()
                    })
                    
                    emoji = "🟢" if pnl_usd > 0 else "🔴"
                    print(f"\n{emoji} CLOSED {pos['side']} on {symbol}")
                    print(f"   📍 Entry: ${pos['entry_price']:,.4f} → Exit: ${current_price:,.4f}")
                    print(f"   💰 PnL: {'+' if pnl_usd > 0 else ''}{pnl_usd:.4f} USD ({pnl_leveraged*100:+.1f}%)")
                    print(f"   📝 Exit: {exit_reason}")
                    print(f"   💵 Balance: ${self.balance:.4f}")
                    
                    closed.append(symbol)
                    
            except Exception as e:
                print(f"  ⚠️ Error checking {symbol}: {e}")
        
        for symbol in closed:
            del self.positions[symbol]
    
    def print_status(self):
        """แสดงสถานะปัจจุบัน"""
        win_rate = (self.stats['wins'] / self.stats['total_trades'] * 100) if self.stats['total_trades'] > 0 else 0
        roi = ((self.balance - INITIAL_BALANCE) / INITIAL_BALANCE) * 100
        
        print(f"\n{'='*70}")
        print(f"📊 PAPER TRADE STATUS - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*70}")
        print(f"💰 Balance: ${self.balance:.4f} (ROI: {roi:+.2f}%)")
        print(f"📈 Trades: {self.stats['total_trades']} | ✅ {self.stats['wins']}W / ❌ {self.stats['losses']}L | WR: {win_rate:.1f}%")
        print(f"💵 Total PnL: ${self.stats['total_pnl']:+.4f}")
        
        if self.positions:
            print(f"\n📊 Open Positions ({len(self.positions)}/{MAX_POSITIONS}):")
            for symbol, pos in self.positions.items():
                try:
                    ticker = self.exchange.fetch_ticker(symbol)
                    current = ticker['last']
                    if pos['side'] == 'LONG':
                        pnl_pct = (current - pos['entry_price']) / pos['entry_price'] * LEVERAGE * 100
                    else:
                        pnl_pct = (pos['entry_price'] - current) / pos['entry_price'] * LEVERAGE * 100
                    emoji = "🟢" if pnl_pct > 0 else "🔴"
                    print(f"   {emoji} {pos['side']} {symbol}: Entry ${pos['entry_price']:.4f} | Now ${current:.4f} | PnL: {pnl_pct:+.1f}%")
                except:
                    print(f"   📊 {pos['side']} {symbol}: Entry ${pos['entry_price']:.4f}")
        else:
            print(f"\n⏳ No open positions - scanning for signals...")
        
        print(f"{'='*70}\n")
    
    def scan_and_trade(self):
        """สแกนทุกเหรียญและเทรดตามสัญญาณ"""
        print(f"\n🔍 Scanning {len(COINS)} coins for signals...")
        
        signals_found = []
        
        for symbol in COINS:
            if symbol in self.positions:
                continue
            
            signal = self.get_signal(symbol)
            
            if signal['signal'] in ['LONG', 'SHORT']:
                signals_found.append({
                    'symbol': symbol,
                    'signal': signal['signal'],
                    'price': signal['price'],
                    'reason': signal['reason'],
                    'confidence': signal.get('confidence', 50)
                })
        
        signals_found.sort(key=lambda x: x['confidence'], reverse=True)
        
        if signals_found:
            print(f"\n📡 Found {len(signals_found)} signals:")
            for sig in signals_found[:5]:
                emoji = "🟢" if sig['signal'] == "LONG" else "🔴"
                print(f"   {emoji} {sig['signal']} {sig['symbol']}: ${sig['price']:.4f} ({sig['reason']})")
            
            for sig in signals_found:
                if len(self.positions) >= MAX_POSITIONS:
                    break
                self.open_position(sig['symbol'], sig['signal'], sig['price'], sig['reason'])
        else:
            print("   ⏳ No signals found")
    
    def save_trades(self):
        """บันทึก trades ลงไฟล์"""
        if self.trade_history:
            filepath = Path(__file__).parent.parent / 'paper_trades.json'
            with open(filepath, 'w') as f:
                json.dump({
                    'balance': self.balance,
                    'initial_balance': INITIAL_BALANCE,
                    'roi_pct': ((self.balance - INITIAL_BALANCE) / INITIAL_BALANCE) * 100,
                    'stats': self.stats,
                    'trades': self.trade_history
                }, f, indent=2)
    
    def run(self):
        """Main loop"""
        print(f"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                     📝 PAPER TRADE BOT STARTED                               ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  Mode: PAPER TRADE (ไม่ใช้เงินจริง)                                           ║
║  Coins: {len(COINS)} เหรียญ (Top performers + Major)                             ║
║  Direction: LONG + SHORT (ทั้งขึ้นและลง)                                      ║
║  Leverage: {LEVERAGE}x | SL: {SL_PCT*100}% | TP: {TP_PCT*100}%                                        ║
║  Starting Balance: ${INITIAL_BALANCE}                                               ║
║                                                                              ║
║  กด Ctrl+C เพื่อหยุด                                                          ║
╚══════════════════════════════════════════════════════════════════════════════╝
        """)
        
        iteration = 0
        
        try:
            while True:
                iteration += 1
                
                if self.positions:
                    self.check_positions()
                
                self.scan_and_trade()
                
                if iteration % 5 == 0:
                    self.print_status()
                
                self.save_trades()
                
                print(f"⏳ Next scan in {SCAN_INTERVAL}s... (Ctrl+C to stop)")
                time.sleep(SCAN_INTERVAL)
                
        except KeyboardInterrupt:
            print("\n\n🛑 Bot stopped by user")
            self.print_status()
            
            roi = ((self.balance - INITIAL_BALANCE) / INITIAL_BALANCE) * 100
            print("\n📊 FINAL SUMMARY:")
            print(f"   Starting: ${INITIAL_BALANCE}")
            print(f"   Ending: ${self.balance:.4f}")
            print(f"   ROI: {roi:+.2f}%")
            print(f"   Trades: {self.stats['total_trades']}")
            
            self.save_trades()
            print("\n📝 Trade History saved to: paper_trades.json")


if __name__ == "__main__":
    bot = PaperTradeBot()
    bot.run()
