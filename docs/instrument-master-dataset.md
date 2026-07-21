# Instrument Master Dataset 记录

> 任务：`SAL-P2-005` 实现证券主数据 Dataset<br>
> 日期：2026-07-21<br>
> Gate：G2 未通过，本任务仅完成证券主数据 Dataset<br>
> 代码：`src/serenity_alpha_lab/datasets/instrument_master.py`<br>
> 测试：`tests/datasets/test_instrument_master.py`

## 1. 范围

本任务新增历史有效期证券主数据 Dataset，覆盖：

- 证券主键：复用 P1 `InstrumentId`，内部主键为 canonical `<symbol>.<exchange>`，不持久化裸 6 位代码作为跨市场主键。
- 主数据字段：名称、市场、交易所、资产类型、币种、上市/退市日期、上市状态、ST 状态、板块和行业分类。
- Provider 映射：复用 P1 `ProviderSymbolMapping`，并在 Dataset 层增加 `valid_from` / `valid_to` 与 Bronze source artifact lineage。
- 历史查询：支持按任意 `as_of` 日期查询当时有效证券状态和 Provider symbol。
- Artifact 发布：复用 P1 `ArtifactStore`，输出 deterministic JSON Artifact，携带 schema、record_count、Bronze lineage、trace/run/stage 和 manifest-last 发布语义。
- 错误边界：Dataset 校验错误继承 `ValueError`，在既有 `ProblemDetails` 边界映射为稳定 `validation_error`。

## 2. Schema

新增常量：

- `INSTRUMENT_MASTER_SCHEMA_NAME = "dataset.instrument_master"`
- `INSTRUMENT_MASTER_SCHEMA_VERSION = "1.0.0"`
- `INSTRUMENT_MASTER_CONTENT_TYPE = "application/vnd.serenity.dataset.instrument-master+json"`

核心记录：

- `InstrumentMasterRecord`：证券在一个历史有效期内的主数据状态。
- `IndustryClassification`：行业分类体系、版本、层级和有效期。
- `ProviderSymbolValidity`：Provider symbol 映射、有效期和 Bronze lineage。
- `InstrumentMasterDataset`：不可变记录集合、as-of 查询和 Artifact 发布入口。

有效期采用半开区间 `[valid_from, valid_to)`；`valid_to=None` 表示当前仍有效。

## 3. 校验规则

- Dataset 不能为空。
- `(instrument_id.canonical, valid_from)` 必须唯一。
- 同一 `instrument_id` 的主数据有效期不得重叠。
- 同一记录内，同一 Provider 的 symbol 映射有效期不得重叠。
- Provider 映射的 `instrument_id` 必须与主记录一致。
- 每条主记录和 Provider 映射必须携带 `source_bronze_artifact_id`，保持从 Bronze 原始响应到 Dataset 的审计链路。
- `created_at` 必须是 timezone-aware datetime；发布时必须提供 `produced_by_run_id` 或 Dataset 自带 `run_id`。

## 4. 验证

本任务使用 TDD：

- Red：`uv run --extra core --extra dev python -m pytest tests/datasets/test_instrument_master.py -q` 先以缺少 `serenity_alpha_lab.datasets.instrument_master` 失败，`3 failed`。
- Green target：`uv run --extra core --extra dev python -m pytest tests/datasets/test_instrument_master.py -q`，`3 passed`。
- Related suite：`uv run --extra core --extra dev python -m pytest tests/datasets/test_instrument_master.py tests/architecture/test_architecture_boundaries.py -q`，`15 passed`。
- Related contract suite：`uv run --extra core --extra dev python -m pytest tests/domain/test_instrument_id.py tests/domain/test_artifacts.py tests/domain/test_provider_contract.py tests/repositories/test_local_artifact_store.py tests/repositories/test_bronze_raw_store.py tests/application/test_api_errors.py tests/application/test_trace_context.py -q`，`81 passed`。

最终全量验证命令和结果记录在 `tasks/todo.md` 的 `SAL-P2-005` review 与任务清单证据登记中。

## 5. 范围限制

本任务明确未实现：

- 交易日历 `SAL-P2-006`。
- 原始日线 Dataset `SAL-P2-007`。
- PIT 基本面 Dataset、fallback policy、Provider 质量门禁、Dataset Catalog/latest alias、Arrow Schema Registry、PersistentTaskBackend、Worker runtime、Quant Core、正式回测、Evidence Agent。
- 真实 Provider/LLM 调用、联网探针或 DSA runtime source 迁移。

Gate G2 仍未通过。
