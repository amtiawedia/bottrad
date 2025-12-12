"""
Trade Journal - บันทึกและวิเคราะห์ทุกเทรด
"""
import json
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
import pandas as pd


@dataclass
class JournalEntry:
    """Single trade entry"""
    id: int
    symbol: str
    side: str  # long/short
    entry_price: float
    exit_price: float
    size: float
    leverage: int
    pnl: float
    pnl_pct: float
    entry_time: str
    exit_time: str
    exit_reason: str
    duration_minutes: int
    fees: float
    
    # Analysis fields
    market_condition: str = ""  # trending/ranging/volatile
    signal_confidence: float = 0.0
    indicators_at_entry: Dict = None
    notes: str = ""
    
    def __post_init__(self):
        if self.indicators_at_entry is None:
            self.indicators_at_entry = {}


class TradeJournal:
    """Trade Journal System - บันทึกและวิเคราะห์เทรด"""
    
    def __init__(self, journal_file: str = "trade_journal.json"):
        self.journal_file = journal_file
        self.entries: List[JournalEntry] = []
        self.load()
    
    def load(self):
        """Load journal from file"""
        if os.path.exists(self.journal_file):
            try:
                with open(self.journal_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.entries = [JournalEntry(**e) for e in data]
            except Exception as e:
                print(f"[Journal] Error loading: {e}")
                self.entries = []
    
    def save(self):
        """Save journal to file"""
        try:
            with open(self.journal_file, 'w', encoding='utf-8') as f:
                data = [asdict(e) for e in self.entries]
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[Journal] Error saving: {e}")
    
    def add_trade(self, trade: Dict, indicators: Dict = None, market_condition: str = "", confidence: float = 0.0):
        """Add new trade to journal"""
        # Calculate duration
        entry_time = datetime.fromisoformat(trade['entry_time']) if isinstance(trade['entry_time'], str) else trade['entry_time']
        exit_time = datetime.fromisoformat(trade['exit_time']) if isinstance(trade['exit_time'], str) else trade['exit_time']
        duration = int((exit_time - entry_time).total_seconds() / 60)
        
        entry = JournalEntry(
            id=len(self.entries) + 1,
            symbol=trade.get('symbol', 'BTC/USDT'),
            side=trade['side'],
            entry_price=trade['entry_price'],
            exit_price=trade['exit_price'],
            size=trade['size'],
            leverage=trade['leverage'],
            pnl=trade['pnl'],
            pnl_pct=trade['pnl_pct'],
            entry_time=entry_time.isoformat(),
            exit_time=exit_time.isoformat(),
            exit_reason=trade['exit_reason'],
            duration_minutes=duration,
            fees=trade.get('fees', 0),
            market_condition=market_condition,
            signal_confidence=confidence,
            indicators_at_entry=indicators or {}
        )
        
        self.entries.append(entry)
        self.save()
        return entry
    
    def get_stats(self) -> Dict:
        """Get overall statistics"""
        if not self.entries:
            return {
                'total_trades': 0,
                'wins': 0,
                'losses': 0,
                'win_rate': 0,
                'total_pnl': 0,
                'avg_pnl': 0,
                'best_trade': 0,
                'worst_trade': 0,
                'avg_duration': 0,
                'profit_factor': 0
            }
        
        wins = [e for e in self.entries if e.pnl > 0]
        losses = [e for e in self.entries if e.pnl <= 0]
        
        total_profit = sum(e.pnl for e in wins) if wins else 0
        total_loss = abs(sum(e.pnl for e in losses)) if losses else 0
        
        return {
            'total_trades': len(self.entries),
            'wins': len(wins),
            'losses': len(losses),
            'win_rate': len(wins) / len(self.entries) if self.entries else 0,
            'total_pnl': sum(e.pnl for e in self.entries),
            'avg_pnl': sum(e.pnl for e in self.entries) / len(self.entries),
            'best_trade': max(e.pnl for e in self.entries),
            'worst_trade': min(e.pnl for e in self.entries),
            'avg_duration': sum(e.duration_minutes for e in self.entries) / len(self.entries),
            'profit_factor': total_profit / total_loss if total_loss > 0 else float('inf'),
            'avg_win': sum(e.pnl for e in wins) / len(wins) if wins else 0,
            'avg_loss': sum(e.pnl for e in losses) / len(losses) if losses else 0
        }
    
    def get_stats_by_side(self) -> Dict:
        """Get statistics by long/short"""
        longs = [e for e in self.entries if e.side == 'long']
        shorts = [e for e in self.entries if e.side == 'short']
        
        def calc_side_stats(trades):
            if not trades:
                return {'trades': 0, 'win_rate': 0, 'total_pnl': 0}
            wins = len([t for t in trades if t.pnl > 0])
            return {
                'trades': len(trades),
                'win_rate': wins / len(trades),
                'total_pnl': sum(t.pnl for t in trades)
            }
        
        return {
            'long': calc_side_stats(longs),
            'short': calc_side_stats(shorts)
        }
    
    def get_stats_by_exit_reason(self) -> Dict:
        """Get statistics by exit reason"""
        reasons = {}
        for e in self.entries:
            if e.exit_reason not in reasons:
                reasons[e.exit_reason] = {'count': 0, 'pnl': 0, 'wins': 0}
            reasons[e.exit_reason]['count'] += 1
            reasons[e.exit_reason]['pnl'] += e.pnl
            if e.pnl > 0:
                reasons[e.exit_reason]['wins'] += 1
        
        # Calculate win rate for each reason
        for reason in reasons:
            count = reasons[reason]['count']
            reasons[reason]['win_rate'] = reasons[reason]['wins'] / count if count > 0 else 0
        
        return reasons
    
    def get_stats_by_hour(self) -> Dict:
        """Get statistics by hour of day"""
        hours = {i: {'trades': 0, 'wins': 0, 'pnl': 0} for i in range(24)}
        
        for e in self.entries:
            hour = datetime.fromisoformat(e.entry_time).hour
            hours[hour]['trades'] += 1
            hours[hour]['pnl'] += e.pnl
            if e.pnl > 0:
                hours[hour]['wins'] += 1
        
        return hours
    
    def get_recent_trades(self, n: int = 10) -> List[JournalEntry]:
        """Get last n trades"""
        return self.entries[-n:] if self.entries else []
    
    def get_streak(self) -> Dict:
        """Get current and best win/loss streaks"""
        if not self.entries:
            return {'current': 0, 'best_win': 0, 'worst_loss': 0}
        
        current_streak = 0
        best_win_streak = 0
        worst_loss_streak = 0
        temp_streak = 0
        last_was_win = None
        
        for e in self.entries:
            is_win = e.pnl > 0
            
            if last_was_win is None:
                temp_streak = 1
            elif is_win == last_was_win:
                temp_streak += 1
            else:
                temp_streak = 1
            
            if is_win:
                best_win_streak = max(best_win_streak, temp_streak)
            else:
                worst_loss_streak = max(worst_loss_streak, temp_streak)
            
            last_was_win = is_win
            current_streak = temp_streak if is_win else -temp_streak
        
        return {
            'current': current_streak,
            'best_win': best_win_streak,
            'worst_loss': worst_loss_streak
        }
    
    def analyze_patterns(self) -> Dict:
        """Analyze trading patterns"""
        if len(self.entries) < 5:
            return {'message': 'ต้องมีอย่างน้อย 5 เทรดเพื่อวิเคราะห์ pattern'}
        
        patterns = {
            'best_market_condition': None,
            'worst_market_condition': None,
            'best_hour': None,
            'worst_hour': None,
            'avg_winning_duration': 0,
            'avg_losing_duration': 0,
            'recommendations': []
        }
        
        # Best/worst by market condition
        by_condition = {}
        for e in self.entries:
            if e.market_condition:
                if e.market_condition not in by_condition:
                    by_condition[e.market_condition] = []
                by_condition[e.market_condition].append(e.pnl)
        
        if by_condition:
            avg_by_condition = {k: sum(v)/len(v) for k, v in by_condition.items()}
            patterns['best_market_condition'] = max(avg_by_condition, key=avg_by_condition.get)
            patterns['worst_market_condition'] = min(avg_by_condition, key=avg_by_condition.get)
        
        # Best/worst hour
        hour_stats = self.get_stats_by_hour()
        profitable_hours = {h: s['pnl'] for h, s in hour_stats.items() if s['trades'] > 0}
        if profitable_hours:
            patterns['best_hour'] = max(profitable_hours, key=profitable_hours.get)
            patterns['worst_hour'] = min(profitable_hours, key=profitable_hours.get)
        
        # Duration analysis
        wins = [e for e in self.entries if e.pnl > 0]
        losses = [e for e in self.entries if e.pnl <= 0]
        
        if wins:
            patterns['avg_winning_duration'] = sum(e.duration_minutes for e in wins) / len(wins)
        if losses:
            patterns['avg_losing_duration'] = sum(e.duration_minutes for e in losses) / len(losses)
        
        # Generate recommendations
        stats = self.get_stats()
        by_side = self.get_stats_by_side()
        
        if stats['win_rate'] < 0.5:
            patterns['recommendations'].append("⚠️ Win rate ต่ำกว่า 50% - ควรเข้าเทรดน้อยลง")
        
        if by_side['long']['win_rate'] > by_side['short']['win_rate'] + 0.1:
            patterns['recommendations'].append("📈 Long ดีกว่า Short - เน้น Long มากขึ้น")
        elif by_side['short']['win_rate'] > by_side['long']['win_rate'] + 0.1:
            patterns['recommendations'].append("📉 Short ดีกว่า Long - เน้น Short มากขึ้น")
        
        if patterns['avg_losing_duration'] > patterns['avg_winning_duration'] * 2:
            patterns['recommendations'].append("⏱️ ถือ losing trades นานเกินไป - ควร cut loss เร็วขึ้น")
        
        return patterns
    
    def get_telegram_summary(self) -> str:
        """Get summary for Telegram"""
        stats = self.get_stats()
        streak = self.get_streak()
        by_side = self.get_stats_by_side()
        
        return f"""📊 <b>Trade Journal Summary</b>

<b>📈 Overall:</b>
• เทรดทั้งหมด: {stats['total_trades']}
• Win Rate: {stats['win_rate']*100:.1f}%
• Total PnL: ${stats['total_pnl']:.2f}
• Profit Factor: {stats['profit_factor']:.2f}

<b>💰 Performance:</b>
• Best Trade: +${stats['best_trade']:.2f}
• Worst Trade: ${stats['worst_trade']:.2f}
• Avg Win: +${stats.get('avg_win', 0):.2f}
• Avg Loss: ${stats.get('avg_loss', 0):.2f}

<b>📊 By Side:</b>
• Long: {by_side['long']['trades']} trades ({by_side['long']['win_rate']*100:.0f}% WR)
• Short: {by_side['short']['trades']} trades ({by_side['short']['win_rate']*100:.0f}% WR)

<b>🔥 Streaks:</b>
• Current: {'+' if streak['current'] > 0 else ''}{streak['current']}
• Best Win Streak: {streak['best_win']}
• Worst Loss Streak: {streak['worst_loss']}

<b>⏱️ Timing:</b>
• Avg Duration: {stats['avg_duration']:.0f} min"""


# For testing
if __name__ == "__main__":
    journal = TradeJournal()
    
    # Add sample trades
    sample_trades = [
        {
            'side': 'long',
            'entry_price': 100000,
            'exit_price': 101000,
            'size': 5,
            'leverage': 50,
            'pnl': 2.5,
            'pnl_pct': 0.01,
            'entry_time': datetime.now() - timedelta(hours=2),
            'exit_time': datetime.now() - timedelta(hours=1),
            'exit_reason': 'TAKE_PROFIT',
            'fees': 0.01
        },
        {
            'side': 'short',
            'entry_price': 101000,
            'exit_price': 101500,
            'size': 5,
            'leverage': 50,
            'pnl': -1.5,
            'pnl_pct': -0.005,
            'entry_time': datetime.now() - timedelta(hours=1),
            'exit_time': datetime.now(),
            'exit_reason': 'STOP_LOSS',
            'fees': 0.01
        }
    ]
    
    for trade in sample_trades:
        journal.add_trade(trade, market_condition='trending')
    
    print(journal.get_telegram_summary())
