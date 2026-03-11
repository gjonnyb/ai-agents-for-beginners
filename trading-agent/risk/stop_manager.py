from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from signals.base import Direction


class StopType(str, Enum):
    INITIAL = "initial"
    BREAKEVEN = "breakeven"
    TRAILING = "trailing"


@dataclass
class StopState:
    """Current state of stop-loss management for a position."""

    stop_price: float
    stop_type: StopType = StopType.INITIAL
    trailing_distance: float = 0.0
    highest_price: float = 0.0  # For long trailing stops
    lowest_price: float = float("inf")  # For short trailing stops


class StopManager:
    """Manages stop-loss progression for open positions.

    Stop progression:
    1. Initial stop at pattern-defined level (e.g., below Wave 2 low)
    2. Move to breakeven when first target is hit
    3. Trail behind price after breakeven (optional)
    """

    def __init__(
        self,
        breakeven_buffer_pct: float = 0.001,
        trailing_pct: float = 0.03,
        enable_trailing: bool = True,
    ):
        self.breakeven_buffer_pct = breakeven_buffer_pct
        self.trailing_pct = trailing_pct
        self.enable_trailing = enable_trailing

    def create_stop(
        self,
        entry_price: float,
        initial_stop: float,
        direction: Direction,
    ) -> StopState:
        """Create initial stop state for a new position."""
        return StopState(
            stop_price=initial_stop,
            stop_type=StopType.INITIAL,
            highest_price=entry_price if direction == Direction.LONG else 0.0,
            lowest_price=entry_price if direction == Direction.SHORT else float("inf"),
        )

    def update(
        self,
        state: StopState,
        current_price: float,
        direction: Direction,
        target_hit: bool = False,
        entry_price: float = 0.0,
    ) -> StopState:
        """Update stop state based on current price action.

        Args:
            state: Current stop state.
            current_price: Current market price.
            direction: Position direction.
            target_hit: Whether first target has been hit.
            entry_price: Original entry price (needed for breakeven).

        Returns:
            Updated StopState.
        """
        # Move to breakeven when first target hit
        if target_hit and state.stop_type == StopType.INITIAL and entry_price > 0:
            if direction == Direction.LONG:
                be_price = entry_price * (1 + self.breakeven_buffer_pct)
                state.stop_price = max(state.stop_price, be_price)
            else:
                be_price = entry_price * (1 - self.breakeven_buffer_pct)
                state.stop_price = min(state.stop_price, be_price)
            state.stop_type = StopType.BREAKEVEN

        # Trailing stop (only after breakeven)
        if self.enable_trailing and state.stop_type in (
            StopType.BREAKEVEN,
            StopType.TRAILING,
        ):
            if direction == Direction.LONG:
                state.highest_price = max(state.highest_price, current_price)
                trail_stop = state.highest_price * (1 - self.trailing_pct)
                if trail_stop > state.stop_price:
                    state.stop_price = trail_stop
                    state.stop_type = StopType.TRAILING
            else:
                state.lowest_price = min(state.lowest_price, current_price)
                trail_stop = state.lowest_price * (1 + self.trailing_pct)
                if trail_stop < state.stop_price:
                    state.stop_price = trail_stop
                    state.stop_type = StopType.TRAILING

        return state

    def is_stopped(
        self,
        state: StopState,
        current_price: float,
        direction: Direction,
    ) -> bool:
        """Check if the current price has hit the stop."""
        if direction == Direction.LONG:
            return current_price <= state.stop_price
        else:
            return current_price >= state.stop_price
