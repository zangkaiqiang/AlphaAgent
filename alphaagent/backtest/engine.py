"""Backtest engine: wires data feed, strategy, portfolio, execution."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

import pandas as pd

from alphaagent.core.event_bus import EventBus
from alphaagent.core.events import EventType, MarketEvent
from alphaagent.data.base import DataFeed
from alphaagent.execution.simulated import SimulatedExecutionHandler
from alphaagent.portfolio.portfolio import Portfolio
from alphaagent.strategy.base import Strategy, StrategyContext


@dataclass
class BacktestResult:
    initial_cash: float
    final_equity: float
    equity_curve: list[tuple[datetime, float]] = field(default_factory=list)
    fills: int = 0

    @property
    def total_return(self) -> float:
        if self.initial_cash == 0:
            return 0.0
        return self.final_equity / self.initial_cash - 1

    def to_dataframe(self) -> pd.DataFrame:
        return pd.DataFrame(self.equity_curve, columns=["timestamp", "equity"]).set_index(
            "timestamp"
        )


class BacktestEngine:
    def __init__(
        self,
        feed: DataFeed,
        strategy: Strategy,
        portfolio: Portfolio,
        execution: SimulatedExecutionHandler,
        event_bus: EventBus,
    ):
        self.feed = feed
        self.strategy = strategy
        self.portfolio = portfolio
        self.execution = execution
        self.event_bus = event_bus
        self._fill_count = 0

        self.strategy.bind(
            StrategyContext(event_bus=event_bus, strategy_id=strategy.strategy_id)
        )

        event_bus.subscribe(EventType.MARKET, self.execution.handle_market)
        event_bus.subscribe(EventType.MARKET, self.portfolio.handle_market)
        event_bus.subscribe(EventType.MARKET, self.strategy.handle_market)
        event_bus.subscribe(EventType.SIGNAL, self.portfolio.handle_signal)
        event_bus.subscribe(EventType.ORDER, self.execution.handle_order)
        event_bus.subscribe(EventType.FILL, self.portfolio.handle_fill)
        event_bus.subscribe(EventType.FILL, self._count_fill)

    def _count_fill(self, _event) -> None:
        self._fill_count += 1

    def run(self) -> BacktestResult:
        self.strategy.on_start()
        for bar in self.feed:
            self.event_bus.put(MarketEvent(bar=bar))
            self.event_bus.dispatch()
        self.strategy.on_finish()

        return BacktestResult(
            initial_cash=self.portfolio.initial_cash,
            final_equity=self.portfolio.equity(),
            equity_curve=list(self.portfolio.equity_curve),
            fills=self._fill_count,
        )
