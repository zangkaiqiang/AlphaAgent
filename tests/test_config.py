"""Config validation for single- vs multi-strategy setups."""

from __future__ import annotations

import pytest
import yaml
from pydantic import ValidationError

from alphaagent.config import AppConfig

_BASE = {
    "data": {
        "source": "csv",
        "root": "./data",
        "symbols": ["600000"],
        "start": "2023-01-01",
        "end": "2023-12-31",
    },
}


def _load(extra: dict) -> AppConfig:
    raw = {**_BASE, **extra}
    return AppConfig(**yaml.safe_load(yaml.safe_dump(raw)))


def test_single_strategy_is_normalized_to_list():
    cfg = _load({"strategy": {"name": "ma_cross", "params": {"fast": 5, "slow": 20}}})
    assert cfg.strategy is None
    assert len(cfg.strategies) == 1
    assert cfg.strategies[0].name == "ma_cross"


def test_strategies_list_accepted():
    cfg = _load(
        {
            "strategies": [
                {"name": "ma_cross", "params": {"fast": 5, "slow": 20}, "capital_weight": 0.4},
                {"name": "ma_cross", "params": {"fast": 10, "slow": 30}, "capital_weight": 0.6},
            ]
        }
    )
    assert len(cfg.strategies) == 2
    assert cfg.strategies[0].capital_weight == 0.4


def test_strategies_weights_must_sum_to_one():
    with pytest.raises(ValidationError, match="sum to 1.0"):
        _load(
            {
                "strategies": [
                    {"name": "ma_cross", "capital_weight": 0.3},
                    {"name": "ma_cross", "capital_weight": 0.5},
                ]
            }
        )


def test_cannot_define_both_strategy_and_strategies():
    with pytest.raises(ValidationError, match="both"):
        _load(
            {
                "strategy": {"name": "ma_cross"},
                "strategies": [{"name": "ma_cross", "capital_weight": 1.0}],
            }
        )


def test_requires_strategy_or_strategies():
    with pytest.raises(ValidationError, match="must define"):
        _load({})


def test_storage_defaults_and_override():
    from alphaagent.config import AppConfig

    base = {
        "data": {"source": "csv", "root": "./data", "symbols": ["600000"],
                 "start": "2023-01-01", "end": "2023-12-31"},
        "strategy": {"name": "ma_cross", "params": {}},
    }
    cfg = AppConfig(**base)
    assert cfg.storage.db_path == "./data/alphaagent.db"

    cfg2 = AppConfig(**base, storage={"db_path": "/tmp/x.db"})
    assert cfg2.storage.db_path == "/tmp/x.db"

    # `storage:` present but empty (all keys commented out) -> defaults, no error.
    cfg3 = AppConfig(**base, storage=None)
    assert cfg3.storage.db_path == "./data/alphaagent.db"
