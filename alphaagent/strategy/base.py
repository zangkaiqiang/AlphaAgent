"""Strategy base class. Strategies consume MarketEvents and emit SignalEvents."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from alphaagent.core.event_bus import EventBus
from alphaagent.core.events import MarketEvent, SignalEvent
from alphaagent.core.types import Bar, Side


@dataclass
class StrategyContext:
    """Passed into strategies. Gives read-only access to portfolio state
    and a helper to emit signals without coupling to the EventBus directly.
    """

    event_bus: EventBus
    strategy_id: str
    # Snapshot of current positions (symbol -> shares). Updated by engine.
    positions: dict[str, int] = field(default_factory=dict)
    cash: float = 0.0

    def emit_signal(self, bar: Bar, side: Side, strength: float = 1.0) -> None:
        self.event_bus.put(
            SignalEvent(
                timestamp=bar.timestamp,
                symbol=bar.symbol,
                side=side,
                strength=strength,
                strategy_id=self.strategy_id,
            )
        )


class Strategy(ABC):
    """Base class for all strategies.

    Subclasses implement ``on_bar`` to react to new market data and
    optionally ``on_start`` / ``on_finish`` for setup/teardown.
    """

    strategy_id: str = "base"

    def __init__(self, strategy_id: str | None = None):
        if strategy_id:
            self.strategy_id = strategy_id
        self.ctx: StrategyContext | None = None

    def bind(self, ctx: StrategyContext) -> None:
        self.ctx = ctx

    def on_start(self) -> None:
        pass

    def on_finish(self) -> None:
        pass

    def handle_market(self, event: MarketEvent) -> None:
        self.on_bar(event.bar)

    @abstractmethod
    def on_bar(self, bar: Bar) -> None:
        """Called once per bar. Emit signals via ``self.ctx.emit_signal``."""
