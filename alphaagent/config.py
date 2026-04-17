"""Configuration loading from YAML + pydantic models."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import yaml
from pydantic import BaseModel, Field


class DataConfig(BaseModel):
    source: str = "csv"  # csv | akshare | tushare
    root: str | None = None  # for csv
    symbols: list[str] = Field(default_factory=list)
    start: date
    end: date
    adjust: str = "qfq"  # qfq | hfq | "" (akshare/tushare)
    tushare_token: str | None = None  # or via TUSHARE_TOKEN env
    cache_dir: str | None = None  # enables CachedDataSource when set


class StrategyConfig(BaseModel):
    name: str
    params: dict = Field(default_factory=dict)


class PortfolioConfig(BaseModel):
    initial_cash: float = 1_000_000.0
    target_pct: float = 0.2
    commission_rate: float = 3e-4
    min_commission: float = 5.0
    stamp_tax_rate: float = 1e-3


class ExecutionConfig(BaseModel):
    slippage_bps: float = 0.0


class AgentConfig(BaseModel):
    enabled: bool = False
    provider: str = "claude"  # claude | null
    model: str = "claude-sonnet-4-6"


class AppConfig(BaseModel):
    data: DataConfig
    strategy: StrategyConfig
    portfolio: PortfolioConfig = PortfolioConfig()
    execution: ExecutionConfig = ExecutionConfig()
    agent: AgentConfig = AgentConfig()


def load_config(path: str | Path) -> AppConfig:
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return AppConfig(**data)
