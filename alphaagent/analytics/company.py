"""Company-level analytics on OHLCV + fundamentals."""

from __future__ import annotations

import pandas as pd


def pe_percentile(pe_history: pd.Series, current_pe: float) -> float:
    """Return the percentile rank of ``current_pe`` within historical values.

    Result in [0, 100]. NaNs are dropped. If the series is empty, returns 50.
    """
    clean = pe_history.dropna().astype(float)
    if clean.empty:
        return 50.0
    return float((clean <= current_pe).mean() * 100.0)


def rolling_return(closes: pd.Series, windows: list[int]) -> dict[str, float]:
    """Return cumulative return over each lookback window (in bars).

    e.g. ``rolling_return(closes, [5, 20, 60])`` → {"5d": 0.03, ...}.
    """
    out: dict[str, float] = {}
    series = closes.dropna().astype(float)
    if series.empty:
        return out
    last = float(series.iloc[-1])
    for n in windows:
        if len(series) > n:
            past = float(series.iloc[-n - 1])
            if past > 0:
                out[f"{n}d"] = last / past - 1.0
    return out


def drawdown_curve(closes: pd.Series) -> pd.Series:
    """Underwater plot: percentage drawdown from running peak at each bar."""
    s = closes.dropna().astype(float)
    peak = s.cummax()
    return (s - peak) / peak
