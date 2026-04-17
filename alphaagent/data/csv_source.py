"""CSV-backed data source. Useful for tests and offline workflows."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd

from alphaagent.data.base import DataSource


class CSVDataSource(DataSource):
    """Loads bars from `<root>/<symbol>.csv` with a 'date' column."""

    def __init__(self, root: str | Path):
        self.root = Path(root)

    def get_bars(
        self,
        symbol: str,
        start: date,
        end: date,
        freq: str = "1d",
    ) -> pd.DataFrame:
        path = self.root / f"{symbol}.csv"
        if not path.exists():
            raise FileNotFoundError(path)
        df = pd.read_csv(path, parse_dates=["date"]).set_index("date").sort_index()
        return df.loc[str(start) : str(end)]
