"""Hard filter behavior."""

from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from alphaagent.screener.filters import (
    BUILTIN_FILTERS,
    ExcludeST,
    MaxPrice,
    MinAvgVolume,
    MinListedDays,
    MinPrice,
    build_filter,
)
from alphaagent.screener.meta import StockMeta


def _bars(closes, amounts=None):
    n = len(closes)
    idx = pd.date_range("2024-01-01", periods=n, freq="D")
    if amounts is None:
        amounts = [1e8] * n
    return pd.DataFrame(
        {
            "open": closes,
            "high": closes,
            "low": closes,
            "close": closes,
            "volume": [1000] * n,
            "amount": amounts,
        },
        index=idx,
    )


def _meta(name="平安银行", list_date=date(1991, 4, 3), is_st=False, industry="银行"):
    return StockMeta(
        symbol="000001",
        name=name,
        industry=industry,
        list_date=list_date,
        is_st=is_st,
    )


def test_min_price_keeps_above_threshold():
    f = MinPrice(min_price=5.0)
    assert f.keep("x", _bars([10]), _meta())
    assert not f.keep("x", _bars([4]), _meta())


def test_min_price_drops_empty_bars():
    f = MinPrice(min_price=5.0)
    empty = pd.DataFrame(columns=["open", "high", "low", "close", "volume", "amount"])
    assert not f.keep("x", empty, _meta())


def test_max_price_caps():
    f = MaxPrice(max_price=100.0)
    assert f.keep("x", _bars([99]), _meta())
    assert not f.keep("x", _bars([101]), _meta())


def test_min_avg_volume_uses_amount_not_volume():
    f = MinAvgVolume(lookback=5, min_amount=1e7)
    bars = _bars([10] * 5, amounts=[2e7] * 5)
    assert f.keep("x", bars, _meta())
    bars_low = _bars([10] * 5, amounts=[1e6] * 5)
    assert not f.keep("x", bars_low, _meta())


def test_min_avg_volume_drops_when_too_few_bars():
    f = MinAvgVolume(lookback=10, min_amount=1)
    assert not f.keep("x", _bars([10, 10, 10]), _meta())


def test_exclude_st_uses_meta_flag():
    f = ExcludeST()
    assert not f.keep("x", _bars([10]), _meta(name="*ST天山", is_st=True))
    assert f.keep("x", _bars([10]), _meta(name="贵州茅台"))


def test_exclude_st_falls_back_to_name_keyword():
    """If meta.is_st was missed but name flags ST, still drop."""
    f = ExcludeST()
    # meta.is_st=False but name says ST → fall-through still rejects
    assert not f.keep("x", _bars([10]), _meta(name="*ST故意", is_st=False))


def test_min_listed_days_drops_new():
    f = MinListedDays(min_days=250)
    bars = _bars([10] * 3)  # last bar at 2024-01-03
    new_meta = StockMeta(symbol="x", name="x", list_date=date(2023, 12, 1))
    assert not f.keep("x", bars, new_meta)
    old_meta = StockMeta(symbol="x", name="x", list_date=date(2020, 1, 1))
    assert f.keep("x", bars, old_meta)


def test_min_listed_days_permissive_on_unknown_date():
    f = MinListedDays(min_days=250)
    meta_no_date = StockMeta(symbol="x", name="x", list_date=None)
    assert f.keep("x", _bars([10]), meta_no_date)


def test_build_filter_dispatches():
    f = build_filter({"type": "min_price", "min_price": 5.0})
    assert isinstance(f, MinPrice)
    assert f.min_price == 5.0


def test_build_filter_unknown_type():
    with pytest.raises(ValueError, match="unknown filter"):
        build_filter({"type": "nope"})


def test_all_builtin_filters_registered():
    expected = {"min_price", "max_price", "min_avg_volume", "exclude_st", "min_listed_days"}
    assert set(BUILTIN_FILTERS) == expected
