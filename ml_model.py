"""
ML Model - Pattern Recognition for Trading Signals
เรียนรู้จาก Trade Journal และ historical data
"""
import json
import os
import math
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
import random


@dataclass
class PatternFeatures:
    """Features extracted from market data"""
    rsi_zone: str  # oversold, neutral, overbought
    ema_trend: str  # bullish, bearish, neutral
    macd_signal: str  # bullish, bearish, cross_up, cross_down
    volume_profile: str  # low, normal, high
    volatility: str  # low, medium, high
    hour_of_day: int
    day_of_week: int
    recent_trend: str  # up, down, sideways


@dataclass
class TradePattern:
    """Pattern learned from historical trades"""
    pattern_id: str
    features: Dict
    success_rate: float
    sample_count: int
    avg_profit: float
    avg_duration: float
    recommended_side: str  # LONG, SHORT, SKIP
    confidence: float


class MLPatternModel:
    """
    Simple ML model for pattern recognition
    Uses pattern matching and statistical learning
    """
    
    def __init__(self, data_dir: str = "."):
        self.data_dir = data_dir
        self.model_file = os.path.join(data_dir, "ml_model.json")
        self.patterns: List[TradePattern] = []
        self.feature_importance: Dict[str, float] = {}
        self.load_model()
    
    def load_model(self):
        """Load trained model from file"""
        if os.path.exists(self.model_file):
            try:
                with open(self.model_file, 'r') as f:
                    data = json.load(f)
                    self.patterns = [
                        TradePattern(**p) for p in data.get('patterns', [])
                    ]
                    self.feature_importance = data.get('feature_importance', {})
                print(f"✅ Loaded {len(self.patterns)} patterns from model")
            except Exception as e:
                print(f"⚠️ Error loading model: {e}")
                self.patterns = []
    
    def save_model(self):
        """Save trained model to file"""
        try:
            data = {
                'patterns': [asdict(p) for p in self.patterns],
                'feature_importance': self.feature_importance,
                'updated_at': datetime.now().isoformat()
            }
            with open(self.model_file, 'w') as f:
                json.dump(data, f, indent=2)
            print(f"💾 Saved {len(self.patterns)} patterns to model")
        except Exception as e:
            print(f"⚠️ Error saving model: {e}")
    
    def extract_features(self, data: Dict) -> Dict:
        """Extract features from market data"""
        features = {}
        
        # RSI Zone
        rsi = data.get('rsi', 50)
        if rsi < 30:
            features['rsi_zone'] = 'oversold'
        elif rsi > 70:
            features['rsi_zone'] = 'overbought'
        else:
            features['rsi_zone'] = 'neutral'
        
        # EMA Trend
        price = data.get('price', 0)
        ema_fast = data.get('ema_fast', price)
        ema_slow = data.get('ema_slow', price)
        
        if ema_fast > ema_slow * 1.002:
            features['ema_trend'] = 'bullish'
        elif ema_fast < ema_slow * 0.998:
            features['ema_trend'] = 'bearish'
        else:
            features['ema_trend'] = 'neutral'
        
        # MACD Signal
        macd = data.get('macd', 0)
        macd_signal = data.get('macd_signal', 0)
        macd_prev = data.get('macd_prev', macd)
        
        if macd > macd_signal and macd_prev <= macd_signal:
            features['macd_signal'] = 'cross_up'
        elif macd < macd_signal and macd_prev >= macd_signal:
            features['macd_signal'] = 'cross_down'
        elif macd > macd_signal:
            features['macd_signal'] = 'bullish'
        else:
            features['macd_signal'] = 'bearish'
        
        # Volume Profile
        volume = data.get('volume', 0)
        avg_volume = data.get('avg_volume', volume)
        
        if avg_volume > 0:
            vol_ratio = volume / avg_volume
            if vol_ratio > 1.5:
                features['volume_profile'] = 'high'
            elif vol_ratio < 0.5:
                features['volume_profile'] = 'low'
            else:
                features['volume_profile'] = 'normal'
        else:
            features['volume_profile'] = 'normal'
        
        # Volatility
        atr = data.get('atr', 0)
        avg_atr = data.get('avg_atr', atr)
        
        if avg_atr > 0:
            vol_ratio = atr / avg_atr
            if vol_ratio > 1.3:
                features['volatility'] = 'high'
            elif vol_ratio < 0.7:
                features['volatility'] = 'low'
            else:
                features['volatility'] = 'medium'
        else:
            features['volatility'] = 'medium'
        
        # Time features
        now = datetime.now()
        features['hour_of_day'] = now.hour
        features['day_of_week'] = now.weekday()
        
        # Recent trend (simplified)
        price_change = data.get('price_change_pct', 0)
        if price_change > 0.5:
            features['recent_trend'] = 'up'
        elif price_change < -0.5:
            features['recent_trend'] = 'down'
        else:
            features['recent_trend'] = 'sideways'
        
        return features
    
    def calculate_pattern_hash(self, features: Dict) -> str:
        """Create a hash for pattern matching"""
        key_features = [
            features.get('rsi_zone', ''),
            features.get('ema_trend', ''),
            features.get('macd_signal', ''),
            features.get('volume_profile', ''),
        ]
        return '_'.join(key_features)
    
    def train_from_journal(self, journal_file: str = "trade_journal.json"):
        """Train model from trade journal"""
        journal_path = os.path.join(self.data_dir, journal_file)
        
        if not os.path.exists(journal_path):
            print("⚠️ Trade journal not found. Using sample data.")
            self._create_sample_patterns()
            return
        
        try:
            with open(journal_path, 'r') as f:
                trades = json.load(f)
            
            if not trades:
                print("⚠️ No trades in journal. Using sample patterns.")
                self._create_sample_patterns()
                return
            
            # Group trades by pattern
            pattern_stats: Dict[str, Dict] = {}
            
            for trade in trades:
                # Extract features from trade entry
                features = trade.get('indicators_at_entry', {})
                if not features:
                    continue
                
                pattern_hash = self.calculate_pattern_hash(features)
                
                if pattern_hash not in pattern_stats:
                    pattern_stats[pattern_hash] = {
                        'features': features,
                        'wins': 0,
                        'losses': 0,
                        'total_pnl': 0,
                        'total_duration': 0,
                        'longs': 0,
                        'shorts': 0,
                    }
                
                stats = pattern_stats[pattern_hash]
                
                # Update stats
                pnl = trade.get('pnl_usd', 0)
                if pnl > 0:
                    stats['wins'] += 1
                else:
                    stats['losses'] += 1
                
                stats['total_pnl'] += pnl
                
                if trade.get('side', '').upper() == 'LONG':
                    stats['longs'] += 1
                else:
                    stats['shorts'] += 1
                
                # Calculate duration
                try:
                    entry = datetime.fromisoformat(trade.get('entry_time', ''))
                    exit = datetime.fromisoformat(trade.get('exit_time', ''))
                    stats['total_duration'] += (exit - entry).total_seconds() / 3600
                except:
                    pass
            
            # Convert to patterns
            self.patterns = []
            for pattern_hash, stats in pattern_stats.items():
                total = stats['wins'] + stats['losses']
                if total < 2:
                    continue
                
                success_rate = stats['wins'] / total
                avg_profit = stats['total_pnl'] / total
                avg_duration = stats['total_duration'] / total if total > 0 else 0
                
                # Determine recommended side
                if stats['longs'] > stats['shorts'] * 1.5 and success_rate > 0.5:
                    recommended_side = 'LONG'
                elif stats['shorts'] > stats['longs'] * 1.5 and success_rate > 0.5:
                    recommended_side = 'SHORT'
                elif success_rate < 0.4:
                    recommended_side = 'SKIP'
                else:
                    recommended_side = 'NEUTRAL'
                
                # Calculate confidence
                confidence = min(0.95, 0.5 + (total * 0.05) + (success_rate * 0.3))
                
                pattern = TradePattern(
                    pattern_id=pattern_hash,
                    features=stats['features'],
                    success_rate=success_rate,
                    sample_count=total,
                    avg_profit=avg_profit,
                    avg_duration=avg_duration,
                    recommended_side=recommended_side,
                    confidence=confidence
                )
                self.patterns.append(pattern)
            
            # Calculate feature importance
            self._calculate_feature_importance()
            
            # Save model
            self.save_model()
            
            print(f"✅ Trained on {len(trades)} trades, created {len(self.patterns)} patterns")
            
        except Exception as e:
            print(f"⚠️ Error training from journal: {e}")
            self._create_sample_patterns()
    
    def _create_sample_patterns(self):
        """Create sample patterns for demo"""
        sample_patterns = [
            # High probability patterns
            TradePattern(
                pattern_id="oversold_bullish_cross_up_high",
                features={
                    'rsi_zone': 'oversold',
                    'ema_trend': 'bullish',
                    'macd_signal': 'cross_up',
                    'volume_profile': 'high'
                },
                success_rate=0.72,
                sample_count=45,
                avg_profit=2.5,
                avg_duration=4.2,
                recommended_side='LONG',
                confidence=0.85
            ),
            TradePattern(
                pattern_id="overbought_bearish_cross_down_high",
                features={
                    'rsi_zone': 'overbought',
                    'ema_trend': 'bearish',
                    'macd_signal': 'cross_down',
                    'volume_profile': 'high'
                },
                success_rate=0.68,
                sample_count=38,
                avg_profit=2.1,
                avg_duration=3.8,
                recommended_side='SHORT',
                confidence=0.82
            ),
            # Medium probability patterns
            TradePattern(
                pattern_id="neutral_bullish_bullish_normal",
                features={
                    'rsi_zone': 'neutral',
                    'ema_trend': 'bullish',
                    'macd_signal': 'bullish',
                    'volume_profile': 'normal'
                },
                success_rate=0.58,
                sample_count=67,
                avg_profit=1.2,
                avg_duration=5.5,
                recommended_side='LONG',
                confidence=0.72
            ),
            # Low probability (should skip)
            TradePattern(
                pattern_id="neutral_neutral_bearish_low",
                features={
                    'rsi_zone': 'neutral',
                    'ema_trend': 'neutral',
                    'macd_signal': 'bearish',
                    'volume_profile': 'low'
                },
                success_rate=0.35,
                sample_count=23,
                avg_profit=-0.8,
                avg_duration=6.2,
                recommended_side='SKIP',
                confidence=0.65
            ),
        ]
        
        self.patterns = sample_patterns
        self._calculate_feature_importance()
        self.save_model()
        print(f"✅ Created {len(self.patterns)} sample patterns")
    
    def _calculate_feature_importance(self):
        """Calculate importance of each feature"""
        feature_scores = {
            'rsi_zone': 0,
            'ema_trend': 0,
            'macd_signal': 0,
            'volume_profile': 0,
        }
        
        for pattern in self.patterns:
            weight = pattern.success_rate * pattern.sample_count
            
            for feature in feature_scores:
                if feature in pattern.features:
                    feature_scores[feature] += weight
        
        # Normalize
        total = sum(feature_scores.values()) or 1
        self.feature_importance = {
            k: v / total for k, v in feature_scores.items()
        }
    
    def predict(self, market_data: Dict) -> Dict:
        """
        Predict trade signal based on current market data
        
        Returns:
            Dict with prediction results:
            - signal: LONG, SHORT, or SKIP
            - confidence: 0.0 - 1.0
            - matching_pattern: pattern details if found
            - reasons: list of reasons for prediction
        """
        features = self.extract_features(market_data)
        pattern_hash = self.calculate_pattern_hash(features)
        
        # Find matching pattern
        matching_pattern = None
        best_similarity = 0
        
        for pattern in self.patterns:
            similarity = self._calculate_similarity(features, pattern.features)
            if similarity > best_similarity:
                best_similarity = similarity
                matching_pattern = pattern
        
        if matching_pattern and best_similarity > 0.7:
            return {
                'signal': matching_pattern.recommended_side,
                'confidence': matching_pattern.confidence * best_similarity,
                'matching_pattern': asdict(matching_pattern),
                'similarity': best_similarity,
                'reasons': self._generate_reasons(matching_pattern, features),
                'expected_profit': matching_pattern.avg_profit,
                'success_rate': matching_pattern.success_rate
            }
        else:
            return {
                'signal': 'NEUTRAL',
                'confidence': 0.3,
                'matching_pattern': None,
                'similarity': best_similarity,
                'reasons': ["No strong pattern match found"],
                'expected_profit': 0,
                'success_rate': 0.5
            }
    
    def _calculate_similarity(self, features1: Dict, features2: Dict) -> float:
        """Calculate similarity between two feature sets"""
        matching = 0
        total = 0
        
        for key in ['rsi_zone', 'ema_trend', 'macd_signal', 'volume_profile']:
            if key in features1 and key in features2:
                total += 1
                if features1[key] == features2[key]:
                    matching += 1
        
        return matching / total if total > 0 else 0
    
    def _generate_reasons(self, pattern: TradePattern, features: Dict) -> List[str]:
        """Generate human-readable reasons for prediction"""
        reasons = []
        
        if pattern.success_rate > 0.65:
            reasons.append(f"Pattern has {pattern.success_rate*100:.0f}% historical success rate")
        
        if pattern.sample_count > 30:
            reasons.append(f"Based on {pattern.sample_count} historical trades")
        
        if pattern.avg_profit > 0:
            reasons.append(f"Average profit: ${pattern.avg_profit:.2f}")
        
        rsi_zone = features.get('rsi_zone', '')
        if rsi_zone == 'oversold':
            reasons.append("RSI indicates oversold conditions")
        elif rsi_zone == 'overbought':
            reasons.append("RSI indicates overbought conditions")
        
        macd = features.get('macd_signal', '')
        if macd == 'cross_up':
            reasons.append("MACD bullish crossover detected")
        elif macd == 'cross_down':
            reasons.append("MACD bearish crossover detected")
        
        return reasons
    
    def get_stats(self) -> Dict:
        """Get model statistics"""
        if not self.patterns:
            return {'message': 'No patterns learned yet'}
        
        return {
            'total_patterns': len(self.patterns),
            'avg_success_rate': sum(p.success_rate for p in self.patterns) / len(self.patterns),
            'best_pattern': max(self.patterns, key=lambda p: p.success_rate).pattern_id,
            'total_samples': sum(p.sample_count for p in self.patterns),
            'feature_importance': self.feature_importance
        }
    
    def get_telegram_summary(self) -> str:
        """Get summary for Telegram"""
        stats = self.get_stats()
        
        if 'message' in stats:
            return f"🤖 ML Model: {stats['message']}"
        
        summary = "🤖 *ML Model Status*\n\n"
        summary += f"📊 Patterns: {stats['total_patterns']}\n"
        summary += f"📈 Avg Success: {stats['avg_success_rate']*100:.1f}%\n"
        summary += f"📝 Total Samples: {stats['total_samples']}\n"
        summary += f"\n🏆 Best Pattern:\n`{stats['best_pattern']}`\n"
        
        if stats['feature_importance']:
            summary += "\n📊 *Feature Importance:*\n"
            for feat, imp in sorted(stats['feature_importance'].items(), 
                                     key=lambda x: x[1], reverse=True):
                bar = "█" * int(imp * 10)
                summary += f"{feat}: {bar} {imp*100:.0f}%\n"
        
        return summary


# Example usage
if __name__ == "__main__":
    # Initialize model
    model = MLPatternModel()
    
    # Train from journal (or create sample patterns)
    model.train_from_journal()
    
    # Print stats
    print("\n📊 Model Stats:")
    stats = model.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    # Test prediction
    print("\n🔮 Test Prediction:")
    test_data = {
        'rsi': 25,
        'price': 95000,
        'ema_fast': 95200,
        'ema_slow': 94800,
        'macd': 50,
        'macd_signal': 30,
        'macd_prev': 25,
        'volume': 1500,
        'avg_volume': 1000,
    }
    
    prediction = model.predict(test_data)
    print(f"  Signal: {prediction['signal']}")
    print(f"  Confidence: {prediction['confidence']:.2%}")
    print(f"  Reasons: {prediction['reasons']}")
    
    # Telegram summary
    print("\n📱 Telegram Summary:")
    print(model.get_telegram_summary())
