# Agentic 引用研究报告(SP2)Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`). For the LLM tool-loop task (T4), implementers SHOULD also consult the `claude-api` skill (Anthropic tool use + prompt caching). For the frontend task (T6), use `frontend-design`.

**Goal:** 输入代码 → LLM 工具循环按需抓取 技术面/财报/资讯 → 产出分章节研究报告,正文带编号内联引用、锚定到来源条目(财报行项 + 资讯)→ 持久化 → 深色公司页「报告 ↔ 来源」联动展示。

**Architecture:** 纯逻辑核心(报告/来源数据模型 + 引用解析 + 来源 ID 注册)与 LLM 解耦,便于无网络测试。`ResearchAnalyst` 跑 Anthropic tool-use 循环(工具:get_technical/get_financials/get_news;终结工具 submit_report);anthropic 懒导入、可注入 client。新闻来自 akshare(带重试、失败降级)。报告持久化到 company_analysis.report_json。前端报告查看器替换 SP1 占位。

**Tech Stack:** Python 3.11 + sqlite3 + pandas + pydantic + FastAPI + anthropic(agent extra,懒导入);Vue 3 + TS + Element Plus。
**测试:** 全程 mock LLM/akshare;`uv run --extra data --extra api pytest`;前端 `cd web && npm run build`。
**Spec:** `docs/superpowers/specs/2026-06-03-agentic-research-report-design.md`

---

## 文件结构
新增:
- `alphaagent/fundamentals/news.py` — `NewsItem`, `NewsProvider`, `AkShareNewsProvider`, `StaticNewsProvider`.
- `alphaagent/agent/report.py` — `Source`, `ResearchReport`, `SourceRegistry`, `assemble_report`, citation 校验(纯逻辑)。
- `alphaagent/agent/research_analyst.py` — 工具定义 + `ResearchAnalyst`(tool-use 循环)+ `AgentNotConfigured`(复用)。
- 测试:`tests/test_news_provider.py`, `tests/test_report_model.py`, `tests/test_research_analyst.py`, `tests/test_api_research_report.py`。
修改:
- `alphaagent/storage/db.py` — `news` 表 + `company_analysis.report_json` 列(迁移)。
- `alphaagent/api/schemas/analysis.py` — `ResearchReportDTO`, `SourceDTO`, `ReportSectionDTO`。
- `alphaagent/api/deps.py` — `get_research_analyst`, `get_news_provider`。
- `alphaagent/api/routers/analysis/company.py` — POST agent 改用 ResearchAnalyst,持久化 report_json,history 返回报告。
- `web/src/api/types.ts`, `web/src/api/analysis.ts`, `web/src/pages/analysis/company/Index.vue`(报告查看器 + 来源面板,替换 SP1 占位)。

---

## Task 1: storage — news 表 + report_json 列

**Files:** Modify `alphaagent/storage/db.py`; Test `tests/test_storage_news.py`.

- [ ] **Step 1: failing test** — `tests/test_storage_news.py`:
```python
from alphaagent.storage.db import Database


def test_news_table_and_report_json_column(tmp_path):
    db = Database(str(tmp_path / "t.db"))
    db.execute(
        "INSERT OR REPLACE INTO news (symbol,url,title,date,source,summary,fetched_at) "
        "VALUES (?,?,?,?,?,?,?)",
        ("600000", "http://x/1", "标题", "2026-06-01", "东财", "摘要", "2026-06-03T00:00:00"),
    )
    assert db.query("SELECT title FROM news WHERE symbol='600000'")[0]["title"] == "标题"
    # report_json column exists on company_analysis
    db.execute(
        "INSERT OR REPLACE INTO company_analysis "
        "(id,symbol,generated_at,rating,confidence,summary,reasons_json,risks_json,model,context_json,report_json) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        ("r1", "600000", "2026-06-03T00:00:00", "BUY", 0.7, "s", "[]", "[]", "m", "{}", '{"sections":[]}'),
    )
    assert db.query("SELECT report_json FROM company_analysis WHERE id='r1'")[0]["report_json"] == '{"sections":[]}'
```

- [ ] **Step 2: run → FAIL** (`no such table: news`).
- [ ] **Step 3: implement** — in `alphaagent/storage/db.py`:
  (a) Append to `_SCHEMA`:
```sql
CREATE TABLE IF NOT EXISTS news (
    symbol TEXT NOT NULL, url TEXT NOT NULL, title TEXT, date TEXT,
    source TEXT, summary TEXT, fetched_at TEXT NOT NULL,
    PRIMARY KEY (symbol, url)
);
```
  (b) In `init_schema`, after the existing `kind` migration, add an idempotent `report_json` migration (mirror the `kind` PRAGMA-check pattern): if `report_json` not in `PRAGMA table_info(company_analysis)`, run `ALTER TABLE company_analysis ADD COLUMN report_json TEXT`.
- [ ] **Step 4: run → PASS.**
- [ ] **Step 5: commit** `feat(storage): news table + company_analysis.report_json`

---

## Task 2: news provider

**Files:** Create `alphaagent/fundamentals/news.py`; Test `tests/test_news_provider.py`.

- [ ] **Step 1: failing test** — `tests/test_news_provider.py`:
```python
from alphaagent.fundamentals.news import NewsItem, StaticNewsProvider


def test_static_news_provider():
    items = [NewsItem(title="t1", date="2026-06-01", source="东财", url="u1", summary="s1")]
    p = StaticNewsProvider({"600000": items})
    got = p.recent_news("600000", limit=5)
    assert got[0].title == "t1"
    assert p.recent_news("999999") == []
```

- [ ] **Step 2: run → FAIL.**
- [ ] **Step 3: implement** — `alphaagent/fundamentals/news.py`:
```python
"""News (资讯) provider. Lazy akshare; static stub for tests."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class NewsItem:
    title: str
    date: str | None = None
    source: str | None = None
    url: str | None = None
    summary: str | None = None


class NewsProvider(ABC):
    @abstractmethod
    def recent_news(self, symbol: str, limit: int = 10) -> list[NewsItem]: ...


class StaticNewsProvider(NewsProvider):
    def __init__(self, by_symbol: dict[str, list[NewsItem]] | None = None):
        self._by = by_symbol or {}

    def recent_news(self, symbol: str, limit: int = 10) -> list[NewsItem]:
        return list(self._by.get(symbol, []))[:limit]


def _retry(producer, *, attempts: int = 3, base_delay: float = 0.6):
    import time
    last = None
    for i in range(attempts):
        try:
            return producer()
        except Exception as e:
            try:
                import requests
                transient = isinstance(e, requests.exceptions.RequestException)
            except Exception:
                transient = False
            if not (transient or isinstance(e, (ConnectionError, TimeoutError, OSError))):
                raise
            last = e
            if i < attempts - 1:
                time.sleep(base_delay * (2 ** i))
    raise last


class AkShareNewsProvider(NewsProvider):
    def recent_news(self, symbol: str, limit: int = 10) -> list[NewsItem]:
        import akshare as ak

        df = _retry(lambda: ak.stock_news_em(symbol=symbol))
        if df is None or df.empty:
            return []
        out: list[NewsItem] = []
        for _, r in df.head(limit).iterrows():
            out.append(
                NewsItem(
                    title=str(r.get("新闻标题") or r.get("title") or ""),
                    date=str(r.get("发布时间") or r.get("date") or "") or None,
                    source=str(r.get("文章来源") or r.get("source") or "") or None,
                    url=str(r.get("新闻链接") or r.get("url") or "") or None,
                    summary=str(r.get("新闻内容") or r.get("summary") or "")[:300] or None,
                )
            )
        return out


__all__ = ["NewsItem", "NewsProvider", "StaticNewsProvider", "AkShareNewsProvider"]
```
(NOTE: akshare's `stock_news_em` column names may vary by version; the `.get(中文 or english)` fallbacks cover common cases. The implementer should verify column names if akshare is available, but tests use StaticNewsProvider so this isn't on the test path.)

- [ ] **Step 4: run → PASS.** `uv run --extra dev ruff check alphaagent/fundamentals/news.py`.
- [ ] **Step 5: commit** `feat(fundamentals): news provider (akshare + static stub)`

---

## Task 3: report data model + source registry + assembly (pure logic)

**Files:** Create `alphaagent/agent/report.py`; Test `tests/test_report_model.py`.

This is the testable core: source ID registry, the report dataclasses, and assembling/validating a report from the LLM's `submit_report` args (resolving cited IDs to sources, dropping bad IDs).

- [ ] **Step 1: failing test** — `tests/test_report_model.py`:
```python
from alphaagent.agent.report import (
    ResearchReport,
    Source,
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
    # only valid cited sources kept (1,2); bad id 9 dropped from sources
    assert {s.id for s in report.sources} == {1, 2}
    assert report.disclaimer
    assert report.sections[0].title == "基本面"
```

- [ ] **Step 2: run → FAIL.**
- [ ] **Step 3: implement** — `alphaagent/agent/report.py`:
```python
"""Research-report data model + source registry + assembly (pure, no LLM)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

_DISCLAIMER = "本报告由 AI 基于有限公开数据自动生成,仅供研究参考,不构成投资建议。"

_RATING_MAP = {"买入": "BUY", "buy": "BUY", "持有": "HOLD", "hold": "HOLD", "卖出": "SELL", "sell": "SELL"}


@dataclass
class Source:
    id: int
    type: str          # technical | financial | news
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
    rating: str        # BUY | HOLD | SELL | UNKNOWN
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
    secs = [ReportSection(title=str(s.get("title") or ""), body=str(s.get("body") or "")) for s in sections]
    # Keep only cited sources that actually exist; preserve registry order.
    valid_ids = {sid for sid in (cited_source_ids or []) if registry.get(sid) is not None}
    sources = [s for s in registry.all() if s.id in valid_ids]
    conf = None
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
```
NOTE: `model` param is accepted for signature stability though not stored on the dataclass (rating/sections carry the report; model is persisted separately by the API). Keep it in the signature.

- [ ] **Step 4: run → PASS.** ruff clean.
- [ ] **Step 5: commit** `feat(agent): research report model + source registry + assembly`

---

## Task 4: tools + ResearchAnalyst (tool-use loop)

**Files:** Create `alphaagent/agent/research_analyst.py`; Test `tests/test_research_analyst.py`.

Consult the `claude-api` skill for the Anthropic tool-use loop + prompt caching. The harness runs tools, registers sources, and loops until the model calls `submit_report` (or hits `max_tool_rounds` → degraded report).

- [ ] **Step 1: failing test** — `tests/test_research_analyst.py` (fake client scripts the loop; no anthropic, no network):
```python
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
    """Returns a queued sequence of Messages API responses."""
    def __init__(self, responses):
        self._responses = list(responses)
        self.messages = SimpleNamespace(create=self._create)

    def _create(self, **kw):
        return self._responses.pop(0)


def _tool_use(tool_id, name, inp):
    return _blk(type="tool_use", id=tool_id, name=name, input=inp)


def test_research_analyst_runs_tools_then_submits_report(tmp_path):
    db = Database(str(tmp_path / "t.db"))
    # Scripted: round1 -> call get_financials; round2 -> call get_news; round3 -> submit_report
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
    # financials persisted, news persisted
    assert db.query("SELECT COUNT(*) AS n FROM financials WHERE symbol='600000'")[0]["n"] >= 1
    assert db.query("SELECT COUNT(*) AS n FROM news WHERE symbol='600000'")[0]["n"] == 1


def test_degraded_report_when_no_submit(tmp_path):
    db = Database(str(tmp_path / "t.db"))
    # Model keeps calling a tool, never submits -> hit max_tool_rounds=2 -> degraded
    loop = _blk(stop_reason="tool_use", content=[_tool_use("t", "get_financials", {})])
    analyst = ResearchAnalyst(model="m", max_tool_rounds=2, client=_ScriptedClient([loop, loop, loop]))
    report = analyst.analyze("600000", bar_source=_Bars(), provider=_Provider(),
                             news_provider=StaticNewsProvider({}), db=db)
    assert report.rating in {"UNKNOWN", "HOLD"}
    assert report.data_complete is False


def test_no_key_raises(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    analyst = ResearchAnalyst(model="m")  # no client
    with pytest.raises(AgentNotConfigured):
        analyst.analyze("600000", bar_source=_Bars(), provider=_Provider(),
                        news_provider=StaticNewsProvider({}), db=Database(":memory:"))
```

- [ ] **Step 2: run → FAIL.**
- [ ] **Step 3: implement** — `alphaagent/agent/research_analyst.py`. Structure (the implementer fills exact Anthropic message-shaping per the claude-api skill):
  - Reuse `AgentNotConfigured` (import from `alphaagent.agent.company_analyst`).
  - `TOOLS` = list of Anthropic tool schemas: `get_technical{}`, `get_financials{}`, `get_news{limit?}`, `submit_report{rating, confidence, sections:[{title,body}], cited_source_ids:[int]}`.
  - `@dataclass ResearchAnalyst(model="claude-sonnet-4-6", max_tool_rounds=6, max_tokens=2000, client=None)`.
  - `_ensure_client()`: same pattern as CompanyAnalyst (injected client wins; else require key + lazy `from anthropic import Anthropic`).
  - `analyze(symbol, *, bar_source, provider, news_provider, db) -> ResearchReport`:
    1. `reg = SourceRegistry()`; build `tool_impls` closures:
       - `get_technical()`: compute technical features (reuse `alphaagent.analytics.company_agent._technical_features` via `bar_source.get_bars`); register each key metric as a `technical` source; return `{"technical": {...}, "sources":[{id,label}...]}`.
       - `get_financials()`: `provider.financial_indicators` + `persist_financials(db,...)` (reuse from company_agent); register each (period,metric,value) as a `financial` source; return `{"financials":[...], "sources":[{id,label}...]}`.
       - `get_news()`: `news_provider.recent_news(symbol, limit)`; persist to `news` table (INSERT OR REPLACE; skip items with empty url or synthesize a key); register each as `news` source; on exception/empty → return `{"news": [], "note": "资讯暂不可用"}` and set a `news_unavailable` flag. (Never raise.)
    2. tool-use loop (Anthropic Messages): system prompt (analyst instructions, cite sources by the `source_id` returned by tools, end by calling `submit_report`) with `cache_control: ephemeral`; `tools=TOOLS`; conversation messages accumulate assistant tool_use + user tool_result blocks. Loop up to `max_tool_rounds`:
       - call `client.messages.create(...)`; for each `tool_use` block: if name == `submit_report` → `assemble_report(...)` with reg + the args + `data_complete = not news_unavailable and had_data` + notes → RETURN. Else execute the matching tool impl, append assistant message (the tool_use) + a user `tool_result` (content = JSON of the tool's return, INCLUDING the registered source ids) → continue loop.
    3. If loop ends without `submit_report`: build a **degraded** report from whatever was registered (a single "数据小结" section listing gathered technical/financial highlights), `rating="UNKNOWN"`, `data_complete=False`, notes=["未能生成完整报告"].
  - Keep tool-result payloads small (the registered sources carry `id` + compact label/values so the model can cite `[id]`).

  The implementer MUST make `test_research_analyst.py` pass: the scripted client drives get_financials → get_news → submit_report; the harness must execute the real tool impls (persisting to db + registering sources) between the scripted responses, and assemble the final report from the submit_report args. Match the response block shape used in the test (`.stop_reason`, `.content` list of blocks with `.type`, `.name`, `.input`, `.id`).

- [ ] **Step 4: run → PASS** (3 tests). ruff clean. (No anthropic import on the test path — client injected.)
- [ ] **Step 5: commit** `feat(agent): ResearchAnalyst agentic tool-use loop with cited report`

---

## Task 5: API — ResearchReportDTO + endpoint + persistence

**Files:** Modify `alphaagent/api/schemas/analysis.py`, `alphaagent/api/deps.py`, `alphaagent/api/routers/analysis/company.py`; Test `tests/test_api_research_report.py`.

- [ ] **Step 1: failing test** — `tests/test_api_research_report.py` (mirror test_api_company_agent: inject a StubResearchAnalyst returning a fixed ResearchReport, fake bars/provider/news, tmp DB; assert POST returns sectioned report + sources, persists report_json, history returns it; AgentNotConfigured → 400). (Full test in the implementer's hands following the existing test_api_company_agent.py pattern; it MUST assert `data["sections"]` and `data["sources"]` and a persisted `report_json` row.)
- [ ] **Step 2: run → FAIL.**
- [ ] **Step 3: implement:**
  - `schemas/analysis.py`: `SourceDTO{id,type,label,detail:dict}`, `ReportSectionDTO{title,body}`, `ResearchReportDTO{symbol,generated_at,rating,confidence,sections:list[ReportSectionDTO],sources:list[SourceDTO],disclaimer,data_complete,notes:list[str],model}`.
  - `deps.py`: `get_news_provider()` → `AkShareNewsProvider()` (overridable); `get_research_analyst()` → `ResearchAnalyst(model=env ALPHAAGENT_AGENT_MODEL or default)`.
  - `routers/analysis/company.py`: change `POST /{symbol}/agent` to: build bar_source (SqliteBarCache as before), get provider + news_provider + analyst via deps; `report = analyst.analyze(symbol, bar_source=..., provider=..., news_provider=..., db=db)`; persist: store `report_json = json.dumps(report as dict)` + keep rating/confidence/summary(=first section body or rating) columns; return `ResearchReportDTO`. Errors: `AgentNotConfigured`→400, `DataUnavailable`(if assemble of technical/financials totally empty — the analyst/tools can raise it)→502, other→502 (HTTPException(detail=err()) as before). `GET /{symbol}/agent/history` returns rows incl. parsed report_json.
  - Helper to convert `ResearchReport` dataclass → `ResearchReportDTO` (+ a dict for persistence).
- [ ] **Step 4: run → PASS**, then full suite `uv run --extra data --extra api pytest -q -p no:warnings` (all pass) + `ruff check alphaagent tests` (only pre-existing screener errors).
- [ ] **Step 5: commit** `feat(api): agentic research report endpoint (sections + cited sources)`

---

## Task 6: 前端报告查看器(替换 SP1 占位)

**Files:** Modify `web/src/api/types.ts`, `web/src/api/analysis.ts`, `web/src/pages/analysis/company/Index.vue`. **Use `frontend-design`.**

- [ ] **Step 1: types** — add `ReportSource{id,type,label,detail}`, `ReportSection{title,body}`, `ResearchReport{symbol,generated_at,rating,confidence,sections,sources,disclaimer,data_complete,notes,model}`. Update `analysis.ts` `agentAnalyze` return type to `ResearchReport`.
- [ ] **Step 2: report viewer** — replace the SP1 AI-card placeholder (the `<!-- SP2: ... -->` block) in the company page with a dark-themed report viewer:
  - 研判 hero: big rating badge (买红/卖绿/持有中性/数据不足灰) + confidence; `data_complete=false` → 「资讯不完整」tag; render `notes`.
  - Sectioned report: each section title + body. **Parse `[n]` markers in body** into clickable superscript anchors (`<a class="cite" @click="goSource(n)">[n]</a>`); render plain text + line breaks otherwise (no heavy markdown lib).
  - 来源面板: list `sources` (each with an `id` anchor target `id="src-{id}"`); financial → 期/指标/值; news → 标题/日期/出处 + external link; technical → 指标/值. Clicking a `[n]` anchor scrolls to + briefly highlights `#src-{n}`.
  - Loading: while generating, show skeleton + staged hint text. The call is slow (tool loop) — set a generous client timeout.
- [ ] **Step 3: build** — `cd web && npm run build` passes. Fix type errors.
- [ ] **Step 4: commit** `feat(web): cited research-report viewer with source anchors`

---

## Self-Review
- **Spec coverage:** §2 contract→T3/T5/T6;§3 tools→T4;§4 harness/loop/degrade→T4;§5 news+表→T1/T2;§6 report_json→T1/T5;§7 API→T5;§8 viewer→T6;§10 errors→T2(news degrade)/T4(degrade)/T5(400/502);§11 tests→each task (LLM/akshare mocked).
- **Type consistency:** `Source{id,type,label,detail}`,`ResearchReport{...sections,sources,confidence,disclaimer,data_complete,notes}`,`assemble_report(...registry...)`,`SourceRegistry.add/get/all`,`ResearchAnalyst.analyze(symbol,*,bar_source,provider,news_provider,db)` consistent across T3/T4/T5; DTO mirrors dataclass; frontend types mirror DTO.
- **Mocking:** T4 uses an injected scripted client (no anthropic/network); T2/T5 use Static providers; all hermetic.
- **Note for implementer (T4):** match the fake client's response block shape (`.stop_reason`, `.content[].type/name/input/id`); execute real tool impls between scripted responses; `submit_report` ends the loop.
