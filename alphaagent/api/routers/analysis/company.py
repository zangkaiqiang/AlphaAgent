"""Company-analysis endpoints.

GET /api/analysis/company/{symbol}
    → SecurityInfo + recent financials + K-line + rolling returns
GET /api/analysis/company/{symbol}/kline?freq=1d&days=180
    → just the K-line (cheap)
GET /api/analysis/company/{symbol}/financials
    → trailing financial indicators
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, date, datetime, timedelta
from typing import Annotated, Any

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse

from alphaagent.agent.company_analyst import AgentNotConfigured, CompanyAnalysis
from alphaagent.analytics.company import rolling_return
from alphaagent.analytics.company_agent import DataUnavailable, assemble_company_context
from alphaagent.api.deps import (
    get_company_analyst,
    get_fundamentals_provider,
    get_kline_data_source,
)
from alphaagent.api.envelope import err, ok
from alphaagent.api.schemas.analysis import (
    CompanyAnalysisDTO,
    CompanyOverviewDTO,
    FinancialIndicatorsDTO,
    KLinePoint,
    SecurityInfoDTO,
)
from alphaagent.data.base import DataSource
from alphaagent.data.sqlite_cache import SqliteBarCache
from alphaagent.fundamentals.base import FundamentalsProvider
from alphaagent.fundamentals.types import FinancialIndicators, SecurityInfo
from alphaagent.storage.db import get_database

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


def _persist_analysis(db, analysis_id, symbol, generated_at, a: CompanyAnalysis, context) -> None:
    db.execute(
        "INSERT OR REPLACE INTO company_analysis "
        "(id,symbol,generated_at,rating,confidence,summary,reasons_json,risks_json,model,context_json) "
        "VALUES (?,?,?,?,?,?,?,?,?,?)",
        (
            analysis_id, symbol, generated_at, a.rating, a.confidence, a.summary,
            json.dumps(a.reasons, ensure_ascii=False), json.dumps(a.risks, ensure_ascii=False),
            a.model, json.dumps(context, ensure_ascii=False),
        ),
    )


@router.post("/{symbol}/agent")
def company_agent_analysis(
    symbol: str,
    provider: Annotated[FundamentalsProvider, Depends(get_fundamentals_provider)],
    upstream: Annotated[DataSource, Depends(get_kline_data_source)],
    analyst: Annotated[Any, Depends(get_company_analyst)],
):
    db = get_database()
    bar_source = SqliteBarCache(upstream, db, "akshare_1d_qfq")
    try:
        context = assemble_company_context(symbol, bar_source, provider, db)
    except DataUnavailable as e:
        return JSONResponse(status_code=502, content=err("DATA_UNAVAILABLE", str(e)))
    try:
        analysis = analyst.analyze(context)
    except AgentNotConfigured as e:
        return JSONResponse(status_code=400, content=err("AGENT_NOT_CONFIGURED", str(e)))
    except Exception as e:  # noqa: BLE001
        return JSONResponse(status_code=502, content=err("AGENT_FAILED", f"{type(e).__name__}: {e}"))

    generated_at = datetime.now(UTC).isoformat()
    _persist_analysis(db, str(uuid.uuid4()), symbol, generated_at, analysis, context)
    return ok(
        CompanyAnalysisDTO(
            symbol=symbol, generated_at=generated_at, rating=analysis.rating,
            confidence=analysis.confidence, summary=analysis.summary, reasons=analysis.reasons,
            risks=analysis.risks, model=analysis.model, disclaimer=analysis.disclaimer,
            data_complete=context.get("data_complete"),
        ).model_dump(mode="json")
    )


@router.get("/{symbol}/agent/history")
def company_agent_history(symbol: str, limit: int = 10):
    db = get_database()
    rows = db.query(
        "SELECT * FROM company_analysis WHERE symbol=? ORDER BY generated_at DESC LIMIT ?",
        (symbol, limit),
    )
    out = [
        CompanyAnalysisDTO(
            symbol=r["symbol"], generated_at=r["generated_at"], rating=r["rating"],
            confidence=r["confidence"], summary=r["summary"] or "",
            reasons=json.loads(r["reasons_json"] or "[]"), risks=json.loads(r["risks_json"] or "[]"),
            model=r["model"] or "", disclaimer="",
        ).model_dump(mode="json")
        for r in rows
    ]
    return ok(out)
