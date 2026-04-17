"""Optional LLM agent layer.

The agent observes context (candidate universe, news, fundamentals) and
returns a structured decision that a strategy can consume. Disabled by
default; enable via ``agent.enabled: true`` in config.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentDecision:
    """Agent output. Open-ended; strategies interpret the payload."""

    action: str  # e.g. "select_universe", "adjust_params", "veto"
    payload: dict[str, Any] = field(default_factory=dict)
    reasoning: str = ""


class Agent(ABC):
    """Base class for LLM-backed agents."""

    @abstractmethod
    def decide(self, context: dict[str, Any]) -> AgentDecision: ...


class NullAgent(Agent):
    """No-op agent used when the agent layer is disabled."""

    def decide(self, context: dict[str, Any]) -> AgentDecision:
        return AgentDecision(action="noop")
