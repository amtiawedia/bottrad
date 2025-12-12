#!/usr/bin/env python3
"""
📊 Paper Trade Status Checker
ดูสถานะบอทจำลอง - ออเดอร์ที่เปิดอยู่ และ กำไร/ขาดทุน
"""

import json
import os
from datetime import datetime

STATUS_FILE = 'paper_trade_status.json'

def load_status():
    """โหลดสถานะจากไฟล์"""
    if os.path.exists(STATUS_FILE):
        with open(STATUS_FILE, 'r') as f:
            return json.load(f)
    return None

def display_status():
    """แสดงสถานะบอท"""
    status = load_status()
    
    print("\n" + "="*60)
    print("📊 PAPER TRADE STATUS")
    print("="*60)
    
    if not status:
        print("\n❌ ไม่พบไฟล์สถานะ")
        print("   บอทอาจยังไม่ได้เริ่มทำงาน หรือยังไม่มีการเทรด")
        print("\n💡 รันบอทด้วยคำสั่ง: python paper_bot_full.py")
        return
    
    # แสดงข้อมูลทั่วไป
    print(f"\n⏰ อัพเดทล่าสุด: {status.get('last_update', 'N/A')}")
    print(f"💰 ทุนเริ่มต้น: ${status.get('initial_balance', 0):.2f}")
    print(f"💵 ยอดปัจจุบัน: ${status.get('current_balance', 0):.2f}")
    
    # คำนวณกำไร/ขาดทุน
    initial = status.get('initial_balance', 0)
    current = status.get('current_balance', 0)
    pnl = current - initial
    pnl_pct = (pnl / initial * 100) if initial > 0 else 0
    
    if pnl >= 0:
        print(f"📈 กำไร: +${pnl:.4f} (+{pnl_pct:.2f}%)")
    else:
        print(f"📉 ขาดทุน: ${pnl:.4f} ({pnl_pct:.2f}%)")
    
    # สถิติการเทรด
    print("\n" + "-"*60)
    print("📈 สถิติการเทรด")
    print("-"*60)
    print(f"   🔢 เทรดทั้งหมด: {status.get('total_trades', 0)}")
    print(f"   ✅ ชนะ: {status.get('wins', 0)}")
    print(f"   ❌ แพ้: {status.get('losses', 0)}")
    
    total = status.get('total_trades', 0)
    wins = status.get('wins', 0)
    win_rate = (wins / total * 100) if total > 0 else 0
    print(f"   🎯 Win Rate: {win_rate:.1f}%")
    
    # ออเดอร์ที่เปิดอยู่
    positions = status.get('open_positions', [])
    print("\n" + "-"*60)
    print(f"📂 ออเดอร์ที่เปิดอยู่: {len(positions)} รายการ")
    print("-"*60)
    
    if positions:
        for i, pos in enumerate(positions, 1):
            side_emoji = "🟢 LONG" if pos.get('side') == 'long' else "🔴 SHORT"
            symbol = pos.get('symbol', 'N/A')
            entry = pos.get('entry_price', 0)
            current_price = pos.get('current_price', entry)
            sl = pos.get('sl', 0)
            tp = pos.get('tp', 0)
            
            # คำนวณ PnL ปัจจุบัน
            if pos.get('side') == 'long':
                unrealized_pnl = (current_price - entry) / entry * 100 * 50  # 50x leverage
            else:
                unrealized_pnl = (entry - current_price) / entry * 100 * 50
            
            pnl_emoji = "📈" if unrealized_pnl >= 0 else "📉"
            
            print(f"\n   {i}. {symbol} {side_emoji}")
            print(f"      💵 Entry: ${entry:.4f}")
            print(f"      📍 ราคาปัจจุบัน: ${current_price:.4f}")
            print(f"      🛑 SL: ${sl:.4f}")
            print(f"      🎯 TP: ${tp:.4f}")
            print(f"      {pnl_emoji} Unrealized PnL: {unrealized_pnl:+.2f}%")
    else:
        print("   ไม่มีออเดอร์ที่เปิดอยู่")
    
    # ประวัติเทรดล่าสุด
    history = status.get('trade_history', [])
    if history:
        print("\n" + "-"*60)
        print("📜 ประวัติเทรดล่าสุด (5 รายการ)")
        print("-"*60)
        
        for trade in history[-5:]:
            side_emoji = "🟢" if trade.get('side') == 'long' else "🔴"
            result_emoji = "✅" if trade.get('pnl', 0) > 0 else "❌"
            print(f"   {side_emoji} {trade.get('symbol', 'N/A')} | {result_emoji} {trade.get('pnl', 0):+.2f}% | {trade.get('exit_reason', 'N/A')} | {trade.get('time', 'N/A')}")
    
    print("\n" + "="*60)
    print("💡 รัน paper_bot_full.py เพื่อเริ่มเทรดจำลอง")
    print("="*60 + "\n")

if __name__ == "__main__":
    display_status()
