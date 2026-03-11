from __future__ import annotations

import math


def fixed_fractional_size(
    capital: float,
    risk_pct: float,
    entry_price: float,
    stop_loss: float,
    max_position_pct: float = 0.15,
) -> float:
    """Calculate position size using fixed fractional method.

    Risks a fixed percentage of capital per trade, with a maximum
    position size cap relative to total capital.

    Args:
        capital: Current account equity.
        risk_pct: Fraction of capital to risk (e.g. 0.02 = 2%).
        entry_price: Planned entry price.
        stop_loss: Stop-loss price.
        max_position_pct: Maximum position value as fraction of capital.

    Returns:
        Number of units/shares to buy.
    """
    risk_per_unit = abs(entry_price - stop_loss)
    if risk_per_unit <= 0 or capital <= 0 or entry_price <= 0:
        return 0.0

    risk_amount = capital * risk_pct
    size_by_risk = risk_amount / risk_per_unit

    # Cap by max position size
    max_position_value = capital * max_position_pct
    size_by_cap = max_position_value / entry_price

    return min(size_by_risk, size_by_cap)


def kelly_size(
    capital: float,
    win_rate: float,
    avg_win: float,
    avg_loss: float,
    entry_price: float,
    fraction: float = 0.25,
    max_position_pct: float = 0.15,
) -> float:
    """Calculate position size using Kelly Criterion.

    Uses a fractional Kelly (default 1/4 Kelly) for safety,
    as full Kelly is too aggressive for most trading.

    Args:
        capital: Current account equity.
        win_rate: Historical win rate (0.0 to 1.0).
        avg_win: Average winning trade amount.
        avg_loss: Average losing trade amount (positive number).
        entry_price: Planned entry price.
        fraction: Kelly fraction (0.25 = quarter Kelly).
        max_position_pct: Maximum position value as fraction of capital.

    Returns:
        Number of units/shares to buy.
    """
    if avg_loss <= 0 or win_rate <= 0 or entry_price <= 0 or capital <= 0:
        return 0.0

    # Kelly formula: f* = (bp - q) / b
    # b = avg_win / avg_loss (payoff ratio)
    # p = win_rate, q = 1 - win_rate
    b = avg_win / avg_loss
    p = win_rate
    q = 1.0 - p

    kelly_pct = (b * p - q) / b

    # If Kelly is negative, don't trade
    if kelly_pct <= 0:
        return 0.0

    # Apply fractional Kelly
    position_pct = kelly_pct * fraction

    # Cap
    position_pct = min(position_pct, max_position_pct)

    position_value = capital * position_pct
    return position_value / entry_price
