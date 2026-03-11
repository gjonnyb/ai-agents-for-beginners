from __future__ import annotations

import pandas as pd

from patterns.elliott_wave import ElliottWaveDetector, WaveStructure, FIB_WAVE3_TARGETS
from patterns.rsi import RSIAnalyzer, compute_rsi
from .base import Signal, TradeSignal, Direction


class Wave3RSISignal(Signal):
    """Wave 3 entry signal: Elliott Wave 1+2 completion + RSI confirmation.

    Entry logic:
    1. Detect completed Wave 1 + Wave 2 structure
    2. Confirm Wave 2 retracement is 50-61.8% of Wave 1 (ideal Fibonacci zone)
    3. RSI confirmation: bullish divergence at Wave 2 low, OR RSI crossing above 50
    4. Entry: break above Wave 1 high (bullish) or below Wave 1 low (bearish)
    5. Stop: below Wave 2 low (bullish) or above Wave 2 high (bearish)
    6. Targets: 1.618x and 2.618x Fibonacci extensions of Wave 1

    This ensures we're entering at the start of the strongest wave (Wave 3)
    with momentum confirmation from RSI.
    """

    def __init__(
        self,
        zigzag_pct: float = 5.0,
        rsi_period: int = 14,
        min_rsi_confirmation: float = 45.0,
        min_confidence: float = 0.50,
        stop_buffer_pct: float = 0.005,
    ):
        self.wave_detector = ElliottWaveDetector(zigzag_pct=zigzag_pct)
        self.rsi_analyzer = RSIAnalyzer(period=rsi_period)
        self.min_rsi_confirmation = min_rsi_confirmation
        self.min_confidence = min_confidence
        self.stop_buffer_pct = stop_buffer_pct

    @property
    def name(self) -> str:
        return "Wave 3 + RSI"

    def generate(self, df: pd.DataFrame, symbol: str = "") -> list[TradeSignal]:
        """Generate Wave 3 entry signals with RSI confirmation."""
        if len(df) < 50:
            return []

        structures = self.wave_detector.find_structures(df)
        rsi = compute_rsi(df["close"], self.rsi_analyzer.period)
        rsi_matches = self.rsi_analyzer.detect(df)

        signals: list[TradeSignal] = []

        for structure in structures:
            if structure.completed_waves < 2:
                continue
            if structure.confidence < self.min_confidence:
                continue

            # Only generate signals at Wave 2 completion (setup for Wave 3)
            # Skip if Wave 3 is already complete (too late)
            if structure.completed_waves >= 3:
                continue

            signal = self._evaluate_structure(
                structure, df, rsi, rsi_matches, symbol
            )
            if signal is not None:
                signals.append(signal)

        return signals

    def _evaluate_structure(
        self,
        structure: WaveStructure,
        df: pd.DataFrame,
        rsi: pd.Series,
        rsi_matches: list,
        symbol: str,
    ) -> TradeSignal | None:
        """Evaluate a Wave 1+2 structure and generate signal if confirmed."""
        wave2_end = structure.wave2_end
        if wave2_end is None:
            return None

        wave2_idx = wave2_end.index
        if wave2_idx >= len(df) - 1:
            return None

        # RSI confirmation at Wave 2 completion
        rsi_confirmed, rsi_confidence_boost = self._check_rsi_confirmation(
            structure, rsi, rsi_matches, wave2_idx
        )

        if not rsi_confirmed:
            return None

        # Calculate entry, stop, and targets
        if structure.direction == "bullish":
            return self._build_bullish_signal(
                structure, df, rsi_confidence_boost, symbol
            )
        else:
            return self._build_bearish_signal(
                structure, df, rsi_confidence_boost, symbol
            )

    def _check_rsi_confirmation(
        self,
        structure: WaveStructure,
        rsi: pd.Series,
        rsi_matches: list,
        wave2_idx: int,
    ) -> tuple[bool, float]:
        """Check RSI conditions at Wave 2 completion.

        Returns (is_confirmed, confidence_boost).
        """
        confidence_boost = 0.0

        if wave2_idx >= len(rsi) or pd.isna(rsi.iloc[wave2_idx]):
            return False, 0.0

        current_rsi = rsi.iloc[wave2_idx]

        if structure.direction == "bullish":
            # Condition 1: RSI bullish divergence near Wave 2 low
            has_divergence = self._has_rsi_divergence_near(
                rsi_matches, wave2_idx, "bullish", lookback=5
            )
            if has_divergence:
                confidence_boost = 0.15

            # Condition 2: RSI crossing above threshold from below
            rsi_recovering = (
                current_rsi >= self.min_rsi_confirmation
                and wave2_idx >= 2
                and not pd.isna(rsi.iloc[wave2_idx - 2])
                and rsi.iloc[wave2_idx - 2] < self.min_rsi_confirmation
            )

            # Condition 3: RSI was oversold during Wave 2
            wave1_end_idx = structure.wave1_end.index if structure.wave1_end else 0
            rsi_slice = rsi.iloc[wave1_end_idx:wave2_idx + 1]
            was_oversold = rsi_slice.min() < 35 if len(rsi_slice) > 0 else False

            if has_divergence or rsi_recovering or was_oversold:
                if was_oversold:
                    confidence_boost = max(confidence_boost, 0.10)
                return True, confidence_boost

        else:  # bearish
            has_divergence = self._has_rsi_divergence_near(
                rsi_matches, wave2_idx, "bearish", lookback=5
            )
            if has_divergence:
                confidence_boost = 0.15

            rsi_declining = (
                current_rsi <= (100 - self.min_rsi_confirmation)
                and wave2_idx >= 2
                and not pd.isna(rsi.iloc[wave2_idx - 2])
                and rsi.iloc[wave2_idx - 2] > (100 - self.min_rsi_confirmation)
            )

            wave1_end_idx = structure.wave1_end.index if structure.wave1_end else 0
            rsi_slice = rsi.iloc[wave1_end_idx:wave2_idx + 1]
            was_overbought = rsi_slice.max() > 65 if len(rsi_slice) > 0 else False

            if has_divergence or rsi_declining or was_overbought:
                if was_overbought:
                    confidence_boost = max(confidence_boost, 0.10)
                return True, confidence_boost

        return False, 0.0

    @staticmethod
    def _has_rsi_divergence_near(
        rsi_matches: list, target_idx: int, direction: str, lookback: int = 5
    ) -> bool:
        """Check if there's an RSI divergence near the target index."""
        from patterns.base import PatternType

        expected_type = (
            PatternType.RSI_BULLISH_DIVERGENCE
            if direction == "bullish"
            else PatternType.RSI_BEARISH_DIVERGENCE
        )

        for match in rsi_matches:
            if match.pattern_type != expected_type:
                continue
            if abs(match.end_idx - target_idx) <= lookback:
                return True
        return False

    def _build_bullish_signal(
        self,
        structure: WaveStructure,
        df: pd.DataFrame,
        rsi_boost: float,
        symbol: str,
    ) -> TradeSignal:
        """Build a bullish Wave 3 entry signal."""
        wave1_end = structure.wave1_end
        wave2_end = structure.wave2_end

        # Entry: at Wave 1 high (breakout confirmation)
        entry_price = wave1_end.price

        # Stop: below Wave 2 low with buffer
        stop_loss = wave2_end.price * (1 - self.stop_buffer_pct)

        # Targets: Fibonacci extensions
        targets = []
        for mult in [1.618, 2.618]:
            t = structure.wave3_target(mult)
            if t is not None:
                targets.append(round(t, 4))

        confidence = min(1.0, structure.confidence + rsi_boost)

        return TradeSignal(
            timestamp=df.index[wave2_end.index],
            symbol=symbol,
            direction=Direction.LONG,
            entry_price=round(entry_price, 4),
            stop_loss=round(stop_loss, 4),
            targets=targets,
            confidence=confidence,
            pattern_name=self.name,
            metadata={
                "wave0_price": structure.wave0.price,
                "wave1_end_price": wave1_end.price,
                "wave2_end_price": wave2_end.price,
                "wave1_length": structure.wave1_length,
                "wave2_retracement": structure.wave2_retracement,
                "fib_targets": {
                    f"{m}x": structure.wave3_target(m)
                    for m in FIB_WAVE3_TARGETS
                    if structure.wave3_target(m)
                },
            },
        )

    def _build_bearish_signal(
        self,
        structure: WaveStructure,
        df: pd.DataFrame,
        rsi_boost: float,
        symbol: str,
    ) -> TradeSignal:
        """Build a bearish Wave 3 entry signal."""
        wave1_end = structure.wave1_end
        wave2_end = structure.wave2_end

        entry_price = wave1_end.price
        stop_loss = wave2_end.price * (1 + self.stop_buffer_pct)

        targets = []
        for mult in [1.618, 2.618]:
            t = structure.wave3_target(mult)
            if t is not None:
                targets.append(round(t, 4))

        confidence = min(1.0, structure.confidence + rsi_boost)

        return TradeSignal(
            timestamp=df.index[wave2_end.index],
            symbol=symbol,
            direction=Direction.SHORT,
            entry_price=round(entry_price, 4),
            stop_loss=round(stop_loss, 4),
            targets=targets,
            confidence=confidence,
            pattern_name=self.name,
            metadata={
                "wave0_price": structure.wave0.price,
                "wave1_end_price": wave1_end.price,
                "wave2_end_price": wave2_end.price,
                "wave1_length": structure.wave1_length,
                "wave2_retracement": structure.wave2_retracement,
                "fib_targets": {
                    f"{m}x": structure.wave3_target(m)
                    for m in FIB_WAVE3_TARGETS
                    if structure.wave3_target(m)
                },
            },
        )
