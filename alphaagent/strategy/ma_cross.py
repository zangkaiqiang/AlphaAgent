"""Moving-average crossover: buy when fast MA crosses above slow MA, sell on reverse."""

from __future__ import annotations

from collections import defaultdict, deque

from alphaagent.core.types import Bar, Side
from alphaagent.strategy.base import Strategy


class MACrossStrategy(Strategy):
    strategy_id = "ma_cross"

    def __init__(
        self,
        fast: int = 5,
        slow: int = 20,
        strategy_id: str | None = None,
    ):
        super().__init__(strategy_id=strategy_id)
        if fast >= slow:
            raise ValueError("fast must be < slow")
        self.fast = fast
        self.slow = slow
        self._windows: dict[str, deque[float]] = defaultdict(lambda: deque(maxlen=slow))
        self._prev_diff: dict[str, float] = {}

    def on_bar(self, bar: Bar) -> None:
        assert self.ctx is not None
        window = self._windows[bar.symbol]
        window.append(bar.close)
        if len(window) < self.slow:
            return

        prices = list(window)
        fast_ma = sum(prices[-self.fast :]) / self.fast
        slow_ma = sum(prices) / self.slow
        diff = fast_ma - slow_ma
        prev = self._prev_diff.get(bar.symbol)
        self._prev_diff[bar.symbol] = diff

        if prev is None:
            return
        if prev <= 0 < diff:
            self.ctx.emit_signal(bar, Side.BUY, strength=1.0)
        elif prev >= 0 > diff:
            self.ctx.emit_signal(bar, Side.SELL, strength=1.0)
