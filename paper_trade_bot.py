#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                     📝 PAPER TRADE BOT V3                                    ║
║             100% Paper Trade - No API Key Required for Orders                ║
║             Long + Short | Top 30 Coins | Real-time Simulation               ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import ccxt
import pandas as pd
import pandas_ta as ta
import os
import time
import json
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
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

# Trading Settings
INITIAL_BALANCE = 4.50      # Starting balance
LEVERAGE = 50               # 50x leverage (simulated)
SL_PCT = 0.012              # 1.2% Stop Loss
TP_PCT = 0.050              # 5.0% Take Profit
TIMEFRAME = '5m'            # 5 minute candles
SCAN_INTERVAL = 30          # Scan every 30 seconds
MAX_POSITIONS = 3           # Max simultaneous positions

# ═══════════════════════════════════════════════════════════════════════════════
# PAPER TRADING ENGINE - NO REAL ORDERS
# ═══════════════════════════════════════════════════════════════════════════════

class PaperTradeBot:
    def __init__(self):
        # Use public API only (no API key needed for price data)
        self.exchange = ccxt.binanceusdm({
            'enableRateLimit': True,
            'options': {'defaultType': 'future'}
        })
        
        self.balance = INITIAL_BALANCE
        self.positions = {}  # {symbol: position_data}
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
        
        print("🔄 Loading markets (public API)...")
        try:
            self.exchange.load_markets()
            print(f"✅ Loaded {len(self.exchange.markets)} markets")
        except Exception as e:
            print(f"⚠️ Warning: {e}")
            print("   Using cached market data...")
        
    def get_signal(self, symbol: str) -> dict:
        """Analyze coin and return signal (LONG/SHORT/NONE)"""
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
    
    def get_current_price(self, symbol: str) -> float:
        """Get current price from public API"""
        try:
            ticker = self.exchange.fetch_ticker(symbol)
            return ticker['last']
        except:
            return 0.0
    
    def open_position(self, symbol: str, side: str, price: float, reason: str):
        """Open a PAPER trade position (no real order)"""
        if symbol in self.positions:
            return False
        
        if len(self.positions) >= MAX_POSITIONS:
            print(f"  ⚠️ Max positions ({MAX_POSITIONS}) reached")
            return False
        
        # Calculate position size
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
        print(f"\n{emoji} [PAPER] OPENED {side} on {symbol}")
        print(f"   📍 Entry: ${price:,.4f}")
        print(f"   🛡️ SL: ${sl:,.4f} ({'-' if side=='LONG' else '+'}{SL_PCT*100}%)")
        print(f"   🎯 TP: ${tp:,.4f} ({'+' if side=='LONG' else '-'}{TP_PCT*100}%)")
        print(f"   💰 Size: ${position_value:.2f} x {LEVERAGE}x = ${position_value*LEVERAGE:.2f}")
        print(f"   📝 Reason: {reason}")
        
        return True
    
    def check_positions(self):
        """Check all open positions for SL/TP hits"""
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
                else:  # SHORT
                    hit_sl = current_price >= pos['sl']
                    hit_tp = current_price <= pos['tp']
                
                if hit_sl or hit_tp:
                    # Calculate PnL
                    if pos['side'] == 'LONG':
                        pnl_pct = (current_price - pos['entry_price']) / pos['entry_price']
                    else:
                        pnl_pct = (pos['entry_price'] - current_price) / pos['entry_price']
                    
                    pnl_leveraged = pnl_pct * LEVERAGE
                    pnl_usd = pos['size'] * pnl_leveraged
                    
                    exit_reason = "🎯 TP HIT" if hit_tp else "🛡️ SL HIT"
                    
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
                        'exit': current_price,
                        'pnl_usd': round(pnl_usd, 4),
                        'pnl_pct': round(pnl_leveraged * 100, 2),
                        'exit_reason': 'TP' if hit_tp else 'SL',
                        'open_time': pos['open_time'],
                        'close_time': datetime.now().isoformat()
                    })
                    
                    # Print result
                    emoji = "✅" if pnl_usd > 0 else "❌"
                    print(f"\n{emoji} [PAPER] CLOSED {pos['side']} on {symbol}")
                    print(f"   📍 Entry: ${pos['entry_price']:,.4f} → Exit: ${current_price:,.4f}")
                    print(f"   💰 PnL: {'+' if pnl_usd > 0 else ''}{pnl_usd:.4f} USD ({pnl_leveraged*100:+.1f}%)")
                    print(f"   📝 Exit: {exit_reason}")
                    print(f"   💵 New Balance: ${self.balance:.4f}")
                    
                    closed.append(symbol)
                else:
                    # Show unrealized PnL
                    if pos['side'] == 'LONG':
                        unrealized_pnl_pct = (current_price - pos['entry_price']) / pos['entry_price'] * LEVERAGE * 100
                    else:
                        unrealized_pnl_pct = (pos['entry_price'] - current_price) / pos['entry_price'] * LEVERAGE * 100
                    
            except Exception as e:
                print(f"  ⚠️ Error checking {symbol}: {e}")
        
        for symbol in closed:
            del self.positions[symbol]
    
    def print_status(self):
        """Print current status"""
        win_rate = (self.stats['wins'] / self.stats['total_trades'] * 100) if self.stats['total_trades'] > 0 else 0
        roi = ((self.balance - INITIAL_BALANCE) / INITIAL_BALANCE) * 100
        
        print(f"\n{'═'*75}")
        print(f"📊 PAPER TRADE STATUS - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'═'*75}")
        print(f"💰 Balance: ${self.balance:.4f} | Starting: ${INITIAL_BALANCE} | ROI: {roi:+.2f}%")
        print(f"📈 Trades: {self.stats['total_trades']} | ✅ {self.stats['wins']}W / ❌ {self.stats['losses']}L | Win Rate: {win_rate:.1f}%")
        print(f"   🟢 Long: {self.stats['long_wins']}W/{self.stats['long_losses']}L | 🔴 Short: {self.stats['short_wins']}W/{self.stats['short_losses']}L")
        print(f"💵 Total PnL: ${self.stats['total_pnl']:+.4f}")
        if self.stats['best_trade'] > 0:
            print(f"🏆 Best: ${self.stats['best_trade']:+.4f} | 💔 Worst: ${self.stats['worst_trade']:.4f}")
        
        if self.positions:
            print(f"\n📊 Open Positions ({len(self.positions)}/{MAX_POSITIONS}):")
            for symbol, pos in self.positions.items():
                current = self.get_current_price(symbol)
                if current > 0:
                    if pos['side'] == 'LONG':
                        pnl_pct = (current - pos['entry_price']) / pos['entry_price'] * LEVERAGE * 100
                        distance_to_sl = (current - pos['sl']) / current * 100
                        distance_to_tp = (pos['tp'] - current) / current * 100
                    else:
                        pnl_pct = (pos['entry_price'] - current) / pos['entry_price'] * LEVERAGE * 100
                        distance_to_sl = (pos['sl'] - current) / current * 100
                        distance_to_tp = (current - pos['tp']) / current * 100
                    
                    emoji = "📈" if pnl_pct > 0 else "📉"
                    side_emoji = "🟢" if pos['side'] == 'LONG' else "🔴"
                    print(f"   {side_emoji} {pos['side']} {symbol}")
                    print(f"      Entry: ${pos['entry_price']:.4f} | Now: ${current:.4f} | {emoji} PnL: {pnl_pct:+.1f}%")
                    print(f"      SL: ${pos['sl']:.4f} ({distance_to_sl:.1f}% away) | TP: ${pos['tp']:.4f} ({distance_to_tp:.1f}% away)")
        else:
            print(f"\n⏳ No open positions - scanning for signals...")
        
        # Progress to goal
        goal = 50.0
        progress = (self.balance / goal) * 100
        print(f"\n🎯 Goal Progress: ${self.balance:.2f} / ${goal:.2f} ({progress:.1f}%)")
        print(f"   {'█' * int(progress/5)}{'░' * (20 - int(progress/5))} {progress:.0f}%")
        
        print(f"{'═'*75}\n")
    
    def scan_and_trade(self):
        """Scan all coins and trade on signals"""
        print(f"\n🔍 Scanning {len(COINS)} coins for signals...")
        
        signals_found = []
        
        for symbol in COINS:
            # Skip if already in position
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
            
            time.sleep(0.1)  # Rate limit
        
        # Sort by confidence
        signals_found.sort(key=lambda x: x['confidence'], reverse=True)
        
        if signals_found:
            long_signals = len([s for s in signals_found if s['signal'] == 'LONG'])
            short_signals = len([s for s in signals_found if s['signal'] == 'SHORT'])
            print(f"\n📡 Found {len(signals_found)} signals (🟢 {long_signals} LONG | 🔴 {short_signals} SHORT)")
            
            for sig in signals_found[:5]:  # Show top 5
                emoji = "🟢" if sig['signal'] == "LONG" else "🔴"
                print(f"   {emoji} {sig['signal']} {sig['symbol']}: ${sig['price']:.4f} | Conf: {sig['confidence']}% | {sig['reason']}")
            
            # Open best signals
            for sig in signals_found:
                if len(self.positions) >= MAX_POSITIONS:
                    break
                self.open_position(sig['symbol'], sig['signal'], sig['price'], sig['reason'])
        else:
            print("   ⏳ No signals found this scan")
    
    def save_state(self):
        """Save current state to file"""
        state = {
            'balance': self.balance,
            'initial_balance': INITIAL_BALANCE,
            'stats': self.stats,
            'positions': self.positions,
            'trades': self.trade_history,
            'last_update': datetime.now().isoformat()
        }
        
        with open('paper_trades.json', 'w') as f:
            json.dump(state, f, indent=2)
    
    def load_state(self):
        """Load previous state if exists"""
        try:
            if os.path.exists('paper_trades.json'):
                with open('paper_trades.json', 'r') as f:
                    state = json.load(f)
                
                self.balance = state.get('balance', INITIAL_BALANCE)
                self.stats = state.get('stats', self.stats)
                self.positions = state.get('positions', {})
                self.trade_history = state.get('trades', [])
                
                print(f"📂 Loaded previous state: ${self.balance:.4f} | {self.stats['total_trades']} trades")
                return True
        except Exception as e:
            print(f"⚠️ Could not load state: {e}")
        return False
    
    def run(self):
        """Main trading loop"""
        print(f"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                     📝 PAPER TRADE BOT V3                                    ║
║                  100% Simulation - No Real Orders                            ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  🎯 Goal: $4.50 → $50.00 (+1,011% ROI)                                       ║
║  📊 Coins: {len(COINS)} coins (Top performers + Major)                              ║
║  📈 Direction: LONG + SHORT (Both ways)                                      ║
║  ⚡ Leverage: {LEVERAGE}x | 🛡️ SL: {SL_PCT*100}% | 🎯 TP: {TP_PCT*100}%                                ║
║  💰 Starting Balance: ${INITIAL_BALANCE}                                            ║
║  ⏱️ Scan Interval: {SCAN_INTERVAL}s | 📊 Max Positions: {MAX_POSITIONS}                         ║
╚══════════════════════════════════════════════════════════════════════════════╝
        """)
        
        # Try to load previous state
        self.load_state()
        
        iteration = 0
        
        try:
            while True:
                iteration += 1
                
                # Check open positions first
                if self.positions:
                    self.check_positions()
                
                # Scan for new signals
                self.scan_and_trade()
                
                # Print status every 3 iterations
                if iteration % 3 == 0:
                    self.print_status()
                
                # Save state
                self.save_state()
                
                # Check if goal reached
                if self.balance >= 50.0:
                    print("\n" + "🎉" * 20)
                    print("🏆 GOAL REACHED! $4.50 → $50.00!")
                    print("🎉" * 20 + "\n")
                    self.print_status()
                    break
                
                # Check if blown
                if self.balance < 0.50:
                    print("\n" + "💀" * 20)
                    print("❌ ACCOUNT BLOWN - Balance too low")
                    print("💀" * 20 + "\n")
                    self.print_status()
                    break
                
                print(f"⏳ Next scan in {SCAN_INTERVAL}s... (Ctrl+C to stop)")
                time.sleep(SCAN_INTERVAL)
                
        except KeyboardInterrupt:
            print("\n\n🛑 Bot stopped by user")
            self.print_status()
            self.save_state()
            
            # Final summary
            roi = ((self.balance - INITIAL_BALANCE) / INITIAL_BALANCE) * 100
            print("\n📊 FINAL SUMMARY:")
            print(f"   💰 Starting: ${INITIAL_BALANCE}")
            print(f"   💵 Ending: ${self.balance:.4f}")
            print(f"   📈 ROI: {roi:+.2f}%")
            print(f"   📊 Total Trades: {self.stats['total_trades']}")
            print(f"   ✅ Wins: {self.stats['wins']} | ❌ Losses: {self.stats['losses']}")
            
            if self.trade_history:
                print("\n📝 Trade History saved to: paper_trades.json")


if __name__ == "__main__":
    bot = PaperTradeBot()
    bot.run()
