from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class PositionInfo:
    """Lightweight position info for portfolio-level risk checks."""

    symbol: str
    direction: str  # "long" or "short"
    value: float  # Position value in account currency
    unrealized_pnl: float = 0.0


class PortfolioRiskManager:
    """Portfolio-level risk management.

    Enforces:
    - Maximum concurrent positions
    - Maximum portfolio drawdown (circuit breaker)
    - Maximum single-position exposure
    - Maximum total exposure
    """

    def __init__(
        self,
        max_positions: int = 6,
        max_drawdown_pct: float = 0.10,
        max_single_position_pct: float = 0.15,
        max_total_exposure_pct: float = 0.80,
    ):
        self.max_positions = max_positions
        self.max_drawdown_pct = max_drawdown_pct
        self.max_single_position_pct = max_single_position_pct
        self.max_total_exposure_pct = max_total_exposure_pct

        self._peak_equity: float = 0.0
        self._circuit_breaker_active: bool = False

    def can_open_position(
        self,
        current_positions: list[PositionInfo],
        proposed_value: float,
        current_equity: float,
    ) -> tuple[bool, str]:
        """Check if a new position can be opened.

        Returns (allowed, reason) tuple.
        """
        # Circuit breaker check
        if self._circuit_breaker_active:
            return False, "Circuit breaker active — max drawdown exceeded"

        # Update peak equity
        if current_equity > self._peak_equity:
            self._peak_equity = current_equity

        # Drawdown check
        if self._peak_equity > 0:
            current_dd = (self._peak_equity - current_equity) / self._peak_equity
            if current_dd >= self.max_drawdown_pct:
                self._circuit_breaker_active = True
                return False, (
                    f"Max drawdown reached ({current_dd:.1%} >= "
                    f"{self.max_drawdown_pct:.1%})"
                )

        # Max positions
        if len(current_positions) >= self.max_positions:
            return False, (
                f"Max positions reached ({len(current_positions)}/{self.max_positions})"
            )

        # Single position size
        if current_equity > 0:
            position_pct = proposed_value / current_equity
            if position_pct > self.max_single_position_pct:
                return False, (
                    f"Position too large ({position_pct:.1%} > "
                    f"{self.max_single_position_pct:.1%})"
                )

        # Total exposure
        total_exposure = sum(abs(p.value) for p in current_positions) + abs(proposed_value)
        if current_equity > 0:
            exposure_pct = total_exposure / current_equity
            if exposure_pct > self.max_total_exposure_pct:
                return False, (
                    f"Total exposure too high ({exposure_pct:.1%} > "
                    f"{self.max_total_exposure_pct:.1%})"
                )

        return True, "OK"

    def reset_circuit_breaker(self) -> None:
        """Manually reset the circuit breaker after drawdown recovery."""
        self._circuit_breaker_active = False

    def update_equity(self, equity: float) -> None:
        """Update peak equity tracking."""
        if equity > self._peak_equity:
            self._peak_equity = equity
