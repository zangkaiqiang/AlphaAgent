from datetime import date

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
