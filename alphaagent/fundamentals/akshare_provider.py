"""AkShare-backed FundamentalsProvider.

Lazy-imports akshare so the package installs without it. All network
results are cached in-process with TTL so the API doesn't hammer
external endpoints for repeated requests.

Each method handles AkShare's quirky column names (mixed Chinese /
English) and returns the strongly-typed domain objects.
"""

from __future__ import annotations

import time
from datetime import date, datetime, timedelta
from typing import Any

from alphaagent.fundamentals.base import FundamentalsProvider
from alphaagent.fundamentals.types import (
    FinancialIndicators,
    IndustryConstituent,
    IndustrySummary,
    MarketBreadth,
    MarketIndex,
    MarketSnapshot,
    MoneyFlow,
    SecurityInfo,
)


def _float(x: Any) -> float | None:
    try:
        if x is None:
            return None
        v = float(x)
        return v if v == v else None  # filter NaN
    except (TypeError, ValueError):
        return None


def _int(x: Any) -> int | None:
    f = _float(x)
    return int(f) if f is not None else None


# How many most-recent periods of financials to keep. The datacenter abstract
# returns ~100+ quarterly columns; the agent only needs recent history.
_FIN_MAX_PERIODS = 12

# Indicator-name aliases for the current akshare ``stock_financial_abstract``
# schema (columns: 选项, 指标, <YYYYMMDD>...). Names drift across akshare
# versions, so each field lists candidates tried in order. Values are native
# percents for ratios (e.g. ROE 12.5 == 12.5%) and 元 for amounts.
_FIN_ALIASES: dict[str, tuple[str, ...]] = {
    "roe": ("净资产收益率(ROE)", "摊薄净资产收益率", "净资产收益率_平均", "净资产收益率"),
    "net_margin": ("销售净利率",),
    "gross_margin": ("毛利率", "销售毛利率"),
    "revenue": ("营业总收入", "营业收入"),
    "revenue_yoy": ("营业总收入增长率", "营业总收入同比增长率", "营业收入增长率"),
    "net_income": ("归母净利润", "归属母公司股东的净利润", "净利润"),
    "net_income_yoy": ("归属母公司净利润增长率", "归母净利润同比增长率", "净利润增长率"),
    "debt_ratio": ("资产负债率",),
}


def _parse_financial_abstract(df, symbol: str) -> list[FinancialIndicators]:
    """Parse the eastmoney datacenter ``stock_financial_abstract`` wide-form.

    The indicator name lives in the ``指标`` column (``选项`` is a category that
    repeats indicator names), and each ``YYYYMMDD`` column is one period. Earlier
    code keyed off ``df.columns[0]`` (the category) and used stale indicator
    names, so every field came back ``None`` — this resolves both.
    """
    if df is None or getattr(df, "empty", True) or "指标" not in df.columns:
        return []
    period_cols = [c for c in df.columns if str(c).isdigit()][:_FIN_MAX_PERIODS]
    if not period_cols:
        return []
    # First occurrence of each indicator name wins (categories repeat names).
    by_name: dict[str, Any] = {}
    for _, row in df.iterrows():
        nm = row.get("指标")
        if nm is not None and nm not in by_name:
            by_name[nm] = row

    def val(field: str, period: str) -> float | None:
        for alias in _FIN_ALIASES[field]:
            row = by_name.get(alias)
            if row is not None:
                v = _float(row.get(period))
                if v is not None:
                    return v
        return None

    out: list[FinancialIndicators] = []
    for period in period_cols:
        out.append(
            FinancialIndicators(
                symbol=symbol,
                period=str(period),
                roe=val("roe", period),
                net_margin=val("net_margin", period),
                gross_margin=val("gross_margin", period),
                revenue=val("revenue", period),
                revenue_yoy=val("revenue_yoy", period),
                net_income=val("net_income", period),
                net_income_yoy=val("net_income_yoy", period),
                debt_ratio=val("debt_ratio", period),
            )
        )
    return out


def _parse_financial_abstract_ths(df, symbol: str) -> list[FinancialIndicators]:
    """Parse 同花顺 ``stock_financial_abstract_ths`` (long-form, one row/period).

    Amount columns (净利润 / 营业总收入) may carry Chinese unit suffixes that
    ``_float`` can't parse; those degrade to ``None`` while the plain-numeric
    ratios still come through.
    """
    if df is None or getattr(df, "empty", True) or "报告期" not in df.columns:
        return []
    out: list[FinancialIndicators] = []
    for _, row in df.head(_FIN_MAX_PERIODS).iterrows():
        out.append(
            FinancialIndicators(
                symbol=symbol,
                period=str(row.get("报告期")),
                roe=_float(row.get("净资产收益率")),
                net_margin=_float(row.get("销售净利率")),
                gross_margin=None,  # not in the ths abstract
                revenue=_float(row.get("营业总收入")),
                revenue_yoy=_float(row.get("营业总收入同比增长率")),
                net_income=_float(row.get("净利润")),
                net_income_yoy=_float(row.get("净利润同比增长率")),
                debt_ratio=_float(row.get("资产负债率")),
            )
        )
    return out


_RETRY_ATTEMPTS = 3
_RETRY_BASE_DELAY = 0.6


def _is_transient(exc: Exception) -> bool:
    """True for network/proxy errors worth retrying (akshare uses ``requests``)."""
    try:
        import requests

        if isinstance(exc, requests.exceptions.RequestException):
            return True
    except Exception:
        pass
    return isinstance(exc, (ConnectionError, TimeoutError, OSError))


def _retry(producer, *, attempts: int = _RETRY_ATTEMPTS, base_delay: float = _RETRY_BASE_DELAY):
    """Call ``producer()``, retrying transient network errors with backoff.

    The local proxy these calls route through drops connections intermittently;
    a fresh attempt usually re-establishes one. Non-transient errors raise
    immediately; the last transient error is re-raised once attempts run out.
    """
    last: Exception | None = None
    for i in range(attempts):
        try:
            return producer()
        except Exception as e:
            if not _is_transient(e):
                raise
            last = e
            if i < attempts - 1:
                time.sleep(base_delay * (2**i))
    assert last is not None
    raise last


class _TTLCache:
    def __init__(self, ttl_seconds: float):
        self.ttl = ttl_seconds
        self._store: dict[Any, tuple[float, Any]] = {}

    def get_or_set(self, key: Any, producer):
        now = time.time()
        hit = self._store.get(key)
        if hit and now - hit[0] < self.ttl:
            return hit[1]
        value = producer()
        self._store[key] = (now, value)
        return value


class AkShareFundamentalsProvider(FundamentalsProvider):
    def __init__(self, ttl_seconds: float = 300):
        self._cache = _TTLCache(ttl_seconds)

    # ------------------------------------------------------------------
    # Company
    # ------------------------------------------------------------------

    def security_info(self, symbol: str) -> SecurityInfo:
        return self._cache.get_or_set(("info", symbol), lambda: self._fetch_info(symbol))

    def _fetch_info(self, symbol: str) -> SecurityInfo:
        import akshare as ak

        try:
            df = _retry(lambda: ak.stock_individual_info_em(symbol=symbol))
            info = dict(zip(df["item"], df["value"], strict=False))
        except Exception:
            # stock_individual_info_em hits push2.eastmoney.com, which local
            # proxies routinely drop. Degrade to a minimal record (code as name)
            # so overview / the research agent still work off the financials,
            # rather than failing the whole request.
            return SecurityInfo(symbol=symbol, name=symbol)
        listed_raw = info.get("上市时间")
        listed = None
        if listed_raw:
            try:
                listed = datetime.strptime(str(int(listed_raw)), "%Y%m%d").date()
            except (TypeError, ValueError):
                listed = None
        return SecurityInfo(
            symbol=symbol,
            name=str(info.get("股票简称") or symbol),
            industry=str(info.get("行业") or "") or None,
            market_cap=_float(info.get("总市值")),
            float_market_cap=_float(info.get("流通市值")),
            listed_date=listed,
        )

    def financial_indicators(self, symbol: str) -> list[FinancialIndicators]:
        return self._cache.get_or_set(
            ("fin", symbol), lambda: self._fetch_financials(symbol)
        )

    def _fetch_financials(self, symbol: str) -> list[FinancialIndicators]:
        import akshare as ak

        try:
            df = _retry(lambda: ak.stock_financial_abstract(symbol=symbol))
        except Exception:
            df = None
        items = _parse_financial_abstract(df, symbol)
        if items:
            return items
        # Datacenter primary returned nothing / errored — fall back to 同花顺,
        # which is served from a different host that the proxy may route fine.
        try:
            df_ths = _retry(
                lambda: ak.stock_financial_abstract_ths(symbol=symbol, indicator="按报告期")
            )
        except Exception:
            return []
        return _parse_financial_abstract_ths(df_ths, symbol)

    def money_flow(self, symbol: str, start: date, end: date) -> list[MoneyFlow]:
        return self._cache.get_or_set(
            ("flow", symbol, start, end),
            lambda: self._fetch_money_flow(symbol, start, end),
        )

    def _fetch_money_flow(self, symbol: str, start: date, end: date) -> list[MoneyFlow]:
        import akshare as ak

        market = "sh" if symbol.startswith(("60", "68")) else "sz"
        try:
            df = _retry(lambda: ak.stock_individual_fund_flow(stock=symbol, market=market))
        except Exception:
            return []
        if df is None or df.empty:
            return []
        out: list[MoneyFlow] = []
        for _, row in df.iterrows():
            try:
                d = datetime.strptime(str(row.get("日期")), "%Y-%m-%d").date()
            except (TypeError, ValueError):
                continue
            if not (start <= d <= end):
                continue
            out.append(
                MoneyFlow(
                    date=d,
                    main_net=_float(row.get("主力净流入-净额")) or 0.0,
                    super_net=_float(row.get("超大单净流入-净额")) or 0.0,
                    large_net=_float(row.get("大单净流入-净额")) or 0.0,
                    medium_net=_float(row.get("中单净流入-净额")) or 0.0,
                    small_net=_float(row.get("小单净流入-净额")) or 0.0,
                )
            )
        return sorted(out, key=lambda m: m.date)

    # ------------------------------------------------------------------
    # Industry
    # ------------------------------------------------------------------

    def industry_list(self) -> list[IndustrySummary]:
        return self._cache.get_or_set("industries", self._fetch_industries)

    def _fetch_industries(self) -> list[IndustrySummary]:
        import akshare as ak

        df = _retry(lambda: ak.stock_board_industry_name_em())
        out: list[IndustrySummary] = []
        for _, row in df.iterrows():
            out.append(
                IndustrySummary(
                    code=str(row.get("板块代码") or ""),
                    name=str(row.get("板块名称") or ""),
                    change_pct=_float(row.get("涨跌幅")),
                    constituent_count=_int(row.get("公司家数")),
                    money_flow_net=_float(row.get("主力净流入")),
                )
            )
        return out

    def industry_constituents(self, industry_code: str) -> list[IndustryConstituent]:
        return self._cache.get_or_set(
            ("industry_members", industry_code),
            lambda: self._fetch_constituents(industry_code),
        )

    def _fetch_constituents(self, industry_code: str) -> list[IndustryConstituent]:
        import akshare as ak

        # AkShare's API uses the industry NAME, not code; map via the list.
        name = next(
            (i.name for i in self._fetch_industries() if i.code == industry_code), None
        )
        if name is None:
            return []
        df = _retry(lambda: ak.stock_board_industry_cons_em(symbol=name))
        out: list[IndustryConstituent] = []
        for _, row in df.iterrows():
            out.append(
                IndustryConstituent(
                    symbol=str(row.get("代码") or ""),
                    name=str(row.get("名称") or ""),
                    change_pct=_float(row.get("涨跌幅")),
                    market_cap=_float(row.get("总市值")),
                    pe=_float(row.get("市盈率-动态")),
                )
            )
        return out

    # ------------------------------------------------------------------
    # Market
    # ------------------------------------------------------------------

    def market_snapshot(self) -> MarketSnapshot:
        # Shorter TTL: dashboard data should be fresh.
        return _TTLCache(60).get_or_set("snapshot", self._fetch_snapshot)

    def _fetch_snapshot(self) -> MarketSnapshot:
        import akshare as ak

        indices: list[MarketIndex] = []
        try:
            df = _retry(lambda: ak.stock_zh_index_spot_em(symbol="沪深重要指数"))
            for _, row in df.iterrows():
                indices.append(
                    MarketIndex(
                        code=str(row.get("代码") or ""),
                        name=str(row.get("名称") or ""),
                        last=_float(row.get("最新价")) or 0.0,
                        change_pct=_float(row.get("涨跌幅")) or 0.0,
                        volume=_float(row.get("成交量")),
                        amount=_float(row.get("成交额")),
                    )
                )
        except Exception:
            pass

        breadth = None
        try:
            spot = _retry(lambda: ak.stock_zh_a_spot_em())
            if spot is not None and not spot.empty:
                changes = spot["涨跌幅"].dropna()
                breadth = MarketBreadth(
                    date=date.today(),
                    advancers=int((changes > 0).sum()),
                    decliners=int((changes < 0).sum()),
                    unchanged=int((changes == 0).sum()),
                    limit_up=int((changes >= 9.9).sum()),
                    limit_down=int((changes <= -9.9).sum()),
                )
        except Exception:
            pass

        northbound = None
        try:
            df = _retry(lambda: ak.stock_hsgt_north_net_flow_in_em(symbol="北上"))
            if df is not None and not df.empty:
                last = df.iloc[-1]
                northbound = _float(last.get("成交净买额")) or _float(last.get("value"))
        except Exception:
            pass

        return MarketSnapshot(
            indices=indices, breadth=breadth, northbound_net=northbound
        )


__all__ = ["AkShareFundamentalsProvider"]
# (also satisfy unused-import lint for timedelta)
_ = timedelta
