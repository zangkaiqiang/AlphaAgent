"""Analysis-module response DTOs."""

from datetime import date

from pydantic import BaseModel


class SecurityInfoDTO(BaseModel):
    symbol: str
    name: str
    industry: str | None = None
    market_cap: float | None = None
    float_market_cap: float | None = None
    pe: float | None = None
    pb: float | None = None
    listed_date: date | None = None


class FinancialIndicatorsDTO(BaseModel):
    period: str
    roe: float | None = None
    net_margin: float | None = None
    gross_margin: float | None = None
    revenue: float | None = None
    revenue_yoy: float | None = None
    net_income: float | None = None
    net_income_yoy: float | None = None
    debt_ratio: float | None = None


class KLinePoint(BaseModel):
    timestamp: date
    open: float
    high: float
    low: float
    close: float
    volume: float


class CompanyOverviewDTO(BaseModel):
    info: SecurityInfoDTO
    financials: list[FinancialIndicatorsDTO]
    kline: list[KLinePoint]
    returns: dict[str, float]  # {"5d": 0.03, "20d": 0.08, ...}


class IndustrySummaryDTO(BaseModel):
    code: str
    name: str
    change_pct: float | None = None
    avg_pe: float | None = None
    constituent_count: int | None = None
    money_flow_net: float | None = None


class IndustryConstituentDTO(BaseModel):
    symbol: str
    name: str
    change_pct: float | None = None
    market_cap: float | None = None
    pe: float | None = None


class IndustryDetailDTO(BaseModel):
    industry: IndustrySummaryDTO
    constituents: list[IndustryConstituentDTO]


class MarketIndexDTO(BaseModel):
    code: str
    name: str
    last: float
    change_pct: float
    volume: float | None = None
    amount: float | None = None


class MarketBreadthDTO(BaseModel):
    as_of: date | None = None
    advancers: int | None = None
    decliners: int | None = None
    unchanged: int | None = None
    limit_up: int | None = None
    limit_down: int | None = None
    advance_decline_ratio: float | None = None


class MarketSnapshotDTO(BaseModel):
    indices: list[MarketIndexDTO]
    breadth: MarketBreadthDTO
    northbound_net: float | None = None


class CompanyAnalysisDTO(BaseModel):
    symbol: str
    generated_at: str
    rating: str
    confidence: float | None = None
    summary: str
    reasons: list[str]
    risks: list[str]
    model: str
    disclaimer: str
    data_complete: bool | None = None
