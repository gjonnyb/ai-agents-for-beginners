from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .base import Pattern, PatternMatch, PatternType


@dataclass
class SwingPoint:
    """A local high or low in price data."""

    index: int
    price: float
    type: str  # "high" or "low"
    date: pd.Timestamp | None = None


@dataclass
class WaveStructure:
    """A detected Elliott Wave impulse structure (Waves 0-5)."""

    # Wave 0 is the origin point (start of Wave 1)
    points: list[SwingPoint] = field(default_factory=list)
    direction: str = "bullish"  # "bullish" (impulse up) or "bearish" (impulse down)
    confidence: float = 0.0
    completed_waves: int = 0  # How many waves (1-5) are complete

    @property
    def wave0(self) -> SwingPoint | None:
        return self.points[0] if len(self.points) > 0 else None

    @property
    def wave1_end(self) -> SwingPoint | None:
        return self.points[1] if len(self.points) > 1 else None

    @property
    def wave2_end(self) -> SwingPoint | None:
        return self.points[2] if len(self.points) > 2 else None

    @property
    def wave3_end(self) -> SwingPoint | None:
        return self.points[3] if len(self.points) > 3 else None

    @property
    def wave4_end(self) -> SwingPoint | None:
        return self.points[4] if len(self.points) > 4 else None

    @property
    def wave5_end(self) -> SwingPoint | None:
        return self.points[5] if len(self.points) > 5 else None

    @property
    def wave1_length(self) -> float | None:
        if self.wave0 and self.wave1_end:
            return abs(self.wave1_end.price - self.wave0.price)
        return None

    @property
    def wave2_retracement(self) -> float | None:
        """Wave 2 retracement as a fraction of Wave 1."""
        if self.wave0 and self.wave1_end and self.wave2_end and self.wave1_length:
            retrace = abs(self.wave2_end.price - self.wave1_end.price)
            return retrace / self.wave1_length
        return None

    def wave3_extension(self, price: float) -> float | None:
        """Current Wave 3 extension as multiple of Wave 1 length."""
        if self.wave2_end and self.wave1_length and self.wave1_length > 0:
            extension = abs(price - self.wave2_end.price)
            return extension / self.wave1_length
        return None

    def wave3_target(self, multiplier: float = 1.618) -> float | None:
        """Calculate Wave 3 price target at given Fibonacci extension."""
        if self.wave2_end and self.wave1_length:
            if self.direction == "bullish":
                return self.wave2_end.price + (self.wave1_length * multiplier)
            else:
                return self.wave2_end.price - (self.wave1_length * multiplier)
        return None


# Fibonacci levels used for wave validation
FIB_WAVE2_MIN = 0.382
FIB_WAVE2_IDEAL_MIN = 0.50
FIB_WAVE2_IDEAL_MAX = 0.618
FIB_WAVE2_MAX = 0.786

FIB_WAVE3_TARGETS = [1.0, 1.618, 2.618, 4.236]


class ElliottWaveDetector(Pattern):
    """Detects Elliott Wave impulse patterns in price data.

    Focuses on identifying completed Wave 1 + Wave 2 structures
    that set up potential Wave 3 entries.
    """

    def __init__(
        self,
        zigzag_pct: float = 5.0,
        min_wave1_bars: int = 5,
        max_wave2_bars: int = 50,
    ):
        self.zigzag_pct = zigzag_pct
        self.min_wave1_bars = min_wave1_bars
        self.max_wave2_bars = max_wave2_bars

    @property
    def name(self) -> str:
        return "Elliott Wave"

    def detect(self, df: pd.DataFrame) -> list[PatternMatch]:
        """Detect Elliott Wave structures in the data."""
        swings = self._find_swing_points(df)
        if len(swings) < 3:
            return []

        structures = self._find_wave_structures(swings, df)
        return self._structures_to_matches(structures, df)

    def find_structures(self, df: pd.DataFrame) -> list[WaveStructure]:
        """Return raw WaveStructure objects (used by signal generator)."""
        swings = self._find_swing_points(df)
        if len(swings) < 3:
            return []
        return self._find_wave_structures(swings, df)

    def _find_swing_points(self, df: pd.DataFrame) -> list[SwingPoint]:
        """Identify swing highs and lows using zigzag algorithm."""
        high = df["high"].values
        low = df["low"].values
        close = df["close"].values
        threshold = self.zigzag_pct / 100.0

        swings: list[SwingPoint] = []
        last_type = ""
        last_price = close[0]
        last_idx = 0

        for i in range(1, len(close)):
            pct_change_high = (high[i] - last_price) / last_price if last_price != 0 else 0
            pct_change_low = (last_price - low[i]) / last_price if last_price != 0 else 0

            if pct_change_high >= threshold and last_type != "high":
                if last_type == "high" and swings:
                    # Update last high if this one is higher
                    if high[i] > swings[-1].price:
                        swings[-1] = SwingPoint(
                            index=i, price=float(high[i]), type="high",
                            date=df.index[i],
                        )
                else:
                    # Need to insert a low before this high
                    if last_type != "low" and swings:
                        # Find lowest point between last swing and here
                        search_start = swings[-1].index + 1 if swings else 0
                        min_idx = search_start + int(np.argmin(low[search_start:i + 1]))
                        swings.append(
                            SwingPoint(
                                index=min_idx, price=float(low[min_idx]),
                                type="low", date=df.index[min_idx],
                            )
                        )
                    swings.append(
                        SwingPoint(
                            index=i, price=float(high[i]), type="high",
                            date=df.index[i],
                        )
                    )
                last_type = "high"
                last_price = high[i]
                last_idx = i

            elif pct_change_low >= threshold and last_type != "low":
                if last_type == "low" and swings:
                    if low[i] < swings[-1].price:
                        swings[-1] = SwingPoint(
                            index=i, price=float(low[i]), type="low",
                            date=df.index[i],
                        )
                else:
                    if last_type != "high" and swings:
                        search_start = swings[-1].index + 1 if swings else 0
                        max_idx = search_start + int(np.argmax(high[search_start:i + 1]))
                        swings.append(
                            SwingPoint(
                                index=max_idx, price=float(high[max_idx]),
                                type="high", date=df.index[max_idx],
                            )
                        )
                    swings.append(
                        SwingPoint(
                            index=i, price=float(low[i]), type="low",
                            date=df.index[i],
                        )
                    )
                last_type = "low"
                last_price = low[i]
                last_idx = i

        # Ensure alternating high/low sequence
        cleaned: list[SwingPoint] = []
        for sp in swings:
            if not cleaned or cleaned[-1].type != sp.type:
                cleaned.append(sp)
            else:
                # Same type: keep the more extreme one
                if sp.type == "high" and sp.price > cleaned[-1].price:
                    cleaned[-1] = sp
                elif sp.type == "low" and sp.price < cleaned[-1].price:
                    cleaned[-1] = sp

        return cleaned

    def _find_wave_structures(
        self, swings: list[SwingPoint], df: pd.DataFrame
    ) -> list[WaveStructure]:
        """Find Elliott Wave impulse structures in swing points."""
        structures = []

        for i in range(len(swings) - 2):
            # Bullish: low -> high -> low (Wave 0 -> Wave 1 end -> Wave 2 end)
            if (
                swings[i].type == "low"
                and i + 1 < len(swings)
                and swings[i + 1].type == "high"
                and i + 2 < len(swings)
                and swings[i + 2].type == "low"
            ):
                structure = self._validate_bullish_waves(
                    swings[i], swings[i + 1], swings[i + 2], swings, i, df
                )
                if structure:
                    structures.append(structure)

            # Bearish: high -> low -> high (Wave 0 -> Wave 1 end -> Wave 2 end)
            if (
                swings[i].type == "high"
                and i + 1 < len(swings)
                and swings[i + 1].type == "low"
                and i + 2 < len(swings)
                and swings[i + 2].type == "high"
            ):
                structure = self._validate_bearish_waves(
                    swings[i], swings[i + 1], swings[i + 2], swings, i, df
                )
                if structure:
                    structures.append(structure)

        return structures

    def _validate_bullish_waves(
        self,
        wave0: SwingPoint,
        wave1_end: SwingPoint,
        wave2_end: SwingPoint,
        swings: list[SwingPoint],
        swing_idx: int,
        df: pd.DataFrame,
    ) -> WaveStructure | None:
        """Validate a bullish impulse Wave 1 + Wave 2 structure."""
        # Wave 1 must go up
        if wave1_end.price <= wave0.price:
            return None

        # Minimum bars for Wave 1
        if wave1_end.index - wave0.index < self.min_wave1_bars:
            return None

        # Wave 2 must retrace down
        if wave2_end.price >= wave1_end.price:
            return None

        # Wave 2 CANNOT retrace beyond Wave 0 (core rule)
        if wave2_end.price <= wave0.price:
            return None

        wave1_len = wave1_end.price - wave0.price
        wave2_retrace = (wave1_end.price - wave2_end.price) / wave1_len

        # Wave 2 retracement must be within valid range
        if wave2_retrace < FIB_WAVE2_MIN or wave2_retrace > FIB_WAVE2_MAX:
            return None

        # Max bars for Wave 2
        if wave2_end.index - wave1_end.index > self.max_wave2_bars:
            return None

        # Calculate confidence based on how ideal the retracement is
        confidence = self._calculate_confidence(wave2_retrace)

        structure = WaveStructure(
            points=[wave0, wave1_end, wave2_end],
            direction="bullish",
            confidence=confidence,
            completed_waves=2,
        )

        # Check if Wave 3 has started/completed
        self._extend_structure_bullish(structure, swings, swing_idx + 2, df)

        return structure

    def _validate_bearish_waves(
        self,
        wave0: SwingPoint,
        wave1_end: SwingPoint,
        wave2_end: SwingPoint,
        swings: list[SwingPoint],
        swing_idx: int,
        df: pd.DataFrame,
    ) -> WaveStructure | None:
        """Validate a bearish impulse Wave 1 + Wave 2 structure."""
        if wave1_end.price >= wave0.price:
            return None

        if wave1_end.index - wave0.index < self.min_wave1_bars:
            return None

        if wave2_end.price <= wave1_end.price:
            return None

        if wave2_end.price >= wave0.price:
            return None

        wave1_len = wave0.price - wave1_end.price
        wave2_retrace = (wave2_end.price - wave1_end.price) / wave1_len

        if wave2_retrace < FIB_WAVE2_MIN or wave2_retrace > FIB_WAVE2_MAX:
            return None

        if wave2_end.index - wave1_end.index > self.max_wave2_bars:
            return None

        confidence = self._calculate_confidence(wave2_retrace)

        structure = WaveStructure(
            points=[wave0, wave1_end, wave2_end],
            direction="bearish",
            confidence=confidence,
            completed_waves=2,
        )

        self._extend_structure_bearish(structure, swings, swing_idx + 2, df)

        return structure

    def _extend_structure_bullish(
        self,
        structure: WaveStructure,
        swings: list[SwingPoint],
        from_idx: int,
        df: pd.DataFrame,
    ) -> None:
        """Try to extend a bullish structure with Waves 3, 4, 5."""
        wave1_len = structure.wave1_length
        if wave1_len is None:
            return

        # Look for Wave 3 end (next swing high after Wave 2 end)
        for i in range(from_idx + 1, min(from_idx + 4, len(swings))):
            if swings[i].type != "high":
                continue

            w3_len = swings[i].price - structure.wave2_end.price
            if w3_len <= 0:
                continue

            # Wave 3 should be at least as long as Wave 1
            if w3_len < wave1_len * 0.8:
                continue

            structure.points.append(swings[i])
            structure.completed_waves = 3

            # Boost confidence if Wave 3 hits 1.618 extension
            extension = w3_len / wave1_len
            if 1.4 <= extension <= 3.0:
                structure.confidence = min(1.0, structure.confidence + 0.15)

            break

    def _extend_structure_bearish(
        self,
        structure: WaveStructure,
        swings: list[SwingPoint],
        from_idx: int,
        df: pd.DataFrame,
    ) -> None:
        """Try to extend a bearish structure with Waves 3, 4, 5."""
        wave1_len = structure.wave1_length
        if wave1_len is None:
            return

        for i in range(from_idx + 1, min(from_idx + 4, len(swings))):
            if swings[i].type != "low":
                continue

            w3_len = structure.wave2_end.price - swings[i].price
            if w3_len <= 0:
                continue

            if w3_len < wave1_len * 0.8:
                continue

            structure.points.append(swings[i])
            structure.completed_waves = 3

            extension = w3_len / wave1_len
            if 1.4 <= extension <= 3.0:
                structure.confidence = min(1.0, structure.confidence + 0.15)

            break

    @staticmethod
    def _calculate_confidence(wave2_retrace: float) -> float:
        """Score confidence based on Wave 2 Fibonacci retracement quality."""
        # Ideal range is 50-61.8%
        if FIB_WAVE2_IDEAL_MIN <= wave2_retrace <= FIB_WAVE2_IDEAL_MAX:
            # Perfect zone: high confidence
            # Peak at 0.618, secondary peak at 0.50
            dist_to_618 = abs(wave2_retrace - 0.618)
            dist_to_50 = abs(wave2_retrace - 0.50)
            best_dist = min(dist_to_618, dist_to_50)
            return 0.70 + (0.20 * (1.0 - best_dist / 0.118))
        elif FIB_WAVE2_MIN <= wave2_retrace < FIB_WAVE2_IDEAL_MIN:
            # Shallow retrace: moderate confidence
            return 0.40 + 0.30 * (
                (wave2_retrace - FIB_WAVE2_MIN)
                / (FIB_WAVE2_IDEAL_MIN - FIB_WAVE2_MIN)
            )
        elif FIB_WAVE2_IDEAL_MAX < wave2_retrace <= FIB_WAVE2_MAX:
            # Deep retrace: lower confidence
            return 0.40 + 0.30 * (
                1.0
                - (wave2_retrace - FIB_WAVE2_IDEAL_MAX)
                / (FIB_WAVE2_MAX - FIB_WAVE2_IDEAL_MAX)
            )
        return 0.30

    def _structures_to_matches(
        self, structures: list[WaveStructure], df: pd.DataFrame
    ) -> list[PatternMatch]:
        """Convert WaveStructure objects to PatternMatch instances."""
        matches = []
        for s in structures:
            if s.completed_waves >= 2:
                # Report the Wave 1+2 structure (setup for Wave 3 entry)
                pattern_type = PatternType.ELLIOTT_WAVE_2
                if s.completed_waves >= 3:
                    pattern_type = PatternType.ELLIOTT_WAVE_3

                targets = {}
                for mult in FIB_WAVE3_TARGETS:
                    t = s.wave3_target(mult)
                    if t is not None:
                        targets[f"wave3_{mult}x"] = round(t, 4)

                matches.append(
                    PatternMatch(
                        pattern_type=pattern_type,
                        start_idx=s.points[0].index,
                        end_idx=s.points[-1].index,
                        start_date=s.points[0].date,
                        end_date=s.points[-1].date,
                        confidence=s.confidence,
                        direction=s.direction,
                        metadata={
                            "wave0_price": s.points[0].price,
                            "wave1_end_price": s.points[1].price,
                            "wave2_end_price": s.points[2].price,
                            "wave1_length": s.wave1_length,
                            "wave2_retracement": round(s.wave2_retracement or 0, 4),
                            "completed_waves": s.completed_waves,
                            "targets": targets,
                        },
                    )
                )

        return matches
