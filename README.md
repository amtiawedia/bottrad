# AlphaBot-Scalper V4 🤖

Autonomous AI Trading Bot for BTC/USDT Futures

## 🚀 Quick Start

### Local Run
```bash
# Install dependencies
pip install -r requirements.txt

# Create .env file with your keys
echo "BINANCE_API_KEY=your_key" > .env
echo "BINANCE_SECRET_KEY=your_secret" >> .env
echo "TELEGRAM_BOT_TOKEN=your_bot_token" >> .env
echo "TELEGRAM_CHAT_ID=your_chat_id" >> .env

# Run backtest
python alphabot_v4.py backtest 7

# Run simulation
python alphabot_v4.py sim

# Run live trading
python alphabot_v4.py live
```

## ☁️ Deploy to Railway (24/7)

1. Go to [railway.app](https://railway.app)
2. Sign up with GitHub
3. Click "New Project" → "Deploy from GitHub repo"
4. Select this repo
5. Add Environment Variables:
   - `BINANCE_API_KEY`
   - `BINANCE_SECRET_KEY`
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`
   - `AUTO_TRADE=true`
6. Deploy!

## 📊 Features

- ✅ Multi-agent AI system
- ✅ BTC/USDT Scalping (5m timeframe)
- ✅ 30x Leverage
- ✅ Auto SL/TP
- ✅ Telegram notifications with charts
- ✅ Hourly status updates
- ✅ Daily summaries

## ⚠️ Risk Warning

This bot uses real money. Trade at your own risk.
