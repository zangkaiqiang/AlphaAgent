"""Command-line entry point."""

from __future__ import annotations

import sys
from pathlib import Path

import click

from alphaagent.agent.base import Agent, NullAgent
from alphaagent.backtest.engine import BacktestEngine
from alphaagent.broker.paper import PaperBroker
from alphaagent.calendar.ashare import AShareCalendar
from alphaagent.config import (
    AgentConfig,
    AppConfig,
    CalendarConfig,
    ExecutionConfig,
    RiskConfig,
    StrategyConfig,
    load_config,
)
from alphaagent.core.event_bus import EventBus
from alphaagent.data.base import DataFeed, DataSource
from alphaagent.data.cache import CachedDataSource
from alphaagent.data.csv_source import CSVDataSource
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
from alphaagent.strategy import registry
from alphaagent.strategy.base import Strategy

PortfolioLike = Portfolio | MultiStrategyPortfolio


def _build_data_source(cfg: AppConfig) -> DataSource:
    source: DataSource
    if cfg.data.source == "csv":
        if not cfg.data.root:
            raise ValueError("data.root is required for csv source")
        source = CSVDataSource(cfg.data.root)
    elif cfg.data.source == "akshare":
        from alphaagent.data.akshare_source import AkShareDataSource

        source = AkShareDataSource(adjust=cfg.data.adjust or "qfq")
    elif cfg.data.source == "tushare":
        from alphaagent.data.tushare_source import TushareDataSource

        source = TushareDataSource(
            token=cfg.data.tushare_token, adjust=cfg.data.adjust or "qfq"
        )
    else:
        raise ValueError(f"unknown data source: {cfg.data.source}")

    if cfg.data.cache_dir:
        source = CachedDataSource(source, cfg.data.cache_dir)
    return source


def _build_strategy(scfg: StrategyConfig) -> Strategy:
    """Build a Strategy from a config entry, applying strategy_id override."""
    params = dict(scfg.params)
    if scfg.strategy_id:
        params.setdefault("strategy_id", scfg.strategy_id)
    cls = registry.get(scfg.name)
    return cls(**params)


def _build_strategies_and_portfolio(
    cfg: AppConfig, event_bus: EventBus
) -> tuple[list[Strategy], PortfolioLike]:
    strategies = [_build_strategy(scfg) for scfg in cfg.strategies]

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


def _build_agent(cfg: AgentConfig) -> Agent:
    if not cfg.enabled:
        return NullAgent()
    if cfg.provider == "claude":
        from alphaagent.agent.claude_agent import ClaudeAgent

        return ClaudeAgent(model=cfg.model)
    return NullAgent()


def _build_calendar(cfg: CalendarConfig) -> AShareCalendar | None:
    if not cfg.enabled:
        return None
    return AShareCalendar(cache_path=cfg.cache_path)


def _build_execution(
    cfg: ExecutionConfig,
    portfolio_cfg_cash: float,
    portfolio_cfg_comm: float,
    portfolio_cfg_min_comm: float,
    portfolio_cfg_stamp: float,
    event_bus: EventBus,
) -> ExecutionHandler:
    backend = cfg.backend
    if backend == "simulated":
        return SimulatedExecutionHandler(
            event_bus=event_bus,
            commission_rate=portfolio_cfg_comm,
            min_commission=portfolio_cfg_min_comm,
            stamp_tax_rate=portfolio_cfg_stamp,
            slippage_bps=cfg.slippage_bps,
        )
    if backend == "paper":
        broker = PaperBroker(
            initial_cash=portfolio_cfg_cash,
            commission_rate=portfolio_cfg_comm,
            min_commission=portfolio_cfg_min_comm,
            stamp_tax_rate=portfolio_cfg_stamp,
            slippage_bps=cfg.slippage_bps,
        )
        return BrokerExecutionHandler(broker, event_bus)
    if backend == "qmt":
        if not cfg.qmt_path or not cfg.qmt_account:
            raise ValueError(
                "execution.backend=qmt requires qmt_path and qmt_account"
            )
        from alphaagent.broker.qmt import QMTBroker

        broker = QMTBroker(qmt_path=cfg.qmt_path, qmt_account=cfg.qmt_account)
        broker.connect()
        return BrokerExecutionHandler(broker, event_bus)
    raise ValueError(f"unknown execution backend: {backend!r}")


def _build_sector_map(cfg: RiskConfig) -> SectorMap | None:
    if cfg.sectors and cfg.sectors_csv:
        raise ValueError("risk: specify either 'sectors' (inline) or 'sectors_csv', not both")
    if cfg.sectors:
        return DictSectorMap(cfg.sectors)
    if cfg.sectors_csv:
        return CSVSectorMap(cfg.sectors_csv)
    return None


def _build_risk_manager(
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
        sector_map = _build_sector_map(cfg)
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


@click.group()
def main() -> None:
    """AlphaAgent CLI."""


@main.command()
@click.option("--config", "-c", required=True, type=click.Path(exists=True, path_type=Path))
def backtest(config: Path) -> None:
    """Run a backtest from a YAML config."""
    cfg = load_config(config)
    source = _build_data_source(cfg)
    frames = {
        sym: source.get_bars(sym, cfg.data.start, cfg.data.end, freq=cfg.data.freq)
        for sym in cfg.data.symbols
    }
    feed = DataFeed(frames)

    event_bus = EventBus()
    strategies, portfolio = _build_strategies_and_portfolio(cfg, event_bus)
    execution = _build_execution(
        cfg.execution,
        cfg.portfolio.initial_cash,
        cfg.portfolio.commission_rate,
        cfg.portfolio.min_commission,
        cfg.portfolio.stamp_tax_rate,
        event_bus,
    )
    agent = _build_agent(cfg.agent)
    calendar = _build_calendar(cfg.calendar)
    risk_manager = _build_risk_manager(cfg.risk, portfolio)

    click.echo(f"Agent: {type(agent).__name__} (enabled={cfg.agent.enabled})")
    click.echo(f"Calendar: {'on' if calendar else 'off'}  Freq: {cfg.data.freq}")
    click.echo(f"Execution: {cfg.execution.backend}")
    click.echo(f"Strategies: {[s.strategy_id for s in strategies]}")
    if risk_manager is not None:
        click.echo(f"Risk rules: {[r.name for r in risk_manager.rules]}")

    engine = BacktestEngine(
        feed,
        strategies if len(strategies) > 1 else strategies[0],
        portfolio,
        execution,
        event_bus,
        calendar=calendar,
        risk_manager=risk_manager,
    )
    result = engine.run()

    click.echo(f"Initial: {result.initial_cash:,.2f}")
    click.echo(f"Final:   {result.final_equity:,.2f}")
    click.echo(f"Bars:    processed={result.bars_processed} skipped={result.bars_skipped}")
    click.echo(f"Fills:   {result.fill_count}")
    if risk_manager is not None:
        click.echo(
            f"Risk:    downsized={risk_manager.downsizes} rejected={risk_manager.rejections}"
        )
    click.echo("")
    click.echo("Performance (aggregate)")
    click.echo("-----------------------")
    click.echo(result.performance().format())

    if result.equity_by_strategy:
        for sid, perf in result.performance_by_strategy().items():
            click.echo("")
            click.echo(f"Performance (strategy={sid})")
            click.echo("-" * (18 + len(sid)))
            click.echo(perf.format())


@main.command(name="list-strategies")
def list_strategies() -> None:
    """List all registered strategies."""
    for name, cls in sorted(registry.BUILTIN_STRATEGIES.items()):
        click.echo(f"{name:<22}  {cls.__name__}")


if __name__ == "__main__":
    main(prog_name="alphaagent", standalone_mode=True)
    sys.exit(0)
