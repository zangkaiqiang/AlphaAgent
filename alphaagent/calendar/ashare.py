"""A-share trading calendar.

Primary source: AkShare's ``tool_trade_date_hist_sina`` (SSE history).
Results are cached to a parquet file so the network call happens at most
once per process unless ``refresh=True``.

For offline tests or environments without AkShare, pass an explicit
``trading_days`` iterable to the constructor.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date, datetime, time, timedelta
from pathlib import Path

import pandas as pd

# A-share continuous-trading sessions (local exchange time, Asia/Shanghai).
# Opening call auction (09:15-09:25) and closing call auction (14:57-15:00)
# are included here for simplicity; tighten if needed.
MORNING_OPEN = time(9, 30)
MORNING_CLOSE = time(11, 30)
AFTERNOON_OPEN = time(13, 0)
AFTERNOON_CLOSE = time(15, 0)


class AShareCalendar:
    def __init__(
        self,
        trading_days: Iterable[date] | None = None,
        cache_path: str | Path | None = None,
    ):
        self._cache_path = Path(cache_path) if cache_path else None
        if trading_days is not None:
            self._days: set[date] = {self._to_date(d) for d in trading_days}
        else:
            self._days = self._load()

    @staticmethod
    def _to_date(d) -> date:
        if isinstance(d, date) and not isinstance(d, datetime):
            return d
        if isinstance(d, datetime):
            return d.date()
        return pd.Timestamp(d).date()

    def _load(self) -> set[date]:
        if self._cache_path and self._cache_path.exists():
            df = pd.read_parquet(self._cache_path)
            return {self._to_date(d) for d in df["trade_date"]}

        import akshare as ak

        df = ak.tool_trade_date_hist_sina()
        df["trade_date"] = pd.to_datetime(df["trade_date"])
        if self._cache_path:
            self._cache_path.parent.mkdir(parents=True, exist_ok=True)
            df.to_parquet(self._cache_path)
        return {d.date() for d in df["trade_date"]}

    def is_trading_day(self, d: date | datetime) -> bool:
        return self._to_date(d) in self._days

    def next_trading_day(self, d: date | datetime) -> date:
        cur = self._to_date(d) + timedelta(days=1)
        while cur not in self._days:
            cur += timedelta(days=1)
            if (cur - self._to_date(d)).days > 30:
                raise RuntimeError("no trading day found within 30 days")
        return cur

    def prev_trading_day(self, d: date | datetime) -> date:
        cur = self._to_date(d) - timedelta(days=1)
        while cur not in self._days:
            cur -= timedelta(days=1)
            if (self._to_date(d) - cur).days > 30:
                raise RuntimeError("no trading day found within 30 days")
        return cur

    def trading_days_between(self, start: date, end: date) -> list[date]:
        start_d = self._to_date(start)
        end_d = self._to_date(end)
        return sorted(d for d in self._days if start_d <= d <= end_d)

    @staticmethod
    def is_session_time(t: time) -> bool:
        """True iff ``t`` falls inside an A-share continuous-trading session."""
        return (MORNING_OPEN <= t <= MORNING_CLOSE) or (
            AFTERNOON_OPEN <= t <= AFTERNOON_CLOSE
        )

    def is_trading_session(self, dt: datetime) -> bool:
        """True iff ``dt`` is a trading day AND within a session window."""
        if not self.is_trading_day(dt):
            return False
        return self.is_session_time(dt.time())
