"""Pure analytical functions on top of fundamentals + OHLCV.

Kept separate from API so CLI and notebooks can call directly.
"""

from alphaagent.analytics.company import (
    drawdown_curve,
    pe_percentile,
    rolling_return,
)
from alphaagent.analytics.industry import rank_by_change, top_n_inflow
from alphaagent.analytics.market import format_breadth

__all__ = [
    "drawdown_curve",
    "format_breadth",
    "pe_percentile",
    "rank_by_change",
    "rolling_return",
    "top_n_inflow",
]
