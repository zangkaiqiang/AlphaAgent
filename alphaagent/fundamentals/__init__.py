"""Fundamentals data layer.

A separate concern from ``alphaagent.data`` (OHLCV):
``fundamentals`` covers basic info, financials, industry composition,
money flow, market indices — everything that's not bar-by-bar price data.
"""

from alphaagent.fundamentals.base import FundamentalsProvider
from alphaagent.fundamentals.static import StaticFundamentalsProvider
from alphaagent.fundamentals.types import (
    FinancialIndicators,
    IndustryConstituent,
    IndustrySummary,
    MarketIndex,
    MoneyFlow,
    SecurityInfo,
)

__all__ = [
    "FinancialIndicators",
    "FundamentalsProvider",
    "IndustryConstituent",
    "IndustrySummary",
    "MarketIndex",
    "MoneyFlow",
    "SecurityInfo",
    "StaticFundamentalsProvider",
]
