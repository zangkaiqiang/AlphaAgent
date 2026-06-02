"""Backtest job lifecycle: submit, list, get status, get result, cancel, watch via WS."""

from __future__ import annotations

import asyncio
from typing import Annotated

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
from alphaagent.api.runner import run_backtest_job
from alphaagent.api.schemas.backtest import (
    BacktestSubmitRequest,
    JobInfo,
    JobStatus,
)

router = APIRouter()


def _job_to_info(job: Job) -> JobInfo:
    return JobInfo(
        id=job.id,
        label=job.label,
        status=job.status,
        progress=job.progress,
        bars_processed=job.bars_processed,
        bars_total=job.bars_total,
        fill_count=job.fill_count,
        started_at=job.started_at,
        completed_at=job.completed_at,
        error=job.error,
    )


@router.post("")
def submit_backtest(
    req: BacktestSubmitRequest,
    background_tasks: BackgroundTasks,
    store: Annotated[JobStore, Depends(get_job_store)],
):
    """Submit a backtest. Returns the job id; poll or subscribe via WS."""
    job = store.create(label=req.label)
    background_tasks.add_task(run_backtest_job, job, req.config)
    return ok({"job_id": job.id})


@router.get("")
def list_jobs(store: Annotated[JobStore, Depends(get_job_store)]):
    items = [_job_to_info(j).model_dump(mode="json") for j in store.list()]
    return ok(items)


@router.get("/{job_id}")
def get_job(job_id: str, store: Annotated[JobStore, Depends(get_job_store)]):
    job = store.get(job_id)
    if job is None:
        raise HTTPException(404, detail=err("JOB_NOT_FOUND", f"job {job_id} not found"))
    return ok(_job_to_info(job).model_dump(mode="json"))


@router.get("/{job_id}/result")
def get_job_result(
    job_id: str, store: Annotated[JobStore, Depends(get_job_store)]
):
    job = store.get(job_id)
    if job is None:
        raise HTTPException(404, detail=err("JOB_NOT_FOUND", f"job {job_id} not found"))
    if job.status not in TERMINAL:
        raise HTTPException(400, detail=err("JOB_NOT_DONE", f"job is {job.status}"))
    if job.status == JobStatus.FAILED:
        raise HTTPException(400, detail=err("JOB_FAILED", job.error or "failed"))
    return ok(job.result)


@router.delete("/{job_id}")
def cancel_job(
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
async def watch_job(
    websocket: WebSocket,
    job_id: str,
    store: Annotated[JobStore, Depends(get_job_store)],
):
    """Push job state updates until the job reaches a terminal state.

    Single-user setup: polls the job's version counter every 200 ms and
    pushes a snapshot whenever it changes. Production multi-user would
    swap this for an explicit asyncio queue per subscriber.
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
