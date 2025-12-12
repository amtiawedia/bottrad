# 🤖 AlphaBot Trading System

## 📁 โครงสร้างไฟล์

```
bottrad/
├── 🚀 ไฟล์รันหลัก (ดับเบิ้ลคลิกใน Windows)
│   ├── RUN_PAPER_TRADE.bat    ← 📝 Paper Trade (แนะนำเริ่มตรงนี้!)
│   ├── RUN_LIVE_BOT.bat       ← ⚠️ Live Trading (ใช้เงินจริง)
│   └── RUN_BACKTEST.bat       ← 📊 Backtest ทดสอบ Strategy
│
├── 📂 bots/                   ← โฟลเดอร์เก็บ Bot
│   └── paper_trade_bot.py     ← Paper Trade Bot (30 เหรียญ)
│
├── 📂 ไฟล์หลัก
│   ├── alphabot_v4.py         ← AlphaBot V4 (ตัวเต็ม)
│   ├── backtester_ui.py       ← Backtest UI
│   ├── trade_journal.py       ← Trade Journal
│   ├── multi_coin.py          ← Multi-Coin Scanner
│   └── ml_model.py            ← ML Model
│
├── 📂 ตั้งค่า
│   ├── .env                   ← API Keys (ต้องสร้างเอง!)
│   ├── .env.example           ← ตัวอย่าง .env
│   └── requirements.txt       ← Python packages
│
└── 📂 ผลลัพธ์
    ├── paper_trades.json      ← ประวัติ Paper Trade
    └── bot.log                ← Log files
```

---

## 🚀 วิธีใช้งาน

### 1️⃣ ติดตั้ง Python (ครั้งแรก)
1. ดาวน์โหลด Python 3.10+ จาก https://www.python.org/downloads/
2. ติดตั้ง และ ✅ เลือก "Add Python to PATH"

### 2️⃣ ติดตั้ง Packages (ครั้งแรก)
เปิด Command Prompt แล้วรัน:
```bash
cd path/to/bottrad
pip install -r requirements.txt
```

### 3️⃣ ตั้งค่า API Keys
1. Copy `.env.example` เป็น `.env`
2. ใส่ API Keys ของคุณ:
```
BINANCE_API_KEY=your_api_key_here
BINANCE_SECRET_KEY=your_secret_key_here
TELEGRAM_BOT_TOKEN=your_telegram_token
TELEGRAM_CHAT_ID=your_chat_id
```

### 4️⃣ เริ่มใช้งาน
**ดับเบิ้ลคลิกไฟล์ .bat ที่ต้องการ:**

| ไฟล์ | คำอธิบาย | ความเสี่ยง |
|------|---------|-----------|
| `RUN_PAPER_TRADE.bat` | Paper Trade 30 เหรียญ | ✅ ไม่มี |
| `RUN_BACKTEST.bat` | ทดสอบ Strategy | ✅ ไม่มี |
| `RUN_LIVE_BOT.bat` | เทรดจริง | ⚠️ เสียเงินได้! |

---

## 📝 Paper Trade Bot

**แนะนำเริ่มที่นี่ก่อน!**

### Features:
- ✅ สแกน **30 เหรียญ** ที่ดีที่สุดจาก Backtest
- ✅ เทรดทั้ง **Long** และ **Short**
- ✅ **ไม่ใช้เงินจริง** - ปลอดภัย 100%
- ✅ บันทึกผลลง `paper_trades.json`

### Settings (แก้ไขใน `bots/paper_trade_bot.py`):
```python
INITIAL_BALANCE = 4.50      # ยอดเริ่มต้น
LEVERAGE = 50               # Leverage
SL_PCT = 0.012              # Stop Loss 1.2%
TP_PCT = 0.050              # Take Profit 5.0%
MAX_POSITIONS = 3           # Max positions พร้อมกัน
```

---

## ⚠️ Live Trading Bot

**ใช้เงินจริง! ระวัง!**

### ก่อนใช้:
1. ✅ ทดสอบ Paper Trade ก่อน
2. ✅ เข้าใจความเสี่ยง
3. ✅ API Key ต้องมี **Futures Permission**
4. ✅ ใช้เงินที่พร้อมจะเสีย

### API Key Setup (Binance):
1. ไปที่ https://www.binance.com/en/my/settings/api-management
2. สร้าง API Key ใหม่
3. ✅ Enable **Futures**
4. ✅ Enable **IP Restriction** (แนะนำ)

---

## 📊 Strategy

Bot ใช้ Strategy ดังนี้:

### Entry Conditions:

**LONG:**
- EMA(20) > EMA(50) (Uptrend)
- ADX > 30 (Strong trend)
- EMA(3) > EMA(8) (Momentum)
- MACD Histogram > 0
- RSI 45-70

**SHORT:**
- EMA(20) < EMA(50) (Downtrend)
- ADX > 30 (Strong trend)
- EMA(3) < EMA(8) (Momentum)
- MACD Histogram < 0
- RSI 30-55

### Risk Management:
- Stop Loss: 1.2%
- Take Profit: 5.0%
- Leverage: 50x
- Risk/Reward: 1:4.17

---

## 🎯 เป้าหมาย

| ระยะเวลา | เป้าหมาย | จาก $4.50 |
|----------|---------|-----------|
| 1 สัปดาห์ | +50% | $6.75 |
| 2 สัปดาห์ | +150% | $11.25 |
| 1 เดือน | +1000% | $50+ |

⚠️ **ไม่รับประกัน** - Crypto มีความเสี่ยงสูง!

---

## ❓ FAQ

### Q: Paper Trade ต่างจาก Live ยังไง?
A: Paper Trade ไม่ส่งคำสั่งจริงไป Binance แค่จำลองการเทรด

### Q: API Key Error?
A: ตรวจสอบว่า API Key มี Permission "Futures" และ IP ถูกต้อง

### Q: Bot ไม่เทรด?
A: รอสัญญาณที่ตรงเงื่อนไข - Strategy ค่อนข้างเข้มงวด

### Q: แก้ไขเหรียญที่จะเทรด?
A: แก้ไข `COINS` list ใน `bots/paper_trade_bot.py`

---

## 📞 Support

- Telegram: พิมพ์ /help ใน bot
- GitHub: Open issue

---

**⚠️ DISCLAIMER:** Trading cryptocurrencies involves substantial risk. Only trade with money you can afford to lose. Past performance does not guarantee future results.
