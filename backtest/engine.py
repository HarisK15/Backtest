from __future__ import annotations
from datetime import datetime
import pandas as pd
from core.types import Order, Side
from risk.metrics import Risk

class BacktestResult:
    def __init__(self, trades, equity_curve: pd.Series, metrics: dict):
        self.trades = trades
        self.equity_curve = equity_curve
        self.metrics = metrics

class Backtester:
    def __init__(self, data: pd.DataFrame, strategy, initial_cash: float, broker, risk_manager):
        self.df = data.sort_index().copy()
        self.strategy = strategy
        self.cash = float(initial_cash)
        self.broker = broker
        self.risk = risk_manager

    def run(self, symbol: str, benchmark: pd.Series | None = None) -> BacktestResult:
        px = self.df["close"].astype(float)
        sig = self.strategy.generate_signals(self.df)
        ret = px.pct_change()
        roll_vol = ret.rolling(20).std().bfill()
        pos = self.broker.position(symbol)
        equity_curve = []
        trades = []
        stop = take = None

        for ts in sig.index:
            s = int(sig.loc[ts].iloc[0])
            price = float(px.loc[ts].iloc[0])
            # Check stop loss / take profit
            if pos.qty != 0 and stop is not None and take is not None:
                if (price <= stop and pos.qty > 0) or (price >= take and pos.qty > 0):
                    qty = abs(pos.qty)
                    o = Order(symbol, Side.SELL, qty, price, ts, tag="exit")
                    fill = self.broker.submit(o, ref_price=price)
                    self.cash += fill.order.qty * fill.fill_price - fill.commission
                    trades.append(fill)
                    pos = self.broker.position(symbol)
                    stop = take = None

            if s > 0 and pos.qty <= 0:
                qty = self.risk.position_size(self.cash + pos.qty*price, price, float(roll_vol.loc[ts].iloc[0]))
                if qty > 0:
                    o = Order(symbol, Side.BUY, qty, price, ts, tag="entry")
                    fill = self.broker.submit(o, ref_price=price)
                    self.cash -= fill.order.qty * fill.fill_price + fill.commission
                    trades.append(fill)
                    pos = self.broker.position(symbol)
                    stop, take = self.risk.stop_levels(fill.fill_price)
            elif s < 0 and pos.qty > 0:
                qty = abs(pos.qty)
                o = Order(symbol, Side.SELL, qty, price, ts, tag="flip/flat")
                fill = self.broker.submit(o, ref_price=price)
                self.cash += fill.order.qty * fill.fill_price - fill.commission
                trades.append(fill)
                pos = self.broker.position(symbol)
                stop = take = None

            equity_curve.append((ts, self.cash + pos.qty*price))

        eq = pd.Series(dict(equity_curve)).sort_index()
        rets = Risk.daily_returns(eq)
        metrics = {
            "CAGR": (eq.iloc[-1] / eq.iloc[0]) ** (252/max(len(rets),1)) - 1 if len(eq) > 1 else float("nan"),
            "Sharpe": Risk.sharpe(rets),
            "Sortino": Risk.sortino(rets),
            "Volatility": Risk.volatility(rets),
            "MaxDrawdown": Risk.max_drawdown(eq),
            "Calmar": Risk.calmar(eq),
            "VaR_95": Risk.historical_var(rets, 0.95),
        }
        if benchmark is not None:
            metrics["Beta"] = Risk.beta(rets, benchmark.pct_change().dropna())
        return BacktestResult(trades, eq, metrics)