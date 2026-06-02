"""Screener-related API schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel

from alphaagent.api.schemas.backtest import JobStatus


class ScreenSubmitRequest(BaseModel):
    """Submit a screener job. ``config`` is a ScreenAppConfig dict."""

    config: dict[str, Any]
    label: str | None = None


class ScreenJobInfo(BaseModel):
    id: str
    label: str | None = None
    status: JobStatus
    progress: float = 0.0
    picks_count: int = 0
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error: str | None = None


class ReasonDTO(BaseModel):
    rule_name: str
    score: float
    detail: dict[str, Any]


class PickDTO(BaseModel):
    symbol: str
    name: str | None = None
    final_score: float
    reasons: list[ReasonDTO]
    metadata: dict[str, Any]


class ScreenResultDTO(BaseModel):
    generated_at: str       # isoformat date string
    resolved_as_of: str     # isoformat date string
    universe_name: str
    universe_size: int
    filtered_size: int
    rules_applied: list[str]
    symbols: list[str]      # top_n symbols from picks, ordered by score
    picks: list[PickDTO]
