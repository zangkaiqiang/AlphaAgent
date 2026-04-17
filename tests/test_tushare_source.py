"""Structural tests for the Tushare source. Network calls are not exercised."""

from __future__ import annotations

import pytest

from alphaagent.data.tushare_source import TushareDataSource, _ts_symbol


def test_ts_symbol_infers_exchange():
    assert _ts_symbol("600000") == "600000.SH"
    assert _ts_symbol("688001") == "688001.SH"
    assert _ts_symbol("000001") == "000001.SZ"
    assert _ts_symbol("300750") == "300750.SZ"
    assert _ts_symbol("430047") == "430047.BJ"
    assert _ts_symbol("600000.SH") == "600000.SH"


def test_ts_symbol_rejects_unknown_prefix():
    with pytest.raises(ValueError):
        _ts_symbol("999999")


def test_constructor_requires_token(monkeypatch):
    monkeypatch.delenv("TUSHARE_TOKEN", raising=False)
    with pytest.raises(ValueError):
        TushareDataSource()


def test_constructor_accepts_explicit_token():
    src = TushareDataSource(token="dummy")
    assert src.token == "dummy"
    assert src.adjust == "qfq"
