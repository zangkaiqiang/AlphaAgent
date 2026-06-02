"""Bridge BacktestEngine into the FastAPI job model.

Runs in a worker thread spawned by FastAPI's BackgroundTasks. Reports
progress via ``Job.update`` (thread-safe) and surfaces the final result as
a JSON-serialisable dict that the API can hand back without further
post-processing.
"""

from __future__ import annotations

import traceback
from datetime import datetime
from typing import Any

from alphaagent.api.job_store import Job
from alphaagent.api.schemas.backtest import (
    BacktestResultDTO,
    EquityPoint,
    FillDTO,
    JobStatus,
    PerformanceDTO,
)
from alphaagent.backtest.engine import BacktestEngine, BacktestResult
from alphaagent.config import AppConfig
from alphaagent.core.event_bus import EventBus
from alphaagent.core.events import FillEvent
from alphaagent.data.base import DataFeed
from alphaagent.metrics.summary import PerformanceSummary
from alphaagent.runtime import (
    build_calendar,
    build_data_source,
    build_execution,
    build_risk_manager,
    build_strategies_and_portfolio,
)


def run_backtest_job(job: Job, config_dict: dict[str, Any]) -> None:
    """BackgroundTasks target. Mutates ``job`` as work progresses."""
    job.update(status=JobStatus.RUNNING, started_at=datetime.utcnow())
    try:
        cfg = AppConfig(**config_dict)
        result = _run(job, cfg)
        if job.is_cancelled():
            job.update(
                status=JobStatus.CANCELLED,
                completed_at=datetime.utcnow(),
                result=_result_to_dto(result).model_dump(mode="json"),
            )
        else:
            job.update(
                status=JobStatus.COMPLETED,
                progress=1.0,
                completed_at=datetime.utcnow(),
                result=_result_to_dto(result).model_dump(mode="json"),
            )
    except Exception as e:
        job.update(
            status=JobStatus.FAILED,
            error=f"{type(e).__name__}: {e}",
            completed_at=datetime.utcnow(),
        )
        traceback.print_exc()


def _run(job: Job, cfg: AppConfig) -> BacktestResult:
    source = build_data_source(cfg)
    frames = {
        sym: source.get_bars(sym, cfg.data.start, cfg.data.end, freq=cfg.data.freq)
        for sym in cfg.data.symbols
    }
    feed = DataFeed(frames)
    total_bars = sum(len(df) for df in frames.values())
    job.update(bars_total=total_bars)

    event_bus = EventBus()
    strategies, portfolio = build_strategies_and_portfolio(cfg, event_bus)
    execution = build_execution(
        cfg.execution,
        cfg.portfolio.initial_cash,
        cfg.portfolio.commission_rate,
        cfg.portfolio.min_commission,
        cfg.portfolio.stamp_tax_rate,
        event_bus,
    )
    from alphaagent.storage.db import get_database

    # The DB is a server-level resource (ALPHAAGENT_DB env / default), shared with
    # the job store. Resolve it lazily — only when the calendar actually needs it —
    # so a disabled-calendar run never opens/creates a database file.
    calendar_db = get_database() if cfg.calendar.enabled else None
    calendar = build_calendar(cfg.calendar, calendar_db)
    risk_manager = build_risk_manager(cfg.risk, portfolio)

    def on_progress(bars_processed: int, fill_count: int) -> None:
        progress = bars_processed / total_bars if total_bars else 0.0
        job.update(
            bars_processed=bars_processed,
            fill_count=fill_count,
            progress=min(0.999, progress),
        )

    engine = BacktestEngine(
        feed,
        strategies if len(strategies) > 1 else strategies[0],
        portfolio,
        execution,
        event_bus,
        calendar=calendar,
        risk_manager=risk_manager,
        progress_callback=on_progress,
        progress_every=max(50, total_bars // 100 or 1),
        should_cancel=job.is_cancelled,
    )
    return engine.run()


def _perf_to_dto(p: PerformanceSummary) -> PerformanceDTO:
    pf = p.profit_factor
    if pf == float("inf"):
        pf = 1e9  # JSON has no infinity; clamp for display
    return PerformanceDTO(
        total_return=p.total_return,
        annualized_return=p.annualized_return,
        annualized_volatility=p.annualized_volatility,
        sharpe=p.sharpe,
        sortino=p.sortino,
        max_drawdown=p.max_drawdown,
        calmar=p.calmar,
        trades=p.trades,
        win_rate=p.win_rate,
        avg_win=p.avg_win,
        avg_loss=p.avg_loss,
        profit_factor=pf,
        total_pnl=p.total_pnl,
    )


def _fill_to_dto(f: FillEvent) -> FillDTO:
    return FillDTO(
        timestamp=f.timestamp,
        symbol=f.symbol,
        side=f.side.value,
        quantity=f.quantity,
        fill_price=f.fill_price,
        commission=f.commission,
        stamp_tax=f.stamp_tax,
        order_id=f.order_id,
        strategy_id=f.strategy_id,
    )


def _result_to_dto(result: BacktestResult) -> BacktestResultDTO:
    return BacktestResultDTO(
        initial_cash=result.initial_cash,
        final_equity=result.final_equity,
        total_return=result.total_return,
        bars_processed=result.bars_processed,
        bars_skipped=result.bars_skipped,
        fill_count=result.fill_count,
        cancelled=result.cancelled,
        equity_curve=[EquityPoint(timestamp=t, equity=e) for t, e in result.equity_curve],
        fills=[_fill_to_dto(f) for f in result.fills],
        performance=_perf_to_dto(result.performance()),
        performance_by_strategy={
            sid: _perf_to_dto(perf)
            for sid, perf in result.performance_by_strategy().items()
        },
        equity_by_strategy={
            sid: [EquityPoint(timestamp=t, equity=e) for t, e in curve]
            for sid, curve in result.equity_by_strategy.items()
        },
    )
