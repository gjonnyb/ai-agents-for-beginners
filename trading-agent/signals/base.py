from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

import pandas as pd


class Direction(str, Enum):
    LONG = "long"
    SHORT = "short"


@dataclass
class TradeSignal:
    """A complete trade signal with entry, stop, and targets."""

    timestamp: datetime
    symbol: str
    direction: Direction
    entry_price: float
    stop_loss: float
    targets: list[float]  # Take-profit levels (ordered nearest to farthest)
    confidence: float = 0.0  # 0.0 to 1.0
    pattern_name: str = ""
    metadata: dict = field(default_factory=dict)

    @property
    def risk_per_unit(self) -> float:
        """Distance from entry to stop loss."""
        return abs(self.entry_price - self.stop_loss)

    @property
    def reward_risk_ratio(self) -> float | None:
        """Reward/risk based on first target."""
        if not self.targets or self.risk_per_unit == 0:
            return None
        reward = abs(self.targets[0] - self.entry_price)
        return reward / self.risk_per_unit

    def __repr__(self) -> str:
        rr = self.reward_risk_ratio
        rr_str = f"{rr:.2f}" if rr else "N/A"
        return (
            f"TradeSignal({self.symbol} {self.direction.value} @ {self.entry_price:.4f}, "
            f"SL={self.stop_loss:.4f}, R:R={rr_str}, conf={self.confidence:.2f})"
        )


class Signal(ABC):
    """Abstract base class for trade signal generators."""

    @abstractmethod
    def generate(self, df: pd.DataFrame, symbol: str = "") -> list[TradeSignal]:
        """Generate trade signals from OHLCV data.

        Args:
            df: OHLCV DataFrame with DatetimeIndex.
            symbol: The ticker symbol for labeling signals.

        Returns:
            List of TradeSignal instances.
        """

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable signal name."""
