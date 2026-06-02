from datetime import date

import pandas as pd

from alphaagent.storage.db import Database


def _write_parquet(path, idx):
    df = pd.DataFrame(
        {
            "open": range(len(idx)), "high": range(len(idx)),
            "low": range(len(idx)), "close": range(len(idx)),
            "volume": [100] * len(idx), "amount": [200] * len(idx),
        },
        index=idx,
    )
    df.to_parquet(path)
    return df


def test_migrate_bars_imports_and_skips_legacy(tmp_path):
    from scripts.migrate_cache import migrate_bars

    cache = tmp_path / "cache"
    cache.mkdir()
    idx = pd.date_range("2023-01-03", "2023-01-31", freq="B")
    _write_parquet(cache / "600000_1d__akshare-sina-qfq.parquet", idx)
    _write_parquet(cache / "600001_1d.parquet", idx)  # legacy: no __source_id

    db = Database(str(tmp_path / "t.db"))
    imported, rows, skipped = migrate_bars(db, str(cache))

    assert imported == 1
    assert skipped == 1
    assert rows == len(idx)
    n = db.query(
        "SELECT COUNT(*) AS n FROM bars WHERE source_id='akshare-sina-qfq' "
        "AND symbol='600000' AND freq='1d'"
    )[0]["n"]
    assert n == len(idx)


def test_migrate_calendar(tmp_path):
    from scripts.migrate_cache import migrate_calendar

    cal_path = tmp_path / "cal.parquet"
    pd.DataFrame(
        {"trade_date": pd.to_datetime([date(2024, 1, 2), date(2024, 1, 3)])}
    ).to_parquet(cal_path)

    db = Database(str(tmp_path / "t.db"))
    n = migrate_calendar(db, str(cal_path))
    assert n == 2
    assert db.query("SELECT COUNT(*) AS n FROM trade_calendar")[0]["n"] == 2
