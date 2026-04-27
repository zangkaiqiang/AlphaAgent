"""Built-in scoring rules.

Three absolute (per-symbol): ``above_ma``, ``price_breakout``, ``volume_breakout``.
Three cross-sectional (rank-based): ``momentum``, ``reversal``, ``low_volatility``.
"""

from __future__ import annotations

import math

import pandas as pd

from alphaagent.screener.base import Reason
from alphaagent.screener.rules import (
    AbsoluteRule,
    CrossSectionalRule,
    percentile_rank,
)

# ──────────────────────────────────────────────────────────────────────────────
# Absolute rules
# ──────────────────────────────────────────────────────────────────────────────


class AboveMA(AbsoluteRule):
    """Latest close above a simple moving average — continuous score.

    ``score = clip((close / ma - 1) / score_scale, 0, 1)``.
    The default ``score_scale=0.10`` means "10% above MA = full score".
    Prior binary 0/1 scoring wasted cross-symbol information; a stock
    15% above its MA and one 0.1% above should not tie.
    """

    name = "above_ma"

    def __init__(
        self, period: int = 60, weight: float = 1.0, score_scale: float = 0.10
    ):
        if period < 2:
            raise ValueError("period must be >= 2")
        if score_scale <= 0:
            raise ValueError("score_scale must be > 0")
        self.period = period
        self.weight = weight
        self.score_scale = score_scale

    def evaluate(self, bars: pd.DataFrame) -> Reason | None:
        if len(bars) < self.period:
            return None
        close = float(bars["close"].iloc[-1])
        ma = float(bars["close"].tail(self.period).mean())
        if ma <= 0:
            return None
        excess = close / ma - 1.0
        score = max(0.0, min(1.0, excess / self.score_scale))
        return Reason(
            rule_name=self.name,
            score=score,
            detail={"close": round(close, 4), f"ma{self.period}": round(ma, 4)},
        )


class PriceBreakout(AbsoluteRule):
    """Latest close above the prior-N-bar max — continuous score.

    ``score = clip((close / prior_max - 1) / score_scale, 0, 1)``.
    """

    name = "price_breakout"

    def __init__(
        self, lookback: int = 60, weight: float = 1.0, score_scale: float = 0.10
    ):
        if lookback < 2:
            raise ValueError("lookback must be >= 2")
        if score_scale <= 0:
            raise ValueError("score_scale must be > 0")
        self.lookback = lookback
        self.weight = weight
        self.score_scale = score_scale

    def evaluate(self, bars: pd.DataFrame) -> Reason | None:
        if len(bars) < self.lookback + 1:
            return None
        close = float(bars["close"].iloc[-1])
        prior_max = float(bars["close"].iloc[-(self.lookback + 1) : -1].max())
        if prior_max <= 0:
            return None
        excess = close / prior_max - 1.0
        score = max(0.0, min(1.0, excess / self.score_scale))
        return Reason(
            rule_name=self.name,
            score=score,
            detail={"close": round(close, 4), "prior_max": round(prior_max, 4)},
        )


class VolumeBreakout(AbsoluteRule):
    """Latest day's amount z-score (relative to prior N bars).

    Uses ``amount`` (turnover, CNY) not ``volume`` (shares) — share count
    jumps after splits/rights issues, amount is invariant.

    Score: 1.0 if z >= threshold, else linearly scales 0..1 over [0, threshold].
    Negative z scores 0.
    """

    name = "volume_breakout"

    def __init__(
        self, lookback: int = 20, z_threshold: float = 1.5, weight: float = 1.0
    ):
        if lookback < 2:
            raise ValueError("lookback must be >= 2")
        if z_threshold <= 0:
            raise ValueError("z_threshold must be > 0")
        self.lookback = lookback
        self.z_threshold = z_threshold
        self.weight = weight

    def evaluate(self, bars: pd.DataFrame) -> Reason | None:
        if "amount" not in bars.columns or len(bars) < self.lookback + 1:
            return None
        amount = bars["amount"].astype(float)
        prior = amount.iloc[-(self.lookback + 1) : -1]
        std = float(prior.std(ddof=0))
        mean = float(prior.mean())
        if std == 0 or math.isnan(std):
            return None
        z = (float(amount.iloc[-1]) - mean) / std
        if z <= 0:
            score = 0.0
        elif z >= self.z_threshold:
            score = 1.0
        else:
            score = z / self.z_threshold
        return Reason(
            rule_name=self.name,
            score=score,
            detail={"amount_z": round(z, 3), "threshold": self.z_threshold},
        )


# ──────────────────────────────────────────────────────────────────────────────
# Cross-sectional rules
# ──────────────────────────────────────────────────────────────────────────────


class Momentum(CrossSectionalRule):
    """Past N-day return, ranked across the universe (higher = better)."""

    name = "momentum"

    def __init__(self, lookback: int = 60, weight: float = 1.0):
        if lookback < 2:
            raise ValueError("lookback must be >= 2")
        self.lookback = lookback
        self.weight = weight

    def evaluate_all(self, panel: dict[str, pd.DataFrame]) -> dict[str, Reason]:
        raw: dict[str, float] = {}
        for sym, bars in panel.items():
            if len(bars) < self.lookback:
                continue
            old = float(bars["close"].iloc[-self.lookback])
            new = float(bars["close"].iloc[-1])
            if old <= 0:
                continue
            raw[sym] = new / old - 1.0
        scores = percentile_rank(raw, reverse=False)
        return {
            sym: Reason(
                rule_name=self.name,
                score=score,
                detail={f"return_{self.lookback}d": round(raw[sym], 4)},
            )
            for sym, score in scores.items()
        }


class Reversal(CrossSectionalRule):
    """Past N-day return, ranked inversely (more negative = higher score)."""

    name = "reversal"

    def __init__(self, lookback: int = 20, weight: float = 1.0):
        if lookback < 2:
            raise ValueError("lookback must be >= 2")
        self.lookback = lookback
        self.weight = weight

    def evaluate_all(self, panel: dict[str, pd.DataFrame]) -> dict[str, Reason]:
        raw: dict[str, float] = {}
        for sym, bars in panel.items():
            if len(bars) < self.lookback:
                continue
            old = float(bars["close"].iloc[-self.lookback])
            new = float(bars["close"].iloc[-1])
            if old <= 0:
                continue
            raw[sym] = new / old - 1.0
        scores = percentile_rank(raw, reverse=True)
        return {
            sym: Reason(
                rule_name=self.name,
                score=score,
                detail={f"return_{self.lookback}d": round(raw[sym], 4)},
            )
            for sym, score in scores.items()
        }


class LowVolatility(CrossSectionalRule):
    """Stdev of daily returns over N bars, ranked inversely (lower = better)."""

    name = "low_volatility"

    def __init__(self, lookback: int = 20, weight: float = 1.0):
        if lookback < 3:
            raise ValueError("lookback must be >= 3")
        self.lookback = lookback
        self.weight = weight

    def evaluate_all(self, panel: dict[str, pd.DataFrame]) -> dict[str, Reason]:
        raw: dict[str, float] = {}
        for sym, bars in panel.items():
            if len(bars) < self.lookback + 1:
                continue
            close = bars["close"].astype(float).tail(self.lookback + 1)
            returns = close.pct_change().dropna()
            if len(returns) < self.lookback:
                continue
            std = float(returns.std(ddof=0))
            if math.isnan(std):
                continue
            raw[sym] = std
        scores = percentile_rank(raw, reverse=True)
        return {
            sym: Reason(
                rule_name=self.name,
                score=score,
                detail={f"vol_{self.lookback}d": round(raw[sym], 5)},
            )
            for sym, score in scores.items()
        }


# ──────────────────────────────────────────────────────────────────────────────
# Registry
# ──────────────────────────────────────────────────────────────────────────────

BUILTIN_ABSOLUTE_RULES: dict[str, type[AbsoluteRule]] = {
    "above_ma": AboveMA,
    "price_breakout": PriceBreakout,
    "volume_breakout": VolumeBreakout,
}

BUILTIN_XS_RULES: dict[str, type[CrossSectionalRule]] = {
    "momentum": Momentum,
    "reversal": Reversal,
    "low_volatility": LowVolatility,
}


def build_rule(spec: dict) -> AbsoluteRule | CrossSectionalRule:
    """Build a rule from a config dict.

    The dict shape is ``{"type": <rule_name>, "weight": float, ...params}``.
    """
    spec = dict(spec)
    rule_type = spec.pop("type")
    if rule_type in BUILTIN_ABSOLUTE_RULES:
        return BUILTIN_ABSOLUTE_RULES[rule_type](**spec)
    if rule_type in BUILTIN_XS_RULES:
        return BUILTIN_XS_RULES[rule_type](**spec)
    available = ", ".join(
        sorted(set(BUILTIN_ABSOLUTE_RULES) | set(BUILTIN_XS_RULES))
    )
    raise ValueError(f"unknown rule: {rule_type!r}. available: {available}")


def split_rules(
    rules: list[AbsoluteRule | CrossSectionalRule],
) -> tuple[list[AbsoluteRule], list[CrossSectionalRule]]:
    abs_rules: list[AbsoluteRule] = []
    xs_rules: list[CrossSectionalRule] = []
    for r in rules:
        if isinstance(r, AbsoluteRule):
            abs_rules.append(r)
        elif isinstance(r, CrossSectionalRule):
            xs_rules.append(r)
        else:
            raise TypeError(f"unexpected rule type: {type(r).__name__}")
    return abs_rules, xs_rules
