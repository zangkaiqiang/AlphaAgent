"""Tests for alphaagent.screener.build – reusable builder helpers."""

from __future__ import annotations


def test_build_universe_static():
    from types import SimpleNamespace

    from alphaagent.screener.build import build_universe
    from alphaagent.screener.universe import StaticUniverse

    cfg = SimpleNamespace(
        universe=SimpleNamespace(
            source="static", symbols=["600000", "000001"], index_code=None
        )
    )
    u = build_universe(cfg)
    assert isinstance(u, StaticUniverse)


def test_build_universe_unknown_raises():
    from types import SimpleNamespace

    from alphaagent.screener.build import build_universe

    cfg = SimpleNamespace(
        universe=SimpleNamespace(source="bad_source", symbols=None, index_code=None)
    )
    import pytest

    with pytest.raises(ValueError, match="unknown universe source"):
        build_universe(cfg)


def test_build_meta_provider_csv(tmp_path):
    from types import SimpleNamespace

    import pandas as pd

    from alphaagent.screener.build import build_meta_provider
    from alphaagent.screener.meta import CSVMetaProvider

    csv_path = tmp_path / "meta.csv"
    pd.DataFrame(
        {"symbol": ["600000"], "name": ["招商银行"], "industry": ["银行"]}
    ).to_csv(csv_path, index=False)

    cfg = SimpleNamespace(
        meta=SimpleNamespace(source="csv", csv=str(csv_path), cache_dir=None)
    )
    provider = build_meta_provider(cfg)
    assert isinstance(provider, CSVMetaProvider)


def test_build_meta_provider_unknown_raises():
    from types import SimpleNamespace

    import pytest

    from alphaagent.screener.build import build_meta_provider

    cfg = SimpleNamespace(
        meta=SimpleNamespace(source="unknown", csv=None, cache_dir=None)
    )
    with pytest.raises(ValueError, match="unknown meta source"):
        build_meta_provider(cfg)


def test_build_screen_data_source_csv_no_cache(tmp_path):
    from types import SimpleNamespace

    from alphaagent.data.csv_source import CSVDataSource
    from alphaagent.screener.build import build_screen_data_source

    data = SimpleNamespace(
        source="csv",
        root=str(tmp_path),
        adjust=None,
        cache_dir=None,
        freq="1d",
        tushare_token=None,
        akshare_backend=None,
    )
    cfg = SimpleNamespace(data=data)
    src = build_screen_data_source(cfg)
    assert isinstance(src, CSVDataSource)


def test_build_screen_data_source_wraps_sqlite_when_cache(tmp_path, monkeypatch):
    from types import SimpleNamespace

    monkeypatch.setenv("ALPHAAGENT_DB", str(tmp_path / "t.db"))
    from alphaagent.storage import db as _dbmod

    _dbmod._INSTANCES.clear()

    from alphaagent.data.sqlite_cache import SqliteBarCache
    from alphaagent.screener.build import build_screen_data_source

    data = SimpleNamespace(
        source="csv",
        root=str(tmp_path),
        adjust="qfq",
        cache_dir=str(tmp_path / "cache"),
        freq="1d",
        tushare_token=None,
        akshare_backend="eastmoney",
    )
    cfg = SimpleNamespace(data=data)
    src = build_screen_data_source(cfg)
    assert isinstance(src, SqliteBarCache)


def test_build_screen_data_source_csv_missing_root_raises():
    from types import SimpleNamespace

    import pytest

    from alphaagent.screener.build import build_screen_data_source

    data = SimpleNamespace(
        source="csv",
        root=None,
        adjust=None,
        cache_dir=None,
        freq="1d",
        tushare_token=None,
        akshare_backend=None,
    )
    cfg = SimpleNamespace(data=data)
    with pytest.raises(ValueError, match="data.root is required"):
        build_screen_data_source(cfg)
