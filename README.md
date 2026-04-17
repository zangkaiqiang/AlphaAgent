# AlphaAgent

事件驱动的 A 股量化交易与策略引擎,内置可选的 LLM Agent 层。

## 特性

- **事件驱动架构**:Market / Signal / Order / Fill 四类事件驱动,回测与实盘共用同一套逻辑
- **A 股规则内置**:T+1、最小 100 股、涨跌停、印花税 + 佣金
- **可插拔数据源**:AkShare / Tushare / 本地 Parquet
- **策略即插件**:继承 `Strategy` 基类,注册即用
- **Agent 层可开关**:通过配置启用 LLM 选股/调参,默认关闭
- **自动化调度**:APScheduler 驱动的定时任务
- **回测 → 模拟盘 → 实盘**:同一策略代码三阶段演进

## 目录结构

```
alphaagent/
  core/         # 事件、事件总线、领域类型
  data/         # 数据源适配 (AkShare/Tushare/本地)
  strategy/     # 策略基类 + 内置样例
  backtest/     # 回测引擎
  execution/    # 下单执行 (模拟/实盘)
  risk/         # 风控 (T+1、仓位、止损)
  portfolio/    # 持仓与 PnL
  agent/        # 可选 LLM Agent 层
  scheduler/    # 自动化调度
  config.py     # 全局配置
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

## 配置

见 `configs/example.yaml`。Agent 层通过 `agent.enabled: true/false` 开关。
