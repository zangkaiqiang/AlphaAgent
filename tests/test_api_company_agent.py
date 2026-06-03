from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from alphaagent.agent.company_analyst import AgentNotConfigured, CompanyAnalysis
from alphaagent.api.deps import (
    get_company_analyst,
    get_fundamentals_provider,
    get_kline_data_source,
)
from alphaagent.api.main import app
from alphaagent.data.base import DataSource
from alphaagent.fundamentals.base import FundamentalsProvider
from alphaagent.fundamentals.types import (
    FinancialIndicators,
    MarketSnapshot,
    SecurityInfo,
)


class _Bars(DataSource):
    def get_bars(self, symbol, start, end, freq="1d"):
        idx = pd.date_range("2023-01-02", periods=260, freq="B")
        c = pd.Series(np.linspace(10, 20, 260), index=idx)
        return pd.DataFrame({"open": c, "high": c, "low": c, "close": c, "volume": 100, "amount": 100}, index=idx)


class _Provider(FundamentalsProvider):
    def security_info(self, symbol): return SecurityInfo(symbol=symbol, name=symbol)
    def financial_indicators(self, symbol):
        return [FinancialIndicators(symbol=symbol, period="2024", roe=0.12, net_margin=0.3,
                gross_margin=0.4, revenue=1e9, revenue_yoy=0.05, net_income=3e8,
                net_income_yoy=0.06, debt_ratio=0.5)]
    def industry_list(self): return []
    def industry_constituents(self, code): return []
    def market_snapshot(self): return MarketSnapshot(indices=[], breadth=None, northbound_net=None)


class _StubAnalyst:
    def analyze(self, context):
        return CompanyAnalysis(rating="BUY", summary="看好", reasons=["盈利稳"], risks=["波动"],
                               model="stub", confidence=0.7)


class _BrokenAnalyst:
    def analyze(self, context):
        raise AgentNotConfigured("未配置 ANTHROPIC_API_KEY")


@pytest.fixture(autouse=True)
def _isolated(tmp_path, monkeypatch):
    monkeypatch.setenv("ALPHAAGENT_DB", str(tmp_path / "t.db"))
    from alphaagent.storage import db as _dbmod
    _dbmod._INSTANCES.clear()
    app.dependency_overrides[get_fundamentals_provider] = lambda: _Provider()
    app.dependency_overrides[get_kline_data_source] = lambda: _Bars()
    app.dependency_overrides[get_company_analyst] = lambda: _StubAnalyst()
    yield
    app.dependency_overrides.clear()
    _dbmod._INSTANCES.clear()


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def test_agent_analysis_and_history(client):
    r = client.post("/api/analysis/company/600000/agent")
    assert r.status_code == 200, r.text
    data = r.json()["data"]
    assert data["rating"] == "BUY"
    assert data["reasons"] == ["盈利稳"] and data["risks"] == ["波动"]
    assert data["disclaimer"]
    h = client.get("/api/analysis/company/600000/agent/history").json()["data"]
    assert len(h) >= 1 and h[0]["symbol"] == "600000"


def test_agent_not_configured_returns_400(client):
    app.dependency_overrides[get_company_analyst] = lambda: _BrokenAnalyst()
    r = client.post("/api/analysis/company/600000/agent")
    assert r.status_code == 400
    assert r.json()["detail"]["error"]["code"] == "AGENT_NOT_CONFIGURED"
