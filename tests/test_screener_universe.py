"""Universe abstractions: behavior + error contracts."""

from __future__ import annotations

from datetime import date

import pytest

from alphaagent.screener.universe import (
    AkshareIndexUniverse,
    StaticUniverse,
    TushareIndexUniverse,
)


def test_static_universe_returns_fixed_list():
    u = StaticUniverse(["600000", "000001"], name="my_pool")
    assert u.name() == "my_pool"
    assert u.get_symbols(date(2024, 1, 1)) == ["600000", "000001"]
    # date is irrelevant
    assert u.get_symbols(date(2030, 1, 1)) == ["600000", "000001"]


def test_static_universe_rejects_empty():
    with pytest.raises(ValueError, match="at least one symbol"):
        StaticUniverse([])


def test_tushare_universe_raises_not_implemented():
    u = TushareIndexUniverse("000300")
    assert "tushare" in u.name()
    with pytest.raises(NotImplementedError, match="2000 points"):
        u.get_symbols(date(2024, 1, 1))


def test_akshare_universe_name():
    # Don't actually call the network — just verify name.
    u = AkshareIndexUniverse("000300")
    assert u.name() == "akshare_index:000300"
