from __future__ import annotations

from dataclasses import dataclass

from .engine import BacktestResult
from .metrics import BacktestMetrics, calculate_metrics


@dataclass
class AssetReport:
    """Backtest report for a single asset/timeframe combination."""

    symbol: str
    timeframe: str
    metrics: BacktestMetrics
    result: BacktestResult


def generate_report(
    results: dict[tuple[str, str], BacktestResult],
) -> list[AssetReport]:
    """Generate reports for all backtested asset/timeframe combos.

    Args:
        results: Dict mapping (symbol, timeframe) to BacktestResult.

    Returns:
        List of AssetReport sorted by composite score (best first).
    """
    reports = []
    for (symbol, timeframe), result in results.items():
        metrics = calculate_metrics(result)
        reports.append(
            AssetReport(
                symbol=symbol,
                timeframe=timeframe,
                metrics=metrics,
                result=result,
            )
        )

    return rank_assets(reports)


def rank_assets(reports: list[AssetReport]) -> list[AssetReport]:
    """Rank assets by composite score (highest first)."""
    return sorted(reports, key=lambda r: r.metrics.composite_score(), reverse=True)


def print_report(reports: list[AssetReport]) -> str:
    """Format a ranked report as a readable string."""
    lines = ["=" * 70]
    lines.append("BACKTEST RESULTS — Ranked by Composite Score")
    lines.append("=" * 70)

    for i, report in enumerate(reports, 1):
        lines.append(f"\n#{i}: {report.symbol} ({report.timeframe})")
        lines.append("-" * 40)
        lines.append(report.metrics.summary())

    lines.append("\n" + "=" * 70)

    if reports:
        best = reports[0]
        lines.append(
            f"BEST: {best.symbol} ({best.timeframe}) — "
            f"Score: {best.metrics.composite_score():.3f}, "
            f"Win Rate: {best.metrics.win_rate:.1%}, "
            f"Sharpe: {best.metrics.sharpe_ratio:.2f}"
        )

    return "\n".join(lines)
