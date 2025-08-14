from __future__ import annotations
import pandas as pd

class MovingAverageCross:
    def __init__(self, fast: int = 20, slow: int = 50):
        self.fast = int(fast); self.slow = int(slow)
        if self.fast <= 1 or self.slow <= 2 or self.fast >= self.slow:
            raise ValueError("Require 1 < fast < slow")
    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        px = df["close"].astype(float)
        fast = px.rolling(self.fast, min_periods=self.fast).mean()
        slow = px.rolling(self.slow, min_periods=self.slow).mean()
        raw = (fast > slow).astype(int) - (fast < slow).astype(int)
        sig = raw.ffill().fillna(0)
        return sig