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
from datetime import date, timedelta
from typing import Annotated, Any

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query

from alphaagent.agent.company_analyst import AgentNotConfigured
from alphaagent.analytics.company import rolling_return
from alphaagent.analytics.company_agent import DataUnavailable
from alphaagent.api.deps import (
    get_fundamentals_provider,
    get_kline_data_source,
    get_news_provider,
    get_research_analyst,
)
from alphaagent.api.envelope import err, ok
from alphaagent.api.schemas.analysis import (
    CompanyOverviewDTO,
    FinancialIndicatorsDTO,
    KLinePoint,
    ReportSectionDTO,
    ResearchReportDTO,
    SecurityInfoDTO,
    SourceDTO,
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


def _report_to_dto(report: Any) -> ResearchReportDTO:
    return ResearchReportDTO(
        symbol=report.symbol,
        generated_at=report.generated_at,
        rating=report.rating,
        confidence=report.confidence,
        sections=[ReportSectionDTO(title=s.title, body=s.body) for s in report.sections],
        sources=[SourceDTO(id=s.id, type=s.type, label=s.label, detail=s.detail) for s in report.sources],
        disclaimer=report.disclaimer,
        data_complete=report.data_complete,
        notes=list(report.notes),
    )


def _persist_report(db, analysis_id: str, report: Any, model: str) -> None:
    summary = report.sections[0].body[:200] if report.sections else report.rating
    report_dict = {
        "symbol": report.symbol,
        "generated_at": report.generated_at,
        "rating": report.rating,
        "confidence": report.confidence,
        "sections": [{"title": s.title, "body": s.body} for s in report.sections],
        "sources": [{"id": s.id, "type": s.type, "label": s.label, "detail": s.detail} for s in report.sources],
        "disclaimer": report.disclaimer,
        "data_complete": report.data_complete,
        "notes": list(report.notes),
        "model": model,
    }
    db.execute(
        "INSERT OR REPLACE INTO company_analysis "
        "(id,symbol,generated_at,rating,confidence,summary,reasons_json,risks_json,model,context_json,report_json) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (
            analysis_id, report.symbol, report.generated_at, report.rating, report.confidence,
            summary, "[]", "[]", model, "{}",
            json.dumps(report_dict, ensure_ascii=False),
        ),
    )


@router.post("/{symbol}/agent")
def company_agent_analysis(
    symbol: str,
    provider: Annotated[FundamentalsProvider, Depends(get_fundamentals_provider)],
    upstream: Annotated[DataSource, Depends(get_kline_data_source)],
    news_provider: Annotated[Any, Depends(get_news_provider)],
    analyst: Annotated[Any, Depends(get_research_analyst)],
):
    db = get_database()
    bar_source = SqliteBarCache(upstream, db, "akshare_1d_qfq")
    try:
        report = analyst.analyze(symbol, bar_source=bar_source, provider=provider,
                                 news_provider=news_provider, db=db)
    except AgentNotConfigured as e:
        raise HTTPException(400, detail=err("AGENT_NOT_CONFIGURED", str(e))) from e
    except DataUnavailable as e:
        raise HTTPException(502, detail=err("DATA_UNAVAILABLE", str(e))) from e
    except Exception as e:
        raise HTTPException(502, detail=err("AGENT_FAILED", f"{type(e).__name__}: {e}")) from e
    dto = _report_to_dto(report)
    _persist_report(db, str(uuid.uuid4()), report, analyst.model if hasattr(analyst, "model") else "")
    return ok(dto.model_dump(mode="json"))


@router.get("/{symbol}/agent/history")
def company_agent_history(symbol: str, limit: int = 10):
    db = get_database()
    rows = db.query(
        "SELECT * FROM company_analysis WHERE symbol=? ORDER BY generated_at DESC LIMIT ?",
        (symbol, limit),
    )
    out = []
    for r in rows:
        row_dict: dict[str, Any] = {
            "symbol": r["symbol"],
            "generated_at": r["generated_at"],
            "rating": r["rating"],
            "confidence": r["confidence"],
            "report": json.loads(r["report_json"]) if r["report_json"] else None,
        }
        out.append(row_dict)
    return ok(out)
