"""Core types for the stock screener.

The screener is an offline batch workflow: take a universe of symbols,
score each one, and produce a ranked candidate list (`ScreenResult`)
that a human reviews before feeding it into a backtest.

This module only defines data containers; abstractions for universe,
metadata, rules, filters and pipeline live in their own modules.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass
class Reason:
    """Per-rule scoring result for a single symbol."""

    rule_name: str
    score: float                     # normalized to [0, 1]
    detail: dict[str, float | int | str | bool] = field(default_factory=dict)


@dataclass
class Pick:
    """A scored candidate symbol."""

    symbol: str
    name: str | None
    final_score: float
    reasons: list[Reason] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


@dataclass
class ScreenResult:
    """Full output of a screener run."""

    generated_at: date
    resolved_as_of: date
    universe_name: str
    universe_size: int
    filtered_size: int
    rules_applied: list[str]                  # "<name> (weight=X.XX)"
    universe_snapshot: list[str]              # full pre-filter symbol list (for --replay)
    picks: list[Pick]                         # already sorted by final_score desc

    def top(self, n: int) -> list[Pick]:
        return self.picks[:n]
