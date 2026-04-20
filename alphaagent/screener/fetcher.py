"""Concurrent bar fetcher with optional progress bar.

Wraps any ``DataSource`` and pulls bars for many symbols in parallel.
The cached source short-circuits to disk reads, so this is fast on
warm caches even with serial work behind the scenes.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date

import pandas as pd

from alphaagent.data.base import DataSource


def fetch_panel(
    source: DataSource,
    symbols: list[str],
    start: date,
    end: date,
    freq: str = "1d",
    max_workers: int = 16,
    show_progress: bool = True,
    desc: str = "Fetching data",
) -> dict[str, pd.DataFrame]:
    """Pull bars for ``symbols`` in parallel and return ``{symbol: bars}``.

    Symbols that fail or come back empty are silently dropped — the screener
    pipeline will skip them in scoring rather than crash the whole run.
    """
    out: dict[str, pd.DataFrame] = {}
    pbar = _make_pbar(len(symbols), desc, enabled=show_progress)
    try:
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = {
                pool.submit(_safe_fetch, source, sym, start, end, freq): sym
                for sym in symbols
            }
            for fut in as_completed(futures):
                sym = futures[fut]
                df = fut.result()
                if df is not None and not df.empty:
                    out[sym] = df
                if pbar is not None:
                    pbar.update(1)
    finally:
        if pbar is not None:
            pbar.close()
    return out


def _safe_fetch(
    source: DataSource, symbol: str, start: date, end: date, freq: str
) -> pd.DataFrame | None:
    try:
        return source.get_bars(symbol, start, end, freq=freq)
    except Exception:
        return None


def _make_pbar(total: int, desc: str, enabled: bool):
    if not enabled:
        return None
    try:
        from tqdm import tqdm

        return tqdm(total=total, desc=desc, unit="sym")
    except ImportError:
        return None
