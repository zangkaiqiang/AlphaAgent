from alphaagent.agent.report import (
    ResearchReport,  # noqa: F401
    Source,  # noqa: F401
    SourceRegistry,
    assemble_report,
)


def test_source_registry_assigns_unique_ids():
    reg = SourceRegistry()
    a = reg.add("financial", "2024 ROE 12%", {"period": "2024", "metric": "ROE", "value": 0.12})
    b = reg.add("news", "某新闻", {"title": "某新闻", "url": "u1"})
    assert a == 1 and b == 2
    assert len(reg.all()) == 2


def test_assemble_report_resolves_citations_and_drops_bad_ids():
    reg = SourceRegistry()
    reg.add("financial", "2024 ROE 12%", {"period": "2024"})   # id 1
    reg.add("news", "利好新闻", {"title": "利好新闻"})           # id 2
    report = assemble_report(
        symbol="600000",
        generated_at="2026-06-03T00:00:00",
        rating="买入",
        confidence=0.8,
        sections=[{"title": "基本面", "body": "ROE 稳健[1];近期有利好[2];坏引用[9]。"}],
        cited_source_ids=[1, 2, 9],
        registry=reg,
        model="m",
        data_complete=True,
        notes=[],
    )
    assert report.rating == "BUY"
    assert {s.id for s in report.sources} == {1, 2}
    assert report.disclaimer
    assert report.sections[0].title == "基本面"


def test_assemble_report_degraded_unknown_rating_and_bad_confidence():
    reg = SourceRegistry()
    report = assemble_report(
        symbol="x", generated_at="t", rating="???", confidence="oops",
        sections=[], cited_source_ids=[], registry=reg, model="m",
        data_complete=False, notes=["未能生成完整报告"],
    )
    assert report.rating == "UNKNOWN"
    assert report.confidence is None
    assert report.data_complete is False
    assert report.notes == ["未能生成完整报告"]
