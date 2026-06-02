"""FundamentalsProvider protocol.

The provider abstraction lets:
  - tests inject ``StaticFundamentalsProvider`` (no network)
  - production wire ``AkShareFundamentalsProvider`` (lazy ``akshare`` import)
  - future adapters (Tushare, Wind, etc.) drop in without API changes
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date

from alphaagent.fundamentals.types import (
    FinancialIndicators,
    IndustryConstituent,
    IndustrySummary,
    MarketSnapshot,
    MoneyFlow,
    SecurityInfo,
)


class FundamentalsProvider(ABC):
    # ---- Company ------------------------------------------------------
    @abstractmethod
    def security_info(self, symbol: str) -> SecurityInfo: ...

    @abstractmethod
    def financial_indicators(self, symbol: str) -> list[FinancialIndicators]:
        """Trailing N periods, most recent last."""

    def money_flow(self, symbol: str, start: date, end: date) -> list[MoneyFlow]:
        return []

    # ---- Industry -----------------------------------------------------
    @abstractmethod
    def industry_list(self) -> list[IndustrySummary]: ...

    @abstractmethod
    def industry_constituents(self, industry_code: str) -> list[IndustryConstituent]: ...

    # ---- Market -------------------------------------------------------
    @abstractmethod
    def market_snapshot(self) -> MarketSnapshot: ...
