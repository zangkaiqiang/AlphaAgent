# AlphaAgent

事件驱动的 A 股量化交易与策略引擎,内置可选的 LLM Agent 层。

## 特性

- **事件驱动架构**:Market → Signal → Order → Fill 四类事件驱动,回测与实盘共用同一套逻辑
- **A 股规则内置**:T+1、最小 100 股、涨跌停、印花税 + 佣金
- **组合级风控**:总敞口、单股敞口、持仓只数上限,自动降档或拒单
- **多数据源**:AkShare / Tushare / 本地 CSV,内建 Parquet 缓存
- **日/分钟频**:`1d`、`1m`、`5m`、`15m`、`30m`、`60m`
- **交易日历**:SSE 日历 + 会话窗口(09:30-11:30、13:00-15:00),自动过滤非交易时段
- **性能指标**:Sharpe、Sortino、最大回撤、Calmar、胜率、盈利因子等 13 项
- **策略即插件**:继承 `Strategy` 基类,注册即用
- **多策略组合**:并行运行多个策略,独立子账户,按权重分配资金,含每策略 PnL 归因
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

查看所有已注册策略:

```bash
alphaagent list-strategies
```

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

CLI 运行时会打印 `downsized` 和 `rejected` 计数,一眼看出哪些规则在生效:

```
Risk rules: ['max_gross_exposure', 'max_per_symbol_exposure']
Fills:   6
Risk:    downsized=3 rejected=0
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
- [x] 多策略组合 + 独立子账户 + 每策略归因
- [x] 策略库:MA Cross / RSI / Bollinger × 2 / 截面动量
- [x] 组合级风控(总敞口、单股、只数、板块集中度、相关性)
- [ ] 实盘券商对接(QMT / XTP)
- [ ] 分红/送股除权事件流
- [ ] LLM Agent 决策链路接入
