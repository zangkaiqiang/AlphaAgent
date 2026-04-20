"""Scoring rule interfaces.

Two distinct kinds:

- ``AbsoluteRule`` evaluates each symbol independently; output is a
  pre-normalized score in [0, 1]. Examples: ``above_ma``, ``price_breakout``,
  ``volume_breakout``.
- ``CrossSectionalRule`` requires the whole panel to compute relative
  rankings. Output is per-symbol score in [0, 1] derived from the rank.
  Examples: ``momentum``, ``reversal``, ``low_volatility``.

Both produce ``Reason`` objects (rule name, score, raw detail).
"""

from __future__ import annotations

from abc import ABC, abstractmethod

import pandas as pd

from alphaagent.screener.base import Reason


class AbsoluteRule(ABC):
    name: str
    weight: float = 1.0

    @abstractmethod
    def evaluate(self, bars: pd.DataFrame) -> Reason | None:
        """Return None if data is insufficient (rule excluded for this symbol)."""
        ...


class CrossSectionalRule(ABC):
    name: str
    weight: float = 1.0

    @abstractmethod
    def evaluate_all(self, panel: dict[str, pd.DataFrame]) -> dict[str, Reason]:
        """Return ``{symbol: Reason}``. Symbols with insufficient data are omitted."""
        ...


def percentile_rank(values: dict[str, float], reverse: bool = False) -> dict[str, float]:
    """Map raw values to [0, 1] via rank percentile.

    ``reverse=False``: highest value → score 1.0.
    ``reverse=True``: lowest value → score 1.0.
    Single-value input returns 0.5 (no relative info).
    """
    if not values:
        return {}
    if len(values) == 1:
        return {next(iter(values)): 0.5}
    sorted_items = sorted(values.items(), key=lambda kv: kv[1], reverse=not reverse)
    n = len(sorted_items)
    return {sym: (n - 1 - rank) / (n - 1) for rank, (sym, _) in enumerate(sorted_items)}
