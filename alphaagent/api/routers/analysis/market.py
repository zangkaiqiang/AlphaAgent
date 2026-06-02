"""Market dashboard endpoint."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from alphaagent.analytics.market import format_breadth
from alphaagent.api.deps import get_fundamentals_provider
from alphaagent.api.envelope import err, ok
from alphaagent.api.schemas.analysis import (
    MarketIndexDTO,
    MarketSnapshotDTO,
)
from alphaagent.fundamentals.base import FundamentalsProvider

router = APIRouter()


@router.get("/snapshot")
def get_snapshot(
    provider: Annotated[FundamentalsProvider, Depends(get_fundamentals_provider)],
):
    try:
        snap = provider.market_snapshot()
    except Exception as e:
        raise HTTPException(502, detail=err("DATA_FETCH_FAILED", str(e))) from e

    indices = [
        MarketIndexDTO(
            code=i.code,
            name=i.name,
            last=i.last,
            change_pct=i.change_pct,
            volume=i.volume,
            amount=i.amount,
        )
        for i in snap.indices
    ]
    breadth_payload = format_breadth(snap.breadth)
    dto = MarketSnapshotDTO.model_validate(
        {
            "indices": [m.model_dump() for m in indices],
            "breadth": breadth_payload,
            "northbound_net": snap.northbound_net,
        }
    )
    return ok(dto.model_dump(mode="json"))
