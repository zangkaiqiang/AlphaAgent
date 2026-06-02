"""Domain types returned by FundamentalsProvider.

Plain dataclasses (not pydantic) so they can flow freely through the
domain layer; the API DTOs in alphaagent/api/schemas convert when needed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass(frozen=True, slots=True)
class SecurityInfo:
    symbol: str           # 6-digit code
    name: str
    industry: str | None = None
    market_cap: float | None = None       # 总市值 (元)
    float_market_cap: float | None = None  # 流通市值 (元)
    pe: float | None = None
    pb: float | None = None
    listed_date: date | None = None


@dataclass(frozen=True, slots=True)
class FinancialIndicators:
    """Snapshot or trailing-period summary of key financial metrics."""

    symbol: str
    period: str   # e.g. "2024Q3"
    roe: float | None = None
    roa: float | None = None
    gross_margin: float | None = None
    net_margin: float | None = None
    revenue: float | None = None
    revenue_yoy: float | None = None
    net_income: float | None = None
    net_income_yoy: float | None = None
    debt_ratio: float | None = None


@dataclass(frozen=True, slots=True)
class IndustrySummary:
    code: str        # industry board code
    name: str        # 板块名称
    change_pct: float | None = None        # 当日涨跌幅
    avg_pe: float | None = None
    constituent_count: int | None = None
    money_flow_net: float | None = None    # 主力净流入 (元)


@dataclass(frozen=True, slots=True)
class IndustryConstituent:
    symbol: str
    name: str
    change_pct: float | None = None
    market_cap: float | None = None
    pe: float | None = None


@dataclass(frozen=True, slots=True)
class MarketIndex:
    code: str        # e.g. "000001" (上证指数), "399001" (深证)
    name: str
    last: float
    change_pct: float
    volume: float | None = None
    amount: float | None = None


@dataclass(frozen=True, slots=True)
class MoneyFlow:
    """Daily aggregate inflow/outflow buckets."""

    date: date
    main_net: float       # 主力净流入
    super_net: float      # 超大单
    large_net: float      # 大单
    medium_net: float
    small_net: float


@dataclass(frozen=True, slots=True)
class MarketBreadth:
    date: date
    advancers: int
    decliners: int
    unchanged: int
    limit_up: int = 0
    limit_down: int = 0

    @property
    def advance_decline_ratio(self) -> float:
        return self.advancers / max(1, self.decliners)


@dataclass(frozen=True, slots=True)
class MarketSnapshot:
    """One-shot dashboard data for the 大盘 page."""

    indices: list[MarketIndex] = field(default_factory=list)
    breadth: MarketBreadth | None = None
    northbound_net: float | None = None      # 北向资金当日净流入
