# Gate G2 数据与任务评审

> 任务：`SAL-P2-020` Gate G2：数据与任务评审<br>
> 评审日期：2026-07-23<br>
> Phase：P2 数据与持久任务<br>
> 上游基线：`ZhuLinsen/daily_stock_analysis v3.26.1 @ e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`<br>
> 评审结论：`GO with accepted risks`

## 1. Gate 结论

Gate G2 通过。P2 数据与持久任务完成度为 `20/20`，项目总完成度推进到 `49/129`，允许进入 P3 AlphaSift、因子与股票筛选开发。

本结论只批准开始 `SAL-P3-001` AlphaSift 版本、许可证和依赖审查及后续筛选/factor 契约工作，不批准以下事项：

- 不启动 Quant Core、正式组合回测、Portfolio Ledger 或硬风控。
- 不启动 Evidence Agent、引用验证、报告 Agent 运行或真实 LLM 调用。
- 不把真实 Provider 调用接入普通测试路径；真实调用仍只能在后续 Worker/调度任务中通过 profile guard、离线契约和 fallback trace 接入。
- 不把 Celery/Redis queue 状态作为任务权威；数据库 task/run events 仍是恢复与审计来源。
- 不移动 `upstream/dsa-v3.26.1`，不做未经批准的大规模 DSA runtime source 迁移。

## 2. 通过条件核对

| Gate 条件 | 结论 | 证据 |
|---|---|---|
| 可发布一个版本化 A 股 Dataset，记录可追溯 | PASS | `tests/gates/test_gate_g2_data_task_review.py` 证明 AKShare 离线 `DataBatch` 经 Provider Policy 选择后发布为 `dataset.bars_1d_raw@1.0.0` 不可变 Dataset Version，包含 Artifact SHA-256、schema hash、quality metadata、trace/run/stage 和 provider fallback trace hash |
| Provider 异常和冲突阻断有效 | PASS | Provider fixture 覆盖 timeout/empty/schema drift；Gate G2 测试验证跨源 close 差异超阈值返回 `quarantined` 且 `selected_batch=None`，不静默平均或推进成功 |
| API/Worker 重启恢复语义通过 | PASS | `PersistentTaskBackend` 使用 SQLite/SQLAlchemy 持久化任务状态；Gate G2 测试重建 backend 后可恢复 queued task、通过 `TaskEventStreamService` 补发 `Last-Event-ID` 后事件，并验证 idempotency replay |
| DSA 单股分析兼容路径通过 | PASS | Gate G2 测试使用 CI profile + injected offline DSA-like manager，验证 `DsaStockHistoryCompatibilityFacade` 通过 Provider contract path 返回 `600519` 日线，不构造真实 DSA Provider manager |
| Dataset 版本、质量和发布边界可用 | PASS | [Dataset Catalog 与 Manifest 记录](./dataset-catalog-manifest.md)、[Data Quality Rule Engine 记录](./data-quality-rule-engine.md)、[Dataset 隔离区与原子发布记录](./dataset-atomic-publication.md) |
| Provider Contract、fallback 和 Data Sync 边界可用 | PASS | [Provider 契约 Fixture 记录](./provider-contract-fixtures.md)、[Provider Policy 与 Fallback Trace 记录](./provider-policy-fallback-trace.md)、[增量同步与交易日调度记录](./data-sync-scheduler.md) |
| PostgreSQL standalone Profile 与任务持久化基础可用 | PASS | [PostgreSQL Standalone Profile 记录](./postgresql-standalone-profile.md)、[PersistentTaskBackend 记录](./persistent-task-backend.md)、[可恢复任务事件流记录](./recoverable-task-event-stream.md) |
| P1 工程边界仍被遵守 | PASS | ProblemDetails、TraceContext、ArtifactStore、Run/Stage/Event、Runtime Profile、Alembic 和 architecture boundary tests 继续通过；未启动真实 Provider/LLM、Quant Core、正式回测或 Evidence Agent |

## 3. P2 交付核对

| 任务 | 结论 | 核心证据 |
|---|---|---|
| `SAL-P2-001` | DONE | Provider Protocol、Capability、DataBatch、Provenance、warning 和错误分类 |
| `SAL-P2-002` | DONE | DSA Provider Compatibility Adapter 与 feature-flag stock-history facade |
| `SAL-P2-003` | DONE | DSA symbol compatibility mapper 与 Provider symbol mapping |
| `SAL-P2-004` | DONE | Bronze raw response store、deterministic gzip Artifact 和脱敏 |
| `SAL-P2-005` | DONE | Instrument Master Dataset、as-of 状态和 provider mapping 有效期 |
| `SAL-P2-006` | DONE | Trading Calendar Dataset、市场时区和交易 session 口径 |
| `SAL-P2-007` | DONE | Raw Daily Bars Dataset、OHLCV/amount 和 Provider lineage |
| `SAL-P2-008` | DONE | Corporate Actions、前/后复权因子和 raw price immutability |
| `SAL-P2-009` | DONE | PIT Fundamentals Dataset、`available_at <= decision_time` 和 unknown temporal gate |
| `SAL-P2-010` | DONE | Arrow Schema Registry、schema hash 和兼容规则 |
| `SAL-P2-011` | DONE | Dataset Catalog、不可变 Manifest、file hash、lineage 和 latest alias |
| `SAL-P2-012` | DONE | Data Quality Rule Engine、warning/quarantine/blocking 报告 |
| `SAL-P2-013` | DONE | Quality-gated publication、old-latest retention 和 tmp cleanup |
| `SAL-P2-014` | DONE | AKShare/efinance/Tushare/BaoStock/YFinance offline Provider fixtures |
| `SAL-P2-015` | DONE | Provider Policy、fallback trace、quality rejection 和 cross-source quarantine |
| `SAL-P2-016` | DONE | Incremental sync planning、checkpoint、lookback、lock 和 backfill |
| `SAL-P2-017` | DONE | PostgreSQL standalone Profile、connection pool 和 Repository Contract |
| `SAL-P2-018` | DONE | PersistentTaskBackend、queue routing、lease/heartbeat/requeue primitives |
| `SAL-P2-019` | DONE | Recoverable task/run event stream、SSE replay、orphan/stalled reconciliation |
| `SAL-P2-020` | DONE | 本 Gate G2 评审记录和 P3 入口约束 |

## 4. 接受风险与后续约束

| 风险/限制 | Gate G2 处理 | 后续关闭条件 |
|---|---|---|
| `RSK-002` PIT 数据时间不可信 | 接受但限制正式实验。P2 已建立 `available_at <= decision_time`、revision 和 unknown temporal confidence hard gate；真实商业/完整公告时间源仍未接入 | P4 正式回测前必须使用可信 PIT Dataset version；unknown temporal confidence 不得进入 formal backtest |
| `RSK-004` 免费 Provider 不稳定 | 接受但限制真实调用。P2 已建立 offline fixture、fallback trace、quality rejection、cross-source quarantine 和 sync retry/checkpoint 语义；真实 Provider SLA/探针未完成 | 后续 Worker/调度任务通过 profile guard 接入真实调用，并在发布门禁前完成 live probe/SLA/降级 Runbook |
| 完整 Worker execution loop 尚未实现 | 不阻断 P3。P2 只批准数据库权威 task state、queue routing 和 lease primitives | `SAL-P4-018`、`SAL-P5-007` 或对应 Worker 任务完成执行 loop、handler sandbox 和生产恢复演练 |
| PostgreSQL live contract 默认跳过 | 接受。SQLite contract 和 optional PostgreSQL contract 共用同一 suite；无 `SERENITY_TEST_POSTGRES_URL` 时 live PostgreSQL 测试跳过 | standalone/service 环境提供真实 PostgreSQL URL 后运行同一 Repository Contract suite |
| Web/Docker/SBOM 发布风险仍存在 | 延续 G0/G1 accepted risks，不阻断 P3 研发 | `SAL-P6-005` 发布安全门禁修复或正式豁免 |

## 5. 本地评审验证

| 验证 | 结果 |
|---|---|
| `uv run --extra core --extra dev python -m pytest tests/gates/test_gate_g2_data_task_review.py -q` | PASS：`3 passed` |
| `uv run --extra core --extra dev python -m pytest tests/gates/test_gate_g2_data_task_review.py tests/datasets/test_dataset_catalog.py tests/datasets/test_data_quality.py tests/datasets/test_dataset_publication.py tests/integrations/test_provider_contract_fixtures.py tests/integrations/test_provider_policy.py tests/integrations/test_dsa_provider_adapter.py tests/services/test_data_sync.py tests/repositories/test_database_profile.py tests/repositories/test_repository_contract.py tests/repositories/test_persistent_task_backend.py tests/services/test_task_event_stream.py tests/application/test_api_errors.py tests/application/test_trace_context.py tests/architecture/test_architecture_boundaries.py -q` | PASS：`80 passed, 3 skipped` |
| `uv run --extra core --extra dev python -m pytest -q` | PASS：`236 passed, 3 skipped` |
| `uv run --extra core --extra dev python -m compileall src tests` | PASS |
| `scripts/verify-python-dependency-lock.sh` | PASS：`uv.lock` 与 `requirements.txt` 无 drift |
| `git diff --check` | PASS |
| `git rev-parse upstream/dsa-v3.26.1` | `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a` |

## 6. P3 入口约束

P3 第一入口为 `SAL-P3-001` 审查并锁定 AlphaSift。P3 实现必须沿用 P2 已冻结的数据和任务边界：

- AlphaSift 只能作为候选发现/快照筛选插件接入，不得替代 Dataset Catalog、PIT Dataset、Provider Policy 或正式组合回测。
- 筛选与因子计算必须引用具体 Dataset Version；`latest` 只能用于 discovery/research display。
- P3 不得绕过 Provider Policy/fallback trace 直接读取真实 Provider 或 DSA manager。
- P3 不得启动 Qlib Adapter、Portfolio Backtest、Risk、Evidence Agent 或报告 Agent；这些属于后续 Phase/Gate。
- 所有新增筛选/因子任务必须继续使用 ProblemDetails、TraceContext、ArtifactStore、Run/Stage/Event 和 Runtime Profile guard。

## 7. 最终判定

`SAL-P2-020` 判定为 `DONE`。Gate G2 通过后，P2 数据与持久任务完成度为 `20/20`，项目进入 P3 AlphaSift、因子与股票筛选阶段。下一步唯一推荐入口是 `SAL-P3-001`，先完成 AlphaSift 源码 commit、Apache-2.0 归因、依赖清单、漏洞和维护风险审查。
