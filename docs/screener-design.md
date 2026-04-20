# 选股模块设计方案

> 目标:在 AlphaAgent 中加入**独立于回测的选股工作流**,产出候选清单 → 人工审核 → 喂回测。
> 状态:**设计稿 v2(已评审),未实现**。本文档已吸收 2026-04-19 评审反馈,可作为开发依据。

## 评审吸收记录(v2)

相对 v1 的实质变更:
1. **`ScreenRule` 拆为两类** — 绝对型(`AbsoluteRule`)与横截面型(`CrossSectionalRule`),Pipeline 两趟跑。原先混在一个接口里,实现会拧巴(详见 §3.3)。
2. **新增 `StockMetaProvider` 抽象** — 股票名称/行业/上市日期统一从这里来,不再散落在各处(详见 §3.5)。
3. **直接复用 `DataConfig`** — 不再造 `ScreenDataConfig`,把 `symbols/start/end` 在 screener 上下文里设为可选,从 `universe + as_of + lookback` 推导。
4. **数据拉取并发化** — `ThreadPoolExecutor` 并发 + tqdm 进度条,首次拉沪深 300 目标 < 60s,缓存命中 < 5s(详见 §3.4)。
5. **权重自动归一化 + 缺失规则从分母扣除** — 明确 `final_score ∈ [0, 1]` 不变(详见 §3.4)。
6. **`as_of` 自动规整到交易日** — 复用现有 `AShareCalendar`(详见 §3.4)。
7. **可复现性** — 输出 yaml 携带 `universe_snapshot`,新增 `--replay` 选项用快照重新打分(详见 §6.1, §7.1)。
8. **MVP 输出只做 yaml + csv** — markdown 挪到 v1.1。
9. **工作量从 13h 上调到 ~20h**(详见 §10)。

## 1. 背景与边界

### 1.1 现状的不足

当前框架做"选股"只能靠 `xs_momentum` 在回测中动态轮动 — 这是**策略内部的横截面排序**,不是真正意义上的"选股 → 审核 → 回测"工作流。

实际工作流是这样的:

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│ Universe │ →  │ Screener │ →  │ 人工审核 │ →  │ Backtest │
│ (股票池) │    │ (打分排序)│    │ (中间环节)│    │ (现有流程)│
└──────────┘    └──────────┘    └──────────┘    └──────────┘
                       ↓                              ↑
                  picks.yaml ────── 复制 symbols ─────┘
```

### 1.2 设计原则

1. **回测引擎完全不动** — `BacktestEngine`、`Strategy`、`Portfolio`、`Risk` 全部维持原状
2. **人工审核是核心环节** — 不做"自动 inject 到 strategy.yaml"的便利,强制人工经过一遍
3. **数据源可降级** — MVP 默认 AkShare(免费,有幸存者偏差),留 Tushare 接口位(付费,可防偏差)
4. **规则可组合可扩展** — 内置规则覆盖技术面 80% 场景,基本面规则按需加

### 1.3 不做的事(刻意排除)

- ❌ 实时选股 / 盘中预警 — 选股是离线批处理
- ❌ 选股结果直接驱动下单 — 必须经人工
- ❌ 因子有效性验证(IC/IR/分组回测) — 后续迭代,不在 MVP 范围
- ❌ 行业中性化、市值中性化 — 后续迭代
- ❌ 多因子机器学习模型 — 不在本框架定位内

## 2. 架构

### 2.1 模块分布

```
alphaagent/
  screener/                    ★ 新增
    __init__.py
    base.py                    # Pick / Reason / ScreenResult 类型
    universe.py                # Universe 抽象 + 三种实现
    meta.py                    # StockMetaProvider 抽象 + akshare 实现
    rules.py                   # AbsoluteRule + CrossSectionalRule 接口
    rules_builtin.py           # 内置规则实现
    filters.py                 # HardFilter 接口 + 内置实现
    fetcher.py                 # 并发拉取数据 + tqdm 进度
    pipeline.py                # 组合规则、打分、过滤、排序、归一化
    output.py                  # 输出 yaml / csv (markdown 挪 v1.1)
    config.py                  # screener 自己的 pydantic 模型
  cli.py                       # 加 screen / list-screen-rules 子命令(改)

configs/
  screen.example.yaml          ★ 新增

docs/
  screener-design.md           ★ 本文件
  screener-usage.md            ★ 实现后写

tests/
  test_screener_universe.py    ★ 新增
  test_screener_rules.py       ★ 新增
  test_screener_pipeline.py    ★ 新增
  test_screener_cli.py         ★ 新增
```

### 2.2 与现有模块的关系

| 现有模块 | 改动 | 复用方式 |
|---|---|---|
| `BacktestEngine` | 不改 | — |
| `Strategy` / `Portfolio` / `Risk` | 不改 | — |
| `DataSource` / `CachedDataSource` | 不改 | Screener 拉数据走同一套缓存 |
| `config.py` | 不改 | Screener 用自己的配置模型 |
| `cli.py` | 加一个子命令 | 复用 `_build_data_source` |
| `xs_momentum` 策略 | 不改 | 保留,跟选股不冲突(场景不同) |

## 3. 核心抽象

### 3.1 数据类型

```python
# alphaagent/screener/base.py

from dataclasses import dataclass, field
from datetime import date

@dataclass
class Reason:
    """单条规则对单只股票的评分结果。"""
    rule_name: str
    score: float                  # [0, 1] 归一化分数
    detail: dict                  # 原始指标值,便于人工查看

@dataclass
class Pick:
    """一只候选股票的完整评分结果。"""
    symbol: str
    name: str | None              # 股票名称(便于人工审核)
    final_score: float            # 加权汇总后的最终分
    reasons: list[Reason] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)  # 行业、上市日期等

@dataclass
class ScreenResult:
    """一次选股的完整产出。"""
    generated_at: date
    universe_name: str
    universe_size: int
    filtered_size: int            # 硬过滤后的股票数
    picks: list[Pick]             # 已按 final_score 倒序

    def top(self, n: int) -> list[Pick]:
        return self.picks[:n]
```

### 3.2 Universe 抽象

```python
# alphaagent/screener/universe.py

class Universe(ABC):
    """股票池抽象。"""

    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def get_symbols(self, as_of: date) -> list[str]:
        """返回 as_of 这一天的成分股代码列表。"""
        ...
```

三种实现:

| 实现 | 数据源 | 防幸存者偏差 | 积分需求 |
|---|---|---|---|
| `StaticUniverse` | yaml 写死 | N/A | 免费 |
| `AkshareIndexUniverse` | akshare 当前成分股 | ❌ 否 | 免费 |
| `TushareIndexUniverse` | tushare `index_weight` 月度快照 | ✅ 是 | 2000 积分(后续) |

`TushareIndexUniverse` MVP 只留接口骨架,默认抛 `NotImplementedError("requires Tushare 2000 points; planned for v2")`。

### 3.3 规则抽象(两类)

**关键设计**:绝对评分(站上均线、量能突破)和横截面评分(涨幅排名、波动率排名)是**不同语义**,混在一个接口里实现会拧巴。拆成两个基类,Pipeline 两趟跑。

```python
# alphaagent/screener/rules.py

class AbsoluteRule(ABC):
    """绝对评分规则。每只股票独立计算,不依赖其他股票。
    例:above_ma、price_breakout、volume_breakout
    """
    name: str
    weight: float = 1.0

    @abstractmethod
    def evaluate(self, bars: pd.DataFrame) -> Reason | None:
        """返回 None 表示数据不足,该股票本条规则被跳过(分母会扣除该权重)。"""
        ...

class CrossSectionalRule(ABC):
    """横截面评分规则。需要全池数据后做相对排名归一化。
    例:momentum、reversal、low_volatility
    """
    name: str
    weight: float = 1.0

    @abstractmethod
    def evaluate_all(
        self,
        panel: dict[str, pd.DataFrame],   # 全池股票的 bars
    ) -> dict[str, Reason]:
        """返回 {symbol: Reason}。数据不足的 symbol 不出现在结果里。"""
        ...

class HardFilter(ABC):
    """硬过滤。不产生分数,只决定股票是否进入打分阶段。"""
    name: str

    @abstractmethod
    def keep(
        self,
        symbol: str,
        bars: pd.DataFrame,
        meta: StockMeta,           # 见 §3.5
    ) -> bool: ...
```

#### 规则归类速查

| 规则名 | 类型 |
|---|---|
| `above_ma` | AbsoluteRule |
| `price_breakout` | AbsoluteRule |
| `volume_breakout` | AbsoluteRule |
| `momentum` | CrossSectionalRule |
| `reversal` | CrossSectionalRule |
| `low_volatility` | CrossSectionalRule |

### 3.4 Pipeline

```python
# alphaagent/screener/pipeline.py

class ScreenerPipeline:
    def __init__(
        self,
        universe: Universe,
        data_source: DataSource,             # 复用现有 DataSource(已带缓存)
        meta_provider: StockMetaProvider,    # 见 §3.5
        absolute_rules: list[AbsoluteRule],
        xs_rules: list[CrossSectionalRule],
        filters: list[HardFilter],
        as_of: date,
        lookback_days: int,                  # >= max(rule lookbacks) + 余量
        calendar: AShareCalendar | None = None,
        max_workers: int = 16,               # 并发拉取
    ): ...

    def run(self) -> ScreenResult: ...
```

#### 执行流程(7 步)

1. **as_of 规整**:若提供 `calendar`,把 `as_of` 推到 `≤ as_of` 的最近**交易日**;输出 `resolved_as_of` 给 CLI 显示。
2. **取股票池**:`symbols = universe.get_symbols(resolved_as_of)`;输出快照 `universe_snapshot`(供 `--replay`)。
3. **并发拉数据**:`ThreadPoolExecutor(max_workers)` 调 `data_source.get_bars`,带 tqdm 进度。`CachedDataSource` 命中时秒返。
   - 性能目标:沪深 300 + 缓存命中 → **< 5s**;首次拉取 → **< 60s**(并发 16)
4. **取元数据**:`meta_provider.get_meta(symbol)` 批量拿名称/行业/上市日期(本地缓存,§3.5)。
5. **硬过滤**:`for f in filters: keep = f.keep(symbol, bars, meta)`;任一返回 False 则剔除。
6. **打分(两趟)**:
   - 绝对型:逐股 `rule.evaluate(bars)`
   - 横截面型:`rule.evaluate_all(panel)` 一次拿全池
7. **加权汇总 + 归一化** → 排序 → 打包 `ScreenResult`。

#### 权重归一化规则(明确)

```
对每只股票 s:
    applicable_rules = {r for r in rules if s in r.scores}   # 数据足够的规则
    total_weight = sum(r.weight for r in applicable_rules)
    if total_weight == 0:
        s.final_score = 0.0
    else:
        s.final_score = sum(r.weight * r.scores[s] for r in applicable_rules) / total_weight
```

含义:
- **权重自动归一化**,yaml 里写 `0.4 + 0.2 + 0.2 + 0.2` 还是 `4 + 2 + 2 + 2` 等价
- **缺失规则从分母扣除**,不会因数据缺失把分数拖低
- **`final_score ∈ [0, 1]`** 始终成立(假设每条规则的分数也在 [0, 1])

> ⚠️ 副作用:同一股票如果命中规则不一样,分数严格不可比。这是合理代价 — 比"分数被空缺拖低"更符合直觉。`Reason.detail` 会记录该股具体命中了哪些规则,人工审核可见。

### 3.5 StockMetaProvider 抽象

股票名称、行业、上市日期、退市日期等**静态/慢变元数据**,跟 bar 行情分离管理。

```python
# alphaagent/screener/meta.py

@dataclass
class StockMeta:
    symbol: str
    name: str
    industry: str | None
    list_date: date | None
    delist_date: date | None
    is_st: bool                     # MVP: 由名称关键字推导;v2 切 stock_st 接口

class StockMetaProvider(ABC):
    @abstractmethod
    def get_meta(self, symbol: str, as_of: date) -> StockMeta: ...

    def get_meta_batch(self, symbols: list[str], as_of: date) -> dict[str, StockMeta]:
        """默认实现:并发调 get_meta。子类可重写为单次批量接口。"""
        ...
```

#### 三种实现

| 实现 | 数据源 | 缓存策略 | MVP |
|---|---|---|---|
| `AkshareMetaProvider` | `stock_info_a_code_name` + `stock_individual_info_em` | `data/cache/meta/{symbol}.json`,**按天 TTL** | ✅ |
| `TushareMetaProvider` | `stock_basic` 一次拿全市场 | 同上,但批量更省 | v2 |
| `CSVMetaProvider` | `meta.csv`(symbol,name,industry,list_date) | 直接读 | ✅ 测试用 |

**为什么名称按天缓存而不是永久缓存?**
A 股股票名称会变(戴帽/摘帽 ST、改名、转板),代码不变。缓存名称必须有 TTL,否则 `exclude_st` 会失效。代码本身永久缓存没问题。

## 4. 内置规则库(MVP)

全部基于免费 AkShare 行情数据。

### 4.1 打分规则

| 规则名 | 类型 | 含义 | 参数 | 计分方式 |
|---|---|---|---|---|
| `momentum` | 横截面 | 过去 N 天涨幅 | `lookback: int = 60` | 涨幅排名 → 百分位归一化 |
| `reversal` | 横截面 | 过去 N 天跌幅(反向) | `lookback: int = 20` | 跌幅排名 → 百分位归一化 |
| `low_volatility` | 横截面 | 过去 N 天日收益标准差 | `lookback: int = 20` | 波动越低分越高(百分位反向) |
| `above_ma` | 绝对 | 当前价站上 N 日均线 | `period: int = 60` | 命中 1.0 / 未命中 0.0 |
| `price_breakout` | 绝对 | 突破过去 N 天最高价 | `lookback: int = 60` | 命中 1.0 / 未命中 0.0 |
| `volume_breakout` | 绝对 | 当日**成交额** z-score | `lookback: int = 20`, `z_threshold: float = 1.5` | z >= 阈值得 1.0,否则线性 |

#### 实现注解

- **`volume_breakout` 用 `amount` 不用 `volume`**:A 股除权会让 `volume` 跳变(送股后股本翻倍 → 成交量数字翻倍但实际换手没变),`amount`(成交额)对除权天然中性。
- **`momentum` 是绝对涨幅,不扣基准**:牛市里会全是同一风格(高 beta 股票)。MVP 不做基准扣除,后续可加 `momentum_vs_benchmark` 规则单算。
- **横截面规则的"百分位归一化"**:`score(s) = rank(s) / (N - 1)`,N 是参与排名的股票数。最高 1.0,最低 0.0。

### 4.2 硬过滤(HardFilter)

| 过滤名 | 含义 | 参数 |
|---|---|---|
| `min_price` | 当前价 ≥ X 元(剔除低价股/壳股) | `min_price: float = 3.0` |
| `max_price` | 当前价 ≤ X 元(剔除高价不便建仓) | `max_price: float = 500.0` |
| `min_avg_volume` | 过去 N 天日均成交额 ≥ X | `lookback: int = 20`, `min_amount: float = 1e7` |
| `exclude_st` | 剔除名称含 ST/退/\* 的股票 | `name_keywords: list[str] = ["ST", "退", "*"]` |
| `min_listed_days` | 上市满 N 天(剔除次新) | `min_days: int = 250` |

> ⚠️ `exclude_st` 在 MVP 里靠**股票名称关键字**判断,只看"今天"的名称,**漏掉中途摘帽/戴帽的历史**。代码里要加 `# TODO(v2): switch to Tushare stock_st for accurate historical ST list`。
> 升级到 Tushare 3000 积分后,改用 `stock_st` 接口的精确历史 ST 名单。

### 4.3 后续规则(Tushare 2000+ 积分,v2)

| 规则名 | 数据来源 | 含义 |
|---|---|---|
| `low_pe` | `daily_basic` | 低 PE |
| `low_pb` | `daily_basic` | 低 PB |
| `high_roe` | 财务接口 | 高 ROE |
| `earnings_surprise` | `forecast` | 业绩预告超预期 |
| `industry_in` | `stock_basic` | 限定行业 |

## 5. 配置文件

### 5.1 完整示例 `configs/screen.example.yaml`

```yaml
# 选股工作流配置,跟回测的 strategy.yaml 解耦

universe:
  source: akshare_index         # static | akshare_index | tushare_index
  index_code: "000300"          # 沪深 300 (中证: 000300, 上证 50: 000016, 中证 500: 000905)
  # static 模式:
  # source: static
  # symbols: ["600000", "000001", ...]

# 直接复用现有 alphaagent/config.py 的 DataConfig
# 在 screener 上下文里,symbols/start/end 自动从 universe + as_of + lookback_days 推导
data:
  source: akshare
  freq: 1d
  adjust: qfq
  cache_dir: ./data/cache

as_of: 2024-12-31               # 选股的"今天"。非交易日会自动规整到 ≤ 该日的最近交易日
lookback_days: 120              # 算因子的回看窗口(应 >= 所有规则 lookback 最大值 + 余量)
calendar_enabled: true          # 启用 AShareCalendar 做 as_of 规整(强烈建议 true)

meta:
  source: akshare               # akshare | tushare | csv
  cache_dir: ./data/cache/meta  # 元数据按天 TTL 缓存
  # csv: ./data/meta.csv        # source=csv 时

# 硬过滤(在打分之前剔除股票)
filters:
  - type: min_price
    min_price: 3.0
  - type: max_price
    max_price: 500.0
  - type: min_avg_volume
    lookback: 20
    min_amount: 10000000        # 1 千万元
  - type: exclude_st
  - type: min_listed_days
    min_days: 250

# 打分规则(权重自动归一化,缺失从分母扣除;详见 §3.4)
rules:
  - type: momentum
    lookback: 60
    weight: 0.4
  - type: above_ma
    period: 60
    weight: 0.2
  - type: low_volatility
    lookback: 20
    weight: 0.2
  - type: volume_breakout
    lookback: 20
    z_threshold: 1.5
    weight: 0.2

execution:
  max_workers: 16               # 并发拉取数据的线程数
  show_progress: true           # tqdm 进度条

output:
  path: ./picks.yaml            # CLI -o 可覆盖
  top_n: 30
  with_reasons: full            # full | compact | none
  format: yaml                  # yaml | csv (markdown 移到 v1.1)
```

### 5.2 配置模型(pydantic)

```python
# alphaagent/screener/config.py (跟主配置解耦,但复用 DataConfig)

from alphaagent.config import DataConfig  # 直接复用

class UniverseConfig(BaseModel):
    source: Literal["static", "akshare_index", "tushare_index"]
    index_code: str | None = None
    symbols: list[str] | None = None

class MetaConfig(BaseModel):
    source: Literal["akshare", "tushare", "csv"] = "akshare"
    cache_dir: str = "./data/cache/meta"
    csv: str | None = None

class FilterConfig(BaseModel):
    type: str
    # 其余字段按 type 动态校验

class RuleConfig(BaseModel):
    type: str
    weight: float = 1.0
    # 其余字段按 type 动态校验

class ExecutionConfig(BaseModel):
    max_workers: int = 16
    show_progress: bool = True

class OutputConfig(BaseModel):
    path: str = "./picks.yaml"
    top_n: int = 30
    with_reasons: Literal["full", "compact", "none"] = "full"
    format: Literal["yaml", "csv"] = "yaml"

class ScreenConfig(BaseModel):
    universe: UniverseConfig
    data: DataConfig                                # 直接复用
    as_of: date
    lookback_days: int = 120
    calendar_enabled: bool = True
    meta: MetaConfig = MetaConfig()
    filters: list[FilterConfig] = Field(default_factory=list)
    rules: list[RuleConfig]
    execution: ExecutionConfig = ExecutionConfig()
    output: OutputConfig = OutputConfig()
```

> 复用 `DataConfig` 的代价:`DataConfig.symbols/start/end` 在 backtest 里是必填,在 screener 里不用。两种方案:
> 1. 把 `DataConfig` 的 `start/end` 改成可选,加 `model_validator` 只在没 universe 时强制
> 2. 在 screener 里包一层,初始化时用 `as_of-lookback_days` 填进去后再传
>
> 倾向 **方案 2**(零侵入,不改 DataConfig 现有契约)。

## 6. CLI 设计

### 6.1 子命令

```bash
# 跑选股(正常模式)
alphaagent screen --config configs/screen.example.yaml -o picks.yaml

# 校验配置(不拉数据)
alphaagent screen --config configs/screen.example.yaml --dry-run

# 列出所有可用规则和过滤器
alphaagent list-screen-rules

# Replay:用上次产出的 picks.yaml 里的 universe_snapshot 重新打分
# 用途:排查"分数变化是来自规则改动还是池子变化"
alphaagent screen --config configs/screen.example.yaml --replay picks.yaml -o picks_v2.yaml
```

`--replay` 语义:跳过 §3.4 步骤 1-2(as_of 规整 + universe 拉取),直接用 `picks.yaml.metadata.universe_snapshot` 当股票池;其余流程(数据拉取、过滤、打分)正常跑。

### 6.2 输出示例(终端)

```
Universe: hs300 (akshare current components, 300 symbols)
as_of: 2024-12-31 → resolved to trading day 2024-12-31

Fetching data... [▓▓▓▓▓▓▓▓▓▓] 300/300 (cache hit: 287/300, took 4.2s)
Fetching meta... [▓▓▓▓▓▓▓▓▓▓] 300/300 (cache hit: 300/300, took 0.1s)

Applying filters:
  min_price          → kept 295
  max_price          → kept 295
  min_avg_volume     → kept 248
  exclude_st         → kept 246
  min_listed_days    → kept 240

Scoring 240 symbols:
  Absolute rules:    above_ma, volume_breakout
  Cross-sectional:   momentum, low_volatility

Top 10:
  600519  贵州茅台      0.873   momentum:0.95 above_ma:1.0 low_vol:0.82 vol_brk:0.62
  000858  五粮液        0.851   momentum:0.91 above_ma:1.0 low_vol:0.78 vol_brk:0.65
  ...

Wrote 30 picks to picks.yaml (with universe_snapshot for --replay)
```

## 7. 输出格式

### 7.1 yaml(默认,便于贴回 strategy.yaml)

```yaml
# picks.yaml — generated 2024-12-31
metadata:
  generated_at: 2024-12-31
  resolved_as_of: 2024-12-31      # as_of 规整后的真实交易日
  universe: hs300
  universe_size: 300
  filtered_size: 240
  rules:
    - momentum (weight=0.4)
    - above_ma (weight=0.2)
    - low_volatility (weight=0.2)
    - volume_breakout (weight=0.2)
  # 完整成分股快照,供 --replay 复现
  universe_snapshot:
    - "000001"
    - "000002"
    # ... 全部 300 只

# 直接复制到 strategy.yaml 的 data.symbols
symbols:
  - "600519"
  - "000858"
  - "601318"
  # ...

# 详细评分(供人工审核,复制 symbols 时不需要)
# with_reasons: full
candidates:
  - symbol: "600519"
    name: "贵州茅台"
    final_score: 0.873
    reasons:
      - rule: momentum
        score: 0.95
        detail: { return_60d: 0.185, rank: 12 }
      - rule: above_ma
        score: 1.0
        detail: { close: 1620.5, ma60: 1502.3 }
      - rule: low_volatility
        score: 0.82
        detail: { vol_20d: 0.012 }
      - rule: volume_breakout
        score: 0.62
        detail: { volume_z: 1.62 }
    metadata:
      industry: 白酒
      list_date: "2001-08-27"
```

`with_reasons` 三档:

| 值 | 输出内容 | 适用 |
|---|---|---|
| `full` | 每条规则的 score + detail | 严肃人工审核 |
| `compact` | 只输出 final_score 和命中分最高的 top_rule | 快速浏览,yaml 短 5x |
| `none` | 不输出 candidates 块,只留 symbols | 自动化场景,最短 |

### 7.2 csv(便于 Excel 审核)

```csv
symbol,name,final_score,momentum,above_ma,low_vol,vol_brk,industry
600519,贵州茅台,0.873,0.95,1.0,0.82,0.62,白酒
000858,五粮液,0.851,0.91,1.0,0.78,0.65,白酒
...
```

### 7.3 markdown — **挪到 v1.1**(YAGNI,等用户要了再加)

## 8. 端到端工作流

### 8.1 用户视角(三步)

```bash
# Step 1: 选股
alphaagent screen --config configs/screen.example.yaml -o picks.yaml

# Step 2: 人工审核 picks.yaml
#   - 看每只股票的评分理由
#   - 剔除明显不合理的(行业过度集中、刚发生重大利空、最近有除权事件...)
#   - 把审核后的 symbols 列表复制到 strategy.yaml

# Step 3: 回测(完全走现有流程)
alphaagent backtest --config configs/strategy.yaml
```

### 8.2 推荐的审核 checklist(写进 README)

人工审核 `picks.yaml` 时关注:
1. **行业集中度** — 30 只里有 15 只白酒?手动剔除一些
2. **市值分布** — 全是大盘股?可能选股规则偏向高动量+低波动
3. **近期公告** — 用同花顺/东财查最近一周公告,剔除有重大利空的
4. **复权事件** — 临近除权日的股票排除(打分会失真)
5. **流动性** — 即便过了硬过滤,日均成交额 < 5000 万的也要谨慎

## 9. 测试方案

### 9.1 单元测试

```
tests/test_screener_universe.py
  - StaticUniverse: 直接返回固定列表
  - AkshareIndexUniverse: mock akshare 接口,断言返回成分股
  - TushareIndexUniverse: mock,断言抛 NotImplementedError(MVP 阶段)

tests/test_screener_meta.py
  - CSVMetaProvider: 读 fixture
  - AkshareMetaProvider: mock + 断言按天 TTL 缓存生效

tests/test_screener_rules.py
  - 每条规则用 3-5 只股票的小数据集断言:
    - 绝对型: above_ma 边界(价 = 均线 ± epsilon)、price_breakout、volume_breakout 边界
    - 横截面: momentum 排名、low_volatility 反向排名
    - 数据不足时:绝对型返回 None、横截面 dict 不含该 symbol

tests/test_screener_filters.py
  - 每个 HardFilter 单独测,边界值

tests/test_screener_pipeline.py
  - 端到端:5 只股票 + 2 绝对 + 2 横截面 + 1 过滤,断言最终排序
  - 权重归一化:0.4+0.2+0.2+0.2 == 4+2+2+2
  - 缺失规则从分母扣除:断言两只 final_score 不可比但都在 [0, 1]
  - as_of 非交易日 → 自动规整到前一交易日
  - --replay 模式:用快照重新打分,绕过 universe 拉取
```

### 9.2 集成测试

```
tests/test_screener_cli.py
  - 用 CSV 数据源 + StaticUniverse + CSVMetaProvider 跑完整 CLI(不依赖网络)
  - 断言生成的 picks.yaml 内容正确
  - 断言 yaml 的 symbols 字段能被 backtest 配置解析(向后兼容)

tests/test_screener_snapshot.py
  - Snapshot 测试:固定 fixture(5 只股票 × 120 天 csv)
  - 跑完整 pipeline,断言 picks.yaml 跟 tests/snapshots/picks.golden.yaml 字节级相等
  - 防回归利器,任何规则/归一化逻辑变动都会触发
  - 故意改 yaml 后跑测试,要求 diff 清晰可读
```

### 9.3 不测的事

- ❌ 真实 akshare 网络调用(慢且不稳定,放在手动 smoke test)
- ❌ 真实 tqdm 进度条渲染(用 `disable=True` 或 mock)
- ❌ Tushare 接口(MVP 没实现)

## 10. 工作量估计(v2 修订)

| 任务 | v1 估计 | v2 修订 |
|---|---|---|
| `screener/base.py` 数据类 + 接口 | 0.5h | 0.8h |
| `screener/universe.py` 三种实现 | 1.5h | 1.5h |
| `screener/meta.py` StockMetaProvider + 3 实现 | — | **2.0h** ★新增 |
| `screener/rules.py` 接口 + 6 条规则(两类) | 2h | **3.0h** ★拆两类 |
| `screener/filters.py` 5 个过滤器 | 1h | 1.0h |
| `screener/fetcher.py` 并发 + tqdm | — | **1.5h** ★新增 |
| `screener/pipeline.py` 主流程 + 归一化 + 两趟跑 + replay | 1.5h | **2.5h** |
| `screener/output.py` yaml + csv + compact 模式 | 1h | 1.2h |
| `screener/config.py` pydantic 模型 | 1h | 1.0h |
| `cli.py` 加 screen / list / replay / dry-run | 0.5h | 1.0h |
| 单元测试(5 个测试文件) | 3h | **4.0h** |
| Snapshot 测试 + fixture | — | **1.0h** ★新增 |
| `configs/screen.example.yaml` | 0.2h | 0.2h |
| README 加"选股"章节 | 0.5h | 0.5h |
| `docs/screener-usage.md` 用户指南 | 0.8h | 0.8h |

**v1 合计: ~13h** → **v2 合计: ~21h(~3 个工作日)**

新增的工作主要在:`StockMetaProvider`、并发 fetcher、规则两类拆分、snapshot 测试。这些都是评审反馈强烈支持的项,值得花。

## 11. Roadmap(实现后的演进)

### v1 (本设计) — 免费可用
- AkShare 当前成分股
- 6 条技术规则 + 5 个硬过滤
- yaml/csv/markdown 输出

### v2 — 防幸存者偏差 + 基本面
- Tushare `index_weight` 历史月度成分股(2000 积分)
- Tushare `daily_basic` PE/PB/换手率(2000 积分)
- Tushare `stock_st` ST 名单(3000 积分)
- 加 `low_pe`、`low_pb`、`high_turnover` 等规则

### v3 — 因子研究工具
- 单因子 IC/IR 检验
- 分组回测(把 universe 分成 5/10 组,看 spread)
- 因子相关性矩阵

### v4(可选) — 多因子模型
- 因子合成(等权 / 半衰期加权 / IC 加权)
- 行业中性化、市值中性化
- 不做机器学习,这超出框架定位

## 12. 评审决策汇总

评审已通过,8 个待确认项的最终决策:

| # | 问题 | 决策 |
|---|---|---|
| 1 | 整体架构 | ✅ 通过。`DataConfig` 直接复用,不造 `ScreenDataConfig` |
| 2 | MVP 规则覆盖 | ✅ 6 条够,**已拆分绝对/横截面两类** |
| 3 | 三种 Universe | ✅ 通过,Tushare 留 `NotImplementedError` |
| 4 | 输出格式 | ✅ MVP 只做 yaml + csv,**markdown 挪 v1.1** |
| 5 | `inject-symbols` 工具 | ❌ **不加**,强制人工审核 |
| 6 | `as_of` 语义 | ✅ 选股的"今天",**自动规整到 ≤ as_of 的最近交易日** |
| 7 | `exclude_st` 用名称 | ✅ MVP 用名称,代码加 `# TODO(v2)` 注释 |
| 8 | e2e 一键化 | ❌ **不加**;但 ✅ **加 `--replay`** 用快照重新打分 |

## 13. 实现 Checklist(开干前过一遍)

- [ ] 评审通过(本文件)
- [ ] 创建 `alphaagent/screener/` 目录结构(§2.1)
- [ ] 实现核心抽象:`Pick`、`Reason`、`ScreenResult`、`Universe`、`StockMetaProvider`、`AbsoluteRule`、`CrossSectionalRule`、`HardFilter`
- [ ] 实现 6 条规则、5 个过滤器
- [ ] 实现 `Pipeline`(并发 fetcher、两趟打分、权重归一化、as_of 规整、replay)
- [ ] 实现 yaml/csv 输出 + 三档 `with_reasons`
- [ ] 实现 `cli.py` 三个子命令
- [ ] 写 `configs/screen.example.yaml`
- [ ] 写 6 个测试文件 + snapshot fixture
- [ ] 跑 `uv run pytest -q`,全绿
- [ ] 跑 `uv run alphaagent screen --config configs/screen.example.yaml`,sanity check
- [ ] README 加"选股"章节(链接到本设计 + usage)
- [ ] 写 `docs/screener-usage.md`(用户视角的快速开始)

---

**附录 A: 跟 `xs_momentum` 策略的区别**

| 维度 | `xs_momentum` (现有策略) | `screener` (本设计) |
|---|---|---|
| 运行时机 | 回测期内,每个 rebalance_days 一次 | 离线一次性,产出快照 |
| 输入 | yaml 写死的 symbols(回测股票池) | universe(沪深 300 等) |
| 输出 | BUY/SELL 信号,直接驱动下单 | yaml 候选清单,给人审核 |
| 审核环节 | 无(自动执行) | 必须人工 |
| 数据范围 | 流式 bar(逐根) | 全历史窗口(批处理) |
| 适用场景 | 高频轮动(如月度调仓) | 月度/季度建池子 |

二者**互补**而非替代。典型用法:用 `screener` 季度刷新 30 只候选股票池,然后在这个池子上跑 `xs_momentum` 月度轮动持有前 5。

**附录 B: Tushare 积分门槛速查(供 v2 参考)**

| 接口 | 用途 | 积分 |
|---|---|---|
| `index_weight` | 历史指数成分股 | 2000 |
| `stock_basic` | 股票基本信息(含退市) | 2000 |
| `daily_basic` | PE/PB/换手率 | 2000 |
| `stock_st` | ST 名单 | 3000 |
| `forecast` | 业绩预告 | 2000 |
| 分钟数据 | — | 独立权限,需单独申请 |

注册即送 20 积分,2000 积分需要捐赠(具体金额以官网"社区捐助"页为准,社区惯例 ≈ 200 元)。
