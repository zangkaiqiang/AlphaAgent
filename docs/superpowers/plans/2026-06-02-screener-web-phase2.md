# Screener Web (Phase 2) Implementation Plan

> Phase 2 of the web-only migration (roadmap: `2026-06-02-sqlite-persistence-design.md` §14).
> Goal: expose the screener over HTTP + a real web page so the CLI `screen` / `list-screen-rules`
> commands can be removed in Phase 3 without losing functionality.

**Tech:** stdlib + FastAPI + pydantic (backend); Vue 3 + Element Plus + axios (frontend).
**Test cmd:** `uv run --extra data --extra api pytest ...`; frontend type-check `cd web && npm run build`.

## Design decisions (made autonomously; user delegated)
- Screening is slow/network-heavy (~300 symbols) → **async job**, reusing Phase-1 `JobStore`/`jobs` table.
- Add a **`kind` column** to `jobs` (`'backtest'` default, `'screen'` for screens) so the two job
  listings don't mix. Idempotent migration (`ALTER TABLE ... ADD COLUMN` guarded by PRAGMA check).
- Screener `Job` uses the generic `progress`(0..1) + `result`(picks dict); it does NOT use
  `bars_*`/`fill_count` (those stay 0). The screener `JobInfo` DTO omits bar fields.
- Extract screener builders out of `cli.py` into `alphaagent/screener/build.py` (reusable by API and,
  until Phase 3, by cli). Use `SqliteBarCache` + `get_database()` for the screener data source.
- New router `alphaagent/api/routers/screeners.py` (prefix `/api/screeners`), lifecycle identical to
  `backtests.py`. Sync `GET /api/screeners/rules` lists builtin rules+filters (replaces `list-screen-rules`).

---

## Task 1: jobs `kind` column + JobStore filtering

**Files:** Modify `alphaagent/storage/db.py` (schema + migration), `alphaagent/api/job_store.py`; Test `tests/test_job_store.py` (extend).

- `db.py`: add `kind TEXT NOT NULL DEFAULT 'backtest'` to the `jobs` CREATE TABLE. In `init_schema`, after `executescript`, run an idempotent migration: if `kind` not in `PRAGMA table_info(jobs)`, `ALTER TABLE jobs ADD COLUMN kind TEXT NOT NULL DEFAULT 'backtest'`.
- `job_store.py`: `Job` gains `kind: str = "backtest"` (place among business fields, before runtime fields). `_job_to_row`/`_row_to_job`/`_INSERT` include `kind`. `JobStore.create(label=None, kind="backtest")`. `JobStore.list(kind: str | None = None)` filters in-memory by kind when given. `_hydrate` reads kind.
- Tests: `kind` round-trips through persist+hydrate; `list(kind="screen")` returns only screen jobs; default kind is `'backtest'`; existing backtest tests unaffected.
- Verify: `uv run --extra data --extra api pytest tests/test_job_store.py -v`. Commit `feat(jobs): add job kind for backtest/screen separation`.

## Task 2: screener builders module

**Files:** Create `alphaagent/screener/build.py`; Modify `alphaagent/cli.py` to import from it; Test `tests/test_screener_build.py`.

- Move `_build_universe`, `_build_meta_provider`, and a data-source builder out of `cli.py` into `build.py` as public funcs: `build_universe(cfg)`, `build_meta_provider(cfg)`, `build_screen_data_source(cfg)`. `build_screen_data_source` wraps the upstream (csv/akshare/tushare per `cfg.data`) with `SqliteBarCache(source, get_database(), source_id_for_data_cfg(cfg.data))` when `cfg.data.cache_dir` is set (reuse `alphaagent.runtime.source_id_for_data_cfg`).
- `cli.py`: replace its local `_build_universe`/`_build_meta_provider`/`_build_screen_data_source` with imports from `build.py` (keep cli working until Phase 3).
- Test: `build_universe` returns StaticUniverse for a static config; `build_screen_data_source` returns a SqliteBarCache when cache_dir set (mirror test_runtime_wiring isolation: set ALPHAAGENT_DB env, clear _INSTANCES).
- Commit `refactor(screener): extract reusable build helpers from cli`.

## Task 3: screener job runner + result DTO

**Files:** Create `alphaagent/api/schemas/screener.py`, `alphaagent/api/runner_screen.py`; Test `tests/test_screener_runner.py`.

- `schemas/screener.py`: `ScreenSubmitRequest{config: dict, label: str|None=None}`; `ScreenJobInfo{id,label,status,progress,picks_count:int,started_at,completed_at,error}`; `PickDTO{symbol,name,final_score,reasons:list[ReasonDTO],metadata:dict}`, `ReasonDTO{rule_name,score,detail:dict}`; `ScreenResultDTO{generated_at,resolved_as_of,universe_name,universe_size,filtered_size,rules_applied:list[str],symbols:list[str],picks:list[PickDTO]}`.
- `runner_screen.py`: `run_screen_job(job, config_dict)` mirroring `run_backtest_job`: `cfg = ScreenAppConfig(**config_dict)`; build universe/filters/rules (via `build_filter`/`build_rule`/`split_rules`)/data_source/meta_provider/calendar; construct `ScreenerPipeline(...)`; run with a progress callback that updates `job.progress` (and store picks_count via `job.update(result=...)` at end). On success set `job.result = ScreenResultDTO(...).model_dump(mode="json")` and status COMPLETED; on error FAILED. (ScreenerPipeline has `show_progress`; pass a progress hook if supported, else update progress coarsely — check the pipeline's run() for a progress_callback; if none, set progress 0→1 around the run.)
- Test (offline): StaticUniverse(["A","B","C"]) + CSV data source (write 3 tiny CSVs in tmp) + CSVMetaProvider (tmp csv) + one `momentum` or `above_ma` rule + no filters; run `run_screen_job` against a Job; assert status COMPLETED and result has picks/symbols. Use a tmp Database via ALPHAAGENT_DB.
- Commit `feat(api): screener job runner + result DTO`.

## Task 4: screeners router + rules endpoint + registration

**Files:** Create `alphaagent/api/routers/screeners.py`; Modify `alphaagent/api/main.py`, `alphaagent/api/deps.py` (a `get_screen_job_store`? NO — reuse the same JobStore singleton); Test `tests/test_api_screener.py`.

- Router (prefix `/api/screeners`): `POST ""` (submit → `store.create(label=req.label, kind="screen")` + `background_tasks.add_task(run_screen_job, job, req.config)` → `{job_id}`); `GET ""` (`store.list(kind="screen")` → ScreenJobInfo list); `GET /{id}`; `GET /{id}/result` (only terminal/completed); `DELETE /{id}` (cancel); `WS /{id}/ws` (mirror backtests). Add `GET /rules` (sync): list `BUILTIN_ABSOLUTE_RULES`, `BUILTIN_XS_RULES`, `BUILTIN_FILTERS` with type key + category (absolute/cross_sectional/filter) + class name + inferred constructor params (mirror the `_infer_param_specs` approach in `routers/strategies.py`). NOTE: `GET /rules` must be declared BEFORE `GET /{id}` so "rules" isn't captured as an id, or use a distinct path; verify routing.
- Reuse `get_job_store` from deps (same singleton; kind separates).
- `main.py`: `from alphaagent.api.routers import screeners` + `app.include_router(screeners.router, prefix="/api/screeners", tags=["screeners"])`.
- Tests (mirror test_api.py isolation fixture): submit a static/CSV screen → poll to completed → result has symbols; `GET /api/screeners` lists it and `GET /api/backtests` does NOT (kind separation); `GET /api/screeners/rules` returns the builtin catalog.
- Commit `feat(api): screeners router + rules catalog`.

## Task 5: frontend screener page

**Files:** Create `web/src/api/screener.ts`; Modify `web/src/api/types.ts`, `web/src/pages/screener/Index.vue`, `web/src/router/index.ts`.
- `types.ts`: add `ScreenerJobInfo`, `ScreenResult`, `PickItem`, `RuleInfo`/`FilterInfo`.
- `api/screener.ts`: mirror `backtest.ts` — `submit/get/list/result/cancel/watch` against `/screeners`, plus `listRules()` → `/screeners/rules`.
- `pages/screener/Index.vue`: replace stub. Left panel: a form to build a screen config (universe source + index_code or static symbols, as_of, lookback_days, a few filters toggles, rule weights from the rules catalog, output top_n). Right panel: submit → progress → picks table (symbol/name/final_score + expandable reasons). Follow `pages/backtest/Index.vue` structure (submit→watch(WS)→result). Keep it functional; UX polish can follow.
- `router/index.ts`: remove `enabled: false` (or set true) on the screener route.
- Verify: `cd web && npm run build` (vue-tsc + vite build) passes with no type errors. (Visual/functional behaviour needs the user to run it — flagged.)
- Commit `feat(web): screener page wired to API`.

## Acceptance (Phase 2)
1. `uv run --extra data --extra api pytest -q` green; `ruff check` no new errors.
2. `GET /api/screeners/rules` lists builtin rules+filters; an offline (static+CSV) screen job completes and returns picks; screen jobs and backtest jobs list separately.
3. `cd web && npm run build` succeeds (type-checked).
4. cli `screen`/`list-screen-rules` still work (until Phase 3) via the extracted builders.
