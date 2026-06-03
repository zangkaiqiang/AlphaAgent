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
    if s in _RATING_MAP:
        return _RATING_MAP[s]
    if s.lower() in _RATING_MAP:
        return _RATING_MAP[s.lower()]
    return s.upper() if s.upper() in {"BUY", "HOLD", "SELL"} else "UNKNOWN"


def _coerce_list(raw: Any) -> list[str]:
    return [str(x) for x in raw] if isinstance(raw, list) else []


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
                {"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}
            ],
            messages=[{"role": "user", "content": json.dumps(context, ensure_ascii=False)}],
        )
        text = "".join(
            getattr(b, "text", "") for b in resp.content if getattr(b, "type", "text") == "text"
        )
        return _parse_analysis(text, model=self.model)
