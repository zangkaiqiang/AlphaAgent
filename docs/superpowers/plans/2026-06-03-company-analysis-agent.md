# 公司分析智能体 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 输入公司代码 → 自动拉轻量数据(K线+财务)并持久化到 SQLite → Claude 综合分析(买入/持有/卖出 + 理由 + 风险 + 摘要)→ 持久化结果 → 在公司分析页展示。

**Architecture:** 三层:`analytics/company_agent.py`(组装+持久化+回退,纯/数据层)、`agent/company_analyst.py`(Claude 调用,JSON 结构化 + prompt caching,可注入 client)、`api/routers/analysis/company.py`(同步 endpoint)。两张新 SQLite 表(`financials`、`company_analysis`)。测试全程 **mock 掉 LLM**(注入 fake client / Stub analyst),不真调、不联网。

**Tech Stack:** Python 3.11+,stdlib sqlite3,pandas,pydantic,FastAPI,anthropic(`agent` extra,懒导入),Vue 3 + Element Plus。

**测试命令:** `uv run --extra data --extra api pytest ...`;前端 `cd web && npm run build`。

**Spec:** `docs/superpowers/specs/2026-06-03-company-analysis-agent-design.md`

---

## 文件结构

新增:
- `alphaagent/analytics/company_agent.py` — `assemble_company_context` + `persist_financials` + `load_persisted_financials` + 技术特征 + `DataUnavailable`。
- `alphaagent/agent/company_analyst.py` — `CompanyAnalyst` + `CompanyAnalysis` + `AgentNotConfigured` + `SYSTEM_PROMPT`。
- 测试:`tests/test_storage_company.py`、`tests/test_company_agent_context.py`、`tests/test_company_analyst.py`、`tests/test_api_company_agent.py`。

修改:
- `alphaagent/storage/db.py` — `_SCHEMA` 加两张表。
- `alphaagent/api/schemas/analysis.py` — `CompanyAnalysisDTO`。
- `alphaagent/api/deps.py` — `get_company_analyst`。
- `alphaagent/api/routers/analysis/company.py` — POST agent + GET history。
- `web/src/api/types.ts`、`web/src/api/analysis.ts`、`web/src/pages/analysis/company/Index.vue`。

---

## Task 1: SQLite 表 financials + company_analysis

**Files:** Modify `alphaagent/storage/db.py`; Test `tests/test_storage_company.py`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_storage_company.py
from alphaagent.storage.db import Database


def test_financials_and_analysis_tables(tmp_path):
    db = Database(str(tmp_path / "t.db"))
    db.execute(
        "INSERT OR REPLACE INTO financials "
        "(symbol,period,roe,net_margin,gross_margin,revenue,revenue_yoy,"
        "net_income,net_income_yoy,debt_ratio,fetched_at) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        ("600000", "2024", 0.12, 0.3, 0.4, 1e9, 0.05, 3e8, 0.06, 0.5, "2026-06-03T00:00:00"),
    )
    assert db.query("SELECT roe FROM financials WHERE symbol='600000'")[0]["roe"] == 0.12

    db.execute(
        "INSERT OR REPLACE INTO company_analysis "
        "(id,symbol,generated_at,rating,confidence,summary,reasons_json,risks_json,model,context_json) "
        "VALUES (?,?,?,?,?,?,?,?,?,?)",
        ("a1", "600000", "2026-06-03T00:00:00", "BUY", 0.7, "ok", "[]", "[]", "m", "{}"),
    )
    rows = db.query("SELECT rating FROM company_analysis WHERE symbol='600000'")
    assert rows[0]["rating"] == "BUY"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --extra data --extra api pytest tests/test_storage_company.py -v`
Expected: FAIL (`sqlite3.OperationalError: no such table: financials`).

- [ ] **Step 3: Implement** — in `alphaagent/storage/db.py`, append these two tables to the `_SCHEMA` string (before the closing `"""`):

```sql
CREATE TABLE IF NOT EXISTS financials (
    symbol TEXT NOT NULL,
    period TEXT NOT NULL,
    roe REAL, net_margin REAL, gross_margin REAL,
    revenue REAL, revenue_yoy REAL,
    net_income REAL, net_income_yoy REAL, debt_ratio REAL,
    fetched_at TEXT NOT NULL,
    PRIMARY KEY (symbol, period)
);
CREATE TABLE IF NOT EXISTS company_analysis (
    id TEXT PRIMARY KEY,
    symbol TEXT NOT NULL,
    generated_at TEXT NOT NULL,
    rating TEXT NOT NULL,
    confidence REAL,
    summary TEXT,
    reasons_json TEXT,
    risks_json TEXT,
    model TEXT,
    context_json TEXT
);
CREATE INDEX IF NOT EXISTS idx_company_analysis_symbol
    ON company_analysis(symbol, generated_at);
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run --extra data --extra api pytest tests/test_storage_company.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add alphaagent/storage/db.py tests/test_storage_company.py
git commit -m "feat(storage): add financials + company_analysis tables"
```

---

## Task 2: 数据组装层 company_agent.py

**Files:** Create `alphaagent/analytics/company_agent.py`; Test `tests/test_company_agent_context.py`.

Reuses `alphaagent/analytics/company.py`: `rolling_return(closes, windows) -> dict[str,float]` and `drawdown_curve(closes) -> pd.Series`. The `FinancialIndicators` type lives in `alphaagent/fundamentals/types.py` with fields `symbol, period, roe, roa, gross_margin, net_margin, revenue, revenue_yoy, net_income, net_income_yoy, debt_ratio`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_company_agent_context.py
from datetime import date

import pandas as pd

from alphaagent.analytics.company_agent import (
    DataUnavailable,
    assemble_company_context,
    load_persisted_financials,
)
from alphaagent.fundamentals.types import FinancialIndicators
from alphaagent.storage.db import Database


class _FakeBars:
    def __init__(self, df, fail=False):
        self._df, self._fail = df, fail

    def get_bars(self, symbol, start, end, freq="1d"):
        if self._fail:
            return pd.DataFrame()
        return self._df


class _FakeProvider:
    def __init__(self, items=None, raises=False):
        self._items, self._raises = items or [], raises

    def financial_indicators(self, symbol):
        if self._raises:
            raise ConnectionError("proxy down")
        return self._items


def _bars(n=260):
    idx = pd.date_range("2023-01-02", periods=n, freq="B")
    close = pd.Series(range(1, n + 1), index=idx, dtype=float)
    return pd.DataFrame(
        {"open": close, "high": close, "low": close, "close": close, "volume": 100, "amount": 100},
        index=idx,
    )


def _fin(period):
    return FinancialIndicators(
        symbol="600000", period=period, roe=0.12, net_margin=0.3, gross_margin=0.4,
        revenue=1e9, revenue_yoy=0.05, net_income=3e8, net_income_yoy=0.06, debt_ratio=0.5,
    )


def test_context_has_technical_and_persists_financials(tmp_path):
    db = Database(str(tmp_path / "t.db"))
    ctx = assemble_company_context(
        "600000", _FakeBars(_bars()), _FakeProvider([_fin("2023"), _fin("2024")]), db
    )
    assert ctx["symbol"] == "600000"
    assert "5d" in ctx["technical"]["returns"]
    assert ctx["technical"]["last_price"] == 260.0
    assert ctx["data_complete"] is True
    assert len(ctx["financials"]) == 2
    # persisted
    assert load_persisted_financials(db, "600000")[0].roe == 0.12


def test_fallback_to_persisted_when_fetch_fails(tmp_path):
    db = Database(str(tmp_path / "t.db"))
    # seed persisted financials
    assemble_company_context("600000", _FakeBars(_bars()), _FakeProvider([_fin("2023")]), db)
    # now fetch fails -> use persisted, data_complete False
    ctx = assemble_company_context("600000", _FakeBars(_bars()), _FakeProvider(raises=True), db)
    assert ctx["data_complete"] is False
    assert len(ctx["financials"]) == 1


def test_raises_when_no_bars_and_no_financials(tmp_path):
    db = Database(str(tmp_path / "t.db"))
    import pytest
    with pytest.raises(DataUnavailable):
        assemble_company_context("999999", _FakeBars(_bars(), fail=True), _FakeProvider(raises=True), db)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --extra data --extra api pytest tests/test_company_agent_context.py -v`
Expected: FAIL (`ModuleNotFoundError: alphaagent.analytics.company_agent`).

- [ ] **Step 3: Implement** — create `alphaagent/analytics/company_agent.py`:

```python
"""Assemble a lightweight, persisted company context for the LLM analyst.

Pulls only per-symbol small requests (daily bars + financial abstract) — never
the 90-field eastmoney quote that chokes the user's proxy. Fetched financials
are persisted to SQLite; on a fetch failure we fall back to the last persisted
copy so analysis still works when the network is flaky.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

import numpy as np
import pandas as pd

from alphaagent.analytics.company import drawdown_curve, rolling_return
from alphaagent.data.base import DataSource
from alphaagent.fundamentals.base import FundamentalsProvider
from alphaagent.fundamentals.types import FinancialIndicators
from alphaagent.storage.db import Database

_RETURN_WINDOWS = [5, 20, 60, 120, 250]


class DataUnavailable(RuntimeError):
    """Neither bars nor financials could be obtained for the symbol."""


def _f(x) -> float | None:
    if x is None:
        return None
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return round(v, 6) if v == v else None


def persist_financials(db: Database, symbol: str, items: list[FinancialIndicators]) -> None:
    now = datetime.utcnow().isoformat()
    rows = [
        (
            symbol, it.period, _f(it.roe), _f(it.net_margin), _f(it.gross_margin),
            _f(it.revenue), _f(it.revenue_yoy), _f(it.net_income), _f(it.net_income_yoy),
            _f(it.debt_ratio), now,
        )
        for it in items
    ]
    if rows:
        db.executemany(
            "INSERT OR REPLACE INTO financials "
            "(symbol,period,roe,net_margin,gross_margin,revenue,revenue_yoy,"
            "net_income,net_income_yoy,debt_ratio,fetched_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            rows,
        )


def load_persisted_financials(db: Database, symbol: str) -> list[FinancialIndicators]:
    rows = db.query(
        "SELECT * FROM financials WHERE symbol=? ORDER BY period", (symbol,)
    )
    return [
        FinancialIndicators(
            symbol=symbol, period=r["period"], roe=r["roe"], net_margin=r["net_margin"],
            gross_margin=r["gross_margin"], revenue=r["revenue"], revenue_yoy=r["revenue_yoy"],
            net_income=r["net_income"], net_income_yoy=r["net_income_yoy"], debt_ratio=r["debt_ratio"],
        )
        for r in rows
    ]


def _technical_features(bars: pd.DataFrame) -> dict[str, Any]:
    closes = bars["close"].astype(float)
    dd = drawdown_curve(closes)
    daily = closes.pct_change().dropna()
    vol = float(daily.std() * np.sqrt(252)) if len(daily) > 1 else None
    last = float(closes.iloc[-1])
    ma20 = float(closes.rolling(20).mean().iloc[-1]) if len(closes) >= 20 else None
    ma60 = float(closes.rolling(60).mean().iloc[-1]) if len(closes) >= 60 else None
    return {
        "last_price": round(last, 4),
        "returns": {k: round(v, 6) for k, v in rolling_return(closes, _RETURN_WINDOWS).items()},
        "current_drawdown": round(float(dd.iloc[-1]), 6),
        "max_drawdown": round(float(dd.min()), 6),
        "annualized_volatility": round(vol, 6) if vol is not None else None,
        "above_ma20": (last > ma20) if ma20 is not None else None,
        "above_ma60": (last > ma60) if ma60 is not None else None,
    }


def _fin_to_dict(it: FinancialIndicators) -> dict[str, Any]:
    return {
        "period": it.period, "roe": _f(it.roe), "net_margin": _f(it.net_margin),
        "gross_margin": _f(it.gross_margin), "revenue": _f(it.revenue),
        "revenue_yoy": _f(it.revenue_yoy), "net_income": _f(it.net_income),
        "net_income_yoy": _f(it.net_income_yoy), "debt_ratio": _f(it.debt_ratio),
    }


def assemble_company_context(
    symbol: str,
    bar_source: DataSource,
    provider: FundamentalsProvider,
    db: Database,
    *,
    lookback_days: int = 400,
    periods: int = 4,
) -> dict[str, Any]:
    end = date.today()
    start = end - timedelta(days=lookback_days)
    try:
        bars = bar_source.get_bars(symbol, start, end, freq="1d")
    except Exception:
        bars = pd.DataFrame()

    data_complete = True
    try:
        items = provider.financial_indicators(symbol)
        if items:
            persist_financials(db, symbol, items)
        else:
            data_complete = False
    except Exception:
        data_complete = False
        items = []
    if not items:
        items = load_persisted_financials(db, symbol)
        data_complete = False

    has_bars = bars is not None and not bars.empty
    if not has_bars and not items:
        raise DataUnavailable(f"no bars or financials for {symbol}")

    technical = _technical_features(bars) if has_bars else None
    return {
        "symbol": symbol,
        "technical": technical,
        "financials": [_fin_to_dict(it) for it in items[-periods:]],
        "data_complete": data_complete and has_bars,
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run --extra data --extra api pytest tests/test_company_agent_context.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add alphaagent/analytics/company_agent.py tests/test_company_agent_context.py
git commit -m "feat(analytics): assemble + persist lightweight company context"
```

---

## Task 3: LLM 分析层 company_analyst.py

**Files:** Create `alphaagent/agent/company_analyst.py`; Test `tests/test_company_analyst.py`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_company_analyst.py
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
    assert a.disclaimer  # non-empty


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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --extra data --extra api pytest tests/test_company_analyst.py -v`
Expected: FAIL (`ModuleNotFoundError: alphaagent.agent.company_analyst`).

- [ ] **Step 3: Implement** — create `alphaagent/agent/company_analyst.py`:

```python
"""LLM company analyst: technical + financial context -> BUY/HOLD/SELL view.

Uses the Anthropic Messages API with the system prompt prompt-cached. The
``anthropic`` SDK is imported lazily so the rest of the app runs without it;
a missing key/SDK surfaces as ``AgentNotConfigured`` for the API to translate
into a clean 400.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any

_DISCLAIMER = "本分析由 AI 基于有限公开数据自动生成,仅供研究参考,不构成投资建议。"

_RATING_MAP = {
    "买入": "BUY", "buy": "BUY", "持有": "HOLD", "hold": "HOLD",
    "卖出": "SELL", "sell": "SELL",
}

SYSTEM_PROMPT = (
    "你是一名严谨的 A 股研究分析师。你只会收到某只股票的有限数据:技术面"
    "(多窗口收益、回撤、波动率、均线趋势)和近几期财务摘要(ROE、利润率、"
    "营收/利润同比、负债率)。你看不到公司名称与行业,只有代码与这些数字。\n"
    "请基于这些数据给出综合判断,严格只输出一个 JSON 对象,字段:\n"
    '{"rating": "买入|持有|卖出", "confidence": 0到1的小数, '
    '"summary": "一句话结论", "reasons": ["看多/支撑点", ...], '
    '"risks": ["风险点", ...]}\n'
    "数据有限时降低 confidence 并在 risks 注明。不要输出 JSON 之外的任何文字。"
)


@dataclass
class CompanyAnalysis:
    rating: str  # BUY | HOLD | SELL | UNKNOWN
    summary: str
    reasons: list[str]
    risks: list[str]
    model: str
    confidence: float | None = None
    disclaimer: str = _DISCLAIMER


class AgentNotConfigured(RuntimeError):
    """anthropic SDK missing or ANTHROPIC_API_KEY not set."""


def _coerce_rating(raw: Any) -> str:
    s = str(raw or "").strip()
    return _RATING_MAP.get(s, _RATING_MAP.get(s.lower(), s.upper() if s.upper() in {"BUY", "HOLD", "SELL"} else "UNKNOWN"))


def _coerce_list(raw: Any) -> list[str]:
    if isinstance(raw, list):
        return [str(x) for x in raw]
    return []


def _parse_analysis(text: str, *, model: str) -> CompanyAnalysis:
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        try:
            obj = json.loads(text[start : end + 1])
            conf = obj.get("confidence")
            return CompanyAnalysis(
                rating=_coerce_rating(obj.get("rating")),
                summary=str(obj.get("summary") or ""),
                reasons=_coerce_list(obj.get("reasons")),
                risks=_coerce_list(obj.get("risks")),
                confidence=float(conf) if isinstance(conf, (int, float)) else None,
                model=model,
            )
        except (ValueError, TypeError):
            pass
    return CompanyAnalysis(
        rating="UNKNOWN", summary=text.strip()[:500], reasons=[], risks=[], model=model
    )


@dataclass
class CompanyAnalyst:
    model: str = "claude-sonnet-4-6"
    max_tokens: int = 1500
    client: Any = field(default=None, repr=False)

    def _ensure_client(self):
        if self.client is not None:
            return self.client
        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise AgentNotConfigured("未配置 ANTHROPIC_API_KEY")
        try:
            from anthropic import Anthropic
        except ImportError as e:
            raise AgentNotConfigured("anthropic 未安装(pip install alphaagent[agent])") from e
        self.client = Anthropic()
        return self.client

    def analyze(self, context: dict[str, Any]) -> CompanyAnalysis:
        client = self._ensure_client()
        resp = client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=[
                {
                    "type": "text",
                    "text": SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[
                {"role": "user", "content": json.dumps(context, ensure_ascii=False)}
            ],
        )
        text = "".join(
            getattr(b, "text", "") for b in resp.content if getattr(b, "type", "text") == "text"
        )
        return _parse_analysis(text, model=self.model)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run --extra data --extra api pytest tests/test_company_analyst.py -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add alphaagent/agent/company_analyst.py tests/test_company_analyst.py
git commit -m "feat(agent): CompanyAnalyst with JSON output + prompt caching"
```

---

## Task 4: API endpoint + DTO + deps

**Files:** Modify `alphaagent/api/schemas/analysis.py`, `alphaagent/api/deps.py`, `alphaagent/api/routers/analysis/company.py`; Test `tests/test_api_company_agent.py`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_api_company_agent.py
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from alphaagent.agent.company_analyst import AgentNotConfigured, CompanyAnalysis
from alphaagent.api.deps import get_company_analyst, get_fundamentals_provider, get_kline_data_source
from alphaagent.api.main import app
from alphaagent.data.base import DataSource
from alphaagent.fundamentals.base import FundamentalsProvider
from alphaagent.fundamentals.types import (
    FinancialIndicators, IndustryConstituent, IndustrySummary, MarketSnapshot, SecurityInfo,
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
    # persisted -> history
    h = client.get("/api/analysis/company/600000/agent/history").json()["data"]
    assert len(h) >= 1 and h[0]["symbol"] == "600000"


def test_agent_not_configured_returns_400(client):
    app.dependency_overrides[get_company_analyst] = lambda: _BrokenAnalyst()
    r = client.post("/api/analysis/company/600000/agent")
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "AGENT_NOT_CONFIGURED"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --extra data --extra api pytest tests/test_api_company_agent.py -v`
Expected: FAIL (`ImportError: cannot import name 'get_company_analyst'`).

- [ ] **Step 3a: Implement DTO** — append to `alphaagent/api/schemas/analysis.py`:

```python
class CompanyAnalysisDTO(BaseModel):
    symbol: str
    generated_at: str
    rating: str
    confidence: float | None = None
    summary: str
    reasons: list[str]
    risks: list[str]
    model: str
    disclaimer: str
    data_complete: bool | None = None
```

- [ ] **Step 3b: Implement dep** — append to `alphaagent/api/deps.py`:

```python
def get_company_analyst():
    """Company-analysis LLM agent. Overridable in tests via dependency_overrides."""
    import os

    from alphaagent.agent.company_analyst import CompanyAnalyst

    model = os.environ.get("ALPHAAGENT_AGENT_MODEL", "claude-sonnet-4-6")
    return CompanyAnalyst(model=model)
```

- [ ] **Step 3c: Implement endpoints** — append to `alphaagent/api/routers/analysis/company.py`. Add these imports near the top (match existing import style):

```python
import json
import uuid
from datetime import datetime

from alphaagent.agent.company_analyst import AgentNotConfigured, CompanyAnalysis
from alphaagent.analytics.company_agent import DataUnavailable, assemble_company_context
from alphaagent.api.deps import get_company_analyst
from alphaagent.api.schemas.analysis import CompanyAnalysisDTO
from alphaagent.data.sqlite_cache import SqliteBarCache
from alphaagent.storage.db import get_database
```

Then add the endpoints (use the existing `router`, `get_fundamentals_provider`, `get_kline_data_source`, `ok`, `err`, `HTTPException`, `Depends`, `Annotated` already imported in that file):

```python
def _persist_analysis(db, analysis_id, symbol, generated_at, a: CompanyAnalysis, context) -> None:
    db.execute(
        "INSERT OR REPLACE INTO company_analysis "
        "(id,symbol,generated_at,rating,confidence,summary,reasons_json,risks_json,model,context_json) "
        "VALUES (?,?,?,?,?,?,?,?,?,?)",
        (
            analysis_id, symbol, generated_at, a.rating, a.confidence, a.summary,
            json.dumps(a.reasons, ensure_ascii=False), json.dumps(a.risks, ensure_ascii=False),
            a.model, json.dumps(context, ensure_ascii=False),
        ),
    )


@router.post("/{symbol}/agent")
def company_agent_analysis(
    symbol: str,
    provider=Depends(get_fundamentals_provider),
    upstream=Depends(get_kline_data_source),
    analyst=Depends(get_company_analyst),
):
    db = get_database()
    bar_source = SqliteBarCache(upstream, db, "akshare_1d_qfq")
    try:
        context = assemble_company_context(symbol, bar_source, provider, db)
    except DataUnavailable as e:
        raise HTTPException(502, detail=err("DATA_UNAVAILABLE", str(e)))
    try:
        analysis = analyst.analyze(context)
    except AgentNotConfigured as e:
        raise HTTPException(400, detail=err("AGENT_NOT_CONFIGURED", str(e)))
    except Exception as e:  # noqa: BLE001
        raise HTTPException(502, detail=err("AGENT_FAILED", f"{type(e).__name__}: {e}"))

    generated_at = datetime.utcnow().isoformat()
    _persist_analysis(db, str(uuid.uuid4()), symbol, generated_at, analysis, context)
    return ok(
        CompanyAnalysisDTO(
            symbol=symbol, generated_at=generated_at, rating=analysis.rating,
            confidence=analysis.confidence, summary=analysis.summary, reasons=analysis.reasons,
            risks=analysis.risks, model=analysis.model, disclaimer=analysis.disclaimer,
            data_complete=context.get("data_complete"),
        ).model_dump(mode="json")
    )


@router.get("/{symbol}/agent/history")
def company_agent_history(symbol: str, limit: int = 10):
    db = get_database()
    rows = db.query(
        "SELECT * FROM company_analysis WHERE symbol=? ORDER BY generated_at DESC LIMIT ?",
        (symbol, limit),
    )
    out = [
        CompanyAnalysisDTO(
            symbol=r["symbol"], generated_at=r["generated_at"], rating=r["rating"],
            confidence=r["confidence"], summary=r["summary"] or "",
            reasons=json.loads(r["reasons_json"] or "[]"), risks=json.loads(r["risks_json"] or "[]"),
            model=r["model"] or "", disclaimer="",
        ).model_dump(mode="json")
        for r in rows
    ]
    return ok(out)
```

> Note: `_persist_analysis` takes the dict `context`; the INSERT has 10 columns / 10 placeholders. Double-check the placeholder count matches when implementing.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run --extra data --extra api pytest tests/test_api_company_agent.py -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Run the full backend suite + ruff**

Run: `uv run --extra data --extra api pytest -q -p no:warnings` → all pass.
Run: `uv run --extra dev ruff check alphaagent tests` → no NEW errors (pre-existing screener/pipeline ones may remain).

- [ ] **Step 6: Commit**

```bash
git add alphaagent/api/schemas/analysis.py alphaagent/api/deps.py alphaagent/api/routers/analysis/company.py tests/test_api_company_agent.py
git commit -m "feat(api): company agent analysis endpoint + history"
```

---

## Task 5: 前端「AI 智能分析」

**Files:** Modify `web/src/api/types.ts`, `web/src/api/analysis.ts`, `web/src/pages/analysis/company/Index.vue`.

READ first: `web/src/api/analysis.ts` (axios client + existing company methods), `web/src/pages/analysis/company/Index.vue` (page structure, where cards go), `web/src/api/types.ts`.

- [ ] **Step 1: Add types** — append to `web/src/api/types.ts`:

```typescript
export interface CompanyAnalysis {
  symbol: string
  generated_at: string
  rating: string            // BUY | HOLD | SELL | UNKNOWN
  confidence: number | null
  summary: string
  reasons: string[]
  risks: string[]
  model: string
  disclaimer: string
  data_complete: boolean | null
}
```

- [ ] **Step 2: Add api methods** — in `web/src/api/analysis.ts`, add to the `analysisApi` object (mirror existing method style; the http client unwraps the envelope):

```typescript
  agentAnalyze(symbol: string) {
    return http.post<CompanyAnalysis>(`/analysis/company/${symbol}/agent`).then(r => r.data)
  },
  agentHistory(symbol: string, limit = 10) {
    return http.get<CompanyAnalysis[]>(`/analysis/company/${symbol}/agent/history`, { params: { limit } }).then(r => r.data)
  },
```

(Import `CompanyAnalysis` from `./types` alongside the existing type imports.)

- [ ] **Step 3: Add the analysis card** — in `web/src/pages/analysis/company/Index.vue`, add a card after the KLine chart card. In `<script setup lang="ts">` add reactive state + handler:

```typescript
import { ref } from 'vue'
import { analysisApi } from '@/api/analysis'
import type { CompanyAnalysis } from '@/api/types'
import { ElMessage } from 'element-plus'

const agent = ref<CompanyAnalysis | null>(null)
const agentLoading = ref(false)

async function runAgent() {
  if (!symbol.value) return
  agentLoading.value = true
  try {
    agent.value = await analysisApi.agentAnalyze(symbol.value)
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.error?.message ?? 'AI 分析失败')
  } finally {
    agentLoading.value = false
  }
}

const ratingType = (r: string) =>
  ({ BUY: 'success', SELL: 'danger', HOLD: 'info' } as Record<string, string>)[r] ?? 'warning'
const ratingLabel = (r: string) =>
  ({ BUY: '买入', SELL: '卖出', HOLD: '持有', UNKNOWN: '数据不足' } as Record<string, string>)[r] ?? r
```

(Reuse the page's existing `symbol` ref — match its actual name in the file; if it differs, adapt.)

Template card:

```vue
<el-card class="mt-4">
  <template #header>
    <div class="flex items-center justify-between">
      <span>AI 智能分析</span>
      <el-button type="primary" :loading="agentLoading" @click="runAgent">运行分析</el-button>
    </div>
  </template>
  <el-empty v-if="!agent" description="点击「运行分析」让 AI 综合技术面与财务给出研判" />
  <div v-else>
    <div class="flex items-center gap-3 mb-3">
      <el-tag :type="ratingType(agent.rating)" size="large">{{ ratingLabel(agent.rating) }}</el-tag>
      <span v-if="agent.confidence != null">置信度 {{ Math.round(agent.confidence * 100) }}%</span>
      <el-tag v-if="agent.data_complete === false" type="warning" size="small">数据不完整</el-tag>
    </div>
    <p class="mb-3">{{ agent.summary }}</p>
    <el-row :gutter="16">
      <el-col :span="12">
        <strong>看多 / 支撑</strong>
        <ul><li v-for="(r, i) in agent.reasons" :key="i">{{ r }}</li></ul>
      </el-col>
      <el-col :span="12">
        <strong>风险点</strong>
        <ul><li v-for="(r, i) in agent.risks" :key="i">{{ r }}</li></ul>
      </el-col>
    </el-row>
    <el-alert :title="agent.disclaimer" type="info" :closable="false" class="mt-3" />
  </div>
</el-card>
```

- [ ] **Step 4: Build (type-check gate)**

Run: `cd web && npm run build`
Expected: passes (vue-tsc + vite), no type errors. Fix any type errors before committing. (Visual UX is verified by the user later.)

- [ ] **Step 5: Commit**

```bash
git add web/src/api/types.ts web/src/api/analysis.ts web/src/pages/analysis/company/Index.vue
git commit -m "feat(web): AI company analysis card on the company page"
```

---

## Self-Review

- **Spec coverage:** §3 tables→T1;§4 assemble/persist/fallback→T2;§5 CompanyAnalyst/parse/caching/AgentNotConfigured→T3;§6 DTO/deps/endpoints/errors→T4;§7 frontend→T5;§8 error handling→T2(DataUnavailable)+T3(degrade)+T4(400/502);§9 tests→each task's tests are LLM-free (parse tested directly; API uses StubAnalyst);§10 deps(anthropic lazy)→T3;§11 acceptance→T4 step5 (full suite) + T5 build.
- **Placeholders:** none — every step has complete code + exact commands.
- **Type consistency:** `CompanyAnalysis{rating,summary,reasons,risks,model,confidence,disclaimer}` consistent across T3/T4/T5; `CompanyAnalysisDTO` fields match; `assemble_company_context(symbol,bar_source,provider,db)` signature consistent T2↔T4; `_parse_analysis(text, *, model)` consistent; rating enum BUY/HOLD/SELL/UNKNOWN consistent; `get_company_analyst` defined T4 (deps) and overridden in T4 test.
- **Note for implementer:** T4's `_persist_analysis` INSERT lists 10 columns — verify 10 `?` placeholders (the plan's VALUES has 10). In T5, reuse the page's actual `symbol` ref name (read the file).
