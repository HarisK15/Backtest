from __future__ import annotations
import math
from datetime import datetime, timedelta, timezone
import pandas as pd
import numpy as np

# Import our modules
from ..strategy.sma_cross import MovingAverageCross
from ..backtest.engine import Backtester
from ..risk.manager import RiskManager, RiskConfig
from ..brokers.paper import PaperBroker
from ..charts.report import Report

OK = "\x1b[92mOK\x1b[0m"; FAIL = "\x1b[91mFAIL\x1b[0m"

def _fake_price_series(n=200, seed=42):
    rng = np.random.default_rng(seed)
    rets = rng.normal(0, 0.01, size=n)
    px = 100 * (1 + pd.Series(rets)).cumprod()
    idx = pd.date_range(datetime.now(timezone.utc) - timedelta(days=n), periods=n, freq="D", tz=timezone.utc)
    df = pd.DataFrame({"open":px, "high":px*1.01, "low":px*0.99, "close":px, "volume":1_000}, index=idx)
    return df

def test_strategy_signals():
    df = _fake_price_series()
    strat = MovingAverageCross(5, 20)
    sig = strat.generate_signals(df)
    assert set(sig.dropna().unique()).issubset({-1,0,1}), "Signals must be in {-1,0,1}"
    print("test_strategy_signals:", OK)


def test_backtester_runs_without_matplotlib():
    df = _fake_price_series()
    bt = Backtester(df, MovingAverageCross(5,20), 10_000.0, PaperBroker(), RiskManager(RiskConfig()))
    res = bt.run("TEST")
    assert isinstance(res.metrics, dict) and len(res.equity_curve) == len(df), "Backtester output shape mismatch"
    # Should handle missing matplotlib gracefully
    try:
        paths = Report.equity_and_drawdown(res.equity_curve, "report_TEST.png")
        assert isinstance(paths, list), "Report should return list of file paths or []"
    except Exception as e:
        raise AssertionError(f"Report generation should not raise, got: {e}")
    print("test_backtester_runs_without_matplotlib:", OK)


def test_risk_metrics_sanity():
    df = _fake_price_series()
    eq = (df["close"] / df["close"].iloc[0]) * 10_000
    from ..risk.metrics import Risk
    rets = Risk.daily_returns(eq)
    _ = Risk.sharpe(rets); _ = Risk.sortino(rets); _ = Risk.volatility(rets)
    _ = Risk.max_drawdown(eq); _ = Risk.calmar(eq); _ = Risk.historical_var(rets)
    print("test_risk_metrics_sanity:", OK)

if __name__ == "__main__":
    try:
        test_strategy_signals()
        test_backtester_runs_without_matplotlib()
        test_risk_metrics_sanity()
        print("\nAll tests:", OK)
    except AssertionError as e:
        print("\nTests:", FAIL, str(e))
        raise