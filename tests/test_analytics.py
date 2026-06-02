"""Unit tests for the analytics layer (pure functions)."""

from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from alphaagent.analytics.company import drawdown_curve, pe_percentile, rolling_return
from alphaagent.analytics.industry import rank_by_change, top_n_inflow
from alphaagent.analytics.market import format_breadth
from alphaagent.fundamentals.types import IndustrySummary, MarketBreadth

# ---------------------------------------------------------------------------
# Company
# ---------------------------------------------------------------------------


def test_pe_percentile_basic():
    hist = pd.Series([10, 20, 30, 40, 50])
    assert pe_percentile(hist, 30) == pytest.approx(60.0)
    assert pe_percentile(hist, 5) == 0.0
    assert pe_percentile(hist, 100) == 100.0


def test_pe_percentile_handles_empty_series():
    assert pe_percentile(pd.Series([], dtype=float), 12.0) == 50.0


def test_rolling_return_windows():
    closes = pd.Series([10.0] * 100 + [11.0])
    rr = rolling_return(closes, [5, 20, 60])
    assert rr["5d"] == pytest.approx(0.1)
    assert rr["20d"] == pytest.approx(0.1)


def test_rolling_return_drops_too_short_windows():
    closes = pd.Series([10.0, 11.0])
    rr = rolling_return(closes, [5, 20])
    assert rr == {}  # both windows exceed series length


def test_drawdown_curve_is_underwater():
    closes = pd.Series([100, 120, 90, 110])
    dd = drawdown_curve(closes)
    assert dd.iloc[0] == 0
    assert dd.iloc[2] == pytest.approx(-0.25)
    assert dd.max() <= 0


# ---------------------------------------------------------------------------
# Industry
# ---------------------------------------------------------------------------


def _ind(name: str, change: float | None, flow: float | None = None) -> IndustrySummary:
    return IndustrySummary(code=name, name=name, change_pct=change, money_flow_net=flow)


def test_rank_by_change_descending():
    items = [_ind("银行", -1.0), _ind("白酒", 3.0), _ind("芯片", 1.0)]
    ranked = rank_by_change(items, descending=True)
    assert [r.name for r in ranked] == ["白酒", "芯片", "银行"]


def test_rank_by_change_puts_none_last():
    items = [_ind("A", None), _ind("B", 2.0)]
    ranked = rank_by_change(items, descending=True)
    assert ranked[0].name == "B"
    assert ranked[-1].name == "A"


def test_top_n_inflow_filters_out_none():
    items = [_ind("A", 1.0, 100.0), _ind("B", 2.0, None), _ind("C", 1.0, 200.0)]
    top = top_n_inflow(items, n=5)
    assert [t.name for t in top] == ["C", "A"]  # B excluded (no flow data)


# ---------------------------------------------------------------------------
# Market
# ---------------------------------------------------------------------------


def test_format_breadth_with_data():
    b = MarketBreadth(
        date=date(2024, 1, 2),
        advancers=3000,
        decliners=1500,
        unchanged=200,
        limit_up=20,
        limit_down=5,
    )
    out = format_breadth(b)
    assert out["advancers"] == 3000
    assert out["advance_decline_ratio"] == pytest.approx(2.0)


def test_format_breadth_with_none_safe():
    out = format_breadth(None)
    assert out["advancers"] is None
    assert out["advance_decline_ratio"] is None
