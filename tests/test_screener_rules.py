"""Rule semantics: absolute + cross-sectional + percentile_rank helper."""

from __future__ import annotations

import math

import pandas as pd
import pytest

from alphaagent.screener.rules import percentile_rank
from alphaagent.screener.rules_builtin import (
    AboveMA,
    LowVolatility,
    Momentum,
    PriceBreakout,
    Reversal,
    VolumeBreakout,
    build_rule,
    split_rules,
)


def _bars(closes, amounts=None):
    """Build a tiny daily DataFrame with deterministic dates."""
    n = len(closes)
    idx = pd.date_range("2024-01-01", periods=n, freq="D")
    if amounts is None:
        amounts = [1e8] * n
    return pd.DataFrame(
        {
            "open": closes,
            "high": closes,
            "low": closes,
            "close": closes,
            "volume": [1000] * n,
            "amount": amounts,
        },
        index=idx,
    )


# ──────────────────────────────────────────────────────────────────────────────
# percentile_rank helper
# ──────────────────────────────────────────────────────────────────────────────


def test_percentile_rank_high_gets_1():
    out = percentile_rank({"a": 10.0, "b": 5.0, "c": 1.0})
    assert out["a"] == pytest.approx(1.0)
    assert out["b"] == pytest.approx(0.5)
    assert out["c"] == pytest.approx(0.0)


def test_percentile_rank_reverse_low_gets_1():
    out = percentile_rank({"a": 10.0, "b": 5.0, "c": 1.0}, reverse=True)
    assert out["c"] == pytest.approx(1.0)
    assert out["a"] == pytest.approx(0.0)


def test_percentile_rank_singleton():
    assert percentile_rank({"a": 1.0}) == {"a": 0.5}


def test_percentile_rank_empty():
    assert percentile_rank({}) == {}


# ──────────────────────────────────────────────────────────────────────────────
# Absolute: AboveMA
# ──────────────────────────────────────────────────────────────────────────────


def test_above_ma_score_1_when_well_above():
    # close = 20, ma5 = 12 → excess ≈ 0.67, scale 0.10 → clipped to 1.0
    rule = AboveMA(period=5)
    bars = _bars([10, 10, 10, 10, 10, 20])
    r = rule.evaluate(bars)
    assert r is not None and r.score == 1.0


def test_above_ma_score_0_when_below():
    rule = AboveMA(period=5)
    bars = _bars([10, 10, 10, 10, 10, 5])  # ma5 = 9, close = 5 < 9
    r = rule.evaluate(bars)
    assert r is not None and r.score == 0.0


def test_above_ma_score_interior_is_continuous():
    # MA over the last 5 = mean([10,10,10,10,10.5]) = 10.1.
    # excess = 10.5/10.1 - 1 ≈ 0.0396; score = 0.0396/0.10 ≈ 0.396.
    # The important assertion is that the score is strictly interior —
    # old 0/1 scoring would have given 1.0 here.
    rule = AboveMA(period=5, score_scale=0.10)
    bars = _bars([10, 10, 10, 10, 10, 10.5])
    r = rule.evaluate(bars)
    assert r is not None
    assert 0.0 < r.score < 1.0
    assert r.score == pytest.approx(0.396, rel=1e-2)


def test_above_ma_returns_none_when_too_few_bars():
    rule = AboveMA(period=10)
    assert rule.evaluate(_bars([1, 2, 3])) is None


def test_above_ma_rejects_bad_period():
    with pytest.raises(ValueError, match="period must be >= 2"):
        AboveMA(period=1)


# ──────────────────────────────────────────────────────────────────────────────
# Absolute: PriceBreakout
# ──────────────────────────────────────────────────────────────────────────────


def test_price_breakout_hits_when_well_above_prior_high():
    # prior max = 14, close = 15 → excess ≈ 0.071, scale 0.10 → 0.71
    rule = PriceBreakout(lookback=5, score_scale=0.10)
    bars = _bars([10, 11, 12, 13, 14, 15])
    r = rule.evaluate(bars)
    assert r is not None and r.score == pytest.approx(1 / 14 / 0.10, rel=1e-3)


def test_price_breakout_misses_when_equal():
    rule = PriceBreakout(lookback=5)
    bars = _bars([10, 11, 12, 13, 14, 14])  # close 14 == prior max 14
    r = rule.evaluate(bars)
    assert r is not None and r.score == 0.0


def test_price_breakout_clips_at_large_excess():
    # close = 20 vs prior max 10 → excess 1.0, scale 0.10 → clipped to 1.0
    rule = PriceBreakout(lookback=5, score_scale=0.10)
    bars = _bars([10, 10, 10, 10, 10, 20])
    r = rule.evaluate(bars)
    assert r is not None and r.score == 1.0


def test_price_breakout_returns_none_when_short():
    rule = PriceBreakout(lookback=5)
    assert rule.evaluate(_bars([1, 2, 3])) is None


# ──────────────────────────────────────────────────────────────────────────────
# Absolute: VolumeBreakout
# ──────────────────────────────────────────────────────────────────────────────


def test_volume_breakout_above_threshold():
    rule = VolumeBreakout(lookback=5, z_threshold=1.5)
    # prior 5 bars: amount = 100, latest = 250 → mean=100, std=0... need variance.
    # Use varying prior amounts so std > 0.
    bars = _bars([10] * 6, amounts=[100, 110, 90, 100, 100, 250])
    r = rule.evaluate(bars)
    assert r is not None and r.score == 1.0


def test_volume_breakout_zero_when_negative_z():
    rule = VolumeBreakout(lookback=5, z_threshold=1.5)
    bars = _bars([10] * 6, amounts=[100, 110, 90, 100, 100, 50])
    r = rule.evaluate(bars)
    assert r is not None and r.score == 0.0


def test_volume_breakout_returns_none_when_zero_std():
    rule = VolumeBreakout(lookback=5, z_threshold=1.5)
    bars = _bars([10] * 6, amounts=[100] * 6)
    assert rule.evaluate(bars) is None


# ──────────────────────────────────────────────────────────────────────────────
# Cross-sectional: Momentum
# ──────────────────────────────────────────────────────────────────────────────


def test_momentum_higher_return_higher_score():
    rule = Momentum(lookback=5)
    panel = {
        "winner": _bars([10, 11, 12, 13, 14, 20]),     # +100% over 5 bars
        "middle": _bars([10, 10.5, 11, 11.5, 12, 12]),  # +20%
        "loser": _bars([10, 9, 8, 7, 6, 5]),            # -50%
    }
    out = rule.evaluate_all(panel)
    assert out["winner"].score == pytest.approx(1.0)
    assert out["middle"].score == pytest.approx(0.5)
    assert out["loser"].score == pytest.approx(0.0)


def test_momentum_skips_short_data():
    rule = Momentum(lookback=10)
    panel = {"a": _bars([1, 2, 3])}
    assert rule.evaluate_all(panel) == {}


# ──────────────────────────────────────────────────────────────────────────────
# Cross-sectional: Reversal
# ──────────────────────────────────────────────────────────────────────────────


def test_reversal_higher_dropper_higher_score():
    rule = Reversal(lookback=5)
    panel = {
        "dropped": _bars([10, 9, 8, 7, 6, 5]),
        "flat": _bars([10, 10, 10, 10, 10, 10]),
        "rose": _bars([10, 11, 12, 13, 14, 15]),
    }
    out = rule.evaluate_all(panel)
    assert out["dropped"].score == pytest.approx(1.0)
    assert out["rose"].score == pytest.approx(0.0)


# ──────────────────────────────────────────────────────────────────────────────
# Cross-sectional: LowVolatility
# ──────────────────────────────────────────────────────────────────────────────


def test_low_volatility_lower_std_higher_score():
    rule = LowVolatility(lookback=5)
    panel = {
        "calm": _bars([10, 10.01, 10.02, 10.01, 10.02, 10.01]),
        "wild": _bars([10, 12, 8, 14, 7, 11]),
        "mid": _bars([10, 10.5, 10.2, 10.6, 10.3, 10.7]),
    }
    out = rule.evaluate_all(panel)
    # The calm series has near-zero std → highest score
    assert out["calm"].score > out["mid"].score > out["wild"].score
    assert out["calm"].score == pytest.approx(1.0)
    assert out["wild"].score == pytest.approx(0.0)


def test_low_volatility_score_in_unit_interval():
    rule = LowVolatility(lookback=5)
    panel = {"a": _bars([10, 11, 12, 11, 12, 13]), "b": _bars([10, 10.1, 10, 10.1, 10, 10.1])}
    out = rule.evaluate_all(panel)
    for r in out.values():
        assert 0.0 <= r.score <= 1.0
        assert not math.isnan(r.score)


# ──────────────────────────────────────────────────────────────────────────────
# Registry / build_rule / split_rules
# ──────────────────────────────────────────────────────────────────────────────


def test_build_rule_dispatches_correctly():
    r = build_rule({"type": "momentum", "lookback": 30, "weight": 0.5})
    assert isinstance(r, Momentum)
    assert r.lookback == 30
    assert r.weight == 0.5


def test_build_rule_unknown_type():
    with pytest.raises(ValueError, match="unknown rule"):
        build_rule({"type": "nope"})


def test_split_rules_partitions_correctly():
    rules = [Momentum(lookback=10), AboveMA(period=20), Reversal(lookback=5)]
    abs_rules, xs_rules = split_rules(rules)
    assert len(abs_rules) == 1 and isinstance(abs_rules[0], AboveMA)
    assert len(xs_rules) == 2
