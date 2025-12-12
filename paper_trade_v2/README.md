# 📝 Paper Trade Bot V2

## 🚀 วิธีใช้

### Windows:
1. ดับเบิ้ลคลิก `START.bat`

### Terminal:
```bash
cd paper_trade_v2
python bot.py
```

---

## ⚙️ ตั้งค่า

แก้ไขใน `bot.py`:

```python
# ยอดเริ่มต้น
BALANCE = 4.50

# Leverage
LEVERAGE = 50

# Stop Loss / Take Profit
SL_PCT = 0.012    # 1.2%
TP_PCT = 0.050    # 5.0%

# จำนวน positions สูงสุด
MAX_POSITIONS = 3

# สแกนทุกกี่วินาที
SCAN_INTERVAL = 30
```

---

## 📊 Features

- ✅ **Paper Trade** - ไม่ใช้เงินจริง
- ✅ **30 เหรียญ** - คัดมาจาก Backtest
- ✅ **Long + Short** - เทรดได้ทั้งสองทาง
- ✅ **บันทึกผล** - `trades.json`

---

## 📁 ไฟล์

```
paper_trade_v2/
├── START.bat      ← ดับเบิ้ลคลิกเพื่อรัน
├── bot.py         ← Bot หลัก
├── trades.json    ← ประวัติการเทรด (สร้างอัตโนมัติ)
└── README.md      ← ไฟล์นี้
```

---

## ❓ FAQ

**Q: ต้องใส่ API Key ไหม?**
A: ไม่จำเป็น แต่ถ้าใส่จะดึงข้อมูลได้เร็วกว่า

**Q: Paper Trade กับ Live ต่างกันยังไง?**
A: Paper Trade ไม่ส่งคำสั่งจริง แค่จำลองการเทรด

**Q: ดูผลลัพธ์ได้ที่ไหน?**
A: ไฟล์ `trades.json` หรือดูบนหน้าจอ

---

⚠️ **หมายเหตุ:** นี่คือ Paper Trade เท่านั้น ไม่ใช้เงินจริง!
