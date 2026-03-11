from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

import pandas as pd


class PatternType(str, Enum):
    ELLIOTT_WAVE_1 = "elliott_wave_1"
    ELLIOTT_WAVE_2 = "elliott_wave_2"
    ELLIOTT_WAVE_3 = "elliott_wave_3"
    ELLIOTT_WAVE_4 = "elliott_wave_4"
    ELLIOTT_WAVE_5 = "elliott_wave_5"
    ELLIOTT_ABC = "elliott_abc"
    RSI_BULLISH_DIVERGENCE = "rsi_bullish_divergence"
    RSI_BEARISH_DIVERGENCE = "rsi_bearish_divergence"
    RSI_OVERSOLD = "rsi_oversold"
    RSI_OVERBOUGHT = "rsi_overbought"


@dataclass
class PatternMatch:
    """A detected pattern occurrence in price data."""

    pattern_type: PatternType
    start_idx: int
    end_idx: int
    start_date: datetime | None = None
    end_date: datetime | None = None
    confidence: float = 0.0  # 0.0 to 1.0
    direction: str = "bullish"  # "bullish" or "bearish"
    metadata: dict = field(default_factory=dict)

    def __repr__(self) -> str:
        return (
            f"PatternMatch({self.pattern_type.value}, "
            f"confidence={self.confidence:.2f}, "
            f"direction={self.direction}, "
            f"idx=[{self.start_idx}:{self.end_idx}])"
        )


class Pattern(ABC):
    """Abstract base class for pattern detectors."""

    @abstractmethod
    def detect(self, df: pd.DataFrame) -> list[PatternMatch]:
        """Detect all occurrences of this pattern in the data.

        Args:
            df: OHLCV DataFrame with DatetimeIndex.

        Returns:
            List of PatternMatch instances found in the data.
        """

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable pattern name."""
