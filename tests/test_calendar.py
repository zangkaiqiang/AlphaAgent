from datetime import date, datetime, time

import pytest

from alphaagent.calendar import AShareCalendar


@pytest.fixture
def cal():
    # Mon-Fri 2024-01-01 .. 2024-01-19, excluding 2024-01-01 (New Year).
    days = [
        date(2024, 1, 2), date(2024, 1, 3), date(2024, 1, 4), date(2024, 1, 5),
        date(2024, 1, 8), date(2024, 1, 9), date(2024, 1, 10), date(2024, 1, 11),
        date(2024, 1, 12), date(2024, 1, 15), date(2024, 1, 16), date(2024, 1, 17),
        date(2024, 1, 18), date(2024, 1, 19),
    ]
    return AShareCalendar(trading_days=days)


def test_is_trading_day(cal):
    assert cal.is_trading_day(date(2024, 1, 2))
    assert not cal.is_trading_day(date(2024, 1, 1))  # holiday
    assert not cal.is_trading_day(date(2024, 1, 6))  # weekend


def test_next_and_prev(cal):
    assert cal.next_trading_day(date(2024, 1, 5)) == date(2024, 1, 8)  # skip weekend
    assert cal.prev_trading_day(date(2024, 1, 8)) == date(2024, 1, 5)


def test_trading_days_between(cal):
    days = cal.trading_days_between(date(2024, 1, 2), date(2024, 1, 5))
    assert days == [date(2024, 1, 2), date(2024, 1, 3), date(2024, 1, 4), date(2024, 1, 5)]


def test_is_session_time():
    assert AShareCalendar.is_session_time(time(9, 30))
    assert AShareCalendar.is_session_time(time(11, 30))
    assert AShareCalendar.is_session_time(time(13, 0))
    assert AShareCalendar.is_session_time(time(15, 0))
    # lunch break
    assert not AShareCalendar.is_session_time(time(12, 0))
    # pre-market
    assert not AShareCalendar.is_session_time(time(9, 0))
    # after close
    assert not AShareCalendar.is_session_time(time(15, 30))


def test_is_trading_session_combines_date_and_time(cal):
    # Trading day within session window.
    assert cal.is_trading_session(datetime(2024, 1, 2, 10, 0))
    # Trading day but lunch break.
    assert not cal.is_trading_session(datetime(2024, 1, 2, 12, 0))
    # Non-trading day, regardless of time.
    assert not cal.is_trading_session(datetime(2024, 1, 6, 10, 0))


def test_calendar_db_roundtrip(tmp_path):
    from datetime import date

    from alphaagent.storage.db import Database

    db = Database(str(tmp_path / "t.db"))
    db.executemany(
        "INSERT OR REPLACE INTO trade_calendar (dt) VALUES (?)",
        [("2024-01-02",), ("2024-01-03",)],
    )
    cal = AShareCalendar(db=db)
    assert cal.is_trading_day(date(2024, 1, 2))
    assert cal.is_trading_day(date(2024, 1, 3))
    assert not cal.is_trading_day(date(2024, 1, 4))
