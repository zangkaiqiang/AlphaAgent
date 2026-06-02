"""End-to-end tests for the analysis API routers using a Static provider."""

from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from alphaagent.api.deps import get_fundamentals_provider, get_kline_data_source
from alphaagent.api.main import app
from alphaagent.data.base import DataSource
from alphaagent.fundamentals.static import StaticFundamentalsProvider
from alphaagent.fundamentals.types import (
    FinancialIndicators,
    IndustryConstituent,
    IndustrySummary,
    MarketBreadth,
    MarketIndex,
    MarketSnapshot,
    SecurityInfo,
)


class _StubKLineSource(DataSource):
    def get_bars(self, symbol, start, end, freq="1d"):
        idx = pd.date_range("2024-01-02", periods=20, freq="B")
        return pd.DataFrame(
            {
                "open": [10.0] * 20,
                "high": [10.1] * 20,
                "low": [9.9] * 20,
                "close": [10.0 + i * 0.1 for i in range(20)],
                "volume": [1_000_000] * 20,
            },
            index=idx,
        )


@pytest.fixture
def provider() -> StaticFundamentalsProvider:
    sec = SecurityInfo(
        symbol="600000",
        name="浦发银行",
        industry="银行",
        market_cap=2.0e11,
        pe=5.5,
        listed_date=date(1999, 11, 10),
    )
    fin = FinancialIndicators(
        symbol="600000", period="2024Q3", roe=0.11, revenue=1.5e11, revenue_yoy=0.05
    )
    ind = IndustrySummary(code="BK0475", name="银行", change_pct=1.2, money_flow_net=5e8)
    other = IndustrySummary(code="BK0473", name="白酒", change_pct=-0.8, money_flow_net=-2e8)
    con = IndustryConstituent(symbol="600000", name="浦发银行", change_pct=1.5, pe=5.5)

    snap = MarketSnapshot(
        indices=[MarketIndex(code="000001", name="上证指数", last=3000.0, change_pct=0.5)],
        breadth=MarketBreadth(
            date=date(2024, 1, 2),
            advancers=3000,
            decliners=1500,
            unchanged=200,
            limit_up=20,
            limit_down=5,
        ),
        northbound_net=1.2e9,
    )
    return StaticFundamentalsProvider(
        securities={"600000": sec},
        financials={"600000": [fin]},
        industries=[ind, other],
        industry_members={"BK0475": [con]},
        snapshot=snap,
    )


@pytest.fixture
def client(provider):
    app.dependency_overrides[get_fundamentals_provider] = lambda: provider
    app.dependency_overrides[get_kline_data_source] = lambda: _StubKLineSource()
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Company
# ---------------------------------------------------------------------------


def test_company_overview(client):
    r = client.get("/api/analysis/company/600000")
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["info"]["name"] == "浦发银行"
    assert data["info"]["industry"] == "银行"
    assert data["financials"][0]["roe"] == 0.11
    assert len(data["kline"]) == 20
    assert "5d" in data["returns"]


def test_company_kline_only(client):
    r = client.get("/api/analysis/company/600000/kline?days=60")
    assert r.status_code == 200
    points = r.json()["data"]
    assert len(points) == 20
    assert {"timestamp", "open", "high", "low", "close", "volume"} <= set(points[0])


def test_company_financials_only(client):
    r = client.get("/api/analysis/company/600000/financials")
    assert r.json()["data"][0]["period"] == "2024Q3"


def test_company_unknown_symbol_returns_404(client):
    r = client.get("/api/analysis/company/999999")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Industry
# ---------------------------------------------------------------------------


def test_industry_list_default_sorts_by_change_desc(client):
    r = client.get("/api/analysis/industry")
    data = r.json()["data"]
    assert data[0]["name"] == "银行"   # +1.2% beats -0.8%


def test_industry_list_sort_by_inflow(client):
    r = client.get("/api/analysis/industry?sort=inflow")
    data = r.json()["data"]
    # Bank has 5e8 inflow, 白酒 has -2e8 -> bank first.
    assert data[0]["name"] == "银行"


def test_industry_detail(client):
    r = client.get("/api/analysis/industry/BK0475")
    data = r.json()["data"]
    assert data["industry"]["name"] == "银行"
    assert len(data["constituents"]) == 1
    assert data["constituents"][0]["symbol"] == "600000"


def test_industry_detail_404_on_unknown_code(client):
    r = client.get("/api/analysis/industry/DOESNOTEXIST")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Market
# ---------------------------------------------------------------------------


def test_market_snapshot(client):
    r = client.get("/api/analysis/market/snapshot")
    data = r.json()["data"]
    assert data["indices"][0]["name"] == "上证指数"
    assert data["breadth"]["advance_decline_ratio"] == pytest.approx(2.0)
    assert data["northbound_net"] == 1.2e9


# silence unused import warning
_ = timedelta
