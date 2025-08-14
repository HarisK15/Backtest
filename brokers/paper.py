from __future__ import annotations
from datetime import datetime, timezone
from typing import Dict
from core.types import Order, Fill, Position, Side

class PaperBroker:
    def __init__(self, slippage_bps: float = 1.0, commission_per_share: float = 0.0):
        self.slippage_bps = slippage_bps
        self.commission_per_share = commission_per_share
        self.positions: Dict[str, Position] = {}

    def _apply_slippage(self, px: float, side: Side) -> float:
        slip = px * (self.slippage_bps / 1e4)
        return px + slip if side == Side.BUY else px - slip

    def submit(self, order: Order, *, ref_price: float | None = None) -> Fill:
        # Market order must provide ref_price; limit uses order.price
        px = order.price if order.price is not None else ref_price
        if px is None:
            raise ValueError("Market order requires ref_price at submit time")
        fill_px = self._apply_slippage(float(px), order.side)
        comm = self.commission_per_share * order.qty
        pos = self.positions.setdefault(order.symbol, Position(order.symbol))
        fill = Fill(order=order, fill_price=fill_px, commission=comm, ts=datetime.now(timezone.utc))
        pos.update(fill)
        return fill

    def position(self, symbol: str) -> Position:
        return self.positions.get(symbol, Position(symbol))