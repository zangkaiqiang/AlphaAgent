"""News (资讯) provider. Lazy akshare; static stub for tests."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class NewsItem:
    title: str
    date: str | None = None
    source: str | None = None
    url: str | None = None
    summary: str | None = None


class NewsProvider(ABC):
    @abstractmethod
    def recent_news(self, symbol: str, limit: int = 10) -> list[NewsItem]: ...


class StaticNewsProvider(NewsProvider):
    def __init__(self, by_symbol: dict[str, list[NewsItem]] | None = None):
        self._by = by_symbol or {}

    def recent_news(self, symbol: str, limit: int = 10) -> list[NewsItem]:
        return list(self._by.get(symbol, []))[:limit]


def _retry(producer, *, attempts: int = 3, base_delay: float = 0.6):
    import time

    last: Exception | None = None
    for i in range(attempts):
        try:
            return producer()
        except Exception as e:
            try:
                import requests

                transient = isinstance(e, requests.exceptions.RequestException)
            except Exception:
                transient = False
            if not (transient or isinstance(e, (ConnectionError, TimeoutError, OSError))):
                raise
            last = e
            if i < attempts - 1:
                time.sleep(base_delay * (2**i))
    assert last is not None
    raise last


# Label applied to fallback market-wide items so the research agent attributes
# them as market context rather than company-specific news.
MARKET_NEWS_SOURCE = "全球财经快讯（市场）"


class AkShareNewsProvider(NewsProvider):
    """Per-symbol news via ``stock_news_em`` (eastmoney).

    That endpoint currently fails to parse on some akshare/pandas combos
    (ArrowInvalid) and is also proxy-sensitive. When it yields nothing we fall
    back to market-wide 资讯 (``stock_info_global_em``), clearly labeled so the
    report doesn't misattribute it to the company. Never raises — returns ``[]``
    when nothing is reachable.
    """

    def recent_news(self, symbol: str, limit: int = 10) -> list[NewsItem]:
        items = self._symbol_news(symbol, limit)
        if items:
            return items
        return self._market_news(limit)

    def _symbol_news(self, symbol: str, limit: int) -> list[NewsItem]:
        import akshare as ak

        try:
            df = _retry(lambda: ak.stock_news_em(symbol=symbol))
        except Exception:
            return []
        if df is None or df.empty:
            return []
        out: list[NewsItem] = []
        for _, r in df.head(limit).iterrows():
            out.append(
                NewsItem(
                    title=str(r.get("新闻标题") or r.get("title") or ""),
                    date=str(r.get("发布时间") or r.get("date") or "") or None,
                    source=str(r.get("文章来源") or r.get("source") or "") or None,
                    url=str(r.get("新闻链接") or r.get("url") or "") or None,
                    summary=str(r.get("新闻内容") or r.get("summary") or "")[:300] or None,
                )
            )
        return out

    def _market_news(self, limit: int) -> list[NewsItem]:
        import akshare as ak

        try:
            df = _retry(lambda: ak.stock_info_global_em())
        except Exception:
            return []
        if df is None or df.empty:
            return []
        out: list[NewsItem] = []
        for _, r in df.head(limit).iterrows():
            out.append(
                NewsItem(
                    title=str(r.get("标题") or "") or "",
                    date=str(r.get("发布时间") or "") or None,
                    source=MARKET_NEWS_SOURCE,
                    url=str(r.get("链接") or "") or None,
                    summary=str(r.get("摘要") or "")[:300] or None,
                )
            )
        return out


__all__ = [
    "NewsItem",
    "NewsProvider",
    "StaticNewsProvider",
    "AkShareNewsProvider",
    "MARKET_NEWS_SOURCE",
]
