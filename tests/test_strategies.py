"""Strategy signal-generation tests.

We bind each strategy to a ``StrategyContext`` backed by a local EventBus
subscription and feed a known price series. The assertions check the
emitted signals, not the downstream portfolio/execution (those are tested
elsewhere).
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from alphaagent.core.event_bus import EventBus
from alphaagent.core.events import EventType, SignalEvent
from alphaagent.core.types import Bar, Side
from alphaagent.strategy import (
    BollingerBreakout,
    BollingerReversion,
    CrossSectionalMomentum,
    MACrossStrategy,
    RSIMeanReversion,
)
from alphaagent.strategy.base import StrategyContext
from alphaagent.strategy.rsi import _rsi_from_prices


def _setup(strategy):
    bus = EventBus()
    signals: list[SignalEvent] = []
    bus.subscribe(EventType.SIGNAL, lambda e: signals.append(e))
    strategy.bind(StrategyContext(event_bus=bus, strategy_id=strategy.strategy_id))
    return bus, signals


def _feed(strategy, bus, symbol: str, prices: list[float], start=datetime(2024, 1, 2)):
    for i, price in enumerate(prices):
        ts = start + timedelta(days=i)
        strategy.on_bar(Bar(symbol, ts, price, price, price, price, 1000))
    bus.dispatch()


# ---------------------------------------------------------------------------
# RSI
# ---------------------------------------------------------------------------


def test_rsi_formula_edge_cases():
    assert _rsi_from_prices([1, 2, 3, 4, 5]) == 100.0  # all gains
    assert _rsi_from_prices([5, 4, 3, 2, 1]) == pytest.approx(0.0)


def test_rsi_signals_on_oversold_recovery():
    strat = RSIMeanReversion(period=5, oversold=30, overbought=70)
    bus, signals = _setup(strat)
    # Sharp drop pushes RSI below 30, then recovery bars cross back up.
    prices = [100, 95, 90, 85, 80, 75, 70, 75, 82, 90]
    _feed(strat, bus, "600000", prices)
    buys = [s for s in signals if s.side == Side.BUY]
    assert buys  # at least one BUY fired on the recovery


def test_rsi_signals_on_overbought_pullback():
    strat = RSIMeanReversion(period=5)
    bus, signals = _setup(strat)
    # Sharp rally then pullback.
    prices = [50, 55, 60, 65, 70, 75, 80, 75, 68, 60]
    _feed(strat, bus, "600000", prices)
    sells = [s for s in signals if s.side == Side.SELL]
    assert sells


def test_rsi_rejects_bad_params():
    with pytest.raises(ValueError):
        RSIMeanReversion(period=1)
    with pytest.raises(ValueError):
        RSIMeanReversion(oversold=80, overbought=50)


# ---------------------------------------------------------------------------
# Bollinger
# ---------------------------------------------------------------------------


def test_bollinger_breakout_buys_on_upper_break_and_sells_on_mid_return():
    strat = BollingerBreakout(period=10, k=2.0)
    bus, signals = _setup(strat)
    # 10 flat bars to set up the band, then a spike above upper, then a return to mid.
    prices = [10.0] * 10 + [12.0, 12.5, 11.0, 10.5, 10.0]
    _feed(strat, bus, "600000", prices)
    buys = [s for s in signals if s.side == Side.BUY]
    sells = [s for s in signals if s.side == Side.SELL]
    assert len(buys) == 1
    assert len(sells) == 1
    assert buys[0].timestamp < sells[0].timestamp


def test_bollinger_breakout_does_not_buy_inside_band():
    strat = BollingerBreakout(period=10, k=2.0)
    bus, signals = _setup(strat)
    prices = [10.0, 10.1, 9.9, 10.05, 9.95] * 4
    _feed(strat, bus, "600000", prices)
    assert [s for s in signals if s.side == Side.BUY] == []


def test_bollinger_reversion_buys_dip_sells_recovery():
    strat = BollingerReversion(period=10, k=2.0)
    bus, signals = _setup(strat)
    # Flat setup, then a dip below lower band, then a rebound above middle.
    prices = [10.0] * 10 + [8.0, 7.5, 8.5, 9.5, 10.0, 10.2]
    _feed(strat, bus, "600000", prices)
    buys = [s for s in signals if s.side == Side.BUY]
    sells = [s for s in signals if s.side == Side.SELL]
    assert len(buys) == 1
    assert len(sells) == 1


# ---------------------------------------------------------------------------
# Cross-sectional momentum
# ---------------------------------------------------------------------------


def test_momentum_holds_top_n_by_return():
    strat = CrossSectionalMomentum(lookback=5, top_n=1, rebalance_days=1)
    bus, signals = _setup(strat)
    # Symbol A rallies; B drifts sideways.
    for i in range(6):
        ts = datetime(2024, 1, 2) + timedelta(days=i)
        strat.on_bar(Bar("A", ts, 10 + i, 10 + i, 10 + i, 10 + i, 1000))
        strat.on_bar(Bar("B", ts, 10, 10, 10, 10, 1000))
    # Next timestamp triggers rebalance based on the prior 5-bar window.
    strat.on_bar(Bar("A", datetime(2024, 1, 9), 16, 16, 16, 16, 1000))
    bus.dispatch()
    buys = [s for s in signals if s.side == Side.BUY]
    assert len(buys) == 1
    assert buys[0].symbol == "A"


def test_momentum_rotates_on_rebalance():
    strat = CrossSectionalMomentum(lookback=3, top_n=1, rebalance_days=1)
    bus, signals = _setup(strat)

    def push(sym, price, day):
        ts = datetime(2024, 1, 2) + timedelta(days=day)
        strat.on_bar(Bar(sym, ts, price, price, price, price, 1000))

    # Phase 1: A strongest.
    for d in range(4):
        push("A", 10 + d, d)
        push("B", 10, d)
    push("A", 14, 4)  # triggers rebalance: BUY A
    bus.dispatch()
    # Phase 2: B becomes strongest; A plateaus.
    for d in range(5, 9):
        push("A", 14, d)
        push("B", 10 + (d - 4) * 2, d)
    push("A", 14, 9)  # triggers rebalance: SELL A, BUY B
    bus.dispatch()

    assert any(s.side == Side.BUY and s.symbol == "A" for s in signals)
    assert any(s.side == Side.SELL and s.symbol == "A" for s in signals)
    assert any(s.side == Side.BUY and s.symbol == "B" for s in signals)


def test_momentum_requires_lookback_bars():
    strat = CrossSectionalMomentum(lookback=10, top_n=1, rebalance_days=1)
    bus, signals = _setup(strat)
    for d in range(5):
        ts = datetime(2024, 1, 2) + timedelta(days=d)
        strat.on_bar(Bar("A", ts, 10 + d, 10 + d, 10 + d, 10 + d, 1000))
        strat.on_bar(Bar("B", ts, 10, 10, 10, 10, 1000))
    bus.dispatch()
    assert signals == []  # not enough history


# ---------------------------------------------------------------------------
# MA cross sanity (existing but covered here too)
# ---------------------------------------------------------------------------


def test_ma_cross_fires_on_golden_cross():
    strat = MACrossStrategy(fast=3, slow=6)
    bus, signals = _setup(strat)
    prices = [10] * 6 + [11, 12, 13, 14, 15]
    _feed(strat, bus, "600000", prices)
    assert any(s.side == Side.BUY for s in signals)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


def test_registry_resolves_all_builtins():
    from alphaagent.strategy import BUILTIN_STRATEGIES, get

    for name in BUILTIN_STRATEGIES:
        cls = get(name)
        assert cls.__name__


def test_registry_unknown_name_lists_available():
    from alphaagent.strategy import get

    with pytest.raises(ValueError, match="available"):
        get("does_not_exist")
