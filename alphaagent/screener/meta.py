"""Stock metadata providers.

Static/slow-changing fields (name, industry, list_date, ST status) live
here, separate from bar data. Names change over time (ST flag, renames),
so caches use a daily TTL — code is immutable so the cache key is safe.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

import pandas as pd

_ST_NAME_KEYWORDS = ("ST", "退", "*")


def _normalize_symbol(s: str) -> str:
    """Zero-pad numeric A-share codes to 6 digits; leave non-numeric as is.

    Real codes look like "1" → "000001". Test tickers like "UPUP" are kept
    verbatim to make synthetic fixtures readable.
    """
    s = str(s)
    if s.isdigit():
        return s.zfill(6)
    return s


@dataclass
class StockMeta:
    symbol: str
    name: str
    industry: str | None = None
    list_date: date | None = None
    delist_date: date | None = None
    is_st: bool = False
    extra: dict = field(default_factory=dict)


class StockMetaProvider(ABC):
    @abstractmethod
    def get_meta(self, symbol: str, as_of: date) -> StockMeta: ...

    def get_meta_batch(
        self,
        symbols: list[str],
        as_of: date,
        max_workers: int = 8,
    ) -> dict[str, StockMeta]:
        """Default: concurrent calls to ``get_meta``. Override for batch APIs."""
        out: dict[str, StockMeta] = {}
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            for sym, meta in zip(
                symbols,
                pool.map(lambda s: self.get_meta(s, as_of), symbols),
                strict=True,
            ):
                out[sym] = meta
        return out


class CSVMetaProvider(StockMetaProvider):
    """Reads a CSV with columns: symbol, name, industry, list_date.

    Useful for tests and offline workflows.
    """

    def __init__(self, csv_path: str | Path):
        df = pd.read_csv(csv_path, dtype={"symbol": str})
        if "symbol" not in df.columns or "name" not in df.columns:
            raise ValueError("meta csv must have 'symbol' and 'name' columns")
        df["symbol"] = df["symbol"].astype(str).map(_normalize_symbol)
        if "list_date" in df.columns:
            df["list_date"] = pd.to_datetime(df["list_date"], errors="coerce")
        self._by_symbol = {row["symbol"]: row for _, row in df.iterrows()}

    def get_meta(self, symbol: str, as_of: date) -> StockMeta:
        symbol = _normalize_symbol(symbol)
        if symbol not in self._by_symbol:
            return StockMeta(symbol=symbol, name=symbol)
        row = self._by_symbol[symbol]
        name = str(row.get("name") or symbol)
        industry = row.get("industry")
        if pd.isna(industry):
            industry = None
        list_date_val = row.get("list_date")
        list_date = (
            list_date_val.date()
            if hasattr(list_date_val, "date") and not pd.isna(list_date_val)
            else None
        )
        return StockMeta(
            symbol=symbol,
            name=name,
            industry=industry,
            list_date=list_date,
            is_st=any(kw in name for kw in _ST_NAME_KEYWORDS),
        )


class AkshareMetaProvider(StockMetaProvider):
    """Stock metadata from akshare with daily-TTL JSON cache.

    Cache layout: ``<cache_dir>/<symbol>.json`` containing fetched_on +
    fields. If ``fetched_on`` is today, the cache is reused; otherwise
    refreshed. The 'name' field is intentionally not persisted forever
    (ST flag flips daily).
    """

    def __init__(self, cache_dir: str | Path | None = None):
        self._cache_dir = Path(cache_dir) if cache_dir else None
        if self._cache_dir is not None:
            self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._name_table: dict[str, str] | None = None

    def _load_name_table(self) -> dict[str, str]:
        if self._name_table is not None:
            return self._name_table
        import akshare as ak

        df = ak.stock_info_a_code_name()
        df["code"] = df["code"].astype(str).str.zfill(6)
        self._name_table = dict(zip(df["code"], df["name"], strict=True))
        return self._name_table

    def _cache_path(self, symbol: str) -> Path | None:
        if self._cache_dir is None:
            return None
        return self._cache_dir / f"{symbol}.json"

    def _read_cache(self, symbol: str) -> dict | None:
        path = self._cache_path(symbol)
        if path is None or not path.exists():
            return None
        try:
            data = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError):
            return None
        fetched_on = data.get("fetched_on")
        if fetched_on != date.today().isoformat():
            return None
        return data

    def _write_cache(self, symbol: str, payload: dict) -> None:
        path = self._cache_path(symbol)
        if path is None:
            return
        payload = dict(payload)
        payload["fetched_on"] = date.today().isoformat()
        path.write_text(json.dumps(payload, ensure_ascii=False))

    def get_meta(self, symbol: str, as_of: date) -> StockMeta:
        symbol = _normalize_symbol(symbol)
        cached = self._read_cache(symbol)
        if cached is not None:
            return _meta_from_dict(symbol, cached)

        # Always re-resolve name from the daily table (cheap once loaded).
        name = self._load_name_table().get(symbol, symbol)

        industry: str | None = None
        list_date: date | None = None
        try:
            import akshare as ak

            info = ak.stock_individual_info_em(symbol=symbol)
            kv = dict(zip(info["item"], info["value"], strict=True))
            industry = kv.get("行业") or None
            ld = kv.get("上市时间")
            if ld:
                try:
                    list_date = datetime.strptime(str(ld), "%Y%m%d").date()
                except ValueError:
                    list_date = None
        except Exception:
            # Network/akshare hiccups shouldn't kill the whole screen run.
            pass

        payload = {
            "name": name,
            "industry": industry,
            "list_date": list_date.isoformat() if list_date else None,
        }
        self._write_cache(symbol, payload)
        return _meta_from_dict(symbol, payload)


def _meta_from_dict(symbol: str, data: dict) -> StockMeta:
    name = data.get("name") or symbol
    list_date_str = data.get("list_date")
    list_date = (
        datetime.fromisoformat(list_date_str).date() if list_date_str else None
    )
    return StockMeta(
        symbol=symbol,
        name=name,
        industry=data.get("industry"),
        list_date=list_date,
        is_st=any(kw in name for kw in _ST_NAME_KEYWORDS),
    )


class TushareMetaProvider(StockMetaProvider):
    """Tushare ``stock_basic`` — single batch call. Planned for v2."""

    def __init__(self, cache_dir: str | Path | None = None):
        self._cache_dir = Path(cache_dir) if cache_dir else None

    def get_meta(self, symbol: str, as_of: date) -> StockMeta:
        raise NotImplementedError(
            "TushareMetaProvider requires Tushare 2000 points; planned for v2."
        )


# Re-exported so other modules don't need to know the keyword list.
def name_implies_st(name: str) -> bool:
    return any(kw in name for kw in _ST_NAME_KEYWORDS)


__all__ = [
    "AkshareMetaProvider",
    "CSVMetaProvider",
    "StockMeta",
    "StockMetaProvider",
    "TushareMetaProvider",
    "name_implies_st",
]
