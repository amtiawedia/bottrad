"""
Multi-Coin Scanner - เทรดหลายเหรียญพร้อมกัน
"""
import ccxt
import pandas as pd
import pandas_ta as ta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import threading
import time


@dataclass
class CoinSignal:
    """Signal for a specific coin"""
    symbol: str
    side: str  # 'long' or 'short'
    confidence: float
    entry_price: float
    stop_loss: float
    take_profit: float
    strength: float  # 0-100
    reasons: List[str]


class MultiCoinScanner:
    """Scan multiple coins for trading opportunities"""
    
    # Supported coins with their characteristics
    COINS = {
        'BTC/USDT': {
            'name': 'Bitcoin',
            'volatility': 'medium',
            'min_size': 0.001,
            'default_leverage': 50
        },
        'ETH/USDT': {
            'name': 'Ethereum', 
            'volatility': 'medium-high',
            'min_size': 0.01,
            'default_leverage': 50
        },
        'SOL/USDT': {
            'name': 'Solana',
            'volatility': 'high',
            'min_size': 0.1,
            'default_leverage': 30
        },
        'BNB/USDT': {
            'name': 'BNB',
            'volatility': 'medium',
            'min_size': 0.01,
            'default_leverage': 40
        },
        'XRP/USDT': {
            'name': 'XRP',
            'volatility': 'medium-high',
            'min_size': 1,
            'default_leverage': 30
        },
        'DOGE/USDT': {
            'name': 'Dogecoin',
            'volatility': 'high',
            'min_size': 10,
            'default_leverage': 25
        }
    }
    
    def __init__(self, api_key: str, secret_key: str, enabled_coins: List[str] = None):
        self.exchange = ccxt.binanceusdm({
            'apiKey': api_key,
            'secret': secret_key,
            'sandbox': False,
            'options': {'defaultType': 'future'}
        })
        self.exchange.load_markets()
        
        # Default to BTC, ETH, SOL if not specified
        self.enabled_coins = enabled_coins or ['BTC/USDT', 'ETH/USDT', 'SOL/USDT']
        self.coin_data: Dict[str, pd.DataFrame] = {}
        self.last_signals: Dict[str, CoinSignal] = {}
    
    def fetch_ohlcv(self, symbol: str, timeframe: str = '5m', limit: int = 500) -> pd.DataFrame:
        """Fetch OHLCV data for a symbol"""
        try:
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            return df
        except Exception as e:
            print(f"[Scanner] Error fetching {symbol}: {e}")
            return pd.DataFrame()
    
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate technical indicators"""
        if df.empty:
            return df
        
        # RSI
        df['RSI'] = ta.rsi(df['close'], length=14)
        
        # EMA
        df['EMA_8'] = ta.ema(df['close'], length=8)
        df['EMA_21'] = ta.ema(df['close'], length=21)
        df['EMA_50'] = ta.ema(df['close'], length=50)
        
        # MACD
        macd = ta.macd(df['close'], fast=12, slow=26, signal=9)
        if macd is not None:
            df = pd.concat([df, macd], axis=1)
        
        # Bollinger Bands
        bb = ta.bbands(df['close'], length=20, std=2)
        if bb is not None:
            df = pd.concat([df, bb], axis=1)
        
        # ADX
        adx = ta.adx(df['high'], df['low'], df['close'], length=14)
        if adx is not None:
            df = pd.concat([df, adx], axis=1)
        
        # Volume SMA
        df['Volume_SMA'] = ta.sma(df['volume'], length=20)
        df['Volume_Ratio'] = df['volume'] / df['Volume_SMA']
        
        return df
    
    def analyze_coin(self, symbol: str) -> Optional[CoinSignal]:
        """Analyze a single coin and generate signal"""
        df = self.fetch_ohlcv(symbol)
        if df.empty:
            return None
        
        df = self.calculate_indicators(df)
        if len(df) < 50:
            return None
        
        current = df.iloc[-1]
        prev = df.iloc[-2]
        
        # Score system
        long_score = 0
        short_score = 0
        reasons = []
        
        # RSI signals
        rsi = current.get('RSI', 50)
        if rsi < 30:
            long_score += 25
            reasons.append(f"RSI oversold ({rsi:.0f})")
        elif rsi > 70:
            short_score += 25
            reasons.append(f"RSI overbought ({rsi:.0f})")
        elif rsi < 45:
            long_score += 10
        elif rsi > 55:
            short_score += 10
        
        # EMA trend
        ema8 = current.get('EMA_8', 0)
        ema21 = current.get('EMA_21', 0)
        ema50 = current.get('EMA_50', 0)
        
        if ema8 > ema21 > ema50:
            long_score += 20
            reasons.append("EMA uptrend")
        elif ema8 < ema21 < ema50:
            short_score += 20
            reasons.append("EMA downtrend")
        
        # EMA crossover
        prev_ema8 = prev.get('EMA_8', 0)
        prev_ema21 = prev.get('EMA_21', 0)
        
        if prev_ema8 < prev_ema21 and ema8 > ema21:
            long_score += 30
            reasons.append("EMA bullish cross")
        elif prev_ema8 > prev_ema21 and ema8 < ema21:
            short_score += 30
            reasons.append("EMA bearish cross")
        
        # MACD
        macd_val = current.get('MACD_12_26_9', 0)
        macd_signal = current.get('MACDs_12_26_9', 0)
        macd_hist = current.get('MACDh_12_26_9', 0)
        
        if macd_val > macd_signal and macd_hist > 0:
            long_score += 15
            reasons.append("MACD bullish")
        elif macd_val < macd_signal and macd_hist < 0:
            short_score += 15
            reasons.append("MACD bearish")
        
        # ADX trend strength
        adx = current.get('ADX_14', 0)
        if adx > 25:
            # Strong trend - amplify signals
            if long_score > short_score:
                long_score += 10
            else:
                short_score += 10
            reasons.append(f"Strong trend (ADX={adx:.0f})")
        
        # Volume confirmation
        vol_ratio = current.get('Volume_Ratio', 1)
        if vol_ratio > 1.5:
            if long_score > short_score:
                long_score += 10
            else:
                short_score += 10
            reasons.append(f"High volume ({vol_ratio:.1f}x)")
        
        # Determine signal
        price = current['close']
        
        if long_score >= 50 and long_score > short_score:
            coin_info = self.COINS.get(symbol, {})
            sl_pct = 0.015 if coin_info.get('volatility') == 'high' else 0.012
            tp_pct = 0.06 if coin_info.get('volatility') == 'high' else 0.05
            
            return CoinSignal(
                symbol=symbol,
                side='long',
                confidence=min(long_score / 100, 0.95),
                entry_price=price,
                stop_loss=price * (1 - sl_pct),
                take_profit=price * (1 + tp_pct),
                strength=long_score,
                reasons=reasons
            )
        
        elif short_score >= 50 and short_score > long_score:
            coin_info = self.COINS.get(symbol, {})
            sl_pct = 0.015 if coin_info.get('volatility') == 'high' else 0.012
            tp_pct = 0.06 if coin_info.get('volatility') == 'high' else 0.05
            
            return CoinSignal(
                symbol=symbol,
                side='short',
                confidence=min(short_score / 100, 0.95),
                entry_price=price,
                stop_loss=price * (1 + sl_pct),
                take_profit=price * (1 - tp_pct),
                strength=short_score,
                reasons=reasons
            )
        
        return None
    
    def scan_all(self) -> List[CoinSignal]:
        """Scan all enabled coins and return signals"""
        signals = []
        
        for symbol in self.enabled_coins:
            try:
                signal = self.analyze_coin(symbol)
                if signal:
                    signals.append(signal)
                    self.last_signals[symbol] = signal
            except Exception as e:
                print(f"[Scanner] Error scanning {symbol}: {e}")
        
        # Sort by strength
        signals.sort(key=lambda x: x.strength, reverse=True)
        return signals
    
    def get_best_opportunity(self) -> Optional[CoinSignal]:
        """Get the best trading opportunity across all coins"""
        signals = self.scan_all()
        if signals:
            return signals[0]
        return None
    
    def get_market_overview(self) -> Dict:
        """Get overview of all coins"""
        overview = {}
        
        for symbol in self.enabled_coins:
            try:
                df = self.fetch_ohlcv(symbol, limit=100)
                if df.empty:
                    continue
                
                df = self.calculate_indicators(df)
                current = df.iloc[-1]
                
                # Calculate 24h change
                if len(df) >= 288:  # 24h in 5m candles
                    change_24h = (current['close'] - df.iloc[-288]['close']) / df.iloc[-288]['close']
                else:
                    change_24h = (current['close'] - df.iloc[0]['close']) / df.iloc[0]['close']
                
                overview[symbol] = {
                    'price': current['close'],
                    'change_24h': change_24h,
                    'rsi': current.get('RSI', 50),
                    'adx': current.get('ADX_14', 0),
                    'volume_ratio': current.get('Volume_Ratio', 1),
                    'trend': 'up' if current.get('EMA_8', 0) > current.get('EMA_21', 0) else 'down'
                }
            except Exception as e:
                print(f"[Scanner] Error getting overview for {symbol}: {e}")
        
        return overview
    
    def get_telegram_summary(self) -> str:
        """Get summary for Telegram"""
        overview = self.get_market_overview()
        
        if not overview:
            return "❌ ไม่สามารถดึงข้อมูลได้"
        
        lines = ["🔍 <b>Multi-Coin Scanner</b>\n"]
        
        for symbol, data in overview.items():
            coin_name = self.COINS.get(symbol, {}).get('name', symbol.split('/')[0])
            emoji = "🟢" if data['trend'] == 'up' else "🔴"
            change_emoji = "📈" if data['change_24h'] > 0 else "📉"
            
            lines.append(
                f"{emoji} <b>{coin_name}</b>\n"
                f"   💰 ${data['price']:,.2f} {change_emoji} {data['change_24h']*100:+.2f}%\n"
                f"   📊 RSI: {data['rsi']:.0f} | ADX: {data['adx']:.0f}"
            )
        
        # Best opportunity
        signals = self.scan_all()
        if signals:
            best = signals[0]
            lines.append(f"\n🎯 <b>Best Signal:</b> {best.symbol}")
            lines.append(f"   {best.side.upper()} @ ${best.entry_price:,.2f}")
            lines.append(f"   Confidence: {best.confidence*100:.0f}%")
        
        return "\n".join(lines)


# For testing
if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    scanner = MultiCoinScanner(
        api_key=os.getenv('BINANCE_API_KEY', ''),
        secret_key=os.getenv('BINANCE_SECRET_KEY', ''),
        enabled_coins=['BTC/USDT', 'ETH/USDT', 'SOL/USDT']
    )
    
    print(scanner.get_telegram_summary())
