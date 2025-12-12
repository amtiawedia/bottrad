#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                     📝 PAPER TRADE BOT V2                                    ║
║               Long + Short | 30 เหรียญ | ไม่ใช้เงินจริง                       ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  ✅ ปลอดภัย 100% - ไม่เสียเงินจริง                                            ║
║  ✅ สแกน 30 เหรียญ ทั้ง Long และ Short                                        ║
║  ✅ บันทึกผลลงไฟล์ trades.json                                                ║
╚══════════════════════════════════════════════════════════════════════════════╝

วิธีรัน:
  Windows: ดับเบิ้ลคลิก START.bat
  Terminal: python bot.py
"""

import ccxt
import pandas as pd
import pandas_ta as ta
import os
import time
import json
from datetime import datetime

# ═══════════════════════════════════════════════════════════════════════════════
# ตั้งค่า - แก้ไขได้ตามต้องการ
# ═══════════════════════════════════════════════════════════════════════════════

# API Keys (ใส่ตรงนี้ หรือ สร้างไฟล์ .env)
API_KEY = os.environ.get('BINANCE_API_KEY', '')
SECRET_KEY = os.environ.get('BINANCE_SECRET_KEY', '')

# 30 เหรียญที่ดีที่สุดจาก Backtest
COINS = [
    # ⭐⭐ Top performers
    'DOGE/USDT', 'ETC/USDT', 'INJ/USDT', 'NEAR/USDT', 'RUNE/USDT',
    # ⭐ Good performers
    'SOL/USDT', 'AVAX/USDT', 'FIL/USDT', 'ARB/USDT', 'OP/USDT',
    'SEI/USDT', 'SUI/USDT', 'PEPE/USDT', 'WIF/USDT', 'ORDI/USDT',
    'STX/USDT', 'IMX/USDT', 'FTM/USDT', 'AAVE/USDT', 'GRT/USDT',
    # Major coins
    'BTC/USDT', 'ETH/USDT', 'XRP/USDT', 'BNB/USDT', 'ADA/USDT',
    'LINK/USDT', 'DOT/USDT', 'MATIC/USDT', 'LTC/USDT', 'UNI/USDT',
]

# ตั้งค่าการเทรด
BALANCE = 4.50              # ยอดเริ่มต้น (USD)
LEVERAGE = 50               # Leverage 50x
SL_PCT = 0.012              # Stop Loss 1.2%
TP_PCT = 0.050              # Take Profit 5.0%
TIMEFRAME = '5m'            # 5 นาที
SCAN_INTERVAL = 30          # สแกนทุก 30 วินาที
MAX_POSITIONS = 3           # เปิดได้สูงสุด 3 positions

# ═══════════════════════════════════════════════════════════════════════════════

class Bot:
    def __init__(self):
        print("\n" + "="*60)
        print("📝 PAPER TRADE BOT V2")
        print("="*60)
        
        self.exchange = ccxt.binanceusdm({
            'apiKey': API_KEY,
            'secret': SECRET_KEY,
            'sandbox': False,
            'options': {'defaultType': 'future'}
        })
        
        self.balance = BALANCE
        self.positions = {}
        self.trades = []
        self.wins = 0
        self.losses = 0
        
        print("🔄 Loading markets...")
        self.exchange.load_markets()
        print(f"✅ Loaded {len(self.exchange.markets)} markets\n")
    
    def analyze(self, symbol):
        """วิเคราะห์และส่งสัญญาณ"""
        try:
            data = self.exchange.fetch_ohlcv(symbol, TIMEFRAME, limit=100)
            if len(data) < 60:
                return None
            
            df = pd.DataFrame(data, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
            
            # Indicators
            df['rsi'] = ta.rsi(df['close'], length=14)
            df['ema3'] = ta.ema(df['close'], length=3)
            df['ema8'] = ta.ema(df['close'], length=8)
            df['ema20'] = ta.ema(df['close'], length=20)
            df['ema50'] = ta.ema(df['close'], length=50)
            adx = ta.adx(df['high'], df['low'], df['close'], length=14)
            df['adx'] = adx['ADX_14'] if 'ADX_14' in adx.columns else 25
            macd = ta.macd(df['close'], fast=12, slow=26, signal=9)
            df['macd'] = macd['MACDh_12_26_9']
            
            r = df.iloc[-1]
            price = float(r['close'])
            rsi = float(r['rsi']) if pd.notna(r['rsi']) else 50
            adx = float(r['adx']) if pd.notna(r['adx']) else 25
            ema3 = float(r['ema3']) if pd.notna(r['ema3']) else 0
            ema8 = float(r['ema8']) if pd.notna(r['ema8']) else 0
            ema20 = float(r['ema20']) if pd.notna(r['ema20']) else 0
            ema50 = float(r['ema50']) if pd.notna(r['ema50']) else 0
            macd_h = float(r['macd']) if pd.notna(r['macd']) else 0
            
            uptrend = ema20 > ema50
            
            # LONG
            if uptrend and adx > 30 and ema3 > ema8 and macd_h > 0 and 45 < rsi < 70:
                return {'side': 'LONG', 'price': price, 'adx': adx, 'rsi': rsi}
            
            # SHORT
            if not uptrend and adx > 30 and ema3 < ema8 and macd_h < 0 and 30 < rsi < 55:
                return {'side': 'SHORT', 'price': price, 'adx': adx, 'rsi': rsi}
            
            return None
        except:
            return None
    
    def open_trade(self, symbol, signal):
        """เปิด position"""
        if symbol in self.positions or len(self.positions) >= MAX_POSITIONS:
            return
        
        price = signal['price']
        size = self.balance / MAX_POSITIONS
        
        if signal['side'] == 'LONG':
            sl = price * (1 - SL_PCT)
            tp = price * (1 + TP_PCT)
        else:
            sl = price * (1 + SL_PCT)
            tp = price * (1 - TP_PCT)
        
        self.positions[symbol] = {
            'side': signal['side'],
            'entry': price,
            'size': size,
            'sl': sl,
            'tp': tp,
            'time': datetime.now()
        }
        
        emoji = "🟢" if signal['side'] == "LONG" else "🔴"
        print(f"\n{emoji} OPEN {signal['side']} {symbol}")
        print(f"   Entry: ${price:.4f} | SL: ${sl:.4f} | TP: ${tp:.4f}")
    
    def check_trades(self):
        """ตรวจ SL/TP"""
        to_close = []
        
        for symbol, pos in self.positions.items():
            try:
                ticker = self.exchange.fetch_ticker(symbol)
                price = ticker['last']
                
                hit_sl = hit_tp = False
                if pos['side'] == 'LONG':
                    hit_sl = price <= pos['sl']
                    hit_tp = price >= pos['tp']
                else:
                    hit_sl = price >= pos['sl']
                    hit_tp = price <= pos['tp']
                
                if hit_sl or hit_tp:
                    # คำนวณ PnL
                    if pos['side'] == 'LONG':
                        pnl_pct = (price - pos['entry']) / pos['entry']
                    else:
                        pnl_pct = (pos['entry'] - price) / pos['entry']
                    
                    pnl = pos['size'] * pnl_pct * LEVERAGE
                    self.balance += pnl
                    
                    if pnl > 0:
                        self.wins += 1
                    else:
                        self.losses += 1
                    
                    # บันทึก
                    self.trades.append({
                        'symbol': symbol,
                        'side': pos['side'],
                        'entry': pos['entry'],
                        'exit': price,
                        'pnl': pnl,
                        'pnl_pct': pnl_pct * LEVERAGE * 100,
                        'result': 'TP' if hit_tp else 'SL',
                        'time': datetime.now().isoformat()
                    })
                    
                    emoji = "✅" if pnl > 0 else "❌"
                    result = "TP" if hit_tp else "SL"
                    print(f"\n{emoji} CLOSE {pos['side']} {symbol} [{result}]")
                    print(f"   PnL: ${pnl:+.4f} ({pnl_pct*LEVERAGE*100:+.1f}%)")
                    print(f"   Balance: ${self.balance:.4f}")
                    
                    to_close.append(symbol)
            except:
                pass
        
        for s in to_close:
            del self.positions[s]
    
    def status(self):
        """แสดงสถานะ"""
        total = self.wins + self.losses
        wr = (self.wins / total * 100) if total > 0 else 0
        roi = ((self.balance - BALANCE) / BALANCE) * 100
        
        print(f"\n{'='*60}")
        print(f"📊 STATUS - {datetime.now().strftime('%H:%M:%S')}")
        print(f"{'='*60}")
        print(f"💰 Balance: ${self.balance:.4f} ({roi:+.2f}% ROI)")
        print(f"📈 Trades: {total} | ✅ {self.wins}W / ❌ {self.losses}L | WR: {wr:.0f}%")
        
        if self.positions:
            print(f"\n📊 Positions ({len(self.positions)}/{MAX_POSITIONS}):")
            for sym, pos in self.positions.items():
                try:
                    t = self.exchange.fetch_ticker(sym)
                    now = t['last']
                    if pos['side'] == 'LONG':
                        pnl = (now - pos['entry']) / pos['entry'] * LEVERAGE * 100
                    else:
                        pnl = (pos['entry'] - now) / pos['entry'] * LEVERAGE * 100
                    e = "🟢" if pnl > 0 else "🔴"
                    print(f"   {e} {pos['side']} {sym}: {pnl:+.1f}%")
                except:
                    print(f"   📊 {pos['side']} {sym}")
        
        print(f"{'='*60}\n")
    
    def save(self):
        """บันทึกลงไฟล์"""
        with open('trades.json', 'w') as f:
            json.dump({
                'balance': self.balance,
                'start_balance': BALANCE,
                'roi': ((self.balance - BALANCE) / BALANCE) * 100,
                'wins': self.wins,
                'losses': self.losses,
                'trades': self.trades
            }, f, indent=2)
    
    def run(self):
        """Main loop"""
        print(f"""
╔══════════════════════════════════════════════════════════════╗
║               📝 PAPER TRADE BOT STARTED                     ║
╠══════════════════════════════════════════════════════════════╣
║  Mode: Paper Trade (ไม่ใช้เงินจริง)                           ║
║  Coins: {len(COINS)} เหรียญ                                         ║
║  Direction: Long + Short                                     ║
║  Leverage: {LEVERAGE}x | SL: {SL_PCT*100}% | TP: {TP_PCT*100}%                           ║
║  Balance: ${BALANCE}                                           ║
║                                                              ║
║  กด Ctrl+C เพื่อหยุด                                          ║
╚══════════════════════════════════════════════════════════════╝
        """)
        
        count = 0
        try:
            while True:
                count += 1
                
                # ตรวจ positions
                if self.positions:
                    self.check_trades()
                
                # สแกนหาสัญญาณ
                print(f"🔍 Scanning {len(COINS)} coins...")
                signals = []
                for coin in COINS:
                    if coin in self.positions:
                        continue
                    sig = self.analyze(coin)
                    if sig:
                        signals.append((coin, sig))
                
                if signals:
                    print(f"📡 Found {len(signals)} signals")
                    for coin, sig in signals:
                        if len(self.positions) < MAX_POSITIONS:
                            self.open_trade(coin, sig)
                
                # แสดงสถานะทุก 5 รอบ
                if count % 5 == 0:
                    self.status()
                
                self.save()
                
                print(f"⏳ Next scan in {SCAN_INTERVAL}s...")
                time.sleep(SCAN_INTERVAL)
                
        except KeyboardInterrupt:
            print("\n\n🛑 Stopped!")
            self.status()
            self.save()
            print("📝 Saved to trades.json")


if __name__ == "__main__":
    # โหลด .env ถ้ามี
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except:
        pass
    
    bot = Bot()
    bot.run()
