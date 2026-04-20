"""Pipeline integration: end-to-end with synthetic data, no network."""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import pytest

from alphaagent.calendar.ashare import AShareCalendar
from alphaagent.data.csv_source import CSVDataSource
from alphaagent.screener.base import Reason
from alphaagent.screener.filters import MinPrice
from alphaagent.screener.meta import CSVMetaProvider
from alphaagent.screener.pipeline import ScreenerPipeline, _weighted_normalize
from alphaagent.screener.rules_builtin import AboveMA, Momentum
from alphaagent.screener.universe import StaticUniverse

# ──────────────────────────────────────────────────────────────────────────────
# Synthetic CSV fixtures so tests don't hit the network
# ──────────────────────────────────────────────────────────────────────────────


def _write_csv(path: Path, closes: list[float], start: date) -> None:
    rows = []
    for i, c in enumerate(closes):
        d = start + timedelta(days=i)
        rows.append((d.isoformat(), c, c, c, c, 1000, 1e8))
    df = pd.DataFrame(rows, columns=["date", "open", "high", "low", "close", "volume", "amount"])
    df.to_csv(path, index=False)


@pytest.fixture
def synthetic_root(tmp_path):
    root = tmp_path / "data"
    root.mkdir()
    start = date(2024, 1, 1)
    # winner: monotonic up
    _write_csv(root / "WIN.csv", [10 + i * 0.5 for i in range(120)], start)
    # loser: monotonic down (and also under min_price by the end)
    _write_csv(root / "LOS.csv", [50 - i * 0.4 for i in range(120)], start)
    # mid: oscillates around 20
    _write_csv(root / "MID.csv", [20 + (i % 5 - 2) for i in range(120)], start)
    return root


@pytest.fixture
def meta_csv(tmp_path):
    p = tmp_path / "meta.csv"
    p.write_text(
        "symbol,name,industry,list_date\n"
        "WIN,WinCo,科技,2010-01-01\n"
        "LOS,LoseCo,科技,2010-01-01\n"
        "MID,MidCo,科技,2010-01-01\n"
    )
    return p


# ──────────────────────────────────────────────────────────────────────────────
# Weight normalization (pure function)
# ──────────────────────────────────────────────────────────────────────────────


def test_weighted_normalize_uses_only_present_rules():
    reasons = [Reason("a", 1.0), Reason("b", 0.0)]
    weights = {"a": 0.4, "b": 0.6, "c": 0.0}
    # both rules present → weighted avg
    assert _weighted_normalize(reasons, weights) == pytest.approx(0.4)


def test_weighted_normalize_drops_missing_from_denominator():
    # Only rule 'a' fired (weight=0.4); 'b' (weight=0.6) is missing.
    # Result should be 1.0, not 0.4 (no penalty for missing).
    reasons = [Reason("a", 1.0)]
    weights = {"a": 0.4, "b": 0.6}
    assert _weighted_normalize(reasons, weights) == pytest.approx(1.0)


def test_weighted_normalize_empty_returns_zero():
    assert _weighted_normalize([], {"a": 1.0}) == 0.0


def test_weight_scaling_invariant():
    """Weights 0.4/0.2/0.2/0.2 should give same result as 4/2/2/2."""
    reasons = [Reason("a", 1.0), Reason("b", 0.5), Reason("c", 0.0), Reason("d", 0.0)]
    w1 = {"a": 0.4, "b": 0.2, "c": 0.2, "d": 0.2}
    w2 = {"a": 4, "b": 2, "c": 2, "d": 2}
    assert _weighted_normalize(reasons, w1) == pytest.approx(_weighted_normalize(reasons, w2))


# ──────────────────────────────────────────────────────────────────────────────
# Pipeline end-to-end
# ──────────────────────────────────────────────────────────────────────────────


def _make_pipeline(synthetic_root, meta_csv, **overrides):
    defaults = dict(
        universe=StaticUniverse(["WIN", "LOS", "MID"]),
        data_source=CSVDataSource(synthetic_root),
        meta_provider=CSVMetaProvider(meta_csv),
        absolute_rules=[AboveMA(period=10, weight=0.5)],
        xs_rules=[Momentum(lookback=30, weight=0.5)],
        filters=[],
        as_of=date(2024, 4, 20),
        lookback_days=120,
        calendar=None,
        max_workers=2,
        show_progress=False,
    )
    defaults.update(overrides)
    return ScreenerPipeline(**defaults)


def test_pipeline_ranks_winner_first(synthetic_root, meta_csv):
    pipe = _make_pipeline(synthetic_root, meta_csv)
    result = pipe.run()
    assert [p.symbol for p in result.picks][0] == "WIN"
    assert result.picks[-1].symbol == "LOS"
    assert result.universe_size == 3
    assert result.filtered_size == 3


def test_pipeline_filter_drops_low_price(synthetic_root, meta_csv):
    """LOS at as_of 2024-04-20 sits around 6 (50 - 110*0.4); WIN around 65;
    MID around 20. min_price=15 drops only LOS.
    """
    pipe = _make_pipeline(
        synthetic_root, meta_csv, filters=[MinPrice(min_price=15.0)]
    )
    result = pipe.run()
    symbols = {p.symbol for p in result.picks}
    assert "LOS" not in symbols
    assert result.filtered_size == 2


def test_pipeline_universe_snapshot_recorded(synthetic_root, meta_csv):
    pipe = _make_pipeline(synthetic_root, meta_csv)
    result = pipe.run()
    assert result.universe_snapshot == ["WIN", "LOS", "MID"]


def test_pipeline_replay_overrides_universe(synthetic_root, meta_csv):
    pipe = _make_pipeline(synthetic_root, meta_csv)
    result = pipe.run(replay_symbols=["WIN", "MID"])
    assert result.universe_snapshot == ["WIN", "MID"]
    assert {p.symbol for p in result.picks} == {"WIN", "MID"}


def test_pipeline_resolves_as_of_to_prior_trading_day(synthetic_root, meta_csv):
    """Sunday 2024-04-21 should snap back to Friday 2024-04-19."""
    cal = AShareCalendar(
        trading_days=[
            date(2024, 4, d) for d in [15, 16, 17, 18, 19]
        ]
    )
    pipe = _make_pipeline(
        synthetic_root,
        meta_csv,
        as_of=date(2024, 4, 21),  # Sunday
        calendar=cal,
    )
    result = pipe.run()
    assert result.resolved_as_of == date(2024, 4, 19)


def test_pipeline_final_score_in_unit_interval(synthetic_root, meta_csv):
    pipe = _make_pipeline(synthetic_root, meta_csv)
    result = pipe.run()
    for p in result.picks:
        assert 0.0 <= p.final_score <= 1.0
