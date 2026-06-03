# Agentic 引用研究报告 设计(SP2,核心)

- 日期:2026-06-03
- 状态:待实现(在 SP1 深色主题之后)
- 关联:[[web-only-direction]];演进自已合并的[[company-analysis-agent]](单次 `CompanyAnalyst` → 工具循环 `ResearchAnalyst`)。前端建立在 SP1 深色主题之上。

## 1. 目标

公司分析页的**核心(重点)**:输入代码 → LLM **像 agent harness 一样自主调用工具**按需抓取**技术面 + 财报 + 资讯** → 产出一份**分章节研究报告**,报告正文带**编号内联引用**,每个引用**锚定**到具体来源(财报行项 / 资讯条目);抓取的数据与报告均**持久化**;前端「报告正文 ↔ 来源面板」点击联动。代理不稳时**降级不报错**。

## 2. 报告数据契约(后端↔前端共享)

```
ResearchReport {
  symbol: str
  generated_at: str (iso)
  rating: "BUY"|"HOLD"|"SELL"|"UNKNOWN"
  confidence: float | null
  sections: [ { title: str, body: str } ]      # body 内含 [n] 内联引用标记
  sources:  [ Source ]
  disclaimer: str
  data_complete: bool                          # 资讯/财报是否完整(降级时 false)
  notes: [str]                                 # 如「资讯暂不可用」
}
Source {
  id: int                                      # 正文 [id] 引用此来源
  type: "technical" | "financial" | "news"
  label: str                                   # 面板显示,如「2024年报 ROE 12.0%」「<新闻标题>」
  detail: dict                                 # financial: {period,metric,value}; news: {title,date,source,url}; technical: {key,value}
}
```

正文里的 `[n]` 对应 `sources` 中 `id==n` 的来源。前端把 `[n]` 渲染为可点击角标 → 跳转/高亮来源面板对应条目。

## 3. 工具(Anthropic tool use)

`alphaagent/agent/tools.py`(或 research_analyst 内)定义工具,工具实现复用 `analytics/company_agent.py` 与新 news provider:

- `get_technical(symbol)` → 技术面特征(复用 `_technical_features`),登记为 `type:"technical"` 来源(每个关键指标一个可引用来源)。
- `get_financials(symbol)` → 近 N 期财务(复用 `financial_indicators` + 持久化),**每个 (期, 指标, 值) 登记为一个 `type:"financial"` 来源**并分配 id。
- `get_news(symbol, limit=10)` → akshare 个股新闻 → 近期资讯,持久化到 `news` 表,**每条登记为 `type:"news"` 来源**(title/date/source/url)。

工具返回给 LLM 的结果**内含已分配的 `source_id`**,LLM 据此在报告里 `[id]` 引用。Harness 维护**来源 ID 注册表**(全程递增,跨工具唯一)。

## 4. Agentic harness `alphaagent/agent/research_analyst.py`

`ResearchAnalyst(model, max_tool_rounds=6, client=None)`,`analyze(symbol, ctx_providers) -> ResearchReport`:

- **懒导入 anthropic**;缺 key/SDK → `AgentNotConfigured`(复用现有异常)。
- 工具循环(Anthropic Messages + tool use):
  1. system prompt:你是 A股 研究分析师;**先用工具收集技术面/财报/资讯**,再撰写分章节研报;正文用 `[id]` 引用工具返回的来源 id;最后调用 `submit_report` 工具提交结构化报告。**system 块开 prompt caching**。
  2. 循环:LLM 发 `tool_use` → harness 执行对应工具(登记来源、持久化)→ 回 `tool_result`(含 source_id);重复直到 LLM 调用 `submit_report` 或达 `max_tool_rounds`。
  3. `submit_report(rating, confidence, sections:[{title,body}], cited_source_ids:[int])`:harness 据此组装 `ResearchReport`,`sources` = 被引用(或全部已登记)的来源 + 其 detail。
- **结构化输出**用 `submit_report` 工具强约束(而非裸 JSON)。
- 解析/校验:rating 归一化(买入→BUY…);`[id]` 引用中指向不存在来源的剔除或保留为纯文本;`submit_report` 缺失/达上限 → 用已收集数据生成**降级报告**(技术面+财报小结 + `data_complete=false` + note)。
- 来源去重 + 上限(避免来源爆炸)。

## 5. 资讯源 + 持久化

- `alphaagent/fundamentals/news.py`:`NewsProvider` 协议 + `AkShareNewsProvider`(懒加载 akshare,`ak.stock_news_em(symbol=...)`,**带现有 `_retry` 风格重试**);测试用 `StaticNewsProvider`。返回 `NewsItem{title, date, source, url, summary}`。
- 新表 `news`(`storage/db.py` `_SCHEMA`):
  ```sql
  CREATE TABLE IF NOT EXISTS news (
      symbol TEXT NOT NULL, url TEXT NOT NULL, title TEXT, date TEXT,
      source TEXT, summary TEXT, fetched_at TEXT NOT NULL,
      PRIMARY KEY (symbol, url)
  );
  ```
- `get_news` 工具:抓取 → upsert `news` 表 → 返回;**抓取失败/代理不通 → 返回空 + harness 标记 `notes:["资讯暂不可用"]`、`data_complete=false`**,报告仅基于技术面+财报(不报错)。

## 6. 报告持久化

扩 `company_analysis` 表:加一列 `report_json TEXT`(幂等 `ALTER TABLE ... ADD COLUMN`,沿用 jobs.kind 的迁移写法)。整份 `ResearchReport`(含 sections + sources)存 `report_json`;`rating/confidence/summary`(取报告首段或结论)仍单列存,供 history 列表快速展示。

## 7. API(演进 `routers/analysis/company.py`)

- `POST /api/analysis/company/{symbol}/agent` 改为运行 `ResearchAnalyst`,返回 `ResearchReportDTO`(= 报告契约)。**同步**;工具循环较慢(数十秒),前端 loading 态承接。错误码沿用:`AGENT_NOT_CONFIGURED`(400)、`DATA_UNAVAILABLE`(502,技术面+财报+资讯全空)、`AGENT_FAILED`(502);均 `HTTPException(detail=err())`。
- `GET .../agent/history` 返回历史(含每份报告概览 + 可取完整 report_json)。
- deps:`get_research_analyst`(替代/并存 `get_company_analyst`),测试用 `dependency_overrides` 注入 Stub。
- DTO `ResearchReportDTO`(`schemas/analysis.py`)= §2 契约。

> 备注:工具循环耗时较长,**流式/异步进度**(展示「正在抓财报/资讯…撰写中」)列为后续增强;v1 同步 + loading。

## 8. 前端报告查看器(公司页旗舰,深色)

`pages/analysis/company/Index.vue` 的 AI 区替换为**报告查看器**(SP1 主题之上):
- 「生成研究报告」按钮 → loading(数十秒,文案提示智能体在收集与撰写)→ 渲染。
- 顶部 **研判 hero**:大号评级徽章(买红/卖绿/持有中性)+ 置信度;`data_complete=false` 时标注「资讯不完整」。
- **报告正文**:分章节(标题 + body);body 内 `[n]` 解析为**可点击角标**;点击 → 滚动到 + 高亮「来源」面板第 n 条。(body 用轻量解析渲染 `[n]` 与基本换行;不引重型 markdown 库,frontend-design 把版式做精。)
- **来源面板**:列出 sources;财报来源显示 期/指标/值,资讯来源显示 标题/日期/出处/外链;每条带 `[n]` 锚,被正文点击时高亮。
- 历史下拉/折叠可看过往报告(可选,v1 可省)。
- 新增 `web/src/api/types.ts` 报告类型 + `api/analysis.ts` 方法(沿用现有 `agentAnalyze`,返回类型升级为 `ResearchReport`)。

## 9. 复用/重构既有 agent

- 既有单次 `agent/company_analyst.py` 被 `research_analyst.py` 取代(API 切到后者);`CompanyAnalysis` → `ResearchReport`。可保留 `_parse`/rating 映射等工具函数复用。
- `analytics/company_agent.py` 的组装函数下沉为**工具的数据来源**(get_technical/get_financials 调它)。
- 前端 AI 卡片 → 报告查看器。

## 10. 错误与降级

- 缺 key/anthropic 未装 → 400 干净错误。
- 资讯抓取失败 → 报告降级(无资讯引用)+ note,不报错。
- 财报抓取失败 → 回退持久化副本(复用现有逻辑);全空且无 bars → 502。
- LLM 未提交报告/超轮次 → 降级报告(基于已收集数据)。
- 引用 id 指向缺失来源 → 该 `[id]` 退化为纯文本。

## 11. 测试(不真调 LLM/不联网)

- 工具数据层:`get_technical/get_financials/get_news` 用 CSV bars + Static financials + StaticNewsProvider + tmp Database,验证来源登记 + 持久化(financials/news 表)。
- News provider:`AkShareNewsProvider` 重试逻辑单测(mock requests/akshare);`StaticNewsProvider` 注入。
- Harness:注入 **fake anthropic client**(脚本化:tool_use(get_financials)→tool_result→tool_use(get_news)→tool_result→submit_report),验证来源 ID 注册、引用解析、`ResearchReport` 组装、降级路径(达上限/资讯失败/缺 submit)。
- 报告组装/校验 纯函数单测(引用→来源映射、坏 id 退化、rating 归一)。
- API:`dependency_overrides` 注 StubAnalyst(返回固定 ResearchReport)+ fake providers + tmp DB;验证 200 DTO(sections+sources)、history、缺 key 400、report_json 落库。
- 前端:`npm run build` 类型校验通过;报告查看器渲染 + 引用锚点点击逻辑(无浏览器实测,用户目视)。
- 全量 `pytest` 绿;`ruff` 零新增。

## 12. 验收

1. `pytest` 全绿(LLM/news 全 mock);`ruff` 零新增;`npm run build` 通过。
2. 设 key + `--extra agent` 时:`POST .../agent` 返回**分章节报告 + 编号来源**,`report_json`/`news`/`financials` 均落库;history 可见。
3. 全程只发轻量单股请求(bars + financial_abstract + 个股新闻),**不碰 90 字段大请求**。
4. 资讯不可用 / 缺 key / 超轮次 三种情况均干净降级,不 500。
5. 前端:正文 `[n]` 角标点击 → 高亮对应来源(用户目视确认)。

## 13. 非目标 / 后续

- v1 同步;**流式进度 / 异步任务**(展示智能体每步)列后续。
- 不接外部搜索/研报库;资讯仅 akshare 个股新闻。
- 不引重型前端 markdown 库(轻量解析 `[n]` 与换行)。
- 历史报告对比、导出 PDF 等后续。
