from __future__ import annotations

from datetime import datetime

import pandas as pd
import yfinance as yf

from .base import DataProvider

# Map our standard timeframes to yfinance intervals
_TIMEFRAME_MAP = {
    "1m": "1m",
    "5m": "5m",
    "15m": "15m",
    "30m": "30m",
    "1h": "1h",
    "4h": "1h",  # yfinance doesn't support 4h natively; we resample
    "1d": "1d",
    "1w": "1wk",
}


class YFinanceProvider(DataProvider):
    """Market data provider using Yahoo Finance (stocks, ETFs, forex)."""

    def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str = "1d",
        start: datetime | str | None = None,
        end: datetime | str | None = None,
    ) -> pd.DataFrame:
        yf_interval = _TIMEFRAME_MAP.get(timeframe)
        if yf_interval is None:
            raise ValueError(
                f"Unsupported timeframe: {timeframe}. "
                f"Supported: {list(_TIMEFRAME_MAP.keys())}"
            )

        ticker = yf.Ticker(symbol)
        df = ticker.history(
            interval=yf_interval,
            start=start,
            end=end,
            auto_adjust=True,
        )

        if df.empty:
            return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])

        df.columns = [c.lower() for c in df.columns]
        df = df.rename(
            columns={
                "stock splits": "stock_splits",
            }
        )

        # Resample to 4h if needed
        if timeframe == "4h" and not df.empty:
            df = (
                df.resample("4h")
                .agg(
                    {
                        "open": "first",
                        "high": "max",
                        "low": "min",
                        "close": "last",
                        "volume": "sum",
                    }
                )
                .dropna()
            )

        return self.validate_dataframe(df)

    def get_available_symbols(self) -> list[str]:
        # yfinance doesn't have a discovery API; return common tickers
        return [
            "SPY", "QQQ", "IWM", "DIA",
            "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA",
            "GLD", "SLV", "USO",
            "EURUSD=X", "GBPUSD=X", "USDJPY=X",
        ]
