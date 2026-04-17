"""Tushare Pro-backed data source for A-share daily bars.

Requires a Tushare Pro token. Pass it explicitly or set ``TUSHARE_TOKEN``
in the environment.

Symbol format: 6-digit code (e.g. ``600000``). The adapter auto-appends
``.SH`` / ``.SZ`` / ``.BJ`` based on the code prefix.
"""

from __future__ import annotations

import os
from datetime import date

import pandas as pd

from alphaagent.data.base import DataSource


def _ts_symbol(symbol: str) -> str:
    """Convert 6-digit code to Tushare ``ts_code`` with exchange suffix."""
    if "." in symbol:
        return symbol
    if symbol.startswith(("60", "68", "90", "113", "11", "51", "58")):
        return f"{symbol}.SH"
    if symbol.startswith(("00", "30", "20", "12", "15", "16", "18")):
        return f"{symbol}.SZ"
    if symbol.startswith(("43", "83", "87", "88")):
        return f"{symbol}.BJ"
    raise ValueError(f"cannot infer exchange for symbol: {symbol}")


class TushareDataSource(DataSource):
    def __init__(self, token: str | None = None, adjust: str = "qfq"):
        self.token = token or os.environ.get("TUSHARE_TOKEN")
        if not self.token:
            raise ValueError(
                "Tushare token not provided. Pass token= or set TUSHARE_TOKEN env var."
            )
        if adjust not in {"qfq", "hfq", None, ""}:
            raise ValueError(f"invalid adjust: {adjust!r}")
        self.adjust = adjust or None

    def _client(self):
        import tushare as ts

        ts.set_token(self.token)
        return ts.pro_api()

    def get_bars(
        self,
        symbol: str,
        start: date,
        end: date,
        freq: str = "1d",
    ) -> pd.DataFrame:
        if freq != "1d":
            raise NotImplementedError("Tushare source currently supports 1d only")

        import tushare as ts

        pro = self._client()
        ts_code = _ts_symbol(symbol)
        start_s = start.strftime("%Y%m%d")
        end_s = end.strftime("%Y%m%d")

        if self.adjust is None:
            df = pro.daily(ts_code=ts_code, start_date=start_s, end_date=end_s)
        else:
            df = ts.pro_bar(
                ts_code=ts_code,
                start_date=start_s,
                end_date=end_s,
                adj=self.adjust,
                freq="D",
                asset="E",
            )

        if df is None or df.empty:
            return pd.DataFrame()

        df = df.rename(columns={"vol": "volume"})
        df["date"] = pd.to_datetime(df["trade_date"])
        df = df.set_index("date").sort_index()
        cols = ["open", "high", "low", "close", "volume"]
        if "amount" in df.columns:
            cols.append("amount")
        return df[cols]
