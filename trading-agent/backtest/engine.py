from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

import pandas as pd

from signals.base import Signal, TradeSignal, Direction


@dataclass
class Trade:
    """A completed (closed) trade."""

    symbol: str
    direction: Direction
    entry_price: float
    entry_time: datetime
    exit_price: float
    exit_time: datetime
    quantity: float
    pnl: float
    pnl_pct: float
    exit_reason: str  # "target_1", "target_2", "stop_loss", "time_stop"
    signal: TradeSignal | None = None


@dataclass
class OpenPosition:
    """A currently open position in the backtest."""

    symbol: str
    direction: Direction
    entry_price: float
    entry_time: datetime
    quantity: float
    stop_loss: float
    targets: list[float]
    targets_hit: int = 0
    signal: TradeSignal | None = None
    bars_held: int = 0
    max_bars: int = 100


class BacktestEngine:
    """Event-driven backtesting engine.

    Uses the same Signal interface as live trading to ensure
    identical signal generation between backtest and production.
    """

    def __init__(
        self,
        signal_generator: Signal,
        initial_capital: float = 10_000.0,
        risk_per_trade: float = 0.02,
        max_positions: int = 3,
        partial_exit_pct: float = 0.5,
        max_bars_in_trade: int = 100,
    ):
        self.signal_generator = signal_generator
        self.initial_capital = initial_capital
        self.risk_per_trade = risk_per_trade
        self.max_positions = max_positions
        self.partial_exit_pct = partial_exit_pct
        self.max_bars_in_trade = max_bars_in_trade

    def run(self, df: pd.DataFrame, symbol: str = "") -> BacktestResult:
        """Run a backtest over the given OHLCV data."""
        capital = self.initial_capital
        equity_curve = [capital]
        trades: list[Trade] = []
        open_positions: list[OpenPosition] = []

        # Generate all signals upfront (same as the signal generator would
        # produce on the full dataset — no look-ahead bias because signals
        # are timestamped and we only act on them at or after their timestamp)
        all_signals = self.signal_generator.generate(df, symbol)

        # Index signals by bar index for O(1) lookup
        signal_map: dict[int, list[TradeSignal]] = {}
        for sig in all_signals:
            # Find the bar index for this signal's timestamp
            bar_idx = df.index.get_indexer([sig.timestamp], method="ffill")[0]
            if bar_idx >= 0:
                signal_map.setdefault(bar_idx, []).append(sig)

        for i in range(len(df)):
            bar = df.iloc[i]
            bar_time = df.index[i]

            # 1. Check open positions against current bar
            closed_this_bar = []
            for pos in open_positions:
                pos.bars_held += 1
                trade = self._check_exit(pos, bar, bar_time)
                if trade is not None:
                    trades.append(trade)
                    capital += trade.pnl
                    closed_this_bar.append(pos)

            for pos in closed_this_bar:
                open_positions.remove(pos)

            # 2. Process new signals at this bar
            bar_signals = signal_map.get(i, [])
            for sig in bar_signals:
                if len(open_positions) >= self.max_positions:
                    break

                # Position sizing: risk X% of capital
                risk_amount = capital * self.risk_per_trade
                risk_per_unit = sig.risk_per_unit
                if risk_per_unit <= 0:
                    continue

                quantity = risk_amount / risk_per_unit

                pos = OpenPosition(
                    symbol=sig.symbol or symbol,
                    direction=sig.direction,
                    entry_price=sig.entry_price,
                    entry_time=sig.timestamp,
                    quantity=quantity,
                    stop_loss=sig.stop_loss,
                    targets=list(sig.targets),
                    signal=sig,
                    max_bars=self.max_bars_in_trade,
                )
                open_positions.append(pos)

            equity_curve.append(capital + self._unrealized_pnl(open_positions, bar))

        # Close any remaining positions at last bar
        last_bar = df.iloc[-1]
        last_time = df.index[-1]
        for pos in open_positions:
            trade = self._force_close(pos, last_bar, last_time)
            trades.append(trade)
            capital += trade.pnl

        equity_curve[-1] = capital

        return BacktestResult(
            trades=trades,
            equity_curve=equity_curve,
            initial_capital=self.initial_capital,
            final_capital=capital,
            symbol=symbol,
            total_signals=len(all_signals),
        )

    def _check_exit(
        self, pos: OpenPosition, bar: pd.Series, bar_time
    ) -> Trade | None:
        """Check if a position should be closed on this bar."""
        high = bar["high"]
        low = bar["low"]

        if pos.direction == Direction.LONG:
            # Check stop loss
            if low <= pos.stop_loss:
                return self._close_trade(pos, pos.stop_loss, bar_time, "stop_loss")

            # Check targets (partial exits)
            for t_idx, target in enumerate(pos.targets):
                if t_idx <= pos.targets_hit and high >= target:
                    if t_idx == 0:
                        # Partial exit at first target, move stop to breakeven
                        pos.targets_hit = 1
                        pos.stop_loss = pos.entry_price  # breakeven stop
                        # Close partial
                        partial_qty = pos.quantity * self.partial_exit_pct
                        pnl = partial_qty * (target - pos.entry_price)
                        pos.quantity -= partial_qty
                        if pos.quantity <= 0:
                            return self._close_trade(pos, target, bar_time, "target_1")
                    elif t_idx == 1:
                        # Full exit at second target
                        return self._close_trade(pos, target, bar_time, "target_2")

            # Time stop
            if pos.bars_held >= pos.max_bars:
                return self._close_trade(pos, bar["close"], bar_time, "time_stop")

        else:  # SHORT
            if high >= pos.stop_loss:
                return self._close_trade(pos, pos.stop_loss, bar_time, "stop_loss")

            for t_idx, target in enumerate(pos.targets):
                if t_idx <= pos.targets_hit and low <= target:
                    if t_idx == 0:
                        pos.targets_hit = 1
                        pos.stop_loss = pos.entry_price
                        partial_qty = pos.quantity * self.partial_exit_pct
                        pnl = partial_qty * (pos.entry_price - target)
                        pos.quantity -= partial_qty
                        if pos.quantity <= 0:
                            return self._close_trade(pos, target, bar_time, "target_1")
                    elif t_idx == 1:
                        return self._close_trade(pos, target, bar_time, "target_2")

            if pos.bars_held >= pos.max_bars:
                return self._close_trade(pos, bar["close"], bar_time, "time_stop")

        return None

    @staticmethod
    def _close_trade(
        pos: OpenPosition, exit_price: float, exit_time, reason: str
    ) -> Trade:
        """Create a Trade from closing an OpenPosition."""
        if pos.direction == Direction.LONG:
            pnl = pos.quantity * (exit_price - pos.entry_price)
        else:
            pnl = pos.quantity * (pos.entry_price - exit_price)

        pnl_pct = (exit_price - pos.entry_price) / pos.entry_price
        if pos.direction == Direction.SHORT:
            pnl_pct = -pnl_pct

        return Trade(
            symbol=pos.symbol,
            direction=pos.direction,
            entry_price=pos.entry_price,
            entry_time=pos.entry_time,
            exit_price=exit_price,
            exit_time=exit_time,
            quantity=pos.quantity,
            pnl=pnl,
            pnl_pct=pnl_pct,
            exit_reason=reason,
            signal=pos.signal,
        )

    @staticmethod
    def _force_close(pos: OpenPosition, bar: pd.Series, bar_time) -> Trade:
        exit_price = bar["close"]
        if pos.direction == Direction.LONG:
            pnl = pos.quantity * (exit_price - pos.entry_price)
        else:
            pnl = pos.quantity * (pos.entry_price - exit_price)

        pnl_pct = (exit_price - pos.entry_price) / pos.entry_price
        if pos.direction == Direction.SHORT:
            pnl_pct = -pnl_pct

        return Trade(
            symbol=pos.symbol,
            direction=pos.direction,
            entry_price=pos.entry_price,
            entry_time=pos.entry_time,
            exit_price=exit_price,
            exit_time=bar_time,
            quantity=pos.quantity,
            pnl=pnl,
            pnl_pct=pnl_pct,
            exit_reason="end_of_data",
            signal=pos.signal,
        )

    @staticmethod
    def _unrealized_pnl(positions: list[OpenPosition], bar: pd.Series) -> float:
        total = 0.0
        price = bar["close"]
        for pos in positions:
            if pos.direction == Direction.LONG:
                total += pos.quantity * (price - pos.entry_price)
            else:
                total += pos.quantity * (pos.entry_price - price)
        return total


@dataclass
class BacktestResult:
    """Container for backtest results."""

    trades: list[Trade]
    equity_curve: list[float]
    initial_capital: float
    final_capital: float
    symbol: str
    total_signals: int

    @property
    def total_return_pct(self) -> float:
        if self.initial_capital == 0:
            return 0.0
        return (self.final_capital - self.initial_capital) / self.initial_capital * 100

    @property
    def num_trades(self) -> int:
        return len(self.trades)
