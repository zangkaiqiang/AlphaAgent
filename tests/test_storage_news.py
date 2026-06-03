from alphaagent.storage.db import Database


def test_news_table_and_report_json_column(tmp_path):
    db = Database(str(tmp_path / "t.db"))
    db.execute(
        "INSERT OR REPLACE INTO news (symbol,url,title,date,source,summary,fetched_at) "
        "VALUES (?,?,?,?,?,?,?)",
        ("600000", "http://x/1", "标题", "2026-06-01", "东财", "摘要", "2026-06-03T00:00:00"),
    )
    assert db.query("SELECT title FROM news WHERE symbol='600000'")[0]["title"] == "标题"
    db.execute(
        "INSERT OR REPLACE INTO company_analysis "
        "(id,symbol,generated_at,rating,confidence,summary,reasons_json,risks_json,model,context_json,report_json) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        ("r1", "600000", "2026-06-03T00:00:00", "BUY", 0.7, "s", "[]", "[]", "m", "{}", '{"sections":[]}'),
    )
    assert db.query("SELECT report_json FROM company_analysis WHERE id='r1'")[0]["report_json"] == '{"sections":[]}'
