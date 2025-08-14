from __future__ import annotations
import enum
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

class Side(str, enum.Enum):
    BUY = "BUY"
    SELL = "SELL"

@dataclass
class Order:
    symbol: str
    side: Side
    qty: int
    # Market orders need ref_price in broker.submit()
    price: Optional[float]
    ts: datetime
    tag: str = ""

@dataclass
class Fill:
    order: Order
    fill_price: float
    commission: float
    ts: datetime

@dataclass
class Position:
    symbol: str
    qty: int = 0
    avg_price: float = 0.0

    def update(self, fill: Fill):
        if fill.order.side == Side.BUY:
            new_qty = self.qty + fill.order.qty
            if new_qty <= 0:
                self.avg_price = 0.0
            else:
                self.avg_price = (self.avg_price * self.qty + fill.fill_price * fill.order.qty) / new_qty
            self.qty = new_qty
        else:
            self.qty -= fill.order.qty
            if self.qty == 0:
                self.avg_price = 0.0