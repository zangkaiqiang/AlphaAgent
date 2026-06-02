"""Shared engine wiring used by the API.

Takes an AppConfig and builds the strategies, the portfolio, execution
backend, calendar, and risk manager — handing back the pieces needed to
run a BacktestEngine. Centralising it here keeps the dispatch tree in one
place for the API runner (and any future entry points).
"""

from __future__ import annotations

from alphaagent.agent.base import Agent, NullAgent
from alphaagent.broker.paper import PaperBroker
from alphaagent.calendar.ashare import AShareCalendar
from alphaagent.config import (
    AgentConfig,
    AppConfig,
    CalendarConfig,
    ExecutionConfig,
    RiskConfig,
    StrategyConfig,
)
from alphaagent.core.event_bus import EventBus
from alphaagent.data.base import DataSource
from alphaagent.data.csv_source import CSVDataSource
from alphaagent.data.sqlite_cache import SqliteBarCache
from alphaagent.execution.base import ExecutionHandler
from alphaagent.execution.broker_exec import BrokerExecutionHandler
from alphaagent.execution.simulated import SimulatedExecutionHandler
from alphaagent.portfolio.multi import MultiStrategyPortfolio, StrategyAllocation
from alphaagent.portfolio.portfolio import Portfolio
from alphaagent.risk.portfolio_risk import (
    MaxGrossExposure,
    MaxPairwiseCorrelation,
    MaxPerSymbolExposure,
    MaxPositionCount,
    MaxSectorExposure,
    PortfolioRiskManager,
    RiskRule,
)
from alphaagent.risk.sector_map import CSVSectorMap, DictSectorMap, SectorMap
from alphaagent.storage.db import Database, get_database
from alphaagent.strategy import registry
from alphaagent.strategy.base import Strategy

PortfolioLike = Portfolio | MultiStrategyPortfolio


def source_id_for_data_cfg(data_cfg) -> str:
    parts = [data_cfg.source]
    if data_cfg.freq:
        parts.append(data_cfg.freq)
    if data_cfg.adjust:
        parts.append(data_cfg.adjust)
    return "_".join(parts)


def build_data_source(cfg: AppConfig) -> DataSource:
    source: DataSource
    if cfg.data.source == "csv":
        if not cfg.data.root:
            raise ValueError("data.root is required for csv source")
        source = CSVDataSource(cfg.data.root)
    elif cfg.data.source == "akshare":
        from alphaagent.data.akshare_source import AkShareDataSource

        source = AkShareDataSource(
            adjust=cfg.data.adjust or "qfq",
            daily_backend=getattr(cfg.data, "akshare_backend", None),
        )
    elif cfg.data.source == "tushare":
        from alphaagent.data.tushare_source import TushareDataSource

        source = TushareDataSource(
            token=cfg.data.tushare_token, adjust=cfg.data.adjust or "qfq"
        )
    else:
        raise ValueError(f"unknown data source: {cfg.data.source}")

    if cfg.data.cache_dir:
        # The DB is a server-level resource resolved uniformly via get_database()
        # (ALPHAAGENT_DB / default) — same instance the job store and calendar use,
        # so a single process never splits across two database files.
        source = SqliteBarCache(
            source,
            get_database(),
            source_id_for_data_cfg(cfg.data),
        )
    return source


def build_strategy(scfg: StrategyConfig) -> Strategy:
    params = dict(scfg.params)
    if scfg.strategy_id:
        params.setdefault("strategy_id", scfg.strategy_id)
    cls = registry.get(scfg.name)
    return cls(**params)


def build_strategies_and_portfolio(
    cfg: AppConfig, event_bus: EventBus
) -> tuple[list[Strategy], PortfolioLike]:
    strategies = [build_strategy(scfg) for scfg in cfg.strategies]
    if len(strategies) == 1:
        portfolio: PortfolioLike = Portfolio(
            initial_cash=cfg.portfolio.initial_cash,
            event_bus=event_bus,
            target_pct=cfg.strategies[0].target_pct or cfg.portfolio.target_pct,
            commission_rate=cfg.portfolio.commission_rate,
            min_commission=cfg.portfolio.min_commission,
            stamp_tax_rate=cfg.portfolio.stamp_tax_rate,
            strategy_id=strategies[0].strategy_id,
        )
        return strategies, portfolio

    allocations = [
        StrategyAllocation(
            strategy_id=strategy.strategy_id,
            weight=scfg.capital_weight,
            target_pct=scfg.target_pct or cfg.portfolio.target_pct,
        )
        for strategy, scfg in zip(strategies, cfg.strategies, strict=True)
    ]
    portfolio = MultiStrategyPortfolio(
        initial_cash=cfg.portfolio.initial_cash,
        event_bus=event_bus,
        allocations=allocations,
        commission_rate=cfg.portfolio.commission_rate,
        min_commission=cfg.portfolio.min_commission,
        stamp_tax_rate=cfg.portfolio.stamp_tax_rate,
    )
    return strategies, portfolio


def build_agent(cfg: AgentConfig) -> Agent:
    if not cfg.enabled:
        return NullAgent()
    if cfg.provider == "claude":
        from alphaagent.agent.claude_agent import ClaudeAgent

        return ClaudeAgent(model=cfg.model)
    return NullAgent()


def build_calendar(
    cfg: CalendarConfig, db: Database | None = None
) -> AShareCalendar | None:
    if not cfg.enabled:
        return None
    return AShareCalendar(db=db, cache_path=cfg.cache_path)


def build_execution(
    cfg: ExecutionConfig,
    initial_cash: float,
    commission_rate: float,
    min_commission: float,
    stamp_tax_rate: float,
    event_bus: EventBus,
) -> ExecutionHandler:
    backend = cfg.backend
    if backend == "simulated":
        return SimulatedExecutionHandler(
            event_bus=event_bus,
            commission_rate=commission_rate,
            min_commission=min_commission,
            stamp_tax_rate=stamp_tax_rate,
            slippage_bps=cfg.slippage_bps,
        )
    if backend == "paper":
        broker = PaperBroker(
            initial_cash=initial_cash,
            commission_rate=commission_rate,
            min_commission=min_commission,
            stamp_tax_rate=stamp_tax_rate,
            slippage_bps=cfg.slippage_bps,
        )
        return BrokerExecutionHandler(broker, event_bus)
    if backend == "qmt":
        if not cfg.qmt_path or not cfg.qmt_account:
            raise ValueError("execution.backend=qmt requires qmt_path and qmt_account")
        from alphaagent.broker.qmt import QMTBroker

        broker = QMTBroker(qmt_path=cfg.qmt_path, qmt_account=cfg.qmt_account)
        broker.connect()
        return BrokerExecutionHandler(broker, event_bus)
    raise ValueError(f"unknown execution backend: {backend!r}")


def build_sector_map(cfg: RiskConfig) -> SectorMap | None:
    if cfg.sectors and cfg.sectors_csv:
        raise ValueError("risk: specify either 'sectors' (inline) or 'sectors_csv', not both")
    if cfg.sectors:
        return DictSectorMap(cfg.sectors)
    if cfg.sectors_csv:
        return CSVSectorMap(cfg.sectors_csv)
    return None


def build_risk_manager(
    cfg: RiskConfig, portfolio: PortfolioLike
) -> PortfolioRiskManager | None:
    rules: list[RiskRule] = []
    if cfg.max_gross_exposure is not None:
        rules.append(MaxGrossExposure(cfg.max_gross_exposure))
    if cfg.max_per_symbol_exposure is not None:
        rules.append(MaxPerSymbolExposure(cfg.max_per_symbol_exposure))
    if cfg.max_position_count is not None:
        rules.append(MaxPositionCount(cfg.max_position_count))
    if cfg.max_sector_exposure is not None:
        sector_map = build_sector_map(cfg)
        if sector_map is None:
            raise ValueError(
                "risk.max_sector_exposure requires either 'sectors' or 'sectors_csv'"
            )
        rules.append(MaxSectorExposure(cfg.max_sector_exposure, sector_map))
    if cfg.max_pairwise_correlation is not None:
        rules.append(
            MaxPairwiseCorrelation(
                max_corr=cfg.max_pairwise_correlation,
                lookback=cfg.correlation_lookback,
            )
        )
    if not rules:
        return None
    return PortfolioRiskManager(portfolio, rules)
