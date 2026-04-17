from datetime import datetime

import pandas as pd
import pytest

from alphaagent.metrics.returns import (
    annualized_return,
    annualized_volatility,
    calmar_ratio,
    infer_periods_per_year,
    max_drawdown,
    sharpe_ratio,
    sortino_ratio,
    total_return,
)


def _series(values, freq="B", start="2023-01-02"):
    idx = pd.date_range(start, periods=len(values), freq=freq)
    return pd.Series(values, index=idx, dtype=float)


def test_total_return():
    s = _series([100, 110, 121])
    assert total_return(s) == pytest.approx(0.21)


def test_total_return_flat():
    s = _series([100, 100, 100])
    assert total_return(s) == 0.0


def test_max_drawdown():
    s = _series([100, 120, 90, 110])
    # Peak 120 -> trough 90 => -25%.
    assert max_drawdown(s) == pytest.approx(-0.25)


def test_max_drawdown_monotone_up_is_zero():
    s = _series([100, 110, 120, 130])
    assert max_drawdown(s) == 0.0


def test_annualized_return_daily():
    # 1% gain over 242 daily bars ~ 1% annualized.
    s = _series([100] + [100] * 240 + [101])
    ann = annualized_return(s)
    assert ann == pytest.approx(0.01, rel=0.05)


def test_sharpe_constant_returns_is_zero():
    # No variance => Sharpe undefined => we return 0.
    s = _series([100, 100, 100, 100])
    assert sharpe_ratio(s) == 0.0


def test_sharpe_positive_for_growing_series():
    s = _series([100 + i for i in range(250)])
    assert sharpe_ratio(s) > 0


def test_sortino_ignores_upside_volatility():
    # No negative returns => Sortino returns 0 by our convention.
    s = _series([100, 101, 102, 103])
    assert sortino_ratio(s) == 0.0


def test_calmar_is_ann_return_over_abs_mdd():
    s = _series([100, 120, 90, 110, 115])
    mdd = abs(max_drawdown(s))
    ann = annualized_return(s)
    expected = ann / mdd if mdd else 0.0
    assert calmar_ratio(s) == pytest.approx(expected)


def test_annualized_volatility_non_negative():
    s = _series([100, 99, 101, 100, 102, 98])
    assert annualized_volatility(s) >= 0


def test_infer_periods_per_year_daily_vs_minute():
    daily_idx = pd.date_range("2023-01-02", periods=30, freq="B")
    minute_idx = pd.DatetimeIndex(
        [datetime(2024, 1, 2, 9, 30) + pd.Timedelta(minutes=i) for i in range(30)]
    )
    assert infer_periods_per_year(daily_idx) == pytest.approx(242.0)
    # Minute data should give far more periods per year than daily.
    assert infer_periods_per_year(minute_idx) > 242 * 100
