"""Local Parquet cache that wraps any DataSource.

Strategy:
- One parquet file per (symbol, freq, source_id) at
  ``<root>/<symbol>_<freq>__<source_id>.parquet``.
- On request, read cached frame; if it covers [start, end], return the slice.
- Otherwise, fetch missing ranges (before and/or after the cached range)
  from the upstream source, merge, persist, and return the requested slice.

``source_id`` is part of the cache key so switching between upstreams
(e.g. akshare sina ↔ eastmoney) never mixes rows with different adjust /
amount semantics into the same file.

This keeps network calls to a minimum without requiring DuckDB.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd

from alphaagent.data.base import DataSource


class CachedDataSource(DataSource):
    def __init__(self, upstream: DataSource, root: str | Path, source_id: str):
        if not source_id:
            raise ValueError("source_id is required to partition cache files")
        self.upstream = upstream
        self.root = Path(root)
        self.source_id = source_id
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, symbol: str, freq: str) -> Path:
        return self.root / f"{symbol}_{freq}__{self.source_id}.parquet"

    def _read_cache(self, symbol: str, freq: str) -> pd.DataFrame | None:
        path = self._path(symbol, freq)
        if not path.exists():
            return None
        df = pd.read_parquet(path)
        df.index = pd.to_datetime(df.index)
        return df.sort_index()

    def _write_cache(self, symbol: str, freq: str, df: pd.DataFrame) -> None:
        df = df[~df.index.duplicated(keep="last")].sort_index()
        df.to_parquet(self._path(symbol, freq))

    def get_bars(
        self,
        symbol: str,
        start: date,
        end: date,
        freq: str = "1d",
    ) -> pd.DataFrame:
        start_ts = pd.Timestamp(start)
        end_ts = pd.Timestamp(end)

        cached = self._read_cache(symbol, freq)
        if cached is None or cached.empty:
            fetched = self.upstream.get_bars(symbol, start, end, freq=freq)
            if not fetched.empty:
                self._write_cache(symbol, freq, fetched)
            return fetched

        cache_start, cache_end = cached.index.min(), cached.index.max()
        parts: list[pd.DataFrame] = [cached]

        if start_ts < cache_start:
            head = self.upstream.get_bars(
                symbol, start, (cache_start - pd.Timedelta(days=1)).date(), freq=freq
            )
            if not head.empty:
                parts.append(head)

        if end_ts > cache_end:
            tail = self.upstream.get_bars(
                symbol, (cache_end + pd.Timedelta(days=1)).date(), end, freq=freq
            )
            if not tail.empty:
                parts.append(tail)

        merged = pd.concat(parts)
        merged = merged[~merged.index.duplicated(keep="last")].sort_index()

        if len(parts) > 1:
            self._write_cache(symbol, freq, merged)

        return merged.loc[start_ts:end_ts]
