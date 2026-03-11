from __future__ import annotations

import uuid
from datetime import datetime, timezone

import ccxt

from .base import (
    Account,
    Broker,
    Order,
    OrderSide,
    OrderStatus,
    OrderType,
    Position,
)


class CCXTBroker(Broker):
    """Crypto exchange broker using CCXT unified API.

    Supports any exchange that CCXT supports (Binance, Coinbase, Kraken, etc.).
    """

    def __init__(
        self,
        exchange_id: str = "binance",
        api_key: str = "",
        secret: str = "",
        sandbox: bool = True,
    ):
        exchange_class = getattr(ccxt, exchange_id, None)
        if exchange_class is None:
            raise ValueError(f"Unknown exchange: {exchange_id}")

        config: dict = {"enableRateLimit": True}
        if api_key:
            config["apiKey"] = api_key
        if secret:
            config["secret"] = secret

        self.exchange: ccxt.Exchange = exchange_class(config)

        if sandbox:
            self.exchange.set_sandbox_mode(True)

    def submit_order(
        self,
        symbol: str,
        side: OrderSide,
        quantity: float,
        order_type: OrderType = OrderType.MARKET,
        price: float | None = None,
        stop_price: float | None = None,
    ) -> Order:
        ccxt_side = "buy" if side == OrderSide.BUY else "sell"
        ccxt_type = "market" if order_type == OrderType.MARKET else "limit"

        params = {}
        if stop_price is not None:
            params["stopPrice"] = stop_price

        result = self.exchange.create_order(
            symbol=symbol,
            type=ccxt_type,
            side=ccxt_side,
            amount=quantity,
            price=price,
            params=params,
        )

        return Order(
            id=result.get("id", str(uuid.uuid4())[:8]),
            symbol=symbol,
            side=side,
            quantity=quantity,
            order_type=order_type,
            price=price,
            stop_price=stop_price,
            status=self._map_status(result.get("status", "open")),
            filled_price=result.get("average"),
            filled_quantity=result.get("filled", 0.0),
            created_at=datetime.now(timezone.utc),
        )

    def cancel_order(self, order_id: str) -> bool:
        try:
            self.exchange.cancel_order(order_id)
            return True
        except Exception:
            return False

    def get_order(self, order_id: str) -> Order | None:
        try:
            # Most exchanges need the symbol; we try without
            result = self.exchange.fetch_order(order_id)
            return Order(
                id=result["id"],
                symbol=result["symbol"],
                side=OrderSide.BUY if result["side"] == "buy" else OrderSide.SELL,
                quantity=result.get("amount", 0),
                order_type=OrderType.MARKET,
                status=self._map_status(result.get("status", "unknown")),
                filled_price=result.get("average"),
                filled_quantity=result.get("filled", 0),
            )
        except Exception:
            return None

    def get_position(self, symbol: str) -> Position | None:
        positions = self.get_positions()
        for pos in positions:
            if pos.symbol == symbol:
                return pos
        return None

    def get_positions(self) -> list[Position]:
        try:
            balances = self.exchange.fetch_balance()
            positions = []
            for currency, balance in balances.get("total", {}).items():
                if balance and balance > 0 and currency != "USDT":
                    positions.append(
                        Position(
                            symbol=f"{currency}/USDT",
                            quantity=balance,
                            avg_entry_price=0.0,  # Not tracked by spot exchanges
                            current_price=0.0,
                        )
                    )
            return positions
        except Exception:
            return []

    def get_account(self) -> Account:
        try:
            balance = self.exchange.fetch_balance()
            usdt = balance.get("USDT", {})
            total = usdt.get("total", 0.0) or 0.0
            free = usdt.get("free", 0.0) or 0.0

            return Account(
                equity=total,
                cash=free,
                buying_power=free,
                positions=self.get_positions(),
            )
        except Exception:
            return Account(equity=0, cash=0, buying_power=0)

    def close_position(self, symbol: str) -> Order | None:
        pos = self.get_position(symbol)
        if pos is None or pos.quantity <= 0:
            return None

        return self.submit_order(
            symbol=symbol,
            side=OrderSide.SELL,
            quantity=pos.quantity,
            order_type=OrderType.MARKET,
        )

    @staticmethod
    def _map_status(status: str) -> OrderStatus:
        mapping = {
            "open": OrderStatus.PENDING,
            "closed": OrderStatus.FILLED,
            "canceled": OrderStatus.CANCELLED,
            "expired": OrderStatus.CANCELLED,
            "rejected": OrderStatus.REJECTED,
        }
        return mapping.get(status, OrderStatus.PENDING)
