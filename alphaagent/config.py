"""Configuration loading from YAML + pydantic models."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import yaml
from pydantic import BaseModel, Field, model_validator


class DataConfig(BaseModel):
    source: str = "csv"  # csv | akshare | tushare
    root: str | None = None  # for csv
    symbols: list[str] = Field(default_factory=list)
    start: date
    end: date
    freq: str = "1d"  # 1d | 1m | 5m | 15m | 30m | 60m
    adjust: str = "qfq"  # qfq | hfq | "" (akshare/tushare)
    tushare_token: str | None = None  # or via TUSHARE_TOKEN env
    cache_dir: str | None = None  # enables CachedDataSource when set
    # akshare-only: which upstream to use for daily bars.
    # Switch to "sina" if eastmoney is unreachable from your network.
    akshare_backend: str = "eastmoney"


class CalendarConfig(BaseModel):
    enabled: bool = False
    cache_path: str | None = None  # parquet path for akshare calendar cache


class StrategyConfig(BaseModel):
    name: str
    params: dict = Field(default_factory=dict)
    # Used only in multi-strategy mode. Weights must sum to 1.0 across strategies.
    capital_weight: float = 1.0
    # Override strategy_id to distinguish multiple instances of the same strategy.
    strategy_id: str | None = None
    target_pct: float | None = None  # overrides portfolio.target_pct for this strategy


class PortfolioConfig(BaseModel):
    initial_cash: float = 1_000_000.0
    target_pct: float = 0.2
    commission_rate: float = 3e-4
    min_commission: float = 5.0
    stamp_tax_rate: float = 1e-3


class ExecutionConfig(BaseModel):
    backend: str = "simulated"  # simulated | paper | qmt
    slippage_bps: float = 0.0
    # QMT-only (required when backend=qmt):
    qmt_path: str | None = None
    qmt_account: str | None = None


class RiskConfig(BaseModel):
    """Portfolio-level risk limits. Any unset field is disabled."""

    max_gross_exposure: float | None = None  # e.g. 0.8 => cap at 80% of equity
    max_per_symbol_exposure: float | None = None  # e.g. 0.3 => any single symbol ≤ 30%
    max_position_count: int | None = None  # max distinct symbols held at once
    max_sector_exposure: float | None = None  # e.g. 0.4 => any single sector ≤ 40%
    sectors: dict[str, str] | None = None  # inline symbol -> sector map
    sectors_csv: str | None = None  # path to symbol,sector CSV (alternative to inline)
    max_pairwise_correlation: float | None = None  # e.g. 0.85
    correlation_lookback: int = 60


class AgentConfig(BaseModel):
    enabled: bool = False
    provider: str = "claude"  # claude | null
    model: str = "claude-sonnet-4-6"


class StorageConfig(BaseModel):
    db_path: str = "./data/alphaagent.db"


class AppConfig(BaseModel):
    data: DataConfig
    # Accept either a single ``strategy`` or a list under ``strategies``.
    # Normalized to the ``strategies`` list after validation.
    strategy: StrategyConfig | None = None
    strategies: list[StrategyConfig] = Field(default_factory=list)
    portfolio: PortfolioConfig = PortfolioConfig()
    execution: ExecutionConfig = ExecutionConfig()
    agent: AgentConfig = AgentConfig()
    calendar: CalendarConfig = CalendarConfig()
    risk: RiskConfig = RiskConfig()
    storage: StorageConfig = StorageConfig()

    @model_validator(mode="before")
    @classmethod
    def _coerce_empty_sections(cls, data):
        # YAML keys like `risk:` with all fields commented out parse to None.
        # Treat that as "use defaults" instead of erroring out.
        if isinstance(data, dict):
            for key in ("portfolio", "execution", "agent", "calendar", "risk", "storage"):
                if data.get(key) is None and key in data:
                    data[key] = {}
        return data

    @model_validator(mode="after")
    def _normalize_strategies(self):
        if self.strategies and self.strategy is not None:
            raise ValueError("config cannot define both 'strategy' and 'strategies'")
        if not self.strategies:
            if self.strategy is None:
                raise ValueError("config must define 'strategy' or 'strategies'")
            object.__setattr__(self, "strategies", [self.strategy])
            object.__setattr__(self, "strategy", None)
        if len(self.strategies) > 1:
            total = sum(s.capital_weight for s in self.strategies)
            if abs(total - 1.0) > 1e-6:
                raise ValueError(
                    f"capital_weight must sum to 1.0 across strategies, got {total:.4f}"
                )
        return self


def load_config(path: str | Path) -> AppConfig:
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return AppConfig(**data)
