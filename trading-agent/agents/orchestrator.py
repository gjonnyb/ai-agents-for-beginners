from __future__ import annotations

import logging
import time
from datetime import datetime, timezone

from config.settings import Settings, TradingMode
from data.base import DataProvider
from signals.base import Signal, TradeSignal, Direction
from execution.base import Broker, OrderSide, OrderType
from risk.portfolio_risk import PortfolioRiskManager, PositionInfo
from risk.position_sizing import fixed_fractional_size
from backtest.engine import BacktestEngine, BacktestResult
from backtest.report import generate_report, print_report, AssetReport
from .research_agent import ResearchAgent
from .trade_planner import TradePlanner, TradePlan

logger = logging.getLogger(__name__)


class Orchestrator:
    """Main coordinator for the trading agent system.

    Modes:
    - research: Analyze patterns and backtest results using AI
    - backtest: Run backtests across assets and generate reports
    - paper: Paper trade with real data, simulated execution
    - live: Live trading with real execution
    """

    def __init__(
        self,
        settings: Settings,
        data_provider: DataProvider,
        signal_generator: Signal,
        broker: Broker,
    ):
        self.settings = settings
        self.data_provider = data_provider
        self.signal = signal_generator
        self.broker = broker

        self.risk_manager = PortfolioRiskManager(
            max_positions=settings.max_concurrent_positions,
            max_drawdown_pct=settings.max_portfolio_drawdown,
            max_single_position_pct=settings.max_position_size_pct,
        )
        self.research_agent = ResearchAgent()
        self.trade_planner = TradePlanner()

    # ── Research Mode ──────────────────────────────────────────────

    def run_research(
        self,
        pattern_description: str | None = None,
        reports: list[AssetReport] | None = None,
    ) -> str:
        """Run AI-powered research on a pattern or backtest results."""
        if pattern_description:
            logger.info("Researching pattern: %s", pattern_description[:80])
            return self.research_agent.research_pattern(pattern_description)

        if reports:
            result = self.research_agent.analyze_backtest_results(reports)
            return result.summary

        return "Provide either a pattern description or backtest reports to analyze."

    # ── Backtest Mode ──────────────────────────────────────────────

    def run_backtest(
        self,
        assets: list[str],
        timeframes: list[str] = ["1d"],
        start: str | None = None,
        end: str | None = None,
        initial_capital: float = 10_000.0,
    ) -> tuple[list[AssetReport], str]:
        """Run backtests across multiple assets and timeframes."""
        results: dict[tuple[str, str], BacktestResult] = {}

        engine = BacktestEngine(
            signal_generator=self.signal,
            initial_capital=initial_capital,
            risk_per_trade=self.settings.default_risk_per_trade,
            max_positions=self.settings.max_concurrent_positions,
        )

        total = len(assets) * len(timeframes)
        completed = 0

        for symbol in assets:
            for timeframe in timeframes:
                completed += 1
                logger.info(
                    "[%d/%d] Backtesting %s (%s)...",
                    completed, total, symbol, timeframe,
                )

                try:
                    df = self.data_provider.fetch_ohlcv(
                        symbol, timeframe=timeframe, start=start, end=end
                    )
                    if df.empty or len(df) < 50:
                        logger.warning(
                            "Insufficient data for %s (%s): %d bars",
                            symbol, timeframe, len(df),
                        )
                        continue

                    result = engine.run(df, symbol)
                    results[(symbol, timeframe)] = result
                    logger.info(
                        "  %s (%s): %d trades, %.1f%% return",
                        symbol, timeframe, result.num_trades, result.total_return_pct,
                    )
                except Exception as e:
                    logger.error("Error backtesting %s (%s): %s", symbol, timeframe, e)

        reports = generate_report(results)
        report_str = print_report(reports)
        return reports, report_str

    # ── Live / Paper Trading Mode ──────────────────────────────────

    def run_trading_loop(
        self,
        assets: list[str],
        timeframe: str = "1d",
        interval_seconds: int = 60,
        max_iterations: int | None = None,
    ) -> None:
        """Run the main trading loop (paper or live).

        Fetches latest data, generates signals, applies risk management,
        creates trade plans, and executes orders.
        """
        mode = self.settings.trading_mode
        logger.info("Starting %s trading loop for %s", mode.value, assets)

        iteration = 0
        while max_iterations is None or iteration < max_iterations:
            iteration += 1
            logger.info("─── Iteration %d ───", iteration)

            try:
                self._trading_iteration(assets, timeframe)
            except KeyboardInterrupt:
                logger.info("Trading loop stopped by user.")
                break
            except Exception as e:
                logger.error("Error in trading iteration: %s", e)

            if max_iterations is None or iteration < max_iterations:
                time.sleep(interval_seconds)

    def _trading_iteration(self, assets: list[str], timeframe: str) -> None:
        """Single iteration of the trading loop."""
        account = self.broker.get_account()
        equity = account.equity
        self.risk_manager.update_equity(equity)

        current_positions = [
            PositionInfo(
                symbol=p.symbol,
                direction="long" if p.quantity > 0 else "short",
                value=abs(p.market_value),
                unrealized_pnl=p.unrealized_pnl,
            )
            for p in account.positions
        ]

        for symbol in assets:
            # Skip if we already have a position
            existing = self.broker.get_position(symbol)
            if existing is not None and existing.quantity != 0:
                logger.info("Already positioned in %s, skipping.", symbol)
                continue

            # Fetch latest data
            try:
                df = self.data_provider.fetch_ohlcv(symbol, timeframe=timeframe)
                if df.empty or len(df) < 50:
                    continue
            except Exception as e:
                logger.error("Data fetch error for %s: %s", symbol, e)
                continue

            # Generate signals
            signals = self.signal.generate(df, symbol)
            if not signals:
                continue

            # Take the most recent, highest-confidence signal
            latest_signal = max(signals, key=lambda s: (s.timestamp, s.confidence))
            logger.info("Signal: %s", latest_signal)

            # Risk check
            position_value = self._estimate_position_value(
                latest_signal, equity
            )
            allowed, reason = self.risk_manager.can_open_position(
                current_positions, position_value, equity
            )
            if not allowed:
                logger.warning("Risk blocked: %s", reason)
                continue

            # Create trade plan
            plan = self.trade_planner.create_plan(
                signal=latest_signal,
                account_equity=equity,
                risk_per_trade=self.settings.default_risk_per_trade,
            )
            logger.info("\n%s", plan.summary())

            # Execute
            self._execute_plan(plan)

    def _estimate_position_value(
        self, signal: TradeSignal, equity: float
    ) -> float:
        """Estimate the dollar value of a proposed position."""
        size = fixed_fractional_size(
            capital=equity,
            risk_pct=self.settings.default_risk_per_trade,
            entry_price=signal.entry_price,
            stop_loss=signal.stop_loss,
            max_position_pct=self.settings.max_position_size_pct,
        )
        return size * signal.entry_price

    def _execute_plan(self, plan: TradePlan) -> None:
        """Execute a trade plan by submitting orders to the broker."""
        signal = plan.signal
        side = OrderSide.BUY if signal.direction == Direction.LONG else OrderSide.SELL

        logger.info(
            "Executing: %s %s %.4f units @ $%.4f",
            side.value, signal.symbol, plan.position_size, plan.entry_price,
        )

        try:
            order = self.broker.submit_order(
                symbol=signal.symbol,
                side=side,
                quantity=plan.position_size,
                order_type=OrderType.MARKET,
            )
            logger.info("Order submitted: %s (status: %s)", order.id, order.status.value)
        except Exception as e:
            logger.error("Order execution failed: %s", e)
