"""Strategy registry — list available strategies and parameter specs."""

from __future__ import annotations

import inspect
from typing import Any

from fastapi import APIRouter

from alphaagent.api.envelope import ok
from alphaagent.api.schemas.strategy import StrategyInfo, StrategyParamSpec
from alphaagent.strategy import registry

router = APIRouter()


def _infer_param_specs(cls) -> list[StrategyParamSpec]:
    """Introspect __init__ signature for hint about params strategy accepts."""
    specs: list[StrategyParamSpec] = []
    try:
        sig = inspect.signature(cls.__init__)
    except (TypeError, ValueError):
        return specs
    for name, param in sig.parameters.items():
        if name in {"self", "strategy_id"}:
            continue
        if param.kind in {param.VAR_POSITIONAL, param.VAR_KEYWORD}:
            continue
        type_hint = _type_name(param.annotation)
        default = None if param.default is inspect._empty else param.default
        specs.append(
            StrategyParamSpec(
                name=name,
                type=type_hint,
                default=default,
                required=param.default is inspect._empty,
            )
        )
    return specs


def _type_name(annotation: Any) -> str:
    if annotation is inspect._empty:
        return "any"
    if annotation is int:
        return "int"
    if annotation is float:
        return "float"
    if annotation is str:
        return "str"
    if annotation is bool:
        return "bool"
    return getattr(annotation, "__name__", str(annotation))


@router.get("")
def list_strategies():
    items = [
        StrategyInfo(
            name=name,
            class_name=cls.__name__,
            description=(inspect.getdoc(cls) or "").split("\n")[0] or None,
            params=_infer_param_specs(cls),
        )
        for name, cls in sorted(registry.BUILTIN_STRATEGIES.items())
    ]
    return ok([s.model_dump() for s in items])
