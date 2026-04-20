"""StockMetaProvider: CSV impl + ST keyword detection + Tushare stub."""

from __future__ import annotations

from datetime import date

import pytest

from alphaagent.screener.meta import (
    CSVMetaProvider,
    TushareMetaProvider,
    name_implies_st,
)


@pytest.fixture
def meta_csv(tmp_path):
    p = tmp_path / "meta.csv"
    p.write_text(
        "symbol,name,industry,list_date\n"
        "600000,浦发银行,银行,1999-11-10\n"
        "000001,平安银行,银行,1991-04-03\n"
        "600519,贵州茅台,白酒,2001-08-27\n"
        "300313,*ST天山,材料,2010-12-15\n"
    )
    return p


def test_csv_meta_basic_fields(meta_csv):
    p = CSVMetaProvider(meta_csv)
    m = p.get_meta("600519", date(2024, 12, 31))
    assert m.symbol == "600519"
    assert m.name == "贵州茅台"
    assert m.industry == "白酒"
    assert m.list_date == date(2001, 8, 27)
    assert m.is_st is False


def test_csv_meta_detects_st_by_name(meta_csv):
    p = CSVMetaProvider(meta_csv)
    m = p.get_meta("300313", date(2024, 12, 31))
    assert m.is_st is True


def test_csv_meta_unknown_symbol_returns_placeholder(meta_csv):
    p = CSVMetaProvider(meta_csv)
    m = p.get_meta("999999", date(2024, 12, 31))
    assert m.name == "999999"
    assert m.industry is None


def test_csv_meta_zero_pads_symbols(tmp_path):
    p = tmp_path / "meta.csv"
    p.write_text("symbol,name\n1,平安银行\n")
    provider = CSVMetaProvider(p)
    m = provider.get_meta("000001", date(2024, 1, 1))
    assert m.name == "平安银行"


def test_csv_meta_batch_returns_all(meta_csv):
    p = CSVMetaProvider(meta_csv)
    out = p.get_meta_batch(["600519", "000001"], date(2024, 12, 31), max_workers=2)
    assert set(out.keys()) == {"600519", "000001"}
    assert out["000001"].name == "平安银行"


def test_name_implies_st_keywords():
    assert name_implies_st("*ST天山")
    assert name_implies_st("ST中安")
    assert name_implies_st("退市股A")
    assert not name_implies_st("贵州茅台")


def test_tushare_meta_raises():
    with pytest.raises(NotImplementedError, match="2000 points"):
        TushareMetaProvider().get_meta("600000", date(2024, 1, 1))
