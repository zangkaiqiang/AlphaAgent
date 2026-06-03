from alphaagent.fundamentals.news import NewsItem, StaticNewsProvider


def test_static_news_provider():
    items = [NewsItem(title="t1", date="2026-06-01", source="东财", url="u1", summary="s1")]
    p = StaticNewsProvider({"600000": items})
    got = p.recent_news("600000", limit=5)
    assert got[0].title == "t1"
    assert p.recent_news("999999") == []
