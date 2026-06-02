# AlphaAgent

事件驱动的 A 股量化交易与策略引擎,内置可选的 LLM Agent 层。

## 特性

- **事件驱动架构**:Market → Signal → Order → Fill 四类事件驱动,回测与实盘共用同一套逻辑
- **A 股规则内置**:T+1、最小 100 股、涨跌停、印花税 + 佣金
- **组合级风控**:总敞口、单股敞口、持仓只数上限,自动降档或拒单
- **多数据源**:AkShare / Tushare / 本地 CSV,内建 SQLite 行情缓存
- **日/分钟频**:`1d`、`1m`、`5m`、`15m`、`30m`、`60m`
- **交易日历**:SSE 日历 + 会话窗口(09:30-11:30、13:00-15:00),自动过滤非交易时段
- **性能指标**:Sharpe、Sortino、最大回撤、Calmar、胜率、盈利因子等 13 项
- **策略即插件**:继承 `Strategy` 基类,注册即用
- **多策略组合**:并行运行多个策略,独立子账户,按权重分配资金,含每策略 PnL 归因
- **Agent 层可开关**:通过配置启用 LLM 选股/调参,默认关闭
- **券商对接**:`simulated` 回测 / `paper` 模拟实盘(次 bar 开盘成交)/ `qmt` 真实盘(miniQMT)
- **选股工作流**:Web 选股页(`选股`),指数成分股 + 6 条技术规则 → 候选清单 → 人工审核 → 喂回测
- **自动化调度**:APScheduler 驱动的定时任务

## 目录结构

```
alphaagent/
  core/         # 事件、事件总线、领域类型
  data/         # 数据源适配 (AkShare/Tushare/CSV) + SQLite 行情缓存
  calendar/     # A 股交易日历
  strategy/     # 策略基类 + 内置样例
  portfolio/    # 持仓、现金、PnL、信号→订单 sizing
  execution/    # 下单执行 (模拟/实盘)
  risk/         # 风控 (T+1、仓位、涨跌停、最小手数)
  backtest/     # 回测引擎
  metrics/      # 性能指标 (收益/风险/交易质量)
  agent/        # 可选 LLM Agent 层
  scheduler/    # 自动化调度
  config.py     # 全局配置 (pydantic + YAML)
  api/          # FastAPI routers (后端入口 alphaagent-api)
strategies/     # 用户策略目录
configs/        # YAML 配置
tests/
```

## 快速开始

> **注意**:CLI 命令模式(`alphaagent backtest` / `alphaagent screen` 等)已移除。项目现在通过 **Web 应用**运行——后端 `alphaagent-api` + 前端 `web/`。

```bash
# 1. 安装依赖
uv sync --extra data --extra api

# 2. 启动后端 (127.0.0.1:8000)
alphaagent-api
# 或
uv run python main.py

# 3. 启动前端(新终端)
cd web && npm install && npm run dev   # http://localhost:5173
```

打开浏览器访问 `http://localhost:5173`,在 **回测** 页面选择策略和配置,点击「运行」即可。回测结果持久化到 SQLite,重启后 `GET /api/backtests` 仍可见历史任务。

**Python 编程 API**(直接调用引擎,无需启动服务):

```python
from alphaagent.backtest import BacktestEngine
# ... 配置 feed / strategy / portfolio / execution / event_bus
result = engine.run()
print(result.performance().sharpe)
```

## 配置

见 `configs/example.yaml`:

```yaml
data:
  source: csv              # csv | akshare | tushare
  root: ./data             # for csv: directory of <symbol>.csv files
  symbols: ["600000", "000001"]
  start: 2023-01-01
  end: 2023-12-31
  freq: 1d                 # 1d | 1m | 5m | 15m | 30m | 60m
  adjust: qfq              # qfq | hfq | ""  (akshare/tushare only)
  cache_dir: ./data/cache  # 启用行情缓存;留空则禁用
  # tushare_token: ""      # 或通过 TUSHARE_TOKEN 环境变量

storage:
  db_path: ./data/alphaagent.db   # 回测任务/行情缓存/交易日历统一入库;可被环境变量 ALPHAAGENT_DB 覆盖

strategy:
  name: ma_cross
  params: { fast: 5, slow: 20 }

portfolio:
  initial_cash: 1_000_000
  target_pct: 0.3          # 每次买入目标仓位比例
  commission_rate: 0.0003  # 万三
  min_commission: 5.0
  stamp_tax_rate: 0.001    # 千一,卖出侧

execution:
  slippage_bps: 5

calendar:
  enabled: false           # 开启后过滤非交易日 / 非会话时段
  cache_path: ./data/cache/ashare_calendar.parquet

agent:
  enabled: false           # 启用 Claude LLM Agent 层
  provider: claude
  model: claude-sonnet-4-6
```

## 性能指标说明

回测结束后,`BacktestResult.performance()` 返回 13 项指标,对应 `PerformanceSummary`:

### 收益类

| 指标 | 公式 / 含义 |
|---|---|
| **Total Return** | `(final - initial) / initial`。整段时间的总收益率 |
| **Annualized Return** | 按复利折算到一年的收益率,便于跨周期对比 |
| **Total PnL** | 已平仓交易的累计净利润(扣手续费 + 印花税) |

### 风险类

| 指标 | 公式 / 含义 |
|---|---|
| **Annualized Vol** | 每期收益率标准差 × √(一年期数)。越低越平稳 |
| **Max Drawdown** | 净值从峰值跌到谷底的最大幅度(负数)。衡量最坏情况 |

### 风险调整收益(最重要)

| 指标 | 公式 / 含义 | 经验值 |
|---|---|---|
| **Sharpe** | `(均收益 − 无风险利率) / 波动率`,再乘 √(一年期数) | <1 普通,1-2 不错,>2 优秀 |
| **Sortino** | 夏普的改良版,只用下跌波动做分母。通常高于 Sharpe | 与 Sharpe 同量级 |
| **Calmar** | `年化收益 / |最大回撤|`。每 1 元最大亏损换多少年化 | >1 合格,>3 优秀 |

### 交易质量类

| 指标 | 公式 / 含义 |
|---|---|
| **Trades** | 已平仓的完整回合数(FIFO 配对 BUY/SELL) |
| **Win Rate** | 盈利交易占比 |
| **Avg Win / Avg Loss** | 平均单笔盈利 / 亏损(已扣费) |
| **Profit Factor** | `总盈利 / |总亏损|`。>1 就赚钱,>1.5 不错,>2 优秀 |

### 怎么看

1. 先看 **Max Drawdown** — 能不能接受最坏情况?
2. 再看 **Sharpe / Calmar** — 收益配得上风险吗?
3. 最后看 **Profit Factor + Win Rate** — 策略逻辑是否稳健?

> 💡 **低胜率 + 高盈亏比** 是趋势跟踪策略的典型特征(抓一次大趋势吃掉很多小错误);
> **高胜率 + 低盈亏比** 是均值回归策略的典型特征。不要只看胜率。

## 数据接入

### 1) AkShare(免费免注册,推荐入门)

```yaml
data:
  source: akshare
  symbols: ["600000", "000001", "600519"]
  start: 2023-01-01
  end: 2024-12-31
  freq: 1d          # 或 1m / 5m / 15m / 30m / 60m
  adjust: qfq
  cache_dir: ./data/cache
```

### 2) Tushare Pro(需注册,部分接口要积分)

```bash
export TUSHARE_TOKEN=your_token_here
```

```yaml
data:
  source: tushare
  symbols: ["600000", "000001"]
  ...
```

6 位代码会自动补全交易所后缀(`.SH` / `.SZ` / `.BJ`)。

### 3) 本地 CSV(适合离线/单测)

目录中放 `<symbol>.csv`,表头:`date, open, high, low, close, volume, amount`。

### 缓存机制

当 `data.cache_dir` 被设置时,引擎使用 `SqliteBarCache` 将行情以行级 `INSERT OR REPLACE` 写入统一 SQLite 数据库(`storage.db_path`,默认 `./data/alphaagent.db`)的 `bars` 表。后续回测只会请求**缓存范围之外**的时间段(头/尾增量),大幅减少网络调用。数据库路径也可通过环境变量 `ALPHAAGENT_DB` 覆盖。

### 数据迁移

已有旧版 Parquet 缓存(由 CLI 选股生成)可一次性导入 SQLite:

```bash
uv run python scripts/migrate_cache.py --cache-dir ./data/cache \
    --calendar ./data/cache/ashare_calendar.parquet
```

脚本幂等(`INSERT OR REPLACE`),可重复跑;文件名中不含 `__source_id` 后缀的旧格式 Parquet 会被跳过并计数。

**已知限制**:旧版 screener 生成的 Parquet 以 `akshare-sina-qfq` 等 source_id 命名,API 回测使用的 source_id 命名可能不一致,迁移后的行不保证被 API 回测命中——必要时仍会联网补拉。

## 多策略组合

并行运行多个策略,每个策略拿到一份**独立的子账户**(初始资金按权重切分),信号与持仓完全隔离,不会互相挤占现金或仓位。配置里把 `strategy` 改成 `strategies` 列表:

```yaml
strategies:
  - name: ma_cross
    params: { fast: 5, slow: 20 }
    capital_weight: 0.5    # 50% 资金
    strategy_id: ma_fast   # 自定义 ID 区分同类策略
    target_pct: 0.3        # 覆盖全局 target_pct(可选)

  - name: ma_cross
    params: { fast: 10, slow: 40 }
    capital_weight: 0.5
    strategy_id: ma_slow
```

- `capital_weight` 必须跨所有策略加起来 = 1.0
- `strategy_id` 可选,不填用策略默认 ID;**运行同一策略的多个参数组合时必填**以区分
- 每笔订单和成交都带 `strategy_id`,回测结束后可按策略单独看性能

回测输出会同时打印**聚合绩效**和**每策略绩效**:

```
Performance (aggregate)
Total Return: 1.43%   Sharpe: 0.90   MDD: -1.00%   Trades: 8

Performance (strategy=ma_fast)
Total Return: 1.59%   Sharpe: 0.82   MDD: -1.24%   Trades: 6

Performance (strategy=ma_slow)
Total Return: 1.27%   Sharpe: 0.82   MDD: -1.14%   Trades: 1
```

> 💡 典型用法:组合一个趋势追踪(低胜率高盈亏比)+ 一个均值回归(高胜率低盈亏比),整体 Sharpe 往往高于单策略,且 MDD 更小 — 这就是分散化收益。

编程 API:

```python
from alphaagent.portfolio import MultiStrategyPortfolio, StrategyAllocation

portfolio = MultiStrategyPortfolio(
    initial_cash=1_000_000,
    event_bus=event_bus,
    allocations=[
        StrategyAllocation("ma_fast", weight=0.5, target_pct=0.3),
        StrategyAllocation("ma_slow", weight=0.5, target_pct=0.3),
    ],
)
engine = BacktestEngine(feed, [strat_fast, strat_slow], portfolio, execution, event_bus)
result = engine.run()
for sid, perf in result.performance_by_strategy().items():
    print(sid, perf.sharpe, perf.max_drawdown)
```

## 内置策略库

在 Web 应用的 **`策略库`** 页面查看所有已注册策略,或通过 `GET /api/strategies` 接口获取完整列表。

| 名称 | 类别 | 核心逻辑 | 典型特征 |
|---|---|---|---|
| `ma_cross` | 趋势 | 快慢均线金叉 BUY / 死叉 SELL | 低胜率,高盈亏比 |
| `rsi_mean_reversion` | 均值回归 | RSI 穿过超卖区上行 BUY / 超买区下行 SELL | 高胜率,低盈亏比 |
| `bollinger_breakout` | 趋势(突破) | 收盘突破上轨 BUY / 跌破中轨 SELL | 抓强势突破 |
| `bollinger_reversion` | 均值回归 | 收盘跌破下轨 BUY / 涨回中轨 SELL | 抄底反弹 |
| `xs_momentum` | 截面动量(选股) | 按过去 N 天收益排序,持有前 K 名,定期轮动 | 相对强弱选股 |

每个策略都支持自定义参数,在 YAML `strategy.params` 下指定,例如:

```yaml
strategy:
  name: rsi_mean_reversion
  params: { period: 14, oversold: 30, overbought: 70 }

# 或者
strategy:
  name: xs_momentum
  params: { lookback: 60, top_n: 3, rebalance_days: 20 }
```

### 真正的多元化:组合对立思路

趋势与均值回归的胜率/盈亏比模式**相反** — 把两者并联往往比单策略更稳:

```yaml
strategies:
  - name: ma_cross          # 趋势:抓大波段
    params: { fast: 5, slow: 20 }
    capital_weight: 0.5
    strategy_id: trend

  - name: rsi_mean_reversion  # 均值回归:抄短期超跌
    params: { period: 14, oversold: 30, overbought: 70 }
    capital_weight: 0.5
    strategy_id: mean_rev
```

## 券商对接(回测 / 模拟 / 实盘)

回测、模拟盘、实盘共用同一套策略代码,只切换执行后端:

```yaml
execution:
  backend: simulated       # simulated | paper | qmt
  slippage_bps: 5
  # qmt 专用(backend=qmt 时必填):
  # qmt_path: "C:/QMT/userdata_mini"
  # qmt_account: "123456"
```

| 后端 | 成交模型 | 用途 |
|---|---|---|
| `simulated` | 当根 bar **收盘价**成交 | 快速批量回测;**注意隐含 lookahead 偏差** |
| `paper` | **下一根 bar 开盘价**成交 + 滑点 + 手续费 + T+1 | 贴近实盘的模拟账户,实盘前必测 |
| `qmt` | 真实委托,实际成交价由交易所回报 | miniQMT 实盘(需要开通量化权限) |

### 为什么 simulated 回测会比实盘好看

同一策略(MA Cross 5/20)跑 240 根日线:
- `simulated`: **+1.59%**(当根收盘价成交)
- `paper`: **-0.15%**(下一根开盘价成交 + 5 bps 滑点)

差距来自**隐含的 lookahead**:策略在 T 根收盘看到信号,不可能当根收盘成交。`paper` 后端强制延迟 1 根 bar,揭示这一点。**实盘前务必用 paper 验证**。

### QMT 实盘接入

`alphaagent/broker/qmt.py` 是基于 `xtquant` 的适配器骨架,已经实现:下单、查持仓、查现金、成交回调 → `FillEvent`。

准备清单:
1. 联系券商开通**量化接口权限**(普通账户升级)
2. 安装 miniQMT 客户端,登录一次
3. `pip install xtquant`(或用客户端自带 wheel)
4. 填写配置 `qmt_path`(客户端安装目录)和 `qmt_account`(资金账号)
5. **先用 QMT 自带的模拟账户跑通流程**,再切真实账户

代码层面还需要补充(生产前必备):
- 启动时用 `query_stock_positions` 对账,不要只依赖回调
- 网络中断重连逻辑
- 订单状态轮询(部分成交、废单)
- 限价单价格校验(涨跌停、tick size)

### XTP

中泰 XTP(`vnpy_xtp` 或原生 API)暂未接入,但结构与 QMT 一致:新建 `broker/xtp.py` 实现同一 `Broker` 接口即可,`BacktestEngine` 无需改动。

### 编程 API

```python
from alphaagent.broker import PaperBroker
from alphaagent.execution import BrokerExecutionHandler

broker = PaperBroker(initial_cash=1_000_000, slippage_bps=5)
execution = BrokerExecutionHandler(broker, event_bus)
engine = BacktestEngine(feed, strategy, portfolio, execution, event_bus)
```

## 组合级风控

策略级规则(T+1、涨跌停、最小手数)已经嵌在引擎里。**组合级**规则用来限制整个账户的风险敞口,在订单提交给执行层**之前**检查,可以**降档**(允许但减少数量)或**拒单**(数量归零)。

可用规则(YAML 里哪个字段没填就禁用哪个):

```yaml
risk:
  max_gross_exposure: 0.8         # 总持仓市值 ≤ 80% 总资产(留 20% 现金缓冲)
  max_per_symbol_exposure: 0.3    # 单只股票 ≤ 30% 总资产
  max_position_count: 10          # 最多同时持有 10 只股票

  # 板块集中度:需要符号 → 板块映射
  max_sector_exposure: 0.4        # 任一板块合计 ≤ 40% 总资产
  sectors:                        # 内联映射
    "600000": "银行"
    "000001": "银行"
    "600519": "白酒"
  # 或用 CSV: sectors_csv: ./data/sectors.csv

  # 相关性:防止多个高度同涨同跌的持仓变相加仓
  max_pairwise_correlation: 0.85  # 新开仓与任一现有持仓 |corr| > 0.85 则拒单
  correlation_lookback: 60        # 用于算相关系数的收益窗口长度(bar 数)
```

| 规则 | 作用 | 触发后 |
|---|---|---|
| `max_gross_exposure` | 总仓位 / 总资产 ≤ X | 按可用额度**降档**下单数量 |
| `max_per_symbol_exposure` | 单股仓位 / 总资产 ≤ X | 按单股可用额度**降档** |
| `max_position_count` | 同时持仓的股票数 ≤ N | 已满时开新股票**拒单**(加仓现有仓位不受限) |
| `max_sector_exposure` | 单板块合计仓位 / 总资产 ≤ X | 板块满额后**降档**或**拒单** |
| `max_pairwise_correlation` | 新开仓与任一现有持仓 \|corr\| ≤ X | 超阈值**拒单**(加仓现有仓位不受限) |

**仅限制 BUY**:SELL 一律放行(减仓永远不增加敞口)。多规则取**最小值**,并向下取整到 100 股倍数。

回测完成后,API 返回的结果中包含 `downsized` 和 `rejected` 计数,一眼看出哪些规则在生效:

```json
{
  "risk_rules": ["max_gross_exposure", "max_per_symbol_exposure"],
  "fills": 6,
  "risk": { "downsized": 3, "rejected": 0 }
}
```

**多策略模式下**,风控看的是**全部子账户合计**的敞口 — 两个策略同时买入同一只股票会触发单股上限,而不是每个子账户单独计算。

编程 API:

```python
from alphaagent.risk import (
    PortfolioRiskManager, MaxGrossExposure, MaxPerSymbolExposure, MaxPositionCount,
)

risk = PortfolioRiskManager(
    portfolio,
    rules=[
        MaxGrossExposure(max_pct=0.8),
        MaxPerSymbolExposure(max_pct=0.3),
        MaxPositionCount(max_n=10),
    ],
)
engine = BacktestEngine(feed, strategy, portfolio, execution, bus, risk_manager=risk)
```

## 选股工作流

选股跟回测**完全解耦** — 通过 Web 应用或 HTTP API 产出候选清单,人工审核后把 symbols 填入回测配置。详细设计见 [docs/screener-design.md](docs/screener-design.md)。

**Web 操作流程**:在 **`选股`** 页面配置 universe/过滤器/规则,点击「运行选股」,等待异步任务完成后查看候选清单和评分详情。

**HTTP API 操作流程**:

```bash
# 查看所有内置规则和过滤器
GET /api/screeners/rules

# 提交选股任务
POST /api/screeners
# Body: configs/screen.example.yaml 对应的 JSON

# 查询任务状态
GET /api/screeners/{id}

# 获取候选结果
GET /api/screeners/{id}/result
```

[configs/screen.example.yaml](configs/screen.example.yaml) 的核心配置:

```yaml
universe:
  source: akshare_index        # 当前成分股(免费,有幸存者偏差)
  index_code: "000300"         # 沪深 300

as_of: 2024-12-31              # 选股的"今天",非交易日自动规整到前一交易日
lookback_days: 120             # 算因子的回看窗口

filters:                       # 硬过滤
  - { type: min_price, min_price: 3.0 }
  - { type: min_avg_volume, lookback: 20, min_amount: 10000000 }
  - { type: exclude_st }
  - { type: min_listed_days, min_days: 250 }

rules:                         # 打分规则,权重自动归一化
  - { type: momentum, lookback: 60, weight: 0.4 }       # 横截面
  - { type: above_ma, period: 60, weight: 0.2 }         # 绝对
  - { type: low_volatility, lookback: 20, weight: 0.2 } # 横截面
  - { type: volume_breakout, lookback: 20, z_threshold: 1.5, weight: 0.2 }  # 绝对
```

### 内置规则

**绝对评分(每只股票独立打分)**:`above_ma`、`price_breakout`、`volume_breakout`(后者用成交额 amount,不用 volume,除权天然中性)。

**横截面评分(全池排名归一化)**:`momentum`、`reversal`、`low_volatility`。

权重自动归一化(`0.4+0.2+0.2+0.2` ≡ `4+2+2+2`),数据缺失的规则从分母扣除。

### 选股结果结构

`GET /api/screeners/{id}/result` 返回以下结构(与旧版 `picks.yaml` 格式一致):

```yaml
metadata:
  resolved_as_of: 2024-12-30          # 自动规整后的真实交易日
  universe: akshare_index:000300
  universe_size: 300
  filtered_size: 240
  universe_snapshot: ["000001", "000002", ...]   # 全部成分股,供 --replay 复现
symbols:                              # 直接复制到 strategy.yaml 的 data.symbols
  - "600519"
  - "000858"
candidates:                           # 详细评分,供人工审核
  - symbol: "600519"
    name: "贵州茅台"
    final_score: 0.873
    reasons:
      - { rule: momentum, score: 0.95, detail: { return_60d: 0.185 } }
      - { rule: above_ma, score: 1.0, detail: { close: 1620.5, ma60: 1502.3 } }
```

`output.with_reasons` 三档:`full`(完整理由)/ `compact`(只保留最高分规则)/ `none`(只输出 symbols 列表)。
`output.format` 支持 `yaml` 和 `csv`(Excel 友好)。

### 人工审核 checklist

从选股结果取出 `symbols` 填入回测配置之前,过一遍:

1. **行业集中度** — 30 只里有 15 只白酒?手动剔除一些
2. **市值分布** — 是否过度偏向某个风格
3. **近期公告** — 用同花顺/东财查最近一周公告,剔除有重大利空的
4. **复权事件** — 临近除权日的股票排除(打分会失真)
5. **流动性** — 即便过了硬过滤,日均成交额 < 5000 万的也要谨慎

### 已知局限(MVP)

- **幸存者偏差**:`akshare_index` 拉的是**当前**成分股,不是历史。回测结果偏好。
  → 升级到 Tushare 2000 积分(`tushare_index`,v2)用 `index_weight` 月度快照。
- **ST 识别靠名称关键字**:漏掉历史摘帽/戴帽。
  → 升级到 Tushare 3000 积分(`stock_st`,v2)拿精确历史。
- **基本面规则缺失**:PE/PB/ROE 没接入。
  → Tushare 2000 积分(`daily_basic`)接入,v2 加 `low_pe`/`low_pb`/`high_roe` 规则。

## 编写自定义策略

在 `strategies/` 下新建文件,继承 `Strategy`:

```python
from alphaagent.strategy import Strategy, register
from alphaagent.core.types import Bar, Side

class MyStrategy(Strategy):
    strategy_id = "my_strategy"

    def on_bar(self, bar: Bar) -> None:
        # 访问 self.ctx.positions / self.ctx.cash
        # 发信号:
        self.ctx.emit_signal(bar, Side.BUY, strength=1.0)

register("my_strategy", MyStrategy)  # 注册后 YAML 可直接用 name: my_strategy
```

## 架构分层

```
┌─────────────────────────────────────────────────┐
│  Agent Layer (LLM 选股/调参/veto,可选)          │
├─────────────────────────────────────────────────┤
│  Strategy Engine (信号生成,事件驱动)            │
├─────────────────────────────────────────────────┤
│  Backtest │ Paper Trading │ Live Trading         │
├─────────────────────────────────────────────────┤
│  Risk │ Portfolio │ Order Mgmt │ Execution       │
├─────────────────────────────────────────────────┤
│  Data Layer (行情,统一接口) + SQLite 缓存        │
├─────────────────────────────────────────────────┤
│  Brokers (AkShare / Tushare / CSV / [QMT/XTP])   │
└─────────────────────────────────────────────────┘
```

## Web 前端

`web/` 是 Vue 3 + Element Plus 单页应用,通过 FastAPI(`alphaagent.api`)与核心引擎通信。
单机启动:

```bash
# 后端
uv sync --extra api
alphaagent-api                       # 127.0.0.1:8000
# 或 uv run python main.py

# 前端(独立终端)
cd web && npm install && npm run dev # http://localhost:5173
```

回测历史与结果已持久化到 SQLite:`alphaagent-api` 重启后 `GET /api/backtests` 仍可见历史任务;进程中断时未完成的任务自动标记为 `interrupted by restart`。

主要模块:回测、策略库、**选股**、**公司分析**(K 线 + 财务 + 多周期收益)、**行业分析**(涨跌排名/资金流/成分股)、**大盘**(指数 + 宽度 + 北向)、(规划中)实盘监控。
新增模块只需 `routers/<m>.py` + `pages/<m>/Index.vue` + 一条 router 记录,菜单自动出现。
详见 [`web/README.md`](./web/README.md)。

### 分析模块的数据层

`alphaagent.fundamentals` 是与 `alphaagent.data`(OHLCV)并列的另一类数据源,负责基本面 / 行业 / 大盘的非 bar 数据。`FundamentalsProvider` 抽象接口,默认实现 `AkShareFundamentalsProvider`(懒加载 akshare),测试用 `StaticFundamentalsProvider` 注入。
`alphaagent.analytics` 是纯函数分析层,只接受数据返回派生指标,CLI 和 API 都能调用。

## 开发

```bash
uv sync --extra data --extra dev --extra api
uv run pytest -q
uv run ruff check alphaagent tests
```

## Roadmap

- [x] 事件驱动核心 + A 股风控
- [x] AkShare + Tushare 数据源 + SQLite 行情缓存(支持 Parquet 迁移)
- [x] 日/分钟频 + 交易日历过滤
- [x] 13 项性能指标
- [x] 多策略组合 + 独立子账户 + 每策略归因
- [x] 策略库:MA Cross / RSI / Bollinger × 2 / 截面动量
- [x] 组合级风控(总敞口、单股、只数、板块集中度、相关性)
- [x] 券商对接:PaperBroker 模拟盘 + QMT 实盘骨架
- [x] 选股(screener)pipeline + Web 选股页 + HTTP API
- [x] FastAPI Web API + Vue 3 前端(回测 / 策略库 / 选股 + sidebar);CLI 命令模式已移除,项目 Web-only
- [x] 公司分析(K 线 + 财务指标 + 多窗口收益)
- [x] 行业分析(涨跌排名 + 资金流 + 成分股下钻)
- [x] 大盘 dashboard(指数 + 市场宽度 + 北向资金)
- [ ] 实盘监控页面
- [ ] XTP 实盘接入
- [ ] QMT 生产化(对账、重连、订单状态轮询)
- [ ] 分红/送股除权事件流
- [ ] LLM Agent 决策链路接入
