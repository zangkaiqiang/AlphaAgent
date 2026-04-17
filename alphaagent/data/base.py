"""Data layer base classes."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator
from datetime import date

import pandas as pd

from alphaagent.core.types import Bar


class DataSource(ABC):
    """A data source fetches historical bars for symbols."""

    @abstractmethod
    def get_bars(
        self,
        symbol: str,
        start: date,
        end: date,
        freq: str = "1d",
    ) -> pd.DataFrame:
        """Return DataFrame indexed by datetime with columns:
        open, high, low, close, volume, amount.
        """


class DataFeed:
    """Streams bars in chronological order across multiple symbols.

    Given a dict of symbol -> DataFrame, iterate bar-by-bar in timestamp
    order. Ties broken by symbol name for determinism.
    """

    def __init__(self, frames: dict[str, pd.DataFrame]):
        self._frames = frames
        self._validate()

    def _validate(self) -> None:
        required = {"open", "high", "low", "close", "volume"}
        for symbol, df in self._frames.items():
            missing = required - set(df.columns)
            if missing:
                raise ValueError(f"{symbol}: missing columns {missing}")

    def __iter__(self) -> Iterator[Bar]:
        records: list[tuple[pd.Timestamp, str, pd.Series]] = []
        for symbol, df in self._frames.items():
            for ts, row in df.iterrows():
                records.append((ts, symbol, row))
        records.sort(key=lambda r: (r[0], r[1]))
        for ts, symbol, row in records:
            yield Bar(
                symbol=symbol,
                timestamp=ts.to_pydatetime() if hasattr(ts, "to_pydatetime") else ts,
                open=float(row["open"]),
                high=float(row["high"]),
                low=float(row["low"]),
                close=float(row["close"]),
                volume=float(row["volume"]),
                amount=float(row.get("amount", 0.0)),
            )

    @property
    def symbols(self) -> list[str]:
        return list(self._frames.keys())
