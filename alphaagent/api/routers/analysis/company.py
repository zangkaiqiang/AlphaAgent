"""Company-analysis endpoints.

GET /api/analysis/company/{symbol}
    → SecurityInfo + recent financials + K-line + rolling returns
GET /api/analysis/company/{symbol}/kline?freq=1d&days=180
    → just the K-line (cheap)
GET /api/analysis/company/{symbol}/financials
    → trailing financial indicators
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Annotated

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query

from alphaagent.analytics.company import rolling_return
from alphaagent.api.deps import get_fundamentals_provider, get_kline_data_source
from alphaagent.api.envelope import err, ok
from alphaagent.api.schemas.analysis import (
    CompanyOverviewDTO,
    FinancialIndicatorsDTO,
    KLinePoint,
    SecurityInfoDTO,
)
from alphaagent.data.base import DataSource
from alphaagent.fundamentals.base import FundamentalsProvider
from alphaagent.fundamentals.types import FinancialIndicators, SecurityInfo

router = APIRouter()

ROLLING_WINDOWS = [5, 20, 60, 120, 250]


def _info_dto(info: SecurityInfo) -> SecurityInfoDTO:
    return SecurityInfoDTO(
        symbol=info.symbol,
        name=info.name,
        industry=info.industry,
        market_cap=info.market_cap,
        float_market_cap=info.float_market_cap,
        pe=info.pe,
        pb=info.pb,
        listed_date=info.listed_date,
    )


def _fin_dto(f: FinancialIndicators) -> FinancialIndicatorsDTO:
    return FinancialIndicatorsDTO(
        period=f.period,
        roe=f.roe,
        net_margin=f.net_margin,
        gross_margin=f.gross_margin,
        revenue=f.revenue,
        revenue_yoy=f.revenue_yoy,
        net_income=f.net_income,
        net_income_yoy=f.net_income_yoy,
        debt_ratio=f.debt_ratio,
    )


def _kline_from_df(df: pd.DataFrame) -> list[KLinePoint]:
    if df is None or df.empty:
        return []
    out: list[KLinePoint] = []
    for ts, row in df.iterrows():
        out.append(
            KLinePoint(
                timestamp=pd.Timestamp(ts).date(),
                open=float(row["open"]),
                high=float(row["high"]),
                low=float(row["low"]),
                close=float(row["close"]),
                volume=float(row["volume"]),
            )
        )
    return out


@router.get("/{symbol}/kline")
def get_kline(
    symbol: str,
    source: Annotated[DataSource, Depends(get_kline_data_source)],
    freq: str = Query("1d"),
    days: int = Query(180, ge=10, le=2000),
):
    end = date.today()
    start = end - timedelta(days=days * 2)  # widen to account for weekends/holidays
    try:
        df = source.get_bars(symbol, start, end, freq=freq)
    except Exception as e:
        raise HTTPException(502, detail=err("DATA_FETCH_FAILED", str(e))) from e
    return ok([p.model_dump(mode="json") for p in _kline_from_df(df)])


@router.get("/{symbol}/financials")
def get_financials(
    symbol: str,
    provider: Annotated[FundamentalsProvider, Depends(get_fundamentals_provider)],
):
    try:
        items = provider.financial_indicators(symbol)
    except Exception as e:
        raise HTTPException(502, detail=err("DATA_FETCH_FAILED", str(e))) from e
    return ok([_fin_dto(f).model_dump(mode="json") for f in items])


@router.get("/{symbol}")
def get_overview(
    symbol: str,
    provider: Annotated[FundamentalsProvider, Depends(get_fundamentals_provider)],
    source: Annotated[DataSource, Depends(get_kline_data_source)],
    days: int = Query(250, ge=30, le=2000),
):
    try:
        info = provider.security_info(symbol)
        fins = provider.financial_indicators(symbol)
    except KeyError as e:
        raise HTTPException(404, detail=err("SYMBOL_NOT_FOUND", str(e))) from e
    except Exception as e:
        raise HTTPException(502, detail=err("DATA_FETCH_FAILED", str(e))) from e

    end = date.today()
    start = end - timedelta(days=days * 2)
    df = source.get_bars(symbol, start, end, freq="1d")
    kline = _kline_from_df(df)
    closes = pd.Series([p.close for p in kline])
    returns = rolling_return(closes, ROLLING_WINDOWS)

    overview = CompanyOverviewDTO(
        info=_info_dto(info),
        financials=[_fin_dto(f) for f in fins],
        kline=kline,
        returns=returns,
    )
    return ok(overview.model_dump(mode="json"))
