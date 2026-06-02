# SQLite 持久化改造设计

- 日期:2026-06-02
- 状态:待实现
- 架构方案:A(单库 + 薄存储层)
- 定位:**Web-only 迁移路线图的 Phase 1**(三阶段见 §14)。本次整体方向是「功能全部走 Web、移除 CLI 命令模式」。

## 1. 背景与目标

AlphaAgent 当前的数据持久化分散在三处:回测任务/结果(纯内存,服务重启即丢)、行情数据缓存(每个 `(symbol,freq,source)` 一个 Parquet 文件)、交易日历缓存(单个 Parquet)。

本次改造把这三处统一迁移到 **SQLite**,目标:

1. 回测历史与结果**跨进程重启可见**(Web 应用最该持久化的部分)。
2. 行情/日历缓存统一进单库,便于备份与 SQL 查询;行情写入从「整文件重写」优化为**行级 upsert**。
3. 零新增运行时依赖(`sqlite3` 标准库 + 已有 `pandas`)。

**不在本次范围:** 基本面 `_TTLCache`(进程内 5 分钟易失缓存,保持现状);screener 的 `picks.yaml`(人工审核产物,保持 YAML)。

## 2. 技术选型

- **标准库 `sqlite3` + `pandas`**(已确认)。jobs/calendar 手写少量 SQL;OHLCV 用 `pd.read_sql` / `executemany` 批量写。
- 不引入 SQLAlchemy / SQLModel / DuckDB,贴合项目既有「不引入 DuckDB」的极简风格。

## 3. 架构总览

```
alphaagent/storage/            # 新包:统一连接 + schema
  db.py        Database / get_database()
data/sqlite_cache.py           # SqliteBarCache 替换 CachedDataSource
calendar/ashare.py             # _load 增加 DB 路径分支
api/job_store.py               # 内存活对象 + 终态落库 + 启动恢复
cli.py                         # 新增 migrate-cache 命令
config.py                      # 新增 StorageConfig
```

所有数据进**同一个库文件**,jobs/bars/calendar **共用一个 `Database` 连接**(进程级单例)。

## 4. 存储层 `alphaagent/storage/`

### 4.1 `Database`(`db.py`)

封装一个 `sqlite3` 连接,集中处理并发与建表:

- `sqlite3.connect(path, check_same_thread=False)`(回测跑在 `BackgroundTasks` worker 线程,需跨线程共享连接)。
- 初始化 PRAGMA:`journal_mode=WAL`(读并发)、`busy_timeout=5000`、`synchronous=NORMAL`;`row_factory = sqlite3.Row`。
- `threading.Lock`(`_write_lock`)串行化所有写入(`execute`/`executemany` + `commit`)。WAL 下读不需加锁。
- 方法:
  - `executescript(sql)` / `execute(sql, params)` / `executemany(sql, seq)`(自动加写锁 + commit)。
  - `query(sql, params) -> list[sqlite3.Row]`。
  - `query_df(sql, params) -> pd.DataFrame`(`pd.read_sql_query`,供行情读取)。
  - `init_schema()`:幂等 `CREATE TABLE IF NOT EXISTS`(见 §5)。

### 4.2 `get_database(path=None)`

- 先解析路径(优先级:显式参数 > 环境变量 `ALPHAAGENT_DB` > 默认 `./data/alphaagent.db`,统一取绝对路径),再**按解析后的绝对路径缓存 `Database` 实例**:同路径复用同一实例,不同路径各自独立。
- 生产:API 侧 `get_database()`(env/默认)与 CLI 侧 `get_database(cfg.storage.db_path)` 只要解析到同一路径即拿到同一实例 → 同一进程单库。
- 测试:显式传 tmp 文件 / `:memory:` 路径即得隔离实例。
- 实例创建时自动 `init_schema()`。

> 设计约束:**生产中每个进程应解析到同一库路径**。`storage.db_path` 默认与 `ALPHAAGENT_DB`/默认值一致(均为 `./data/alphaagent.db`),避免回测库与 jobs 库分裂;按路径缓存的设计仅为支持测试隔离。

## 5. 数据库 Schema

```sql
CREATE TABLE IF NOT EXISTS bars (
    source_id TEXT NOT NULL,
    symbol    TEXT NOT NULL,
    freq      TEXT NOT NULL,
    dt        TEXT NOT NULL,           -- ISO 时间戳
    open   REAL, high REAL, low REAL, close REAL,
    volume REAL, amount REAL,
    PRIMARY KEY (source_id, symbol, freq, dt)
);   -- 复合主键即 (source_id,symbol,freq,dt) 范围扫描索引

CREATE TABLE IF NOT EXISTS trade_calendar (
    dt TEXT PRIMARY KEY               -- 'YYYY-MM-DD'
);

CREATE TABLE IF NOT EXISTS jobs (
    id             TEXT PRIMARY KEY,
    label          TEXT,
    status         TEXT NOT NULL,
    progress       REAL    NOT NULL DEFAULT 0,
    bars_processed INTEGER NOT NULL DEFAULT 0,
    bars_total     INTEGER NOT NULL DEFAULT 0,
    fill_count     INTEGER NOT NULL DEFAULT 0,
    started_at     TEXT,
    completed_at   TEXT,
    error          TEXT,
    result_json    TEXT,              -- BacktestResultDTO 的 JSON(已 model_dump(mode="json"))
    created_at     TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_jobs_created ON jobs(created_at);
```

行情帧规范列(见 `data/base.py`):`open/high/low/close/volume/amount`,`amount` 可缺失(存 NULL)。`dt` 以 ISO 字符串存储,读出时 `pd.to_datetime` 还原为 datetime 索引。

## 6. 行情缓存 `data/sqlite_cache.py`

`SqliteBarCache(DataSource)`,替换 `CachedDataSource`:

- `__init__(self, upstream: DataSource, db: Database, source_id: str)`(`source_id` 非空,沿用现有分区语义)。
- `get_bars(symbol, start, end, freq)`:
  1. `SELECT MIN(dt), MAX(dt) FROM bars WHERE source_id=? AND symbol=? AND freq=?`。
  2. 无缓存 → 拉全区间 → upsert → 返回。
  3. 有缓存 → `start < cache_min` 拉头段、`end > cache_max` 拉尾段,各自 upsert。
  4. `query_df(SELECT ... WHERE ... AND dt BETWEEN ? AND ? ORDER BY dt)` → 设 datetime 索引返回。
- upsert:`INSERT OR REPLACE INTO bars(...) VALUES(...)` via `executemany`,主键天然去重。
- **与现有 Parquet 增量逻辑等价**,但避免整文件重写;头/尾分段拉取行为与 `test_cache.py` 的断言保持一致(切片不重拉、按需扩展两次)。

`runtime.build_data_source`:缓存开启时改为
`source = SqliteBarCache(source, get_database(cfg.storage.db_path), source_id_for_data_cfg(cfg.data))`。
**缓存开关沿用 `cfg.data.cache_dir` 是否设置**(向后兼容现有 YAML,不破坏 example.yaml),但数据落到 `cfg.storage.db_path` 指向的统一库。

## 7. 交易日历 `calendar/ashare.py`

- `AShareCalendar.__init__` 增加 `db: Database | None`(替代 `cache_path` 的 Parquet 角色)。
- `_load`:`db` 存在且 `trade_calendar` 非空 → `SELECT dt` 读集合;否则 akshare 拉取 → 写 `trade_calendar` → 返回。
- 显式传 `trading_days`(测试用)路径不变。
- `runtime.build_calendar` 传入共享 `Database`。`CalendarConfig.cache_path` 保留字段仅供迁移导入参考(运行时不再用)。

## 8. 回测任务持久化 `api/job_store.py`

### 8.1 持久化语义(已确认)

- `Job` 的 `cancel_event` / `_lock` / `version` 仍为内存运行态,不入库。
- **写库时机:仅 create + 终态**(COMPLETED/FAILED/CANCELLED)。高频进度更新(每 ~50 bar)只改内存,不落库。
- 实现:`Job.update(**fields)` 应用后,若 `status` 进入终态且设置了 `_persist` 回调,则触发回调写整行。`JobStore.create` 时注入该回调。

### 8.2 启动恢复

- `JobStore(db)` 初始化:`init_schema` → 读全部 jobs 行 hydrate 成 `Job` 对象进 `_jobs`。
- 任一 hydrate 的 job 若为非终态(PENDING/RUNNING)——说明是上次进程残留(worker 已随进程死亡)——标记为 `FAILED`,`error="interrupted by restart"`,并回写库。
- `get`/`list` 读内存;`create` 插入行(status=PENDING, created_at);`delete` 删内存 + `DELETE FROM jobs`。

### 8.3 依赖装配

- `api/deps.py`:新增 `get_database()`(返回 `get_database()` 单例);`get_job_store()` 改为持有该 `Database` 的单例 `JobStore`。
- 测试:`app.dependency_overrides` 注入用 `Database(":memory:")` 或 tmp 文件构造的 `JobStore`/`get_database`。

## 9. 迁移脚本 `scripts/migrate_cache.py`

一次性运维脚本(**非功能 CLI**;`uv run python scripts/migrate_cache.py ...`)。定位为 ops 脚本,与「功能走 Web」方向不冲突。

- 参数(argparse):`--cache-dir`(默认 `./data/cache`)、`--db`(默认走 `storage.db_path`/env)、`--calendar`(可选 parquet 路径)。
- 行情:遍历 `cache-dir` 下匹配 `{symbol}_{freq}__{source_id}.parquet` 的文件 → `read_parquet` → upsert 到 `bars`。
- **旧命名 `{symbol}_{freq}.parquet`(无 `__source_id`):跳过并计数警告**(现有代码本就读不到,属孤儿数据)。
- 日历:`--calendar` 给定则 `read_parquet` → 写 `trade_calendar`。
- 结束打印:导入文件数 / 总行数 / 跳过(旧命名)数。
- 迁移逻辑复用 storage 层(`Database` + upsert helper),不重复实现。
- 幂等:`INSERT OR REPLACE`,可重复跑。

## 10. 配置变更 `config.py`

```python
class StorageConfig(BaseModel):
    db_path: str = "./data/alphaagent.db"

class AppConfig(BaseModel):
    ...
    storage: StorageConfig = StorageConfig()
```

`_coerce_empty_sections` 的空段列表加入 `"storage"`。`DataConfig.cache_dir` 语义不变(作为行情缓存开关)。

## 11. 清理与测试

### 清理(注意跨阶段顺序)
- Phase 1 **不删** `alphaagent/data/cache.py`:`cli.py` 仍依赖它(`cli.py` 在 Phase 3 才整体删除)。Phase 1 只让 `runtime.build_data_source` 与 API 改用 `SqliteBarCache`,Parquet 后端暂时与 SQLite 并存。
- `alphaagent/data/cache.py` + `tests/test_cache.py` 随 `cli.py` 在 **Phase 3** 一并删除。
- `calendar/ashare.py` 的 Parquet 读写在 Phase 1 即替换为 DB(`build_calendar` 走 runtime,不受 cli 影响);旧 `cache_path` 参数保留兼容,运行时不再用。

### 测试
- `tests/test_sqlite_cache.py`(替换 `test_cache.py`):沿用「切片不重拉」「按需扩展(头+尾两次 fetch)」两个断言,用 tmp 文件 `Database`;新增 upsert 去重断言。
- `tests/test_storage_db.py`:schema 幂等、WAL pragma 生效、写锁下并发写基本验证。
- `tests/test_job_store.py`:create→终态落库→新建 `JobStore` 同库恢复→非终态标记 interrupted→delete 删行。
- `tests/test_calendar.py`:扩展 DB 路径分支(读表 / 写表)。
- `tests/test_migrate_cache.py`:tmp 写若干 parquet → 迁移 → 断言 `bars` 行数;旧命名文件被跳过计数。
- 回归:`test_backtest_e2e.py` / `test_backtest_calendar.py` 若依赖 cache/parquet 路径需相应更新。

### 依赖与文档
- 无新增运行时依赖。`pyarrow`(parquet)仍由 `data` extra 提供,迁移命令与历史测试需要。
- README 更新:「缓存机制」(Parquet→SQLite)、新增 `migrate-cache` 用法与 `storage.db_path` / `ALPHAAGENT_DB` 配置说明。

## 12. 并发与一致性说明

- 单用户本地场景:一个进程、一个连接、WAL + 写锁,足够。
- 回测 worker 线程同时写 `bars`(缓存)与 `jobs`(终态)——共用连接的写锁串行化,WAL 保证 WS 轮询线程的读不被阻塞。
- WS 监听仍轮询内存中的 `job.version`(不变),不读库,延迟无回退。

## 13. 验收标准(Phase 1)

1. `pytest -q` 全绿;`ruff check alphaagent tests` 无新增告警。
2. `alphaagent-api` 回测落库,重启后 `GET /api/backtests` 仍能看到历史任务与结果;上次未跑完的任务显示为 `interrupted by restart`。
3. `uv run python scripts/migrate_cache.py` 把现有 601 个 Parquet 导入 `bars`,旧命名文件被跳过并报数;迁移后回测命中 SQLite 缓存、不再联网拉历史。
4. `runtime.build_data_source` / API K 线 / `build_calendar` 均经 SQLite,不再读写 Parquet(Parquet 后端代码暂留,待 Phase 3 随 cli.py 清理)。

## 14. Web-only 迁移路线图(三阶段)

整体方向:**功能全部走 Web,移除 CLI 命令模式**。按依赖顺序分三阶段,每阶段独立可验收;各阶段有自己的 spec→plan→实现循环。

| 阶段 | 内容 | 依赖 | 独立验收 |
|---|---|---|---|
| **Phase 1(本 spec)** | SQLite 持久化:jobs/bars/calendar 入库 + `scripts/migrate_cache.py` | 无 | §13 |
| **Phase 2** | screener Web 后端:新增 `api/routers/screener.py`(参考 backtests 的 job 模型)+ schemas,接通 `web/pages/screener`;补 `list-screen-rules` 对应接口 | Phase 1(选股复用 SQLite 行情缓存) | 选股可在 Web 端跑通、出 picks |
| **Phase 3** | 移除 CLI 功能命令:删 `cli.py`(backtest/screen/list-* 子命令)、`alphaagent` entry point、`data/cache.py`(Parquet 后端)、`tests/test_cache.py`;保留 `alphaagent-api` 启动入口与 `main.py` | Phase 2(Web 须先覆盖 screener) | `pytest` 绿;Web 覆盖全部原 CLI 功能;无对 cli.py/Parquet 的残留引用 |

说明:
- `cli.py` 当前自带一套重复的 `_build_*`(早于 `runtime.py` 的集中化)。Phase 1 不动 cli.py;它在 Phase 3 整体删除,故 Parquet 后端 (`data/cache.py`) 的删除也推迟到 Phase 3,避免中途破坏 cli.py 导入。
- `alphaagent-api`(server 启动)与 `main.py`(`uv run python main.py`)**不属于**「CLI 命令模式」,保留。
- Phase 2、Phase 3 各自再走一次设计→计划→实现;本 spec 仅锁定 Phase 1 细节与整体顺序。
