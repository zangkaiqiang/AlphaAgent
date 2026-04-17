"""Backtest engine: wires data feed, strategy, portfolio, execution."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

import pandas as pd

from alphaagent.calendar.ashare import AShareCalendar
from alphaagent.core.event_bus import EventBus
from alphaagent.core.events import EventType, MarketEvent
from alphaagent.core.types import Bar
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
    bars_processed: int = 0
    bars_skipped: int = 0

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
        calendar: AShareCalendar | None = None,
    ):
        """Wires the event-driven engine.

        If ``calendar`` is provided, bars whose timestamp is not a trading
        day are dropped. For bars with a non-midnight time component
        (i.e. minute bars), the session-hours window is additionally
        enforced.
        """
        self.feed = feed
        self.strategy = strategy
        self.portfolio = portfolio
        self.execution = execution
        self.event_bus = event_bus
        self.calendar = calendar
        self._fill_count = 0
        self._bars_processed = 0
        self._bars_skipped = 0

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

    def _accept_bar(self, bar: Bar) -> bool:
        if self.calendar is None:
            return True
        ts = bar.timestamp
        if not self.calendar.is_trading_day(ts):
            return False
        # Midnight timestamp => daily bar; skip session-hours check.
        if ts.hour == 0 and ts.minute == 0 and ts.second == 0:
            return True
        return self.calendar.is_session_time(ts.time())

    def run(self) -> BacktestResult:
        self.strategy.on_start()
        for bar in self.feed:
            if not self._accept_bar(bar):
                self._bars_skipped += 1
                continue
            self._bars_processed += 1
            self.event_bus.put(MarketEvent(bar=bar))
            self.event_bus.dispatch()
        self.strategy.on_finish()

        return BacktestResult(
            initial_cash=self.portfolio.initial_cash,
            final_equity=self.portfolio.equity(),
            equity_curve=list(self.portfolio.equity_curve),
            fills=self._fill_count,
            bars_processed=self._bars_processed,
            bars_skipped=self._bars_skipped,
        )
