"""Industry-analysis endpoints.

GET /api/analysis/industry                  → ranked industry list
GET /api/analysis/industry/{code}           → industry + constituents
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from alphaagent.analytics.industry import rank_by_change
from alphaagent.api.deps import get_fundamentals_provider
from alphaagent.api.envelope import err, ok
from alphaagent.api.schemas.analysis import (
    IndustryConstituentDTO,
    IndustryDetailDTO,
    IndustrySummaryDTO,
)
from alphaagent.fundamentals.base import FundamentalsProvider
from alphaagent.fundamentals.types import IndustryConstituent, IndustrySummary

router = APIRouter()


def _ind_dto(i: IndustrySummary) -> IndustrySummaryDTO:
    return IndustrySummaryDTO(
        code=i.code,
        name=i.name,
        change_pct=i.change_pct,
        avg_pe=i.avg_pe,
        constituent_count=i.constituent_count,
        money_flow_net=i.money_flow_net,
    )


def _con_dto(c: IndustryConstituent) -> IndustryConstituentDTO:
    return IndustryConstituentDTO(
        symbol=c.symbol,
        name=c.name,
        change_pct=c.change_pct,
        market_cap=c.market_cap,
        pe=c.pe,
    )


@router.get("")
def list_industries(
    provider: Annotated[FundamentalsProvider, Depends(get_fundamentals_provider)],
    sort: str = Query("change", description="change | inflow"),
    descending: bool = Query(True),
):
    try:
        items = provider.industry_list()
    except Exception as e:
        raise HTTPException(502, detail=err("DATA_FETCH_FAILED", str(e))) from e

    if sort == "inflow":
        items = sorted(
            items,
            key=lambda x: (x.money_flow_net is None, -(x.money_flow_net or 0) if descending else (x.money_flow_net or 0)),
        )
    else:
        items = rank_by_change(items, descending=descending)
    return ok([_ind_dto(i).model_dump(mode="json") for i in items])


@router.get("/{code}")
def get_industry_detail(
    code: str,
    provider: Annotated[FundamentalsProvider, Depends(get_fundamentals_provider)],
):
    try:
        industries = provider.industry_list()
        match = next((i for i in industries if i.code == code or i.name == code), None)
        if match is None:
            raise HTTPException(404, detail=err("INDUSTRY_NOT_FOUND", code))
        constituents = provider.industry_constituents(match.code)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(502, detail=err("DATA_FETCH_FAILED", str(e))) from e

    dto = IndustryDetailDTO(
        industry=_ind_dto(match),
        constituents=[_con_dto(c) for c in constituents],
    )
    return ok(dto.model_dump(mode="json"))
