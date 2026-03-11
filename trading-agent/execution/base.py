from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"


class OrderType(str, Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class OrderStatus(str, Enum):
    PENDING = "pending"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


@dataclass
class Order:
    """Represents a trading order."""

    id: str
    symbol: str
    side: OrderSide
    quantity: float
    order_type: OrderType
    price: float | None = None  # Limit price
    stop_price: float | None = None  # Stop trigger price
    status: OrderStatus = OrderStatus.PENDING
    filled_price: float | None = None
    filled_quantity: float = 0.0
    created_at: datetime | None = None
    filled_at: datetime | None = None
    metadata: dict = field(default_factory=dict)


@dataclass
class Position:
    """Represents a current position."""

    symbol: str
    quantity: float  # Positive = long, negative = short
    avg_entry_price: float
    current_price: float = 0.0
    unrealized_pnl: float = 0.0
    market_value: float = 0.0


@dataclass
class Account:
    """Account summary."""

    equity: float
    cash: float
    buying_power: float
    positions: list[Position] = field(default_factory=list)


class Broker(ABC):
    """Abstract base class for broker integrations."""

    @abstractmethod
    def submit_order(
        self,
        symbol: str,
        side: OrderSide,
        quantity: float,
        order_type: OrderType = OrderType.MARKET,
        price: float | None = None,
        stop_price: float | None = None,
    ) -> Order:
        """Submit a new order."""

    @abstractmethod
    def cancel_order(self, order_id: str) -> bool:
        """Cancel a pending order. Returns True if successful."""

    @abstractmethod
    def get_order(self, order_id: str) -> Order | None:
        """Get order status by ID."""

    @abstractmethod
    def get_position(self, symbol: str) -> Position | None:
        """Get current position for a symbol."""

    @abstractmethod
    def get_positions(self) -> list[Position]:
        """Get all open positions."""

    @abstractmethod
    def get_account(self) -> Account:
        """Get account summary."""

    @abstractmethod
    def close_position(self, symbol: str) -> Order | None:
        """Close an entire position for a symbol."""
