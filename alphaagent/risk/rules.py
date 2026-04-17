"""A-share risk rules: price limits, T+1, lot size.

These are pure-function checks used by portfolio/execution to reject
orders that would violate exchange rules.
"""

from __future__ import annotations

from alphaagent.core.events import OrderEvent
from alphaagent.core.types import Side

LOT_SIZE = 100
DEFAULT_PRICE_LIMIT = 0.10  # ±10% for normal boards
STAR_MARKET_LIMIT = 0.20  # 科创板 / 创业板


class RiskViolation(Exception):
    """Base for risk rule violations."""


class PriceLimitViolation(RiskViolation):
    pass


class TPlusOneViolation(RiskViolation):
    pass


class LotSizeViolation(RiskViolation):
    pass


class AShareRiskRules:
    """Holds A-share-specific guardrails.

    - ``check_order``: validates lot size pre-submit.
    - ``check_price_against_limit``: given prev close, validates tradable price.
    - ``check_tplusone``: given position lock map, validates sell allowance.
    """

    def __init__(self, price_limit: float = DEFAULT_PRICE_LIMIT):
        self.price_limit = price_limit

    def check_lot_size(self, order: OrderEvent) -> None:
        if order.quantity <= 0 or order.quantity % LOT_SIZE != 0:
            raise LotSizeViolation(
                f"order {order.order_id}: quantity {order.quantity} not a multiple of {LOT_SIZE}"
            )

    def upper_limit(self, prev_close: float) -> float:
        return round(prev_close * (1 + self.price_limit), 2)

    def lower_limit(self, prev_close: float) -> float:
        return round(prev_close * (1 - self.price_limit), 2)

    def check_price_against_limit(
        self, order: OrderEvent, prev_close: float, fill_price: float
    ) -> None:
        up = self.upper_limit(prev_close)
        down = self.lower_limit(prev_close)
        if order.side == Side.BUY and fill_price >= up:
            raise PriceLimitViolation(
                f"{order.symbol}: BUY blocked at upper limit {up}"
            )
        if order.side == Side.SELL and fill_price <= down:
            raise PriceLimitViolation(
                f"{order.symbol}: SELL blocked at lower limit {down}"
            )

    @staticmethod
    def check_tplusone(available_shares: int, sell_qty: int) -> None:
        if sell_qty > available_shares:
            raise TPlusOneViolation(
                f"attempting to sell {sell_qty} but only {available_shares} are T+1-unlocked"
            )
