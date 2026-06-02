"""FastAPI dependency providers (process-wide singletons)."""

from __future__ import annotations

from functools import lru_cache

from alphaagent.api.job_store import JobStore


@lru_cache(maxsize=1)
def get_job_store() -> JobStore:
    return JobStore()
