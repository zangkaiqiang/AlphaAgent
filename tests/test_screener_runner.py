"""Offline integration test for the screener job runner.

Uses only CSVDataSource + CSVMetaProvider (no network).
"""

from __future__ import annotations

import os
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import pytest

from alphaagent.api.job_store import JobStore
from alphaagent.api.schemas.backtest import JobStatus
from alphaagent.storage.db import Database, _INSTANCES, _INSTANCES_LOCK


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_ohlcv(path: Path, n_rows: int, start: date) -> None:
    """Write a simple monotonically-rising OHLCV CSV."""
    rows = []
    for i in range(n_rows):
        d = start + timedelta(days=i)
        c = 10.0 + i * 0.05
        rows.append((d.isoformat(), c, c + 0.1, c - 0.1, c, 100_000, 1_000_000.0))
    df = pd.DataFrame(
        rows,
        columns=["date", "open", "high", "low", "close", "volume", "amount"],
    )
    df.to_csv(path, index=False)


def _write_meta(path: Path, symbols: list[str]) -> None:
    lines = ["symbol,name,industry,list_date"]
    for sym in symbols:
        lines.append(f"{sym},{sym}Co,科技,2010-01-01")
    path.write_text("\n".join(lines) + "\n")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def tmp_env(tmp_path, monkeypatch):
    """Isolated DB + data directory; clears the get_database() singleton cache."""
    db_path = str(tmp_path / "test.db")
    monkeypatch.setenv("ALPHAAGENT_DB", db_path)

    # Clear singleton so this test gets a fresh Database instance.
    with _INSTANCES_LOCK:
        _INSTANCES.clear()

    yield tmp_path

    # Cleanup singleton after test.
    with _INSTANCES_LOCK:
        _INSTANCES.clear()


@pytest.fixture()
def data_root(tmp_env):
    root = tmp_env / "bars"
    root.mkdir()
    # Write ~200 calendar days so that lookback_days=120 (×1.5+7 = 187 days)
    # window is fully covered.
    start = date(2024, 1, 1)
    for sym in ("A", "B", "C"):
        _write_ohlcv(root / f"{sym}.csv", 200, start)
    return root


@pytest.fixture()
def meta_csv(tmp_env):
    p = tmp_env / "meta.csv"
    _write_meta(p, ["A", "B", "C"])
    return p


@pytest.fixture()
def job_store(tmp_env):
    db = Database(str(tmp_env / "test.db"))
    return JobStore(db)


# ---------------------------------------------------------------------------
# Config helpers
# ---------------------------------------------------------------------------


def _config_dict(data_root: Path, meta_csv: Path) -> dict:
    as_of = date(2024, 6, 1)
    return {
        "universe": {"source": "static", "symbols": ["A", "B", "C"]},
        "data": {
            "source": "csv",
            "root": str(data_root),
            "freq": "1d",
            "adjust": "",
            # start/end are filled in by ScreenAppConfig._coerce_empty_sections
        },
        "meta": {"source": "csv", "csv": str(meta_csv)},
        "as_of": as_of.isoformat(),
        "lookback_days": 120,
        "calendar_enabled": False,
        "filters": [],
        "rules": [
            {"type": "momentum", "lookback": 60, "weight": 1.0},
        ],
        "execution": {"max_workers": 2, "show_progress": False},
        "output": {"top_n": 3},
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_run_screen_job_completed(data_root, meta_csv, job_store):
    """Happy-path: job transitions to COMPLETED with non-empty picks."""
    from alphaagent.api.runner_screen import run_screen_job

    config = _config_dict(data_root, meta_csv)
    job = job_store.create(kind="screen")

    run_screen_job(job, config)

    assert job.status == JobStatus.COMPLETED
    result = job.result
    assert result is not None
    assert isinstance(result["symbols"], list)
    assert len(result["symbols"]) > 0
    assert all(s in {"A", "B", "C"} for s in result["symbols"])
    assert isinstance(result["picks"], list)
    assert len(result["picks"]) > 0

    # Each pick must have final_score and reasons
    first_pick = result["picks"][0]
    assert "final_score" in first_pick
    assert "reasons" in first_pick
    assert isinstance(first_pick["reasons"], list)


def test_run_screen_job_pick_fields(data_root, meta_csv, job_store):
    """PickDTO fields are all present and correctly typed."""
    from alphaagent.api.runner_screen import run_screen_job

    config = _config_dict(data_root, meta_csv)
    job = job_store.create(kind="screen")
    run_screen_job(job, config)

    assert job.status == JobStatus.COMPLETED
    for pick in job.result["picks"]:
        assert "symbol" in pick
        assert "final_score" in pick
        assert isinstance(pick["final_score"], float)
        assert "reasons" in pick
        for r in pick["reasons"]:
            assert "rule_name" in r
            assert "score" in r
            assert "detail" in r


def test_run_screen_job_result_metadata(data_root, meta_csv, job_store):
    """ScreenResultDTO metadata fields are present."""
    from alphaagent.api.runner_screen import run_screen_job

    config = _config_dict(data_root, meta_csv)
    job = job_store.create(kind="screen")
    run_screen_job(job, config)

    result = job.result
    assert "generated_at" in result
    assert "resolved_as_of" in result
    assert "universe_name" in result
    assert "universe_size" in result
    assert result["universe_size"] == 3
    assert "filtered_size" in result
    assert "rules_applied" in result
    assert isinstance(result["rules_applied"], list)


def test_run_screen_job_progress_updated(data_root, meta_csv, job_store):
    """Progress should reach 1.0 at completion."""
    from alphaagent.api.runner_screen import run_screen_job

    config = _config_dict(data_root, meta_csv)
    job = job_store.create(kind="screen")
    run_screen_job(job, config)

    assert job.progress == 1.0


def test_run_screen_job_failed_on_bad_config(tmp_env, job_store):
    """Bad config triggers FAILED status with an error message."""
    from alphaagent.api.runner_screen import run_screen_job

    bad_config = {"universe": {"source": "static", "symbols": ["X"]}}
    job = job_store.create(kind="screen")
    run_screen_job(job, bad_config)

    assert job.status == JobStatus.FAILED
    assert job.error is not None
    assert ":" in job.error  # format is "ExceptionType: message"


def test_screen_result_to_dto(data_root, meta_csv):
    """screen_result_to_dto helper converts a ScreenResult correctly."""
    from datetime import date as date_type

    from alphaagent.api.runner_screen import screen_result_to_dto
    from alphaagent.screener.base import Pick, Reason, ScreenResult

    result = ScreenResult(
        generated_at=date_type(2024, 6, 1),
        resolved_as_of=date_type(2024, 6, 1),
        universe_name="static",
        universe_size=3,
        filtered_size=2,
        rules_applied=["momentum (weight=1.00)"],
        universe_snapshot=["A", "B", "C"],
        picks=[
            Pick(
                symbol="A",
                name="ACo",
                final_score=0.9,
                reasons=[Reason("momentum", 0.9, {"return_60d": 0.12})],
                metadata={"industry": "科技", "list_date": "2010-01-01"},
            ),
            Pick(
                symbol="B",
                name="BCo",
                final_score=0.5,
                reasons=[Reason("momentum", 0.5, {"return_60d": 0.05})],
                metadata={"industry": "科技", "list_date": "2010-01-01"},
            ),
        ],
    )

    dto = screen_result_to_dto(result, top_n=2)

    assert dto.universe_name == "static"
    assert dto.universe_size == 3
    assert dto.filtered_size == 2
    assert dto.symbols == ["A", "B"]
    assert len(dto.picks) == 2
    assert dto.picks[0].symbol == "A"
    assert dto.picks[0].final_score == pytest.approx(0.9)
    assert dto.picks[0].reasons[0].rule_name == "momentum"
    assert dto.generated_at == "2024-06-01"
    assert dto.resolved_as_of == "2024-06-01"
