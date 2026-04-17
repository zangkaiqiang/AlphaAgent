"""Registry of built-in strategies.

Strategies are looked up by their config ``name``. To register a custom
strategy, call ``register("my_name", MyStrategy)`` or add it to
``BUILTIN_STRATEGIES`` below.
"""

from __future__ import annotations

from alphaagent.strategy.base import Strategy
from alphaagent.strategy.bollinger import BollingerBreakout, BollingerReversion
from alphaagent.strategy.ma_cross import MACrossStrategy
from alphaagent.strategy.momentum import CrossSectionalMomentum
from alphaagent.strategy.rsi import RSIMeanReversion

BUILTIN_STRATEGIES: dict[str, type[Strategy]] = {
    "ma_cross": MACrossStrategy,
    "rsi_mean_reversion": RSIMeanReversion,
    "bollinger_breakout": BollingerBreakout,
    "bollinger_reversion": BollingerReversion,
    "xs_momentum": CrossSectionalMomentum,
}


def register(name: str, cls: type[Strategy]) -> None:
    if name in BUILTIN_STRATEGIES:
        raise ValueError(f"strategy {name!r} already registered")
    BUILTIN_STRATEGIES[name] = cls


def get(name: str) -> type[Strategy]:
    try:
        return BUILTIN_STRATEGIES[name]
    except KeyError as e:
        available = ", ".join(sorted(BUILTIN_STRATEGIES))
        raise ValueError(
            f"unknown strategy: {name!r}. available: {available}"
        ) from e
