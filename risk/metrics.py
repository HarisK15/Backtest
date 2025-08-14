from __future__ import annotations
import numpy as np
import pandas as pd

class Risk:
    @staticmethod
    def daily_returns(equity: pd.Series) -> pd.Series:
        return equity.pct_change().dropna()
    @staticmethod
    def sharpe(returns: pd.Series, rf: float = 0.0, periods: int = 252) -> float:
        if len(returns) == 0:
            return float("nan")
        ex = returns - rf/periods
        denom = ex.std(ddof=1)
        return float(np.sqrt(periods) * ex.mean() / (denom if denom else 1e-12))
    @staticmethod
    def sortino(returns: pd.Series, rf: float = 0.0, periods: int = 252) -> float:
        if len(returns) == 0:
            return float("nan")
        ex = returns - rf/periods
        downside = ex[ex < 0]
        denom = downside.std(ddof=1)
        return float(np.sqrt(periods) * ex.mean() / (denom if denom else 1e-12))
    @staticmethod
    def volatility(returns: pd.Series, periods: int = 252) -> float:
        return float(returns.std(ddof=1) * np.sqrt(periods)) if len(returns) else float("nan")
    @staticmethod
    def max_drawdown(equity: pd.Series) -> float:
        if len(equity) == 0:
            return float("nan")
        cummax = equity.cummax()
        dd = equity / cummax - 1.0
        return float(dd.min())
    @staticmethod
    def calmar(equity: pd.Series, periods: int = 252) -> float:
        if len(equity) < 2:
            return float("nan")
        returns = Risk.daily_returns(equity)
        mdd = abs(Risk.max_drawdown(equity)) + 1e-12
        cagr = (equity.iloc[-1] / equity.iloc[0]) ** (periods/len(returns)) - 1
        return float(cagr / mdd)
    @staticmethod
    def beta(returns: pd.Series, benchmark: pd.Series) -> float:
        aligned = pd.concat([returns, benchmark], axis=1).dropna()
        if aligned.shape[0] < 3:
            return float("nan")
        cov = np.cov(aligned.iloc[:,0], aligned.iloc[:,1])[0,1]
        var_m = np.var(aligned.iloc[:,1]) + 1e-12
        return float(cov / var_m)
    @staticmethod
    def historical_var(returns: pd.Series, level: float = 0.95) -> float:
        return float(np.percentile(returns, (1-level)*100)) if len(returns) else float("nan")