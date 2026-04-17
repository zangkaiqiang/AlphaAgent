"""AkShare-backed data source for A-share daily bars.

Only imported lazily so that the package installs without akshare. Install
with ``pip install alphaagent[data]`` to enable.
"""

from __future__ import annotations

from datetime import date

import pandas as pd

from alphaagent.data.base import DataSource


class AkShareDataSource(DataSource):
    """Fetches A-share daily bars via AkShare.

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

        if freq != "1d":
            raise NotImplementedError("AkShare source currently supports 1d only")
        df = ak.stock_zh_a_hist(
            symbol=symbol,
            period="daily",
            start_date=start.strftime("%Y%m%d"),
            end_date=end.strftime("%Y%m%d"),
            adjust=self.adjust,
        )
        if df.empty:
            return df
        df = df.rename(
            columns={
                "日期": "date",
                "开盘": "open",
                "最高": "high",
                "最低": "low",
                "收盘": "close",
                "成交量": "volume",
                "成交额": "amount",
            }
        )
        df["date"] = pd.to_datetime(df["date"])
        return df.set_index("date")[["open", "high", "low", "close", "volume", "amount"]]
