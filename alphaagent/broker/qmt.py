"""迅投 miniQMT / iQuant broker adapter.

QMT is the most common institutional quant trading client for A-share
market, supported by most major brokers (中信、国君、华泰、招商...). This
adapter wraps the ``xtquant`` Python API that QMT ships with.

Setup
-----
1. Apply for miniQMT access through your broker (普通账户升级为量化权限)
2. Install the QMT client and log in at least once
3. ``pip install xtquant`` (or use the wheel shipped with the client)
4. Point ``qmt_path`` at the QMT client install directory (contains
   ``userdata_mini``) and set ``qmt_account`` to your fund account
5. Call ``connect()`` at session start; ``disconnect()`` at shutdown

Usage
-----
This scaffold maps the core OrderEvent → xt_trader → FillEvent flow.
Before going live:
  - Test every code path against QMT's built-in simulation account
  - Add order status polling / reconnection on network drops
  - Reconcile positions and cash against ``query_stock_positions`` on
    startup, not just the callback stream

Reference: https://dict.thinktrader.net/innerApi/
"""

from __future__ import annotations

from typing import Any

from alphaagent.broker.base import Broker, BrokerError
from alphaagent.core.events import FillEvent, OrderEvent
from alphaagent.core.types import Side


class QMTBroker(Broker):
    def __init__(self, qmt_path: str, qmt_account: str, account_type: str = "STOCK"):
        super().__init__()
        self.qmt_path = qmt_path
        self.qmt_account = qmt_account
        self.account_type = account_type
        self._trader: Any = None
        self._account: Any = None

    def connect(self) -> None:
        try:
            from xtquant import xtconstant  # type: ignore
            from xtquant.xttrader import StockAccount, XtQuantTrader  # type: ignore
        except ImportError as e:
            raise ImportError(
                "xtquant not installed. Install the QMT client and run "
                "`pip install xtquant`."
            ) from e

        session_id = int(__import__("time").time())
        self._trader = XtQuantTrader(self.qmt_path, session_id)
        self._trader.register_callback(_QMTCallback(self))
        self._trader.start()
        if self._trader.connect() != 0:
            raise BrokerError("QMT connect failed")
        self._account = StockAccount(self.qmt_account, self.account_type)
        if self._trader.subscribe(self._account) != 0:
            raise BrokerError("QMT subscribe failed")
        # Expose xtconstant for order_type translation.
        self._xt = xtconstant

    def disconnect(self) -> None:
        if self._trader is not None:
            self._trader.stop()
            self._trader = None

    def place_order(self, order: OrderEvent) -> None:
        if self._trader is None or self._account is None:
            raise BrokerError("QMT not connected; call connect() first")
        stock_code = _to_xt_code(order.symbol)
        trade_type = (
            self._xt.STOCK_BUY if order.side == Side.BUY else self._xt.STOCK_SELL
        )
        # Market orders use FIX_PRICE at the last known price on QMT; to keep
        # this adapter simple we require a LIMIT price for live trading.
        if order.limit_price is None:
            raise BrokerError(
                "QMT orders require a limit_price (use OrderType.LIMIT)"
            )
        self._trader.order_stock(
            account=self._account,
            stock_code=stock_code,
            order_type=trade_type,
            order_volume=order.quantity,
            price_type=self._xt.FIX_PRICE,
            price=order.limit_price,
            strategy_name=order.strategy_id or "alphaagent",
            order_remark=order.order_id,
        )

    def positions(self) -> dict[str, int]:
        if self._trader is None or self._account is None:
            return {}
        positions = self._trader.query_stock_positions(self._account)
        return {_from_xt_code(p.stock_code): int(p.volume) for p in positions}

    def cash(self) -> float:
        if self._trader is None or self._account is None:
            return 0.0
        asset = self._trader.query_stock_asset(self._account)
        return float(asset.cash) if asset else 0.0


class _QMTCallback:
    """Adapter between xtquant trade callbacks and our FillEvent stream."""

    def __init__(self, broker: QMTBroker):
        self._broker = broker

    def on_stock_trade(self, trade: Any) -> None:
        from datetime import datetime

        self._broker._emit_fill(
            FillEvent(
                timestamp=datetime.fromtimestamp(trade.traded_time),
                symbol=_from_xt_code(trade.stock_code),
                side=Side.BUY if trade.order_type == 23 else Side.SELL,
                quantity=int(trade.traded_volume),
                fill_price=float(trade.traded_price),
                commission=0.0,  # filled in by query_stock_trades if needed
                stamp_tax=0.0,
                order_id=str(trade.order_id),
                strategy_id=trade.order_remark or "",
            )
        )


def _to_xt_code(symbol: str) -> str:
    """600000 -> 600000.SH, 000001 -> 000001.SZ."""
    if "." in symbol:
        return symbol
    if symbol.startswith(("60", "68", "90")):
        return f"{symbol}.SH"
    if symbol.startswith(("00", "30")):
        return f"{symbol}.SZ"
    if symbol.startswith(("43", "83", "87", "88")):
        return f"{symbol}.BJ"
    raise ValueError(f"cannot infer exchange for {symbol!r}")


def _from_xt_code(xt_code: str) -> str:
    return xt_code.split(".")[0]
