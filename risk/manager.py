from __future__ import annotations
import numpy as np
from dataclasses import dataclass

@dataclass
class RiskConfig:
    vol_target: float = 0.15
    max_drawdown: float = 0.2
    per_trade_risk: float = 0.01
    stop_loss_pct: float = 0.05
    take_profit_pct: float = 0.10

class RiskManager:
    def __init__(self, cfg: RiskConfig):
        self.cfg = cfg
    def position_size(self, equity: float, px: float, rolling_vol: float) -> int:
        if rolling_vol <= 0 or px <= 0 or equity <= 0:
            return 0
        annualized_vol = rolling_vol * np.sqrt(252)
        target_exposure = (self.cfg.vol_target / max(annualized_vol, 1e-9)) * equity
        return max(0, int(target_exposure // px))
    def stop_levels(self, entry_price: float) -> tuple[float,float]:
        return entry_price * (1 - self.cfg.stop_loss_pct), entry_price * (1 + self.cfg.take_profit_pct)
