"""APScheduler wrapper for automating daily runs during A-share hours.

A-share sessions: 09:30-11:30, 13:00-15:00 CST, Monday-Friday (excluding
holidays - caller responsible for calendar).
"""

from __future__ import annotations

from collections.abc import Callable

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger


class TradingScheduler:
    def __init__(self, timezone: str = "Asia/Shanghai"):
        self.scheduler = BlockingScheduler(timezone=timezone)

    def add_pre_market(self, func: Callable[[], None], hour: int = 9, minute: int = 15) -> None:
        self.scheduler.add_job(
            func,
            CronTrigger(day_of_week="mon-fri", hour=hour, minute=minute),
            name="pre_market",
        )

    def add_session_tick(
        self, func: Callable[[], None], every_minutes: int = 5
    ) -> None:
        # Morning session
        self.scheduler.add_job(
            func,
            CronTrigger(day_of_week="mon-fri", hour="9-11", minute=f"*/{every_minutes}"),
            name="morning_tick",
        )
        # Afternoon session
        self.scheduler.add_job(
            func,
            CronTrigger(day_of_week="mon-fri", hour="13-14", minute=f"*/{every_minutes}"),
            name="afternoon_tick",
        )

    def add_post_market(
        self, func: Callable[[], None], hour: int = 15, minute: int = 30
    ) -> None:
        self.scheduler.add_job(
            func,
            CronTrigger(day_of_week="mon-fri", hour=hour, minute=minute),
            name="post_market",
        )

    def start(self) -> None:
        self.scheduler.start()

    def shutdown(self) -> None:
        self.scheduler.shutdown()
