import sys
from types import ModuleType

import pandas as pd
import pytest

from alphaagent.fundamentals.news import (
    MARKET_NEWS_SOURCE,
    AkShareNewsProvider,
    NewsItem,
    StaticNewsProvider,
)


def test_static_news_provider():
    items = [NewsItem(title="t1", date="2026-06-01", source="东财", url="u1", summary="s1")]
    p = StaticNewsProvider({"600000": items})
    got = p.recent_news("600000", limit=5)
    assert got[0].title == "t1"
    assert p.recent_news("999999") == []


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch):
    import time

    monkeypatch.setattr(time, "sleep", lambda *a, **k: None)


def _fake_ak(monkeypatch, **funcs):
    fake = ModuleType("akshare")
    for name, fn in funcs.items():
        setattr(fake, name, fn)
    monkeypatch.setitem(sys.modules, "akshare", fake)


def test_symbol_news_used_when_available(monkeypatch):
    def stock_news_em(symbol):
        return pd.DataFrame(
            {
                "新闻标题": ["利好公告"],
                "发布时间": ["2026-06-01 09:00:00"],
                "文章来源": ["东方财富"],
                "新闻链接": ["https://x/1"],
                "新闻内容": ["公司发布了..."],
            }
        )

    def global_must_not_be_called():
        raise AssertionError("market fallback must not run when symbol news works")

    _fake_ak(monkeypatch, stock_news_em=stock_news_em,
             stock_info_global_em=global_must_not_be_called)
    items = AkShareNewsProvider().recent_news("600000", limit=5)
    assert len(items) == 1
    assert items[0].title == "利好公告"
    assert items[0].source == "东方财富"


def test_falls_back_to_market_news_on_parse_bug(monkeypatch):
    def stock_news_em(symbol):
        # mimic the real akshare ArrowInvalid parse failure (non-transient)
        raise ValueError("Invalid regular expression: invalid escape sequence: \\u")

    def stock_info_global_em():
        return pd.DataFrame(
            {
                "标题": ["央行公开市场操作", "A股震荡"],
                "摘要": ["逆回购投放...", "三大指数..."],
                "发布时间": ["2026-06-02 12:00:00", "2026-06-02 13:00:00"],
                "链接": ["https://x/a", "https://x/b"],
            }
        )

    _fake_ak(monkeypatch, stock_news_em=stock_news_em,
             stock_info_global_em=stock_info_global_em)
    items = AkShareNewsProvider().recent_news("600000", limit=5)
    assert len(items) == 2
    assert items[0].title == "央行公开市场操作"
    # clearly labeled as market-level, not company-specific
    assert items[0].source == MARKET_NEWS_SOURCE
    assert items[0].url == "https://x/a"


def test_returns_empty_when_both_unavailable(monkeypatch):
    def boom_symbol(symbol):
        raise ValueError("parse bug")

    def boom_market():
        raise ConnectionError("proxy dropped")

    _fake_ak(monkeypatch, stock_news_em=boom_symbol, stock_info_global_em=boom_market)
    assert AkShareNewsProvider().recent_news("600000") == []
