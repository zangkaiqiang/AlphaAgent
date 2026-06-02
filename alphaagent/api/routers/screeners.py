"""Screener job lifecycle: submit, list, get status, get result, cancel, watch via WS.

Mirrors ``backtests.py`` for screener jobs.
"""

from __future__ import annotations

import asyncio
import inspect
from typing import Annotated, Any

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
)

from alphaagent.api.deps import get_job_store
from alphaagent.api.envelope import err, ok
from alphaagent.api.job_store import TERMINAL, Job, JobStore
from alphaagent.api.runner_screen import run_screen_job
from alphaagent.api.schemas.screener import ScreenJobInfo, ScreenSubmitRequest
from alphaagent.screener.filters import BUILTIN_FILTERS
from alphaagent.screener.rules_builtin import BUILTIN_ABSOLUTE_RULES, BUILTIN_XS_RULES

router = APIRouter()


def _job_to_info(job: Job) -> ScreenJobInfo:
    picks_count = len(job.result.get("picks", [])) if job.result else 0
    return ScreenJobInfo(
        id=job.id,
        label=job.label,
        status=job.status,
        progress=job.progress,
        picks_count=picks_count,
        started_at=job.started_at,
        completed_at=job.completed_at,
        error=job.error,
    )


def _param_specs(cls) -> list[dict[str, Any]]:
    """Introspect __init__ signature and return a list of param dicts."""
    specs: list[dict[str, Any]] = []
    try:
        sig = inspect.signature(cls.__init__)
    except (TypeError, ValueError):
        return specs
    for name, param in sig.parameters.items():
        if name in {"self"}:
            continue
        if param.kind in {param.VAR_POSITIONAL, param.VAR_KEYWORD}:
            continue
        default = None if param.default is inspect.Parameter.empty else param.default
        required = param.default is inspect.Parameter.empty
        specs.append(
            {
                "name": name,
                "default": default,
                "required": required,
            }
        )
    return specs


@router.post("")
def submit_screen(
    req: ScreenSubmitRequest,
    background_tasks: BackgroundTasks,
    store: Annotated[JobStore, Depends(get_job_store)],
):
    """Submit a screener job. Returns the job id; poll or subscribe via WS."""
    job = store.create(label=req.label, kind="screen")
    background_tasks.add_task(run_screen_job, job, req.config)
    return ok({"job_id": job.id})


@router.get("")
def list_screen_jobs(store: Annotated[JobStore, Depends(get_job_store)]):
    items = [_job_to_info(j).model_dump(mode="json") for j in store.list(kind="screen")]
    return ok(items)


# CRITICAL: /rules MUST be declared BEFORE /{job_id} so FastAPI doesn't
# treat "rules" as a job_id path parameter.
@router.get("/rules")
def list_rules():
    """Catalog all built-in scoring rules and hard filters with their param specs."""
    rules = []
    for name, cls in sorted(BUILTIN_ABSOLUTE_RULES.items()):
        rules.append(
            {
                "type": name,
                "category": "absolute",
                "class_name": cls.__name__,
                "params": _param_specs(cls),
            }
        )
    for name, cls in sorted(BUILTIN_XS_RULES.items()):
        rules.append(
            {
                "type": name,
                "category": "cross_sectional",
                "class_name": cls.__name__,
                "params": _param_specs(cls),
            }
        )

    filters = []
    for name, cls in sorted(BUILTIN_FILTERS.items()):
        filters.append(
            {
                "type": name,
                "class_name": cls.__name__,
                "params": _param_specs(cls),
            }
        )

    return ok({"rules": rules, "filters": filters})


@router.get("/{job_id}")
def get_screen_job(job_id: str, store: Annotated[JobStore, Depends(get_job_store)]):
    job = store.get(job_id)
    if job is None:
        raise HTTPException(404, detail=err("JOB_NOT_FOUND", f"job {job_id} not found"))
    return ok(_job_to_info(job).model_dump(mode="json"))


@router.get("/{job_id}/result")
def get_screen_job_result(
    job_id: str, store: Annotated[JobStore, Depends(get_job_store)]
):
    job = store.get(job_id)
    if job is None:
        raise HTTPException(404, detail=err("JOB_NOT_FOUND", f"job {job_id} not found"))
    if job.status not in TERMINAL:
        raise HTTPException(400, detail=err("JOB_NOT_DONE", f"job is {job.status}"))
    from alphaagent.api.schemas.backtest import JobStatus

    if job.status == JobStatus.FAILED:
        raise HTTPException(400, detail=err("JOB_FAILED", job.error or "failed"))
    return ok(job.result)


@router.delete("/{job_id}")
def cancel_screen_job(
    job_id: str, store: Annotated[JobStore, Depends(get_job_store)]
):
    job = store.get(job_id)
    if job is None:
        raise HTTPException(404, detail=err("JOB_NOT_FOUND", f"job {job_id} not found"))
    if job.status in TERMINAL:
        return ok({"cancelled": False, "status": job.status.value})
    job.request_cancel()
    return ok({"cancelled": True})


@router.websocket("/{job_id}/ws")
async def watch_screen_job(
    websocket: WebSocket,
    job_id: str,
    store: Annotated[JobStore, Depends(get_job_store)],
):
    """Push screen job state updates until the job reaches a terminal state.

    Polls the job's version counter every 200 ms and pushes a snapshot
    whenever it changes.
    """
    await websocket.accept()
    job = store.get(job_id)
    if job is None:
        await websocket.close(code=1008, reason="job not found")
        return

    last_version = -1
    try:
        while True:
            if job.version != last_version:
                last_version = job.version
                await websocket.send_json(_job_to_info(job).model_dump(mode="json"))
            if job.status in TERMINAL:
                break
            await asyncio.sleep(0.2)
    except WebSocketDisconnect:
        pass
