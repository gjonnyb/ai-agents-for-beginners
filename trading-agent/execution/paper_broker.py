from __future__ import annotations

import uuid
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


class PaperBroker(Broker):
    """Simulated broker for paper trading.

    Fills market orders immediately at the specified price.
    Tracks positions and P&L in memory.
    """

    def __init__(self, initial_capital: float = 10_000.0):
        self.cash = initial_capital
        self.initial_capital = initial_capital
        self._positions: dict[str, Position] = {}
        self._orders: dict[str, Order] = {}
        self._current_prices: dict[str, float] = {}

    def set_price(self, symbol: str, price: float) -> None:
        """Update the current price for a symbol (used by the backtest/live loop)."""
        self._current_prices[symbol] = price
        if symbol in self._positions:
            pos = self._positions[symbol]
            pos.current_price = price
            pos.market_value = abs(pos.quantity) * price
            pos.unrealized_pnl = (price - pos.avg_entry_price) * pos.quantity

    def submit_order(
        self,
        symbol: str,
        side: OrderSide,
        quantity: float,
        order_type: OrderType = OrderType.MARKET,
        price: float | None = None,
        stop_price: float | None = None,
    ) -> Order:
        order_id = str(uuid.uuid4())[:8]
        now = datetime.now(timezone.utc)

        order = Order(
            id=order_id,
            symbol=symbol,
            side=side,
            quantity=quantity,
            order_type=order_type,
            price=price,
            stop_price=stop_price,
            created_at=now,
        )

        if order_type == OrderType.MARKET:
            fill_price = self._current_prices.get(symbol, price or 0.0)
            self._fill_order(order, fill_price, now)
        else:
            order.status = OrderStatus.PENDING

        self._orders[order_id] = order
        return order

    def _fill_order(
        self, order: Order, fill_price: float, fill_time: datetime
    ) -> None:
        """Execute an order fill."""
        order.filled_price = fill_price
        order.filled_quantity = order.quantity
        order.filled_at = fill_time
        order.status = OrderStatus.FILLED

        symbol = order.symbol
        signed_qty = order.quantity if order.side == OrderSide.BUY else -order.quantity

        if symbol in self._positions:
            pos = self._positions[symbol]
            old_qty = pos.quantity
            new_qty = old_qty + signed_qty

            if new_qty == 0:
                # Position closed
                realized_pnl = (fill_price - pos.avg_entry_price) * old_qty
                self.cash += abs(old_qty) * fill_price
                del self._positions[symbol]
                return

            if (old_qty > 0 and signed_qty > 0) or (old_qty < 0 and signed_qty < 0):
                # Adding to position
                total_cost = pos.avg_entry_price * abs(old_qty) + fill_price * abs(signed_qty)
                pos.avg_entry_price = total_cost / abs(new_qty)
            else:
                # Reducing position
                pass

            pos.quantity = new_qty
            self.cash -= signed_qty * fill_price
        else:
            # New position
            self._positions[symbol] = Position(
                symbol=symbol,
                quantity=signed_qty,
                avg_entry_price=fill_price,
                current_price=fill_price,
                market_value=abs(signed_qty) * fill_price,
            )
            self.cash -= signed_qty * fill_price

    def cancel_order(self, order_id: str) -> bool:
        if order_id in self._orders:
            order = self._orders[order_id]
            if order.status == OrderStatus.PENDING:
                order.status = OrderStatus.CANCELLED
                return True
        return False

    def get_order(self, order_id: str) -> Order | None:
        return self._orders.get(order_id)

    def get_position(self, symbol: str) -> Position | None:
        return self._positions.get(symbol)

    def get_positions(self) -> list[Position]:
        return list(self._positions.values())

    def get_account(self) -> Account:
        positions = list(self._positions.values())
        position_value = sum(
            abs(p.quantity) * p.current_price for p in positions
        )
        equity = self.cash + position_value

        return Account(
            equity=equity,
            cash=self.cash,
            buying_power=self.cash,
            positions=positions,
        )

    def close_position(self, symbol: str) -> Order | None:
        pos = self._positions.get(symbol)
        if pos is None:
            return None

        side = OrderSide.SELL if pos.quantity > 0 else OrderSide.BUY
        return self.submit_order(
            symbol=symbol,
            side=side,
            quantity=abs(pos.quantity),
            order_type=OrderType.MARKET,
        )
