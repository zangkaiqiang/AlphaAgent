from datetime import date

import pandas as pd
import pytest

from alphaagent.analytics.company_agent import (
    DataUnavailable,
    assemble_company_context,
    load_persisted_financials,
)
from alphaagent.fundamentals.types import FinancialIndicators
from alphaagent.storage.db import Database


class _FakeBars:
    def __init__(self, df, fail=False):
        self._df, self._fail = df, fail

    def get_bars(self, symbol, start, end, freq="1d"):
        if self._fail:
            return pd.DataFrame()
        return self._df


class _FakeProvider:
    def __init__(self, items=None, raises=False):
        self._items, self._raises = items or [], raises

    def financial_indicators(self, symbol):
        if self._raises:
            raise ConnectionError("proxy down")
        return self._items


def _bars(n=260):
    idx = pd.date_range("2023-01-02", periods=n, freq="B")
    close = pd.Series(range(1, n + 1), index=idx, dtype=float)
    return pd.DataFrame(
        {"open": close, "high": close, "low": close, "close": close, "volume": 100, "amount": 100},
        index=idx,
    )


def _fin(period):
    return FinancialIndicators(
        symbol="600000", period=period, roe=0.12, net_margin=0.3, gross_margin=0.4,
        revenue=1e9, revenue_yoy=0.05, net_income=3e8, net_income_yoy=0.06, debt_ratio=0.5,
    )


def test_context_has_technical_and_persists_financials(tmp_path):
    db = Database(str(tmp_path / "t.db"))
    ctx = assemble_company_context(
        "600000", _FakeBars(_bars()), _FakeProvider([_fin("2023"), _fin("2024")]), db
    )
    assert ctx["symbol"] == "600000"
    assert "5d" in ctx["technical"]["returns"]
    assert ctx["technical"]["last_price"] == 260.0
    assert ctx["data_complete"] is True
    assert len(ctx["financials"]) == 2
    assert load_persisted_financials(db, "600000")[0].roe == 0.12


def test_fallback_to_persisted_when_fetch_fails(tmp_path):
    db = Database(str(tmp_path / "t.db"))
    assemble_company_context("600000", _FakeBars(_bars()), _FakeProvider([_fin("2023")]), db)
    ctx = assemble_company_context("600000", _FakeBars(_bars()), _FakeProvider(raises=True), db)
    assert ctx["data_complete"] is False
    assert len(ctx["financials"]) == 1


def test_raises_when_no_bars_and_no_financials(tmp_path):
    db = Database(str(tmp_path / "t.db"))
    with pytest.raises(DataUnavailable):
        assemble_company_context("999999", _FakeBars(_bars(), fail=True), _FakeProvider(raises=True), db)
