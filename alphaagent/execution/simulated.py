"""Simulated execution: fills at last known close with A-share commissions."""

from __future__ import annotations

from alphaagent.core.event_bus import EventBus
from alphaagent.core.events import FillEvent, MarketEvent, OrderEvent
from alphaagent.core.types import Side
from alphaagent.execution.base import ExecutionHandler


class SimulatedExecutionHandler(ExecutionHandler):
    """Market orders fill at the next bar's open (conservative). For
    simplicity in this scaffold we fill at the last observed close. The
    backtest engine can swap in next-bar-open fills by calling
    ``set_pending_fill_price`` before dispatch.

    Commission model (A-share):
      - commission:    max(rate * notional, min_commission)
      - stamp tax:     rate * notional, SELL-side only
    """

    def __init__(
        self,
        event_bus: EventBus,
        commission_rate: float = 3e-4,
        min_commission: float = 5.0,
        stamp_tax_rate: float = 1e-3,
        slippage_bps: float = 0.0,
    ):
        self.event_bus = event_bus
        self.commission_rate = commission_rate
        self.min_commission = min_commission
        self.stamp_tax_rate = stamp_tax_rate
        self.slippage_bps = slippage_bps
        self._last_price: dict[str, float] = {}

    def handle_market(self, event: MarketEvent) -> None:
        self._last_price[event.bar.symbol] = event.bar.close

    def handle_order(self, event: OrderEvent) -> None:
        price = self._last_price.get(event.symbol)
        if price is None:
            return  # no price observed yet; drop silently

        # Apply slippage: BUY pays more, SELL receives less.
        slip = price * self.slippage_bps / 10_000
        fill_price = price + slip if event.side == Side.BUY else price - slip

        notional = fill_price * event.quantity
        commission = max(notional * self.commission_rate, self.min_commission)
        stamp_tax = notional * self.stamp_tax_rate if event.side == Side.SELL else 0.0

        self.event_bus.put(
            FillEvent(
                timestamp=event.timestamp,
                symbol=event.symbol,
                side=event.side,
                quantity=event.quantity,
                fill_price=fill_price,
                commission=commission,
                stamp_tax=stamp_tax,
                order_id=event.order_id,
            )
        )
