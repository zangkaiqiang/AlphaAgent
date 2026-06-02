"""Strategy registry schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class StrategyParamSpec(BaseModel):
    name: str
    type: str  # int | float | str | bool
    default: Any | None = None
    required: bool = False


class StrategyInfo(BaseModel):
    name: str
    class_name: str
    description: str | None = None
    params: list[StrategyParamSpec] = []
