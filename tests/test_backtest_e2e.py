"""End-to-end backtest with synthetic data."""

from __future__ import annotations

import pandas as pd

from alphaagent.backtest.engine import BacktestEngine
from alphaagent.core.event_bus import EventBus
from alphaagent.data.base import DataFeed
from alphaagent.execution.simulated import SimulatedExecutionHandler
from alphaagent.portfolio.portfolio import Portfolio
from alphaagent.strategy.ma_cross import MACrossStrategy


def _synthetic_frame(seed: int, n: int = 120) -> pd.DataFrame:
    import numpy as np

    rng = np.random.default_rng(seed)
    # Trending price with noise so MA cross fires.
    drift = np.linspace(0, 2.0, n)
    noise = rng.normal(0, 0.5, n).cumsum() * 0.1
    close = 10 + drift + noise
    close = np.maximum(close, 1.0)
    dates = pd.date_range("2023-01-03", periods=n, freq="B")
    return pd.DataFrame(
        {
            "open": close,
            "high": close * 1.01,
            "low": close * 0.99,
            "close": close,
            "volume": 1_000_000,
            "amount": close * 1_000_000,
        },
        index=dates,
    )


def test_backtest_runs_end_to_end():
    frames = {"600000": _synthetic_frame(seed=1), "000001": _synthetic_frame(seed=2)}
    feed = DataFeed(frames)
    bus = EventBus()
    portfolio = Portfolio(initial_cash=1_000_000, event_bus=bus, target_pct=0.3)
    execution = SimulatedExecutionHandler(event_bus=bus)
    strategy = MACrossStrategy(fast=5, slow=20)

    engine = BacktestEngine(feed, strategy, portfolio, execution, bus)
    result = engine.run()

    assert result.initial_cash == 1_000_000
    assert len(result.equity_curve) == len(frames["600000"]) * 2
    # Should have triggered at least one fill given the trending data.
    assert result.fill_count >= 1
    assert len(result.fills) == result.fill_count
    # Equity must remain finite and non-negative.
    assert result.final_equity > 0
