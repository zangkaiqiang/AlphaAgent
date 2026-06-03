"""Single SQLite database shared by jobs, the bar cache, and the calendar.

One connection per resolved DB path (process-wide), ``check_same_thread=False``
so backtest worker threads can share it, WAL for concurrent reads, and a write
lock to serialise writes. Schema is created idempotently on construction.
"""

from __future__ import annotations

import os
import sqlite3
import threading
from pathlib import Path

import pandas as pd

_SCHEMA = """
CREATE TABLE IF NOT EXISTS bars (
    source_id TEXT NOT NULL,
    symbol    TEXT NOT NULL,
    freq      TEXT NOT NULL,
    dt        TEXT NOT NULL,
    open REAL, high REAL, low REAL, close REAL, volume REAL, amount REAL,
    PRIMARY KEY (source_id, symbol, freq, dt)
);
CREATE TABLE IF NOT EXISTS trade_calendar (
    dt TEXT PRIMARY KEY
);
CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,
    kind TEXT NOT NULL DEFAULT 'backtest',
    label TEXT,
    status TEXT NOT NULL,
    progress REAL NOT NULL DEFAULT 0,
    bars_processed INTEGER NOT NULL DEFAULT 0,
    bars_total INTEGER NOT NULL DEFAULT 0,
    fill_count INTEGER NOT NULL DEFAULT 0,
    started_at TEXT,
    completed_at TEXT,
    error TEXT,
    result_json TEXT,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_jobs_created ON jobs(created_at);
CREATE TABLE IF NOT EXISTS financials (
    symbol TEXT NOT NULL,
    period TEXT NOT NULL,
    roe REAL, net_margin REAL, gross_margin REAL,
    revenue REAL, revenue_yoy REAL,
    net_income REAL, net_income_yoy REAL, debt_ratio REAL,
    fetched_at TEXT NOT NULL,
    PRIMARY KEY (symbol, period)
);
CREATE TABLE IF NOT EXISTS company_analysis (
    id TEXT PRIMARY KEY,
    symbol TEXT NOT NULL,
    generated_at TEXT NOT NULL,
    rating TEXT NOT NULL,
    confidence REAL,
    summary TEXT,
    reasons_json TEXT,
    risks_json TEXT,
    model TEXT,
    context_json TEXT
);
CREATE INDEX IF NOT EXISTS idx_company_analysis_symbol
    ON company_analysis(symbol, generated_at);
CREATE TABLE IF NOT EXISTS news (
    symbol TEXT NOT NULL, url TEXT NOT NULL, title TEXT, date TEXT,
    source TEXT, summary TEXT, fetched_at TEXT NOT NULL,
    PRIMARY KEY (symbol, url)
);
"""


class Database:
    def __init__(self, path: str | Path):
        self.path = str(path)
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._write_lock = threading.Lock()
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=NORMAL")
        self._conn.execute("PRAGMA busy_timeout=5000")
        self.init_schema()

    def init_schema(self) -> None:
        with self._write_lock:
            self._conn.executescript(_SCHEMA)
            self._conn.commit()
            # Idempotent migration: add 'kind' column to pre-existing DBs.
            cols = {row[1] for row in self._conn.execute("PRAGMA table_info(jobs)")}
            if "kind" not in cols:
                self._conn.execute(
                    "ALTER TABLE jobs ADD COLUMN kind TEXT NOT NULL DEFAULT 'backtest'"
                )
                self._conn.commit()
            # Idempotent migration: add 'report_json' column to pre-existing company_analysis DBs.
            cols = {row[1] for row in self._conn.execute("PRAGMA table_info(company_analysis)")}
            if "report_json" not in cols:
                self._conn.execute(
                    "ALTER TABLE company_analysis ADD COLUMN report_json TEXT"
                )
                self._conn.commit()

    def execute(self, sql: str, params: tuple = ()) -> None:
        with self._write_lock:
            self._conn.execute(sql, params)
            self._conn.commit()

    def executemany(self, sql: str, seq) -> None:
        with self._write_lock:
            self._conn.executemany(sql, seq)
            self._conn.commit()

    def query(self, sql: str, params: tuple = ()) -> list[sqlite3.Row]:
        # Use an explicit cursor (not the connection's implicit one) so concurrent
        # backtest worker threads reading via the shared connection don't contend
        # on a single cursor. Safe lock-free under WAL.
        cur = self._conn.cursor()
        return cur.execute(sql, params).fetchall()

    def query_df(self, sql: str, params: tuple = ()) -> pd.DataFrame:
        return pd.read_sql_query(sql, self._conn, params=params)

    def close(self) -> None:
        self._conn.close()


_INSTANCES: dict[str, Database] = {}
_INSTANCES_LOCK = threading.Lock()


def resolve_db_path(path: str | None = None) -> str:
    p = path or os.environ.get("ALPHAAGENT_DB", "./data/alphaagent.db")
    return p if p == ":memory:" else str(Path(p).resolve())


def get_database(path: str | None = None) -> Database:
    resolved = resolve_db_path(path)
    with _INSTANCES_LOCK:
        db = _INSTANCES.get(resolved)
        if db is None:
            db = Database(resolved)
            _INSTANCES[resolved] = db
        return db
