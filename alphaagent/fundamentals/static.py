"""In-memory FundamentalsProvider for tests and offline demos.

Construct with whatever subset of data you need; missing entries raise
``KeyError`` from the corresponding method.
"""

from __future__ import annotations

from datetime import date

from alphaagent.fundamentals.base import FundamentalsProvider
from alphaagent.fundamentals.types import (
    FinancialIndicators,
    IndustryConstituent,
    IndustrySummary,
    MarketSnapshot,
    MoneyFlow,
    SecurityInfo,
)


class StaticFundamentalsProvider(FundamentalsProvider):
    def __init__(
        self,
        securities: dict[str, SecurityInfo] | None = None,
        financials: dict[str, list[FinancialIndicators]] | None = None,
        industries: list[IndustrySummary] | None = None,
        industry_members: dict[str, list[IndustryConstituent]] | None = None,
        snapshot: MarketSnapshot | None = None,
        money_flow: dict[str, list[MoneyFlow]] | None = None,
    ):
        self._securities = securities or {}
        self._financials = financials or {}
        self._industries = industries or []
        self._industry_members = industry_members or {}
        self._snapshot = snapshot or MarketSnapshot()
        self._money_flow = money_flow or {}

    def security_info(self, symbol: str) -> SecurityInfo:
        return self._securities[symbol]

    def financial_indicators(self, symbol: str) -> list[FinancialIndicators]:
        return list(self._financials.get(symbol, []))

    def money_flow(self, symbol: str, start: date, end: date) -> list[MoneyFlow]:
        return [m for m in self._money_flow.get(symbol, []) if start <= m.date <= end]

    def industry_list(self) -> list[IndustrySummary]:
        return list(self._industries)

    def industry_constituents(self, industry_code: str) -> list[IndustryConstituent]:
        return list(self._industry_members.get(industry_code, []))

    def market_snapshot(self) -> MarketSnapshot:
        return self._snapshot
