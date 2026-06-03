"""FastAPI dependency providers (process-wide singletons).

Most of these are overridable for tests via FastAPI's
``app.dependency_overrides[get_xxx] = ...``.
"""

from __future__ import annotations

import os
from functools import lru_cache

from alphaagent.api.job_store import JobStore
from alphaagent.data.base import DataSource
from alphaagent.fundamentals.base import FundamentalsProvider
from alphaagent.storage.db import get_database


@lru_cache(maxsize=1)
def get_job_store() -> JobStore:
    return JobStore(get_database())


def get_fundamentals_provider() -> FundamentalsProvider:
    """Default: try AkShare-backed; tests override via dependency_overrides.

    The provider is lazy-imported so importing this module doesn't drag in
    akshare. If akshare isn't installed, raise a clear error at call time.
    """
    from alphaagent.fundamentals.akshare_provider import AkShareFundamentalsProvider

    ttl = float(os.environ.get("ALPHAAGENT_FUND_TTL", "300"))
    return AkShareFundamentalsProvider(ttl_seconds=ttl)


def get_kline_data_source() -> DataSource:
    """OHLCV source for K-line endpoints. Defaults to AkShare."""
    from alphaagent.data.akshare_source import AkShareDataSource

    return AkShareDataSource(adjust="qfq")


def get_news_provider():
    """News provider for the research analyst. Overridable in tests."""
    from alphaagent.fundamentals.news import AkShareNewsProvider

    return AkShareNewsProvider()


def get_research_analyst():
    """Agentic research analyst. Overridable in tests via dependency_overrides."""
    from alphaagent.agent.research_analyst import ResearchAnalyst

    model = os.environ.get("ALPHAAGENT_AGENT_MODEL", "claude-sonnet-4-6")
    return ResearchAnalyst(model=model)
