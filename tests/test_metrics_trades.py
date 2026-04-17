from datetime import datetime

from alphaagent.core.events import FillEvent
from alphaagent.core.types import Side
from alphaagent.metrics.trades import build_trades, trade_stats


def _fill(ts, symbol, side, qty, price, commission=0.0, stamp_tax=0.0):
    return FillEvent(
        timestamp=ts,
        symbol=symbol,
        side=side,
        quantity=qty,
        fill_price=price,
        commission=commission,
        stamp_tax=stamp_tax,
    )


def test_simple_roundtrip_is_winner():
    fills = [
        _fill(datetime(2024, 1, 2), "600000", Side.BUY, 1000, 10.0),
        _fill(datetime(2024, 1, 5), "600000", Side.SELL, 1000, 11.0),
    ]
    trades = build_trades(fills)
    assert len(trades) == 1
    t = trades[0]
    assert t.quantity == 1000
    assert t.pnl == 1000 * (11.0 - 10.0)
    assert t.is_winner


def test_fifo_partial_close_creates_two_trades():
    fills = [
        _fill(datetime(2024, 1, 2), "600000", Side.BUY, 500, 10.0),
        _fill(datetime(2024, 1, 3), "600000", Side.BUY, 500, 12.0),
        _fill(datetime(2024, 1, 4), "600000", Side.SELL, 700, 13.0),
    ]
    trades = build_trades(fills)
    assert len(trades) == 2
    # First trade closes 500 @ 10 -> 13.
    assert trades[0].open_price == 10.0
    assert trades[0].quantity == 500
    # Second trade closes 200 @ 12 -> 13 from the second lot.
    assert trades[1].open_price == 12.0
    assert trades[1].quantity == 200


def test_fees_reduce_pnl():
    fills = [
        _fill(datetime(2024, 1, 2), "600000", Side.BUY, 1000, 10.0, commission=5.0),
        _fill(datetime(2024, 1, 5), "600000", Side.SELL, 1000, 10.5, commission=5.0, stamp_tax=10.5),
    ]
    trades = build_trades(fills)
    # gross = 500, fees = 5 (buy) + 5 + 10.5 (sell) = 20.5
    assert trades[0].pnl == 500 - 20.5


def test_unclosed_lot_is_ignored():
    fills = [
        _fill(datetime(2024, 1, 2), "600000", Side.BUY, 1000, 10.0),
    ]
    assert build_trades(fills) == []


def test_trade_stats_wins_and_losses():
    fills = [
        _fill(datetime(2024, 1, 2), "600000", Side.BUY, 1000, 10.0),
        _fill(datetime(2024, 1, 3), "600000", Side.SELL, 1000, 11.0),  # win +1000
        _fill(datetime(2024, 1, 4), "600000", Side.BUY, 1000, 11.0),
        _fill(datetime(2024, 1, 5), "600000", Side.SELL, 1000, 10.5),  # loss -500
    ]
    stats = trade_stats(build_trades(fills))
    assert stats["trades"] == 2
    assert stats["win_rate"] == 0.5
    assert stats["avg_win"] == 1000.0
    assert stats["avg_loss"] == -500.0
    assert stats["profit_factor"] == 2.0
    assert stats["total_pnl"] == 500.0


def test_empty_trade_stats():
    stats = trade_stats([])
    assert stats["trades"] == 0
    assert stats["win_rate"] == 0.0
