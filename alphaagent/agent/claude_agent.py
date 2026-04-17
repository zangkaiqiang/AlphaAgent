"""Claude-backed agent. Lazy-imports anthropic so it is optional."""

from __future__ import annotations

import json
from typing import Any

from alphaagent.agent.base import Agent, AgentDecision

DEFAULT_SYSTEM_PROMPT = (
    "You are a quantitative trading assistant for Chinese A-share markets. "
    "Given market context, respond with a JSON object containing: "
    '{"action": str, "payload": object, "reasoning": str}. '
    "Be concise, deterministic, and risk-aware."
)


class ClaudeAgent(Agent):
    def __init__(
        self,
        model: str = "claude-sonnet-4-6",
        system_prompt: str = DEFAULT_SYSTEM_PROMPT,
        max_tokens: int = 1024,
    ):
        self.model = model
        self.system_prompt = system_prompt
        self.max_tokens = max_tokens

    def decide(self, context: dict[str, Any]) -> AgentDecision:
        from anthropic import Anthropic

        client = Anthropic()
        message = client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=self.system_prompt,
            messages=[
                {"role": "user", "content": json.dumps(context, ensure_ascii=False)},
            ],
        )
        text = "".join(
            block.text for block in message.content if getattr(block, "type", "") == "text"
        )
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return AgentDecision(action="noop", reasoning=text)
        return AgentDecision(
            action=data.get("action", "noop"),
            payload=data.get("payload", {}),
            reasoning=data.get("reasoning", ""),
        )
