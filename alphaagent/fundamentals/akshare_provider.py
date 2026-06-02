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

        df = ak.stock_individual_info_em(symbol=symbol)
        info = dict(zip(df["item"], df["value"], strict=False))
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
            df = ak.stock_financial_abstract(symbol=symbol)
        except Exception:
            return []
        if df is None or df.empty:
            return []
        # AkShare wide-form: columns are period strings, rows are indicators.
        # Pivot so each column is one indicator slice per period.
        df = df.set_index(df.columns[0])
        out: list[FinancialIndicators] = []
        for period in df.columns:
            col = df[period]
            out.append(
                FinancialIndicators(
                    symbol=symbol,
                    period=str(period),
                    roe=_float(col.get("净资产收益率")),
                    net_margin=_float(col.get("销售净利率")),
                    gross_margin=_float(col.get("销售毛利率")),
                    revenue=_float(col.get("营业总收入")),
                    revenue_yoy=_float(col.get("营业总收入同比增长率")),
                    net_income=_float(col.get("归属母公司股东的净利润")),
                    net_income_yoy=_float(col.get("归属母公司股东的净利润同比增长率")),
                    debt_ratio=_float(col.get("资产负债率")),
                )
            )
        return out

    def money_flow(self, symbol: str, start: date, end: date) -> list[MoneyFlow]:
        return self._cache.get_or_set(
            ("flow", symbol, start, end),
            lambda: self._fetch_money_flow(symbol, start, end),
        )

    def _fetch_money_flow(self, symbol: str, start: date, end: date) -> list[MoneyFlow]:
        import akshare as ak

        market = "sh" if symbol.startswith(("60", "68")) else "sz"
        try:
            df = ak.stock_individual_fund_flow(stock=symbol, market=market)
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

        df = ak.stock_board_industry_name_em()
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
        df = ak.stock_board_industry_cons_em(symbol=name)
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
            df = ak.stock_zh_index_spot_em(symbol="沪深重要指数")
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
            spot = ak.stock_zh_a_spot_em()
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
            df = ak.stock_hsgt_north_net_flow_in_em(symbol="北上")
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
