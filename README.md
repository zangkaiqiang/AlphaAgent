# AlphaAgent

事件驱动的 A 股量化交易与策略引擎,内置可选的 LLM Agent 层。

## 特性

- **事件驱动架构**:Market → Signal → Order → Fill 四类事件驱动,回测与实盘共用同一套逻辑
- **A 股规则内置**:T+1、最小 100 股、涨跌停、印花税 + 佣金
- **多数据源**:AkShare / Tushare / 本地 CSV,内建 Parquet 缓存
- **日/分钟频**:`1d`、`1m`、`5m`、`15m`、`30m`、`60m`
- **交易日历**:SSE 日历 + 会话窗口(09:30-11:30、13:00-15:00),自动过滤非交易时段
- **性能指标**:Sharpe、Sortino、最大回撤、Calmar、胜率、盈利因子等 13 项
- **策略即插件**:继承 `Strategy` 基类,注册即用
- **Agent 层可开关**:通过配置启用 LLM 选股/调参,默认关闭
- **自动化调度**:APScheduler 驱动的定时任务

## 目录结构

```
alphaagent/
  core/         # 事件、事件总线、领域类型
  data/         # 数据源适配 (AkShare/Tushare/CSV) + Parquet 缓存
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
  cli.py        # 命令行入口
strategies/     # 用户策略目录
configs/        # YAML 配置
tests/
```

## 快速开始

```bash
pip install -e ".[data,dev]"
alphaagent backtest --config configs/example.yaml
```

输出示例:

```
Agent: NullAgent (enabled=False)
Calendar: off  Freq: 1d
Initial: 1,000,000.00
Final:   1,015,874.15
Bars:    processed=240 skipped=0
Fills:   13

Performance
-----------
Total Return:          1.59%
Annualized Return:     3.25%
Annualized Vol:        4.02%
Sharpe:                 0.82
Sortino:                0.69
Max Drawdown:         -1.24%
Calmar:                 2.62
Trades:                    6
Win Rate:             16.67%
Avg Win:             8953.69
Avg Loss:           -1502.29
Profit Factor:          1.19
Total PnL:           1442.26
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
  cache_dir: ./data/cache  # 启用 Parquet 本地缓存;留空则禁用
  # tushare_token: ""      # 或通过 TUSHARE_TOKEN 环境变量

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

当 `cache_dir` 被设置时,`CachedDataSource` 会把每个 symbol 的行情落为 Parquet。后续回测只会请求 **缓存范围之外** 的时间段(头/尾增量),大幅减少网络调用。

## 编写自定义策略

在 `strategies/` 下新建文件,继承 `Strategy`:

```python
from alphaagent.strategy import Strategy
from alphaagent.core.types import Bar, Side

class MyStrategy(Strategy):
    strategy_id = "my_strategy"

    def on_bar(self, bar: Bar) -> None:
        # 访问 self.ctx.positions、self.ctx.cash
        # 触发信号:
        self.ctx.emit_signal(bar, Side.BUY, strength=1.0)
```

把策略名注册到 `alphaagent/cli.py::_build_strategy`(后续会做成自动发现)。

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
│  Data Layer (行情,统一接口) + Parquet 缓存      │
├─────────────────────────────────────────────────┤
│  Brokers (AkShare / Tushare / CSV / [QMT/XTP])   │
└─────────────────────────────────────────────────┘
```

## 开发

```bash
pip install -e ".[data,dev]"
pytest -q
ruff check alphaagent tests
```

## Roadmap

- [x] 事件驱动核心 + A 股风控
- [x] AkShare + Tushare 数据源 + Parquet 缓存
- [x] 日/分钟频 + 交易日历过滤
- [x] 13 项性能指标
- [ ] 多策略组合 + 组合级风控
- [ ] 实盘券商对接(QMT / XTP)
- [ ] 分红/送股除权事件流
- [ ] LLM Agent 决策链路接入
