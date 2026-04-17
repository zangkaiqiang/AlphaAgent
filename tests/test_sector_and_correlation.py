"""Sector-concentration and pairwise-correlation risk rules."""

from __future__ import annotations

from datetime import datetime, timedelta

import numpy as np
import pytest

from alphaagent.core.event_bus import EventBus
from alphaagent.core.events import MarketEvent, OrderEvent
from alphaagent.core.types import Bar, OrderType, Side
from alphaagent.portfolio.portfolio import Portfolio, Position
from alphaagent.risk.portfolio_risk import (
    MaxPairwiseCorrelation,
    MaxSectorExposure,
    PortfolioRiskManager,
)
from alphaagent.risk.sector_map import CSVSectorMap, DictSectorMap


def _bar(symbol, ts, close):
    return Bar(symbol=symbol, timestamp=ts, open=close, high=close, low=close, close=close, volume=1000)


def _order(symbol, side, qty, ts=datetime(2024, 1, 2)):
    return OrderEvent(
        timestamp=ts,
        symbol=symbol,
        side=side,
        quantity=qty,
        order_type=OrderType.MARKET,
    )


# ---------------------------------------------------------------------------
# SectorMap
# ---------------------------------------------------------------------------


def test_dict_sector_map_returns_none_for_unknown():
    m = DictSectorMap({"600000": "银行"})
    assert m.get("600000") == "银行"
    assert m.get("999999") is None


def test_csv_sector_map_loads(tmp_path):
    path = tmp_path / "sectors.csv"
    path.write_text("symbol,sector\n600000,银行\n600519,白酒\n", encoding="utf-8")
    m = CSVSectorMap(path)
    assert m.get("600000") == "银行"
    assert m.get("600519") == "白酒"
    assert m.get("other") is None


def test_csv_sector_map_rejects_bad_schema(tmp_path):
    path = tmp_path / "sectors.csv"
    path.write_text("symbol,industry\n600000,银行\n", encoding="utf-8")
    with pytest.raises(ValueError):
        CSVSectorMap(path)


# ---------------------------------------------------------------------------
# MaxSectorExposure
# ---------------------------------------------------------------------------


def test_sector_exposure_aggregates_across_symbols():
    bus = EventBus()
    pf = Portfolio(initial_cash=1_000_000, event_bus=bus)
    ts = datetime(2024, 1, 2)
    # Two bank stocks already held, one new bank stock attempting to open.
    pf.handle_market(MarketEvent(bar=_bar("600000", ts, 10.0)))
    pf.handle_market(MarketEvent(bar=_bar("000001", ts, 10.0)))
    pf.handle_market(MarketEvent(bar=_bar("600036", ts, 10.0)))
    pf.positions["600000"] = Position(symbol="600000", quantity=10_000, avg_cost=10.0)
    pf.positions["000001"] = Position(symbol="000001", quantity=10_000, avg_cost=10.0)

    m = DictSectorMap({"600000": "银行", "000001": "银行", "600036": "银行", "600519": "白酒"})
    # Equity = cash 1M + 200k positions = 1.2M. Cap 0.3 => 360k. Bank holds 200k => 160k headroom.
    rule = MaxSectorExposure(max_pct=0.3, sector_map=m)
    allowed = rule.allowed_qty(_order("600036", Side.BUY, 100_000), pf)
    assert allowed == 16_000


def test_sector_exposure_passes_unknown_symbol_through():
    bus = EventBus()
    pf = Portfolio(initial_cash=1_000_000, event_bus=bus)
    pf.handle_market(MarketEvent(bar=_bar("999999", datetime(2024, 1, 2), 10.0)))
    m = DictSectorMap({"600000": "银行"})
    rule = MaxSectorExposure(max_pct=0.1, sector_map=m)
    # Symbol not in map => unconstrained.
    assert rule.allowed_qty(_order("999999", Side.BUY, 1_000), pf) == 1_000


def test_sector_exposure_rejects_when_sector_already_full():
    bus = EventBus()
    pf = Portfolio(initial_cash=500_000, event_bus=bus)
    ts = datetime(2024, 1, 2)
    pf.handle_market(MarketEvent(bar=_bar("600000", ts, 10.0)))
    pf.handle_market(MarketEvent(bar=_bar("600036", ts, 10.0)))
    # Bank already takes 500k of a 1M equity.
    pf.positions["600000"] = Position(symbol="600000", quantity=50_000, avg_cost=10.0)
    m = DictSectorMap({"600000": "银行", "600036": "银行"})
    rule = MaxSectorExposure(max_pct=0.5, sector_map=m)
    assert rule.allowed_qty(_order("600036", Side.BUY, 1_000), pf) == 0


# ---------------------------------------------------------------------------
# MaxPairwiseCorrelation
# ---------------------------------------------------------------------------


def _feed_bars(rule, symbol: str, prices: list[float]):
    """Push MarketEvents through a rule's on_market hook."""
    start = datetime(2024, 1, 2)
    for i, p in enumerate(prices):
        ts = start + timedelta(days=i)
        rule.on_market(MarketEvent(bar=_bar(symbol, ts, p)))


def test_correlation_rejects_highly_correlated_new_symbol():
    rule = MaxPairwiseCorrelation(max_corr=0.85, lookback=30, min_samples=10)
    rng = np.random.default_rng(1)
    noise = rng.normal(0, 0.1, 40)
    base = 10 + noise.cumsum()
    # B = A + tiny noise => highly correlated.
    a = list(base)
    b = list(base + rng.normal(0, 0.01, 40))
    _feed_bars(rule, "A", a)
    _feed_bars(rule, "B", b)

    bus = EventBus()
    pf = Portfolio(initial_cash=1_000_000, event_bus=bus)
    pf.handle_market(MarketEvent(bar=_bar("A", datetime(2024, 3, 1), a[-1])))
    pf.handle_market(MarketEvent(bar=_bar("B", datetime(2024, 3, 1), b[-1])))
    pf.positions["A"] = Position(symbol="A", quantity=1000, avg_cost=a[-1])

    # Holding A; attempting to open B which is ~perfectly correlated.
    assert rule.allowed_qty(_order("B", Side.BUY, 1000), pf) == 0


def test_correlation_allows_uncorrelated_new_symbol():
    rule = MaxPairwiseCorrelation(max_corr=0.85, lookback=30, min_samples=10)
    rng = np.random.default_rng(2)
    a = [10 + x for x in rng.normal(0, 0.1, 40).cumsum()]
    b = [20 + x for x in rng.normal(0, 0.1, 40).cumsum()]  # independent
    _feed_bars(rule, "A", a)
    _feed_bars(rule, "B", b)

    bus = EventBus()
    pf = Portfolio(initial_cash=1_000_000, event_bus=bus)
    pf.handle_market(MarketEvent(bar=_bar("A", datetime(2024, 3, 1), a[-1])))
    pf.handle_market(MarketEvent(bar=_bar("B", datetime(2024, 3, 1), b[-1])))
    pf.positions["A"] = Position(symbol="A", quantity=1000, avg_cost=a[-1])

    assert rule.allowed_qty(_order("B", Side.BUY, 1000), pf) == 1000


def test_correlation_adding_to_existing_position_is_unconstrained():
    rule = MaxPairwiseCorrelation(max_corr=0.85, lookback=30, min_samples=10)
    bus = EventBus()
    pf = Portfolio(initial_cash=1_000_000, event_bus=bus)
    pf.positions["A"] = Position(symbol="A", quantity=1000, avg_cost=10.0)
    # No returns accumulated, but already held => pass.
    assert rule.allowed_qty(_order("A", Side.BUY, 1000), pf) == 1000


def test_correlation_needs_enough_samples():
    rule = MaxPairwiseCorrelation(max_corr=0.5, lookback=30, min_samples=20)
    _feed_bars(rule, "A", [10, 11, 12])  # too few
    bus = EventBus()
    pf = Portfolio(initial_cash=1_000_000, event_bus=bus)
    pf.positions["B"] = Position(symbol="B", quantity=1000, avg_cost=10.0)
    # Not enough samples for A => pass through.
    assert rule.allowed_qty(_order("A", Side.BUY, 1000), pf) == 1000


# ---------------------------------------------------------------------------
# Manager forwards market events to stateful rules
# ---------------------------------------------------------------------------


def test_manager_forwards_market_to_stateful_rule():
    bus = EventBus()
    pf = Portfolio(initial_cash=1_000_000, event_bus=bus)
    rule = MaxPairwiseCorrelation(max_corr=0.5, lookback=30)
    mgr = PortfolioRiskManager(pf, [rule])

    mgr.handle_market(MarketEvent(bar=_bar("A", datetime(2024, 1, 2), 10.0)))
    mgr.handle_market(MarketEvent(bar=_bar("A", datetime(2024, 1, 3), 11.0)))
    assert list(rule._returns["A"]) == [pytest.approx(0.1)]
