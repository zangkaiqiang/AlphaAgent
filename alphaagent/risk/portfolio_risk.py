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
from typing import Protocol

from alphaagent.core.events import OrderEvent
from alphaagent.core.types import Side

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
