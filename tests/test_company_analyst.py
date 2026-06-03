from types import SimpleNamespace

import pytest

from alphaagent.agent.company_analyst import (
    AgentNotConfigured,
    CompanyAnalyst,
    _parse_analysis,
)


def _fake_client(text: str):
    create = lambda **kw: SimpleNamespace(content=[SimpleNamespace(text=text)])  # noqa: E731
    return SimpleNamespace(messages=SimpleNamespace(create=create))


def test_parse_valid_json():
    a = _parse_analysis(
        '{"rating":"买入","confidence":0.8,"summary":"强","reasons":["r1"],"risks":["x1"]}',
        model="m",
    )
    assert a.rating == "BUY"
    assert a.confidence == 0.8
    assert a.reasons == ["r1"] and a.risks == ["x1"]
    assert a.disclaimer


def test_parse_non_json_degrades():
    a = _parse_analysis("the market looks fine, no json here", model="m")
    assert a.rating == "UNKNOWN"
    assert "no json" in a.summary


def test_analyze_with_injected_client():
    analyst = CompanyAnalyst(model="m", client=_fake_client('{"rating":"SELL","summary":"s","reasons":[],"risks":["r"]}'))
    a = analyst.analyze({"symbol": "600000"})
    assert a.rating == "SELL"
    assert a.risks == ["r"]


def test_analyze_without_key_raises(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    analyst = CompanyAnalyst(model="m")  # no client injected -> must build one -> needs key
    with pytest.raises(AgentNotConfigured):
        analyst.analyze({"symbol": "600000"})
