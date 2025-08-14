from __future__ import annotations
import asyncio
from datetime import datetime
import pandas as pd
from core.types import Order, Side

class LiveTrader:
    def __init__(self, data_provider, broker, strategy, risk_manager):
        self.data = data_provider
        self.broker = broker
        self.strategy = strategy
        self.risk = risk_manager
        self.hist = pd.DataFrame(columns=["open","high","low","close","volume"]).astype(float)
        self.pos = None
        self.stop = None
        self.take = None

    def _update_hist(self, price: float, ts: datetime):
        row = pd.DataFrame({"open":[price],"high":[price],"low":[price],"close":[price],"volume":[float("nan")]}, index=[pd.to_datetime(ts)])
        self.hist = pd.concat([self.hist, row]).tail(5000)

    async def run_websocket(self, symbol: str, trade_async_iter):
        print(f"[Live] Websocket trading for {symbol}")
        self.pos = self.broker.position(symbol)
        async for tick in trade_async_iter:
            if tick.get("symbol") != symbol:
                continue
            price = float(tick["price"]); ts = tick["ts"]
            self._update_hist(price, ts)

            sig = self.strategy.generate_signals(self.hist)
            current = int(sig.iloc[-1]) if len(sig) else 0
            rets = self.hist["close"].pct_change().dropna()
            rolling_vol = rets.tail(120).std() if len(rets) > 10 else 0.0

            # Stops
            if self.pos.qty != 0 and self.stop is not None and self.take is not None:
                if (price <= self.stop and self.pos.qty > 0) or (price >= self.take and self.pos.qty > 0):
                    qty = abs(self.pos.qty)
                    fill = self.broker.submit(Order(symbol, Side.SELL, qty, None, ts, tag="live-exit"), ref_price=price)
                    print(f"[Live] EXIT {qty} {symbol} @ {fill.fill_price}")
                    self.pos = self.broker.position(symbol)
                    self.stop = self.take = None

            if current > 0 and self.pos.qty <= 0:
                qty = max(1, self.risk.position_size(10000.0, price, rolling_vol))  # demo equity estimate
                fill = self.broker.submit(Order(symbol, Side.BUY, qty, None, ts, tag="live-entry"), ref_price=price)
                print(f"[Live] BUY {qty} {symbol} @ {fill.fill_price}")
                self.pos = self.broker.position(symbol)
                self.stop, self.take = self.risk.stop_levels(fill.fill_price)
            elif current < 0 and self.pos.qty > 0:
                qty = abs(self.pos.qty)
                fill = self.broker.submit(Order(symbol, Side.SELL, qty, None, ts, tag="live-flip"), ref_price=price)
                print(f"[Live] SELL {qty} {symbol} @ {fill.fill_price}")
                self.pos = self.broker.position(symbol)
                self.stop = self.take = None

    def run_polling(self, symbol: str, poll_secs: int = 10):
        import time
        print(f"[Live] Polling {symbol} every {poll_secs}s")
        self.pos = self.broker.position(symbol)
        while True:
            tick = self.data.latest(symbol)
            price = float(tick["price"]) ; ts = tick["ts"]
            self._update_hist(price, ts)
            sig = self.strategy.generate_signals(self.hist)
            current = int(sig.iloc[-1]) if len(sig) else 0
            rets = self.hist["close"].pct_change().dropna()
            rolling_vol = rets.tail(120).std() if len(rets) > 10 else 0.0
            if self.pos.qty != 0 and self.stop is not None and self.take is not None:
                if (price <= self.stop and self.pos.qty > 0) or (price >= self.take and self.pos.qty > 0):
                    qty = abs(self.pos.qty)
                    fill = self.broker.submit(Order(symbol, Side.SELL, qty, None, ts, tag="live-exit"), ref_price=price)
                    print(f"[Live] EXIT {qty} {symbol} @ {fill.fill_price}")
                    self.pos = self.broker.position(symbol)
                    self.stop = self.take = None
            if current > 0 and self.pos.qty <= 0:
                qty = max(1, self.risk.position_size(10000.0, price, rolling_vol))
                fill = self.broker.submit(Order(symbol, Side.BUY, qty, None, ts, tag="live-entry"), ref_price=price)
                print(f"[Live] BUY {qty} {symbol} @ {fill.fill_price}")
                self.pos = self.broker.position(symbol)
                self.stop, self.take = self.risk.stop_levels(fill.fill_price)
            elif current < 0 and self.pos.qty > 0:
                qty = abs(self.pos.qty)
                fill = self.broker.submit(Order(symbol, Side.SELL, qty, None, ts, tag="live-flip"), ref_price=price)
                print(f"[Live] SELL {qty} {symbol} @ {fill.fill_price}")
                self.pos = self.broker.position(symbol)
                self.stop = self.take = None
            time.sleep(poll_secs)
