"""Command-line entry point."""

from __future__ import annotations

import sys
from pathlib import Path

import click

from alphaagent.agent.base import Agent, NullAgent
from alphaagent.backtest.engine import BacktestEngine
from alphaagent.config import AgentConfig, AppConfig, load_config
from alphaagent.core.event_bus import EventBus
from alphaagent.data.base import DataFeed, DataSource
from alphaagent.data.csv_source import CSVDataSource
from alphaagent.execution.simulated import SimulatedExecutionHandler
from alphaagent.portfolio.portfolio import Portfolio
from alphaagent.strategy.base import Strategy
from alphaagent.strategy.ma_cross import MACrossStrategy


def _build_data_source(cfg: AppConfig) -> DataSource:
    if cfg.data.source == "csv":
        if not cfg.data.root:
            raise ValueError("data.root is required for csv source")
        return CSVDataSource(cfg.data.root)
    if cfg.data.source == "akshare":
        from alphaagent.data.akshare_source import AkShareDataSource

        return AkShareDataSource()
    raise ValueError(f"unknown data source: {cfg.data.source}")


def _build_strategy(cfg: AppConfig) -> Strategy:
    name = cfg.strategy.name
    if name == "ma_cross":
        return MACrossStrategy(**cfg.strategy.params)
    raise ValueError(f"unknown strategy: {name}")


def _build_agent(cfg: AgentConfig) -> Agent:
    if not cfg.enabled:
        return NullAgent()
    if cfg.provider == "claude":
        from alphaagent.agent.claude_agent import ClaudeAgent

        return ClaudeAgent(model=cfg.model)
    return NullAgent()


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
        sym: source.get_bars(sym, cfg.data.start, cfg.data.end) for sym in cfg.data.symbols
    }
    feed = DataFeed(frames)

    event_bus = EventBus()
    portfolio = Portfolio(
        initial_cash=cfg.portfolio.initial_cash,
        event_bus=event_bus,
        target_pct=cfg.portfolio.target_pct,
        commission_rate=cfg.portfolio.commission_rate,
        min_commission=cfg.portfolio.min_commission,
        stamp_tax_rate=cfg.portfolio.stamp_tax_rate,
    )
    execution = SimulatedExecutionHandler(
        event_bus=event_bus,
        commission_rate=cfg.portfolio.commission_rate,
        min_commission=cfg.portfolio.min_commission,
        stamp_tax_rate=cfg.portfolio.stamp_tax_rate,
        slippage_bps=cfg.execution.slippage_bps,
    )
    strategy = _build_strategy(cfg)
    agent = _build_agent(cfg.agent)
    click.echo(f"Agent: {type(agent).__name__} (enabled={cfg.agent.enabled})")

    engine = BacktestEngine(feed, strategy, portfolio, execution, event_bus)
    result = engine.run()

    click.echo(f"Initial: {result.initial_cash:,.2f}")
    click.echo(f"Final:   {result.final_equity:,.2f}")
    click.echo(f"Return:  {result.total_return:.2%}")
    click.echo(f"Fills:   {result.fills}")


if __name__ == "__main__":
    main(prog_name="alphaagent", standalone_mode=True)
    sys.exit(0)
