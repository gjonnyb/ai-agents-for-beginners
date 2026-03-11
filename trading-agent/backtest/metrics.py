from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .engine import BacktestResult, Trade


@dataclass
class BacktestMetrics:
    """Comprehensive performance metrics for a backtest."""

    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    profit_factor: float
    total_pnl: float
    total_return_pct: float
    avg_win: float
    avg_loss: float
    largest_win: float
    largest_loss: float
    expectancy: float  # Average PnL per trade
    max_drawdown_pct: float
    sharpe_ratio: float
    sortino_ratio: float
    avg_bars_held: float
    exit_breakdown: dict[str, int]  # Count by exit reason

    def composite_score(self) -> float:
        """Single score for ranking asset/timeframe suitability.

        Combines Sharpe, win rate, and profit factor into one metric.
        Higher is better.
        """
        if self.total_trades < 5:
            return 0.0
        sharpe = max(0, self.sharpe_ratio)
        return sharpe * self.win_rate * min(self.profit_factor, 5.0)

    def summary(self) -> str:
        lines = [
            f"Trades: {self.total_trades} ({self.winning_trades}W / {self.losing_trades}L)",
            f"Win Rate: {self.win_rate:.1%}",
            f"Profit Factor: {self.profit_factor:.2f}",
            f"Total PnL: ${self.total_pnl:,.2f} ({self.total_return_pct:+.1f}%)",
            f"Avg Win: ${self.avg_win:,.2f} | Avg Loss: ${self.avg_loss:,.2f}",
            f"Largest Win: ${self.largest_win:,.2f} | Largest Loss: ${self.largest_loss:,.2f}",
            f"Expectancy: ${self.expectancy:,.2f}/trade",
            f"Max Drawdown: {self.max_drawdown_pct:.1%}",
            f"Sharpe Ratio: {self.sharpe_ratio:.2f}",
            f"Sortino Ratio: {self.sortino_ratio:.2f}",
            f"Composite Score: {self.composite_score():.3f}",
        ]
        if self.exit_breakdown:
            lines.append("Exit Breakdown: " + ", ".join(
                f"{k}={v}" for k, v in sorted(self.exit_breakdown.items())
            ))
        return "\n".join(lines)


def calculate_metrics(result: BacktestResult) -> BacktestMetrics:
    """Calculate performance metrics from a BacktestResult."""
    trades = result.trades

    if not trades:
        return BacktestMetrics(
            total_trades=0, winning_trades=0, losing_trades=0,
            win_rate=0.0, profit_factor=0.0, total_pnl=0.0,
            total_return_pct=0.0, avg_win=0.0, avg_loss=0.0,
            largest_win=0.0, largest_loss=0.0, expectancy=0.0,
            max_drawdown_pct=0.0, sharpe_ratio=0.0, sortino_ratio=0.0,
            avg_bars_held=0.0, exit_breakdown={},
        )

    pnls = [t.pnl for t in trades]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]

    total_pnl = sum(pnls)
    gross_profit = sum(wins) if wins else 0.0
    gross_loss = abs(sum(losses)) if losses else 0.0

    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")
    win_rate = len(wins) / len(trades) if trades else 0.0

    # Drawdown from equity curve
    max_dd = _max_drawdown(result.equity_curve)

    # Sharpe and Sortino from trade returns
    returns = np.array([t.pnl_pct for t in trades])
    sharpe = _sharpe_ratio(returns)
    sortino = _sortino_ratio(returns)

    # Exit breakdown
    exit_breakdown: dict[str, int] = {}
    for t in trades:
        exit_breakdown[t.exit_reason] = exit_breakdown.get(t.exit_reason, 0) + 1

    return BacktestMetrics(
        total_trades=len(trades),
        winning_trades=len(wins),
        losing_trades=len(losses),
        win_rate=win_rate,
        profit_factor=profit_factor,
        total_pnl=total_pnl,
        total_return_pct=result.total_return_pct,
        avg_win=np.mean(wins) if wins else 0.0,
        avg_loss=np.mean(losses) if losses else 0.0,
        largest_win=max(wins) if wins else 0.0,
        largest_loss=min(losses) if losses else 0.0,
        expectancy=np.mean(pnls),
        max_drawdown_pct=max_dd,
        sharpe_ratio=sharpe,
        sortino_ratio=sortino,
        avg_bars_held=0.0,  # Could track in Trade if needed
        exit_breakdown=exit_breakdown,
    )


def _max_drawdown(equity_curve: list[float]) -> float:
    """Calculate maximum drawdown percentage from an equity curve."""
    if len(equity_curve) < 2:
        return 0.0
    peak = equity_curve[0]
    max_dd = 0.0
    for val in equity_curve:
        if val > peak:
            peak = val
        dd = (peak - val) / peak if peak > 0 else 0.0
        max_dd = max(max_dd, dd)
    return max_dd


def _sharpe_ratio(returns: np.ndarray, risk_free: float = 0.0) -> float:
    """Annualized Sharpe ratio (assuming daily returns)."""
    if len(returns) < 2:
        return 0.0
    excess = returns - risk_free
    std = np.std(excess, ddof=1)
    if std == 0:
        return 0.0
    return float(np.mean(excess) / std * np.sqrt(252))


def _sortino_ratio(returns: np.ndarray, risk_free: float = 0.0) -> float:
    """Annualized Sortino ratio."""
    if len(returns) < 2:
        return 0.0
    excess = returns - risk_free
    downside = returns[returns < 0]
    if len(downside) < 1:
        return float("inf") if np.mean(excess) > 0 else 0.0
    downside_std = np.std(downside, ddof=1)
    if downside_std == 0:
        return 0.0
    return float(np.mean(excess) / downside_std * np.sqrt(252))
