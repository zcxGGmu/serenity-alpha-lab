# 增量同步与交易日调度记录

> 任务：`SAL-P2-016` 实现增量同步与交易日调度<br>
> 日期：2026-07-23<br>
> Phase：P2 数据与持久任务<br>
> Gate：G2 未通过<br>
> 代码：`src/serenity_alpha_lab/services/data_sync.py`<br>
> 测试：`tests/services/test_data_sync.py`

## 1. 范围

本任务新增离线数据同步编排层，用于在后续 Worker/调度任务接入真实 Provider 前，冻结增量计划、交易日调度、checkpoint、锁和补数语义。

覆盖范围：

- Scope：用 `DataSyncScope` 固定 Dataset、市场和 Catalog alias scope。
- Checkpoint：用 `DataSyncCheckpoint` 记录已完成交易日、最新成功 Dataset version、失败交易日、Provider Policy 状态、fallback trace 和 trace/run/stage 标量。
- Lock：用 `LocalDataSyncStateStore.acquire_lock()` 基于本地文件 `O_EXCL` 创建 scope lock，阻止同一 Dataset/市场并发同步。
- Incremental plan：`DataSyncScheduler.plan_incremental()` 从 checkpoint 和 `TradingCalendarDataset` 计算下一批交易日，支持 lookback window 和非交易日跳过。
- Catalog lineage：当 checkpoint 没有 `last_successful_version_id` 时，可从 `LocalDatasetCatalog` latest alias 解析 previous version，用于后续发布血缘。
- Backfill：`DataBackfillCommand` 支持历史区间补数，默认跳过 checkpoint 已完成交易日，显式 `include_completed=True` 时重放完整交易日区间。
- Run：`DataSyncRun` 复用 P1 `Run/Stage/Event`，在每个交易日结果后记录 checkpoint；`selected` 才推进 checkpoint，`exhausted/quarantined` 只记录失败，等待重试。

## 2. 实现口径

| 类型 / 函数 | 作用 |
|---|---|
| `DataSyncScope` | Dataset + market + alias scope 的同步边界。 |
| `DataSyncCheckpoint` | 本地可序列化 checkpoint，记录完成/失败交易日、最新成功 version、Provider Policy trace 和 trace 标量。 |
| `LocalDataSyncStateStore` | 本地 JSON checkpoint 和 lock store；checkpoint 采用原子替换，lock 采用独占创建。 |
| `DataSyncScheduler.plan_incremental()` | 按交易日历、checkpoint 和 lookback window 生成增量计划，并记录被跳过的非交易日。 |
| `DataSyncScheduler.plan_backfill()` | 根据补数命令生成历史交易日计划，默认只补缺口。 |
| `DataSyncTradeDateResult` | 单个交易日的 Provider Policy 选择结果和成功发布的 Dataset version。 |
| `DataSyncRun` | 复用 `Run/Stage/Event` 表达同步运行，记录交易日结果并释放 lock。 |

## 3. 调度语义

- `lookback_window=1` 表示从 checkpoint 的最后成功交易日开始重算，再补齐之后的交易日。
- `lookback_window=0` 表示只同步 checkpoint 之后的下一个交易日，不重算最后成功日。
- `as_of` 是自然日；若 `as_of` 非交易日，则计划只推进到 `as_of` 之前最近的交易日，并把非交易日写入 `skipped_non_trading_dates`。
- 无 checkpoint 时，增量计划只选择 `as_of` 对应的最近交易日；大范围历史初始化应使用 backfill command。
- backfill 默认排除 checkpoint 已完成交易日，避免重复补数；显式 `include_completed=True` 可用于质量回看或修复重放。
- 成功交易日由 `ProviderPolicyStatus.SELECTED` 且提供具体 `dataset_version_id` 定义；`EXHAUSTED` 和 `QUARANTINED` 不会推进 `last_completed_trade_date`。
- 重复记录同一成功交易日只保留一个 completed date，避免至少一次投递造成重复 checkpoint。

## 4. 安全与边界

- 本层不导入 AKShare、efinance、Tushare、BaoStock、YFinance SDK。
- 本层不调用 DSA `DataFetcherManager`，不访问网络，不执行真实 Provider/LLM 调用。
- 本层不发布真实 Dataset，不写 Bronze，不执行质量门禁，不启动 Worker runtime 或 PersistentTaskBackend。
- 本层不启动 Quant Core、正式回测、Evidence Agent、定时探针或大规模 DSA runtime source migration。
- Catalog latest 只用于恢复 previous lineage；正式实验仍必须使用具体 Dataset version。
- Provider failure、quarantine 或 exhaustion 只记录失败 checkpoint，不伪装成成功。

## 5. 验证证据

| 验证 | 结果 |
|---|---|
| Red：data sync module | `uv run --extra core --extra dev python -m pytest tests/services/test_data_sync.py -q` 先以 `ModuleNotFoundError: No module named 'serenity_alpha_lab.services.data_sync'` 失败。 |
| Green：target | `uv run --extra core --extra dev python -m pytest tests/services/test_data_sync.py -q`，`5 passed`。 |
| Green：related | `uv run --extra core --extra dev python -m pytest tests/services/test_data_sync.py tests/datasets/test_trading_calendar.py tests/datasets/test_dataset_catalog.py tests/integrations/test_provider_policy.py tests/domain/test_run_lifecycle.py tests/architecture/test_architecture_boundaries.py -q`，`35 passed`。 |
| Green：full pytest | `uv run --extra core --extra dev python -m pytest -q`，`214 passed`。 |
| Compile | `uv run --extra core --extra dev python -m compileall -q src/serenity_alpha_lab tests`，PASS。 |
| Dependency lock | `scripts/verify-python-dependency-lock.sh`，PASS。 |
| Diff check | `git diff --check`，PASS。 |
| Immutable upstream tag | `git rev-parse upstream/dsa-v3.26.1`，`e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`。 |

## 6. 后续衔接

`SAL-P2-017` 可以继续建立 PostgreSQL standalone Profile；`SAL-P2-018` 才接入 PersistentTaskBackend 和 Worker lease/heartbeat。真实 Provider 调用仍需后续 Worker/调度任务通过 profile guard、离线契约和 Provider Policy/fallback trace 接入。
