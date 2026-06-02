"""Backtest-related schemas."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class BacktestSubmitRequest(BaseModel):
    """Submit a backtest. ``config`` is an AppConfig dict (same shape as YAML)."""

    config: dict[str, Any] = Field(..., description="AppConfig as JSON dict")
    label: str | None = Field(None, description="Optional human-friendly name")


class JobInfo(BaseModel):
    id: str
    label: str | None = None
    status: JobStatus
    progress: float = 0.0  # 0..1
    bars_processed: int = 0
    bars_total: int = 0
    fill_count: int = 0
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error: str | None = None


class EquityPoint(BaseModel):
    timestamp: datetime
    equity: float


class FillDTO(BaseModel):
    timestamp: datetime
    symbol: str
    side: str
    quantity: int
    fill_price: float
    commission: float
    stamp_tax: float
    order_id: str
    strategy_id: str


class PerformanceDTO(BaseModel):
    total_return: float
    annualized_return: float
    annualized_volatility: float
    sharpe: float
    sortino: float
    max_drawdown: float
    calmar: float
    trades: int
    win_rate: float
    avg_win: float
    avg_loss: float
    profit_factor: float
    total_pnl: float


class BacktestResultDTO(BaseModel):
    initial_cash: float
    final_equity: float
    total_return: float
    bars_processed: int
    bars_skipped: int
    fill_count: int
    cancelled: bool
    equity_curve: list[EquityPoint]
    fills: list[FillDTO]
    performance: PerformanceDTO
    performance_by_strategy: dict[str, PerformanceDTO] = Field(default_factory=dict)
    equity_by_strategy: dict[str, list[EquityPoint]] = Field(default_factory=dict)
