"""Hard filters: drop symbols before scoring (no score, just keep/drop)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date

import pandas as pd

from alphaagent.screener.meta import StockMeta, name_implies_st


class HardFilter(ABC):
    name: str

    @abstractmethod
    def keep(self, symbol: str, bars: pd.DataFrame, meta: StockMeta) -> bool: ...


class MinPrice(HardFilter):
    """Keep symbols whose latest close >= ``min_price``."""

    name = "min_price"

    def __init__(self, min_price: float = 3.0):
        self.min_price = min_price

    def keep(self, symbol: str, bars: pd.DataFrame, meta: StockMeta) -> bool:
        if bars.empty:
            return False
        return float(bars["close"].iloc[-1]) >= self.min_price


class MaxPrice(HardFilter):
    """Keep symbols whose latest close <= ``max_price``."""

    name = "max_price"

    def __init__(self, max_price: float = 500.0):
        self.max_price = max_price

    def keep(self, symbol: str, bars: pd.DataFrame, meta: StockMeta) -> bool:
        if bars.empty:
            return False
        return float(bars["close"].iloc[-1]) <= self.max_price


class MinAvgVolume(HardFilter):
    """Keep symbols whose mean daily ``amount`` over last N bars >= threshold.

    Uses ``amount`` (turnover in CNY), which is invariant to splits/dividends —
    unlike ``volume`` (share count), which jumps after rights issues.
    """

    name = "min_avg_volume"

    def __init__(self, lookback: int = 20, min_amount: float = 1e7):
        if lookback < 1:
            raise ValueError("lookback must be >= 1")
        self.lookback = lookback
        self.min_amount = min_amount

    def keep(self, symbol: str, bars: pd.DataFrame, meta: StockMeta) -> bool:
        if "amount" not in bars.columns or len(bars) < self.lookback:
            return False
        avg = float(bars["amount"].tail(self.lookback).mean())
        return avg >= self.min_amount


class ExcludeST(HardFilter):
    """Drop symbols whose name flags them as ST/退/* (delisting risk).

    MVP uses name keywords from ``meta.is_st``. Misses historical ST status
    (capping/uncapping events). TODO(v2): switch to Tushare ``stock_st``.
    """

    name = "exclude_st"

    def keep(self, symbol: str, bars: pd.DataFrame, meta: StockMeta) -> bool:
        if meta.is_st:
            return False
        # Defensive: if meta lookup failed, fall back to checking name field.
        return not name_implies_st(meta.name)


class MinListedDays(HardFilter):
    """Drop symbols listed for fewer than ``min_days`` calendar days."""

    name = "min_listed_days"

    def __init__(self, min_days: int = 250):
        if min_days < 0:
            raise ValueError("min_days must be >= 0")
        self.min_days = min_days

    def keep(self, symbol: str, bars: pd.DataFrame, meta: StockMeta) -> bool:
        if meta.list_date is None:
            # Unknown listing date — be permissive (don't drop).
            return True
        as_of = bars.index[-1].date() if len(bars) else date.today()
        return (as_of - meta.list_date).days >= self.min_days


BUILTIN_FILTERS: dict[str, type[HardFilter]] = {
    "min_price": MinPrice,
    "max_price": MaxPrice,
    "min_avg_volume": MinAvgVolume,
    "exclude_st": ExcludeST,
    "min_listed_days": MinListedDays,
}


def build_filter(spec: dict) -> HardFilter:
    """Build a filter from a config dict like ``{"type": "min_price", "min_price": 3.0}``."""
    spec = dict(spec)
    filter_type = spec.pop("type")
    cls = BUILTIN_FILTERS.get(filter_type)
    if cls is None:
        available = ", ".join(sorted(BUILTIN_FILTERS))
        raise ValueError(f"unknown filter: {filter_type!r}. available: {available}")
    return cls(**spec)
