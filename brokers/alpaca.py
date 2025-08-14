from __future__ import annotations
import os, requests
from datetime import datetime, timezone
from typing import Dict
from core.types import Order, Fill, Position, Side

class AlpacaBroker:
    def __init__(self):
        self.base = os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")
        self.key = os.getenv("ALPACA_API_KEY")
        self.secret = os.getenv("ALPACA_API_SECRET")
        if not (self.key and self.secret):
            raise RuntimeError("Set ALPACA_API_KEY and ALPACA_API_SECRET")
        self._positions: Dict[str, Position] = {}
    def _headers(self):
        return {"APCA-API-KEY-ID": self.key, "APCA-API-SECRET-KEY": self.secret}
    def submit(self, order: Order, *, ref_price: float | None = None) -> Fill:
        side = "buy" if order.side == Side.BUY else "sell"
        typ = "market" if order.price is None else "limit"
        payload = {"symbol": order.symbol, "qty": order.qty, "side": side, "type": typ, "time_in_force": "day"}
        if order.price is not None:
            payload["limit_price"] = order.price
        r = requests.post(f"{self.base}/v2/orders", headers=self._headers(), json=payload, timeout=15)
        r.raise_for_status()
        px = ref_price if ref_price is not None else self.latest_price(order.symbol)
        fill = Fill(order=order, fill_price=float(px), commission=0.0, ts=datetime.now(timezone.utc))
        pos = self._positions.setdefault(order.symbol, Position(order.symbol))
        pos.update(fill)
        return fill
    def latest_price(self, symbol: str) -> float:
        r = requests.get(f"{self.base}/v2/stocks/{symbol}/trades/latest", headers=self._headers(), timeout=10)
        r.raise_for_status()
        data = r.json()
        for k in ("p","price"):
            if k in data.get("trade", {}):
                return float(data["trade"][k])
        raise RuntimeError("No price field in latest trade")
    def position(self, symbol: str) -> Position:
        return self._positions.get(symbol, Position(symbol))