from flask import Flask, render_template_string, request, jsonify
import threading
import time
from datetime import datetime
import pandas as pd
import os

# Import your existing modules
from data.providers import YFinanceProvider
from strategy.sma_cross import MovingAverageCross
from risk.manager import RiskManager, RiskConfig
from brokers.paper import PaperBroker
from backtest.engine import Backtester

app = Flask(__name__)

# Global variables for the trading bot
trading_bot = None
bot_status = "stopped"
bot_thread = None
trading_history = []

# HTML template for the web interface
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Quant Trading Bot</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .header { text-align: center; margin-bottom: 30px; }
        .status { padding: 10px; border-radius: 5px; margin: 10px 0; }
        .status.running { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
        .status.stopped { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
        .controls { margin: 20px 0; }
        button { padding: 10px 20px; margin: 5px; border: none; border-radius: 5px; cursor: pointer; }
        .btn-start { background: #28a745; color: white; }
        .btn-stop { background: #dc3545; color: white; }
        .btn-backtest { background: #007bff; color: white; }
        .form-group { margin: 15px 0; }
        label { display: inline-block; width: 120px; }
        input { padding: 8px; border: 1px solid #ddd; border-radius: 4px; }
        .history { margin-top: 30px; }
        .trade { background: #f8f9fa; padding: 10px; margin: 5px 0; border-radius: 4px; border-left: 4px solid #007bff; }
        .metrics { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin: 20px 0; }
        .metric { background: #e9ecef; padding: 15px; border-radius: 5px; text-align: center; }
        .metric-value { font-size: 24px; font-weight: bold; color: #007bff; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 Quant Trading Bot</h1>
            <p>Automated trading with Moving Average Crossover Strategy</p>
        </div>
        
        <div class="status {{ bot_status }}">
            <strong>Status:</strong> {{ bot_status.upper() }}
        </div>
        
        <div class="controls">
            <form method="POST" action="/start" style="display: inline;">
                <div class="form-group">
                    <label>Symbol:</label>
                    <input type="text" name="symbol" value="AAPL" required>
                </div>
                <div class="form-group">
                    <label>Poll Interval (sec):</label>
                    <input type="number" name="poll_secs" value="5" min="1" max="60" required>
                </div>
                <button type="submit" class="btn-start">🚀 Start Trading</button>
            </form>
            
            <form method="POST" action="/stop" style="display: inline;">
                <button type="submit" class="btn-stop">⏹️ Stop Trading</button>
            </form>
        </div>
        
        <div class="controls">
            <form method="POST" action="/backtest">
                <div class="form-group">
                    <label>Symbol:</label>
                    <input type="text" name="symbol" value="AAPL" required>
                </div>
                <div class="form-group">
                    <label>Start Date:</label>
                    <input type="date" name="start" value="2022-01-01" required>
                </div>
                <div class="form-group">
                    <label>End Date:</label>
                    <input type="date" name="end" value="2024-12-31" required>
                </div>
                <button type="submit" class="btn-backtest">📊 Run Backtest</button>
            </form>
        </div>
        
        {% if backtest_results %}
        <div class="metrics">
            {% for key, value in backtest_results.items() %}
            <div class="metric">
                <div class="metric-value">{{ "%.4f"|format(value) if value is number else value }}</div>
                <div>{{ key }}</div>
            </div>
            {% endfor %}
        </div>
        {% endif %}
        
        <div class="history">
            <h3>📈 Trading History</h3>
            {% if trading_history %}
                {% for trade in trading_history[-10:] %}
                <div class="trade">
                    <strong>{{ trade.timestamp }}</strong> - {{ trade.action }} {{ trade.quantity }} {{ trade.symbol }} @ ${{ "%.2f"|format(trade.price) }}
                </div>
                {% endfor %}
            {% else %}
                <p>No trading activity yet.</p>
            {% endif %}
        </div>
    </div>
    
    <script>
        // Auto-refresh every 5 seconds if bot is running
        {% if bot_status == 'running' %}
        setTimeout(() => location.reload(), 5000);
        {% endif %}
    </script>
</body>
</html>
"""

class TradingBot:
    def __init__(self, symbol, poll_secs):
        self.symbol = symbol
        self.poll_secs = poll_secs
        self.running = False
        self.data_provider = YFinanceProvider()
        self.strategy = MovingAverageCross(20, 50)
        self.risk_manager = RiskManager(RiskConfig())
        self.broker = PaperBroker()
        self.position = self.broker.position(symbol)
        self.history = pd.DataFrame(columns=["open","high","low","close","volume"]).astype(float)
        
    def update_history(self, price, ts):
        row = pd.DataFrame({
            "open": [price], "high": [price], "low": [price], 
            "close": [price], "volume": [float("nan")]
        }, index=[pd.to_datetime(ts)])
        self.history = pd.concat([self.history, row]).tail(5000)
        
    def run(self):
        global trading_history, bot_status
        bot_status = "running"
        
        while self.running:
            try:
                # Get latest price
                tick = self.data_provider.latest(self.symbol)
                price = float(tick["price"])
                ts = tick["ts"]
                
                # Update history
                self.update_history(price, ts)
                
                # Generate signals
                if len(self.history) > 50:  # Need enough data
                    sig = self.strategy.generate_signals(self.history)
                    current = int(sig.iloc[-1]) if len(sig) else 0
                    
                    # Trading logic
                    if current > 0 and self.position.qty <= 0:
                        # Buy signal
                        qty = max(1, self.risk_manager.position_size(10000.0, price, 0.02))
                        fill = self.broker.submit(
                            type('Order', (), {
                                'symbol': self.symbol, 'side': type('Side', (), {'BUY': 'BUY'})().BUY,
                                'qty': qty, 'price': None, 'ts': ts, 'tag': 'web-entry'
                            })(),
                            ref_price=price
                        )
                        
                        trading_history.append(type('Trade', (), {
                            'timestamp': ts.strftime('%Y-%m-%d %H:%M:%S'),
                            'action': 'BUY',
                            'quantity': qty,
                            'symbol': self.symbol,
                            'price': price
                        })())
                        
                        print(f"[Web] BUY {qty} {self.symbol} @ {price}")
                        
                    elif current < 0 and self.position.qty > 0:
                        # Sell signal
                        qty = abs(self.position.qty)
                        fill = self.broker.submit(
                            type('Order', (), {
                                'symbol': self.symbol, 'side': type('Side', (), {'SELL': 'SELL'})().SELL,
                                'qty': qty, 'price': None, 'ts': ts, 'tag': 'web-exit'
                            })(),
                            ref_price=price
                        )
                        
                        trading_history.append(type('Trade', (), {
                            'timestamp': ts.strftime('%Y-%m-%d %H:%M:%S'),
                            'action': 'SELL',
                            'quantity': qty,
                            'symbol': self.symbol,
                            'price': price
                        })())
                        
                        print(f"[Web] SELL {qty} {self.symbol} @ {price}")
                
                self.position = self.broker.position(self.symbol)
                time.sleep(self.poll_secs)
                
            except Exception as e:
                print(f"Error in trading bot: {e}")
                time.sleep(self.poll_secs)
        
        bot_status = "stopped"

@app.route('/')
def home():
    global bot_status, trading_history, backtest_results
    return render_template_string(HTML_TEMPLATE, 
                                bot_status=bot_status, 
                                trading_history=trading_history,
                                backtest_results=getattr(app, 'backtest_results', None))

@app.route('/start', methods=['POST'])
def start_bot():
    global trading_bot, bot_thread, bot_status
    
    if bot_status == "running":
        return jsonify({"status": "error", "message": "Bot is already running"})
    
    symbol = request.form.get('symbol', 'AAPL').upper()
    poll_secs = int(request.form.get('poll_secs', 5))
    
    trading_bot = TradingBot(symbol, poll_secs)
    trading_bot.running = True
    bot_thread = threading.Thread(target=trading_bot.run)
    bot_thread.daemon = True
    bot_thread.start()
    
    return jsonify({"status": "success", "message": f"Started trading {symbol}"})

@app.route('/stop', methods=['POST'])
def stop_bot():
    global trading_bot, bot_status
    
    if trading_bot:
        trading_bot.running = False
        bot_status = "stopped"
        return jsonify({"status": "success", "message": "Stopped trading bot"})
    
    return jsonify({"status": "error", "message": "No bot running"})

@app.route('/backtest', methods=['POST'])
def run_backtest():
    global backtest_results
    
    symbol = request.form.get('symbol', 'AAPL').upper()
    start_date = request.form.get('start', '2022-01-01')
    end_date = request.form.get('end', '2024-12-31')
    
    try:
        provider = YFinanceProvider()
        df = provider.history(symbol, start_date, end_date)
        strat = MovingAverageCross(20, 50)
        risk = RiskManager(RiskConfig())
        broker = PaperBroker()
        bt = Backtester(df, strat, 100000, broker, risk)
        res = bt.run(symbol)
        
        app.backtest_results = res.metrics
        return jsonify({"status": "success", "message": "Backtest completed", "results": res.metrics})
        
    except Exception as e:
        return jsonify({"status": "error", "message": f"Backtest failed: {str(e)}"})

@app.route('/health')
def health():
    return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
