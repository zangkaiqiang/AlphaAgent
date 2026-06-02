from alphaagent.config import AppConfig
from alphaagent.data.sqlite_cache import SqliteBarCache
from alphaagent.runtime import build_data_source


def _cfg(tmp_path, cache_on: bool):
    data = {
        "source": "csv", "root": str(tmp_path), "symbols": ["A"],
        "start": "2023-01-01", "end": "2023-12-31",
    }
    if cache_on:
        data["cache_dir"] = str(tmp_path / "cache")
    return AppConfig(
        data=data,
        strategy={"name": "ma_cross", "params": {}},
        storage={"db_path": str(tmp_path / "t.db")},
    )


def test_build_data_source_wraps_with_sqlite_when_cache_on(tmp_path):
    src = build_data_source(_cfg(tmp_path, cache_on=True))
    assert isinstance(src, SqliteBarCache)


def test_build_data_source_unwrapped_when_cache_off(tmp_path):
    src = build_data_source(_cfg(tmp_path, cache_on=False))
    assert not isinstance(src, SqliteBarCache)
