"""Cross-sectional momentum: hold the top-N strongest-performing symbols.

On each new timestamp we rank every symbol by its return over the past
``lookback`` bars. Every ``rebalance_days`` timestamps the held set is
rotated to the current top-N, selling drops and buying new entrants.

Unlike single-symbol trend strategies (MA Cross, Bollinger), this one
operates on a *universe* and produces signals through relative ranking.
"""

from __future__ import annotations

from collections import defaultdict, deque
from datetime import datetime

from alphaagent.core.types import Bar, Side
from alphaagent.strategy.base import Strategy


class CrossSectionalMomentum(Strategy):
    strategy_id = "xs_momentum"

    def __init__(
        self,
        lookback: int = 60,
        top_n: int = 3,
        rebalance_days: int = 20,
        strategy_id: str | None = None,
    ):
        super().__init__(strategy_id=strategy_id)
        if lookback < 2:
            raise ValueError("lookback must be >= 2")
        if top_n < 1:
            raise ValueError("top_n must be >= 1")
        if rebalance_days < 1:
            raise ValueError("rebalance_days must be >= 1")
        self.lookback = lookback
        self.top_n = top_n
        self.rebalance_days = rebalance_days
        self._prices: dict[str, deque[float]] = defaultdict(
            lambda: deque(maxlen=lookback)
        )
        self._latest_bar: dict[str, Bar] = {}
        self._last_ts: datetime | None = None
        self._days_since_rebalance: int = 0
        self._held: set[str] = set()

    def on_bar(self, bar: Bar) -> None:
        assert self.ctx is not None
        if self._last_ts is not None and bar.timestamp != self._last_ts:
            self._days_since_rebalance += 1
            if self._days_since_rebalance >= self.rebalance_days:
                self._rebalance()
        self._last_ts = bar.timestamp
        self._prices[bar.symbol].append(bar.close)
        self._latest_bar[bar.symbol] = bar

    def _rebalance(self) -> None:
        assert self.ctx is not None
        ranked: list[tuple[str, float]] = []
        for sym, prices in self._prices.items():
            if len(prices) < self.lookback:
                continue
            prices_list = list(prices)
            if prices_list[0] <= 0:
                continue
            ranked.append((sym, prices_list[-1] / prices_list[0] - 1))
        if not ranked:
            return
        ranked.sort(key=lambda r: r[1], reverse=True)
        top = {s for s, _ in ranked[: self.top_n]}

        for sym in self._held - top:
            bar = self._latest_bar.get(sym)
            if bar is not None:
                self.ctx.emit_signal(bar, Side.SELL)
        for sym in top - self._held:
            bar = self._latest_bar.get(sym)
            if bar is not None:
                self.ctx.emit_signal(bar, Side.BUY)

        self._held = top
        self._days_since_rebalance = 0
