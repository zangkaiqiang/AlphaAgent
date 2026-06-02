"""In-memory job store for backtest tasks.

Single-process, single-user. Each job carries its own threading.Event for
cancellation and a list of progress snapshots that WS subscribers poll.
"""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from alphaagent.api.schemas.backtest import JobStatus


@dataclass
class Job:
    id: str
    label: str | None = None
    status: JobStatus = JobStatus.PENDING
    progress: float = 0.0
    bars_processed: int = 0
    bars_total: int = 0
    fill_count: int = 0
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error: str | None = None
    result: dict[str, Any] | None = None
    cancel_event: threading.Event = field(default_factory=threading.Event)
    version: int = 0  # bumped on every state mutation; WS uses for change detection
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def update(self, **fields: Any) -> None:
        with self._lock:
            for k, v in fields.items():
                setattr(self, k, v)
            self.version += 1

    def request_cancel(self) -> None:
        self.cancel_event.set()

    def is_cancelled(self) -> bool:
        return self.cancel_event.is_set()


class JobStore:
    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}
        self._lock = threading.Lock()

    def create(self, label: str | None = None) -> Job:
        jid = str(uuid.uuid4())
        job = Job(id=jid, label=label)
        with self._lock:
            self._jobs[jid] = job
        return job

    def get(self, jid: str) -> Job | None:
        return self._jobs.get(jid)

    def list(self) -> list[Job]:
        with self._lock:
            return list(self._jobs.values())

    def delete(self, jid: str) -> bool:
        with self._lock:
            return self._jobs.pop(jid, None) is not None
