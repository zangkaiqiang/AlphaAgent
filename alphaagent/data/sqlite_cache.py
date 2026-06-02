"""SQLite-backed OHLCV cache wrapping any upstream DataSource.

Bars live in the shared ``bars`` table keyed by (source_id, symbol, freq, dt).
Incremental fetch mirrors the previous Parquet CachedDataSource: only the
missing head/tail ranges hit upstream. ``upsert_bars`` is reused by the
migration script (scripts/migrate_cache.py).
"""

from __future__ import annotations

from datetime import date

import pandas as pd

from alphaagent.data.base import DataSource
from alphaagent.storage.db import Database

_INSERT = (
    "INSERT OR REPLACE INTO bars "
    "(source_id, symbol, freq, dt, open, high, low, close, volume, amount) "
    "VALUES (?,?,?,?,?,?,?,?,?,?)"
)


def _f(x) -> float | None:
    if x is None:
        return None
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if v == v else None  # NaN -> None


def upsert_bars(
    db: Database, source_id: str, symbol: str, freq: str, df: pd.DataFrame | None
) -> None:
    if df is None or df.empty:
        return
    # NOTE: timestamps are stored via isoformat() assuming tz-naive bars (daily
    # AKShare data). Revisit normalisation if tz-aware intraday bars are added.
    rows = [
        (
            source_id, symbol, freq, pd.Timestamp(ts).isoformat(),
            _f(r.get("open")), _f(r.get("high")), _f(r.get("low")),
            _f(r.get("close")), _f(r.get("volume")), _f(r.get("amount")),
        )
        for ts, r in df.iterrows()
    ]
    db.executemany(_INSERT, rows)


class SqliteBarCache(DataSource):
    def __init__(self, upstream: DataSource, db: Database, source_id: str):
        if not source_id:
            raise ValueError("source_id is required to partition cached bars")
        self.upstream = upstream
        self.db = db
        self.source_id = source_id

    def _bounds(
        self, symbol: str, freq: str
    ) -> tuple[pd.Timestamp, pd.Timestamp] | None:
        row = self.db.query(
            "SELECT MIN(dt) AS lo, MAX(dt) AS hi FROM bars "
            "WHERE source_id=? AND symbol=? AND freq=?",
            (self.source_id, symbol, freq),
        )[0]
        if row["lo"] is None:
            return None
        return pd.Timestamp(row["lo"]), pd.Timestamp(row["hi"])

    def _read(self, symbol: str, freq: str, start_ts, end_ts) -> pd.DataFrame:
        df = self.db.query_df(
            "SELECT dt, open, high, low, close, volume, amount FROM bars "
            "WHERE source_id=? AND symbol=? AND freq=? AND dt BETWEEN ? AND ? "
            "ORDER BY dt",
            (self.source_id, symbol, freq, start_ts.isoformat(), end_ts.isoformat()),
        )
        # Always index by datetime (even when empty) so the returned shape is
        # consistent for callers that inspect df.index.
        df.index = pd.to_datetime(df.pop("dt"))
        return df

    def get_bars(
        self, symbol: str, start: date, end: date, freq: str = "1d"
    ) -> pd.DataFrame:
        start_ts, end_ts = pd.Timestamp(start), pd.Timestamp(end)
        bounds = self._bounds(symbol, freq)

        if bounds is None:
            fetched = self.upstream.get_bars(symbol, start, end, freq=freq)
            upsert_bars(self.db, self.source_id, symbol, freq, fetched)
            return fetched

        cache_lo, cache_hi = bounds
        if start_ts < cache_lo:
            head = self.upstream.get_bars(
                symbol, start, (cache_lo - pd.Timedelta(days=1)).date(), freq=freq
            )
            upsert_bars(self.db, self.source_id, symbol, freq, head)
        if end_ts > cache_hi:
            tail = self.upstream.get_bars(
                symbol, (cache_hi + pd.Timedelta(days=1)).date(), end, freq=freq
            )
            upsert_bars(self.db, self.source_id, symbol, freq, tail)
        return self._read(symbol, freq, start_ts, end_ts)
