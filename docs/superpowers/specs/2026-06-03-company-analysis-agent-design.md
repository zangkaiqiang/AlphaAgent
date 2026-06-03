# 公司分析智能体 设计

- 日期:2026-06-03
- 状态:待实现
- 关联:[[web-only-direction]];复用 Phase 1 的 SQLite 存储层(`alphaagent/storage/db.py`)与现有 agent 层(`alphaagent/agent/`)。

## 1. 目标

用户**只输入公司代码(symbol)**,系统:
1. 自动联网拉取**轻量**数据(避开卡代理的 90 字段大请求 `stock_individual_info_em`);
2. 把拉到的信息**持久化**到 SQLite;
3. 用 LLM 做**综合分析**,输出**买入/持有/卖出 + 置信度 + 看多理由 + 风险点 + 摘要 + 免责声明**;
4. 分析结果也持久化(留历史)。

同步调用(一次 Claude 调用 ~5-20s),在公司分析页一个「AI 智能分析」按钮触发。

**明确取舍(已确认):** 同步;模型默认 `claude-sonnet-4-6`;分析**不含公司名/行业**(避开大请求);分析结果保留历史;拉取失败回退到上次持久化副本。

## 2. 数据流

```
symbol
 → 日K线: SqliteBarCache(AkShareDataSource) → 落 bars 表(已有);算技术面特征
 → 财务: provider.financial_indicators(symbol)(带重试)→ upsert 到 financials 表
          拉取失败 → 回退读 financials 表上次持久化副本
 → 组装 CompanyContext(symbol + 技术面 + 财务[近 N 期])
 → CompanyAnalyst.analyze(context) → Claude(JSON 结构化 + prompt caching)
 → 落 company_analysis 表
 → 返回 CompanyAnalysisDTO
```

技术面特征(复用 `alphaagent/analytics/company.py` 纯函数 + 少量新增):多窗口收益 `rolling_return(closes,[5,20,60,120,250])`、当前/最大回撤 `drawdown_curve`、年化波动率、最新收盘价、相对 MA20/MA60 趋势(上/下穿)。

## 3. 持久化(扩 `alphaagent/storage/db.py`)

幂等建表(`CREATE TABLE IF NOT EXISTS`,沿用既有 schema 风格):

```sql
CREATE TABLE IF NOT EXISTS financials (
    symbol TEXT NOT NULL,
    period TEXT NOT NULL,
    roe REAL, net_margin REAL, gross_margin REAL,
    revenue REAL, revenue_yoy REAL,
    net_income REAL, net_income_yoy REAL, debt_ratio REAL,
    fetched_at TEXT NOT NULL,
    PRIMARY KEY (symbol, period)
);
CREATE TABLE IF NOT EXISTS company_analysis (
    id TEXT PRIMARY KEY,
    symbol TEXT NOT NULL,
    generated_at TEXT NOT NULL,
    rating TEXT NOT NULL,        -- BUY | HOLD | SELL | UNKNOWN
    confidence REAL,             -- 0..1, 可空
    summary TEXT,
    reasons_json TEXT,           -- JSON list[str]
    risks_json TEXT,             -- JSON list[str]
    model TEXT,
    context_json TEXT            -- 输入快照(技术面+财务),便于复现
);
CREATE INDEX IF NOT EXISTS idx_company_analysis_symbol
    ON company_analysis(symbol, generated_at);
```

K线已由 `bars` 表持久化,不重复存。两张新表加入 `init_schema` 的 `_SCHEMA`。

## 4. 数据组装层 `alphaagent/analytics/company_agent.py`(新)

- `assemble_company_context(symbol, bar_source, provider, db, *, lookback_days=250, periods=4) -> dict`
  - `bars = bar_source.get_bars(symbol, start, end)`(SqliteBarCache,落 bars)。
  - 技术面:用 analytics 纯函数算上述特征,组成 `technical` 子 dict。
  - 财务:`items = provider.financial_indicators(symbol)`;成功 → `persist_financials(db, symbol, items)`(upsert,带 `fetched_at`);异常 → `items = load_persisted_financials(db, symbol)`(回退)。取最近 `periods` 期组成 `financials` 子 dict。
  - 返回 `{"symbol", "technical": {...}, "financials": [...], "data_complete": bool}`(`data_complete=False` 表示财务走了回退/为空)。
- 辅助:`persist_financials(db, symbol, items)`、`load_persisted_financials(db, symbol) -> list[FinancialIndicators]`。
- bar_source 由 `SqliteBarCache(AkShareDataSource(adjust="qfq"), get_database(), "akshare_1d_qfq")` 构建(与 API 数据路径一致的 source_id)。

## 5. LLM 分析层 `alphaagent/agent/company_analyst.py`(新)

- `CompanyAnalysis`(dataclass):`rating: str`(BUY/HOLD/SELL/UNKNOWN)、`confidence: float | None`、`summary: str`、`reasons: list[str]`、`risks: list[str]`、`model: str`、`disclaimer: str`。
- `CompanyAnalyst(model="claude-sonnet-4-6", max_tokens=1500)`,方法 `analyze(context: dict) -> CompanyAnalysis`:
  - **懒导入** `anthropic`(API 不强依赖;未装/缺 key 时由 API 层转干净错误)。先检查 `os.environ.get("ANTHROPIC_API_KEY")`,缺失则 `raise AgentNotConfigured`(自定义异常)。
  - `client.messages.create(model=..., max_tokens=..., system=[{"type":"text","text":SYSTEM_PROMPT,"cache_control":{"type":"ephemeral"}}], messages=[{"role":"user","content":json.dumps(context, ensure_ascii=False)}])` —— system 块开 **prompt caching**。
  - `SYSTEM_PROMPT`:中文 A股 分析师设定,基于"技术面+财务"给出 `rating`(买入/持有/卖出)、`confidence`(0-1)、`reasons`(看多/支撑点)、`risks`(风险点)、`summary`(一句话);**严格输出 JSON** `{"rating","confidence","summary","reasons":[],"risks":[]}`;强调数据有限(无公司名/行业)、非投资建议。
  - 解析:抽取并 `json.loads`;校验 `rating ∈ {BUY,HOLD,SELL}`(中文映射→大写枚举);失败 → 降级 `CompanyAnalysis(rating="UNKNOWN", summary=raw_text, reasons=[], risks=[])`。
  - `disclaimer` 为常量(本分析由 AI 基于有限公开数据生成,仅供研究,非投资建议)。
- 自定义异常 `AgentNotConfigured(RuntimeError)`(放 `agent/base.py` 或本模块)。

## 6. API(`alphaagent/api/routers/analysis/company.py` 扩 + `schemas/analysis.py` 扩)

- `POST /api/analysis/company/{symbol}/agent`(同步):
  - deps:`get_fundamentals_provider`、`get_company_analyst`(新,返回 `CompanyAnalyst(model=env ALPHAAGENT_AGENT_MODEL or "claude-sonnet-4-6")`,可被测试 override)、`get_database`、bar_source(内部构建)。
  - 组装 context → `analyst.analyze` → 持久化 company_analysis → 返回 `CompanyAnalysisDTO`。
  - 错误:`AgentNotConfigured` → `400 err("AGENT_NOT_CONFIGURED","未配置 ANTHROPIC_API_KEY 或未安装 anthropic")`;数据完全不可用(无 bars 且无财务)→ `502 err("DATA_UNAVAILABLE",...)`;LLM/其他异常 → `502 err("AGENT_FAILED",...)`。
- `GET /api/analysis/company/{symbol}/agent/history?limit=10`:读 `company_analysis` 表返回历史(倒序)。
- DTO(`schemas/analysis.py`):`CompanyAnalysisDTO{symbol, generated_at, rating, confidence, summary, reasons:list[str], risks:list[str], model, disclaimer, data_complete: bool | None = None}`。`data_complete` 仅在新分析(POST,来自 context)填充;`company_analysis` 表不存该列,故 history(GET)读出的项 `data_complete=None`。

## 7. 前端(`web/src/pages/analysis/company/Index.vue` 扩 + `api/analysis.ts` + `types.ts`)

- `analysis.ts`:`companyAgentAnalyze(symbol)`(POST)、`companyAgentHistory(symbol, limit=10)`(GET)。
- 公司页:K线卡片下方加「AI 智能分析」卡片 + 按钮。点击 → loading → 渲染:评级徽章(买入绿/持有灰/卖出红)、置信度进度条、摘要、看多理由列表、风险点列表、免责声明、生成时间。可选「历史」折叠。
- `types.ts`:`CompanyAnalysis` 类型。
- 仅需 `npm run build`(vue-tsc 类型校验)通过;UX 由用户目视。

## 8. 错误处理与降级

- `ANTHROPIC_API_KEY` 缺失 / anthropic 未装 → `AgentNotConfigured` → 400 干净错误。
- 财务拉取失败 → 回退持久化副本;若也无 → `data_complete=False`,仍可基于技术面分析。
- bars 与财务都拿不到 → 502 DATA_UNAVAILABLE。
- LLM 返回非 JSON → 降级 `rating=UNKNOWN` + 原文摘要(不 500)。

## 9. 测试(不真调 LLM)

- **mock**:`get_company_analyst` 通过 `app.dependency_overrides` 注入 `StubAnalyst`(返回固定 `CompanyAnalysis`);数据用 `StaticFundamentalsProvider` + 临时 CSV bars + `Database(tmp)`(`ALPHAAGENT_DB` 隔离)。
- 用例:
  - `assemble_company_context`:技术面字段齐全;财务 upsert 后 `financials` 表有行;`load_persisted_financials` 往返。
  - 回退:provider 抛错 → 用持久化副本,`data_complete=False`。
  - `company_analysis` 持久化 + `GET .../history` 返回。
  - API:POST(StubAnalyst)→ 200 + DTO 字段;`AgentNotConfigured` 的 analyst → 400。
  - `CompanyAnalyst.analyze` 的 JSON 解析(用 mock 的 anthropic client 返回固定 JSON / 非 JSON)→ 正常解析 & 降级两条路径。
- 全量 `uv run --extra data --extra api pytest` 绿;`ruff` 零新增;`cd web && npm run build` 通过。

## 10. 依赖与配置

- `anthropic` 在 `agent` extra(已有 `anthropic>=0.40`)。用此功能需装该 extra(`uv run --extra data --extra api --extra agent ...`)并设 `ANTHROPIC_API_KEY`。未满足时接口干净报错,不影响其余功能。
- 模型可由 `ALPHAAGENT_AGENT_MODEL` 环境变量覆盖,默认 `claude-sonnet-4-6`。

## 11. 验收标准

1. `pytest` 全绿;`ruff` 零新增;`npm run build` 通过。
2. 设了 key 时:`POST /api/analysis/company/600000/agent` 返回评级/理由/风险/摘要,且 `company_analysis` 表落库;再次 `GET .../agent/history` 可见。
3. 全程只对单股发轻量请求(bars + financials),不触发 `stock_individual_info_em`。
4. 缺 key / 数据不可用 / LLM 非 JSON 三种情况都返回干净结果,不 500 堆栈。
