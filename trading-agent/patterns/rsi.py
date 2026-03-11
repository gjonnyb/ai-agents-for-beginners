from __future__ import annotations

import numpy as np
import pandas as pd

from .base import Pattern, PatternMatch, PatternType


def compute_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """Compute Relative Strength Index."""
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta).where(delta < 0, 0.0)

    avg_gain = gain.ewm(alpha=1.0 / period, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, min_periods=period).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return rsi


class RSIAnalyzer(Pattern):
    """RSI pattern detector: oversold/overbought zones and divergences."""

    def __init__(
        self,
        period: int = 14,
        oversold: float = 30.0,
        overbought: float = 70.0,
        divergence_lookback: int = 20,
    ):
        self.period = period
        self.oversold = oversold
        self.overbought = overbought
        self.divergence_lookback = divergence_lookback

    @property
    def name(self) -> str:
        return f"RSI({self.period})"

    def compute(self, df: pd.DataFrame) -> pd.Series:
        """Return the RSI series for the given data."""
        return compute_rsi(df["close"], self.period)

    def detect(self, df: pd.DataFrame) -> list[PatternMatch]:
        """Detect RSI oversold, overbought, and divergence patterns."""
        rsi = self.compute(df)
        matches: list[PatternMatch] = []
        close = df["close"]

        # Detect oversold/overbought zones
        matches.extend(self._detect_zones(rsi, df))

        # Detect divergences
        matches.extend(self._detect_divergences(close, rsi, df))

        return matches

    def _detect_zones(
        self, rsi: pd.Series, df: pd.DataFrame
    ) -> list[PatternMatch]:
        matches = []
        in_oversold = False
        zone_start = 0

        for i in range(len(rsi)):
            if pd.isna(rsi.iloc[i]):
                continue

            # Oversold
            if rsi.iloc[i] < self.oversold and not in_oversold:
                in_oversold = True
                zone_start = i
            elif rsi.iloc[i] >= self.oversold and in_oversold:
                in_oversold = False
                matches.append(
                    PatternMatch(
                        pattern_type=PatternType.RSI_OVERSOLD,
                        start_idx=zone_start,
                        end_idx=i,
                        start_date=df.index[zone_start],
                        end_date=df.index[i],
                        confidence=min(1.0, (self.oversold - rsi.iloc[zone_start:i].min()) / 20.0),
                        direction="bullish",
                        metadata={
                            "rsi_low": float(rsi.iloc[zone_start:i].min()),
                            "exit_rsi": float(rsi.iloc[i]),
                        },
                    )
                )

        return matches

    def _detect_divergences(
        self, close: pd.Series, rsi: pd.Series, df: pd.DataFrame
    ) -> list[PatternMatch]:
        """Detect bullish and bearish divergences between price and RSI."""
        matches = []
        lookback = self.divergence_lookback

        # Find local lows in price and RSI for bullish divergence
        price_lows = self._find_local_extrema(close, mode="min", window=5)
        rsi_lows = self._find_local_extrema(rsi, mode="min", window=5)

        # Bullish divergence: price makes lower low, RSI makes higher low
        for i in range(1, len(price_lows)):
            prev_idx = price_lows[i - 1]
            curr_idx = price_lows[i]

            if curr_idx - prev_idx > lookback:
                continue

            # Find corresponding RSI lows near these price lows
            prev_rsi_idx = self._nearest_extremum(rsi_lows, prev_idx, tolerance=3)
            curr_rsi_idx = self._nearest_extremum(rsi_lows, curr_idx, tolerance=3)

            if prev_rsi_idx is None or curr_rsi_idx is None:
                continue

            price_lower_low = close.iloc[curr_idx] < close.iloc[prev_idx]
            rsi_higher_low = rsi.iloc[curr_rsi_idx] > rsi.iloc[prev_rsi_idx]

            if price_lower_low and rsi_higher_low:
                rsi_diff = rsi.iloc[curr_rsi_idx] - rsi.iloc[prev_rsi_idx]
                confidence = min(1.0, rsi_diff / 15.0)
                matches.append(
                    PatternMatch(
                        pattern_type=PatternType.RSI_BULLISH_DIVERGENCE,
                        start_idx=prev_idx,
                        end_idx=curr_idx,
                        start_date=df.index[prev_idx],
                        end_date=df.index[curr_idx],
                        confidence=max(0.1, confidence),
                        direction="bullish",
                        metadata={
                            "price_prev_low": float(close.iloc[prev_idx]),
                            "price_curr_low": float(close.iloc[curr_idx]),
                            "rsi_prev_low": float(rsi.iloc[prev_rsi_idx]),
                            "rsi_curr_low": float(rsi.iloc[curr_rsi_idx]),
                        },
                    )
                )

        # Bearish divergence: price makes higher high, RSI makes lower high
        price_highs = self._find_local_extrema(close, mode="max", window=5)
        rsi_highs = self._find_local_extrema(rsi, mode="max", window=5)

        for i in range(1, len(price_highs)):
            prev_idx = price_highs[i - 1]
            curr_idx = price_highs[i]

            if curr_idx - prev_idx > lookback:
                continue

            prev_rsi_idx = self._nearest_extremum(rsi_highs, prev_idx, tolerance=3)
            curr_rsi_idx = self._nearest_extremum(rsi_highs, curr_idx, tolerance=3)

            if prev_rsi_idx is None or curr_rsi_idx is None:
                continue

            price_higher_high = close.iloc[curr_idx] > close.iloc[prev_idx]
            rsi_lower_high = rsi.iloc[curr_rsi_idx] < rsi.iloc[prev_rsi_idx]

            if price_higher_high and rsi_lower_high:
                rsi_diff = rsi.iloc[prev_rsi_idx] - rsi.iloc[curr_rsi_idx]
                confidence = min(1.0, rsi_diff / 15.0)
                matches.append(
                    PatternMatch(
                        pattern_type=PatternType.RSI_BEARISH_DIVERGENCE,
                        start_idx=prev_idx,
                        end_idx=curr_idx,
                        start_date=df.index[prev_idx],
                        end_date=df.index[curr_idx],
                        confidence=max(0.1, confidence),
                        direction="bearish",
                        metadata={
                            "price_prev_high": float(close.iloc[prev_idx]),
                            "price_curr_high": float(close.iloc[curr_idx]),
                            "rsi_prev_high": float(rsi.iloc[prev_rsi_idx]),
                            "rsi_curr_high": float(rsi.iloc[curr_rsi_idx]),
                        },
                    )
                )

        return matches

    @staticmethod
    def _find_local_extrema(
        series: pd.Series, mode: str = "min", window: int = 5
    ) -> list[int]:
        """Find indices of local minima or maxima."""
        extrema = []
        values = series.values
        for i in range(window, len(values) - window):
            if pd.isna(values[i]):
                continue
            neighborhood = values[i - window: i + window + 1]
            if np.any(pd.isna(neighborhood)):
                continue
            if mode == "min" and values[i] == np.nanmin(neighborhood):
                extrema.append(i)
            elif mode == "max" and values[i] == np.nanmax(neighborhood):
                extrema.append(i)
        return extrema

    @staticmethod
    def _nearest_extremum(
        extrema: list[int], target: int, tolerance: int = 3
    ) -> int | None:
        """Find the nearest extremum index within tolerance of target."""
        best = None
        best_dist = tolerance + 1
        for idx in extrema:
            dist = abs(idx - target)
            if dist <= tolerance and dist < best_dist:
                best = idx
                best_dist = dist
        return best
