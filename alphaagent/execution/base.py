"""Execution handler base class."""

from __future__ import annotations

from abc import ABC, abstractmethod

from alphaagent.core.events import MarketEvent, OrderEvent


class ExecutionHandler(ABC):
    """Consumes OrderEvents and produces FillEvents.

    Stateful handlers (e.g. simulated fill-at-close, or a paper broker that
    fills at next-bar-open) override ``handle_market`` to track prices.
    """

    @abstractmethod
    def handle_order(self, event: OrderEvent) -> None: ...

    def handle_market(self, event: MarketEvent) -> None:
        """Default: no-op. Override to observe market data."""
