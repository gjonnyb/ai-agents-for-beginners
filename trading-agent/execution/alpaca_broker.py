from __future__ import annotations

from datetime import datetime, timezone

from .base import (
    Account,
    Broker,
    Order,
    OrderSide,
    OrderStatus,
    OrderType,
    Position,
)


def _map_order_status(alpaca_status: str) -> OrderStatus:
    mapping = {
        "new": OrderStatus.PENDING,
        "accepted": OrderStatus.PENDING,
        "pending_new": OrderStatus.PENDING,
        "filled": OrderStatus.FILLED,
        "partially_filled": OrderStatus.PARTIALLY_FILLED,
        "canceled": OrderStatus.CANCELLED,
        "expired": OrderStatus.CANCELLED,
        "rejected": OrderStatus.REJECTED,
    }
    return mapping.get(alpaca_status, OrderStatus.PENDING)


class AlpacaBroker(Broker):
    """Alpaca Markets broker integration for stocks/ETFs.

    Supports both paper and live trading via Alpaca's API.
    Paper trading URL: https://paper-api.alpaca.markets
    Live trading URL: https://api.alpaca.markets
    """

    def __init__(
        self,
        api_key: str,
        secret_key: str,
        base_url: str = "https://paper-api.alpaca.markets",
    ):
        import alpaca_trade_api as tradeapi

        self.api = tradeapi.REST(
            key_id=api_key,
            secret_key=secret_key,
            base_url=base_url,
            api_version="v2",
        )

    def submit_order(
        self,
        symbol: str,
        side: OrderSide,
        quantity: float,
        order_type: OrderType = OrderType.MARKET,
        price: float | None = None,
        stop_price: float | None = None,
    ) -> Order:
        alpaca_side = "buy" if side == OrderSide.BUY else "sell"
        alpaca_type = {
            OrderType.MARKET: "market",
            OrderType.LIMIT: "limit",
            OrderType.STOP: "stop",
            OrderType.STOP_LIMIT: "stop_limit",
        }[order_type]

        kwargs: dict = {
            "symbol": symbol,
            "qty": quantity,
            "side": alpaca_side,
            "type": alpaca_type,
            "time_in_force": "day",
        }
        if price is not None and order_type in (OrderType.LIMIT, OrderType.STOP_LIMIT):
            kwargs["limit_price"] = price
        if stop_price is not None and order_type in (OrderType.STOP, OrderType.STOP_LIMIT):
            kwargs["stop_price"] = stop_price

        result = self.api.submit_order(**kwargs)

        return Order(
            id=result.id,
            symbol=symbol,
            side=side,
            quantity=float(result.qty),
            order_type=order_type,
            price=price,
            stop_price=stop_price,
            status=_map_order_status(result.status),
            filled_price=float(result.filled_avg_price) if result.filled_avg_price else None,
            filled_quantity=float(result.filled_qty) if result.filled_qty else 0.0,
            created_at=result.created_at,
        )

    def cancel_order(self, order_id: str) -> bool:
        try:
            self.api.cancel_order(order_id)
            return True
        except Exception:
            return False

    def get_order(self, order_id: str) -> Order | None:
        try:
            result = self.api.get_order(order_id)
            return Order(
                id=result.id,
                symbol=result.symbol,
                side=OrderSide.BUY if result.side == "buy" else OrderSide.SELL,
                quantity=float(result.qty),
                order_type=OrderType.MARKET,
                status=_map_order_status(result.status),
                filled_price=float(result.filled_avg_price) if result.filled_avg_price else None,
                filled_quantity=float(result.filled_qty) if result.filled_qty else 0.0,
            )
        except Exception:
            return None

    def get_position(self, symbol: str) -> Position | None:
        try:
            pos = self.api.get_position(symbol)
            return Position(
                symbol=pos.symbol,
                quantity=float(pos.qty),
                avg_entry_price=float(pos.avg_entry_price),
                current_price=float(pos.current_price),
                unrealized_pnl=float(pos.unrealized_pl),
                market_value=float(pos.market_value),
            )
        except Exception:
            return None

    def get_positions(self) -> list[Position]:
        positions = self.api.list_positions()
        return [
            Position(
                symbol=p.symbol,
                quantity=float(p.qty),
                avg_entry_price=float(p.avg_entry_price),
                current_price=float(p.current_price),
                unrealized_pnl=float(p.unrealized_pl),
                market_value=float(p.market_value),
            )
            for p in positions
        ]

    def get_account(self) -> Account:
        acct = self.api.get_account()
        return Account(
            equity=float(acct.equity),
            cash=float(acct.cash),
            buying_power=float(acct.buying_power),
            positions=self.get_positions(),
        )

    def close_position(self, symbol: str) -> Order | None:
        try:
            result = self.api.close_position(symbol)
            return Order(
                id=result.id if hasattr(result, "id") else "close",
                symbol=symbol,
                side=OrderSide.SELL,
                quantity=0,
                order_type=OrderType.MARKET,
                status=OrderStatus.FILLED,
            )
        except Exception:
            return None
