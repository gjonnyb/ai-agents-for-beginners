from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # LLM
    anthropic_api_key: str = ""
    openai_api_key: str = ""

    # Database
    database_url: str = "sqlite:///./contractor_crm.db"

    # App
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    app_debug: bool = True

    # Concentration risk thresholds
    concentration_single_customer_threshold: float = Field(
        default=15.0, description="Flag customers exceeding this % of total revenue"
    )
    concentration_top3_threshold: float = Field(
        default=50.0, description="Flag if top 3 customers exceed this % of total revenue"
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
