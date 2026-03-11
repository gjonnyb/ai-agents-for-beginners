from __future__ import annotations

from datetime import datetime

import ccxt
import pandas as pd

from .base import DataProvider, OHLCV_COLUMNS

_TIMEFRAME_MAP = {
    "1m": "1m",
    "5m": "5m",
    "15m": "15m",
    "30m": "30m",
    "1h": "1h",
    "4h": "4h",
    "1d": "1d",
    "1w": "1w",
}


class CCXTProvider(DataProvider):
    """Market data provider using CCXT (crypto exchanges)."""

    def __init__(
        self,
        exchange_id: str = "binance",
        api_key: str = "",
        secret: str = "",
    ):
        exchange_class = getattr(ccxt, exchange_id, None)
        if exchange_class is None:
            raise ValueError(f"Unknown exchange: {exchange_id}")

        config: dict = {"enableRateLimit": True}
        if api_key:
            config["apiKey"] = api_key
        if secret:
            config["secret"] = secret

        self.exchange: ccxt.Exchange = exchange_class(config)

    def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str = "1d",
        start: datetime | str | None = None,
        end: datetime | str | None = None,
    ) -> pd.DataFrame:
        ccxt_tf = _TIMEFRAME_MAP.get(timeframe)
        if ccxt_tf is None:
            raise ValueError(
                f"Unsupported timeframe: {timeframe}. "
                f"Supported: {list(_TIMEFRAME_MAP.keys())}"
            )

        since = None
        if start is not None:
            if isinstance(start, str):
                start = datetime.fromisoformat(start)
            since = int(start.timestamp() * 1000)

        # Fetch in batches (most exchanges cap at 1000 candles)
        all_candles: list = []
        limit = 1000
        while True:
            candles = self.exchange.fetch_ohlcv(
                symbol, timeframe=ccxt_tf, since=since, limit=limit
            )
            if not candles:
                break
            all_candles.extend(candles)
            since = candles[-1][0] + 1  # next ms after last candle

            # If end date specified, stop when we pass it
            if end is not None:
                end_dt = end if isinstance(end, datetime) else datetime.fromisoformat(end)
                end_ms = int(end_dt.timestamp() * 1000)
                if candles[-1][0] >= end_ms:
                    break

            if len(candles) < limit:
                break

        if not all_candles:
            return pd.DataFrame(columns=OHLCV_COLUMNS)

        df = pd.DataFrame(
            all_candles, columns=["timestamp", "open", "high", "low", "close", "volume"]
        )
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
        df.set_index("timestamp", inplace=True)

        # Filter to end date
        if end is not None:
            end_dt = end if isinstance(end, datetime) else datetime.fromisoformat(end)
            df = df[df.index <= pd.Timestamp(end_dt, tz="UTC")]

        return self.validate_dataframe(df)

    def get_available_symbols(self) -> list[str]:
        self.exchange.load_markets()
        return list(self.exchange.symbols)
