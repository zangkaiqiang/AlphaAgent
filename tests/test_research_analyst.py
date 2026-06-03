from types import SimpleNamespace

import pandas as pd
import pytest

from alphaagent.agent.research_analyst import AgentNotConfigured, ResearchAnalyst
from alphaagent.fundamentals.news import NewsItem, StaticNewsProvider
from alphaagent.fundamentals.types import FinancialIndicators
from alphaagent.storage.db import Database


class _Bars:
    def get_bars(self, symbol, start, end, freq="1d"):
        idx = pd.date_range("2023-01-02", periods=260, freq="B")
        c = pd.Series(range(1, 261), index=idx, dtype=float)
        return pd.DataFrame({"open": c, "high": c, "low": c, "close": c, "volume": 1, "amount": 1}, index=idx)


class _Provider:
    def financial_indicators(self, symbol):
        return [FinancialIndicators(symbol=symbol, period="2024", roe=0.12, net_margin=0.3,
                gross_margin=0.4, revenue=1e9, revenue_yoy=0.05, net_income=3e8,
                net_income_yoy=0.06, debt_ratio=0.5)]


def _blk(**kw):
    return SimpleNamespace(**kw)


class _ScriptedClient:
    def __init__(self, responses):
        self._responses = list(responses)
        self.messages = SimpleNamespace(create=self._create)

    def _create(self, **kw):
        return self._responses.pop(0)


def _tool_use(tid, name, inp):
    return _blk(type="tool_use", id=tid, name=name, input=inp)


def test_research_analyst_runs_tools_then_submits_report(tmp_path):
    db = Database(str(tmp_path / "t.db"))
    r1 = _blk(stop_reason="tool_use", content=[_tool_use("t1", "get_financials", {})])
    r2 = _blk(stop_reason="tool_use", content=[_tool_use("t2", "get_news", {})])
    r3 = _blk(stop_reason="tool_use", content=[_tool_use("t3", "submit_report", {
        "rating": "买入", "confidence": 0.8,
        "sections": [{"title": "基本面", "body": "ROE 稳健[1];资讯[3]。"}],
        "cited_source_ids": [1, 3],
    })])
    analyst = ResearchAnalyst(model="m", client=_ScriptedClient([r1, r2, r3]))
    report = analyst.analyze(
        "600000", bar_source=_Bars(), provider=_Provider(),
        news_provider=StaticNewsProvider({"600000": [NewsItem(title="利好", url="u1")]}),
        db=db,
    )
    assert report.rating == "BUY"
    assert report.sections[0].title == "基本面"
    assert any(s.type == "financial" for s in report.sources)
    assert db.query("SELECT COUNT(*) AS n FROM financials WHERE symbol='600000'")[0]["n"] >= 1
    assert db.query("SELECT COUNT(*) AS n FROM news WHERE symbol='600000'")[0]["n"] == 1


def test_degraded_report_when_no_submit(tmp_path):
    db = Database(str(tmp_path / "t.db"))
    loop = _blk(stop_reason="tool_use", content=[_tool_use("t", "get_financials", {})])
    analyst = ResearchAnalyst(model="m", max_tool_rounds=2, client=_ScriptedClient([loop, loop, loop]))
    report = analyst.analyze("600000", bar_source=_Bars(), provider=_Provider(),
                             news_provider=StaticNewsProvider({}), db=db)
    assert report.rating in {"UNKNOWN", "HOLD"}
    assert report.data_complete is False


def test_no_key_raises(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    analyst = ResearchAnalyst(model="m")
    with pytest.raises(AgentNotConfigured):
        analyst.analyze("600000", bar_source=_Bars(), provider=_Provider(),
                        news_provider=StaticNewsProvider({}), db=Database(":memory:"))
