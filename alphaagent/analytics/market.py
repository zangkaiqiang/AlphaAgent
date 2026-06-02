"""Market-level analytics."""

from __future__ import annotations

from alphaagent.fundamentals.types import MarketBreadth


def format_breadth(breadth: MarketBreadth | None) -> dict[str, float | int | None]:
    """Compact JSON-friendly summary of the market breadth snapshot."""
    if breadth is None:
        return {
            "advancers": None,
            "decliners": None,
            "unchanged": None,
            "limit_up": None,
            "limit_down": None,
            "advance_decline_ratio": None,
        }
    return {
        "as_of": breadth.date.isoformat(),
        "advancers": breadth.advancers,
        "decliners": breadth.decliners,
        "unchanged": breadth.unchanged,
        "limit_up": breadth.limit_up,
        "limit_down": breadth.limit_down,
        "advance_decline_ratio": breadth.advance_decline_ratio,
    }
