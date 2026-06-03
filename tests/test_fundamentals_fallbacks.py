"""Graceful degradation + upstream fallbacks for AkShareFundamentalsProvider.

All akshare calls are faked (no network). Covers:
- security_info degrading to a minimal record when push2.eastmoney.com drops
- financial_indicators falling back to 同花顺 (ths) when the datacenter primary
  returns nothing / errors
"""

from __future__ import annotations

import sys
from types import ModuleType

import pandas as pd
import pytest
import requests

from alphaagent.fundamentals.akshare_provider import AkShareFundamentalsProvider


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch):
    # retry backoff -> no real waiting in tests
    import alphaagent.fundamentals.akshare_provider as mod

    monkeypatch.setattr(mod.time, "sleep", lambda *a, **k: None)


def _fake_ak(monkeypatch, **funcs):
    fake = ModuleType("akshare")
    for name, fn in funcs.items():
        setattr(fake, name, fn)
    monkeypatch.setitem(sys.modules, "akshare", fake)
    return fake


# ---- security_info -------------------------------------------------------

def test_security_info_degrades_on_proxy_drop(monkeypatch):
    def boom(symbol):
        raise requests.exceptions.ProxyError("push2 dropped the tunnel")

    _fake_ak(monkeypatch, stock_individual_info_em=boom)
    p = AkShareFundamentalsProvider(ttl_seconds=0)
    info = p.security_info("600000")
    assert info.symbol == "600000"
    assert info.name == "600000"  # name falls back to the code, no crash
    assert info.industry is None
    assert info.market_cap is None


def test_security_info_happy_path(monkeypatch):
    def ok(symbol):
        return pd.DataFrame(
            {
                "item": ["股票简称", "行业", "总市值", "流通市值", "上市时间"],
                "value": ["浦发银行", "银行", 3.0e11, 2.9e11, "19991110"],
            }
        )

    _fake_ak(monkeypatch, stock_individual_info_em=ok)
    p = AkShareFundamentalsProvider(ttl_seconds=0)
    info = p.security_info("600000")
    assert info.name == "浦发银行"
    assert info.industry == "银行"
    assert info.market_cap == pytest.approx(3.0e11)
    assert info.listed_date is not None and info.listed_date.year == 1999


# ---- financial_indicators fallback --------------------------------------

def test_financials_fall_back_to_ths(monkeypatch):
    def primary_empty(symbol):
        return pd.DataFrame()  # datacenter returns nothing

    def ths(symbol, indicator):
        return pd.DataFrame(
            {
                "报告期": ["2024", "2023"],
                "净资产收益率": ["12.5", "11.0"],
                "销售净利率": ["30.1", "29.0"],
                "资产负债率": ["50.2", "51.0"],
                "营业总收入": ["1.0e9", "0.9e9"],
                "营业总收入同比增长率": ["5.0", "4.0"],
                "净利润": ["3.0e8", "2.7e8"],
                "净利润同比增长率": ["6.0", "5.0"],
            }
        )

    _fake_ak(monkeypatch, stock_financial_abstract=primary_empty,
             stock_financial_abstract_ths=ths)
    p = AkShareFundamentalsProvider(ttl_seconds=0)
    items = p.financial_indicators("600000")
    assert len(items) == 2
    first = items[0]
    assert first.period == "2024"
    assert first.roe == pytest.approx(12.5)
    assert first.net_margin == pytest.approx(30.1)
    assert first.debt_ratio == pytest.approx(50.2)
    assert first.revenue == pytest.approx(1.0e9)
    assert first.revenue_yoy == pytest.approx(5.0)


def test_financials_primary_wins_when_available(monkeypatch):
    def primary(symbol):
        # Real datacenter schema: 选项=category, 指标=indicator name, then period
        # columns. Indicator names match current akshare ('(ROE)' suffix, etc.).
        return pd.DataFrame(
            {
                "选项": ["盈利能力", "盈利能力", "财务风险", "成长能力"],
                "指标": ["净资产收益率(ROE)", "销售净利率", "资产负债率", "营业总收入增长率"],
                "20260331": [2.37, 39.01, 91.83, 5.0],
                "20251231": [10.1, 38.0, 90.0, 4.0],
            }
        )

    def ths_should_not_be_called(symbol, indicator):
        raise AssertionError("ths must not be called when primary has data")

    _fake_ak(monkeypatch, stock_financial_abstract=primary,
             stock_financial_abstract_ths=ths_should_not_be_called)
    p = AkShareFundamentalsProvider(ttl_seconds=0)
    items = p.financial_indicators("600000")
    assert len(items) == 2  # two period columns, most-recent first
    assert items[0].period == "20260331"
    assert items[0].roe == pytest.approx(2.37)  # native percent, not None
    assert items[0].net_margin == pytest.approx(39.01)
    assert items[0].debt_ratio == pytest.approx(91.83)
    assert items[0].revenue_yoy == pytest.approx(5.0)


def test_financials_empty_when_both_fail(monkeypatch):
    def primary_boom(symbol):
        raise requests.exceptions.ConnectionError("down")

    def ths_boom(symbol, indicator):
        raise requests.exceptions.ConnectionError("down")

    _fake_ak(monkeypatch, stock_financial_abstract=primary_boom,
             stock_financial_abstract_ths=ths_boom)
    p = AkShareFundamentalsProvider(ttl_seconds=0)
    assert p.financial_indicators("600000") == []
