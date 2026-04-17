from datetime import datetime

import pytest

from alphaagent.core.events import OrderEvent
from alphaagent.core.types import OrderType, Side
from alphaagent.risk.rules import (
    AShareRiskRules,
    LotSizeViolation,
    PriceLimitViolation,
    TPlusOneViolation,
)


def _order(side, qty):
    return OrderEvent(
        timestamp=datetime(2023, 1, 3),
        symbol="600000",
        side=side,
        quantity=qty,
        order_type=OrderType.MARKET,
    )


def test_lot_size_rejects_non_multiple_of_100():
    rules = AShareRiskRules()
    with pytest.raises(LotSizeViolation):
        rules.check_lot_size(_order(Side.BUY, 150))


def test_price_limit_buy_at_upper_blocked():
    rules = AShareRiskRules(price_limit=0.1)
    with pytest.raises(PriceLimitViolation):
        rules.check_price_against_limit(_order(Side.BUY, 100), prev_close=10.0, fill_price=11.0)


def test_price_limit_sell_at_lower_blocked():
    rules = AShareRiskRules(price_limit=0.1)
    with pytest.raises(PriceLimitViolation):
        rules.check_price_against_limit(_order(Side.SELL, 100), prev_close=10.0, fill_price=9.0)


def test_tplusone_blocks_oversell():
    with pytest.raises(TPlusOneViolation):
        AShareRiskRules.check_tplusone(available_shares=500, sell_qty=1000)
