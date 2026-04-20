"""Snapshot regression test.

Pins the full pipeline output for a fixed synthetic dataset. Any change
to rule semantics, normalization, or output format will break this — run
``UPDATE_SNAPSHOT=1 pytest tests/test_screener_snapshot.py`` to refresh
intentionally, then review the diff.
"""

from __future__ import annotations

import os
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

from alphaagent.data.csv_source import CSVDataSource
from alphaagent.screener.filters import MinPrice
from alphaagent.screener.meta import CSVMetaProvider
from alphaagent.screener.output import render_picks
from alphaagent.screener.pipeline import ScreenerPipeline
from alphaagent.screener.rules_builtin import (
    AboveMA,
    LowVolatility,
    Momentum,
    VolumeBreakout,
)
from alphaagent.screener.universe import StaticUniverse

SNAPSHOT_PATH = Path(__file__).parent / "snapshots" / "picks.golden.yaml"


def _build_fixtures(tmp_path: Path):
    data = tmp_path / "data"
    data.mkdir()
    start = date(2024, 1, 1)

    def _csv(sym: str, closes: list[float], amounts: list[float] | None = None):
        n = len(closes)
        if amounts is None:
            amounts = [1e8] * n
        rows = [
            ((start + timedelta(days=i)).isoformat(), c, c, c, c, 1000, a)
            for i, (c, a) in enumerate(zip(closes, amounts, strict=True))
        ]
        pd.DataFrame(
            rows,
            columns=["date", "open", "high", "low", "close", "volume", "amount"],
        ).to_csv(data / f"{sym}.csv", index=False)

    # 5 symbols, deterministic deterministic deterministic.
    _csv("UPUP", [10 + i * 0.3 for i in range(120)])
    _csv("DOWN", [50 - i * 0.3 for i in range(120)])
    _csv("FLAT", [25.0] * 120)
    _csv("OSCI", [20 + 2 * (i % 5 - 2) for i in range(120)])
    _csv("VOLS", [30 + (i % 7 - 3) * 1.5 for i in range(120)])

    meta = tmp_path / "meta.csv"
    meta.write_text(
        "symbol,name,industry,list_date\n"
        "UPUP,Upward,科技,2010-01-01\n"
        "DOWN,Downward,科技,2010-01-01\n"
        "FLAT,Flatland,公用,2010-01-01\n"
        "OSCI,Oscillator,材料,2010-01-01\n"
        "VOLS,Volatile,材料,2010-01-01\n"
    )
    return data, meta


def test_pipeline_snapshot(tmp_path):
    data_root, meta_path = _build_fixtures(tmp_path)
    pipe = ScreenerPipeline(
        universe=StaticUniverse(["UPUP", "DOWN", "FLAT", "OSCI", "VOLS"]),
        data_source=CSVDataSource(data_root),
        meta_provider=CSVMetaProvider(meta_path),
        absolute_rules=[
            AboveMA(period=20, weight=0.3),
            VolumeBreakout(lookback=20, z_threshold=1.5, weight=0.2),
        ],
        xs_rules=[
            Momentum(lookback=60, weight=0.3),
            LowVolatility(lookback=20, weight=0.2),
        ],
        filters=[MinPrice(min_price=2.0)],
        as_of=date(2024, 4, 20),
        lookback_days=120,
        calendar=None,
        max_workers=2,
        show_progress=False,
    )
    result = pipe.run()
    # Override generated_at so snapshot stays stable across days.
    result.generated_at = date(2024, 4, 20)

    rendered = render_picks(result, top_n=10, with_reasons="full", fmt="yaml")

    if os.environ.get("UPDATE_SNAPSHOT") == "1":
        SNAPSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)
        SNAPSHOT_PATH.write_text(rendered, encoding="utf-8")

    assert SNAPSHOT_PATH.exists(), (
        f"Snapshot missing — run UPDATE_SNAPSHOT=1 pytest {Path(__file__).name} "
        "to create it after reviewing rendered output."
    )
    expected = SNAPSHOT_PATH.read_text(encoding="utf-8")
    assert rendered == expected, (
        "Pipeline output drifted from snapshot. "
        "If this change is intentional, regenerate with "
        f"UPDATE_SNAPSHOT=1 pytest {Path(__file__).name}"
    )
