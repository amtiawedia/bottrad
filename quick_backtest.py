#!/usr/bin/env python3
"""Quick Backtest Script"""
import ccxt
import pandas as pd
import pandas_ta as ta
import warnings
warnings.filterwarnings('ignore')

exchange = ccxt.binanceusdm({'enableRateLimit': True})
exchange.load_markets()

# Get symbols
COINS = []
for sym in exchange.symbols:
    if sym.endswith(':USDT') and '/USDT' in sym:
        base = sym.split('/')[0]
        if base in ['BTC', 'ETH', 'SOL', 'XRP', 'LINK', 'LTC', 'AVAX', 'DOT', 'ADA', 'OP', 'ARB', 'INJ', 'SUI', 'NEAR', 'BNB']:
            COINS.append(sym)

print(f'Testing {len(COINS)} coins: {COINS[:5]}...')

LEVERAGE = 20
INITIAL_BALANCE = 4.50

def backtest(name, sl_pct, tp_pct, adx_thresh):
    wins, losses = 0, 0
    balance = INITIAL_BALANCE
    all_trades = []
    
    for symbol in COINS:
        try:
            ohlcv = exchange.fetch_ohlcv(symbol, '5m', limit=1500)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            
            df['ema_3'] = ta.ema(df['close'], length=3)
            df['ema_8'] = ta.ema(df['close'], length=8)
            df['ema_20'] = ta.ema(df['close'], length=20)
            df['rsi'] = ta.rsi(df['close'], length=14)
            macd = ta.macd(df['close'])
            df['macd_hist'] = macd['MACDh_12_26_9'] if macd is not None else 0
            adx_data = ta.adx(df['high'], df['low'], df['close'], length=14)
            df['adx'] = adx_data['ADX_14'] if adx_data is not None else 0
            
            last_idx = 0
            
            for i in range(50, len(df)-30):
                if i < last_idx + 8:
                    continue
                
                adx = df['adx'].iloc[i]
                rsi = df['rsi'].iloc[i]
                macd_hist = df['macd_hist'].iloc[i]
                ema_fast = df['ema_3'].iloc[i]
                ema_slow = df['ema_8'].iloc[i]
                ema_trend = df['ema_20'].iloc[i]
                
                if pd.isna(adx):
                    continue
                
                trend_up = ema_fast > ema_slow > ema_trend
                trend_down = ema_fast < ema_slow < ema_trend
                
                signal = None
                if trend_up and adx >= adx_thresh and macd_hist > 0 and 40 < rsi < 70:
                    signal = 'LONG'
                elif trend_down and adx >= adx_thresh and macd_hist < 0 and 30 < rsi < 60:
                    signal = 'SHORT'
                
                if signal:
                    entry = df['close'].iloc[i]
                    sl = entry * (1 - sl_pct) if signal == 'LONG' else entry * (1 + sl_pct)
                    tp = entry * (1 + tp_pct) if signal == 'LONG' else entry * (1 - tp_pct)
                    
                    for j in range(i+1, min(i+150, len(df))):
                        high = df['high'].iloc[j]
                        low = df['low'].iloc[j]
                        
                        hit = None
                        if signal == 'LONG':
                            if low <= sl:
                                hit = 'SL'
                            elif high >= tp:
                                hit = 'TP'
                        else:
                            if high >= sl:
                                hit = 'SL'
                            elif low <= tp:
                                hit = 'TP'
                        
                        if hit:
                            if hit == 'TP':
                                wins += 1
                                pnl_pct = tp_pct * LEVERAGE * 100
                            else:
                                losses += 1
                                pnl_pct = -sl_pct * LEVERAGE * 100
                            
                            pos_size = balance / 3
                            balance += pos_size * (pnl_pct / 100)
                            all_trades.append({
                                'symbol': symbol,
                                'signal': signal,
                                'result': hit,
                                'pnl_pct': pnl_pct
                            })
                            last_idx = j
                            break
                            
        except Exception as e:
            pass
    
    total = wins + losses
    wr = wins / total * 100 if total > 0 else 0
    roi = (balance - INITIAL_BALANCE) / INITIAL_BALANCE * 100
    
    return {
        'name': name,
        'trades': total,
        'wins': wins,
        'losses': losses,
        'wr': wr,
        'roi': roi,
        'balance': balance,
        'all_trades': all_trades
    }


print()
print('=' * 70)
print('📊 BACKTEST COMPARISON (5 days data)')
print('=' * 70)

# Test different configs
configs = [
    ('V1 (SL 1.5%, TP 2.0%)', 0.015, 0.020, 30),
    ('V3 (SL 1.8%, TP 2.5%)', 0.018, 0.025, 30),
    ('V4 (SL 1.2%, TP 1.8%)', 0.012, 0.018, 30),
    ('V5 (SL 1.0%, TP 1.5%)', 0.010, 0.015, 30),
    ('V6 (ADX 25)', 0.015, 0.020, 25),
]

results = []
for name, sl, tp, adx in configs:
    print(f'Testing {name}...', end=' ', flush=True)
    r = backtest(name, sl, tp, adx)
    results.append(r)
    print(f'{r["trades"]} trades, {r["wr"]:.1f}% WR')

print()
print(f'{"Config":<25} {"Trades":<8} {"Win":<6} {"Loss":<6} {"WR":<8} {"ROI":<10}')
print('-' * 70)
for r in results:
    print(f'{r["name"]:<25} {r["trades"]:<8} {r["wins"]:<6} {r["losses"]:<6} {r["wr"]:.1f}%    {r["roi"]:+.1f}%')

print()
print('=' * 70)
best = max(results, key=lambda x: x['roi'])
print(f'🏆 WINNER: {best["name"]}')
print(f'   📊 {best["trades"]} trades, {best["wr"]:.1f}% Win Rate')
print(f'   💰 Balance: ${best["balance"]:.2f} (ROI: {best["roi"]:+.1f}%)')
print('=' * 70)
