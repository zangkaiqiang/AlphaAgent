"""Concurrent bar fetcher with optional progress bar.

Wraps any ``DataSource`` and pulls bars for many symbols in parallel.
The cached source short-circuits to disk reads, so this is fast on
warm caches even with serial work behind the scenes.
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import date

import pandas as pd

from alphaagent.data.base import DataSource

logger = logging.getLogger(__name__)


@dataclass
class FetchResult:
    """Panel of successfully-fetched bars plus the symbols that didn't make it.

    Callers should surface ``failed`` — otherwise a universe of 300 that
    silently becomes 250 will look like a clean screen over 250.
    """

    bars: dict[str, pd.DataFrame] = field(default_factory=dict)
    failed: dict[str, str] = field(default_factory=dict)  # symbol -> reason

    @property
    def failure_rate(self) -> float:
        total = len(self.bars) + len(self.failed)
        return len(self.failed) / total if total else 0.0


def fetch_panel(
    source: DataSource,
    symbols: list[str],
    start: date,
    end: date,
    freq: str = "1d",
    max_workers: int = 16,
    show_progress: bool = True,
    desc: str = "Fetching data",
) -> FetchResult:
    """Pull bars for ``symbols`` in parallel, returning successes and failures.

    Failures are logged (DEBUG per-symbol, WARN on summary) and returned
    alongside the panel so the pipeline can report them.
    """
    result = FetchResult()
    pbar = _make_pbar(len(symbols), desc, enabled=show_progress)
    try:
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = {
                pool.submit(_safe_fetch, source, sym, start, end, freq): sym
                for sym in symbols
            }
            for fut in as_completed(futures):
                sym = futures[fut]
                df, err = fut.result()
                if err is not None:
                    result.failed[sym] = err
                elif df is None or df.empty:
                    result.failed[sym] = "empty"
                else:
                    result.bars[sym] = df
                if pbar is not None:
                    pbar.update(1)
    finally:
        if pbar is not None:
            pbar.close()

    if result.failed:
        sample = list(result.failed.items())[:5]
        logger.warning(
            "fetch failed for %d/%d symbols (%.1f%%); sample: %s",
            len(result.failed),
            len(symbols),
            result.failure_rate * 100,
            sample,
        )
    return result


def _safe_fetch(
    source: DataSource, symbol: str, start: date, end: date, freq: str
) -> tuple[pd.DataFrame | None, str | None]:
    try:
        return source.get_bars(symbol, start, end, freq=freq), None
    except Exception as exc:
        logger.debug("fetch %s failed: %s", symbol, exc)
        return None, f"{type(exc).__name__}: {exc}"


def _make_pbar(total: int, desc: str, enabled: bool):
    if not enabled:
        return None
    try:
        from tqdm import tqdm

        return tqdm(total=total, desc=desc, unit="sym")
    except ImportError:
        return None
