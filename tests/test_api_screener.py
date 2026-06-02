"""FastAPI screener endpoint tests."""

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
def synthetic_screen_data(tmp_path: Path):
    """Write 3 OHLCV CSVs (A, B, C, ~200 rows) + a meta CSV under tmp."""
    rng = np.random.default_rng(42)
    for sym in ["A", "B", "C"]:
        n = 200
        close = 10 + np.linspace(0, 5, n) + rng.normal(0, 0.2, n).cumsum()
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

    # Write meta CSV
    meta_df = pd.DataFrame(
        {"symbol": ["A", "B", "C"], "name": ["Alpha Inc", "Beta Corp", "Gamma Ltd"]}
    )
    meta_csv = tmp_path / "meta.csv"
    meta_df.to_csv(meta_csv, index=False)
    return tmp_path


def _screen_config(data_root: Path, meta_csv: Path) -> dict:
    """Build a minimal ScreenAppConfig dict."""
    return {
        "universe": {
            "source": "static",
            "symbols": ["A", "B", "C"],
        },
        "data": {
            "source": "csv",
            "root": str(data_root),
        },
        "meta": {
            "source": "csv",
            "csv": str(meta_csv),
        },
        "as_of": "2023-10-31",
        "lookback_days": 120,
        "calendar_enabled": False,
        "filters": [],
        "rules": [
            {"type": "momentum", "lookback": 60, "weight": 1.0},
        ],
        "output": {"top_n": 3},
    }


def test_rules_catalog(client):
    """GET /api/screeners/rules → 200, payload has non-empty rules and filters."""
    r = client.get("/api/screeners/rules")
    assert r.status_code == 200
    payload = r.json()
    assert payload["error"] is None
    data = payload["data"]
    assert "rules" in data
    assert "filters" in data
    assert len(data["rules"]) > 0
    assert len(data["filters"]) > 0

    # Check known keys
    rule_types = {item["type"] for item in data["rules"]}
    assert "momentum" in rule_types

    filter_types = {item["type"] for item in data["filters"]}
    assert "min_price" in filter_types

    # Verify params introspection
    momentum_rule = next(r for r in data["rules"] if r["type"] == "momentum")
    param_names = {p["name"] for p in momentum_rule["params"]}
    assert "lookback" in param_names
    assert "weight" in param_names


def test_submit_poll_result(client, synthetic_screen_data):
    """POST config → job_id; poll until terminal; assert completed; check result."""
    meta_csv = synthetic_screen_data / "meta.csv"
    cfg = _screen_config(synthetic_screen_data, meta_csv)

    r = client.post("/api/screeners", json={"config": cfg, "label": "smoke-screen"})
    assert r.status_code == 200
    job_id = r.json()["data"]["job_id"]

    # Poll until terminal
    info = None
    for _ in range(100):
        r = client.get(f"/api/screeners/{job_id}")
        assert r.status_code == 200
        info = r.json()["data"]
        if info["status"] in ("completed", "failed", "cancelled"):
            break
        time.sleep(0.1)

    assert info is not None
    assert info["status"] == "completed", f"Job failed with: {info.get('error')}"

    # Result endpoint returns picks
    r = client.get(f"/api/screeners/{job_id}/result")
    assert r.status_code == 200
    result = r.json()["data"]
    assert "symbols" in result
    assert len(result["symbols"]) > 0


def test_kind_separation(client, synthetic_screen_data):
    """Screen jobs appear in /api/screeners but NOT in /api/backtests."""
    meta_csv = synthetic_screen_data / "meta.csv"
    cfg = _screen_config(synthetic_screen_data, meta_csv)

    r = client.post("/api/screeners", json={"config": cfg, "label": "kind-test"})
    assert r.status_code == 200
    job_id = r.json()["data"]["job_id"]

    # Screener list contains the job
    r = client.get("/api/screeners")
    assert r.status_code == 200
    screen_ids = {j["id"] for j in r.json()["data"]}
    assert job_id in screen_ids

    # Backtest list does NOT contain the screen job
    r = client.get("/api/backtests")
    assert r.status_code == 200
    backtest_ids = {j["id"] for j in r.json()["data"]}
    assert job_id not in backtest_ids
