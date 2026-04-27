"""Screening pipeline.

Orchestrates: as_of normalization → universe → fetch → meta → filter →
two-pass scoring (absolute then cross-sectional) → weighted normalization
→ ranking → ScreenResult.

See ``docs/screener-design.md`` §3.4 for the executable spec.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import date, datetime, timedelta

import pandas as pd

logger = logging.getLogger(__name__)

from alphaagent.calendar.ashare import AShareCalendar
from alphaagent.data.base import DataSource
from alphaagent.screener.base import Pick, Reason, ScreenResult
from alphaagent.screener.fetcher import fetch_panel
from alphaagent.screener.filters import HardFilter
from alphaagent.screener.meta import StockMeta, StockMetaProvider
from alphaagent.screener.rules import AbsoluteRule, CrossSectionalRule
from alphaagent.screener.universe import Universe


class ScreenerPipeline:
    def __init__(
        self,
        universe: Universe,
        data_source: DataSource,
        meta_provider: StockMetaProvider,
        absolute_rules: list[AbsoluteRule],
        xs_rules: list[CrossSectionalRule],
        filters: list[HardFilter],
        as_of: date,
        lookback_days: int,
        calendar: AShareCalendar | None = None,
        max_workers: int = 16,
        show_progress: bool = True,
        freq: str = "1d",
        max_fetch_failure_rate: float = 0.1,
        max_per_industry: int | None = None,
    ):
        if lookback_days < 1:
            raise ValueError("lookback_days must be >= 1")
        if not 0.0 <= max_fetch_failure_rate <= 1.0:
            raise ValueError("max_fetch_failure_rate must be in [0, 1]")
        if max_per_industry is not None and max_per_industry < 1:
            raise ValueError("max_per_industry must be >= 1 when set")
        self.universe = universe
        self.data_source = data_source
        self.meta_provider = meta_provider
        self.absolute_rules = list(absolute_rules)
        self.xs_rules = list(xs_rules)
        self.filters = list(filters)
        self.as_of = as_of
        self.lookback_days = lookback_days
        self.calendar = calendar
        self.max_workers = max_workers
        self.show_progress = show_progress
        self.freq = freq
        self.max_fetch_failure_rate = max_fetch_failure_rate
        self.max_per_industry = max_per_industry

    @property
    def all_rules(self) -> list[AbsoluteRule | CrossSectionalRule]:
        return [*self.absolute_rules, *self.xs_rules]

    def run(self, replay_symbols: list[str] | None = None) -> ScreenResult:
        resolved = self._resolve_as_of(self.as_of)
        symbols = (
            list(replay_symbols)
            if replay_symbols is not None
            else self.universe.get_symbols(resolved)
        )
        snapshot = list(symbols)

        # Pull a generous window so rules with the longest lookback have data.
        # ``lookback_days`` is in *calendar* days; daily bars roughly need
        # 1.5x to cover weekends/holidays, but DataSource will handle slicing.
        start = resolved - timedelta(days=int(self.lookback_days * 1.5) + 7)

        fetch_result = fetch_panel(
            self.data_source,
            symbols,
            start=start,
            end=resolved,
            freq=self.freq,
            max_workers=self.max_workers,
            show_progress=self.show_progress,
            desc="Fetching bars",
        )
        panel = fetch_result.bars
        if fetch_result.failed:
            # Already logged at WARN by fetcher; raise if the universe has
            # collapsed past the threshold so callers don't silently rank
            # on a fraction of the intended pool.
            if fetch_result.failure_rate > self.max_fetch_failure_rate:
                raise RuntimeError(
                    f"fetch failure rate {fetch_result.failure_rate:.1%} "
                    f"exceeds max_fetch_failure_rate={self.max_fetch_failure_rate:.1%}; "
                    f"{len(fetch_result.failed)} of {len(symbols)} symbols failed"
                )

        meta_map = self.meta_provider.get_meta_batch(symbols, resolved)

        kept: dict[str, pd.DataFrame] = {}
        for sym, bars in panel.items():
            meta = meta_map.get(sym, StockMeta(symbol=sym, name=sym))
            if all(f.keep(sym, bars, meta) for f in self.filters):
                kept[sym] = bars

        per_symbol_reasons: dict[str, list[Reason]] = {sym: [] for sym in kept}

        for rule in self.absolute_rules:
            for sym, bars in kept.items():
                reason = rule.evaluate(bars)
                if reason is not None:
                    per_symbol_reasons[sym].append(reason)

        for rule in self.xs_rules:
            xs_results = rule.evaluate_all(kept)
            for sym, reason in xs_results.items():
                if sym in per_symbol_reasons:
                    per_symbol_reasons[sym].append(reason)

        rule_weights = {r.name: r.weight for r in self.all_rules}
        picks: list[Pick] = []
        for sym, reasons in per_symbol_reasons.items():
            final_score = _weighted_normalize(reasons, rule_weights)
            meta = meta_map.get(sym, StockMeta(symbol=sym, name=sym))
            picks.append(
                Pick(
                    symbol=sym,
                    name=meta.name,
                    final_score=final_score,
                    reasons=reasons,
                    metadata={
                        "industry": meta.industry,
                        "list_date": (
                            meta.list_date.isoformat() if meta.list_date else None
                        ),
                    },
                )
            )

        picks.sort(key=lambda p: p.final_score, reverse=True)

        if self.max_per_industry is not None:
            picks = _apply_industry_cap(picks, self.max_per_industry)

        return ScreenResult(
            generated_at=date.today(),
            resolved_as_of=resolved,
            universe_name=self.universe.name(),
            universe_size=len(snapshot),
            filtered_size=len(kept),
            rules_applied=[
                f"{r.name} (weight={r.weight:.2f})" for r in self.all_rules
            ],
            universe_snapshot=snapshot,
            picks=picks,
        )

    def _resolve_as_of(self, d: date) -> date:
        if self.calendar is None:
            return d
        if self.calendar.is_trading_day(d):
            return d
        return self.calendar.prev_trading_day(d)


def _weighted_normalize(
    reasons: list[Reason], rule_weights: dict[str, float]
) -> float:
    """Weighted score with a fixed denominator over *all* configured rules.

    A rule that didn't produce a Reason (e.g. not enough bars) contributes
    0 to the numerator but its full weight stays in the denominator. This
    prevents a symbol that only hit 1 of N rules from tying a symbol that
    hit all N — the earlier "drop missing from denominator" behavior let
    thin coverage inflate final_score to 1.0.
    """
    total_weight = sum(rule_weights.values())
    if total_weight == 0.0:
        return 0.0
    weighted = sum(
        rule_weights.get(r.rule_name, 0.0) * r.score for r in reasons
    )
    return weighted / total_weight


def _apply_industry_cap(picks: list[Pick], max_per_industry: int) -> list[Pick]:
    """Keep picks in score order, dropping ones that exceed the per-industry
    quota. Picks with unknown industry share a single "(unknown)" bucket —
    this is conservative: when we can't place a pick we treat it as
    fungible with other unplaceable picks rather than letting the cap
    silently fail open.
    """
    counts: dict[str, int] = defaultdict(int)
    kept: list[Pick] = []
    for p in picks:
        industry = (p.metadata or {}).get("industry") or "(unknown)"
        if counts[industry] < max_per_industry:
            kept.append(p)
            counts[industry] += 1
    return kept


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")
