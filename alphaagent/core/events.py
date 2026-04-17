"""Event definitions for the event-driven engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from alphaagent.core.types import Bar, OrderType, Side


class EventType(str, Enum):
    MARKET = "MARKET"
    SIGNAL = "SIGNAL"
    ORDER = "ORDER"
    FILL = "FILL"


@dataclass
class Event:
    type: EventType
    timestamp: datetime


@dataclass
class MarketEvent(Event):
    bar: Bar

    def __init__(self, bar: Bar):
        super().__init__(type=EventType.MARKET, timestamp=bar.timestamp)
        self.bar = bar


@dataclass
class SignalEvent(Event):
    """Strategy output: a desired directional intent, not yet sized."""

    symbol: str
    side: Side
    strength: float = 1.0  # 0..1, portfolio uses this to size
    strategy_id: str = ""

    def __init__(
        self,
        timestamp: datetime,
        symbol: str,
        side: Side,
        strength: float = 1.0,
        strategy_id: str = "",
    ):
        super().__init__(type=EventType.SIGNAL, timestamp=timestamp)
        self.symbol = symbol
        self.side = side
        self.strength = strength
        self.strategy_id = strategy_id


@dataclass
class OrderEvent(Event):
    """Portfolio output: a concrete order to be executed."""

    symbol: str
    side: Side
    quantity: int  # shares, must be multiple of 100 for A-share
    order_type: OrderType = OrderType.MARKET
    limit_price: float | None = None
    order_id: str = ""

    def __init__(
        self,
        timestamp: datetime,
        symbol: str,
        side: Side,
        quantity: int,
        order_type: OrderType = OrderType.MARKET,
        limit_price: float | None = None,
        order_id: str = "",
    ):
        super().__init__(type=EventType.ORDER, timestamp=timestamp)
        self.symbol = symbol
        self.side = side
        self.quantity = quantity
        self.order_type = order_type
        self.limit_price = limit_price
        self.order_id = order_id


@dataclass
class FillEvent(Event):
    """Execution output: an order has been filled."""

    symbol: str
    side: Side
    quantity: int
    fill_price: float
    commission: float = 0.0
    stamp_tax: float = 0.0
    order_id: str = ""
    metadata: dict = field(default_factory=dict)

    def __init__(
        self,
        timestamp: datetime,
        symbol: str,
        side: Side,
        quantity: int,
        fill_price: float,
        commission: float = 0.0,
        stamp_tax: float = 0.0,
        order_id: str = "",
        metadata: dict | None = None,
    ):
        super().__init__(type=EventType.FILL, timestamp=timestamp)
        self.symbol = symbol
        self.side = side
        self.quantity = quantity
        self.fill_price = fill_price
        self.commission = commission
        self.stamp_tax = stamp_tax
        self.order_id = order_id
        self.metadata = metadata or {}

    @property
    def total_cost(self) -> float:
        return self.commission + self.stamp_tax
