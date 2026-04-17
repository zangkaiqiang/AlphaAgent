"""BacktestEngine bar filtering via the trading calendar."""

from __future__ import annotations

from datetime import date

import pandas as pd

from alphaagent.backtest.engine import BacktestEngine
from alphaagent.calendar import AShareCalendar
from alphaagent.core.event_bus import EventBus
from alphaagent.data.base import DataFeed
from alphaagent.execution.simulated import SimulatedExecutionHandler
from alphaagent.portfolio.portfolio import Portfolio
from alphaagent.strategy.base import Strategy


class _NoopStrategy(Strategy):
    strategy_id = "noop"

    def on_bar(self, bar):  # pragma: no cover - no signals
        pass


def _frame(index):
    n = len(index)
    return pd.DataFrame(
        {
            "open": [10.0] * n,
            "high": [10.0] * n,
            "low": [10.0] * n,
            "close": [10.0] * n,
            "volume": [1000] * n,
        },
        index=index,
    )


def test_engine_drops_non_trading_days_when_calendar_set():
    # Mix in a Sunday (2024-01-07) that the calendar will reject.
    index = pd.to_datetime(
        ["2024-01-02", "2024-01-03", "2024-01-05", "2024-01-07", "2024-01-08"]
    )
    feed = DataFeed({"600000": _frame(index)})
    cal = AShareCalendar(
        trading_days=[
            date(2024, 1, 2), date(2024, 1, 3), date(2024, 1, 4), date(2024, 1, 5),
            date(2024, 1, 8),
        ]
    )
    bus = EventBus()
    pf = Portfolio(initial_cash=100_000, event_bus=bus)
    ex = SimulatedExecutionHandler(event_bus=bus)
    engine = BacktestEngine(feed, _NoopStrategy(), pf, ex, bus, calendar=cal)

    result = engine.run()
    assert result.bars_processed == 4
    assert result.bars_skipped == 1


def test_engine_drops_lunch_break_minutes():
    # Five minute bars: three in session, one during lunch, one after close.
    index = pd.to_datetime(
        [
            "2024-01-02 09:30",
            "2024-01-02 11:00",
            "2024-01-02 12:00",  # lunch break - should be skipped
            "2024-01-02 13:30",
            "2024-01-02 15:30",  # after close - should be skipped
        ]
    )
    feed = DataFeed({"600000": _frame(index)})
    cal = AShareCalendar(trading_days=[date(2024, 1, 2)])
    bus = EventBus()
    pf = Portfolio(initial_cash=100_000, event_bus=bus)
    ex = SimulatedExecutionHandler(event_bus=bus)
    engine = BacktestEngine(feed, _NoopStrategy(), pf, ex, bus, calendar=cal)

    result = engine.run()
    assert result.bars_processed == 3
    assert result.bars_skipped == 2


def test_engine_without_calendar_passes_all_bars():
    index = pd.to_datetime(["2024-01-02", "2024-01-07", "2024-01-08"])
    feed = DataFeed({"600000": _frame(index)})
    bus = EventBus()
    pf = Portfolio(initial_cash=100_000, event_bus=bus)
    ex = SimulatedExecutionHandler(event_bus=bus)
    engine = BacktestEngine(feed, _NoopStrategy(), pf, ex, bus)

    result = engine.run()
    assert result.bars_processed == 3
    assert result.bars_skipped == 0
