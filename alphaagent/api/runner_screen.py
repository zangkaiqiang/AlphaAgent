"""Bridge ScreenerPipeline into the FastAPI job model.

Mirrors ``alphaagent.api.runner`` (run_backtest_job) for screener jobs.
Runs in a worker thread spawned by FastAPI's BackgroundTasks.

Progress note: ``ScreenerPipeline.run()`` does **not** accept a progress
callback. Progress is therefore set coarsely: 0.05 at pipeline start,
1.0 at completion.
"""

from __future__ import annotations

import traceback
from datetime import datetime
from typing import Any

from alphaagent.api.job_store import Job
from alphaagent.api.schemas.backtest import JobStatus
from alphaagent.api.schemas.screener import PickDTO, ReasonDTO, ScreenResultDTO
from alphaagent.screener.base import ScreenResult


def run_screen_job(job: Job, config_dict: dict[str, Any]) -> None:
    """BackgroundTasks target for screener jobs. Mutates ``job`` as work progresses."""
    job.update(status=JobStatus.RUNNING, started_at=datetime.utcnow())
    try:
        from alphaagent.screener.build import (
            build_meta_provider,
            build_screen_data_source,
            build_universe,
        )
        from alphaagent.screener.config import ScreenAppConfig
        from alphaagent.screener.filters import build_filter
        from alphaagent.screener.pipeline import ScreenerPipeline
        from alphaagent.screener.rules_builtin import build_rule, split_rules

        cfg = ScreenAppConfig(**config_dict)

        universe = build_universe(cfg)
        meta_provider = build_meta_provider(cfg)
        data_source = build_screen_data_source(cfg)

        filters = [
            build_filter(f.to_kwargs() | {"type": f.type})
            for f in cfg.filters
        ]
        rules = [build_rule(r.to_kwargs()) for r in cfg.rules]
        abs_rules, xs_rules = split_rules(rules)

        calendar = None
        if cfg.calendar_enabled:
            from alphaagent.calendar.ashare import AShareCalendar
            from alphaagent.storage.db import get_database

            calendar = AShareCalendar(db=get_database())

        pipeline = ScreenerPipeline(
            universe=universe,
            data_source=data_source,
            meta_provider=meta_provider,
            absolute_rules=abs_rules,
            xs_rules=xs_rules,
            filters=filters,
            as_of=cfg.as_of,
            lookback_days=cfg.lookback_days,
            calendar=calendar,
            max_workers=cfg.execution.max_workers,
            show_progress=cfg.execution.show_progress,
            max_per_industry=cfg.max_per_industry,
        )

        job.update(progress=0.05)

        result = pipeline.run()

        if job.is_cancelled():
            job.update(
                status=JobStatus.CANCELLED,
                completed_at=datetime.utcnow(),
                result=screen_result_to_dto(result, cfg.output.top_n).model_dump(
                    mode="json"
                ),
            )
        else:
            job.update(
                status=JobStatus.COMPLETED,
                progress=1.0,
                completed_at=datetime.utcnow(),
                result=screen_result_to_dto(result, cfg.output.top_n).model_dump(
                    mode="json"
                ),
            )
    except Exception as e:
        job.update(
            status=JobStatus.FAILED,
            error=f"{type(e).__name__}: {e}",
            completed_at=datetime.utcnow(),
        )
        traceback.print_exc()


def screen_result_to_dto(result: ScreenResult, top_n: int) -> ScreenResultDTO:
    """Convert a ``ScreenResult`` to a JSON-serialisable ``ScreenResultDTO``."""
    top_picks = result.picks[:top_n]
    return ScreenResultDTO(
        generated_at=result.generated_at.isoformat(),
        resolved_as_of=result.resolved_as_of.isoformat(),
        universe_name=result.universe_name,
        universe_size=result.universe_size,
        filtered_size=result.filtered_size,
        rules_applied=result.rules_applied,
        symbols=[p.symbol for p in top_picks],
        picks=[
            PickDTO(
                symbol=p.symbol,
                name=p.name,
                final_score=p.final_score,
                reasons=[
                    ReasonDTO(
                        rule_name=r.rule_name,
                        score=r.score,
                        detail=r.detail,
                    )
                    for r in p.reasons
                ],
                metadata=p.metadata or {},
            )
            for p in top_picks
        ],
    )
