"""Assemble a lightweight, persisted company context for the LLM analyst.

Pulls only per-symbol small requests (daily bars + financial abstract) — never
the 90-field eastmoney quote that chokes the user's proxy. Fetched financials
are persisted to SQLite; on a fetch failure we fall back to the last persisted
copy so analysis still works when the network is flaky.
"""

from __future__ import annotations

import contextlib
from datetime import UTC, date, datetime, timedelta
from typing import Any

import numpy as np
import pandas as pd

from alphaagent.analytics.company import drawdown_curve, rolling_return
from alphaagent.data.base import DataSource
from alphaagent.fundamentals.base import FundamentalsProvider
from alphaagent.fundamentals.types import FinancialIndicators
from alphaagent.storage.db import Database

_RETURN_WINDOWS = [5, 20, 60, 120, 250]


class DataUnavailable(RuntimeError):
    """Neither bars nor financials could be obtained for the symbol."""


def _f(x) -> float | None:
    if x is None:
        return None
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return round(v, 6) if v == v else None


def persist_financials(db: Database, symbol: str, items: list[FinancialIndicators]) -> None:
    now = datetime.now(UTC).isoformat()
    rows = [
        (
            symbol, it.period, _f(it.roe), _f(it.net_margin), _f(it.gross_margin),
            _f(it.revenue), _f(it.revenue_yoy), _f(it.net_income), _f(it.net_income_yoy),
            _f(it.debt_ratio), now,
        )
        for it in items
    ]
    if rows:
        db.executemany(
            "INSERT OR REPLACE INTO financials "
            "(symbol,period,roe,net_margin,gross_margin,revenue,revenue_yoy,"
            "net_income,net_income_yoy,debt_ratio,fetched_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            rows,
        )


def load_persisted_financials(db: Database, symbol: str) -> list[FinancialIndicators]:
    rows = db.query("SELECT * FROM financials WHERE symbol=? ORDER BY period", (symbol,))
    return [
        FinancialIndicators(
            symbol=symbol, period=r["period"], roe=r["roe"], net_margin=r["net_margin"],
            gross_margin=r["gross_margin"], revenue=r["revenue"], revenue_yoy=r["revenue_yoy"],
            net_income=r["net_income"], net_income_yoy=r["net_income_yoy"], debt_ratio=r["debt_ratio"],
        )
        for r in rows
    ]


def _technical_features(bars: pd.DataFrame) -> dict[str, Any]:
    closes = bars["close"].astype(float)
    dd = drawdown_curve(closes)
    daily = closes.pct_change().dropna()
    vol = float(daily.std() * np.sqrt(252)) if len(daily) > 1 else None
    last = float(closes.iloc[-1])
    ma20 = float(closes.rolling(20).mean().iloc[-1]) if len(closes) >= 20 else None
    ma60 = float(closes.rolling(60).mean().iloc[-1]) if len(closes) >= 60 else None
    return {
        "last_price": round(last, 4),
        "returns": {k: round(v, 6) for k, v in rolling_return(closes, _RETURN_WINDOWS).items()},
        "current_drawdown": round(float(dd.iloc[-1]), 6),
        "max_drawdown": round(float(dd.min()), 6),
        "annualized_volatility": round(vol, 6) if vol is not None else None,
        "above_ma20": (last > ma20) if ma20 is not None else None,
        "above_ma60": (last > ma60) if ma60 is not None else None,
    }


def _fin_to_dict(it: FinancialIndicators) -> dict[str, Any]:
    return {
        "period": it.period, "roe": _f(it.roe), "net_margin": _f(it.net_margin),
        "gross_margin": _f(it.gross_margin), "revenue": _f(it.revenue),
        "revenue_yoy": _f(it.revenue_yoy), "net_income": _f(it.net_income),
        "net_income_yoy": _f(it.net_income_yoy), "debt_ratio": _f(it.debt_ratio),
    }


def assemble_company_context(
    symbol: str,
    bar_source: DataSource,
    provider: FundamentalsProvider,
    db: Database,
    *,
    lookback_days: int = 400,
    periods: int = 4,
) -> dict[str, Any]:
    end = date.today()
    start = end - timedelta(days=lookback_days)
    try:
        bars = bar_source.get_bars(symbol, start, end, freq="1d")
    except Exception:
        bars = pd.DataFrame()

    data_complete = True
    try:
        items = provider.financial_indicators(symbol)
    except Exception:
        items = []
    if items:
        # Persist separately so a DB-write failure never discards fresh data.
        with contextlib.suppress(Exception):
            persist_financials(db, symbol, items)
    else:
        # Fetch failed or returned nothing → fall back to the last persisted copy.
        items = load_persisted_financials(db, symbol)
        data_complete = False

    has_bars = bars is not None and not bars.empty
    if not has_bars and not items:
        raise DataUnavailable(f"no bars or financials for {symbol}")

    technical = _technical_features(bars) if has_bars else None
    return {
        "symbol": symbol,
        "technical": technical,
        "financials": [_fin_to_dict(it) for it in items[-periods:]],
        "data_complete": data_complete and has_bars,
    }
