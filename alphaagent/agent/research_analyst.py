"""Agentic research analyst: gathers technical/financial/news data via tool
calls, then asks the model to submit a cited ResearchReport.

The tool loop uses the Anthropic Messages API with a prompt-cached system
prompt.  A fake client (any object with .messages.create(**kw)) can be injected
for testing without touching the network.
"""

from __future__ import annotations

import contextlib
import json
import os
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

from alphaagent.agent.company_analyst import AgentNotConfigured
from alphaagent.agent.report import ResearchReport, SourceRegistry, assemble_report
from alphaagent.analytics.company_agent import _technical_features, persist_financials

# ---------------------------------------------------------------------------
# Tool schemas (Anthropic tool-use format)
# ---------------------------------------------------------------------------

TOOLS: list[dict[str, Any]] = [
    {
        "name": "get_technical",
        "description": "获取股票技术面特征（价格、均线、波动率、回撤等）。",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "get_financials",
        "description": "获取并持久化股票财务指标（ROE、净利率、毛利率、营收同比等）。",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "get_news",
        "description": "获取股票相关新闻资讯。",
        "input_schema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "最多返回条数，默认10"}
            },
            "required": [],
        },
    },
    {
        "name": "submit_report",
        "description": (
            "完成数据收集后调用此工具提交研究报告。"
            "rating 取值：买入/持有/卖出；confidence 为0到1的小数；"
            "sections 为章节列表；cited_source_ids 为引用的来源 id 列表。"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "rating": {"type": "string", "description": "买入|持有|卖出"},
                "confidence": {"type": "number"},
                "sections": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "body": {"type": "string"},
                        },
                        "required": ["title", "body"],
                    },
                },
                "cited_source_ids": {
                    "type": "array",
                    "items": {"type": "integer"},
                },
            },
            "required": ["rating", "confidence", "sections", "cited_source_ids"],
        },
    },
]

# ---------------------------------------------------------------------------
# System prompt (will be prompt-cached)
# ---------------------------------------------------------------------------

_SYSTEM_TEXT = (
    "你是一名专业的 A 股研究分析师。通过调用工具依次获取技术面、财务面和资讯数据，"
    "然后生成有引用来源的研究报告。\n\n"
    "工作流程：\n"
    "1. 调用 get_technical 获取技术指标；\n"
    "2. 调用 get_financials 获取财务指标；\n"
    "3. 调用 get_news 获取新闻资讯；\n"
    "4. 综合以上数据，调用 submit_report 提交完整报告。\n\n"
    "引用规则：每条数据来源都有唯一 id，在报告正文中用 [id] 标注引用。"
    "cited_source_ids 必须包含正文中引用的所有 id。\n"
    "数据不完整时降低 confidence，并在 sections 中注明数据局限性。"
)


# ---------------------------------------------------------------------------
# Main analyst dataclass
# ---------------------------------------------------------------------------


@dataclass
class ResearchAnalyst:
    model: str = "claude-sonnet-4-6"
    max_tool_rounds: int = 6
    max_tokens: int = 2000
    client: Any = field(default=None, repr=False)

    # Lazily built real Anthropic client (cached on instance)
    _real_client: Any = field(default=None, repr=False, init=False)

    def _ensure_client(self) -> Any:
        """Return the injected client, or build a real Anthropic one."""
        if self.client is not None:
            return self.client
        if self._real_client is not None:
            return self._real_client
        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise AgentNotConfigured("未配置 ANTHROPIC_API_KEY")
        try:
            from anthropic import Anthropic
        except ImportError as exc:
            raise AgentNotConfigured(
                "anthropic 未安装 (pip install alphaagent[api])"
            ) from exc
        self._real_client = Anthropic()
        return self._real_client

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def analyze(
        self,
        symbol: str,
        *,
        bar_source: Any,
        provider: Any,
        news_provider: Any,
        db: Any,
    ) -> ResearchReport:
        client = self._ensure_client()  # raises AgentNotConfigured if not ready

        reg = SourceRegistry()
        state: dict[str, Any] = {
            "had_data": False,
            "news_unavailable": False,
            "technical_feats": None,
            "financial_rows": [],
        }

        # Build date range for bar retrieval
        end_date = datetime.now(UTC).date()
        start_date = end_date - timedelta(days=400)

        # -----------------------------------------------------------------
        # Tool implementations
        # -----------------------------------------------------------------

        def _t_technical() -> dict[str, Any]:
            try:
                bars = bar_source.get_bars(symbol, start_date, end_date, freq="1d")
            except Exception:
                bars = None
            if bars is None or (hasattr(bars, "empty") and bars.empty):
                return {"technical": None, "note": "技术数据不可用", "sources": []}
            feats = _technical_features(bars)
            state["technical_feats"] = feats
            state["had_data"] = True
            sources_out: list[dict[str, Any]] = []
            for k, v in list(feats.items())[:6]:  # register a few key metrics
                sid = reg.add("technical", f"{k}={v}", {"key": k, "value": v})
                sources_out.append({"id": sid, "label": f"{k}={v}"})
            return {"technical": feats, "sources": sources_out}

        def _t_financials() -> dict[str, Any]:
            try:
                items = provider.financial_indicators(symbol)
            except Exception:
                items = []
            if items:
                with contextlib.suppress(Exception):
                    persist_financials(db, symbol, items)
            sources_out: list[dict[str, Any]] = []
            fin_rows: list[dict[str, Any]] = []
            for it in items:
                period = str(it.period)
                metrics = {
                    "ROE": it.roe,
                    "净利率": it.net_margin,
                    "毛利率": it.gross_margin,
                    "营收同比": it.revenue_yoy,
                    "净利润同比": it.net_income_yoy,
                }
                for metric, value in metrics.items():
                    if value is None:
                        continue
                    label = f"{period} {metric} {round(float(value), 4)}"
                    sid = reg.add(
                        "financial", label,
                        {"period": period, "metric": metric, "value": value},
                    )
                    sources_out.append({"id": sid, "label": label})
                fin_rows.append({"period": period, "roe": it.roe,
                                 "net_margin": it.net_margin, "revenue_yoy": it.revenue_yoy})
                state["had_data"] = True
            state["financial_rows"] = fin_rows
            return {"financials": fin_rows, "sources": sources_out}

        def _t_news(limit: int = 10) -> dict[str, Any]:
            try:
                news_items = news_provider.recent_news(symbol, limit)
            except Exception:
                state["news_unavailable"] = True
                return {"news": [], "note": "资讯暂不可用"}
            if not news_items:
                state["news_unavailable"] = True
                return {"news": [], "note": "资讯暂不可用"}
            sources_out: list[dict[str, Any]] = []
            news_out: list[dict[str, Any]] = []
            now_str = datetime.now(UTC).isoformat()
            for i, item in enumerate(news_items):
                # Persist to news table
                url_key = item.url if item.url else f"{symbol}#{i}"
                with contextlib.suppress(Exception):
                    db.execute(
                        "INSERT OR REPLACE INTO news "
                        "(symbol, url, title, date, source, summary, fetched_at) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (symbol, url_key, item.title, item.date,
                         item.source, item.summary, now_str),
                    )
                # Register source
                sid = reg.add(
                    "news", item.title or url_key,
                    {"title": item.title, "date": item.date,
                     "source": item.source, "url": item.url},
                )
                sources_out.append({"id": sid, "label": item.title or url_key})
                news_out.append({"title": item.title, "date": item.date, "url": item.url})
            return {"news": news_out, "sources": sources_out}

        # -----------------------------------------------------------------
        # Tool dispatch map
        # -----------------------------------------------------------------

        _tool_dispatch = {
            "get_technical": lambda inp: _t_technical(),
            "get_financials": lambda inp: _t_financials(),
            "get_news": lambda inp: _t_news(limit=int(inp.get("limit", 10))),
        }

        # -----------------------------------------------------------------
        # System prompt with prompt caching marker
        # -----------------------------------------------------------------

        system = [
            {
                "type": "text",
                "text": _SYSTEM_TEXT,
                "cache_control": {"type": "ephemeral"},
            }
        ]

        # -----------------------------------------------------------------
        # Agentic tool-use loop
        # -----------------------------------------------------------------

        messages: list[dict[str, Any]] = [
            {"role": "user", "content": f"分析股票 {symbol}"}
        ]

        for _round in range(self.max_tool_rounds):
            resp = client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                system=system,
                tools=TOOLS,
                messages=messages,
            )

            # Collect tool_use blocks (works for both SDK objects and SimpleNamespace)
            tool_blocks = [
                blk for blk in resp.content
                if getattr(blk, "type", None) == "tool_use"
            ]

            if not tool_blocks:
                # Model stopped without calling tools — fall through to degraded
                break

            # Append assistant turn (resp.content is the raw list from the client)
            messages.append({"role": "assistant", "content": resp.content})

            # Process each tool block
            tool_results: list[dict[str, Any]] = []
            for blk in tool_blocks:
                name = getattr(blk, "name", "")
                inp = getattr(blk, "input", {}) or {}
                bid = getattr(blk, "id", "")

                # Handle submit_report: assemble and return immediately
                if name == "submit_report":
                    report = assemble_report(
                        symbol=symbol,
                        generated_at=datetime.now(UTC).isoformat(),
                        rating=inp.get("rating"),
                        confidence=inp.get("confidence"),
                        sections=inp.get("sections") or [],
                        cited_source_ids=inp.get("cited_source_ids") or [],
                        registry=reg,
                        model=self.model,
                        data_complete=(state["had_data"] and not state["news_unavailable"]),
                        notes=(["资讯暂不可用"] if state["news_unavailable"] else []),
                    )
                    return report

                # Execute the tool
                if name in _tool_dispatch:
                    try:
                        result = _tool_dispatch[name](inp)
                    except Exception as exc:
                        result = {"error": str(exc)}
                else:
                    result = {"error": f"unknown tool: {name}"}

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": bid,
                    "content": json.dumps(result, ensure_ascii=False),
                })

            # Append tool results as user turn
            messages.append({"role": "user", "content": tool_results})

        # -----------------------------------------------------------------
        # Degraded report: model never called submit_report
        # -----------------------------------------------------------------

        all_sources = reg.all()
        notes = ["未能生成完整报告"]
        if state["news_unavailable"]:
            notes.append("资讯暂不可用")

        # Build a brief data summary section from gathered sources
        if all_sources:
            summary_lines = [f"[{s.id}] {s.label}" for s in all_sources[:10]]
            body = "已收集的数据摘要：\n" + "\n".join(summary_lines)
        else:
            body = "未能收集到有效数据。"

        return assemble_report(
            symbol=symbol,
            generated_at=datetime.now(UTC).isoformat(),
            rating="UNKNOWN",
            confidence=None,
            sections=[{"title": "数据小结", "body": body}],
            cited_source_ids=[s.id for s in all_sources],
            registry=reg,
            model=self.model,
            data_complete=False,
            notes=notes,
        )


__all__ = ["ResearchAnalyst", "AgentNotConfigured", "TOOLS"]
