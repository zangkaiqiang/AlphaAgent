from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from alphaagent.agent.company_analyst import AgentNotConfigured
from alphaagent.agent.report import ReportSection, ResearchReport, Source
from alphaagent.api.deps import (
    get_fundamentals_provider,
    get_kline_data_source,
    get_news_provider,
    get_research_analyst,
)
from alphaagent.api.main import app
from alphaagent.data.base import DataSource
from alphaagent.fundamentals.base import FundamentalsProvider
from alphaagent.fundamentals.news import StaticNewsProvider
from alphaagent.fundamentals.types import FinancialIndicators, MarketSnapshot, SecurityInfo


class _Bars(DataSource):
    def get_bars(self, symbol, start, end, freq="1d"):
        idx = pd.date_range("2023-01-02", periods=60, freq="B")
        c = pd.Series(np.linspace(10, 20, 60), index=idx)
        return pd.DataFrame({"open": c, "high": c, "low": c, "close": c, "volume": 1, "amount": 1}, index=idx)


class _Provider(FundamentalsProvider):
    def security_info(self, symbol): return SecurityInfo(symbol=symbol, name=symbol)
    def financial_indicators(self, symbol):
        return [FinancialIndicators(symbol=symbol, period="2024", roe=0.12, net_margin=0.3,
                gross_margin=0.4, revenue=1e9, revenue_yoy=0.05, net_income=3e8, net_income_yoy=0.06, debt_ratio=0.5)]
    def industry_list(self): return []
    def industry_constituents(self, code): return []
    def market_snapshot(self): return MarketSnapshot(indices=[], breadth=None, northbound_net=None)


class _StubAnalyst:
    model = "stub-model"

    def analyze(self, symbol, *, bar_source, provider, news_provider, db):
        return ResearchReport(
            symbol=symbol, generated_at="2026-06-03T00:00:00", rating="BUY",
            sections=[ReportSection(title="基本面", body="ROE 稳健[1]。")],
            sources=[Source(id=1, type="financial", label="2024 ROE 0.12", detail={"period": "2024"})],
            confidence=0.8, data_complete=True, notes=[],
        )


class _BrokenAnalyst:
    def analyze(self, symbol, **kw):
        raise AgentNotConfigured("未配置 ANTHROPIC_API_KEY")


@pytest.fixture(autouse=True)
def _isolated(tmp_path, monkeypatch):
    monkeypatch.setenv("ALPHAAGENT_DB", str(tmp_path / "t.db"))
    from alphaagent.storage import db as _dbmod
    _dbmod._INSTANCES.clear()
    app.dependency_overrides[get_fundamentals_provider] = lambda: _Provider()
    app.dependency_overrides[get_kline_data_source] = lambda: _Bars()
    app.dependency_overrides[get_news_provider] = lambda: StaticNewsProvider({})
    app.dependency_overrides[get_research_analyst] = lambda: _StubAnalyst()
    yield
    app.dependency_overrides.clear()
    _dbmod._INSTANCES.clear()


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def test_report_and_history(client):
    r = client.post("/api/analysis/company/600000/agent")
    assert r.status_code == 200, r.text
    d = r.json()["data"]
    assert d["rating"] == "BUY"
    assert d["sections"][0]["title"] == "基本面"
    assert d["sources"][0]["id"] == 1
    assert d["disclaimer"]
    assert d["model"] == "stub-model"  # populated from analyst.model (the Important fix)
    h = client.get("/api/analysis/company/600000/agent/history").json()["data"]
    assert len(h) >= 1 and h[0]["symbol"] == "600000"
    assert h[0]["report"] is not None and h[0]["report"]["rating"] == "BUY"


def test_not_configured_400(client):
    app.dependency_overrides[get_research_analyst] = lambda: _BrokenAnalyst()
    r = client.post("/api/analysis/company/600000/agent")
    assert r.status_code == 400
    assert r.json()["detail"]["error"]["code"] == "AGENT_NOT_CONFIGURED"
