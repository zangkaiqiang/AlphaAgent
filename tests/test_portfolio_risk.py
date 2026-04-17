"""Portfolio-level risk rules and end-to-end gating."""

from __future__ import annotations

from datetime import datetime

import pandas as pd
import pytest

from alphaagent.backtest.engine import BacktestEngine
from alphaagent.core.event_bus import EventBus
from alphaagent.core.events import MarketEvent, OrderEvent
from alphaagent.core.types import Bar, OrderType, Side
from alphaagent.data.base import DataFeed
from alphaagent.execution.simulated import SimulatedExecutionHandler
from alphaagent.portfolio.multi import MultiStrategyPortfolio, StrategyAllocation
from alphaagent.portfolio.portfolio import Portfolio
from alphaagent.risk.portfolio_risk import (
    MaxGrossExposure,
    MaxPerSymbolExposure,
    MaxPositionCount,
    PortfolioRiskManager,
)
from alphaagent.strategy.base import Strategy


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
# Rule unit tests
# ---------------------------------------------------------------------------


def test_max_gross_exposure_caps_at_equity_fraction():
    bus = EventBus()
    pf = Portfolio(initial_cash=1_000_000, event_bus=bus)
    ts = datetime(2024, 1, 2)
    pf.handle_market(MarketEvent(bar=_bar("600000", ts, 10.0)))

    rule = MaxGrossExposure(max_pct=0.5)
    # Requesting 100_000 shares at 10 = 1,000,000 notional; cap is 500,000 => 50,000 shares.
    assert rule.allowed_qty(_order("600000", Side.BUY, 100_000), pf) == 50_000


def test_max_per_symbol_exposure_accounts_for_existing_position():
    bus = EventBus()
    pf = Portfolio(initial_cash=1_000_000, event_bus=bus)
    ts = datetime(2024, 1, 2)
    pf.handle_market(MarketEvent(bar=_bar("600000", ts, 10.0)))
    # Simulate an existing 20,000-share position worth 200,000.
    from alphaagent.portfolio.portfolio import Position

    pf.positions["600000"] = Position(symbol="600000", quantity=20_000, avg_cost=10.0)

    rule = MaxPerSymbolExposure(max_pct=0.3)
    # Equity = cash 1M + positions 200k = 1.2M. Cap = 360k.
    # Already holding 200k, headroom = 160k => 16,000 shares allowed.
    allowed = rule.allowed_qty(_order("600000", Side.BUY, 100_000), pf)
    assert allowed == 16_000


def test_max_position_count_rejects_new_symbol_when_full():
    bus = EventBus()
    pf = Portfolio(initial_cash=1_000_000, event_bus=bus)
    ts = datetime(2024, 1, 2)
    from alphaagent.portfolio.portfolio import Position

    pf.positions["A"] = Position(symbol="A", quantity=100, avg_cost=1.0)
    pf.positions["B"] = Position(symbol="B", quantity=100, avg_cost=1.0)
    pf.handle_market(MarketEvent(bar=_bar("C", ts, 10.0)))

    rule = MaxPositionCount(max_n=2)
    # Adding to an existing position is fine.
    assert rule.allowed_qty(_order("A", Side.BUY, 1000), pf) == 1000
    # Opening a third symbol is rejected.
    assert rule.allowed_qty(_order("C", Side.BUY, 1000), pf) == 0


def test_rules_reject_invalid_params():
    with pytest.raises(ValueError):
        MaxGrossExposure(max_pct=1.5)
    with pytest.raises(ValueError):
        MaxPerSymbolExposure(max_pct=0)
    with pytest.raises(ValueError):
        MaxPositionCount(max_n=0)


# ---------------------------------------------------------------------------
# Risk manager: order mutation
# ---------------------------------------------------------------------------


def test_manager_downsizes_buy_to_lot_multiple():
    bus = EventBus()
    pf = Portfolio(initial_cash=1_000_000, event_bus=bus)
    pf.handle_market(MarketEvent(bar=_bar("600000", datetime(2024, 1, 2), 10.0)))
    mgr = PortfolioRiskManager(pf, [MaxGrossExposure(max_pct=0.333)])

    order = _order("600000", Side.BUY, 100_000)
    mgr.handle_order(order)
    # Cap = 333k. Allowed = 33,333 shares, lot-rounded to 33,300.
    assert order.quantity == 33_300
    assert mgr.downsizes == 1
    assert mgr.rejections == 0


def test_manager_rejects_when_no_headroom():
    bus = EventBus()
    pf = Portfolio(initial_cash=1_000_000, event_bus=bus)
    ts = datetime(2024, 1, 2)
    pf.handle_market(MarketEvent(bar=_bar("600000", ts, 10.0)))
    # position value 1M, cash 1M, equity 2M, cap (0.5) = 1M, gross = 1M => headroom 0.
    from alphaagent.portfolio.portfolio import Position

    pf.positions["600000"] = Position(symbol="600000", quantity=100_000, avg_cost=10.0)
    mgr = PortfolioRiskManager(pf, [MaxGrossExposure(max_pct=0.5)])

    order = _order("600000", Side.BUY, 100_000)
    mgr.handle_order(order)
    assert order.quantity == 0
    assert mgr.rejections == 1


def test_manager_passes_sell_orders_unchanged():
    bus = EventBus()
    pf = Portfolio(initial_cash=1_000_000, event_bus=bus)
    pf.handle_market(MarketEvent(bar=_bar("600000", datetime(2024, 1, 2), 10.0)))
    mgr = PortfolioRiskManager(pf, [MaxGrossExposure(max_pct=0.1)])
    order = _order("600000", Side.SELL, 5_000)
    mgr.handle_order(order)
    assert order.quantity == 5_000
    assert mgr.rejections == 0


# ---------------------------------------------------------------------------
# End-to-end: engine subscribes risk before execution
# ---------------------------------------------------------------------------


class _BuyAllStrategy(Strategy):
    strategy_id = "buy_all"

    def __init__(self, symbols):
        super().__init__()
        self.symbols = set(symbols)
        self._signalled: set[str] = set()

    def on_bar(self, bar):
        if bar.symbol in self.symbols and bar.symbol not in self._signalled:
            self.ctx.emit_signal(bar, Side.BUY, strength=1.0)
            self._signalled.add(bar.symbol)


def _flat_frame(n=30):
    idx = pd.date_range("2024-01-02", periods=n, freq="B")
    return pd.DataFrame(
        {
            "open": [10.0] * n, "high": [10.0] * n, "low": [10.0] * n,
            "close": [10.0] * n, "volume": [1_000_000] * n,
        },
        index=idx,
    )


def test_engine_applies_max_position_count():
    feed = DataFeed({s: _flat_frame() for s in ["A", "B", "C", "D"]})
    bus = EventBus()
    # target_pct=0.2 leaves room to buy all four cash-wise, so the rule is
    # the binding constraint.
    pf = Portfolio(initial_cash=1_000_000, event_bus=bus, target_pct=0.2)
    ex = SimulatedExecutionHandler(event_bus=bus)
    mgr = PortfolioRiskManager(pf, [MaxPositionCount(max_n=2)])

    engine = BacktestEngine(
        feed, _BuyAllStrategy(["A", "B", "C", "D"]), pf, ex, bus, risk_manager=mgr
    )
    result = engine.run()

    assert len(pf.held_symbols()) == 2
    assert result.fill_count == 2
    assert mgr.rejections == 2


def test_engine_applies_max_gross_exposure():
    feed = DataFeed({s: _flat_frame() for s in ["A", "B", "C"]})
    bus = EventBus()
    # target_pct=0.5 per BUY would try to allocate 50% into each symbol.
    # Gross cap 0.8 means only ~80% of equity worth of positions total.
    pf = Portfolio(initial_cash=1_000_000, event_bus=bus, target_pct=0.5)
    ex = SimulatedExecutionHandler(event_bus=bus)
    mgr = PortfolioRiskManager(pf, [MaxGrossExposure(max_pct=0.8)])

    engine = BacktestEngine(
        feed, _BuyAllStrategy(["A", "B", "C"]), pf, ex, bus, risk_manager=mgr
    )
    engine.run()
    assert pf.gross_value() <= 0.8 * pf.equity() + 1e-6


# ---------------------------------------------------------------------------
# Multi-strategy: risk sees the combined book
# ---------------------------------------------------------------------------


def test_multi_strategy_sums_exposure_across_sub_portfolios():
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
    pf.handle_market(MarketEvent(bar=_bar("600000", ts, 10.0)))
    # Place the same symbol in both sub-portfolios.
    from alphaagent.portfolio.portfolio import Position

    pf.portfolios["alpha"].positions["600000"] = Position(
        symbol="600000", quantity=10_000, avg_cost=10.0
    )
    pf.portfolios["beta"].positions["600000"] = Position(
        symbol="600000", quantity=10_000, avg_cost=10.0
    )

    # Combined symbol value = 200k. Per-symbol cap 20% of 1.2M equity = 240k.
    rule = MaxPerSymbolExposure(max_pct=0.2)
    # Headroom = 40k at price 10 => 4,000 shares allowed.
    allowed = rule.allowed_qty(_order("600000", Side.BUY, 100_000), pf)
    assert allowed == 4_000
