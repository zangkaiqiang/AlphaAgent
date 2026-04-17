"""Backtest engine: wires data feed, strategies, portfolio, execution."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

import pandas as pd

from alphaagent.calendar.ashare import AShareCalendar
from alphaagent.core.event_bus import EventBus
from alphaagent.core.events import EventType, FillEvent, MarketEvent
from alphaagent.core.types import Bar
from alphaagent.data.base import DataFeed
from alphaagent.execution.base import ExecutionHandler
from alphaagent.metrics.summary import PerformanceSummary, summarize
from alphaagent.portfolio.multi import MultiStrategyPortfolio
from alphaagent.portfolio.portfolio import Portfolio
from alphaagent.risk.portfolio_risk import PortfolioRiskManager
from alphaagent.strategy.base import Strategy, StrategyContext

PortfolioLike = Portfolio | MultiStrategyPortfolio


@dataclass
class BacktestResult:
    initial_cash: float
    final_equity: float
    equity_curve: list[tuple[datetime, float]] = field(default_factory=list)
    fills: list[FillEvent] = field(default_factory=list)
    bars_processed: int = 0
    bars_skipped: int = 0
    # Per-strategy equity curves, keyed by strategy_id. Empty for single-strategy runs.
    equity_by_strategy: dict[str, list[tuple[datetime, float]]] = field(default_factory=dict)

    @property
    def fill_count(self) -> int:
        return len(self.fills)

    @property
    def total_return(self) -> float:
        if self.initial_cash == 0:
            return 0.0
        return self.final_equity / self.initial_cash - 1

    def to_dataframe(self) -> pd.DataFrame:
        return pd.DataFrame(self.equity_curve, columns=["timestamp", "equity"]).set_index(
            "timestamp"
        )

    def performance(
        self,
        risk_free: float = 0.0,
        periods_per_year: float | None = None,
    ) -> PerformanceSummary:
        return summarize(
            self.equity_curve,
            self.fills,
            risk_free=risk_free,
            periods_per_year=periods_per_year,
        )

    def performance_by_strategy(
        self,
        risk_free: float = 0.0,
        periods_per_year: float | None = None,
    ) -> dict[str, PerformanceSummary]:
        """Per-strategy performance breakdown. Empty for single-strategy runs."""
        out: dict[str, PerformanceSummary] = {}
        for sid, curve in self.equity_by_strategy.items():
            sid_fills = [f for f in self.fills if f.strategy_id == sid]
            out[sid] = summarize(
                curve,
                sid_fills,
                risk_free=risk_free,
                periods_per_year=periods_per_year,
            )
        return out


class BacktestEngine:
    def __init__(
        self,
        feed: DataFeed,
        strategies: Strategy | list[Strategy],
        portfolio: PortfolioLike,
        execution: ExecutionHandler,
        event_bus: EventBus,
        calendar: AShareCalendar | None = None,
        risk_manager: PortfolioRiskManager | None = None,
    ):
        """Wires the event-driven engine.

        ``strategies`` may be a single Strategy or a list. When a list is
        passed, ``portfolio`` must be a MultiStrategyPortfolio whose
        allocations include every strategy's ``strategy_id``.

        If ``calendar`` is provided, bars whose timestamp is not a trading
        day are dropped. For bars with a non-midnight time component
        (i.e. minute bars), the session-hours window is additionally
        enforced.
        """
        self.feed = feed
        self.strategies: list[Strategy] = (
            list(strategies) if isinstance(strategies, list) else [strategies]
        )
        self.portfolio = portfolio
        self.execution = execution
        self.event_bus = event_bus
        self.calendar = calendar
        self.risk_manager = risk_manager
        self._fills: list[FillEvent] = []
        self._bars_processed = 0
        self._bars_skipped = 0

        self._validate()

        for strategy in self.strategies:
            strategy.bind(
                StrategyContext(event_bus=event_bus, strategy_id=strategy.strategy_id)
            )

        # Order matters: execution and portfolio see the bar first so they
        # know the price, THEN strategies emit signals against that price.
        event_bus.subscribe(EventType.MARKET, self.execution.handle_market)
        event_bus.subscribe(EventType.MARKET, self.portfolio.handle_market)
        for strategy in self.strategies:
            event_bus.subscribe(EventType.MARKET, strategy.handle_market)
        # Stateful risk rules (e.g. correlation) need to see market data to
        # keep their internal windows current. Subscribed after the portfolio
        # so view.last_price is already fresh if rules want to peek.
        if self.risk_manager is not None:
            event_bus.subscribe(EventType.MARKET, self.risk_manager.handle_market)
        event_bus.subscribe(EventType.SIGNAL, self.portfolio.handle_signal)
        # Risk manager must see ORDER events BEFORE execution so that any
        # downsize or rejection is applied before the fill is generated.
        if self.risk_manager is not None:
            event_bus.subscribe(EventType.ORDER, self.risk_manager.handle_order)
        event_bus.subscribe(EventType.ORDER, self.execution.handle_order)
        event_bus.subscribe(EventType.FILL, self.portfolio.handle_fill)
        event_bus.subscribe(EventType.FILL, self._record_fill)

    def _validate(self) -> None:
        ids = [s.strategy_id for s in self.strategies]
        if len(set(ids)) != len(ids):
            raise ValueError(f"duplicate strategy_id across strategies: {ids}")
        if len(self.strategies) > 1 and not isinstance(self.portfolio, MultiStrategyPortfolio):
            raise TypeError(
                "multiple strategies require a MultiStrategyPortfolio"
            )
        if isinstance(self.portfolio, MultiStrategyPortfolio):
            missing = set(ids) - set(self.portfolio.portfolios.keys())
            if missing:
                raise ValueError(
                    f"MultiStrategyPortfolio missing allocations for: {sorted(missing)}"
                )

    def _record_fill(self, event: FillEvent) -> None:
        self._fills.append(event)

    def _accept_bar(self, bar: Bar) -> bool:
        if self.calendar is None:
            return True
        ts = bar.timestamp
        if not self.calendar.is_trading_day(ts):
            return False
        # Midnight timestamp => daily bar; skip session-hours check.
        if ts.hour == 0 and ts.minute == 0 and ts.second == 0:
            return True
        return self.calendar.is_session_time(ts.time())

    def run(self) -> BacktestResult:
        for strategy in self.strategies:
            strategy.on_start()
        for bar in self.feed:
            if not self._accept_bar(bar):
                self._bars_skipped += 1
                continue
            self._bars_processed += 1
            self.event_bus.put(MarketEvent(bar=bar))
            self.event_bus.dispatch()
        for strategy in self.strategies:
            strategy.on_finish()

        equity_by_strategy: dict[str, list[tuple[datetime, float]]] = {}
        if isinstance(self.portfolio, MultiStrategyPortfolio):
            equity_by_strategy = {
                sid: list(pf.equity_curve) for sid, pf in self.portfolio.portfolios.items()
            }

        return BacktestResult(
            initial_cash=self.portfolio.initial_cash,
            final_equity=self.portfolio.equity(),
            equity_curve=list(self.portfolio.equity_curve),
            fills=list(self._fills),
            bars_processed=self._bars_processed,
            bars_skipped=self._bars_skipped,
            equity_by_strategy=equity_by_strategy,
        )
