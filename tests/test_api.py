"""FastAPI endpoint tests using synthetic CSV data."""

from __future__ import annotations

import time
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from alphaagent.api.deps import get_job_store
from alphaagent.api.main import app


@pytest.fixture(autouse=True)
def _isolated_db(tmp_path, monkeypatch):
    """Each test gets its own SQLite DB + a fresh JobStore."""
    monkeypatch.setenv("ALPHAAGENT_DB", str(tmp_path / "test.db"))
    from alphaagent.storage import db as _dbmod
    _dbmod._INSTANCES.clear()
    get_job_store.cache_clear()
    yield
    get_job_store.cache_clear()
    _dbmod._INSTANCES.clear()


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def synthetic_data(tmp_path: Path) -> Path:
    rng = np.random.default_rng(7)
    for sym in ["A", "B"]:
        n = 80
        close = 10 + np.linspace(0, 2, n) + rng.normal(0, 0.1, n).cumsum()
        close = np.maximum(close, 1.0)
        df = pd.DataFrame(
            {
                "date": pd.date_range("2023-01-03", periods=n, freq="B"),
                "open": close,
                "high": close * 1.01,
                "low": close * 0.99,
                "close": close,
                "volume": 1_000_000,
                "amount": close * 1_000_000,
            }
        )
        df.to_csv(tmp_path / f"{sym}.csv", index=False)
    return tmp_path


def _config(data_root: Path) -> dict:
    return {
        "data": {
            "source": "csv",
            "root": str(data_root),
            "symbols": ["A", "B"],
            "start": "2023-01-01",
            "end": "2023-12-31",
        },
        "strategy": {
            "name": "ma_cross",
            "params": {"fast": 5, "slow": 20},
        },
        "portfolio": {"initial_cash": 1_000_000, "target_pct": 0.3},
    }


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json() == {"data": {"status": "ok"}, "error": None}


def test_list_strategies_returns_all_builtins(client):
    r = client.get("/api/strategies")
    assert r.status_code == 200
    payload = r.json()
    assert payload["error"] is None
    names = {s["name"] for s in payload["data"]}
    assert {"ma_cross", "rsi_mean_reversion", "bollinger_breakout"} <= names
    # MA cross param introspection should pick up fast / slow.
    ma = next(s for s in payload["data"] if s["name"] == "ma_cross")
    param_names = {p["name"] for p in ma["params"]}
    assert {"fast", "slow"} <= param_names


def test_backtest_submit_and_poll_to_completion(client, synthetic_data):
    cfg = _config(synthetic_data)
    r = client.post("/api/backtests", json={"config": cfg, "label": "smoke"})
    assert r.status_code == 200
    job_id = r.json()["data"]["job_id"]

    # Poll until terminal.
    for _ in range(50):
        r = client.get(f"/api/backtests/{job_id}")
        info = r.json()["data"]
        if info["status"] in ("completed", "failed", "cancelled"):
            break
        time.sleep(0.05)
    assert info["status"] == "completed", info
    assert info["progress"] == 1.0
    assert info["bars_processed"] > 0

    # Result endpoint returns the full DTO.
    r = client.get(f"/api/backtests/{job_id}/result")
    assert r.status_code == 200
    result = r.json()["data"]
    assert "performance" in result
    assert "equity_curve" in result
    assert result["performance"]["max_drawdown"] <= 0
    assert isinstance(result["equity_curve"], list)


def test_backtest_invalid_config_fails_job(client):
    bad = {"data": {"source": "csv", "symbols": []}}  # missing required fields
    r = client.post("/api/backtests", json={"config": bad})
    job_id = r.json()["data"]["job_id"]
    for _ in range(50):
        info = client.get(f"/api/backtests/{job_id}").json()["data"]
        if info["status"] in ("completed", "failed"):
            break
        time.sleep(0.05)
    assert info["status"] == "failed"
    assert info["error"]


def test_list_jobs_returns_submitted_ones(client, synthetic_data):
    cfg = _config(synthetic_data)
    job_id = client.post("/api/backtests", json={"config": cfg}).json()["data"]["job_id"]
    r = client.get("/api/backtests")
    ids = {j["id"] for j in r.json()["data"]}
    assert job_id in ids


def test_get_unknown_job_returns_404(client):
    r = client.get("/api/backtests/nonexistent")
    assert r.status_code == 404


def test_jobs_survive_store_restart(client, synthetic_data):
    import time as _t

    from alphaagent.api.deps import get_job_store

    cfg = _config(synthetic_data)
    job_id = client.post("/api/backtests", json={"config": cfg}).json()["data"]["job_id"]
    for _ in range(50):
        info = client.get(f"/api/backtests/{job_id}").json()["data"]
        if info["status"] in ("completed", "failed"):
            break
        _t.sleep(0.05)
    assert info["status"] == "completed"

    # Drop the cached store; a new one must hydrate the finished job from SQLite.
    get_job_store.cache_clear()
    listed = client.get("/api/backtests").json()["data"]
    assert job_id in {j["id"] for j in listed}
