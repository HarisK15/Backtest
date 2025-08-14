# Quant Trading Bot

A quantitative trading bot that implements a Moving Average Crossover strategy with backtesting and live trading capabilities.

## Features

- **Backtesting Engine**: Historical strategy performance analysis
- **Live Trading**: Real-time paper trading simulation
- **Web Interface**: Beautiful dashboard for monitoring and control
- **Risk Management**: Position sizing and stop-loss logic
- **Multiple Data Sources**: Yahoo Finance integration

## Deployment on Railway

### Prerequisites
- Railway account (free tier available)
- GitHub repository

### Steps

1. **Push to GitHub**
   ```bash
   git add .
   git commit -m "Add web interface for Railway deployment"
   git push origin main
   ```

2. **Deploy on Railway**
   - Go to [Railway.app](https://railway.app)
   - Click "New Project"
   - Select "Deploy from GitHub repo"
   - Choose your repository
   - Railway will automatically detect the Python app and deploy

3. **Environment Variables** (Optional)
   - `PORT`: Railway sets this automatically
   - `ALPACA_API_KEY`: For live Alpaca trading (optional)
   - `ALPACA_API_SECRET`: For live Alpaca trading (optional)

### Files for Railway
- `app.py` - Main Flask application
- `Procfile` - Tells Railway how to start the app
- `requirements.txt` - Python dependencies
- `runtime.txt` - Python version specification

## Local Development

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the app
python app.py

# Open http://localhost:8080
```

## Usage

### Web Interface
- **Start Trading**: Begin live paper trading
- **Stop Trading**: Halt the trading bot
- **Run Backtest**: Analyze historical performance
- **Monitor**: View real-time trading activity

### CLI Commands
```bash
# Backtesting
python3 -m cli backtest --symbol AAPL --start 2022-01-01 --end 2024-12-31

# Live Trading
python3 -m cli live --symbol AAPL --broker paper --poll-secs 5
```

## Strategy

**Moving Average Crossover**
- Fast MA (20 periods) vs Slow MA (50 periods)
- Golden Cross (fast > slow) = BUY signal
- Death Cross (fast < slow) = SELL signal
- Risk management with stop-losses and take-profits

## Architecture

- **Data Layer**: Yahoo Finance provider
- **Strategy Layer**: Moving Average Crossover
- **Risk Layer**: Position sizing and stop management
- **Execution Layer**: Paper trading broker
- **Web Layer**: Flask dashboard

## License

MIT License - Use at your own risk for educational purposes only.
