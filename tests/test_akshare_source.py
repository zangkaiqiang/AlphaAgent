"""AkShareDataSource backend resolution + sina normalization (no network).

The eastmoney push servers are frequently unreachable behind local proxies,
so daily bars default to the sina upstream. These tests pin that default,
the env override, and the sina column normalization via a faked akshare.
"""

from __future__ import annotations

import sys
from datetime import date
from types import ModuleType

import pandas as pd
import pytest

from alphaagent.data.akshare_source import (
    AkShareDataSource,
    _to_sina_symbol,
    resolve_daily_backend,
)


def test_resolve_backend_defaults_to_sina(monkeypatch):
    monkeypatch.delenv("ALPHAAGENT_AKSHARE_BACKEND", raising=False)
    assert resolve_daily_backend(None) == "sina"


def test_resolve_backend_env_override(monkeypatch):
    monkeypatch.setenv("ALPHAAGENT_AKSHARE_BACKEND", "eastmoney")
    assert resolve_daily_backend(None) == "eastmoney"


def test_resolve_backend_explicit_wins_over_env(monkeypatch):
    monkeypatch.setenv("ALPHAAGENT_AKSHARE_BACKEND", "eastmoney")
    assert resolve_daily_backend("sina") == "sina"


def test_resolve_backend_rejects_garbage(monkeypatch):
    monkeypatch.delenv("ALPHAAGENT_AKSHARE_BACKEND", raising=False)
    with pytest.raises(ValueError, match="daily_backend"):
        resolve_daily_backend("tencent")


def test_default_construction_uses_sina(monkeypatch):
    monkeypatch.delenv("ALPHAAGENT_AKSHARE_BACKEND", raising=False)
    src = AkShareDataSource(adjust="qfq")
    assert src.daily_backend == "sina"


def test_to_sina_symbol():
    assert _to_sina_symbol("600000") == "sh600000"
    assert _to_sina_symbol("000001") == "sz000001"
    assert _to_sina_symbol("300750") == "sz300750"
    assert _to_sina_symbol("688981") == "sh688981"
    assert _to_sina_symbol("830799") == "bj830799"


def _install_fake_akshare(monkeypatch, **funcs):
    fake = ModuleType("akshare")
    for name, fn in funcs.items():
        setattr(fake, name, fn)
    monkeypatch.setitem(sys.modules, "akshare", fake)


def test_sina_get_bars_normalizes(monkeypatch):
    captured = {}

    def fake_daily(symbol, start_date, end_date, adjust):
        captured["symbol"] = symbol
        return pd.DataFrame(
            {
                "date": ["2024-01-02", "2024-01-03"],
                "open": [10.0, 11.0],
                "high": [10.5, 11.5],
                "low": [9.8, 10.9],
                "close": [10.2, 11.2],
                "volume": [1000.0, 2000.0],
                "outstanding_share": [1e8, 1e8],
                "turnover": [0.01, 0.02],
            }
        )

    _install_fake_akshare(monkeypatch, stock_zh_a_daily=fake_daily)
    src = AkShareDataSource(adjust="qfq", daily_backend="sina")
    df = src.get_bars("600000", date(2024, 1, 1), date(2024, 1, 31), freq="1d")

    assert captured["symbol"] == "sh600000"  # sina prefix mapping applied
    assert list(df.columns) == ["open", "high", "low", "close", "volume", "amount"]
    assert len(df) == 2
    # amount synthesized from close*volume when sina omits it
    assert df.iloc[0]["amount"] == pytest.approx(10.2 * 1000.0)
    assert str(df.index[0].date()) == "2024-01-02"


def test_sina_empty_returns_empty(monkeypatch):
    _install_fake_akshare(monkeypatch, stock_zh_a_daily=lambda **kw: pd.DataFrame())
    src = AkShareDataSource(daily_backend="sina")
    df = src.get_bars("600000", date(2024, 1, 1), date(2024, 1, 31))
    assert df.empty
