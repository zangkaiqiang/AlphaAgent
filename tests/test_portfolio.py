from datetime import datetime

from alphaagent.core.event_bus import EventBus
from alphaagent.core.events import FillEvent, MarketEvent, SignalEvent
from alphaagent.core.types import Bar, Side
from alphaagent.portfolio.portfolio import Portfolio


def _bar(symbol, ts, close):
    return Bar(symbol=symbol, timestamp=ts, open=close, high=close, low=close, close=close, volume=1000)


def test_portfolio_sizes_buy_to_lot_multiple():
    bus = EventBus()
    pf = Portfolio(initial_cash=100_000, event_bus=bus, target_pct=0.5)
    ts = datetime(2023, 1, 3)
    pf.handle_market(MarketEvent(bar=_bar("600000", ts, 10.0)))
    pf.handle_signal(SignalEvent(timestamp=ts, symbol="600000", side=Side.BUY))

    bus.dispatch()
    # Dispatched one OrderEvent; we can inspect via equity curve length instead.
    # Re-simulate by pulling the order off the bus.
    # Easier: call _size_order directly.
    order = pf._size_order(SignalEvent(timestamp=ts, symbol="600000", side=Side.BUY))
    assert order is not None
    assert order.quantity % 100 == 0
    assert order.quantity * 10.0 <= 100_000 * 0.5


def test_tplus_one_blocks_same_day_sell():
    bus = EventBus()
    pf = Portfolio(initial_cash=100_000, event_bus=bus)
    ts = datetime(2023, 1, 3, 10, 0)
    # Buy fill at 10:00.
    pf.handle_fill(
        FillEvent(timestamp=ts, symbol="600000", side=Side.BUY, quantity=1000, fill_price=10.0)
    )
    pf.handle_market(MarketEvent(bar=_bar("600000", ts, 10.0)))
    # Same-day sell signal produces no order (all shares locked).
    order = pf._size_order(SignalEvent(timestamp=ts, symbol="600000", side=Side.SELL))
    assert order is None

    # Next day, sell allowed.
    next_day = datetime(2023, 1, 4, 9, 30)
    pf.handle_market(MarketEvent(bar=_bar("600000", next_day, 10.5)))
    order = pf._size_order(SignalEvent(timestamp=next_day, symbol="600000", side=Side.SELL))
    assert order is not None
    assert order.quantity == 1000
