"""Research-report data model + source registry + assembly (pure, no LLM)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

_DISCLAIMER = "本报告由 AI 基于有限公开数据自动生成,仅供研究参考,不构成投资建议。"

_RATING_MAP = {"买入": "BUY", "buy": "BUY", "持有": "HOLD", "hold": "HOLD", "卖出": "SELL", "sell": "SELL"}


@dataclass
class Source:
    id: int
    type: str
    label: str
    detail: dict[str, Any]


@dataclass
class ReportSection:
    title: str
    body: str


@dataclass
class ResearchReport:
    symbol: str
    generated_at: str
    rating: str
    sections: list[ReportSection]
    sources: list[Source]
    confidence: float | None = None
    disclaimer: str = _DISCLAIMER
    data_complete: bool = True
    notes: list[str] = field(default_factory=list)


class SourceRegistry:
    def __init__(self) -> None:
        self._items: list[Source] = []
        self._next = 1

    def add(self, type: str, label: str, detail: dict[str, Any]) -> int:
        sid = self._next
        self._next += 1
        self._items.append(Source(id=sid, type=type, label=label, detail=detail))
        return sid

    def get(self, sid: int) -> Source | None:
        return next((s for s in self._items if s.id == sid), None)

    def all(self) -> list[Source]:
        return list(self._items)


def coerce_rating(raw: Any) -> str:
    s = str(raw or "").strip()
    if s in _RATING_MAP:
        return _RATING_MAP[s]
    if s.lower() in _RATING_MAP:
        return _RATING_MAP[s.lower()]
    return s.upper() if s.upper() in {"BUY", "HOLD", "SELL"} else "UNKNOWN"


def assemble_report(
    *, symbol, generated_at, rating, confidence, sections, cited_source_ids,
    registry: SourceRegistry, model, data_complete=True, notes=None,
) -> ResearchReport:
    secs = [
        ReportSection(title=str(s.get("title") or ""), body=str(s.get("body") or ""))
        for s in (sections or [])
    ]
    valid_ids = {sid for sid in (cited_source_ids or []) if registry.get(sid) is not None}
    sources = [s for s in registry.all() if s.id in valid_ids]
    try:
        conf = float(confidence) if confidence is not None else None
    except (TypeError, ValueError):
        conf = None
    return ResearchReport(
        symbol=symbol, generated_at=generated_at, rating=coerce_rating(rating),
        sections=secs, sources=sources, confidence=conf,
        data_complete=bool(data_complete), notes=list(notes or []),
    )


__all__ = ["Source", "ReportSection", "ResearchReport", "SourceRegistry", "coerce_rating", "assemble_report"]
