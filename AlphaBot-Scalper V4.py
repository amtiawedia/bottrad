#!/usr/bin/env python3
"""
Scalping Bot - Optimized for Profit
====================================
- Timeframe: 5m (ลด noise และค่าธรรมเนียม)
- Strategy: Short-biased with strict filters
- Risk Management: Tight SL, moderate TP, trailing stop
- Session Filter: เทรดเฉพาะช่วง high liquidity
- Walk-forward Gating: หยุดเทรดถ้าระบบไม่ดี
"""

import ccxt
import pandas as pd
import pandas_ta as ta
import time
from datetime import datetime, timedelta
import json
import os

# === Configuration ===
API_KEY = os.environ.get('BINANCE_API_KEY', '')
SECRET_KEY = os.environ.get('BINANCE_SECRET_KEY', '')

SYMBOL = 'BTC/USDT'
TIMEFRAME = '15m'

# Risk Management - 3.6:1 RR Ratio
STOP_LOSS_PERCENT = 0.0025      # 0.25% SL
TAKE_PROFIT_PERCENT = 0.009     # 0.9% TP (3.6:1 RR)
TRAILING_STOP_PERCENT = 0.0015  # 0.15% trailing
BALANCE_PERCENT = 0.10          # 10% per trade
FEE_PERCENT = 0.0002            # 0.02% fee

# Indicators - 5m EMA Crossover
RSI_PERIOD = 14
RSI_OVERSOLD = 30
RSI_OVERBOUGHT = 70
EMA_FAST = 5
EMA_SLOW = 13
BB_PERIOD = 20
BB_STD = 2
ADX_PERIOD = 14
ADX_THRESHOLD = 20
VOLUME_MULT = 1.0

# Session Filter (UTC)
ACTIVE_HOURS = list(range(0, 24))  # 24h

# Signal Thresholds
MIN_SCORE = 5
ALLOW_LONGS = False  # Short-only
ALLOW_SHORTS = True

# Walk-forward Gating
ENABLE_GATING = True
GATING_LOOKBACK_TRADES = 10     # ดูย้อนหลัง 10 เทรด
GATING_MIN_WINRATE = 0.35       # ต้อง win rate > 35%
GATING_MIN_PF = 0.8             # profit factor > 0.8

# State
trade_history = []
current_position = None
is_gated = False  # ถ้า True = หยุดเทรด

# Exchange setup
exchange = ccxt.binance({
    'apiKey': API_KEY,
    'secret': SECRET_KEY,
    'enableRateLimit': True,
    'options': {'adjustForTimeDifference': True}
})


def log(msg: str):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}")


def fetch_data(symbol: str, timeframe: str, limit: int = 200) -> pd.DataFrame:
    """ดึงข้อมูลแท่งเทียน"""
    try:
        bars = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        return df
    except Exception as e:
        log(f"❌ Error fetching data: {e}")
        return pd.DataFrame()


def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """คำนวณ indicators ทั้งหมด"""
    if df.empty or len(df) < 50:
        return df

    # RSI
    df.ta.rsi(close='close', length=RSI_PERIOD, append=True)

    # EMA
    df.ta.ema(close='close', length=EMA_FAST, append=True)
    df.ta.ema(close='close', length=EMA_SLOW, append=True)

    # MACD
    df.ta.macd(close='close', fast=12, slow=26, signal=9, append=True)

    # Bollinger Bands
    df.ta.bbands(close='close', length=BB_PERIOD, std=BB_STD, append=True)

    # ADX
    df.ta.adx(length=ADX_PERIOD, append=True)

    # Volume SMA
    df.ta.sma(close='volume', length=20, append=True)
    df.rename(columns={'SMA_20': 'Volume_SMA'}, inplace=True)

    return df.dropna()


def check_session() -> bool:
    """ตรวจว่าอยู่ในช่วงเทรดหรือไม่"""
    hour = datetime.utcnow().hour
    return hour in ACTIVE_HOURS


def check_gating() -> bool:
    """ตรวจ walk-forward gating"""
    global is_gated

    if not ENABLE_GATING or len(trade_history) < GATING_LOOKBACK_TRADES:
        is_gated = False
        return True

    recent = trade_history[-GATING_LOOKBACK_TRADES:]
    wins = sum(1 for t in recent if t['pnl'] > 0)
    win_rate = wins / len(recent)

    total_profit = sum(t['pnl'] for t in recent if t['pnl'] > 0)
    total_loss = abs(sum(t['pnl'] for t in recent if t['pnl'] <= 0))
    pf = total_profit / total_loss if total_loss > 0 else 999

    if win_rate < GATING_MIN_WINRATE or pf < GATING_MIN_PF:
        is_gated = True
        log(f"⚠️ GATED: WinRate {win_rate:.1%} < {GATING_MIN_WINRATE:.1%} or PF {pf:.2f} < {GATING_MIN_PF}")
        return False

    is_gated = False
    return True


def get_signal(df: pd.DataFrame) -> tuple[str, int]:
    """Simple EMA Crossover with ADX filter"""
    if len(df) < 5:
        return 'HOLD', 0

    row = df.iloc[-1]
    prev = df.iloc[-2]

    price = row['close']
    ema_fast = row[f'EMA_{EMA_FAST}']
    ema_slow = row[f'EMA_{EMA_SLOW}']
    prev_ema_fast = prev[f'EMA_{EMA_FAST}']
    prev_ema_slow = prev[f'EMA_{EMA_SLOW}']
    adx = row[f'ADX_{ADX_PERIOD}']
    rsi = row[f'RSI_{RSI_PERIOD}']

    # Need trending market
    if adx < 20:
        return 'HOLD', 0

    # Golden Cross: Fast EMA crosses above Slow EMA
    if prev_ema_fast <= prev_ema_slow and ema_fast > ema_slow:
        if rsi < 68 and ALLOW_LONGS:  # Not overbought
            return 'BUY', 5
    
    # Death Cross: Fast EMA crosses below Slow EMA
    if prev_ema_fast >= prev_ema_slow and ema_fast < ema_slow:
        if rsi > 32 and ALLOW_SHORTS:  # Not oversold
            return 'SELL', 5

    return 'HOLD', 0


def get_balance() -> float:
    """ดึงยอด USDT"""
    try:
        balance = exchange.fetch_balance()
        return balance.get('USDT', {}).get('free', 0)
    except Exception as e:
        log(f"❌ Error fetching balance: {e}")
        return 0


def open_position(signal: str, price: float, score: int):
    """เปิด position"""
    global current_position

    balance = get_balance()
    if balance < 10:
        log("⚠️ Balance too low")
        return

    position_value = balance * BALANCE_PERCENT
    quantity = position_value / price

    if signal == 'BUY':
        pos_type = 'LONG'
        stop_loss = price * (1 - STOP_LOSS_PERCENT)
        take_profit = price * (1 + TAKE_PROFIT_PERCENT)
    else:
        pos_type = 'SHORT'
        stop_loss = price * (1 + STOP_LOSS_PERCENT)
        take_profit = price * (1 - TAKE_PROFIT_PERCENT)

    current_position = {
        'type': pos_type,
        'entry_price': price,
        'quantity': quantity,
        'stop_loss': stop_loss,
        'take_profit': take_profit,
        'highest_price': price,
        'lowest_price': price,
        'entry_time': datetime.now(),
        'score': score,
    }

    log(f"🚀 OPEN {pos_type} @ {price:.2f} | Qty: {quantity:.6f} | SL: {stop_loss:.2f} | TP: {take_profit:.2f} | Score: {score}")

    # TODO: ส่งคำสั่งจริงที่นี่
    # if signal == 'BUY':
    #     exchange.create_market_buy_order(SYMBOL, quantity)
    # else:
    #     exchange.create_market_sell_order(SYMBOL, quantity)


def close_position(price: float, reason: str):
    """ปิด position"""
    global current_position, trade_history

    if current_position is None:
        return

    entry = current_position['entry_price']
    qty = current_position['quantity']

    if current_position['type'] == 'LONG':
        pnl = (price - entry) * qty
        pnl_pct = (price - entry) / entry * 100
    else:
        pnl = (entry - price) * qty
        pnl_pct = (entry - price) / entry * 100

    # Deduct fee
    fee = price * qty * FEE_PERCENT * 2
    net_pnl = pnl - fee

    trade = {
        'type': current_position['type'],
        'entry_price': entry,
        'exit_price': price,
        'quantity': qty,
        'pnl': net_pnl,
        'pnl_pct': pnl_pct,
        'reason': reason,
        'entry_time': current_position['entry_time'],
        'exit_time': datetime.now(),
    }
    trade_history.append(trade)

    icon = '✅' if net_pnl > 0 else '❌'
    log(f"{icon} CLOSE {current_position['type']} @ {price:.2f} | PnL: ${net_pnl:.2f} ({pnl_pct:+.2f}%) | {reason}")

    # TODO: ส่งคำสั่งปิดจริงที่นี่
    # if current_position['type'] == 'LONG':
    #     exchange.create_market_sell_order(SYMBOL, qty)
    # else:
    #     exchange.create_market_buy_order(SYMBOL, qty)

    current_position = None


def manage_position(high: float, low: float, close: float):
    """จัดการ position - trailing stop, SL, TP"""
    global current_position

    if current_position is None:
        return

    pos = current_position

    if pos['type'] == 'LONG':
        # Update trailing
        if high > pos['highest_price']:
            pos['highest_price'] = high
            new_sl = high * (1 - TRAILING_STOP_PERCENT)
            if new_sl > pos['stop_loss']:
                pos['stop_loss'] = new_sl
                log(f"📈 Trailing SL updated: {new_sl:.2f}")

        # Check SL
        if low <= pos['stop_loss']:
            close_position(pos['stop_loss'], 'STOP_LOSS')
            return

        # Check TP
        if high >= pos['take_profit']:
            close_position(pos['take_profit'], 'TAKE_PROFIT')
            return

    else:  # SHORT
        # Update trailing
        if low < pos['lowest_price']:
            pos['lowest_price'] = low
            new_sl = low * (1 + TRAILING_STOP_PERCENT)
            if new_sl < pos['stop_loss']:
                pos['stop_loss'] = new_sl
                log(f"📉 Trailing SL updated: {new_sl:.2f}")

        # Check SL
        if high >= pos['stop_loss']:
            close_position(pos['stop_loss'], 'STOP_LOSS')
            return

        # Check TP
        if low <= pos['take_profit']:
            close_position(pos['take_profit'], 'TAKE_PROFIT')
            return


def print_stats():
    """แสดงสถิติ"""
    if not trade_history:
        return

    total = len(trade_history)
    wins = sum(1 for t in trade_history if t['pnl'] > 0)
    losses = total - wins
    win_rate = wins / total * 100

    total_profit = sum(t['pnl'] for t in trade_history if t['pnl'] > 0)
    total_loss = abs(sum(t['pnl'] for t in trade_history if t['pnl'] <= 0))
    net = sum(t['pnl'] for t in trade_history)
    pf = total_profit / total_loss if total_loss > 0 else 999

    log(f"📊 Stats: {total} trades | Win: {wins} ({win_rate:.1f}%) | Loss: {losses} | Net: ${net:.2f} | PF: {pf:.2f}")


def run_bot():
    """Main loop"""
    log("=" * 60)
    log("🚀 SCALPING BOT STARTED")
    log(f"Symbol: {SYMBOL} | TF: {TIMEFRAME}")
    log(f"SL: {STOP_LOSS_PERCENT*100}% | TP: {TAKE_PROFIT_PERCENT*100}% | Trail: {TRAILING_STOP_PERCENT*100}%")
    log(f"Session: {ACTIVE_HOURS[0]:02d}:00 - {ACTIVE_HOURS[-1]:02d}:00 UTC")
    log(f"Gating: {'ON' if ENABLE_GATING else 'OFF'}")
    log("=" * 60)

    while True:
        try:
            # Check session
            if not check_session():
                if current_position:
                    df = fetch_data(SYMBOL, TIMEFRAME, 10)
                    if not df.empty:
                        close_position(df['close'].iloc[-1], 'SESSION_END')
                log("💤 Outside trading hours, sleeping...")
                time.sleep(300)
                continue

            # Check gating
            if not check_gating():
                log("⛔ System gated, waiting for improvement...")
                time.sleep(300)
                continue

            # Fetch data
            df = fetch_data(SYMBOL, TIMEFRAME, 200)
            if df.empty:
                time.sleep(60)
                continue

            df = calculate_indicators(df)
            if df.empty:
                time.sleep(60)
                continue

            row = df.iloc[-1]
            price = row['close']
            high = row['high']
            low = row['low']

            # Manage existing position
            if current_position:
                manage_position(high, low, price)

            # Look for new signal if no position
            if current_position is None:
                signal, score = get_signal(df)
                if signal in ['BUY', 'SELL']:
                    open_position(signal, price, score)

            # Print stats every 10 trades
            if len(trade_history) > 0 and len(trade_history) % 10 == 0:
                print_stats()

            # Sleep until next candle
            time.sleep(60)

        except KeyboardInterrupt:
            log("👋 Bot stopped by user")
            if current_position:
                df = fetch_data(SYMBOL, TIMEFRAME, 10)
                if not df.empty:
                    close_position(df['close'].iloc[-1], 'USER_STOP')
            print_stats()
            break

        except Exception as e:
            log(f"❌ Error: {e}")
            time.sleep(60)


def backtest_quick(days: int = 14):
    """Quick backtest to verify strategy"""
    log("=" * 60)
    log(f"📊 QUICK BACKTEST: {SYMBOL} {TIMEFRAME} {days}d")
    log("=" * 60)

    # Fetch historical data
    all_data = []
    since = exchange.parse8601((datetime.now() - timedelta(days=days)).isoformat())

    while True:
        bars = exchange.fetch_ohlcv(SYMBOL, TIMEFRAME, since=since, limit=1000)
        if not bars:
            break
        all_data.extend(bars)
        since = bars[-1][0] + 1
        if bars[-1][0] >= exchange.milliseconds() - 60000:
            break
        log(f"  Downloaded {len(all_data)} candles...")

    df = pd.DataFrame(all_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df = df.drop_duplicates(subset='timestamp').reset_index(drop=True)
    log(f"✅ Total: {len(df)} candles")

    df = calculate_indicators(df)

    # Simulate
    balance = 1000
    position = None
    trades = []

    for i in range(1, len(df)):
        row = df.iloc[i]
        price = row['close']
        high = row['high']
        low = row['low']
        hour = row['timestamp'].hour

        # Session filter
        if hour not in ACTIVE_HOURS:
            if position:
                # Close at session end
                if position['type'] == 'LONG':
                    pnl = (price - position['entry']) * position['qty']
                else:
                    pnl = (position['entry'] - price) * position['qty']
                fee = price * position['qty'] * FEE_PERCENT * 2
                balance += pnl - fee + position['value']
                trades.append({'pnl': pnl - fee})
                position = None
            continue

        # Manage position
        if position:
            if position['type'] == 'LONG':
                if high > position['highest']:
                    position['highest'] = high
                    new_sl = high * (1 - TRAILING_STOP_PERCENT)
                    if new_sl > position['sl']:
                        position['sl'] = new_sl

                if low <= position['sl']:
                    pnl = (position['sl'] - position['entry']) * position['qty']
                    fee = position['sl'] * position['qty'] * FEE_PERCENT * 2
                    balance += pnl - fee + position['value']
                    trades.append({'pnl': pnl - fee})
                    position = None
                    continue

                if high >= position['tp']:
                    pnl = (position['tp'] - position['entry']) * position['qty']
                    fee = position['tp'] * position['qty'] * FEE_PERCENT * 2
                    balance += pnl - fee + position['value']
                    trades.append({'pnl': pnl - fee})
                    position = None
                    continue

            else:  # SHORT
                if low < position['lowest']:
                    position['lowest'] = low
                    new_sl = low * (1 + TRAILING_STOP_PERCENT)
                    if new_sl < position['sl']:
                        position['sl'] = new_sl

                if high >= position['sl']:
                    pnl = (position['entry'] - position['sl']) * position['qty']
                    fee = position['sl'] * position['qty'] * FEE_PERCENT * 2
                    balance += pnl - fee + position['value']
                    trades.append({'pnl': pnl - fee})
                    position = None
                    continue

                if low <= position['tp']:
                    pnl = (position['entry'] - position['tp']) * position['qty']
                    fee = position['tp'] * position['qty'] * FEE_PERCENT * 2
                    balance += pnl - fee + position['value']
                    trades.append({'pnl': pnl - fee})
                    position = None
                    continue

        # New signal
        if position is None:
            # Simple version of get_signal for backtest
            df_slice = df.iloc[:i+1].copy()
            signal, score = get_signal(df_slice)

            if signal in ['BUY', 'SELL']:
                value = balance * BALANCE_PERCENT
                qty = value / price
                fee = value * FEE_PERCENT
                balance -= value + fee

                if signal == 'BUY':
                    position = {
                        'type': 'LONG',
                        'entry': price,
                        'qty': qty,
                        'value': value,
                        'sl': price * (1 - STOP_LOSS_PERCENT),
                        'tp': price * (1 + TAKE_PROFIT_PERCENT),
                        'highest': price,
                        'lowest': price,
                    }
                else:
                    position = {
                        'type': 'SHORT',
                        'entry': price,
                        'qty': qty,
                        'value': value,
                        'sl': price * (1 + STOP_LOSS_PERCENT),
                        'tp': price * (1 - TAKE_PROFIT_PERCENT),
                        'highest': price,
                        'lowest': price,
                    }

    # Close remaining position
    if position:
        price = df['close'].iloc[-1]
        if position['type'] == 'LONG':
            pnl = (price - position['entry']) * position['qty']
        else:
            pnl = (position['entry'] - price) * position['qty']
        fee = price * position['qty'] * FEE_PERCENT * 2
        balance += pnl - fee + position['value']
        trades.append({'pnl': pnl - fee})

    # Results
    if trades:
        wins = sum(1 for t in trades if t['pnl'] > 0)
        total = len(trades)
        win_rate = wins / total * 100
        total_profit = sum(t['pnl'] for t in trades if t['pnl'] > 0)
        total_loss = abs(sum(t['pnl'] for t in trades if t['pnl'] <= 0))
        pf = total_profit / total_loss if total_loss > 0 else 999
        roi = (balance - 1000) / 1000 * 100

        log(f"\n📊 RESULTS:")
        log(f"  Trades: {total}")
        log(f"  Win Rate: {win_rate:.1f}%")
        log(f"  Profit Factor: {pf:.2f}")
        log(f"  ROI: {roi:+.2f}%")
        log(f"  Final Balance: ${balance:.2f}")

        return {'roi': roi, 'pf': pf, 'win_rate': win_rate, 'trades': total}
    else:
        log("❌ No trades executed")
        return None


if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == 'backtest':
        days = int(sys.argv[2]) if len(sys.argv) > 2 else 14
        backtest_quick(days)
    else:
        run_bot()
