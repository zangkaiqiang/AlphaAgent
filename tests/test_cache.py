from datetime import date

import pandas as pd

from alphaagent.data.base import DataSource
from alphaagent.data.cache import CachedDataSource


class StubSource(DataSource):
    """Counts calls and returns deterministic bars for the requested range."""

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


def test_cache_returns_slice_without_second_fetch(tmp_path):
    stub = StubSource()
    cache = CachedDataSource(stub, tmp_path)

    first = cache.get_bars("600000", date(2023, 1, 3), date(2023, 3, 31))
    assert not first.empty
    assert len(stub.calls) == 1

    sliced = cache.get_bars("600000", date(2023, 2, 1), date(2023, 2, 28))
    assert len(stub.calls) == 1  # no new fetch
    assert sliced.index.min() >= pd.Timestamp(2023, 2, 1)
    assert sliced.index.max() <= pd.Timestamp(2023, 2, 28)


def test_cache_extends_range_on_demand(tmp_path):
    stub = StubSource()
    cache = CachedDataSource(stub, tmp_path)

    cache.get_bars("600000", date(2023, 2, 1), date(2023, 2, 28))
    assert len(stub.calls) == 1

    extended = cache.get_bars("600000", date(2023, 1, 3), date(2023, 3, 31))
    # Two extra fetches: head (pre-cache) and tail (post-cache).
    assert len(stub.calls) == 3
    assert extended.index.min() <= pd.Timestamp(2023, 1, 5)
    assert extended.index.max() >= pd.Timestamp(2023, 3, 30)

    # Third call covered by cache.
    cache.get_bars("600000", date(2023, 1, 10), date(2023, 3, 20))
    assert len(stub.calls) == 3
