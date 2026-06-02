"""Reusable builder helpers for screener components.

Used by both the CLI (``alphaagent.cli``) and the API routes.
The old private copies in ``cli.py`` are replaced by these public functions.

Key difference from the old CLI helpers
----------------------------------------
``build_screen_data_source`` wraps the upstream with ``SqliteBarCache``
(via ``get_database()`` + ``source_id_for_data_cfg``) instead of the
Parquet ``CachedDataSource`` used by the original ``_build_screen_data_source``
in ``cli.py``.  This aligns the screener cache with the API / runtime data
path so both share the same SQLite store and the same source-ID convention:
``{source}_{freq}_{adjust}``  (from ``runtime.source_id_for_data_cfg``).

The old CLI used a different ID scheme
(``akshare-{backend}-{adjust}``, ``tushare-{adjust}``) which would have
mixed up rows had both the backtest API and the screener CLI ever shared a
cache file. The new scheme is consistent.
"""

from __future__ import annotations

from alphaagent.data.base import DataSource
from alphaagent.screener.universe import Universe

# ---------------------------------------------------------------------------
# Universe
# ---------------------------------------------------------------------------


def build_universe(cfg) -> Universe:
    """Build a Universe from a *ScreenAppConfig* (or duck-typed equivalent)."""
    from alphaagent.screener.universe import (
        AkshareIndexUniverse,
        StaticUniverse,
        TushareIndexUniverse,
    )

    src = cfg.universe.source
    if src == "static":
        return StaticUniverse(cfg.universe.symbols, name="static")
    if src == "akshare_index":
        return AkshareIndexUniverse(cfg.universe.index_code)
    if src == "tushare_index":
        return TushareIndexUniverse(cfg.universe.index_code)
    raise ValueError(f"unknown universe source: {src!r}")


# ---------------------------------------------------------------------------
# Meta provider
# ---------------------------------------------------------------------------


def build_meta_provider(cfg):
    """Build a StockMetaProvider from a *ScreenAppConfig*."""
    from alphaagent.screener.meta import (
        AkshareMetaProvider,
        CSVMetaProvider,
        TushareMetaProvider,
    )

    src = cfg.meta.source
    if src == "akshare":
        return AkshareMetaProvider(cache_dir=cfg.meta.cache_dir)
    if src == "csv":
        return CSVMetaProvider(cfg.meta.csv)
    if src == "tushare":
        return TushareMetaProvider(cache_dir=cfg.meta.cache_dir)
    raise ValueError(f"unknown meta source: {src!r}")


# ---------------------------------------------------------------------------
# Data source
# ---------------------------------------------------------------------------


def build_screen_data_source(cfg) -> DataSource:
    """Build a DataSource for the screener, optionally wrapped with SqliteBarCache.

    When ``cfg.data.cache_dir`` is set the upstream source is wrapped with
    ``SqliteBarCache`` using the shared server-level database (``get_database()``)
    and a source-id derived via ``source_id_for_data_cfg`` from ``alphaagent.runtime``.
    This is the same cache path used by the backtest API, ensuring a single
    consistent SQLite store.

    Akshare/tushare sources are imported lazily to avoid pulling those heavy
    optional dependencies at module load time.
    """
    from alphaagent.data.csv_source import CSVDataSource

    data = cfg.data
    if data.source == "csv":
        if not data.root:
            raise ValueError("data.root is required for csv source")
        source: DataSource = CSVDataSource(data.root)
    elif data.source == "akshare":
        from alphaagent.data.akshare_source import AkShareDataSource

        source = AkShareDataSource(
            adjust=data.adjust or "qfq",
            daily_backend=getattr(data, "akshare_backend", None),
        )
    elif data.source == "tushare":
        from alphaagent.data.tushare_source import TushareDataSource

        source = TushareDataSource(
            token=data.tushare_token, adjust=data.adjust or "qfq"
        )
    else:
        raise ValueError(f"unknown data source: {data.source!r}")

    if data.cache_dir:
        from alphaagent.data.sqlite_cache import SqliteBarCache
        from alphaagent.runtime import source_id_for_data_cfg
        from alphaagent.storage.db import get_database

        source = SqliteBarCache(
            source,
            get_database(),
            source_id_for_data_cfg(data),
        )

    return source
