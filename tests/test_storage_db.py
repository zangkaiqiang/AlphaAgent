import pandas as pd

from alphaagent.storage.db import Database, get_database, resolve_db_path


def test_schema_created_and_crud(tmp_path):
    db = Database(str(tmp_path / "t.db"))
    db.execute(
        "INSERT INTO trade_calendar (dt) VALUES (?)", ("2024-01-02",)
    )
    rows = db.query("SELECT dt FROM trade_calendar")
    assert [r["dt"] for r in rows] == ["2024-01-02"]


def test_query_df_returns_frame(tmp_path):
    db = Database(str(tmp_path / "t.db"))
    db.executemany(
        "INSERT OR REPLACE INTO bars "
        "(source_id,symbol,freq,dt,open,high,low,close,volume,amount) "
        "VALUES (?,?,?,?,?,?,?,?,?,?)",
        [("s", "600000", "1d", "2023-01-03T00:00:00", 1, 1, 1, 1, 10, None)],
    )
    df = db.query_df("SELECT * FROM bars")
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 1
    assert df.iloc[0]["symbol"] == "600000"


def test_get_database_caches_by_path(tmp_path, monkeypatch):
    from alphaagent.storage import db as dbmod
    dbmod._INSTANCES.clear()
    monkeypatch.setenv("ALPHAAGENT_DB", str(tmp_path / "env.db"))
    a = get_database()
    b = get_database()
    assert a is b
    assert resolve_db_path() == str((tmp_path / "env.db").resolve())
    dbmod._INSTANCES.clear()
