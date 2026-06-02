# SQLite 持久化(Phase 1)Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把回测任务/结果、行情(OHLCV)缓存、交易日历从「内存 / Parquet」迁移到单个 SQLite 库,并提供一次性迁移脚本。

**Architecture:** 单库 + 薄存储层(spec 方案 A)。新增 `alphaagent/storage/db.py` 统一管连接(WAL + 写锁,跨 worker 线程共享)与建表;`SqliteBarCache` 替换 Parquet 缓存的使用(runtime/API),`AShareCalendar` 增加 DB 分支,`JobStore` 改为「内存活对象 + 终态落库 + 启动恢复」。Parquet 后端代码本阶段保留(cli.py 仍依赖,Phase 3 删)。

**Tech Stack:** Python 3.11+,标准库 `sqlite3`,`pandas`,`pydantic`,FastAPI,`pytest`,`ruff`。

**测试命令统一加 extra:** `uv run --extra data --extra api pytest <...>`(pyarrow / fastapi 在可选 extra 里)。

**Spec:** `docs/superpowers/specs/2026-06-02-sqlite-persistence-design.md`

---

## 文件结构

新增:
- `alphaagent/storage/__init__.py` — 导出 `Database`、`get_database`、`resolve_db_path`。
- `alphaagent/storage/db.py` — `Database` 类 + 单例 + schema。
- `alphaagent/data/sqlite_cache.py` — `SqliteBarCache` + 可复用 `upsert_bars()`。
- `scripts/__init__.py`、`scripts/migrate_cache.py` — 迁移脚本。
- `tests/test_storage_db.py`、`tests/test_sqlite_cache.py`、`tests/test_job_store.py`、`tests/test_migrate_cache.py`。

修改:
- `alphaagent/config.py` — 新增 `StorageConfig`,`AppConfig.storage`。
- `alphaagent/calendar/ashare.py` — `_load` 增加 DB 分支(保留 parquet 回退)。
- `alphaagent/api/job_store.py` — SQLite 持久化 + 启动恢复。
- `alphaagent/api/deps.py` — `get_job_store` 绑定 `Database`。
- `alphaagent/api/routers/backtests.py` — `TERMINAL` 从 job_store 导入(DRY)。
- `alphaagent/runtime.py` — `build_data_source` 用 `SqliteBarCache`;`build_calendar` 接收 `db`。
- `alphaagent/api/runner.py` — `build_calendar` 传 `db`。
- `tests/test_api.py` — 隔离 fixture 指向 tmp DB。
- `tests/test_calendar.py` — 增加 DB-backed 用例。
- `README.md` — 缓存机制 / 配置 / 迁移脚本说明。

---

## Task 1: 配置新增 StorageConfig

**Files:**
- Modify: `alphaagent/config.py`
- Test: `tests/test_config.py`

- [ ] **Step 1: Write the failing test**

在 `tests/test_config.py` 末尾追加:

```python
def test_storage_defaults_and_override():
    from alphaagent.config import AppConfig

    base = {
        "data": {"source": "csv", "root": "./data", "symbols": ["600000"],
                 "start": "2023-01-01", "end": "2023-12-31"},
        "strategy": {"name": "ma_cross", "params": {}},
    }
    cfg = AppConfig(**base)
    assert cfg.storage.db_path == "./data/alphaagent.db"

    cfg2 = AppConfig(**base, storage={"db_path": "/tmp/x.db"})
    assert cfg2.storage.db_path == "/tmp/x.db"

    # `storage:` present but empty (all keys commented out) -> defaults, no error.
    cfg3 = AppConfig(**base, storage=None)
    assert cfg3.storage.db_path == "./data/alphaagent.db"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --extra data --extra api pytest tests/test_config.py::test_storage_defaults_and_override -v`
Expected: FAIL (`AppConfig` has no field `storage` / `AttributeError`).

- [ ] **Step 3: Implement**

在 `alphaagent/config.py` 新增模型(放在 `AgentConfig` 之后):

```python
class StorageConfig(BaseModel):
    db_path: str = "./data/alphaagent.db"
```

在 `AppConfig` 字段中加入:

```python
    storage: StorageConfig = StorageConfig()
```

在 `_coerce_empty_sections` 的 key 元组里加 `"storage"`:

```python
            for key in ("portfolio", "execution", "agent", "calendar", "risk", "storage"):
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run --extra data --extra api pytest tests/test_config.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add alphaagent/config.py tests/test_config.py
git commit -m "feat(config): add StorageConfig.db_path"
```

---

## Task 2: 存储层 Database + get_database

**Files:**
- Create: `alphaagent/storage/__init__.py`, `alphaagent/storage/db.py`
- Test: `tests/test_storage_db.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_storage_db.py
import pandas as pd

from alphaagent.storage.db import Database, get_database, resolve_db_path


def test_schema_created_and_crud(tmp_path):
    db = Database(str(tmp_path / "t.db"))
    db.execute(
        "INSERT INTO trade_calendar (dt) VALUES (?)", ("2024-01-02",)
    )
    rows = db.query("SELECT dt FROM trade_calendar")
    assert [r["dt"] for r in rows] == ["2024-01-02"]


def test_query_df_returns_frame(tmp_path):
    db = Database(str(tmp_path / "t.db"))
    db.executemany(
        "INSERT OR REPLACE INTO bars "
        "(source_id,symbol,freq,dt,open,high,low,close,volume,amount) "
        "VALUES (?,?,?,?,?,?,?,?,?,?)",
        [("s", "600000", "1d", "2023-01-03T00:00:00", 1, 1, 1, 1, 10, None)],
    )
    df = db.query_df("SELECT * FROM bars")
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 1
    assert df.iloc[0]["symbol"] == "600000"


def test_get_database_caches_by_path(tmp_path, monkeypatch):
    from alphaagent.storage import db as dbmod
    dbmod._INSTANCES.clear()
    monkeypatch.setenv("ALPHAAGENT_DB", str(tmp_path / "env.db"))
    a = get_database()
    b = get_database()
    assert a is b
    assert resolve_db_path() == str((tmp_path / "env.db").resolve())
    dbmod._INSTANCES.clear()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --extra data --extra api pytest tests/test_storage_db.py -v`
Expected: FAIL (`ModuleNotFoundError: alphaagent.storage`).

- [ ] **Step 3: Implement**

```python
# alphaagent/storage/__init__.py
from alphaagent.storage.db import Database, get_database, resolve_db_path

__all__ = ["Database", "get_database", "resolve_db_path"]
```

```python
# alphaagent/storage/db.py
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

    def execute(self, sql: str, params: tuple = ()) -> None:
        with self._write_lock:
            self._conn.execute(sql, params)
            self._conn.commit()

    def executemany(self, sql: str, seq) -> None:
        with self._write_lock:
            self._conn.executemany(sql, seq)
            self._conn.commit()

    def query(self, sql: str, params: tuple = ()) -> list[sqlite3.Row]:
        return self._conn.execute(sql, params).fetchall()

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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run --extra data --extra api pytest tests/test_storage_db.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add alphaagent/storage tests/test_storage_db.py
git commit -m "feat(storage): add shared SQLite Database with WAL + write lock"
```

---

## Task 3: SqliteBarCache + upsert_bars

**Files:**
- Create: `alphaagent/data/sqlite_cache.py`
- Test: `tests/test_sqlite_cache.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_sqlite_cache.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --extra data --extra api pytest tests/test_sqlite_cache.py -v`
Expected: FAIL (`ModuleNotFoundError: alphaagent.data.sqlite_cache`).

- [ ] **Step 3: Implement**

```python
# alphaagent/data/sqlite_cache.py
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
    db: Database, source_id: str, symbol: str, freq: str, df: pd.DataFrame
) -> None:
    if df is None or df.empty:
        return
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

    def _bounds(self, symbol: str, freq: str):
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
        if df.empty:
            return df
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run --extra data --extra api pytest tests/test_sqlite_cache.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add alphaagent/data/sqlite_cache.py tests/test_sqlite_cache.py
git commit -m "feat(data): add SqliteBarCache with incremental upsert"
```

---

## Task 4: runtime 接入 SqliteBarCache + build_calendar 接收 db

**Files:**
- Modify: `alphaagent/runtime.py:56-80` (`build_data_source`), `alphaagent/runtime.py:136-139` (`build_calendar`)
- Test: `tests/test_runtime_wiring.py` (new)

- [ ] **Step 1: Write the failing test**

```python
# tests/test_runtime_wiring.py
from alphaagent.config import AppConfig
from alphaagent.data.sqlite_cache import SqliteBarCache
from alphaagent.runtime import build_data_source


def _cfg(tmp_path, cache_on: bool):
    data = {
        "source": "csv", "root": str(tmp_path), "symbols": ["A"],
        "start": "2023-01-01", "end": "2023-12-31",
    }
    if cache_on:
        data["cache_dir"] = str(tmp_path / "cache")
    return AppConfig(
        data=data,
        strategy={"name": "ma_cross", "params": {}},
        storage={"db_path": str(tmp_path / "t.db")},
    )


def test_build_data_source_wraps_with_sqlite_when_cache_on(tmp_path):
    src = build_data_source(_cfg(tmp_path, cache_on=True))
    assert isinstance(src, SqliteBarCache)


def test_build_data_source_unwrapped_when_cache_off(tmp_path):
    src = build_data_source(_cfg(tmp_path, cache_on=False))
    assert not isinstance(src, SqliteBarCache)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --extra data --extra api pytest tests/test_runtime_wiring.py -v`
Expected: FAIL (still wraps with `CachedDataSource`, not `SqliteBarCache`).

- [ ] **Step 3: Implement**

在 `alphaagent/runtime.py` 顶部 import 区,把
```python
from alphaagent.data.cache import CachedDataSource
```
替换为
```python
from alphaagent.data.sqlite_cache import SqliteBarCache
from alphaagent.storage.db import Database, get_database
```

`build_data_source` 末尾的缓存包装替换:

```python
    if cfg.data.cache_dir:
        source = SqliteBarCache(
            source,
            get_database(cfg.storage.db_path),
            source_id_for_data_cfg(cfg.data),
        )
    return source
```

`build_calendar` 改为接收 `db`:

```python
def build_calendar(
    cfg: CalendarConfig, db: Database | None = None
) -> AShareCalendar | None:
    if not cfg.enabled:
        return None
    return AShareCalendar(db=db, cache_path=cfg.cache_path)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run --extra data --extra api pytest tests/test_runtime_wiring.py -v`
Expected: PASS.

> 注:`AShareCalendar(db=...)` 在 Task 5 才实现 `db` 参数。本任务 `build_calendar` 仅传参,`test_runtime_wiring.py` 不触发日历构建,故此处先通过;若先跑日历相关测试会失败,按计划顺序执行即可。

- [ ] **Step 5: Commit**

```bash
git add alphaagent/runtime.py tests/test_runtime_wiring.py
git commit -m "feat(runtime): use SqliteBarCache; thread db into build_calendar"
```

---

## Task 5: AShareCalendar DB 分支

**Files:**
- Modify: `alphaagent/calendar/ashare.py:28-60`
- Test: `tests/test_calendar.py`

- [ ] **Step 1: Write the failing test**

在 `tests/test_calendar.py` 末尾追加:

```python
def test_calendar_db_roundtrip(tmp_path):
    from datetime import date

    from alphaagent.storage.db import Database

    db = Database(str(tmp_path / "t.db"))
    db.executemany(
        "INSERT OR REPLACE INTO trade_calendar (dt) VALUES (?)",
        [("2024-01-02",), ("2024-01-03",)],
    )
    cal = AShareCalendar(db=db)
    assert cal.is_trading_day(date(2024, 1, 2))
    assert cal.is_trading_day(date(2024, 1, 3))
    assert not cal.is_trading_day(date(2024, 1, 4))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --extra data --extra api pytest tests/test_calendar.py::test_calendar_db_roundtrip -v`
Expected: FAIL (`AShareCalendar.__init__` got unexpected keyword `db`).

- [ ] **Step 3: Implement**

修改 `alphaagent/calendar/ashare.py`。先在顶部增加类型 import(仅类型,避免循环依赖用字符串注解亦可):

```python
from alphaagent.storage.db import Database
```

`__init__` 与 `_load` 改为:

```python
    def __init__(
        self,
        trading_days: Iterable[date] | None = None,
        db: Database | None = None,
        cache_path: str | Path | None = None,
    ):
        self._db = db
        self._cache_path = Path(cache_path) if cache_path else None
        if trading_days is not None:
            self._days: set[date] = {self._to_date(d) for d in trading_days}
        else:
            self._days = self._load()

    def _load(self) -> set[date]:
        # 1) SQLite (preferred)
        if self._db is not None:
            rows = self._db.query("SELECT dt FROM trade_calendar")
            if rows:
                return {self._to_date(r["dt"]) for r in rows}
        # 2) legacy parquet fallback (used by cli.py until Phase 3)
        elif self._cache_path and self._cache_path.exists():
            df = pd.read_parquet(self._cache_path)
            return {self._to_date(d) for d in df["trade_date"]}

        # 3) fetch from akshare and persist
        import akshare as ak

        df = ak.tool_trade_date_hist_sina()
        df["trade_date"] = pd.to_datetime(df["trade_date"])
        days = {d.date() for d in df["trade_date"]}
        if self._db is not None:
            self._db.executemany(
                "INSERT OR REPLACE INTO trade_calendar (dt) VALUES (?)",
                [(d.isoformat(),) for d in sorted(days)],
            )
        elif self._cache_path:
            self._cache_path.parent.mkdir(parents=True, exist_ok=True)
            df.to_parquet(self._cache_path)
        return days
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run --extra data --extra api pytest tests/test_calendar.py -v`
Expected: PASS（含原有用例 + 新用例）。

- [ ] **Step 5: Commit**

```bash
git add alphaagent/calendar/ashare.py tests/test_calendar.py
git commit -m "feat(calendar): load/persist trading days via SQLite (parquet fallback kept)"
```

---

## Task 6: JobStore SQLite 持久化 + 启动恢复

**Files:**
- Modify: `alphaagent/api/job_store.py`(整体重写)
- Test: `tests/test_job_store.py` (new)

- [ ] **Step 1: Write the failing test**

```python
# tests/test_job_store.py
from alphaagent.api.job_store import JobStore
from alphaagent.api.schemas.backtest import JobStatus
from alphaagent.storage.db import Database


def test_terminal_state_persists_and_hydrates(tmp_path):
    db = Database(str(tmp_path / "t.db"))
    store = JobStore(db)
    job = store.create(label="x")
    job.update(status=JobStatus.RUNNING, bars_processed=5)   # not persisted
    job.update(status=JobStatus.COMPLETED, result={"k": 1})  # persisted

    store2 = JobStore(db)  # simulate restart
    j2 = store2.get(job.id)
    assert j2 is not None
    assert j2.status == JobStatus.COMPLETED
    assert j2.result == {"k": 1}
    assert j2.label == "x"


def test_interrupted_job_marked_failed_on_restart(tmp_path):
    db = Database(str(tmp_path / "t.db"))
    store = JobStore(db)
    job = store.create()           # inserts a PENDING row, never reaches terminal

    store2 = JobStore(db)          # restart
    j2 = store2.get(job.id)
    assert j2.status == JobStatus.FAILED
    assert j2.error == "interrupted by restart"


def test_delete_removes_row(tmp_path):
    db = Database(str(tmp_path / "t.db"))
    store = JobStore(db)
    job = store.create()
    assert store.delete(job.id) is True

    store2 = JobStore(db)
    assert store2.get(job.id) is None


def test_list_includes_persisted_history(tmp_path):
    db = Database(str(tmp_path / "t.db"))
    store = JobStore(db)
    a = store.create(label="a")
    a.update(status=JobStatus.COMPLETED, result={})
    store2 = JobStore(db)
    assert a.id in {j.id for j in store2.list()}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --extra data --extra api pytest tests/test_job_store.py -v`
Expected: FAIL (`JobStore.__init__` takes no `db` arg).

- [ ] **Step 3: Implement** — 用以下内容整体替换 `alphaagent/api/job_store.py`:

```python
"""SQLite-backed job store for backtest tasks.

Single-process, single-user. The live ``Job`` object keeps its in-memory
runtime bits (cancel_event, lock, version) for cheap high-frequency progress
updates and WS polling. Durable state is written to the shared ``jobs`` table
only on create and on terminal transitions. On startup the store hydrates
history from the DB and marks any non-terminal leftovers (from a process that
died mid-run) as FAILED.
"""

from __future__ import annotations

import json
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable

from alphaagent.api.schemas.backtest import JobStatus
from alphaagent.storage.db import Database

TERMINAL = {JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED}


@dataclass
class Job:
    id: str
    label: str | None = None
    status: JobStatus = JobStatus.PENDING
    progress: float = 0.0
    bars_processed: int = 0
    bars_total: int = 0
    fill_count: int = 0
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error: str | None = None
    result: dict[str, Any] | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    cancel_event: threading.Event = field(
        default_factory=threading.Event, compare=False, repr=False
    )
    version: int = 0  # bumped on every mutation; WS uses it for change detection
    _lock: threading.Lock = field(
        default_factory=threading.Lock, compare=False, repr=False
    )
    _persist: Callable[["Job"], None] | None = field(
        default=None, compare=False, repr=False
    )

    def update(self, **fields: Any) -> None:
        with self._lock:
            for k, v in fields.items():
                setattr(self, k, v)
            self.version += 1
        # Persist outside the job lock; only when reaching a terminal state.
        if self.status in TERMINAL and self._persist is not None:
            self._persist(self)

    def request_cancel(self) -> None:
        self.cancel_event.set()

    def is_cancelled(self) -> bool:
        return self.cancel_event.is_set()


def _iso(dt: datetime | None) -> str | None:
    return dt.isoformat() if dt else None


def _dt(s: str | None) -> datetime | None:
    return datetime.fromisoformat(s) if s else None


def _job_to_row(job: Job) -> tuple:
    return (
        job.id, job.label, job.status.value, job.progress,
        job.bars_processed, job.bars_total, job.fill_count,
        _iso(job.started_at), _iso(job.completed_at), job.error,
        json.dumps(job.result) if job.result is not None else None,
        _iso(job.created_at) or datetime.utcnow().isoformat(),
    )


def _row_to_job(row) -> Job:
    return Job(
        id=row["id"],
        label=row["label"],
        status=JobStatus(row["status"]),
        progress=row["progress"],
        bars_processed=row["bars_processed"],
        bars_total=row["bars_total"],
        fill_count=row["fill_count"],
        started_at=_dt(row["started_at"]),
        completed_at=_dt(row["completed_at"]),
        error=row["error"],
        result=json.loads(row["result_json"]) if row["result_json"] else None,
        created_at=_dt(row["created_at"]) or datetime.utcnow(),
    )


_INSERT = (
    "INSERT OR REPLACE INTO jobs "
    "(id,label,status,progress,bars_processed,bars_total,fill_count,"
    "started_at,completed_at,error,result_json,created_at) "
    "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)"
)


class JobStore:
    def __init__(self, db: Database) -> None:
        self.db = db
        self._jobs: dict[str, Job] = {}
        self._lock = threading.Lock()
        self._hydrate()

    def _persist_job(self, job: Job) -> None:
        self.db.execute(_INSERT, _job_to_row(job))

    def _hydrate(self) -> None:
        for row in self.db.query("SELECT * FROM jobs ORDER BY created_at"):
            job = _row_to_job(row)
            if job.status not in TERMINAL:
                job.status = JobStatus.FAILED
                job.error = "interrupted by restart"
                job.completed_at = datetime.utcnow()
                self._persist_job(job)
            job._persist = self._persist_job
            self._jobs[job.id] = job

    def create(self, label: str | None = None) -> Job:
        jid = str(uuid.uuid4())
        job = Job(id=jid, label=label)
        job._persist = self._persist_job
        with self._lock:
            self._jobs[jid] = job
        self._persist_job(job)  # insert PENDING row so it survives a crash
        return job

    def get(self, jid: str) -> Job | None:
        return self._jobs.get(jid)

    def list(self) -> list[Job]:
        with self._lock:
            return list(self._jobs.values())

    def delete(self, jid: str) -> bool:
        with self._lock:
            existed = self._jobs.pop(jid, None) is not None
        self.db.execute("DELETE FROM jobs WHERE id=?", (jid,))
        return existed
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run --extra data --extra api pytest tests/test_job_store.py -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add alphaagent/api/job_store.py tests/test_job_store.py
git commit -m "feat(api): persist backtest jobs to SQLite with restart recovery"
```

---

## Task 7: deps + backtests router 接入(DRY TERMINAL)

**Files:**
- Modify: `alphaagent/api/deps.py:17-19`, `alphaagent/api/routers/backtests.py:17-29`
- Test: 复用 `tests/test_api.py`(Task 8 改隔离 fixture 后整体验证)

- [ ] **Step 1: Implement deps**

把 `alphaagent/api/deps.py` 的 job-store 提供器改为:

```python
from alphaagent.storage.db import get_database


@lru_cache(maxsize=1)
def get_job_store() -> JobStore:
    return JobStore(get_database())
```

(保留文件其余 import / 其它 provider 不变;`JobStore` 的 import 已存在。)

- [ ] **Step 2: Implement router DRY**

在 `alphaagent/api/routers/backtests.py`:
- 从 import `from alphaagent.api.job_store import Job, JobStore` 改为 `from alphaagent.api.job_store import TERMINAL, Job, JobStore`。
- 删除文件内的本地定义 `TERMINAL = {JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED}`。

- [ ] **Step 3: Smoke import check**

Run: `uv run --extra data --extra api python -c "import alphaagent.api.main"`
Expected: 无异常(import 成功)。

- [ ] **Step 4: Commit**

```bash
git add alphaagent/api/deps.py alphaagent/api/routers/backtests.py
git commit -m "refactor(api): bind JobStore to shared Database; reuse TERMINAL"
```

---

## Task 8: runner 传 db + test_api 隔离 fixture

**Files:**
- Modify: `alphaagent/api/runner.py:86` (`build_calendar` 调用)
- Modify: `tests/test_api.py:17-23` (隔离 fixture)

- [ ] **Step 1: Implement runner**

在 `alphaagent/api/runner.py` 的 `_run` 中,把
```python
    calendar = build_calendar(cfg.calendar)
```
改为
```python
    from alphaagent.storage.db import get_database

    calendar = build_calendar(cfg.calendar, get_database(cfg.storage.db_path))
```

- [ ] **Step 2: Update test_api 隔离 fixture**

把 `tests/test_api.py` 的 `_reset_jobs` fixture 整体替换为:

```python
@pytest.fixture(autouse=True)
def _isolated_db(tmp_path, monkeypatch):
    """Each test gets its own SQLite DB + a fresh JobStore."""
    monkeypatch.setenv("ALPHAAGENT_DB", str(tmp_path / "test.db"))
    from alphaagent.storage import db as _dbmod
    _dbmod._INSTANCES.clear()
    get_job_store.cache_clear()
    yield
    get_job_store.cache_clear()
    _dbmod._INSTANCES.clear()
```

(文件顶部已 `from alphaagent.api.deps import get_job_store`,无需改 import。)

- [ ] **Step 3: Run the API suite**

Run: `uv run --extra data --extra api pytest tests/test_api.py -v`
Expected: PASS（5 个用例,含 submit→poll→completed、result、list、404、invalid-config-fails）。

- [ ] **Step 4: 重启持久化手工断言(可选自动化)**

新增 `tests/test_api.py::test_jobs_survive_store_restart`:

```python
def test_jobs_survive_store_restart(client, synthetic_data):
    import time as _t

    from alphaagent.api.deps import get_job_store

    cfg = _config(synthetic_data)
    job_id = client.post("/api/backtests", json={"config": cfg}).json()["data"]["job_id"]
    for _ in range(50):
        info = client.get(f"/api/backtests/{job_id}").json()["data"]
        if info["status"] in ("completed", "failed"):
            break
        _t.sleep(0.05)
    assert info["status"] == "completed"

    # Drop the cached store; a new one must hydrate the finished job from SQLite.
    get_job_store.cache_clear()
    listed = client.get("/api/backtests").json()["data"]
    assert job_id in {j["id"] for j in listed}
```

Run: `uv run --extra data --extra api pytest tests/test_api.py::test_jobs_survive_store_restart -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add alphaagent/api/runner.py tests/test_api.py
git commit -m "feat(api): persist calendar via db in runner; isolate API tests per tmp DB"
```

---

## Task 9: 迁移脚本 scripts/migrate_cache.py

**Files:**
- Create: `scripts/__init__.py`, `scripts/migrate_cache.py`
- Test: `tests/test_migrate_cache.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_migrate_cache.py
from datetime import date

import pandas as pd

from alphaagent.storage.db import Database


def _write_parquet(path, idx):
    df = pd.DataFrame(
        {
            "open": range(len(idx)), "high": range(len(idx)),
            "low": range(len(idx)), "close": range(len(idx)),
            "volume": [100] * len(idx), "amount": [200] * len(idx),
        },
        index=idx,
    )
    df.to_parquet(path)
    return df


def test_migrate_bars_imports_and_skips_legacy(tmp_path):
    from scripts.migrate_cache import migrate_bars

    cache = tmp_path / "cache"
    cache.mkdir()
    idx = pd.date_range("2023-01-03", "2023-01-31", freq="B")
    _write_parquet(cache / "600000_1d__akshare-sina-qfq.parquet", idx)
    _write_parquet(cache / "600001_1d.parquet", idx)  # legacy: no __source_id

    db = Database(str(tmp_path / "t.db"))
    imported, rows, skipped = migrate_bars(db, str(cache))

    assert imported == 1
    assert skipped == 1
    assert rows == len(idx)
    n = db.query(
        "SELECT COUNT(*) AS n FROM bars WHERE source_id='akshare-sina-qfq' "
        "AND symbol='600000' AND freq='1d'"
    )[0]["n"]
    assert n == len(idx)


def test_migrate_calendar(tmp_path):
    from scripts.migrate_cache import migrate_calendar

    cal_path = tmp_path / "cal.parquet"
    pd.DataFrame(
        {"trade_date": pd.to_datetime([date(2024, 1, 2), date(2024, 1, 3)])}
    ).to_parquet(cal_path)

    db = Database(str(tmp_path / "t.db"))
    n = migrate_calendar(db, str(cal_path))
    assert n == 2
    assert db.query("SELECT COUNT(*) AS n FROM trade_calendar")[0]["n"] == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --extra data --extra api pytest tests/test_migrate_cache.py -v`
Expected: FAIL (`ModuleNotFoundError: scripts.migrate_cache`).

- [ ] **Step 3: Implement**

```python
# scripts/__init__.py
```
(空文件,使 `scripts` 成为可导入包;pytest `pythonpath=["."]` 已配置。)

```python
# scripts/migrate_cache.py
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

import pandas as pd

from alphaagent.data.sqlite_cache import upsert_bars
from alphaagent.storage.db import Database, resolve_db_path

_NAME_RE = re.compile(r"^(?P<symbol>[^_]+)_(?P<freq>[^_]+)__(?P<source_id>.+)\.parquet$")


def migrate_bars(db: Database, cache_dir: str) -> tuple[int, int, int]:
    from pathlib import Path

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
    ap.add_argument("--db", default=None, help="SQLite path; default ALPHAAGENT_DB or ./data/alphaagent.db")
    ap.add_argument("--calendar", default=None, help="Optional calendar parquet path.")
    args = ap.parse_args()

    db = Database(resolve_db_path(args.db))
    imported, rows, skipped = migrate_bars(db, args.cache_dir)
    print(f"bars: imported {imported} files, {rows} rows, skipped {skipped} legacy")
    if args.calendar:
        n = migrate_calendar(db, args.calendar)
        print(f"calendar: {n} dates")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run --extra data --extra api pytest tests/test_migrate_cache.py -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add scripts/__init__.py scripts/migrate_cache.py tests/test_migrate_cache.py
git commit -m "feat(scripts): add one-off Parquet->SQLite migration"
```

---

## Task 10: 全量回归 + ruff

**Files:** 无新增(验证 + 必要修复)

- [ ] **Step 1: 跑全量测试**

Run: `uv run --extra data --extra api pytest -q`
Expected: 全绿。`tests/test_cache.py`(旧 Parquet 缓存)仍在,应继续通过(Phase 3 才删)。若有红:对照报错按 systematic-debugging 修单点,不要批量改。

- [ ] **Step 2: ruff**

Run: `uv run --extra dev ruff check alphaagent tests scripts`
Expected: 无新增告警。常见需修:未用 import(如 runtime 里旧的 `CachedDataSource` 已移除)、`N`/`UP` 规则。逐条修。

- [ ] **Step 3: Commit(若有修复)**

```bash
git add -A
git commit -m "chore: lint + test fixups for sqlite persistence"
```

---

## Task 11: 文档更新

**Files:**
- Modify: `README.md`(「缓存机制」「配置」段)

- [ ] **Step 1: 更新 README**

- 「缓存机制」段:把「`CachedDataSource` 落 Parquet」改为「`SqliteBarCache` 落统一 SQLite 库(`storage.db_path`,默认 `./data/alphaagent.db`),行级 `INSERT OR REPLACE` 增量」。
- 「配置」示例 YAML 增加:

```yaml
storage:
  db_path: ./data/alphaagent.db   # 回测任务/行情缓存/交易日历统一入库;可被环境变量 ALPHAAGENT_DB 覆盖
```

- 新增「数据迁移」小节:

```bash
# 把旧的 Parquet 缓存导入 SQLite(一次性,幂等)
uv run python scripts/migrate_cache.py --cache-dir ./data/cache \
    --calendar ./data/cache/ashare_calendar.parquet
```

- 说明:回测历史/结果现已持久化,`alphaagent-api` 重启后 `GET /api/backtests` 仍可见;上次未完成的任务标记为 `interrupted by restart`。

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: document SQLite storage, migration script, job persistence"
```

---

## Self-Review(计划编写者已核对)

- **Spec 覆盖:** §4 Database→Task2;§5 schema→Task2;§6 SqliteBarCache→Task3/4;§7 calendar→Task5;§8 JobStore→Task6/7/8;§9 迁移脚本→Task9;§10 StorageConfig→Task1;§11 测试/清理→各 Task + Task10(注:Parquet 后端删除属 Phase 3,本计划不含);§13 验收→Task8(重启可见)/Task9(迁移)/Task10(全绿)。
- **占位符:** 无 TBD/TODO;每个代码步骤均给出完整代码与命令。
- **类型一致性:** `Database.execute/executemany/query/query_df`、`get_database/resolve_db_path`、`upsert_bars(db,source_id,symbol,freq,df)`、`SqliteBarCache(upstream,db,source_id)`、`JobStore(db)`、`build_calendar(cfg,db=None)`、`TERMINAL`(job_store 定义、router 导入)在各 Task 间签名一致。
- **执行顺序依赖:** Task4 先于 Task5 实现日历参数,但 Task4 的测试不构建日历;按 1→11 顺序执行即可避免红。
