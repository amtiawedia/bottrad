#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                     📝 PAPER TRADE BOT - FINAL                               ║
║              ไม่ต้องใช้ API Key - 100% Public API Only                        ║
║             Long + Short | Top 30 Coins | Real-time Simulation               ║
╚══════════════════════════════════════════════════════════════════════════════╝

วิธีรัน:
    python paper_bot.py

ไม่ต้องตั้งค่าอะไรเลย ทำงานได้เลย!
"""

import ccxt
import pandas as pd
import pandas_ta as ta
import os
import time
import json
from datetime import datetime

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION - แก้ไขได้ตามต้องการ
# ═══════════════════════════════════════════════════════════════════════════════

# Top 30 coins from backtest (best performers + major coins)
COINS = [
    # ⭐⭐⭐ Best performers from backtest
    'DOGE/USDT', 'ETC/USDT', 'INJ/USDT', 'NEAR/USDT', 'RUNE/USDT',
    # ⭐⭐ Good performers
    'SOL/USDT', 'AVAX/USDT', 'FIL/USDT', 'ARB/USDT', 'OP/USDT',
    'SEI/USDT', 'SUI/USDT', 'PEPE/USDT', 'WIF/USDT', 'ORDI/USDT',
    'STX/USDT', 'IMX/USDT', 'FTM/USDT', 'AAVE/USDT', 'GRT/USDT',
    # Major coins for liquidity
    'BTC/USDT', 'ETH/USDT', 'XRP/USDT', 'BNB/USDT', 'ADA/USDT',
    'LINK/USDT', 'DOT/USDT', 'MATIC/USDT', 'LTC/USDT', 'UNI/USDT',
]

# ═══════════════════════════════════════════════════════════════════════════════
# TRADING SETTINGS - ตั้งค่าการเทรด
# ═══════════════════════════════════════════════════════════════════════════════
INITIAL_BALANCE = 4.50      # เงินเริ่มต้น (จำลอง)
LEVERAGE = 50               # Leverage 50x (จำลอง)
SL_PCT = 0.012              # Stop Loss 1.2%
TP_PCT = 0.050              # Take Profit 5.0%
TIMEFRAME = '5m'            # Timeframe 5 นาที
SCAN_INTERVAL = 30          # สแกนทุก 30 วินาที
MAX_POSITIONS = 3           # เปิด position พร้อมกันได้สูงสุด 3

# ═══════════════════════════════════════════════════════════════════════════════
# PAPER TRADING ENGINE - ไม่ใช้ API KEY
# ═══════════════════════════════════════════════════════════════════════════════

class PaperTradeBot:
    def __init__(self):
        # ใช้ PUBLIC API เท่านั้น - ไม่ต้องใส่ API Key!
        print("🔄 เชื่อมต่อ Binance Futures (Public API)...")
        self.exchange = ccxt.binanceusdm({
            'enableRateLimit': True,
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
            'long_wins': 0,
            'long_losses': 0,
            'short_wins': 0,
            'short_losses': 0,
        }
        
        try:
            self.exchange.load_markets()
            print(f"✅ เชื่อมต่อสำเร็จ! โหลด {len(self.exchange.markets)} ตลาด")
        except Exception as e:
            print(f"⚠️ Warning: {e}")
        
    def get_signal(self, symbol: str) -> dict:
        """วิเคราะห์เหรียญและส่งสัญญาณ LONG/SHORT/NONE"""
        try:
            ohlcv = self.exchange.fetch_ohlcv(symbol, TIMEFRAME, limit=100)
            if len(ohlcv) < 60:
                return {'signal': 'NONE', 'reason': 'ข้อมูลไม่พอ'}
            
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            
            # คำนวณ Indicators
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
            
            # สัญญาณ LONG
            if trend_up and adx > 30 and ema_fast > ema_slow and macd_hist > 0:
                if 45 < rsi < 70:
                    return {
                        'signal': 'LONG',
                        'price': price,
                        'reason': f'Uptrend+ADX{adx:.0f}+RSI{rsi:.0f}+MACD+',
                        'confidence': min(90, 50 + adx)
                    }
            
            # สัญญาณ SHORT
            if not trend_up and adx > 30 and ema_fast < ema_slow and macd_hist < 0:
                if 30 < rsi < 55:
                    return {
                        'signal': 'SHORT',
                        'price': price,
                        'reason': f'Downtrend+ADX{adx:.0f}+RSI{rsi:.0f}+MACD-',
                        'confidence': min(90, 50 + adx)
                    }
            
            return {'signal': 'NONE', 'price': price, 'reason': 'ไม่มีสัญญาณ'}
            
        except Exception as e:
            return {'signal': 'ERROR', 'reason': str(e)}
    
    def get_current_price(self, symbol: str) -> float:
        """ดึงราคาปัจจุบันจาก Public API"""
        try:
            ticker = self.exchange.fetch_ticker(symbol)
            return ticker['last']
        except:
            return 0.0
    
    def open_position(self, symbol: str, side: str, price: float, reason: str):
        """เปิด Paper Position (ไม่มี order จริง)"""
        if symbol in self.positions:
            return False
        
        if len(self.positions) >= MAX_POSITIONS:
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
        
        emoji = "🟢" if side == "LONG" else "🔴"
        print(f"\n{emoji} [PAPER] เปิด {side} {symbol}")
        print(f"   📍 Entry: ${price:,.4f}")
        print(f"   🛡️ SL: ${sl:,.4f} | 🎯 TP: ${tp:,.4f}")
        print(f"   💰 Size: ${position_value:.2f} x {LEVERAGE}x")
        
        return True
    
    def check_positions(self):
        """เช็ค positions ว่าโดน SL/TP หรือยัง"""
        closed = []
        
        for symbol, pos in self.positions.items():
            try:
                current_price = self.get_current_price(symbol)
                if current_price == 0:
                    continue
                
                hit_sl = False
                hit_tp = False
                
                if pos['side'] == 'LONG':
                    hit_sl = current_price <= pos['sl']
                    hit_tp = current_price >= pos['tp']
                else:
                    hit_sl = current_price >= pos['sl']
                    hit_tp = current_price <= pos['tp']
                
                if hit_sl or hit_tp:
                    # คำนวณ PnL
                    if pos['side'] == 'LONG':
                        pnl_pct = (current_price - pos['entry_price']) / pos['entry_price']
                    else:
                        pnl_pct = (pos['entry_price'] - current_price) / pos['entry_price']
                    
                    pnl_leveraged = pnl_pct * LEVERAGE
                    pnl_usd = pos['size'] * pnl_leveraged
                    
                    # อัพเดท balance
                    self.balance += pnl_usd
                    
                    # อัพเดท stats
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
                    
                    # บันทึก trade
                    self.trade_history.append({
                        'symbol': symbol,
                        'side': pos['side'],
                        'entry': pos['entry_price'],
                        'exit': current_price,
                        'pnl_usd': round(pnl_usd, 4),
                        'pnl_pct': round(pnl_leveraged * 100, 2),
                        'exit_reason': 'TP' if hit_tp else 'SL',
                        'time': datetime.now().isoformat()
                    })
                    
                    # แสดงผล
                    exit_type = "🎯 TP HIT" if hit_tp else "🛡️ SL HIT"
                    emoji = "✅" if pnl_usd > 0 else "❌"
                    print(f"\n{emoji} [PAPER] ปิด {pos['side']} {symbol}")
                    print(f"   📍 Entry: ${pos['entry_price']:,.4f} → Exit: ${current_price:,.4f}")
                    print(f"   💰 PnL: {'+' if pnl_usd > 0 else ''}{pnl_usd:.4f} USD ({pnl_leveraged*100:+.1f}%)")
                    print(f"   📝 {exit_type}")
                    print(f"   💵 Balance: ${self.balance:.4f}")
                    
                    closed.append(symbol)
                    
            except Exception as e:
                print(f"  ⚠️ Error {symbol}: {e}")
        
        for symbol in closed:
            del self.positions[symbol]
    
    def print_status(self):
        """แสดงสถานะปัจจุบัน"""
        win_rate = (self.stats['wins'] / self.stats['total_trades'] * 100) if self.stats['total_trades'] > 0 else 0
        roi = ((self.balance - INITIAL_BALANCE) / INITIAL_BALANCE) * 100
        
        print(f"\n{'═'*70}")
        print(f"📊 PAPER TRADE STATUS - {datetime.now().strftime('%H:%M:%S')}")
        print(f"{'═'*70}")
        print(f"💰 Balance: ${self.balance:.4f} | เริ่ม: ${INITIAL_BALANCE} | ROI: {roi:+.2f}%")
        print(f"📈 เทรด: {self.stats['total_trades']} | ✅ {self.stats['wins']}W / ❌ {self.stats['losses']}L | WR: {win_rate:.1f}%")
        print(f"   🟢 Long: {self.stats['long_wins']}W/{self.stats['long_losses']}L | 🔴 Short: {self.stats['short_wins']}W/{self.stats['short_losses']}L")
        
        if self.positions:
            print(f"\n📊 Positions ({len(self.positions)}/{MAX_POSITIONS}):")
            for symbol, pos in self.positions.items():
                current = self.get_current_price(symbol)
                if current > 0:
                    if pos['side'] == 'LONG':
                        pnl_pct = (current - pos['entry_price']) / pos['entry_price'] * LEVERAGE * 100
                    else:
                        pnl_pct = (pos['entry_price'] - current) / pos['entry_price'] * LEVERAGE * 100
                    
                    emoji = "📈" if pnl_pct > 0 else "📉"
                    side_emoji = "🟢" if pos['side'] == 'LONG' else "🔴"
                    print(f"   {side_emoji} {pos['side']} {symbol}: ${pos['entry_price']:.4f} → ${current:.4f} | {emoji} {pnl_pct:+.1f}%")
        else:
            print(f"\n⏳ ไม่มี position - กำลังหาสัญญาณ...")
        
        # Progress bar
        goal = 50.0
        progress = min(100, (self.balance / goal) * 100)
        bars = int(progress / 5)
        print(f"\n🎯 เป้าหมาย: ${self.balance:.2f} / ${goal:.2f} ({progress:.0f}%)")
        print(f"   {'█' * bars}{'░' * (20 - bars)}")
        print(f"{'═'*70}\n")
    
    def scan_and_trade(self):
        """สแกนเหรียญทั้งหมดและเปิด trade"""
        print(f"\n🔍 สแกน {len(COINS)} เหรียญ...")
        
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
            
            time.sleep(0.1)
        
        signals_found.sort(key=lambda x: x['confidence'], reverse=True)
        
        if signals_found:
            long_count = len([s for s in signals_found if s['signal'] == 'LONG'])
            short_count = len([s for s in signals_found if s['signal'] == 'SHORT'])
            print(f"\n📡 พบ {len(signals_found)} สัญญาณ (🟢 {long_count} LONG | 🔴 {short_count} SHORT)")
            
            for sig in signals_found[:5]:
                emoji = "🟢" if sig['signal'] == "LONG" else "🔴"
                print(f"   {emoji} {sig['signal']} {sig['symbol']}: ${sig['price']:.4f} | {sig['reason']}")
            
            for sig in signals_found:
                if len(self.positions) >= MAX_POSITIONS:
                    break
                self.open_position(sig['symbol'], sig['signal'], sig['price'], sig['reason'])
        else:
            print("   ⏳ ไม่พบสัญญาณ")
    
    def save_state(self):
        """บันทึก state ลงไฟล์"""
        state = {
            'balance': self.balance,
            'stats': self.stats,
            'positions': self.positions,
            'trades': self.trade_history,
            'last_update': datetime.now().isoformat()
        }
        with open('paper_trades.json', 'w') as f:
            json.dump(state, f, indent=2)
    
    def load_state(self):
        """โหลด state จากไฟล์ (ถ้ามี)"""
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
║                     📝 PAPER TRADE BOT                                       ║
║                  จำลองการเทรด - ไม่มี order จริง                              ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  🎯 เป้าหมาย: $4.50 → $50.00 (+1,011%)                                       ║
║  📊 เหรียญ: {len(COINS)} เหรียญ                                                       ║
║  📈 ทิศทาง: LONG + SHORT                                                     ║
║  ⚡ Leverage: {LEVERAGE}x | 🛡️ SL: {SL_PCT*100}% | 🎯 TP: {TP_PCT*100}%                                ║
║  💰 เงินเริ่มต้น: ${INITIAL_BALANCE}                                                  ║
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
                
                if iteration % 3 == 0:
                    self.print_status()
                
                self.save_state()
                
                if self.balance >= 50.0:
                    print("\n🎉🎉🎉 ถึงเป้าหมาย $50 แล้ว! 🎉🎉🎉\n")
                    self.print_status()
                    break
                
                if self.balance < 0.50:
                    print("\n💀 หมดตัว! Balance ต่ำเกินไป 💀\n")
                    self.print_status()
                    break
                
                print(f"⏳ รอ {SCAN_INTERVAL} วินาที... (Ctrl+C หยุด)")
                time.sleep(SCAN_INTERVAL)
                
        except KeyboardInterrupt:
            print("\n\n🛑 หยุด Bot")
            self.print_status()
            self.save_state()
            
            roi = ((self.balance - INITIAL_BALANCE) / INITIAL_BALANCE) * 100
            print("\n📊 สรุป:")
            print(f"   💰 เริ่ม: ${INITIAL_BALANCE}")
            print(f"   💵 จบ: ${self.balance:.4f}")
            print(f"   📈 ROI: {roi:+.2f}%")


if __name__ == "__main__":
    bot = PaperTradeBot()
    bot.run()
