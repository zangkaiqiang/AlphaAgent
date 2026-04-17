"""Bollinger Bands strategies.

Both share the same indicator (MA ± k·σ over ``period`` bars) but express
opposite philosophies:

- ``BollingerBreakout``: price breaking above the upper band is momentum;
  buy the breakout, exit when price falls back through the middle band.
- ``BollingerReversion``: price below the lower band is oversold; buy the
  dip, exit when price revisits the middle band.

A simple long/flat state per symbol prevents repeated signals while the
price sits outside the bands.
"""

from __future__ import annotations

import math
from collections import defaultdict, deque
from typing import Literal

from alphaagent.core.types import Bar, Side
from alphaagent.strategy.base import Strategy


def _band(prices: list[float], k: float) -> tuple[float, float, float]:
    n = len(prices)
    mid = sum(prices) / n
    var = sum((p - mid) ** 2 for p in prices) / n
    std = math.sqrt(var)
    return mid - k * std, mid, mid + k * std


State = Literal["flat", "long"]


class _BollingerBase(Strategy):
    def __init__(
        self,
        period: int = 20,
        k: float = 2.0,
        strategy_id: str | None = None,
    ):
        super().__init__(strategy_id=strategy_id)
        if period < 2:
            raise ValueError("period must be >= 2")
        if k <= 0:
            raise ValueError("k must be > 0")
        self.period = period
        self.k = k
        self._prices: dict[str, deque[float]] = defaultdict(
            lambda: deque(maxlen=period)
        )
        self._state: dict[str, State] = defaultdict(lambda: "flat")


class BollingerBreakout(_BollingerBase):
    strategy_id = "bollinger_breakout"

    def on_bar(self, bar: Bar) -> None:
        assert self.ctx is not None
        window = self._prices[bar.symbol]
        window.append(bar.close)
        if len(window) < self.period:
            return
        lower, mid, upper = _band(list(window), self.k)
        state = self._state[bar.symbol]
        if state == "flat" and bar.close > upper:
            self.ctx.emit_signal(bar, Side.BUY)
            self._state[bar.symbol] = "long"
        elif state == "long" and bar.close < mid:
            self.ctx.emit_signal(bar, Side.SELL)
            self._state[bar.symbol] = "flat"


class BollingerReversion(_BollingerBase):
    strategy_id = "bollinger_reversion"

    def on_bar(self, bar: Bar) -> None:
        assert self.ctx is not None
        window = self._prices[bar.symbol]
        window.append(bar.close)
        if len(window) < self.period:
            return
        lower, mid, upper = _band(list(window), self.k)
        state = self._state[bar.symbol]
        if state == "flat" and bar.close < lower:
            self.ctx.emit_signal(bar, Side.BUY)
            self._state[bar.symbol] = "long"
        elif state == "long" and bar.close > mid:
            self.ctx.emit_signal(bar, Side.SELL)
            self._state[bar.symbol] = "flat"
