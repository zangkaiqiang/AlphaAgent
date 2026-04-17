"""Portfolio: tracks cash, positions, and converts signals into sized orders.

For A-share, enforces T+1 (shares bought today cannot be sold today) and
lot size of 100. Position sizing follows a simple target-percent model:
each BUY signal allocates ``target_pct`` of total equity to that symbol.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from uuid import uuid4

from alphaagent.core.event_bus import EventBus
from alphaagent.core.events import (
    FillEvent,
    MarketEvent,
    OrderEvent,
    SignalEvent,
)
from alphaagent.core.types import OrderType, Side

LOT_SIZE = 100


@dataclass
class Position:
    symbol: str
    quantity: int = 0
    avg_cost: float = 0.0
    # shares bought on a given date (T+1 lock). Maps date -> shares bought.
    locked_by_date: dict[date, int] = field(default_factory=dict)

    def available_to_sell(self, today: date) -> int:
        locked = sum(shares for d, shares in self.locked_by_date.items() if d >= today)
        return max(0, self.quantity - locked)

    def apply_fill(self, fill: FillEvent) -> None:
        if fill.side == Side.BUY:
            new_qty = self.quantity + fill.quantity
            if new_qty > 0:
                self.avg_cost = (
                    self.avg_cost * self.quantity + fill.fill_price * fill.quantity
                ) / new_qty
            self.quantity = new_qty
            d = fill.timestamp.date()
            self.locked_by_date[d] = self.locked_by_date.get(d, 0) + fill.quantity
        else:
            self.quantity -= fill.quantity
            if self.quantity <= 0:
                self.quantity = 0
                self.avg_cost = 0.0


class Portfolio:
    def __init__(
        self,
        initial_cash: float,
        event_bus: EventBus,
        target_pct: float = 0.2,
        commission_rate: float = 3e-4,
        min_commission: float = 5.0,
        stamp_tax_rate: float = 1e-3,
    ):
        self.initial_cash = initial_cash
        self.cash = initial_cash
        self.event_bus = event_bus
        self.target_pct = target_pct
        self.commission_rate = commission_rate
        self.min_commission = min_commission
        self.stamp_tax_rate = stamp_tax_rate

        self.positions: dict[str, Position] = {}
        self._last_price: dict[str, float] = {}
        self.equity_curve: list[tuple[datetime, float]] = []

    # ---- event handlers -------------------------------------------------

    def handle_market(self, event: MarketEvent) -> None:
        self._last_price[event.bar.symbol] = event.bar.close
        self.equity_curve.append((event.bar.timestamp, self.equity()))

    def handle_signal(self, event: SignalEvent) -> None:
        order = self._size_order(event)
        if order is not None:
            self.event_bus.put(order)

    def handle_fill(self, event: FillEvent) -> None:
        pos = self.positions.setdefault(event.symbol, Position(symbol=event.symbol))
        notional = event.fill_price * event.quantity
        if event.side == Side.BUY:
            self.cash -= notional + event.total_cost
        else:
            self.cash += notional - event.total_cost
        pos.apply_fill(event)

    # ---- sizing ---------------------------------------------------------

    def _size_order(self, signal: SignalEvent) -> OrderEvent | None:
        price = self._last_price.get(signal.symbol)
        if price is None or price <= 0:
            return None

        if signal.side == Side.BUY:
            target_value = self.equity() * self.target_pct * signal.strength
            current_value = self._position_value(signal.symbol)
            to_buy_value = target_value - current_value
            if to_buy_value <= 0:
                return None
            raw_shares = int(to_buy_value / price)
            shares = (raw_shares // LOT_SIZE) * LOT_SIZE
            if shares <= 0:
                return None
            cost = shares * price * (1 + self.commission_rate)
            if cost > self.cash:
                return None
            return OrderEvent(
                timestamp=signal.timestamp,
                symbol=signal.symbol,
                side=Side.BUY,
                quantity=shares,
                order_type=OrderType.MARKET,
                order_id=str(uuid4()),
            )

        pos = self.positions.get(signal.symbol)
        if pos is None or pos.quantity <= 0:
            return None
        sellable = pos.available_to_sell(signal.timestamp.date())
        if sellable <= 0:
            return None
        return OrderEvent(
            timestamp=signal.timestamp,
            symbol=signal.symbol,
            side=Side.SELL,
            quantity=sellable,
            order_type=OrderType.MARKET,
            order_id=str(uuid4()),
        )

    # ---- valuation ------------------------------------------------------

    def _position_value(self, symbol: str) -> float:
        pos = self.positions.get(symbol)
        if pos is None:
            return 0.0
        price = self._last_price.get(symbol, pos.avg_cost)
        return pos.quantity * price

    def equity(self) -> float:
        positions_value = sum(self._position_value(s) for s in self.positions)
        return self.cash + positions_value

    def snapshot_positions(self) -> dict[str, int]:
        return {s: p.quantity for s, p in self.positions.items() if p.quantity > 0}
