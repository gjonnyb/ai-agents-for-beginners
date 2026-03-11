#!/usr/bin/env python3
"""Elliott Wave Trading Agent — CLI Entry Point.

Usage:
    python main.py research --pattern "Elliott Wave 3 with RSI confirmation"
    python main.py backtest --assets SPY,QQQ,AAPL --start 2020-01-01
    python main.py paper --assets AAPL --capital 10000
    python main.py live --assets AAPL --capital 10000
"""

import argparse
import logging
import sys
from pathlib import Path

# Add trading-agent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from config.settings import Settings, TradingMode, get_settings
from data.yfinance_provider import YFinanceProvider
from data.ccxt_provider import CCXTProvider
from signals.wave3_rsi import Wave3RSISignal
from execution.paper_broker import PaperBroker
from execution.alpaca_broker import AlpacaBroker
from execution.ccxt_broker import CCXTBroker
from agents.orchestrator import Orchestrator


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("trading-agent")


def create_data_provider(args, settings: Settings):
    """Create the appropriate data provider based on asset types."""
    # If any asset has "/" in it, it's likely crypto
    assets = args.assets.split(",") if hasattr(args, "assets") and args.assets else []
    has_crypto = any("/" in a for a in assets)

    if has_crypto and not any("/" not in a for a in assets):
        # All crypto
        return CCXTProvider(
            exchange_id=settings.ccxt_exchange,
            api_key=settings.ccxt_api_key,
            secret=settings.ccxt_secret,
        )

    # Default to yfinance (works for stocks, ETFs, forex)
    return YFinanceProvider()


def create_broker(settings: Settings, capital: float = 10_000.0):
    """Create the appropriate broker based on trading mode."""
    mode = settings.trading_mode

    if mode in (TradingMode.RESEARCH, TradingMode.BACKTEST, TradingMode.PAPER):
        return PaperBroker(initial_capital=capital)
    elif mode == TradingMode.LIVE:
        if settings.alpaca_api_key:
            return AlpacaBroker(
                api_key=settings.alpaca_api_key,
                secret_key=settings.alpaca_secret_key,
                base_url=settings.alpaca_base_url,
            )
        elif settings.ccxt_api_key:
            return CCXTBroker(
                exchange_id=settings.ccxt_exchange,
                api_key=settings.ccxt_api_key,
                secret=settings.ccxt_secret,
                sandbox=False,
            )
        else:
            logger.error("No broker credentials configured for live trading.")
            sys.exit(1)

    return PaperBroker(initial_capital=capital)


def cmd_research(args, settings: Settings):
    """Handle the research command."""
    data_provider = YFinanceProvider()
    broker = PaperBroker()
    signal = Wave3RSISignal()

    orchestrator = Orchestrator(settings, data_provider, signal, broker)

    if args.pattern:
        print(f"\nResearching pattern: {args.pattern}\n")
        result = orchestrator.run_research(pattern_description=args.pattern)
        print(result)
    elif args.assets:
        # Run backtest first, then analyze with AI
        assets = [a.strip() for a in args.assets.split(",")]
        timeframes = [t.strip() for t in args.timeframes.split(",")]

        reports, report_str = orchestrator.run_backtest(
            assets=assets,
            timeframes=timeframes,
            start=args.start,
            end=args.end,
        )
        print(report_str)

        if reports:
            print("\n\nAI Analysis:\n")
            analysis = orchestrator.run_research(reports=reports)
            print(analysis)
    else:
        print("Provide --pattern or --assets for research.")


def cmd_backtest(args, settings: Settings):
    """Handle the backtest command."""
    assets = [a.strip() for a in args.assets.split(",")]
    timeframes = [t.strip() for t in args.timeframes.split(",")]

    data_provider = create_data_provider(args, settings)
    broker = PaperBroker(initial_capital=args.capital)
    signal = Wave3RSISignal()

    orchestrator = Orchestrator(settings, data_provider, signal, broker)

    reports, report_str = orchestrator.run_backtest(
        assets=assets,
        timeframes=timeframes,
        start=args.start,
        end=args.end,
        initial_capital=args.capital,
    )
    print(report_str)


def cmd_paper(args, settings: Settings):
    """Handle the paper trading command."""
    settings.trading_mode = TradingMode.PAPER
    assets = [a.strip() for a in args.assets.split(",")]

    data_provider = create_data_provider(args, settings)
    broker = PaperBroker(initial_capital=args.capital)
    signal = Wave3RSISignal()

    orchestrator = Orchestrator(settings, data_provider, signal, broker)

    print(f"\nStarting paper trading: {assets}")
    print(f"Capital: ${args.capital:,.2f}")
    print(f"Risk per trade: {settings.default_risk_per_trade:.1%}\n")

    orchestrator.run_trading_loop(
        assets=assets,
        timeframe=args.timeframe,
        interval_seconds=args.interval,
    )


def cmd_live(args, settings: Settings):
    """Handle the live trading command."""
    settings.trading_mode = TradingMode.LIVE
    assets = [a.strip() for a in args.assets.split(",")]

    print("\n⚠  LIVE TRADING MODE")
    print("This will execute real trades with real money.")
    confirm = input("Type 'YES' to confirm: ")
    if confirm != "YES":
        print("Aborted.")
        return

    data_provider = create_data_provider(args, settings)
    broker = create_broker(settings, args.capital)
    signal = Wave3RSISignal()

    orchestrator = Orchestrator(settings, data_provider, signal, broker)

    orchestrator.run_trading_loop(
        assets=assets,
        timeframe=args.timeframe,
        interval_seconds=args.interval,
    )


def main():
    parser = argparse.ArgumentParser(
        description="Elliott Wave Trading Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Research
    p_research = subparsers.add_parser("research", help="Research patterns with AI")
    p_research.add_argument("--pattern", type=str, help="Pattern description to research")
    p_research.add_argument("--assets", type=str, help="Comma-separated assets to analyze")
    p_research.add_argument("--timeframes", type=str, default="1d", help="Timeframes (default: 1d)")
    p_research.add_argument("--start", type=str, help="Start date (YYYY-MM-DD)")
    p_research.add_argument("--end", type=str, help="End date (YYYY-MM-DD)")

    # Backtest
    p_backtest = subparsers.add_parser("backtest", help="Run backtests across assets")
    p_backtest.add_argument("--assets", type=str, required=True, help="Comma-separated assets")
    p_backtest.add_argument("--timeframes", type=str, default="1d", help="Timeframes (default: 1d)")
    p_backtest.add_argument("--start", type=str, help="Start date")
    p_backtest.add_argument("--end", type=str, help="End date")
    p_backtest.add_argument("--capital", type=float, default=10000, help="Initial capital (default: 10000)")

    # Paper
    p_paper = subparsers.add_parser("paper", help="Paper trade with simulated execution")
    p_paper.add_argument("--assets", type=str, required=True, help="Comma-separated assets")
    p_paper.add_argument("--capital", type=float, default=10000, help="Initial capital")
    p_paper.add_argument("--timeframe", type=str, default="1d", help="Timeframe (default: 1d)")
    p_paper.add_argument("--interval", type=int, default=60, help="Check interval in seconds")

    # Live
    p_live = subparsers.add_parser("live", help="Live trading (real money)")
    p_live.add_argument("--assets", type=str, required=True, help="Comma-separated assets")
    p_live.add_argument("--capital", type=float, default=10000, help="Account capital reference")
    p_live.add_argument("--timeframe", type=str, default="1d", help="Timeframe")
    p_live.add_argument("--interval", type=int, default=60, help="Check interval in seconds")

    args = parser.parse_args()
    settings = get_settings()

    if args.command is None:
        parser.print_help()
        return

    commands = {
        "research": cmd_research,
        "backtest": cmd_backtest,
        "paper": cmd_paper,
        "live": cmd_live,
    }

    commands[args.command](args, settings)


if __name__ == "__main__":
    main()
