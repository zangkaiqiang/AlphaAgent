"""Symbol → sector mapping for sector-concentration risk rules.

Two built-in loaders:

- ``DictSectorMap`` wraps a literal dict (useful for YAML-inline configs).
- ``CSVSectorMap`` loads a ``symbol,sector`` CSV.

Both return ``None`` for symbols they don't know about; rules treat unknown
symbols as unconstrained rather than rejecting them outright.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

import pandas as pd


class SectorMap(Protocol):
    def get(self, symbol: str) -> str | None: ...


class DictSectorMap:
    def __init__(self, mapping: dict[str, str]):
        self._map = dict(mapping)

    def get(self, symbol: str) -> str | None:
        return self._map.get(symbol)


class CSVSectorMap:
    """Loads `<root>` CSV with columns ``symbol,sector``."""

    def __init__(self, path: str | Path):
        df = pd.read_csv(path, dtype={"symbol": str, "sector": str})
        required = {"symbol", "sector"}
        missing = required - set(df.columns)
        if missing:
            raise ValueError(f"CSV missing columns: {missing}")
        self._map = dict(zip(df["symbol"], df["sector"], strict=True))

    def get(self, symbol: str) -> str | None:
        return self._map.get(symbol)
