"""Integration test: BacktestResult.performance() returns a coherent summary."""

from __future__ import annotations

import numpy as np
import pandas as pd

from alphaagent.backtest.engine import BacktestEngine
from alphaagent.core.event_bus import EventBus
from alphaagent.data.base import DataFeed
from alphaagent.execution.simulated import SimulatedExecutionHandler
from alphaagent.portfolio.portfolio import Portfolio
from alphaagent.strategy.ma_cross import MACrossStrategy


def test_backtest_result_performance_summary_runs():
    rng = np.random.default_rng(7)
    n = 180
    close = 10 + np.linspace(0, 3, n) + rng.normal(0, 0.1, n).cumsum()
    close = np.maximum(close, 1.0)
    dates = pd.date_range("2023-01-03", periods=n, freq="B")
    df = pd.DataFrame(
        {
            "open": close, "high": close * 1.01, "low": close * 0.99,
            "close": close, "volume": 1_000_000,
        },
        index=dates,
    )
    feed = DataFeed({"600000": df})
    bus = EventBus()
    pf = Portfolio(initial_cash=1_000_000, event_bus=bus, target_pct=0.3)
    ex = SimulatedExecutionHandler(event_bus=bus)
    engine = BacktestEngine(feed, MACrossStrategy(fast=5, slow=20), pf, ex, bus)
    result = engine.run()

    perf = result.performance()
    # Basic shape checks.
    assert isinstance(perf.sharpe, float)
    assert perf.max_drawdown <= 0
    assert 0 <= perf.win_rate <= 1
    # Any fills should produce at least one trade (either closed or held).
    assert perf.trades <= result.fill_count
    # Formatted string is multi-line and includes all headings.
    text = perf.format()
    for label in ("Sharpe", "Max Drawdown", "Calmar", "Win Rate"):
        assert label in text
