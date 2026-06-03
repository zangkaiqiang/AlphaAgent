"""AkShare-backed data source for A-share daily and minute bars.

Only imported lazily so that the package installs without akshare. Install
with ``pip install alphaagent[data]`` to enable.

Supported freqs: ``1d`` (daily), ``1m`` / ``5m`` / ``15m`` / ``30m`` / ``60m``.

Daily bars can come from one of two upstreams (see ``resolve_daily_backend``):
- ``sina`` (default): via ``stock_zh_a_daily``. No ``amount`` column natively,
  so we synthesize it as ``close * volume``. Reachable when the eastmoney push
  servers are dropped by a local proxy or blocked from non-CN exit IPs.
- ``eastmoney``: full OHLCV+amount via ``stock_zh_a_hist``, but the
  push2*.eastmoney.com servers are frequently unreachable. Opt in with
  ``ALPHAAGENT_AKSHARE_BACKEND=eastmoney`` or config ``data.akshare_backend``.

Minute bars only support eastmoney (sina has no equivalent in akshare).
"""

from __future__ import annotations

import os
from datetime import date, datetime, time
from typing import Literal

import pandas as pd

from alphaagent.data.base import DataSource

_MINUTE_PERIODS = {"1m": "1", "5m": "5", "15m": "15", "30m": "30", "60m": "60"}

DailyBackend = Literal["eastmoney", "sina"]

# Default to sina: the eastmoney push servers (push2*.eastmoney.com) are
# routinely dropped by local proxies / blocked from non-CN exit IPs, while
# sina's daily endpoint stays reachable. Override per-process with
# ALPHAAGENT_AKSHARE_BACKEND, or explicitly via config / constructor arg.
_DEFAULT_DAILY_BACKEND: DailyBackend = "sina"


def resolve_daily_backend(explicit: str | None = None) -> DailyBackend:
    """Resolve the daily-bar upstream: explicit arg > env var > sina default.

    ``explicit`` is what a caller passed (may be ``None`` when unset, e.g. a
    config field that wasn't provided). Empty/None falls through to the
    ``ALPHAAGENT_AKSHARE_BACKEND`` env var, then the sina default.
    """
    value = (explicit or os.environ.get("ALPHAAGENT_AKSHARE_BACKEND") or _DEFAULT_DAILY_BACKEND)
    value = value.lower()
    if value not in ("eastmoney", "sina"):
        raise ValueError(
            f"daily_backend must be 'eastmoney' or 'sina', got {value!r}"
        )
    return value  # type: ignore[return-value]


class AkShareDataSource(DataSource):
    """Fetches A-share bars via AkShare.

    Symbol format: 6-digit code, e.g. "600000" or "000001".
    """

    def __init__(
        self,
        adjust: str = "qfq",
        daily_backend: DailyBackend | None = None,
    ) -> None:
        self.adjust = adjust
        self.daily_backend = resolve_daily_backend(daily_backend)

    def get_bars(
        self,
        symbol: str,
        start: date,
        end: date,
        freq: str = "1d",
    ) -> pd.DataFrame:
        import akshare as ak

        if freq == "1d":
            if self.daily_backend == "eastmoney":
                df = ak.stock_zh_a_hist(
                    symbol=symbol,
                    period="daily",
                    start_date=start.strftime("%Y%m%d"),
                    end_date=end.strftime("%Y%m%d"),
                    adjust=self.adjust,
                )
                return self._normalize(df, intraday=False)
            # sina backend
            df = ak.stock_zh_a_daily(
                symbol=_to_sina_symbol(symbol),
                start_date=start.strftime("%Y%m%d"),
                end_date=end.strftime("%Y%m%d"),
                adjust=self.adjust,
            )
            return self._normalize_sina(df)

        if freq in _MINUTE_PERIODS:
            start_dt = datetime.combine(start, time(9, 30)).strftime("%Y-%m-%d %H:%M:%S")
            end_dt = datetime.combine(end, time(15, 0)).strftime("%Y-%m-%d %H:%M:%S")
            df = ak.stock_zh_a_hist_min_em(
                symbol=symbol,
                start_date=start_dt,
                end_date=end_dt,
                period=_MINUTE_PERIODS[freq],
                adjust=self.adjust or "",
            )
            return self._normalize(df, intraday=True)

        raise NotImplementedError(f"AkShare source does not support freq={freq!r}")

    @staticmethod
    def _normalize(df: pd.DataFrame, intraday: bool) -> pd.DataFrame:
        if df is None or df.empty:
            return pd.DataFrame()
        rename = {
            "日期": "date",
            "时间": "date",
            "开盘": "open",
            "最高": "high",
            "最低": "low",
            "收盘": "close",
            "成交量": "volume",
            "成交额": "amount",
        }
        df = df.rename(columns=rename)
        df["date"] = pd.to_datetime(df["date"])
        cols = ["open", "high", "low", "close", "volume"]
        if "amount" in df.columns:
            cols.append("amount")
        return df.set_index("date")[cols].sort_index()

    @staticmethod
    def _normalize_sina(df: pd.DataFrame) -> pd.DataFrame:
        """Sina returns columns: date, open, high, low, close, volume,
        outstanding_share, turnover. Sina's ``volume`` is in shares already
        (not 100-share lots), and there's no ``amount``. Synthesize amount
        as ``close * volume`` so downstream rules using amount still work.
        """
        if df is None or df.empty:
            return pd.DataFrame()
        df = df.copy()
        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date").sort_index()
        if "amount" not in df.columns:
            df["amount"] = df["close"] * df["volume"]
        return df[["open", "high", "low", "close", "volume", "amount"]]


def _to_sina_symbol(code: str) -> str:
    """Sina expects ``shXXXXXX`` / ``szXXXXXX`` / ``bjXXXXXX`` prefixes."""
    code = str(code).zfill(6)
    if code.startswith(("60", "68", "9")):
        return f"sh{code}"
    if code.startswith(("00", "30", "20")):
        return f"sz{code}"
    if code.startswith(("4", "8")):
        return f"bj{code}"
    return f"sh{code}"
