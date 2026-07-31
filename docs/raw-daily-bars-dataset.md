# Raw Daily Bars Dataset 记录

> 任务：`SAL-P2-007` 实现原始日线 Dataset<br>
> 日期：2026-07-21<br>
> Gate：G2 未通过，本任务仅完成未复权 OHLCV/amount 原始日线 Dataset<br>
> 代码：`src/serenity_alpha_lab/datasets/raw_daily_bars.py`<br>
> 测试：`tests/datasets/test_raw_daily_bars.py`

## 1. 范围

本任务新增原始日线 Dataset，覆盖：

- 数据口径：仅保存未复权 `open`、`high`、`low`、`close`、`volume`、`amount` 日线，不生成前复权、后复权或公司行动数据。
- 主键：内部主键为 `instrument_id.canonical + trade_date + provider_id`，避免跨市场裸 symbol 或跨 Provider 数据碰撞。
- 分区口径：冻结逻辑分区键为 `market`、`year`、`month`，用于后续 Parquet/Dataset Catalog 任务对齐；本任务只发布 deterministic JSON artifact。
- Provider 输入：仅消费注入式/离线 `DataBatch` daily-bar records，不构造真实 Provider，不联网。
- 证券校验：每条记录必须能在 `InstrumentMasterDataset` 中按 `trade_date` 查到有效证券。
- 交易日校验：每条记录的 `trade_date` 必须在 `TradingCalendarDataset` 中是交易日。
- 来源链路：记录 Provider id/source、Provider source timestamp、raw response SHA-256、field lineage 和 Bronze source artifact id。
- 查询能力：支持按单条主键、证券日期区间、市场交易日和 Provider 日期区间查询。
- 增量合并：`merge_incremental()` 以主键替换同一 Provider 的同日记录，并返回新的不可变 Dataset。
- Artifact 发布：复用 P1 `ArtifactStore`，输出 deterministic JSON Artifact，携带 schema、record_count、Bronze lineage、trace/run/stage 和 manifest-last 发布语义。
- 错误边界：Dataset 校验错误继承 `ValueError`，在既有 `ProblemDetails` 边界映射为稳定 `validation_error`。

## 2. Schema

新增常量：

- `RAW_DAILY_BARS_SCHEMA_NAME = "dataset.bars_1d_raw"`
- `RAW_DAILY_BARS_SCHEMA_VERSION = "1.0.0"`
- `RAW_DAILY_BARS_CONTENT_TYPE = "application/vnd.serenity.dataset.raw-daily-bars+json"`
- `RAW_DAILY_BARS_PARTITION_KEYS = ("market", "year", "month")`
- `RAW_DAILY_BARS_FIELD_SCHEMA`：冻结 Arrow-compatible 字段名与类型字符串，但不建立 Arrow Schema Registry。

核心记录：

- `RawDailyBar`：一个证券在一个交易日、一个 Provider 下的未复权 OHLCV/amount 记录。
- `RawDailyBarsDataset`：不可变记录集合、离线索引、Provider batch 转换、查询 API、增量合并和 Artifact 发布入口。

## 3. 校验规则

- Dataset 不能为空。
- `(instrument_id.canonical, trade_date, provider_id)` 必须唯一。
- `created_at` 必须是 timezone-aware datetime。
- `instrument_id` 必须是 canonical `InstrumentId`，或可解析为 `InstrumentId`。
- `trade_date` 必须是 date，Provider 行可使用 `trade_date` 或 legacy `date` 字段。
- OHLC 必须有限、非负，并满足 `low <= open/close <= high`。
- `volume` 与 `amount` 必须有限且非负。
- `adjustment` 必须为 `unadjusted`。
- Provider `source_timestamp` 如果存在，必须是 timezone-aware datetime。
- Provider raw response hash 必须是合法 SHA-256。
- 每条记录必须携带 `source_bronze_artifact_id`，保持从 Bronze 原始响应到 Dataset 的审计链路。
- 发布时必须提供 `produced_by_run_id` 或 Dataset 自带 `run_id`。

## 4. 验证

本任务使用 TDD：

- Red：`uv run --extra core --extra dev python -m pytest tests/datasets/test_raw_daily_bars.py -q` 先以缺少 `serenity_alpha_lab.datasets.raw_daily_bars` 失败。
- Green target：`uv run --extra core --extra dev python -m pytest tests/datasets/test_raw_daily_bars.py -q`，`3 passed`。
- Related suite：`uv run --extra core --extra dev python -m pytest tests/datasets tests/domain/test_provider_contract.py tests/repositories/test_bronze_raw_store.py tests/application/test_api_errors.py tests/application/test_trace_context.py tests/architecture/test_architecture_boundaries.py -q`，`59 passed`。
- Full suite：`uv run --extra core --extra dev python -m pytest -q`，`172 passed`。
- Compile：`uv run --extra core --extra dev python -m compileall -q src/serenity_alpha_lab tests` 通过。

最终提交前验证命令和结果记录在 `tasks/todo.md` 的 `SAL-P2-007` review 与任务清单证据登记中。

## 5. 范围限制

本任务明确未实现：

- 公司行动、复权因子或 adjusted bars。
- PIT 基本面 Dataset、fallback policy、Provider 质量门禁、Dataset Catalog/latest alias、Arrow Schema Registry、PersistentTaskBackend、Worker runtime、Quant Core、正式回测、Evidence Agent。
- 真实 Provider/LLM 调用、联网探针或 DSA runtime source 迁移。

Gate G2 仍未通过。
