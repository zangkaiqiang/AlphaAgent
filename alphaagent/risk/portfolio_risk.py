"""Portfolio-level risk rules.

These rules gate BUY orders *after* the portfolio has sized them but
*before* execution. Each rule returns the allowed quantity (<= the
requested quantity); 0 means the order is rejected entirely. The risk
manager takes the minimum across all rules and rounds down to the
A-share lot size.

For multi-strategy runs, ``portfolio_view`` is the aggregated
MultiStrategyPortfolio, so exposure rules see the *combined* book.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections import defaultdict, deque
from typing import Protocol

import numpy as np

from alphaagent.core.events import MarketEvent, OrderEvent
from alphaagent.core.types import Side
from alphaagent.risk.sector_map import SectorMap

LOT_SIZE = 100


class PortfolioView(Protocol):
    """Structural type implemented by Portfolio and MultiStrategyPortfolio."""

    def equity(self) -> float: ...
    def gross_value(self) -> float: ...
    def position_value(self, symbol: str) -> float: ...
    def held_symbols(self) -> set[str]: ...
    def last_price(self, symbol: str) -> float | None: ...


class RiskRule(ABC):
    name: str

    @abstractmethod
    def allowed_qty(self, order: OrderEvent, view: PortfolioView) -> int:
        """Return the allowed quantity for ``order`` (<= order.quantity)."""


class MaxGrossExposure(RiskRule):
    """Cap total position value at ``max_pct * equity``."""

    name = "max_gross_exposure"

    def __init__(self, max_pct: float):
        if not 0 < max_pct <= 1:
            raise ValueError("max_pct must be in (0, 1]")
        self.max_pct = max_pct

    def allowed_qty(self, order: OrderEvent, view: PortfolioView) -> int:
        price = view.last_price(order.symbol)
        if price is None or price <= 0:
            return 0
        headroom = self.max_pct * view.equity() - view.gross_value()
        if headroom <= 0:
            return 0
        return min(order.quantity, int(headroom / price))


class MaxPerSymbolExposure(RiskRule):
    """Cap any single symbol's value at ``max_pct * equity``."""

    name = "max_per_symbol_exposure"

    def __init__(self, max_pct: float):
        if not 0 < max_pct <= 1:
            raise ValueError("max_pct must be in (0, 1]")
        self.max_pct = max_pct

    def allowed_qty(self, order: OrderEvent, view: PortfolioView) -> int:
        price = view.last_price(order.symbol)
        if price is None or price <= 0:
            return 0
        headroom = self.max_pct * view.equity() - view.position_value(order.symbol)
        if headroom <= 0:
            return 0
        return min(order.quantity, int(headroom / price))


class MaxPositionCount(RiskRule):
    """Limit the number of distinct symbols held simultaneously."""

    name = "max_position_count"

    def __init__(self, max_n: int):
        if max_n < 1:
            raise ValueError("max_n must be >= 1")
        self.max_n = max_n

    def allowed_qty(self, order: OrderEvent, view: PortfolioView) -> int:
        held = view.held_symbols()
        if order.symbol in held:
            return order.quantity  # adding to existing position
        if len(held) < self.max_n:
            return order.quantity  # room for one more
        return 0


class MaxSectorExposure(RiskRule):
    """Cap combined position value within any single sector.

    Unknown symbols (not in the sector map) are treated as unconstrained
    rather than rejected - that avoids surprise rejections when the map
    is incomplete.
    """

    name = "max_sector_exposure"

    def __init__(self, max_pct: float, sector_map: SectorMap):
        if not 0 < max_pct <= 1:
            raise ValueError("max_pct must be in (0, 1]")
        self.max_pct = max_pct
        self.sector_map = sector_map

    def allowed_qty(self, order: OrderEvent, view: PortfolioView) -> int:
        sector = self.sector_map.get(order.symbol)
        if sector is None:
            return order.quantity
        price = view.last_price(order.symbol)
        if price is None or price <= 0:
            return 0
        sector_value = sum(
            view.position_value(s)
            for s in view.held_symbols()
            if self.sector_map.get(s) == sector
        )
        headroom = self.max_pct * view.equity() - sector_value
        if headroom <= 0:
            return 0
        return min(order.quantity, int(headroom / price))


class MaxPairwiseCorrelation(RiskRule):
    """Reject BUYs that would add a highly correlated new position.

    Rolling returns per symbol are built by subscribing to MARKET events
    via ``on_market``. When a BUY order arrives for a symbol NOT already
    held, we compute the Pearson correlation of its recent returns
    against every currently held symbol; if any pairwise correlation
    exceeds ``max_corr`` in absolute value, the order is rejected.

    Adding to an existing position is allowed (no new pair is created).
    Symbols with fewer than ``min_samples`` observations pass through
    unconstrained.
    """

    name = "max_pairwise_correlation"

    def __init__(
        self,
        max_corr: float = 0.85,
        lookback: int = 60,
        min_samples: int | None = None,
    ):
        if not 0 < max_corr <= 1:
            raise ValueError("max_corr must be in (0, 1]")
        if lookback < 3:
            raise ValueError("lookback must be >= 3")
        self.max_corr = max_corr
        self.lookback = lookback
        self.min_samples = min_samples if min_samples is not None else max(10, lookback // 2)
        self._returns: dict[str, deque[float]] = defaultdict(
            lambda: deque(maxlen=lookback)
        )
        self._last_close: dict[str, float] = {}

    def on_market(self, event: MarketEvent) -> None:
        symbol = event.bar.symbol
        close = event.bar.close
        prev = self._last_close.get(symbol)
        if prev is not None and prev > 0:
            self._returns[symbol].append(close / prev - 1)
        self._last_close[symbol] = close

    def allowed_qty(self, order: OrderEvent, view: PortfolioView) -> int:
        held = view.held_symbols()
        if order.symbol in held:
            return order.quantity  # already held, no new pair introduced
        my_returns = list(self._returns.get(order.symbol, []))
        if len(my_returns) < self.min_samples:
            return order.quantity
        for sym in held:
            other = list(self._returns.get(sym, []))
            n = min(len(my_returns), len(other))
            if n < self.min_samples:
                continue
            a = np.asarray(my_returns[-n:])
            b = np.asarray(other[-n:])
            if a.std() == 0 or b.std() == 0:
                continue
            corr = float(np.corrcoef(a, b)[0, 1])
            if abs(corr) > self.max_corr:
                return 0
        return order.quantity


class PortfolioRiskManager:
    """Subscribes to ORDER events and mutates BUY orders to respect limits.

    SELL orders pass through unchanged: closing positions never increases
    exposure. The manager must be subscribed to ORDER events *before* the
    execution handler so execution sees the adjusted quantity.
    """

    def __init__(self, portfolio: PortfolioView, rules: list[RiskRule]):
        self.portfolio = portfolio
        self.rules = list(rules)
        self.rejections: int = 0
        self.downsizes: int = 0

    def handle_market(self, event: MarketEvent) -> None:
        for rule in self.rules:
            on_market = getattr(rule, "on_market", None)
            if on_market is not None:
                on_market(event)

    def handle_order(self, event: OrderEvent) -> None:
        if event.side != Side.BUY or event.quantity <= 0:
            return
        requested = event.quantity
        allowed = requested
        for rule in self.rules:
            allowed = min(allowed, rule.allowed_qty(event, self.portfolio))
            if allowed <= 0:
                break
        allowed = max(0, (allowed // LOT_SIZE) * LOT_SIZE)
        if allowed == 0:
            self.rejections += 1
            event.quantity = 0
            return
        if allowed < requested:
            self.downsizes += 1
            event.quantity = allowed
