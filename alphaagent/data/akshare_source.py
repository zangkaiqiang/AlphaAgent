"""AkShare-backed data source for A-share daily and minute bars.

Only imported lazily so that the package installs without akshare. Install
with ``pip install alphaagent[data]`` to enable.

Supported freqs: ``1d`` (daily), ``1m`` / ``5m`` / ``15m`` / ``30m`` / ``60m``.
"""

from __future__ import annotations

from datetime import date, datetime, time

import pandas as pd

from alphaagent.data.base import DataSource

_MINUTE_PERIODS = {"1m": "1", "5m": "5", "15m": "15", "30m": "30", "60m": "60"}


class AkShareDataSource(DataSource):
    """Fetches A-share bars via AkShare.

    Symbol format: 6-digit code, e.g. "600000" or "000001".
    """

    def __init__(self, adjust: str = "qfq") -> None:
        self.adjust = adjust

    def get_bars(
        self,
        symbol: str,
        start: date,
        end: date,
        freq: str = "1d",
    ) -> pd.DataFrame:
        import akshare as ak

        if freq == "1d":
            df = ak.stock_zh_a_hist(
                symbol=symbol,
                period="daily",
                start_date=start.strftime("%Y%m%d"),
                end_date=end.strftime("%Y%m%d"),
                adjust=self.adjust,
            )
            return self._normalize(df, intraday=False)

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
