"""Broker interface.

The broker is the runtime counterpart to a backtest's execution handler:
it receives orders and, asynchronously, emits fills. For live trading the
fills arrive via a vendor callback (e.g. xtquant); for PaperBroker they
are produced deterministically on the next MarketEvent. Either way the
interface is the same.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable

from alphaagent.core.events import FillEvent, OrderEvent

FillHandler = Callable[[FillEvent], None]


class BrokerError(Exception):
    """Raised when the broker cannot accept or execute an order."""


class Broker(ABC):
    """Abstract broker.

    Lifecycle:
      1. ``connect()``  — open vendor session (noop for PaperBroker).
      2. ``on_fill(handler)``  — subscribe to fill events.
      3. ``place_order(order)``  — submit; broker responds via the fill handler.
      4. ``disconnect()``  — close vendor session.

    Implementations may buffer fills and flush them at deterministic
    points (e.g. next bar), or deliver them as soon as the vendor reports.
    """

    def __init__(self) -> None:
        self._fill_handlers: list[FillHandler] = []

    def on_fill(self, handler: FillHandler) -> None:
        self._fill_handlers.append(handler)

    def _emit_fill(self, fill: FillEvent) -> None:
        for handler in self._fill_handlers:
            handler(fill)

    def connect(self) -> None:  # pragma: no cover - override in live adapters
        pass

    def disconnect(self) -> None:  # pragma: no cover - override in live adapters
        pass

    @abstractmethod
    def place_order(self, order: OrderEvent) -> None: ...

    def cancel_order(self, order_id: str) -> None:  # pragma: no cover - optional
        raise NotImplementedError(f"{type(self).__name__} does not support cancel")

    @abstractmethod
    def positions(self) -> dict[str, int]: ...

    @abstractmethod
    def cash(self) -> float: ...
