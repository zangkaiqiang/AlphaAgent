"""SQLite-backed job store for backtest tasks.

Single-process, single-user. The live ``Job`` object keeps its in-memory
runtime bits (cancel_event, lock, version) for cheap high-frequency progress
updates and WS polling. Durable state is written to the shared ``jobs`` table
only on create and on terminal transitions. On startup the store hydrates
history from the DB and marks any non-terminal leftovers (from a process that
died mid-run) as FAILED.
"""

from __future__ import annotations

import json
import threading
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from alphaagent.api.schemas.backtest import JobStatus
from alphaagent.storage.db import Database

TERMINAL = {JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED}


@dataclass
class Job:
    id: str
    label: str | None = None
    kind: str = "backtest"
    status: JobStatus = JobStatus.PENDING
    progress: float = 0.0
    bars_processed: int = 0
    bars_total: int = 0
    fill_count: int = 0
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error: str | None = None
    result: dict[str, Any] | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    cancel_event: threading.Event = field(
        default_factory=threading.Event, compare=False, repr=False
    )
    version: int = 0  # bumped on every mutation; WS uses it for change detection
    _lock: threading.Lock = field(
        default_factory=threading.Lock, compare=False, repr=False
    )
    _persist: Callable[[Job], None] | None = field(
        default=None, compare=False, repr=False
    )

    def update(self, **fields: Any) -> None:
        with self._lock:
            for k, v in fields.items():
                setattr(self, k, v)
            self.version += 1
        # Persist outside the job lock; only when reaching a terminal state.
        if self.status in TERMINAL and self._persist is not None:
            self._persist(self)

    def request_cancel(self) -> None:
        self.cancel_event.set()

    def is_cancelled(self) -> bool:
        return self.cancel_event.is_set()


def _iso(dt: datetime | None) -> str | None:
    return dt.isoformat() if dt else None


def _dt(s: str | None) -> datetime | None:
    return datetime.fromisoformat(s) if s else None


def _job_to_row(job: Job) -> tuple:
    return (
        job.id, job.kind, job.label, job.status.value, job.progress,
        job.bars_processed, job.bars_total, job.fill_count,
        _iso(job.started_at), _iso(job.completed_at), job.error,
        json.dumps(job.result) if job.result is not None else None,
        _iso(job.created_at) or datetime.utcnow().isoformat(),
    )


def _row_to_job(row) -> Job:
    keys = row.keys() if hasattr(row, "keys") else []
    return Job(
        id=row["id"],
        label=row["label"],
        kind=row["kind"] if "kind" in keys and row["kind"] else "backtest",
        status=JobStatus(row["status"]),
        progress=row["progress"],
        bars_processed=row["bars_processed"],
        bars_total=row["bars_total"],
        fill_count=row["fill_count"],
        started_at=_dt(row["started_at"]),
        completed_at=_dt(row["completed_at"]),
        error=row["error"],
        result=json.loads(row["result_json"]) if row["result_json"] else None,
        created_at=_dt(row["created_at"]) or datetime.utcnow(),
    )


_INSERT = (
    "INSERT OR REPLACE INTO jobs "
    "(id,kind,label,status,progress,bars_processed,bars_total,fill_count,"
    "started_at,completed_at,error,result_json,created_at) "
    "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)"
)


class JobStore:
    def __init__(self, db: Database) -> None:
        self.db = db
        self._jobs: dict[str, Job] = {}
        self._lock = threading.Lock()
        self._hydrate()

    def _persist_job(self, job: Job) -> None:
        self.db.execute(_INSERT, _job_to_row(job))

    def _hydrate(self) -> None:
        for row in self.db.query("SELECT * FROM jobs ORDER BY created_at"):
            job = _row_to_job(row)
            if job.status not in TERMINAL:
                job.status = JobStatus.FAILED
                job.error = "interrupted by restart"
                job.completed_at = datetime.utcnow()
                self._persist_job(job)
            job._persist = self._persist_job
            self._jobs[job.id] = job

    def create(self, label: str | None = None, kind: str = "backtest") -> Job:
        jid = str(uuid.uuid4())
        job = Job(id=jid, label=label, kind=kind)
        job._persist = self._persist_job
        with self._lock:
            self._jobs[jid] = job
        self._persist_job(job)  # insert PENDING row so it survives a crash
        return job

    def get(self, jid: str) -> Job | None:
        return self._jobs.get(jid)

    def list(self, kind: str | None = None) -> list[Job]:
        with self._lock:
            jobs = list(self._jobs.values())
        if kind is not None:
            jobs = [j for j in jobs if j.kind == kind]
        return jobs

    def delete(self, jid: str) -> bool:
        with self._lock:
            existed = self._jobs.pop(jid, None) is not None
        self.db.execute("DELETE FROM jobs WHERE id=?", (jid,))
        return existed
