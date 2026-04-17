"""Multi-strategy portfolio and engine integration."""

from __future__ import annotations

from datetime import datetime

import numpy as np
import pandas as pd
import pytest

from alphaagent.backtest.engine import BacktestEngine
from alphaagent.core.event_bus import EventBus
from alphaagent.core.events import FillEvent, MarketEvent, SignalEvent
from alphaagent.core.types import Bar, Side
from alphaagent.data.base import DataFeed
from alphaagent.execution.simulated import SimulatedExecutionHandler
from alphaagent.portfolio.multi import MultiStrategyPortfolio, StrategyAllocation
from alphaagent.portfolio.portfolio import Portfolio
from alphaagent.strategy.base import Strategy
from alphaagent.strategy.ma_cross import MACrossStrategy


def _bar(symbol, ts, close):
    return Bar(symbol=symbol, timestamp=ts, open=close, high=close, low=close, close=close, volume=1000)


# ---------------------------------------------------------------------------
# MultiStrategyPortfolio unit tests
# ---------------------------------------------------------------------------


def test_weights_must_sum_to_one():
    bus = EventBus()
    with pytest.raises(ValueError, match="sum to 1.0"):
        MultiStrategyPortfolio(
            initial_cash=100_000,
            event_bus=bus,
            allocations=[
                StrategyAllocation("a", 0.3),
                StrategyAllocation("b", 0.3),
            ],
        )


def test_duplicate_strategy_id_rejected():
    bus = EventBus()
    with pytest.raises(ValueError, match="duplicate"):
        MultiStrategyPortfolio(
            initial_cash=100_000,
            event_bus=bus,
            allocations=[
                StrategyAllocation("a", 0.5),
                StrategyAllocation("a", 0.5),
            ],
        )


def test_initial_cash_is_sliced_by_weight():
    bus = EventBus()
    pf = MultiStrategyPortfolio(
        initial_cash=1_000_000,
        event_bus=bus,
        allocations=[
            StrategyAllocation("alpha", 0.6),
            StrategyAllocation("beta", 0.4),
        ],
    )
    assert pf.portfolios["alpha"].cash == 600_000
    assert pf.portfolios["beta"].cash == 400_000
    assert pf.equity() == 1_000_000


def test_signals_route_by_strategy_id():
    bus = EventBus()
    orders: list = []
    from alphaagent.core.events import EventType

    bus.subscribe(EventType.ORDER, lambda e: orders.append(e))
    pf = MultiStrategyPortfolio(
        initial_cash=1_000_000,
        event_bus=bus,
        allocations=[
            StrategyAllocation("alpha", 0.5, target_pct=0.5),
            StrategyAllocation("beta", 0.5, target_pct=0.5),
        ],
    )
    ts = datetime(2024, 1, 2)
    pf.handle_market(MarketEvent(bar=_bar("600000", ts, 10.0)))
    pf.handle_signal(
        SignalEvent(timestamp=ts, symbol="600000", side=Side.BUY, strategy_id="alpha")
    )
    bus.dispatch()
    assert len(orders) == 1
    assert orders[0].strategy_id == "alpha"


def test_fills_for_unknown_strategy_are_ignored():
    bus = EventBus()
    pf = MultiStrategyPortfolio(
        initial_cash=1_000_000,
        event_bus=bus,
        allocations=[StrategyAllocation("alpha", 1.0)],
    )
    ts = datetime(2024, 1, 2)
    pf.handle_fill(
        FillEvent(
            timestamp=ts,
            symbol="600000",
            side=Side.BUY,
            quantity=1000,
            fill_price=10.0,
            strategy_id="unknown",
        )
    )
    # Cash unchanged; no position opened.
    assert pf.cash == 1_000_000
    assert pf.portfolios["alpha"].positions == {}


def test_strategies_are_isolated():
    """A BUY fill tagged for alpha must not affect beta's cash or positions."""
    bus = EventBus()
    pf = MultiStrategyPortfolio(
        initial_cash=1_000_000,
        event_bus=bus,
        allocations=[
            StrategyAllocation("alpha", 0.5),
            StrategyAllocation("beta", 0.5),
        ],
    )
    ts = datetime(2024, 1, 2)
    pf.handle_fill(
        FillEvent(
            timestamp=ts,
            symbol="600000",
            side=Side.BUY,
            quantity=1000,
            fill_price=10.0,
            commission=3.0,
            strategy_id="alpha",
        )
    )
    assert pf.portfolios["alpha"].cash == 500_000 - (1000 * 10.0 + 3.0)
    assert pf.portfolios["beta"].cash == 500_000
    assert "600000" in pf.portfolios["alpha"].positions
    assert "600000" not in pf.portfolios["beta"].positions


# ---------------------------------------------------------------------------
# BacktestEngine integration
# ---------------------------------------------------------------------------


class _BuyOnceStrategy(Strategy):
    def __init__(self, strategy_id: str, symbol: str):
        super().__init__(strategy_id=strategy_id)
        self._symbol = symbol
        self._emitted = False

    def on_bar(self, bar: Bar) -> None:
        if not self._emitted and bar.symbol == self._symbol:
            self.ctx.emit_signal(bar, Side.BUY, strength=1.0)
            self._emitted = True


def _frame(symbol_seed: int = 1):
    rng = np.random.default_rng(symbol_seed)
    n = 60
    close = 10 + rng.normal(0, 0.05, n).cumsum()
    close = np.maximum(close, 1.0)
    idx = pd.date_range("2023-01-03", periods=n, freq="B")
    return pd.DataFrame(
        {
            "open": close, "high": close * 1.01, "low": close * 0.99,
            "close": close, "volume": 1_000_000,
        },
        index=idx,
    )


def test_engine_rejects_list_with_single_portfolio():
    feed = DataFeed({"600000": _frame()})
    bus = EventBus()
    pf = Portfolio(initial_cash=100_000, event_bus=bus)
    ex = SimulatedExecutionHandler(event_bus=bus)
    with pytest.raises(TypeError, match="MultiStrategyPortfolio"):
        BacktestEngine(
            feed,
            [MACrossStrategy(strategy_id="a"), MACrossStrategy(strategy_id="b")],
            pf, ex, bus,
        )


def test_engine_runs_two_strategies_with_attribution():
    feed = DataFeed({"600000": _frame(1), "000001": _frame(2)})
    bus = EventBus()
    pf = MultiStrategyPortfolio(
        initial_cash=1_000_000,
        event_bus=bus,
        allocations=[
            StrategyAllocation("alpha", 0.5, target_pct=0.5),
            StrategyAllocation("beta", 0.5, target_pct=0.5),
        ],
    )
    ex = SimulatedExecutionHandler(event_bus=bus)

    engine = BacktestEngine(
        feed,
        [
            _BuyOnceStrategy("alpha", "600000"),
            _BuyOnceStrategy("beta", "000001"),
        ],
        pf, ex, bus,
    )
    result = engine.run()

    # Each strategy should have placed exactly one buy.
    assert result.fill_count == 2
    assert {f.strategy_id for f in result.fills} == {"alpha", "beta"}
    # Per-strategy equity curves exist and are non-empty.
    assert set(result.equity_by_strategy.keys()) == {"alpha", "beta"}
    assert len(result.equity_by_strategy["alpha"]) > 0

    # Alpha only holds 600000; beta only holds 000001.
    alpha_fill = next(f for f in result.fills if f.strategy_id == "alpha")
    beta_fill = next(f for f in result.fills if f.strategy_id == "beta")
    assert alpha_fill.symbol == "600000"
    assert beta_fill.symbol == "000001"

    # Per-strategy performance summaries.
    by_strategy = result.performance_by_strategy()
    assert set(by_strategy.keys()) == {"alpha", "beta"}


def test_engine_rejects_duplicate_strategy_ids():
    feed = DataFeed({"600000": _frame()})
    bus = EventBus()
    pf = MultiStrategyPortfolio(
        initial_cash=1_000_000,
        event_bus=bus,
        allocations=[StrategyAllocation("same", 1.0)],
    )
    ex = SimulatedExecutionHandler(event_bus=bus)
    with pytest.raises(ValueError, match="duplicate"):
        BacktestEngine(
            feed,
            [_BuyOnceStrategy("same", "600000"), _BuyOnceStrategy("same", "600000")],
            pf, ex, bus,
        )
