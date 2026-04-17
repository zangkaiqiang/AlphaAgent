"""Multi-strategy portfolio: N sub-portfolios, one per strategy.

Each strategy gets an isolated slice of initial cash and an independent
position book. Signals and fills route by ``strategy_id`` so strategies
cannot accidentally share positions or cash. Aggregate equity is the
sum across sub-portfolios; per-strategy attribution is preserved on each
sub-portfolio's own equity_curve.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from alphaagent.core.event_bus import EventBus
from alphaagent.core.events import FillEvent, MarketEvent, SignalEvent
from alphaagent.portfolio.portfolio import Portfolio


@dataclass(frozen=True, slots=True)
class StrategyAllocation:
    strategy_id: str
    weight: float  # 0..1; weights across all strategies must sum to 1.0
    target_pct: float = 0.2  # per-signal position sizing within the sub-portfolio


class MultiStrategyPortfolio:
    """Interface-compatible with ``Portfolio`` for the event bus.

    ``handle_market`` broadcasts to all sub-portfolios and records an
    aggregate equity snapshot. ``handle_signal`` and ``handle_fill``
    dispatch by ``strategy_id``. Fills or signals with an unknown
    strategy_id are silently dropped, not routed to a default.
    """

    def __init__(
        self,
        initial_cash: float,
        event_bus: EventBus,
        allocations: list[StrategyAllocation],
        commission_rate: float = 3e-4,
        min_commission: float = 5.0,
        stamp_tax_rate: float = 1e-3,
    ):
        if not allocations:
            raise ValueError("at least one strategy allocation required")
        total_weight = sum(a.weight for a in allocations)
        if abs(total_weight - 1.0) > 1e-6:
            raise ValueError(
                f"strategy weights must sum to 1.0, got {total_weight:.4f}"
            )
        seen: set[str] = set()
        for a in allocations:
            if a.strategy_id in seen:
                raise ValueError(f"duplicate strategy_id: {a.strategy_id}")
            seen.add(a.strategy_id)

        self.initial_cash = initial_cash
        self.event_bus = event_bus
        self.portfolios: dict[str, Portfolio] = {
            a.strategy_id: Portfolio(
                initial_cash=initial_cash * a.weight,
                event_bus=event_bus,
                target_pct=a.target_pct,
                commission_rate=commission_rate,
                min_commission=min_commission,
                stamp_tax_rate=stamp_tax_rate,
                strategy_id=a.strategy_id,
            )
            for a in allocations
        }
        self.equity_curve: list[tuple[datetime, float]] = []

    # ---- event bus interface -------------------------------------------

    def handle_market(self, event: MarketEvent) -> None:
        for pf in self.portfolios.values():
            pf.handle_market(event)
        self.equity_curve.append((event.bar.timestamp, self.equity()))

    def handle_signal(self, event: SignalEvent) -> None:
        pf = self.portfolios.get(event.strategy_id)
        if pf is None:
            return
        pf.handle_signal(event)

    def handle_fill(self, event: FillEvent) -> None:
        pf = self.portfolios.get(event.strategy_id)
        if pf is None:
            return
        pf.handle_fill(event)

    # ---- aggregation / portfolio view ----------------------------------

    def equity(self) -> float:
        return sum(pf.equity() for pf in self.portfolios.values())

    @property
    def cash(self) -> float:
        return sum(pf.cash for pf in self.portfolios.values())

    def position_value(self, symbol: str) -> float:
        return sum(pf.position_value(symbol) for pf in self.portfolios.values())

    def gross_value(self) -> float:
        return sum(pf.gross_value() for pf in self.portfolios.values())

    def held_symbols(self) -> set[str]:
        out: set[str] = set()
        for pf in self.portfolios.values():
            out |= pf.held_symbols()
        return out

    def last_price(self, symbol: str) -> float | None:
        for pf in self.portfolios.values():
            p = pf.last_price(symbol)
            if p is not None:
                return p
        return None

    def snapshot_positions(self) -> dict[str, dict[str, int]]:
        """Per-strategy position snapshots."""
        return {sid: pf.snapshot_positions() for sid, pf in self.portfolios.items()}
