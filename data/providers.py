from __future__ import annotations
from datetime import datetime, timezone
import os
import pandas as pd
import numpy as np

try:
    import yfinance as yf
except Exception:
    yf = None

class DataProvider:
    def history(self, symbol: str, start: str, end: str, interval: str = "1d") -> pd.DataFrame:
        raise NotImplementedError
    def latest(self, symbol: str) -> dict:
        raise NotImplementedError

class YFinanceProvider(DataProvider):
    def history(self, symbol: str, start: str, end: str, interval: str = "1d") -> pd.DataFrame:
        if yf is None:
            raise RuntimeError("yfinance not installed")
        df = yf.download(symbol, start=start, end=end, interval=interval, auto_adjust=True, progress=False)
        df = df.rename(columns={"Open":"open","High":"high","Low":"low","Close":"close","Adj Close":"adj_close","Volume":"volume"})
        df.index = pd.to_datetime(df.index, utc=True)
        return df[["open","high","low","close","volume"]]
    def latest(self, symbol: str) -> dict:
        if yf is None:
            raise RuntimeError("yfinance not installed")
        last = yf.Ticker(symbol).history(period="1d").tail(1)["Close"].iloc[0]
        return {"price": float(last), "ts": datetime.now(timezone.utc)}

# --- True real-time via Alpaca Market Data v2 (websocket) ---
# Notes:
# - Requires: ALPACA_API_KEY, ALPACA_API_SECRET env vars.
# - Provides an async iterator of trades; a thin wrapper is included for convenience.
import asyncio
import json
import websockets

class AlpacaRealtime:
    def __init__(self, symbols: list[str]):
        self.base_ws = os.getenv("ALPACA_DATA_WS", "wss://stream.data.alpaca.markets/v2/sip")
        self.key = os.getenv("ALPACA_API_KEY")
        self.secret = os.getenv("ALPACA_API_SECRET")
        if not (self.key and self.secret):
            raise RuntimeError("Set ALPACA_API_KEY and ALPACA_API_SECRET")
        self.symbols = symbols

    async def stream_trades(self):
        async with websockets.connect(self.base_ws, ping_interval=15, ping_timeout=20) as ws:
            await ws.send(json.dumps({"action": "auth", "key": self.key, "secret": self.secret}))
            await ws.send(json.dumps({"action": "subscribe", "trades": self.symbols}))
            async for msg in ws:
                data = json.loads(msg)
                # Each trade event: {"T":"t","S":"AAPL","p":price,"t":timestamp,...}
                if isinstance(data, list):
                    for ev in data:
                        if ev.get("T") == "t":
                            yield {"symbol": ev["S"], "price": float(ev["p"]), "ts": datetime.fromisoformat(ev["t"].replace("Z","+00:00"))}