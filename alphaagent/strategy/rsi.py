"""RSI mean-reversion strategy.

Buys when RSI crosses up out of the oversold zone; sells when RSI crosses
down out of the overbought zone. Using "exit the zone" transitions rather
than "enter the zone" avoids repeated signals while RSI stays extreme.
"""

from __future__ import annotations

from collections import defaultdict, deque

from alphaagent.core.types import Bar, Side
from alphaagent.strategy.base import Strategy


def _rsi_from_prices(prices: list[float]) -> float:
    """Classic Wilder-style RSI over a simple average (no smoothing)."""
    gains = 0.0
    losses = 0.0
    for prev, cur in zip(prices, prices[1:], strict=False):
        delta = cur - prev
        if delta >= 0:
            gains += delta
        else:
            losses -= delta
    n = len(prices) - 1
    avg_gain = gains / n
    avg_loss = losses / n
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - 100.0 / (1.0 + rs)


class RSIMeanReversion(Strategy):
    strategy_id = "rsi_mean_reversion"

    def __init__(
        self,
        period: int = 14,
        oversold: float = 30.0,
        overbought: float = 70.0,
        strategy_id: str | None = None,
    ):
        super().__init__(strategy_id=strategy_id)
        if period < 2:
            raise ValueError("period must be >= 2")
        if not 0 < oversold < overbought < 100:
            raise ValueError("need 0 < oversold < overbought < 100")
        self.period = period
        self.oversold = oversold
        self.overbought = overbought
        self._prices: dict[str, deque[float]] = defaultdict(
            lambda: deque(maxlen=period + 1)
        )
        self._prev_rsi: dict[str, float] = {}

    def on_bar(self, bar: Bar) -> None:
        assert self.ctx is not None
        window = self._prices[bar.symbol]
        window.append(bar.close)
        if len(window) < self.period + 1:
            return

        rsi = _rsi_from_prices(list(window))
        prev = self._prev_rsi.get(bar.symbol)
        self._prev_rsi[bar.symbol] = rsi
        if prev is None:
            return

        if prev < self.oversold <= rsi:
            self.ctx.emit_signal(bar, Side.BUY)
        elif prev > self.overbought >= rsi:
            self.ctx.emit_signal(bar, Side.SELL)
