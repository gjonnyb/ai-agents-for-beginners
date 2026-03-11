from __future__ import annotations

from enum import Enum
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class TradingMode(str, Enum):
    RESEARCH = "research"
    BACKTEST = "backtest"
    PAPER = "paper"
    LIVE = "live"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # LLM
    anthropic_api_key: str = ""
    openai_api_key: str = ""

    # Alpaca
    alpaca_api_key: str = ""
    alpaca_secret_key: str = ""
    alpaca_base_url: str = "https://paper-api.alpaca.markets"

    # CCXT
    ccxt_exchange: str = "binance"
    ccxt_api_key: str = ""
    ccxt_secret: str = ""

    # Risk
    default_risk_per_trade: float = Field(default=0.02, ge=0.001, le=0.10)
    max_portfolio_drawdown: float = Field(default=0.10, ge=0.01, le=0.50)
    max_concurrent_positions: int = Field(default=6, ge=1, le=50)
    max_position_size_pct: float = Field(default=0.15, ge=0.01, le=1.0)

    # Mode
    trading_mode: TradingMode = TradingMode.PAPER


@lru_cache
def get_settings() -> Settings:
    return Settings()
