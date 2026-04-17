"""Equity-curve performance metrics.

All functions accept a pandas Series of equity values indexed by timestamp.
Annualization uses ``periods_per_year``; when omitted it is inferred from
the median timestamp spacing (e.g. ~242 for A-share daily bars).
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

# A-share trading calendar averages ~242 sessions per year.
TRADING_DAYS_PER_YEAR = 242


def infer_periods_per_year(index: pd.DatetimeIndex) -> float:
    """Estimate annualization factor from timestamp spacing.

    For daily or lower frequency, returns ``TRADING_DAYS_PER_YEAR``. For
    intraday, returns ``TRADING_DAYS_PER_YEAR`` multiplied by the typical
    bars-per-day derived from the median bar duration.
    """
    if len(index) < 2:
        return float(TRADING_DAYS_PER_YEAR)
    # Drop duplicates (e.g. multiple symbols sharing a timestamp in the
    # equity curve) so the median reflects the true bar cadence.
    unique = pd.DatetimeIndex(index).unique()
    if len(unique) < 2:
        return float(TRADING_DAYS_PER_YEAR)
    diffs = pd.Series(unique).diff().dropna()
    # Filter out zero-length diffs for robustness.
    diffs = diffs[diffs > pd.Timedelta(0)]
    if diffs.empty:
        return float(TRADING_DAYS_PER_YEAR)
    seconds = diffs.median().total_seconds()
    if seconds <= 0 or seconds >= 24 * 3600:
        return float(TRADING_DAYS_PER_YEAR)
    # Intraday: 4 hours of continuous trading per A-share session.
    bars_per_day = max(1.0, (4 * 3600) / seconds)
    return TRADING_DAYS_PER_YEAR * bars_per_day


def _returns(equity: pd.Series) -> pd.Series:
    return equity.pct_change().dropna()


def total_return(equity: pd.Series) -> float:
    if len(equity) < 2 or equity.iloc[0] == 0:
        return 0.0
    return float(equity.iloc[-1] / equity.iloc[0] - 1)


def annualized_return(
    equity: pd.Series, periods_per_year: float | None = None
) -> float:
    if len(equity) < 2 or equity.iloc[0] <= 0:
        return 0.0
    periods_per_year = periods_per_year or infer_periods_per_year(equity.index)
    n = len(equity) - 1
    growth = equity.iloc[-1] / equity.iloc[0]
    if growth <= 0:
        return -1.0
    return float(growth ** (periods_per_year / n) - 1)


def annualized_volatility(
    equity: pd.Series, periods_per_year: float | None = None
) -> float:
    r = _returns(equity)
    if r.empty:
        return 0.0
    periods_per_year = periods_per_year or infer_periods_per_year(equity.index)
    return float(r.std(ddof=1) * math.sqrt(periods_per_year))


def sharpe_ratio(
    equity: pd.Series,
    risk_free: float = 0.0,
    periods_per_year: float | None = None,
) -> float:
    r = _returns(equity)
    if r.empty:
        return 0.0
    periods_per_year = periods_per_year or infer_periods_per_year(equity.index)
    excess = r - risk_free / periods_per_year
    std = excess.std(ddof=1)
    if std == 0 or np.isnan(std):
        return 0.0
    return float(math.sqrt(periods_per_year) * excess.mean() / std)


def sortino_ratio(
    equity: pd.Series,
    risk_free: float = 0.0,
    periods_per_year: float | None = None,
) -> float:
    r = _returns(equity)
    if r.empty:
        return 0.0
    periods_per_year = periods_per_year or infer_periods_per_year(equity.index)
    excess = r - risk_free / periods_per_year
    downside = excess[excess < 0]
    if downside.empty:
        return 0.0
    dd_std = math.sqrt((downside**2).mean())
    if dd_std == 0:
        return 0.0
    return float(math.sqrt(periods_per_year) * excess.mean() / dd_std)


def max_drawdown(equity: pd.Series) -> float:
    """Maximum drawdown as a negative number (e.g. -0.18 for -18%)."""
    if equity.empty:
        return 0.0
    peak = equity.cummax()
    # guard against zero peak at the very start
    valid = peak > 0
    if not valid.any():
        return 0.0
    dd = (equity[valid] - peak[valid]) / peak[valid]
    return float(dd.min())


def calmar_ratio(
    equity: pd.Series, periods_per_year: float | None = None
) -> float:
    mdd = abs(max_drawdown(equity))
    if mdd == 0:
        return 0.0
    return annualized_return(equity, periods_per_year) / mdd
