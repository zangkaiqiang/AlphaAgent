"""PaperBroker + BrokerExecutionHandler."""

from __future__ import annotations

from datetime import datetime

import pandas as pd
import pytest

from alphaagent.backtest.engine import BacktestEngine
from alphaagent.broker.base import BrokerError
from alphaagent.broker.paper import PaperBroker
from alphaagent.core.event_bus import EventBus
from alphaagent.core.events import EventType, MarketEvent, OrderEvent
from alphaagent.core.types import Bar, OrderType, Side
from alphaagent.data.base import DataFeed
from alphaagent.execution.broker_exec import BrokerExecutionHandler
from alphaagent.portfolio.portfolio import Portfolio
from alphaagent.strategy.base import Strategy


def _bar(symbol, ts, price):
    return Bar(symbol=symbol, timestamp=ts, open=price, high=price, low=price, close=price, volume=1000)


def _order(symbol, side, qty, ts, oid="oid1"):
    return OrderEvent(
        timestamp=ts,
        symbol=symbol,
        side=side,
        quantity=qty,
        order_type=OrderType.MARKET,
        order_id=oid,
    )


# ---------------------------------------------------------------------------
# PaperBroker: fill semantics
# ---------------------------------------------------------------------------


def test_paper_broker_fills_on_next_bar_open():
    broker = PaperBroker(initial_cash=100_000, slippage_bps=0)
    fills = []
    broker.on_fill(fills.append)

    t0 = datetime(2024, 1, 2, 10, 0)
    t1 = datetime(2024, 1, 2, 10, 1)
    broker.handle_market(MarketEvent(bar=_bar("600000", t0, 10.0)))  # no pending yet
    broker.place_order(_order("600000", Side.BUY, 1000, t0))
    # Same-timestamp bar: order placed at t0 must not fill at t0.
    broker.handle_market(MarketEvent(bar=_bar("600000", t0, 10.5)))
    assert fills == []

    # Next bar at t1: fill at that bar's open.
    broker.handle_market(MarketEvent(bar=_bar("600000", t1, 11.0)))
    assert len(fills) == 1
    fill = fills[0]
    assert fill.symbol == "600000"
    assert fill.fill_price == pytest.approx(11.0)
    assert fill.quantity == 1000


def test_paper_broker_applies_slippage_and_fees():
    broker = PaperBroker(initial_cash=100_000, slippage_bps=10, commission_rate=3e-4, min_commission=5.0)
    fills = []
    broker.on_fill(fills.append)

    t0 = datetime(2024, 1, 2, 10, 0)
    broker.handle_market(MarketEvent(bar=_bar("600000", t0, 10.0)))  # initial bar
    broker.place_order(_order("600000", Side.BUY, 1000, t0))
    broker.handle_market(MarketEvent(bar=_bar("600000", datetime(2024, 1, 2, 10, 1), 10.0)))

    fill = fills[0]
    assert fill.fill_price == pytest.approx(10.0 * 1.001)  # 10 bps slip
    notional = fill.fill_price * 1000
    assert fill.commission == pytest.approx(max(notional * 3e-4, 5.0))
    assert fill.stamp_tax == 0.0  # BUY


def test_paper_broker_charges_stamp_tax_on_sell():
    broker = PaperBroker(initial_cash=100_000, slippage_bps=0, stamp_tax_rate=1e-3)
    # Seed a position via a prior BUY fill.
    t0 = datetime(2024, 1, 2, 10, 0)
    broker.handle_market(MarketEvent(bar=_bar("600000", t0, 10.0)))
    broker.place_order(_order("600000", Side.BUY, 1000, t0))
    broker.handle_market(MarketEvent(bar=_bar("600000", datetime(2024, 1, 2, 10, 1), 10.0)))

    # Next trading day, sell.
    t_sell = datetime(2024, 1, 3, 10, 0)
    broker.handle_market(MarketEvent(bar=_bar("600000", t_sell, 11.0)))
    broker.place_order(_order("600000", Side.SELL, 1000, t_sell))
    fills = []
    broker.on_fill(fills.append)
    broker.handle_market(MarketEvent(bar=_bar("600000", datetime(2024, 1, 3, 10, 1), 11.0)))

    sell_fill = fills[-1]
    assert sell_fill.side == Side.SELL
    assert sell_fill.stamp_tax == pytest.approx(sell_fill.fill_price * 1000 * 1e-3)


def test_paper_broker_enforces_tplusone():
    broker = PaperBroker(initial_cash=100_000, slippage_bps=0)
    t0 = datetime(2024, 1, 2, 10, 0)
    broker.handle_market(MarketEvent(bar=_bar("600000", t0, 10.0)))
    broker.place_order(_order("600000", Side.BUY, 1000, t0))
    broker.handle_market(MarketEvent(bar=_bar("600000", datetime(2024, 1, 2, 10, 1), 10.0)))

    # Same-day sell attempt: blocked by T+1 lock.
    with pytest.raises(BrokerError, match="sellable"):
        broker.place_order(
            _order("600000", Side.SELL, 1000, datetime(2024, 1, 2, 14, 0))
        )


def test_paper_broker_rejects_when_insufficient_cash():
    broker = PaperBroker(initial_cash=100, slippage_bps=0)
    t0 = datetime(2024, 1, 2, 10, 0)
    broker.handle_market(MarketEvent(bar=_bar("600000", t0, 10.0)))
    broker.place_order(_order("600000", Side.BUY, 1000, t0))
    with pytest.raises(BrokerError, match="insufficient cash"):
        broker.handle_market(
            MarketEvent(bar=_bar("600000", datetime(2024, 1, 2, 10, 1), 10.0))
        )


# ---------------------------------------------------------------------------
# BrokerExecutionHandler bridges to event bus
# ---------------------------------------------------------------------------


def test_broker_execution_handler_republishes_fills():
    bus = EventBus()
    broker = PaperBroker(initial_cash=100_000, slippage_bps=0)
    handler = BrokerExecutionHandler(broker, bus)

    recorded = []
    bus.subscribe(EventType.FILL, recorded.append)

    t0 = datetime(2024, 1, 2, 10, 0)
    handler.handle_market(MarketEvent(bar=_bar("600000", t0, 10.0)))
    handler.handle_order(_order("600000", Side.BUY, 1000, t0))
    handler.handle_market(MarketEvent(bar=_bar("600000", datetime(2024, 1, 2, 10, 1), 10.0)))
    bus.dispatch()

    assert len(recorded) == 1
    assert recorded[0].symbol == "600000"


def test_broker_handler_skips_zero_quantity_order():
    bus = EventBus()
    broker = PaperBroker(initial_cash=100_000, slippage_bps=0)
    handler = BrokerExecutionHandler(broker, bus)
    handler.handle_order(_order("600000", Side.BUY, 0, datetime(2024, 1, 2)))
    assert broker.positions() == {}


# ---------------------------------------------------------------------------
# End-to-end: engine with PaperBroker completes a backtest
# ---------------------------------------------------------------------------


class _OneShotBuy(Strategy):
    strategy_id = "one_shot"

    def __init__(self):
        super().__init__()
        self._done = False

    def on_bar(self, bar):
        if not self._done:
            self.ctx.emit_signal(bar, Side.BUY, strength=1.0)
            self._done = True


def test_engine_works_with_broker_execution_handler():
    idx = pd.date_range("2024-01-02", periods=20, freq="B")
    df = pd.DataFrame(
        {
            "open": [10.0] * 20, "high": [10.0] * 20, "low": [10.0] * 20,
            "close": [10.0] * 20, "volume": [1_000_000] * 20,
        },
        index=idx,
    )
    feed = DataFeed({"600000": df})
    bus = EventBus()
    pf = Portfolio(initial_cash=1_000_000, event_bus=bus, target_pct=0.3)
    broker = PaperBroker(initial_cash=1_000_000, slippage_bps=0)
    handler = BrokerExecutionHandler(broker, bus)
    engine = BacktestEngine(feed, _OneShotBuy(), pf, handler, bus)
    result = engine.run()

    # Fill happened (next-bar-open model).
    assert result.fill_count >= 1
    assert "600000" in broker.positions()
