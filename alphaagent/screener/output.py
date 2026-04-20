"""Writers for ScreenResult.

Two formats: yaml (default, easy to paste back into ``strategy.yaml``)
and csv (Excel-friendly review).

``with_reasons`` modes:
- ``full``: every Reason with detail
- ``compact``: only ``final_score`` and the top-scoring rule name
- ``none``: only the symbols list
"""

from __future__ import annotations

import csv
from io import StringIO
from pathlib import Path
from typing import Literal

import yaml

from alphaagent.screener.base import Pick, ScreenResult

Reasons = Literal["full", "compact", "none"]


def write_picks(
    result: ScreenResult,
    path: str | Path,
    top_n: int,
    with_reasons: Reasons = "full",
    fmt: Literal["yaml", "csv"] = "yaml",
) -> None:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    text = render_picks(result, top_n=top_n, with_reasons=with_reasons, fmt=fmt)
    out.write_text(text, encoding="utf-8")


def render_picks(
    result: ScreenResult,
    top_n: int,
    with_reasons: Reasons = "full",
    fmt: Literal["yaml", "csv"] = "yaml",
) -> str:
    if fmt == "yaml":
        return _render_yaml(result, top_n, with_reasons)
    if fmt == "csv":
        return _render_csv(result, top_n, with_reasons)
    raise ValueError(f"unknown format: {fmt!r}")


def _render_yaml(result: ScreenResult, top_n: int, with_reasons: Reasons) -> str:
    top = result.top(top_n)
    payload: dict = {
        "metadata": {
            "generated_at": result.generated_at.isoformat(),
            "resolved_as_of": result.resolved_as_of.isoformat(),
            "universe": result.universe_name,
            "universe_size": result.universe_size,
            "filtered_size": result.filtered_size,
            "rules": result.rules_applied,
            "universe_snapshot": result.universe_snapshot,
        },
        "symbols": [p.symbol for p in top],
    }

    if with_reasons == "none":
        return yaml.safe_dump(payload, allow_unicode=True, sort_keys=False)

    candidates: list[dict] = []
    for p in top:
        entry: dict = {
            "symbol": p.symbol,
            "name": p.name,
            "final_score": round(p.final_score, 4),
        }
        if with_reasons == "full":
            entry["reasons"] = [
                {
                    "rule": r.rule_name,
                    "score": round(r.score, 4),
                    "detail": r.detail,
                }
                for r in p.reasons
            ]
            entry["metadata"] = p.metadata
        else:  # compact
            entry["top_rule"] = _top_rule(p)
        candidates.append(entry)

    payload["candidates"] = candidates
    return yaml.safe_dump(payload, allow_unicode=True, sort_keys=False)


def _render_csv(result: ScreenResult, top_n: int, with_reasons: Reasons) -> str:
    top = result.top(top_n)
    buf = StringIO()
    rule_names: list[str] = []
    if with_reasons == "full" and top:
        seen: set[str] = set()
        for p in top:
            for r in p.reasons:
                if r.rule_name not in seen:
                    seen.add(r.rule_name)
                    rule_names.append(r.rule_name)

    header = ["symbol", "name", "final_score"]
    if with_reasons == "full":
        header += rule_names + ["industry"]
    elif with_reasons == "compact":
        header += ["top_rule", "industry"]

    writer = csv.writer(buf)
    writer.writerow(header)
    for p in top:
        row = [p.symbol, p.name or "", f"{p.final_score:.4f}"]
        if with_reasons == "full":
            scores_by_rule = {r.rule_name: r.score for r in p.reasons}
            for rn in rule_names:
                v = scores_by_rule.get(rn)
                row.append(f"{v:.4f}" if v is not None else "")
            row.append(p.metadata.get("industry") or "")
        elif with_reasons == "compact":
            row.append(_top_rule(p) or "")
            row.append(p.metadata.get("industry") or "")
        writer.writerow(row)
    return buf.getvalue()


def _top_rule(p: Pick) -> str | None:
    if not p.reasons:
        return None
    best = max(p.reasons, key=lambda r: r.score)
    return f"{best.rule_name}={best.score:.2f}"
