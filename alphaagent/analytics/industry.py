"""Industry-level analytics."""

from __future__ import annotations

from alphaagent.fundamentals.types import IndustrySummary


def rank_by_change(industries: list[IndustrySummary], descending: bool = True) -> list[IndustrySummary]:
    """Sort industries by ``change_pct``. None values sink to the bottom."""
    return sorted(
        industries,
        key=lambda x: (x.change_pct is None, -(x.change_pct or 0) if descending else (x.change_pct or 0)),
    )


def top_n_inflow(industries: list[IndustrySummary], n: int = 10) -> list[IndustrySummary]:
    """Top N industries by main-force net inflow."""
    have_flow = [i for i in industries if i.money_flow_net is not None]
    return sorted(have_flow, key=lambda x: -(x.money_flow_net or 0))[:n]
