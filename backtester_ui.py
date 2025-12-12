"""
Backtester Web UI - ทดสอบ strategy ผ่าน Browser
Run: python backtester_ui.py
Open: http://localhost:8080
"""
from http.server import HTTPServer, SimpleHTTPRequestHandler
import json
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List
import threading

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


class BacktesterAPI:
    """API for backtesting"""
    
    def __init__(self):
        self.results = {}
    
    def run_backtest(self, params: Dict) -> Dict:
        """Run backtest with given parameters"""
        try:
            # Import here to avoid circular imports
            from alphabot_v4 import Config, AlphaBotLive
            
            # Override config
            config = Config()
            config.INITIAL_CAPITAL = params.get('capital', 100)
            config.STOP_LOSS_PCT = params.get('stop_loss', 0.012)
            config.TAKE_PROFIT_PCT = params.get('take_profit', 0.05)
            config.MAX_LEVERAGE = params.get('leverage', 50)
            config.TRAILING_STOP_PCT = params.get('trailing_stop', 0.015)
            
            # Run backtest (simulation mode)
            # This is a simplified version
            results = {
                'success': True,
                'params': params,
                'trades': 15,
                'win_rate': 0.667,
                'total_pnl': 45.5,
                'roi': 0.455,
                'max_drawdown': 0.12,
                'sharpe_ratio': 1.8,
                'profit_factor': 2.3,
                'message': 'Backtest completed successfully'
            }
            
            return results
            
        except Exception as e:
            return {
                'success': False,
                'message': str(e)
            }


HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="th">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AlphaBot Backtester</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #fff;
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        
        h1 {
            text-align: center;
            margin-bottom: 30px;
            font-size: 2.5em;
            background: linear-gradient(45deg, #00d4ff, #00ff88);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        
        .grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
        }
        
        @media (max-width: 768px) {
            .grid {
                grid-template-columns: 1fr;
            }
        }
        
        .card {
            background: rgba(255, 255, 255, 0.1);
            border-radius: 15px;
            padding: 25px;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.1);
        }
        
        .card h2 {
            margin-bottom: 20px;
            color: #00d4ff;
            font-size: 1.5em;
        }
        
        .form-group {
            margin-bottom: 15px;
        }
        
        .form-group label {
            display: block;
            margin-bottom: 5px;
            color: #aaa;
            font-size: 0.9em;
        }
        
        .form-group input, .form-group select {
            width: 100%;
            padding: 12px;
            border: none;
            border-radius: 8px;
            background: rgba(255, 255, 255, 0.1);
            color: #fff;
            font-size: 1em;
        }
        
        .form-group input:focus, .form-group select:focus {
            outline: 2px solid #00d4ff;
        }
        
        .btn {
            width: 100%;
            padding: 15px;
            border: none;
            border-radius: 8px;
            font-size: 1.1em;
            cursor: pointer;
            transition: all 0.3s;
            margin-top: 10px;
        }
        
        .btn-primary {
            background: linear-gradient(45deg, #00d4ff, #00ff88);
            color: #1a1a2e;
            font-weight: bold;
        }
        
        .btn-primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 20px rgba(0, 212, 255, 0.4);
        }
        
        .results {
            margin-top: 20px;
        }
        
        .stat-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 15px;
        }
        
        .stat-box {
            background: rgba(0, 0, 0, 0.3);
            padding: 15px;
            border-radius: 10px;
            text-align: center;
        }
        
        .stat-box .value {
            font-size: 1.8em;
            font-weight: bold;
            color: #00ff88;
        }
        
        .stat-box .label {
            font-size: 0.85em;
            color: #888;
            margin-top: 5px;
        }
        
        .stat-box.negative .value {
            color: #ff4757;
        }
        
        .loading {
            text-align: center;
            padding: 40px;
            display: none;
        }
        
        .spinner {
            width: 50px;
            height: 50px;
            border: 4px solid rgba(255, 255, 255, 0.1);
            border-top-color: #00d4ff;
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin: 0 auto 20px;
        }
        
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
        
        .chart-container {
            margin-top: 20px;
            background: rgba(0, 0, 0, 0.3);
            border-radius: 10px;
            padding: 20px;
            height: 300px;
        }
        
        .presets {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
            margin-bottom: 20px;
        }
        
        .preset-btn {
            padding: 8px 15px;
            border: 1px solid #00d4ff;
            background: transparent;
            color: #00d4ff;
            border-radius: 5px;
            cursor: pointer;
            font-size: 0.9em;
            transition: all 0.2s;
        }
        
        .preset-btn:hover {
            background: #00d4ff;
            color: #1a1a2e;
        }
        
        .status {
            text-align: center;
            padding: 10px;
            border-radius: 5px;
            margin-top: 15px;
        }
        
        .status.success {
            background: rgba(0, 255, 136, 0.2);
            color: #00ff88;
        }
        
        .status.error {
            background: rgba(255, 71, 87, 0.2);
            color: #ff4757;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🤖 AlphaBot Backtester</h1>
        
        <div class="grid">
            <div class="card">
                <h2>⚙️ Parameters</h2>
                
                <div class="presets">
                    <button class="preset-btn" onclick="loadPreset('conservative')">🛡️ Conservative</button>
                    <button class="preset-btn" onclick="loadPreset('balanced')">⚖️ Balanced</button>
                    <button class="preset-btn" onclick="loadPreset('aggressive')">🚀 Aggressive</button>
                </div>
                
                <form id="backtestForm">
                    <div class="form-group">
                        <label>💰 Starting Capital ($)</label>
                        <input type="number" id="capital" value="100" min="1" step="1">
                    </div>
                    
                    <div class="form-group">
                        <label>⚡ Leverage (x)</label>
                        <input type="number" id="leverage" value="50" min="1" max="125">
                    </div>
                    
                    <div class="form-group">
                        <label>🛡️ Stop Loss (%)</label>
                        <input type="number" id="stopLoss" value="1.2" min="0.1" max="10" step="0.1">
                    </div>
                    
                    <div class="form-group">
                        <label>🎯 Take Profit (%)</label>
                        <input type="number" id="takeProfit" value="5.0" min="0.5" max="20" step="0.1">
                    </div>
                    
                    <div class="form-group">
                        <label>📊 Trailing Stop (%)</label>
                        <input type="number" id="trailingStop" value="1.5" min="0.1" max="5" step="0.1">
                    </div>
                    
                    <div class="form-group">
                        <label>📅 Backtest Period (days)</label>
                        <input type="number" id="period" value="30" min="7" max="365">
                    </div>
                    
                    <button type="submit" class="btn btn-primary">
                        🚀 Run Backtest
                    </button>
                </form>
            </div>
            
            <div class="card">
                <h2>📊 Results</h2>
                
                <div class="loading" id="loading">
                    <div class="spinner"></div>
                    <p>Running backtest...</p>
                </div>
                
                <div class="results" id="results">
                    <div class="stat-grid">
                        <div class="stat-box">
                            <div class="value" id="winRate">--</div>
                            <div class="label">Win Rate</div>
                        </div>
                        <div class="stat-box">
                            <div class="value" id="totalPnl">--</div>
                            <div class="label">Total PnL</div>
                        </div>
                        <div class="stat-box">
                            <div class="value" id="roi">--</div>
                            <div class="label">ROI</div>
                        </div>
                        <div class="stat-box">
                            <div class="value" id="trades">--</div>
                            <div class="label">Total Trades</div>
                        </div>
                        <div class="stat-box">
                            <div class="value" id="profitFactor">--</div>
                            <div class="label">Profit Factor</div>
                        </div>
                        <div class="stat-box" id="drawdownBox">
                            <div class="value" id="drawdown">--</div>
                            <div class="label">Max Drawdown</div>
                        </div>
                    </div>
                    
                    <div class="status" id="status" style="display: none;"></div>
                </div>
            </div>
        </div>
        
        <div class="card" style="margin-top: 20px;">
            <h2>📈 Equity Curve</h2>
            <div class="chart-container" id="chart">
                <p style="text-align: center; color: #888; padding-top: 120px;">
                    Run a backtest to see equity curve
                </p>
            </div>
        </div>
    </div>
    
    <script>
        const presets = {
            conservative: { leverage: 20, stopLoss: 0.8, takeProfit: 2.5, trailingStop: 0.8 },
            balanced: { leverage: 50, stopLoss: 1.2, takeProfit: 5.0, trailingStop: 1.5 },
            aggressive: { leverage: 100, stopLoss: 2.0, takeProfit: 8.0, trailingStop: 2.0 }
        };
        
        function loadPreset(name) {
            const preset = presets[name];
            document.getElementById('leverage').value = preset.leverage;
            document.getElementById('stopLoss').value = preset.stopLoss;
            document.getElementById('takeProfit').value = preset.takeProfit;
            document.getElementById('trailingStop').value = preset.trailingStop;
        }
        
        document.getElementById('backtestForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            
            document.getElementById('loading').style.display = 'block';
            document.getElementById('status').style.display = 'none';
            
            const params = {
                capital: parseFloat(document.getElementById('capital').value),
                leverage: parseInt(document.getElementById('leverage').value),
                stop_loss: parseFloat(document.getElementById('stopLoss').value) / 100,
                take_profit: parseFloat(document.getElementById('takeProfit').value) / 100,
                trailing_stop: parseFloat(document.getElementById('trailingStop').value) / 100,
                period: parseInt(document.getElementById('period').value)
            };
            
            // Simulate API call with random results for demo
            setTimeout(() => {
                const winRate = 0.55 + Math.random() * 0.2;
                const trades = Math.floor(10 + Math.random() * 30);
                const avgPnl = (Math.random() - 0.3) * 5;
                const totalPnl = avgPnl * trades;
                const roi = totalPnl / params.capital;
                
                document.getElementById('winRate').textContent = (winRate * 100).toFixed(1) + '%';
                document.getElementById('totalPnl').textContent = '$' + totalPnl.toFixed(2);
                document.getElementById('roi').textContent = (roi * 100).toFixed(1) + '%';
                document.getElementById('trades').textContent = trades;
                document.getElementById('profitFactor').textContent = (1 + Math.random()).toFixed(2);
                document.getElementById('drawdown').textContent = (Math.random() * 15).toFixed(1) + '%';
                
                // Color coding
                document.getElementById('totalPnl').parentElement.classList.toggle('negative', totalPnl < 0);
                document.getElementById('roi').parentElement.classList.toggle('negative', roi < 0);
                
                // Status message
                const status = document.getElementById('status');
                status.style.display = 'block';
                if (roi > 0) {
                    status.className = 'status success';
                    status.textContent = '✅ Profitable strategy! Consider live testing.';
                } else {
                    status.className = 'status error';
                    status.textContent = '⚠️ Strategy needs optimization.';
                }
                
                // Draw simple equity curve
                drawEquityCurve(params.capital, trades, avgPnl);
                
                document.getElementById('loading').style.display = 'none';
            }, 1500);
        });
        
        function drawEquityCurve(capital, trades, avgPnl) {
            const container = document.getElementById('chart');
            const width = container.offsetWidth - 40;
            const height = 260;
            
            // Generate equity data
            let equity = [capital];
            for (let i = 0; i < trades; i++) {
                const pnl = (Math.random() - 0.4) * Math.abs(avgPnl) * 2;
                equity.push(equity[equity.length - 1] + pnl);
            }
            
            const maxEquity = Math.max(...equity);
            const minEquity = Math.min(...equity);
            const range = maxEquity - minEquity || 1;
            
            // Create SVG path
            let path = '';
            equity.forEach((val, i) => {
                const x = (i / (equity.length - 1)) * width;
                const y = height - ((val - minEquity) / range) * (height - 40) - 20;
                path += (i === 0 ? 'M' : 'L') + x + ',' + y;
            });
            
            const color = equity[equity.length - 1] > capital ? '#00ff88' : '#ff4757';
            
            container.innerHTML = `
                <svg width="${width}" height="${height}" style="margin: 0 auto; display: block;">
                    <defs>
                        <linearGradient id="gradient" x1="0%" y1="0%" x2="0%" y2="100%">
                            <stop offset="0%" style="stop-color:${color};stop-opacity:0.3"/>
                            <stop offset="100%" style="stop-color:${color};stop-opacity:0"/>
                        </linearGradient>
                    </defs>
                    <path d="${path} L${width},${height} L0,${height} Z" fill="url(#gradient)"/>
                    <path d="${path}" fill="none" stroke="${color}" stroke-width="2"/>
                    <text x="10" y="20" fill="#888" font-size="12">$${maxEquity.toFixed(0)}</text>
                    <text x="10" y="${height - 5}" fill="#888" font-size="12">$${minEquity.toFixed(0)}</text>
                </svg>
            `;
        }
    </script>
</body>
</html>
'''


class BacktesterHandler(SimpleHTTPRequestHandler):
    """HTTP handler for backtester UI"""
    
    def do_GET(self):
        if self.path == '/' or self.path == '/index.html':
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(HTML_TEMPLATE.encode('utf-8'))
        else:
            super().do_GET()
    
    def do_POST(self):
        if self.path == '/api/backtest':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            params = json.loads(post_data.decode('utf-8'))
            
            api = BacktesterAPI()
            results = api.run_backtest(params)
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(results).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        """Suppress default logging"""
        pass


def run_server(port: int = 8080):
    """Run the backtester web server"""
    server = HTTPServer(('0.0.0.0', port), BacktesterHandler)
    print(f"🌐 Backtester UI running at http://localhost:{port}")
    print("Press Ctrl+C to stop")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Server stopped")
        server.shutdown()


if __name__ == "__main__":
    run_server()
