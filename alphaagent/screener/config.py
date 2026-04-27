"""Pydantic models for the screener config (loaded from yaml).

Independent of the backtest config in ``alphaagent.config``, but reuses
``DataConfig`` so source/freq/adjust/cache_dir share semantics.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, model_validator

from alphaagent.config import DataConfig


class UniverseConfig(BaseModel):
    source: Literal["static", "akshare_index", "tushare_index"]
    index_code: str | None = None
    symbols: list[str] | None = None

    @model_validator(mode="after")
    def _check(self):
        if self.source == "static" and not self.symbols:
            raise ValueError("universe.source=static requires 'symbols'")
        if self.source in ("akshare_index", "tushare_index") and not self.index_code:
            raise ValueError(f"universe.source={self.source} requires 'index_code'")
        return self


class MetaConfig(BaseModel):
    source: Literal["akshare", "tushare", "csv"] = "akshare"
    cache_dir: str | None = "./data/cache/meta"
    csv: str | None = None

    @model_validator(mode="after")
    def _check(self):
        if self.source == "csv" and not self.csv:
            raise ValueError("meta.source=csv requires 'csv' path")
        return self


class FilterConfig(BaseModel):
    type: str
    model_config = {"extra": "allow"}

    def to_kwargs(self) -> dict:
        out = self.model_dump()
        out.pop("type", None)
        return out


class RuleConfig(BaseModel):
    type: str
    weight: float = 1.0
    model_config = {"extra": "allow"}

    def to_kwargs(self) -> dict:
        return self.model_dump()


class ExecutionConfig(BaseModel):
    max_workers: int = 16
    show_progress: bool = True


class OutputConfig(BaseModel):
    path: str = "./picks.yaml"
    top_n: int = 30
    with_reasons: Literal["full", "compact", "none"] = "full"
    format: Literal["yaml", "csv"] = "yaml"


class ScreenAppConfig(BaseModel):
    universe: UniverseConfig
    data: DataConfig
    as_of: date
    lookback_days: int = 120
    calendar_enabled: bool = True
    meta: MetaConfig = MetaConfig()
    filters: list[FilterConfig] = Field(default_factory=list)
    rules: list[RuleConfig]
    execution: ExecutionConfig = ExecutionConfig()
    output: OutputConfig = OutputConfig()
    # Diversity: cap per-industry picks after global ranking. None disables.
    max_per_industry: int | None = None

    @model_validator(mode="before")
    @classmethod
    def _coerce_empty_sections(cls, data):
        if isinstance(data, dict):
            for key in ("meta", "execution", "output"):
                if key in data and data.get(key) is None:
                    data[key] = {}
            # The screener doesn't need symbols/start/end on DataConfig — they
            # are derived from universe + as_of + lookback_days. Inject
            # placeholder values so DataConfig validation passes without
            # asking the user to populate them.
            data_cfg = data.get("data")
            if isinstance(data_cfg, dict):
                data_cfg.setdefault("symbols", [])
                data_cfg.setdefault("start", data.get("as_of") or "1970-01-01")
                data_cfg.setdefault("end", data.get("as_of") or "1970-01-01")
        return data

    @model_validator(mode="after")
    def _check_rules_present(self):
        if not self.rules:
            raise ValueError("screen config must define at least one rule")
        return self


def load_screen_config(path: str | Path) -> ScreenAppConfig:
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return ScreenAppConfig(**data)
