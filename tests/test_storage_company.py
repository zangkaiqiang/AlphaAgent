from alphaagent.storage.db import Database


def test_financials_and_analysis_tables(tmp_path):
    db = Database(str(tmp_path / "t.db"))
    db.execute(
        "INSERT OR REPLACE INTO financials "
        "(symbol,period,roe,net_margin,gross_margin,revenue,revenue_yoy,"
        "net_income,net_income_yoy,debt_ratio,fetched_at) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        ("600000", "2024", 0.12, 0.3, 0.4, 1e9, 0.05, 3e8, 0.06, 0.5, "2026-06-03T00:00:00"),
    )
    assert db.query("SELECT roe FROM financials WHERE symbol='600000'")[0]["roe"] == 0.12

    db.execute(
        "INSERT OR REPLACE INTO company_analysis "
        "(id,symbol,generated_at,rating,confidence,summary,reasons_json,risks_json,model,context_json) "
        "VALUES (?,?,?,?,?,?,?,?,?,?)",
        ("a1", "600000", "2026-06-03T00:00:00", "BUY", 0.7, "ok", "[]", "[]", "m", "{}"),
    )
    rows = db.query("SELECT rating FROM company_analysis WHERE symbol='600000'")
    assert rows[0]["rating"] == "BUY"
