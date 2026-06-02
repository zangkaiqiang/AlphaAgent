from datetime import date

import pandas as pd

from alphaagent.data.base import DataSource
from alphaagent.data.sqlite_cache import SqliteBarCache
from alphaagent.storage.db import Database


class StubSource(DataSource):
    def __init__(self):
        self.calls: list[tuple[str, date, date]] = []

    def get_bars(self, symbol, start, end, freq="1d"):
        self.calls.append((symbol, start, end))
        idx = pd.date_range(start, end, freq="B")
        return pd.DataFrame(
            {
                "open": range(len(idx)),
                "high": range(len(idx)),
                "low": range(len(idx)),
                "close": range(len(idx)),
                "volume": [100] * len(idx),
            },
            index=idx,
        )


def _cache(tmp_path):
    return SqliteBarCache(StubSource(), Database(str(tmp_path / "t.db")), "stub")


def test_cache_returns_slice_without_second_fetch(tmp_path):
    cache = _cache(tmp_path)
    stub = cache.upstream

    first = cache.get_bars("600000", date(2023, 1, 3), date(2023, 3, 31))
    assert not first.empty
    assert len(stub.calls) == 1

    sliced = cache.get_bars("600000", date(2023, 2, 1), date(2023, 2, 28))
    assert len(stub.calls) == 1  # no new fetch
    assert sliced.index.min() >= pd.Timestamp(2023, 2, 1)
    assert sliced.index.max() <= pd.Timestamp(2023, 2, 28)


def test_cache_extends_range_on_demand(tmp_path):
    cache = _cache(tmp_path)
    stub = cache.upstream

    cache.get_bars("600000", date(2023, 2, 1), date(2023, 2, 28))
    assert len(stub.calls) == 1

    extended = cache.get_bars("600000", date(2023, 1, 3), date(2023, 3, 31))
    assert len(stub.calls) == 3  # head + tail
    assert extended.index.min() <= pd.Timestamp(2023, 1, 5)
    assert extended.index.max() >= pd.Timestamp(2023, 3, 30)

    cache.get_bars("600000", date(2023, 1, 10), date(2023, 3, 20))
    assert len(stub.calls) == 3  # fully covered


def test_upsert_dedups_on_primary_key(tmp_path):
    cache = _cache(tmp_path)
    cache.get_bars("600000", date(2023, 1, 3), date(2023, 1, 31))
    cache.get_bars("600000", date(2023, 1, 3), date(2023, 1, 31))  # same range again
    rows = cache.db.query(
        "SELECT COUNT(*) AS n FROM bars WHERE symbol='600000'"
    )
    business_days = len(pd.date_range(date(2023, 1, 3), date(2023, 1, 31), freq="B"))
    assert rows[0]["n"] == business_days  # no duplicate rows
