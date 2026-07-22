# PIT Fundamental Dataset 记录

> 任务：`SAL-P2-009` 实现 PIT 基本面 Dataset<br>
> 日期：2026-07-22<br>
> Gate：G2 未通过，本任务仅完成离线 PIT 基本面 Dataset<br>
> 代码：`src/serenity_alpha_lab/datasets/fundamentals.py`<br>
> 测试：`tests/datasets/test_fundamentals_dataset.py`

## 1. 范围

本任务新增 PIT 基本面 Dataset，覆盖：

- 时点口径：每条 `FundamentalRecord` 显式区分 `period_end`、`announced_at`、`available_at`、`ingested_at` 和 `revision`，防止用当前最新财务数据覆盖历史决策时点。
- 主键：内部主键为 `instrument_id.canonical + period_end + item + revision + provider_id`，避免跨市场裸 symbol 或跨 Provider 修订碰撞。
- 分区口径：冻结逻辑分区键为 `market`、`period_year`，用于后续 Parquet/Dataset Catalog 任务对齐；本任务只发布 deterministic JSON Artifact。
- Provider 输入：仅消费注入式/离线 `DataBatch` fundamentals records，不构造真实 Provider，不联网。
- 证券校验：每条记录必须能在 `InstrumentMasterDataset` 中按 `period_end` 查到有效证券。
- 来源链路：记录 Provider id/source、Provider source timestamp、raw response SHA-256、field lineage 和 Bronze source artifact id。
- PIT 查询：`latest_as_of()`、`history_for_item()` 和 `records_for_instrument()` 均以 `available_at <= decision_time` 作为硬过滤条件。
- 修订选择：`latest_as_of()` 在可用记录中按 `period_end`、`available_at`、`revision` 选择最新可用记录，晚于决策时间的修订不会泄漏到早期查询。
- 可信度等级：旧 DSA `FundamentalSnapshot` 类记录若无法证明公告时间，必须标记为 `temporal_confidence=unknown`；该记录可用于当前研究展示，但正式回测查询会拒绝。
- 增量合并：`merge_incremental()` 以 PIT 主键替换记录，并返回新的不可变 Dataset。
- Artifact 发布：复用 P1 `ArtifactStore`，输出 deterministic JSON Artifact，携带 schema、record_count、Bronze lineage、trace/run/stage 和 manifest-last 发布语义。
- 错误边界：Dataset 校验错误继承 `ValueError`，在既有 `ProblemDetails` 边界映射为稳定 `validation_error`。

## 2. PIT 查询口径

正式历史决策查询必须满足：

```text
record.available_at <= decision_time
record.temporal_confidence != unknown
record.announced_at is not None
```

查询行为：

- `latest_as_of(instrument_id, item, decision_time, ...)` 先按证券、指标、Provider、period type 和 `available_at <= decision_time` 过滤，再选择最新 `period_end`、`available_at` 和 `revision`。
- `history_for_item(...)` 返回指定 period 范围内、截至 `decision_time` 已可用的全部修订记录。
- `records_for_instrument(...)` 用于研究展示和审计检查，默认允许 unknown confidence；若显式传入 `FORMAL_BACKTEST`，同样执行 unknown confidence gate。

本任务只定义 Dataset 查询语义，不建立正式回测引擎、因子计算或 Dataset Catalog/latest alias。

## 3. Schema

新增常量：

- `FUNDAMENTALS_SCHEMA_NAME = "dataset.fundamentals"`
- `FUNDAMENTALS_SCHEMA_VERSION = "1.0.0"`
- `FUNDAMENTALS_CONTENT_TYPE = "application/vnd.serenity.dataset.fundamentals+json"`
- `FUNDAMENTALS_PARTITION_KEYS = ("market", "period_year")`
- `FUNDAMENTALS_FIELD_SCHEMA`：冻结 Arrow-compatible 字段名与类型字符串，但不建立 Arrow Schema Registry。

核心类型：

- `FundamentalPeriodType`：`annual`、`quarterly`、`ttm`、`snapshot`。
- `TemporalConfidence`：`exact`、`estimated`、`unknown`。
- `FundamentalQueryPurpose`：`formal_backtest`、`research_display`。
- `FundamentalRecord`：一个证券、一个 period、一个指标、一个 revision 和一个 Provider 下的 PIT 基本面记录。
- `FundamentalsDataset`：不可变记录集合、Provider batch 转换、离线索引、PIT 查询 API、增量合并和 Artifact 发布入口。

## 4. 校验规则

- `(instrument_id.canonical, period_end, item, revision, provider_id)` 必须唯一。
- `created_at`、`available_at`、`ingested_at`、Provider source timestamp 必须是 timezone-aware datetime。
- `temporal_confidence != unknown` 时必须提供 `announced_at`，且 `announced_at <= available_at <= ingested_at`。
- `temporal_confidence=unknown` 时必须省略 `announced_at`，且正式回测查询拒绝使用。
- `value` 必须是有限数值；`revision` 必须为正整数；`fiscal_quarter` 若存在必须在 1 至 4。
- Provider raw response hash 必须是合法 SHA-256。
- 每条记录必须携带 `source_bronze_artifact_id`，保持从 Bronze 原始响应到 Dataset 的审计链路。
- 发布时必须提供 `produced_by_run_id` 或 Dataset 自带 `run_id`。

## 5. 验证

本任务使用 TDD：

- Red：`uv run --extra core --extra dev python -m pytest tests/datasets/test_fundamentals_dataset.py -q` 先以缺少 `serenity_alpha_lab.datasets.fundamentals` 失败。
- Green target：`uv run --extra core --extra dev python -m pytest tests/datasets/test_fundamentals_dataset.py -q`，`4 passed`。
- Related suite：`uv run --extra core --extra dev python -m pytest tests/datasets tests/domain/test_provider_contract.py tests/architecture/test_architecture_boundaries.py -q`，`51 passed`。
- Full suite：`uv run --extra core --extra dev python -m pytest -q`，`179 passed`。
- Compile：`uv run --extra core --extra dev python -m compileall -q src/serenity_alpha_lab/datasets/fundamentals.py tests/datasets/test_fundamentals_dataset.py` 通过。

最终提交前还会复跑全量验证、依赖锁、diff whitespace 和 immutable tag 检查，结果记录在 `tasks/todo.md` 的 `SAL-P2-009` review 与任务清单证据登记中。

## 6. 范围限制

本任务明确未实现：

- fallback policy、Provider 质量门禁、Dataset Catalog/latest alias、Arrow Schema Registry、PersistentTaskBackend、Worker runtime、Quant Core、正式回测、Evidence Agent。
- 从 DSA `fundamental_snapshot` 表做正式历史迁移或可信公告时间补全。
- 真实 Provider/LLM 调用、联网探针或 DSA runtime source 迁移。

Gate G2 仍未通过。
