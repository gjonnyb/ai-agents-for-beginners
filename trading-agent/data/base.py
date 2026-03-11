from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

import pandas as pd

OHLCV_COLUMNS = ["open", "high", "low", "close", "volume"]


class DataProvider(ABC):
    """Abstract base class for market data providers.

    All providers return DataFrames with a DatetimeIndex and columns:
    open, high, low, close, volume.
    """

    @abstractmethod
    def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str = "1d",
        start: datetime | str | None = None,
        end: datetime | str | None = None,
    ) -> pd.DataFrame:
        """Fetch OHLCV data for a symbol.

        Args:
            symbol: Ticker symbol (e.g. "AAPL" or "BTC/USDT").
            timeframe: Candle interval ("1m", "5m", "15m", "1h", "4h", "1d", "1w").
            start: Start date/datetime.
            end: End date/datetime.

        Returns:
            DataFrame with DatetimeIndex and columns: open, high, low, close, volume.
        """

    @abstractmethod
    def get_available_symbols(self) -> list[str]:
        """Return a list of available symbols for this provider."""

    @staticmethod
    def validate_dataframe(df: pd.DataFrame) -> pd.DataFrame:
        """Ensure the DataFrame has the expected structure."""
        if df.empty:
            return df
        for col in OHLCV_COLUMNS:
            if col not in df.columns:
                raise ValueError(f"Missing required column: {col}")
        df = df[OHLCV_COLUMNS].copy()
        df.index = pd.DatetimeIndex(df.index)
        df.sort_index(inplace=True)
        df.dropna(subset=["close"], inplace=True)
        return df
