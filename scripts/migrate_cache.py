"""One-off migration: import the existing Parquet bar cache + calendar into SQLite.

Usage:
    uv run python scripts/migrate_cache.py --cache-dir ./data/cache \
        [--db ./data/alphaagent.db] [--calendar ./data/cache/ashare_calendar.parquet]

Idempotent (INSERT OR REPLACE). Legacy files without a ``__source_id`` suffix are
skipped (the current code cannot read them anyway).
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import pandas as pd

from alphaagent.data.sqlite_cache import upsert_bars
from alphaagent.storage.db import Database, resolve_db_path

_NAME_RE = re.compile(r"^(?P<symbol>[^_]+)_(?P<freq>[^_]+)__(?P<source_id>.+)\.parquet$")


def migrate_bars(db: Database, cache_dir: str) -> tuple[int, int, int]:
    imported = total_rows = skipped = 0
    for p in sorted(Path(cache_dir).glob("*.parquet")):
        m = _NAME_RE.match(p.name)
        if not m:
            skipped += 1
            print(f"  skip (legacy name, unreadable by current code): {p.name}")
            continue
        df = pd.read_parquet(p)
        df.index = pd.to_datetime(df.index)
        upsert_bars(db, m["source_id"], m["symbol"], m["freq"], df)
        imported += 1
        total_rows += len(df)
    return imported, total_rows, skipped


def migrate_calendar(db: Database, path: str) -> int:
    df = pd.read_parquet(path)
    df["trade_date"] = pd.to_datetime(df["trade_date"])
    dates = sorted({d.date().isoformat() for d in df["trade_date"]})
    db.executemany(
        "INSERT OR REPLACE INTO trade_calendar (dt) VALUES (?)",
        [(d,) for d in dates],
    )
    return len(dates)


def main() -> None:
    ap = argparse.ArgumentParser(description="Migrate Parquet cache into SQLite.")
    ap.add_argument("--cache-dir", default="./data/cache")
    ap.add_argument("--db", default=None,
                    help="SQLite path; default ALPHAAGENT_DB or ./data/alphaagent.db")
    ap.add_argument("--calendar", default=None, help="Optional calendar parquet path.")
    args = ap.parse_args()

    if not Path(args.cache_dir).is_dir():
        raise SystemExit(f"cache_dir not found: {args.cache_dir}")

    db = Database(resolve_db_path(args.db))
    imported, rows, skipped = migrate_bars(db, args.cache_dir)
    print(f"bars: imported {imported} files, {rows} rows, skipped {skipped} legacy")
    if args.calendar:
        n = migrate_calendar(db, args.calendar)
        print(f"calendar: {n} dates")


if __name__ == "__main__":
    main()
