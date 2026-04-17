"""Paper broker: simulates a live broker with realistic fill latency.

Unlike the backtest ``SimulatedExecutionHandler`` (which fills at the
current bar's close), PaperBroker queues orders and fills them at the
NEXT bar's open — the same latency you'd see running real orders during
A-share trading hours.

Use it for:
  - pre-production dry-runs with live data
  - regression tests that need realistic fill timing
  - any scenario where "fill at current close" would be lookahead

Cash, commission, and stamp tax accounting mirrors the live account.
"""

from __future__ import annotations

from collections import defaultdict, deque
from datetime import date

from alphaagent.broker.base import Broker, BrokerError
from alphaagent.core.events import FillEvent, MarketEvent, OrderEvent
from alphaagent.core.types import Side


class PaperBroker(Broker):
    def __init__(
        self,
        initial_cash: float,
        commission_rate: float = 3e-4,
        min_commission: float = 5.0,
        stamp_tax_rate: float = 1e-3,
        slippage_bps: float = 5.0,
    ):
        super().__init__()
        self.initial_cash = initial_cash
        self._cash = initial_cash
        self.commission_rate = commission_rate
        self.min_commission = min_commission
        self.stamp_tax_rate = stamp_tax_rate
        self.slippage_bps = slippage_bps
        self._positions: dict[str, int] = defaultdict(int)
        # Shares bought on a given date (T+1 lock).
        self._locked: dict[str, dict[date, int]] = defaultdict(dict)
        self._pending: dict[str, deque[OrderEvent]] = defaultdict(deque)

    # ---- Broker interface ----------------------------------------------

    def place_order(self, order: OrderEvent) -> None:
        if order.quantity <= 0:
            return
        if order.side == Side.SELL:
            available = self._available_to_sell(order.symbol, order.timestamp.date())
            if order.quantity > available:
                raise BrokerError(
                    f"insufficient sellable shares for {order.symbol}: "
                    f"have {available}, want {order.quantity}"
                )
        self._pending[order.symbol].append(order)

    def positions(self) -> dict[str, int]:
        return {s: q for s, q in self._positions.items() if q > 0}

    def cash(self) -> float:
        return self._cash

    # ---- Market-driven fills -------------------------------------------

    def handle_market(self, event: MarketEvent) -> None:
        """Fill any orders pending for this symbol at this bar's open.

        Subscribed by BrokerExecutionHandler.
        """
        symbol = event.bar.symbol
        if symbol not in self._pending or not self._pending[symbol]:
            return
        pending = self._pending[symbol]
        while pending:
            order = pending.popleft()
            # Skip orders placed in the same bar; they fill from the NEXT bar.
            if order.timestamp >= event.bar.timestamp:
                pending.appendleft(order)
                break
            fill = self._fill_order(order, event.bar.open)
            if fill is not None:
                self._emit_fill(fill)

    # ---- internals -----------------------------------------------------

    def _fill_order(self, order: OrderEvent, open_price: float) -> FillEvent | None:
        slip = open_price * self.slippage_bps / 10_000
        price = open_price + slip if order.side == Side.BUY else open_price - slip
        notional = price * order.quantity
        commission = max(notional * self.commission_rate, self.min_commission)
        stamp_tax = notional * self.stamp_tax_rate if order.side == Side.SELL else 0.0

        if order.side == Side.BUY:
            total = notional + commission
            if total > self._cash:
                raise BrokerError(
                    f"insufficient cash for {order.symbol}: need {total:.2f}, have {self._cash:.2f}"
                )
            self._cash -= total
            self._positions[order.symbol] += order.quantity
            d = order.timestamp.date()
            self._locked[order.symbol][d] = (
                self._locked[order.symbol].get(d, 0) + order.quantity
            )
        else:
            self._cash += notional - commission - stamp_tax
            self._positions[order.symbol] -= order.quantity

        return FillEvent(
            timestamp=order.timestamp,  # preserve intent timestamp; bar.timestamp is fill time
            symbol=order.symbol,
            side=order.side,
            quantity=order.quantity,
            fill_price=price,
            commission=commission,
            stamp_tax=stamp_tax,
            order_id=order.order_id,
            strategy_id=order.strategy_id,
        )

    def _available_to_sell(self, symbol: str, today: date) -> int:
        locked = sum(q for d, q in self._locked.get(symbol, {}).items() if d >= today)
        return max(0, self._positions.get(symbol, 0) - locked)
