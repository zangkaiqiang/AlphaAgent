from datetime import date

import pandas as pd

from alphaagent.data.base import DataSource
from alphaagent.screener.fetcher import FetchResult, fetch_panel


class FlakeSource(DataSource):
    """Returns bars for some symbols, raises for others, empty for yet others."""

    def __init__(self, failing: set[str], empty: set[str]):
        self.failing = failing
        self.empty = empty

    def get_bars(self, symbol, start, end, freq="1d"):
        if symbol in self.failing:
            raise RuntimeError(f"upstream blew up on {symbol}")
        if symbol in self.empty:
            return pd.DataFrame()
        idx = pd.date_range(start, end, freq="B")
        return pd.DataFrame({"close": range(len(idx))}, index=idx)


def test_fetch_panel_reports_failed_and_empty():
    src = FlakeSource(failing={"AAA"}, empty={"BBB"})
    result = fetch_panel(
        src,
        ["AAA", "BBB", "CCC"],
        date(2024, 1, 2),
        date(2024, 1, 10),
        show_progress=False,
    )
    assert isinstance(result, FetchResult)
    assert set(result.bars) == {"CCC"}
    assert set(result.failed) == {"AAA", "BBB"}
    assert "RuntimeError" in result.failed["AAA"]
    assert result.failed["BBB"] == "empty"
    assert result.failure_rate == 2 / 3


def test_fetch_panel_all_success():
    src = FlakeSource(failing=set(), empty=set())
    result = fetch_panel(
        src, ["AAA", "BBB"], date(2024, 1, 2), date(2024, 1, 10), show_progress=False
    )
    assert set(result.bars) == {"AAA", "BBB"}
    assert result.failed == {}
    assert result.failure_rate == 0.0
