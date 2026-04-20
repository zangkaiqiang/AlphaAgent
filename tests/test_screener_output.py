"""Output writers: yaml + csv across the three with_reasons modes."""

from __future__ import annotations

from datetime import date

import yaml

from alphaagent.screener.base import Pick, Reason, ScreenResult
from alphaagent.screener.output import render_picks


def _result():
    picks = [
        Pick(
            symbol="600519",
            name="贵州茅台",
            final_score=0.873,
            reasons=[
                Reason("momentum", 0.95, {"return_60d": 0.185}),
                Reason("above_ma", 1.0, {"close": 1620.5, "ma60": 1502.3}),
            ],
            metadata={"industry": "白酒", "list_date": "2001-08-27"},
        ),
        Pick(
            symbol="000858",
            name="五粮液",
            final_score=0.851,
            reasons=[
                Reason("momentum", 0.91, {"return_60d": 0.16}),
                Reason("above_ma", 1.0, {"close": 200, "ma60": 180}),
            ],
            metadata={"industry": "白酒", "list_date": "1998-04-27"},
        ),
    ]
    return ScreenResult(
        generated_at=date(2024, 12, 31),
        resolved_as_of=date(2024, 12, 31),
        universe_name="hs300",
        universe_size=300,
        filtered_size=240,
        rules_applied=["momentum (weight=0.50)", "above_ma (weight=0.50)"],
        universe_snapshot=["600519", "000858"],
        picks=picks,
    )


def test_yaml_full_includes_reasons_and_snapshot():
    text = render_picks(_result(), top_n=10, with_reasons="full", fmt="yaml")
    parsed = yaml.safe_load(text)
    assert parsed["symbols"] == ["600519", "000858"]
    assert parsed["metadata"]["universe_snapshot"] == ["600519", "000858"]
    cand = parsed["candidates"][0]
    assert cand["symbol"] == "600519"
    assert cand["reasons"][0]["rule"] == "momentum"
    assert cand["metadata"]["industry"] == "白酒"


def test_yaml_compact_includes_top_rule():
    text = render_picks(_result(), top_n=10, with_reasons="compact", fmt="yaml")
    parsed = yaml.safe_load(text)
    cand = parsed["candidates"][0]
    assert "reasons" not in cand
    assert "top_rule" in cand
    assert "above_ma" in cand["top_rule"] or "momentum" in cand["top_rule"]


def test_yaml_none_omits_candidates():
    text = render_picks(_result(), top_n=10, with_reasons="none", fmt="yaml")
    parsed = yaml.safe_load(text)
    assert "candidates" not in parsed
    assert parsed["symbols"] == ["600519", "000858"]


def test_yaml_top_n_truncates():
    text = render_picks(_result(), top_n=1, with_reasons="none", fmt="yaml")
    parsed = yaml.safe_load(text)
    assert parsed["symbols"] == ["600519"]


def test_csv_full_has_per_rule_columns():
    text = render_picks(_result(), top_n=10, with_reasons="full", fmt="csv")
    lines = text.strip().splitlines()
    header = lines[0]
    assert "momentum" in header
    assert "above_ma" in header
    assert "industry" in header
    assert "600519" in lines[1]
    assert "贵州茅台" in lines[1]


def test_csv_compact_has_top_rule_column():
    text = render_picks(_result(), top_n=10, with_reasons="compact", fmt="csv")
    header = text.strip().splitlines()[0]
    assert "top_rule" in header
    assert "industry" in header


def test_csv_writes_unicode_safely(tmp_path):
    from alphaagent.screener.output import write_picks

    p = tmp_path / "picks.csv"
    write_picks(_result(), p, top_n=5, with_reasons="compact", fmt="csv")
    text = p.read_text(encoding="utf-8")
    assert "贵州茅台" in text
