#!/usr/bin/env python3
"""
📊 BACKTEST: V1 vs V2 Comparison
================================
เปรียบเทียบผลลัพธ์ระหว่าง:
- V1: SL 1.5%, TP 2.0%, ADX>=30, รวม Meme Coins
- V2: SL 2.5%, TP 3.5%, ADX>=35, ไม่มี Meme Coins, Dynamic Sizing
"""

import ccxt
import pandas as pd
import pandas_ta as ta
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

# V1 Settings (Original)
V1_CONFIG = {
    'name': 'V1 (Original)',
    'sl_pct': 0.015,  # 1.5%
    'tp_pct': 0.020,  # 2.0%
    'adx_threshold': 30,
    'coins': [
        'DOGE/USDT', 'ETC/USDT', 'INJ/USDT', 'NEAR/USDT', 'RUNE/USDT',
        'SOL/USDT', 'AVAX/USDT', 'FIL/USDT', 'ARB/USDT', 'OP/USDT',
        'SEI/USDT', 'SUI/USDT', '1000PEPE/USDT', 'WIF/USDT', 'ORDI/USDT',
        'STX/USDT', 'IMX/USDT', 'FTM/USDT', 'AAVE/USDT', 'GRT/USDT',
        'BTC/USDT', 'ETH/USDT', 'XRP/USDT', 'BNB/USDT', 'ADA/USDT',
        'LINK/USDT', 'DOT/USDT', 'POL/USDT', 'LTC/USDT', 'UNI/USDT',
    ]
}

# V2 Settings (Improved)
V2_CONFIG = {
    'name': 'V2 (Improved)',
    'sl_pct': 0.025,  # 2.5%
    'tp_pct': 0.035,  # 3.5%
    'adx_threshold': 35,
    'coins': [
        'BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'XRP/USDT', 'SOL/USDT',
        'ADA/USDT', 'AVAX/USDT', 'DOT/USDT', 'NEAR/USDT', 'SUI/USDT',
        'ARB/USDT', 'OP/USDT', 'POL/USDT', 'LINK/USDT', 'UNI/USDT',
        'LTC/USDT', 'ETC/USDT', 'FIL/USDT', 'AAVE/USDT', 'INJ/USDT',
        'RUNE/USDT', 'SEI/USDT', 'STX/USDT', 'IMX/USDT', 'FTM/USDT', 'GRT/USDT',
    ]
    # ลบ: DOGE, ORDI, WIF, 1000PEPE
}

# Common Settings
INITIAL_BALANCE = 4.50
LEVERAGE = 20
TIMEFRAME = '5m'
BACKTEST_DAYS = 7  # 7 วันย้อนหลัง

# ═══════════════════════════════════════════════════════════════════════════════
# BACKTESTER CLASS
# ═══════════════════════════════════════════════════════════════════════════════

class Backtester:
    def __init__(self, config: dict):
        self.config = config
        self.exchange = ccxt.binanceusdm({
            'enableRateLimit': True,
            'options': {'defaultType': 'future'}
        })
        
        self.balance = INITIAL_BALANCE
        self.trades = []
        self.wins = 0
        self.losses = 0
        
    def get_confidence(self, adx: float, rsi: float, trend_aligned: bool, macd_aligned: bool) -> int:
        """คำนวณ Confidence Score"""
        confidence = 50
        
        if adx > 25:
            confidence += min(30, (adx - 25) * 1.5)
        
        if 40 < rsi < 60:
            confidence += 5
        elif trend_aligned:
            confidence += 10
            
        if macd_aligned:
            confidence += 10
            
        return min(95, int(confidence))
    
    def get_position_multiplier(self, confidence: int) -> float:
        """Dynamic Position Sizing (V2 only)"""
        if 'V2' in self.config['name']:
            if confidence >= 85:
                return 1.5
            elif confidence >= 70:
                return 1.0
            else:
                return 0.5
        return 1.0  # V1 always 1x
    
    def analyze_candle(self, df: pd.DataFrame, idx: int) -> dict:
        """วิเคราะห์สัญญาณที่แท่งเทียนนั้น"""
        if idx < 50:
            return None
            
        # Get values at index
        price = df['close'].iloc[idx]
        rsi = df['rsi'].iloc[idx]
        adx = df['adx'].iloc[idx]
        macd_hist = df['macd_hist'].iloc[idx]
        
        ema_fast = df['ema_3'].iloc[idx]
        ema_slow = df['ema_8'].iloc[idx]
        ema_trend = df['ema_20'].iloc[idx]
        
        if pd.isna(adx) or pd.isna(rsi):
            return None
            
        trend_up = ema_fast > ema_slow > ema_trend
        trend_down = ema_fast < ema_slow < ema_trend
        
        adx_threshold = self.config['adx_threshold']
        
        # LONG Signal
        if trend_up and adx >= adx_threshold and ema_fast > ema_slow and macd_hist > 0:
            if 40 < rsi < 70:
                confidence = self.get_confidence(adx, rsi, True, True)
                return {
                    'signal': 'LONG',
                    'price': price,
                    'confidence': confidence,
                    'adx': adx,
                    'rsi': rsi
                }
        
        # SHORT Signal
        if trend_down and adx >= adx_threshold and ema_fast < ema_slow and macd_hist < 0:
            if 30 < rsi < 60:
                confidence = self.get_confidence(adx, rsi, True, True)
                return {
                    'signal': 'SHORT',
                    'price': price,
                    'confidence': confidence,
                    'adx': adx,
                    'rsi': rsi
                }
        
        return None
    
    def simulate_trade(self, df: pd.DataFrame, entry_idx: int, signal: dict) -> dict:
        """จำลองการเทรด - ดูว่าถึง TP หรือ SL ก่อน"""
        entry_price = signal['price']
        side = signal['signal']
        confidence = signal['confidence']
        
        sl_pct = self.config['sl_pct']
        tp_pct = self.config['tp_pct']
        
        if side == 'LONG':
            sl = entry_price * (1 - sl_pct)
            tp = entry_price * (1 + tp_pct)
        else:
            sl = entry_price * (1 + sl_pct)
            tp = entry_price * (1 - tp_pct)
        
        # Scan forward to find exit
        for i in range(entry_idx + 1, len(df)):
            high = df['high'].iloc[i]
            low = df['low'].iloc[i]
            
            if side == 'LONG':
                if low <= sl:
                    return {'result': 'SL', 'pnl_pct': -sl_pct * LEVERAGE * 100, 'bars': i - entry_idx, 'confidence': confidence}
                if high >= tp:
                    return {'result': 'TP', 'pnl_pct': tp_pct * LEVERAGE * 100, 'bars': i - entry_idx, 'confidence': confidence}
            else:
                if high >= sl:
                    return {'result': 'SL', 'pnl_pct': -sl_pct * LEVERAGE * 100, 'bars': i - entry_idx, 'confidence': confidence}
                if low <= tp:
                    return {'result': 'TP', 'pnl_pct': tp_pct * LEVERAGE * 100, 'bars': i - entry_idx, 'confidence': confidence}
        
        # Still open
        return None
    
    def backtest_symbol(self, symbol: str) -> list:
        """Backtest 1 symbol"""
        try:
            # Fetch data
            ohlcv = self.exchange.fetch_ohlcv(symbol, TIMEFRAME, limit=1000)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            # Calculate indicators
            df['ema_3'] = ta.ema(df['close'], length=3)
            df['ema_8'] = ta.ema(df['close'], length=8)
            df['ema_20'] = ta.ema(df['close'], length=20)
            df['rsi'] = ta.rsi(df['close'], length=14)
            
            macd = ta.macd(df['close'])
            if macd is not None:
                df['macd_hist'] = macd['MACDh_12_26_9']
            else:
                df['macd_hist'] = 0
                
            adx_data = ta.adx(df['high'], df['low'], df['close'], length=14)
            if adx_data is not None:
                df['adx'] = adx_data['ADX_14']
            else:
                df['adx'] = 0
            
            trades = []
            last_trade_idx = 0
            
            # Scan for signals
            for i in range(50, len(df) - 20):  # Leave room for trade to complete
                if i < last_trade_idx + 5:  # Min 5 bars between trades
                    continue
                    
                signal = self.analyze_candle(df, i)
                
                if signal:
                    result = self.simulate_trade(df, i, signal)
                    
                    if result:
                        result['symbol'] = symbol
                        result['side'] = signal['signal']
                        result['entry_price'] = signal['price']
                        result['adx'] = signal['adx']
                        result['rsi'] = signal['rsi']
                        result['timestamp'] = df['timestamp'].iloc[i]
                        trades.append(result)
                        last_trade_idx = i + result['bars']
            
            return trades
            
        except Exception as e:
            print(f"   ❌ Error {symbol}: {e}")
            return []
    
    def run_backtest(self) -> dict:
        """รัน Backtest ทั้งหมด"""
        print(f"\n{'='*60}")
        print(f"📊 BACKTEST: {self.config['name']}")
        print(f"{'='*60}")
        print(f"⚙️ SL: {self.config['sl_pct']*100:.1f}% | TP: {self.config['tp_pct']*100:.1f}%")
        print(f"📈 ADX >= {self.config['adx_threshold']}")
        print(f"🪙 Coins: {len(self.config['coins'])}")
        print(f"{'='*60}\n")
        
        all_trades = []
        
        for i, symbol in enumerate(self.config['coins']):
            print(f"\r   🔍 Scanning {symbol} ({i+1}/{len(self.config['coins'])})...", end="", flush=True)
            trades = self.backtest_symbol(symbol)
            all_trades.extend(trades)
        
        print(f"\r   ✅ Scanned {len(self.config['coins'])} coins                    ")
        
        # Calculate results
        if not all_trades:
            return {
                'config': self.config['name'],
                'total_trades': 0,
                'wins': 0,
                'losses': 0,
                'win_rate': 0,
                'total_pnl_pct': 0,
                'avg_pnl': 0,
                'final_balance': INITIAL_BALANCE,
                'roi': 0
            }
        
        wins = len([t for t in all_trades if t['result'] == 'TP'])
        losses = len([t for t in all_trades if t['result'] == 'SL'])
        total = len(all_trades)
        
        win_rate = wins / total * 100 if total > 0 else 0
        
        # Calculate final balance with position sizing
        balance = INITIAL_BALANCE
        for trade in all_trades:
            multiplier = self.get_position_multiplier(trade['confidence'])
            position_size = (balance / 3) * multiplier  # Max 3 positions
            pnl = position_size * (trade['pnl_pct'] / 100)
            balance += pnl
        
        total_pnl_pct = sum(t['pnl_pct'] for t in all_trades)
        avg_pnl = total_pnl_pct / total if total > 0 else 0
        roi = (balance - INITIAL_BALANCE) / INITIAL_BALANCE * 100
        
        # Stats by confidence (V2 feature)
        conf_stats = {'LOW': [], 'MEDIUM': [], 'HIGH': []}
        for t in all_trades:
            conf = t['confidence']
            if conf >= 85:
                conf_stats['HIGH'].append(t)
            elif conf >= 70:
                conf_stats['MEDIUM'].append(t)
            else:
                conf_stats['LOW'].append(t)
        
        return {
            'config': self.config['name'],
            'total_trades': total,
            'wins': wins,
            'losses': losses,
            'win_rate': win_rate,
            'total_pnl_pct': total_pnl_pct,
            'avg_pnl': avg_pnl,
            'final_balance': balance,
            'roi': roi,
            'trades': all_trades,
            'conf_stats': conf_stats
        }

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    print("""
╔═══════════════════════════════════════════════════════════════════╗
║  📊 BACKTEST COMPARISON: V1 vs V2                                ║
║  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ║
║  V1: SL 1.5%, TP 2.0%, ADX>=30, With Meme Coins                  ║
║  V2: SL 2.5%, TP 3.5%, ADX>=35, No Meme, Dynamic Sizing          ║
╚═══════════════════════════════════════════════════════════════════╝
    """)
    
    # Run V1 Backtest
    bt_v1 = Backtester(V1_CONFIG)
    results_v1 = bt_v1.run_backtest()
    
    # Run V2 Backtest
    bt_v2 = Backtester(V2_CONFIG)
    results_v2 = bt_v2.run_backtest()
    
    # Print Comparison
    print("\n" + "="*70)
    print("📊 BACKTEST RESULTS COMPARISON")
    print("="*70)
    
    print(f"\n{'Metric':<25} {'V1 (Original)':<20} {'V2 (Improved)':<20}")
    print("-"*65)
    print(f"{'Total Trades':<25} {results_v1['total_trades']:<20} {results_v2['total_trades']:<20}")
    print(f"{'Wins':<25} {results_v1['wins']:<20} {results_v2['wins']:<20}")
    print(f"{'Losses':<25} {results_v1['losses']:<20} {results_v2['losses']:<20}")
    print(f"{'Win Rate':<25} {results_v1['win_rate']:.1f}%{'':<15} {results_v2['win_rate']:.1f}%")
    print(f"{'Avg PnL/Trade':<25} {results_v1['avg_pnl']:+.1f}%{'':<14} {results_v2['avg_pnl']:+.1f}%")
    print(f"{'Final Balance':<25} ${results_v1['final_balance']:.2f}{'':<14} ${results_v2['final_balance']:.2f}")
    print(f"{'ROI':<25} {results_v1['roi']:+.1f}%{'':<15} {results_v2['roi']:+.1f}%")
    
    # Highlight winner
    print("\n" + "="*70)
    
    v1_score = results_v1['roi']
    v2_score = results_v2['roi']
    
    if v2_score > v1_score:
        diff = v2_score - v1_score
        print(f"🏆 V2 ดีกว่า V1 อยู่ {diff:+.1f}% ROI!")
        print(f"   💰 V2: ${results_v2['final_balance']:.2f} vs V1: ${results_v1['final_balance']:.2f}")
    elif v1_score > v2_score:
        diff = v1_score - v2_score
        print(f"⚠️ V1 ยังดีกว่า V2 อยู่ {diff:.1f}% ROI")
        print(f"   💰 V1: ${results_v1['final_balance']:.2f} vs V2: ${results_v2['final_balance']:.2f}")
    else:
        print("🤝 V1 และ V2 ผลลัพธ์ใกล้เคียงกัน")
    
    # V2 Confidence breakdown
    if results_v2['conf_stats']:
        print("\n" + "="*70)
        print("📊 V2 - Stats by Confidence Level")
        print("="*70)
        
        for level in ['LOW', 'MEDIUM', 'HIGH']:
            trades = results_v2['conf_stats'][level]
            if trades:
                wins = len([t for t in trades if t['result'] == 'TP'])
                total = len(trades)
                wr = wins / total * 100 if total > 0 else 0
                avg_pnl = sum(t['pnl_pct'] for t in trades) / total
                
                emoji = "🔥" if level == "HIGH" else "⚡" if level == "MEDIUM" else "⚠️"
                print(f"   {emoji} {level}: {total} trades, {wr:.0f}% WR, Avg: {avg_pnl:+.1f}%")
    
    # Meme Coin Analysis
    print("\n" + "="*70)
    print("🎰 Meme Coins Analysis (V1 only)")
    print("="*70)
    
    meme_coins = ['DOGE/USDT', 'ORDI/USDT', 'WIF/USDT', '1000PEPE/USDT']
    meme_trades = [t for t in results_v1.get('trades', []) if t['symbol'] in meme_coins]
    
    if meme_trades:
        meme_wins = len([t for t in meme_trades if t['result'] == 'TP'])
        meme_total = len(meme_trades)
        meme_wr = meme_wins / meme_total * 100 if meme_total > 0 else 0
        meme_pnl = sum(t['pnl_pct'] for t in meme_trades)
        
        print(f"   📊 Meme Coin Trades: {meme_total}")
        print(f"   🎯 Win Rate: {meme_wr:.0f}%")
        print(f"   💰 Total PnL: {meme_pnl:+.1f}%")
        
        if meme_pnl < 0:
            print(f"   ⚠️ Meme coins ทำให้ขาดทุน {meme_pnl:.1f}% - V2 ตัดออกถูกแล้ว!")
        else:
            print(f"   ✅ Meme coins กำไร {meme_pnl:.1f}%")
    else:
        print("   ไม่มี trade จาก Meme coins ในช่วงนี้")
    
    print("\n" + "="*70)
    print("✅ Backtest เสร็จสิ้น!")
    print("="*70 + "\n")

if __name__ == "__main__":
    main()
