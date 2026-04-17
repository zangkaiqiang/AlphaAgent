"""Top-level performance summary combining equity and trade metrics."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from alphaagent.core.events import FillEvent
from alphaagent.metrics.returns import (
    annualized_return,
    annualized_volatility,
    calmar_ratio,
    max_drawdown,
    sharpe_ratio,
    sortino_ratio,
    total_return,
)
from alphaagent.metrics.trades import build_trades, trade_stats


@dataclass
class PerformanceSummary:
    total_return: float
    annualized_return: float
    annualized_volatility: float
    sharpe: float
    sortino: float
    max_drawdown: float
    calmar: float
    trades: int
    win_rate: float
    avg_win: float
    avg_loss: float
    profit_factor: float
    total_pnl: float

    def format(self) -> str:
        pf = "inf" if self.profit_factor == float("inf") else f"{self.profit_factor:.2f}"
        return (
            f"Total Return:       {self.total_return:>8.2%}\n"
            f"Annualized Return:  {self.annualized_return:>8.2%}\n"
            f"Annualized Vol:     {self.annualized_volatility:>8.2%}\n"
            f"Sharpe:             {self.sharpe:>8.2f}\n"
            f"Sortino:            {self.sortino:>8.2f}\n"
            f"Max Drawdown:       {self.max_drawdown:>8.2%}\n"
            f"Calmar:             {self.calmar:>8.2f}\n"
            f"Trades:             {self.trades:>8d}\n"
            f"Win Rate:           {self.win_rate:>8.2%}\n"
            f"Avg Win:            {self.avg_win:>8.2f}\n"
            f"Avg Loss:           {self.avg_loss:>8.2f}\n"
            f"Profit Factor:      {pf:>8}\n"
            f"Total PnL:          {self.total_pnl:>8.2f}"
        )


def summarize(
    equity_curve: list[tuple] | pd.Series,
    fills: list[FillEvent],
    risk_free: float = 0.0,
    periods_per_year: float | None = None,
) -> PerformanceSummary:
    if isinstance(equity_curve, list):
        series = (
            pd.DataFrame(equity_curve, columns=["timestamp", "equity"])
            .set_index("timestamp")["equity"]
        )
    else:
        series = equity_curve

    # Portfolio writes one snapshot per symbol per bar; collapse duplicate
    # timestamps to the last snapshot (which reflects the full portfolio).
    if series.index.has_duplicates:
        series = series.groupby(level=0).last()

    trades = build_trades(fills)
    ts = trade_stats(trades)

    return PerformanceSummary(
        total_return=total_return(series),
        annualized_return=annualized_return(series, periods_per_year),
        annualized_volatility=annualized_volatility(series, periods_per_year),
        sharpe=sharpe_ratio(series, risk_free, periods_per_year),
        sortino=sortino_ratio(series, risk_free, periods_per_year),
        max_drawdown=max_drawdown(series),
        calmar=calmar_ratio(series, periods_per_year),
        trades=int(ts["trades"]),
        win_rate=float(ts["win_rate"]),
        avg_win=float(ts["avg_win"]),
        avg_loss=float(ts["avg_loss"]),
        profit_factor=float(ts["profit_factor"]),
        total_pnl=float(ts["total_pnl"]),
    )
