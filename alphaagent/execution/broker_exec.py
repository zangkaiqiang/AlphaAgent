"""Bridge: routes ORDER events to a Broker and republishes FillEvents."""

from __future__ import annotations

from alphaagent.broker.base import Broker
from alphaagent.core.event_bus import EventBus
from alphaagent.core.events import FillEvent, MarketEvent, OrderEvent
from alphaagent.execution.base import ExecutionHandler


class BrokerExecutionHandler(ExecutionHandler):
    """ExecutionHandler backed by a Broker.

    The broker delivers fills asynchronously via its ``on_fill`` callback;
    this handler wires that callback back onto the event bus so the rest
    of the engine (portfolio, metrics, logs) sees FillEvents the same way
    it does in a backtest.

    If the broker also wants to see bars (as PaperBroker does to fill
    pending orders), ``handle_market`` forwards them.
    """

    def __init__(self, broker: Broker, event_bus: EventBus):
        self.broker = broker
        self.event_bus = event_bus
        broker.on_fill(self._on_fill)

    def _on_fill(self, fill: FillEvent) -> None:
        self.event_bus.put(fill)

    def handle_market(self, event: MarketEvent) -> None:
        forward = getattr(self.broker, "handle_market", None)
        if forward is not None:
            forward(event)

    def handle_order(self, event: OrderEvent) -> None:
        if event.quantity <= 0:
            return
        self.broker.place_order(event)
