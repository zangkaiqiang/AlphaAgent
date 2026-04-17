"""Trade-level metrics.

A "trade" here means a round-trip: one or more BUY fills matched against
one or more SELL fills on the same symbol, FIFO. This gives us win rate,
profit factor, and average win/loss from raw FillEvents.
"""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime

from alphaagent.core.events import FillEvent
from alphaagent.core.types import Side


@dataclass
class Trade:
    symbol: str
    open_time: datetime
    close_time: datetime
    quantity: int
    open_price: float
    close_price: float
    pnl: float  # net of commission and stamp tax

    @property
    def return_pct(self) -> float:
        if self.open_price == 0:
            return 0.0
        return (self.close_price - self.open_price) / self.open_price

    @property
    def is_winner(self) -> bool:
        return self.pnl > 0


@dataclass
class _OpenLot:
    timestamp: datetime
    quantity: int
    price: float
    cost_fees: float  # fees proportional to shares in this lot


def build_trades(fills: list[FillEvent]) -> list[Trade]:
    """Pair BUY/SELL fills per symbol using FIFO, returning closed trades.

    Partial closes produce multiple Trade records. Unclosed lots at the end
    of the series are discarded (not counted as trades).
    """
    lots_by_symbol: dict[str, deque[_OpenLot]] = defaultdict(deque)
    trades: list[Trade] = []

    for fill in sorted(fills, key=lambda f: f.timestamp):
        if fill.side == Side.BUY:
            lots_by_symbol[fill.symbol].append(
                _OpenLot(
                    timestamp=fill.timestamp,
                    quantity=fill.quantity,
                    price=fill.fill_price,
                    cost_fees=fill.total_cost,
                )
            )
            continue

        remaining = fill.quantity
        sell_fees_remaining = fill.total_cost
        lots = lots_by_symbol[fill.symbol]
        while remaining > 0 and lots:
            lot = lots[0]
            qty = min(lot.quantity, remaining)
            # allocate fees proportionally to the matched slice
            buy_fee_slice = lot.cost_fees * (qty / lot.quantity) if lot.quantity else 0.0
            sell_fee_slice = sell_fees_remaining * (qty / remaining) if remaining else 0.0
            gross = (fill.fill_price - lot.price) * qty
            trades.append(
                Trade(
                    symbol=fill.symbol,
                    open_time=lot.timestamp,
                    close_time=fill.timestamp,
                    quantity=qty,
                    open_price=lot.price,
                    close_price=fill.fill_price,
                    pnl=gross - buy_fee_slice - sell_fee_slice,
                )
            )
            lot.quantity -= qty
            lot.cost_fees -= buy_fee_slice
            sell_fees_remaining -= sell_fee_slice
            remaining -= qty
            if lot.quantity == 0:
                lots.popleft()

    return trades


def trade_stats(trades: list[Trade]) -> dict[str, float | int]:
    """Summary statistics for a list of closed trades."""
    if not trades:
        return {
            "trades": 0,
            "win_rate": 0.0,
            "avg_win": 0.0,
            "avg_loss": 0.0,
            "profit_factor": 0.0,
            "total_pnl": 0.0,
        }
    wins = [t.pnl for t in trades if t.pnl > 0]
    losses = [t.pnl for t in trades if t.pnl < 0]
    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))
    return {
        "trades": len(trades),
        "win_rate": len(wins) / len(trades),
        "avg_win": gross_profit / len(wins) if wins else 0.0,
        "avg_loss": -gross_loss / len(losses) if losses else 0.0,
        "profit_factor": gross_profit / gross_loss if gross_loss > 0 else float("inf"),
        "total_pnl": sum(t.pnl for t in trades),
    }
