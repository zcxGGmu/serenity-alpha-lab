# CandidateBatch 候选契约记录

> 任务：`SAL-P3-004` 定义 CandidateBatch 契约<br>
> 日期：2026-07-23<br>
> 上游基线：DSA `v3.26.1 @ e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`<br>
> Gate 入口：G2 已通过；G3 未通过<br>
> 结论：`APPROVED FOR SAL-P3-005 FACTORDEFINITION VERSION MODEL`

## 1. 交付结论

`SAL-P3-004` 已冻结平台侧 `Candidate` / `CandidateBatch` 标准契约。该契约位于 `application` 层，作为 `ScreeningProvider` raw candidates 之后、后续 ScreenDefinition / FactorDefinition 之前的稳定中间格式。

本任务只标准化候选、层级分数、原因、来源、rank 和可序列化记录；不执行筛选流水线、不计算因子、不调用 AlphaSift 真实运行时、不调用真实 Provider/LLM，也不启动 Quant Core、正式回测或 Evidence Agent。

## 2. 契约对象

新增模块：

```text
src/serenity_alpha_lab/application/candidate_batch.py
```

核心对象：

- `CandidateBatch`：批次级元数据，包含 `batch_id`、provider、strategy、market、具体 Dataset Version、source snapshot time、discovered time、candidate list、source lineage、trace/run/stage 和 LLM overlay 标记。
- `Candidate`：标准候选，包含 canonical `InstrumentId`、`rank`、`final_score`、L1/L2/L3 score records、reason codes、source ids、可选名称和冻结 raw payload。
- `CandidateLayerScore`：标准化层级分数，分层为 `l1_provider`、`l2_deterministic` 和 `l3_llm_overlay`，分数统一为 `0..100`，保留 raw score、weight、source id 和 reason codes。
- `CandidateReason`：稳定 reason code，记录所属层级、方向、权重、source ids 和冻结 details。
- `CandidateSource`：候选来源，支持 `screening_provider`、`dataset`、`rule`、`llm_overlay` 和 `raw_payload`，Dataset 来源必须引用具体 `dsv_*` Dataset Version。
- `candidate_batch_from_screening_result()`：从 `ScreeningResult` 搬运 provider/strategy/dataset/count/timing/trace metadata，只接受已经标准化的 `Candidate`，不解析 raw provider candidates。

## 3. 关键校验

- `CandidateBatch.dataset_versions` 与 `CandidateSource.dataset_version` 必须通过 `DatasetVersionRef.version()` 校验；`latest` alias 被拒绝。
- `source_snapshot_at` 和 `discovered_at` 必须为 timezone-aware datetime，且 `discovered_at >= source_snapshot_at`。
- 如果同时存在 `requested_at` 与 `received_at`，则 `received_at >= requested_at`。
- Candidate ranks 必须为正整数、唯一且按升序排列。
- 每个 Candidate 必须包含 `L1_PROVIDER` 与 `L2_DETERMINISTIC` 分数。
- `L3_LLM_OVERLAY` 只允许在 `llm_overlay_enabled=True` 的批次中出现；它独立记录，不覆盖 L1/L2 确定性分数。
- Score 必须为有限数且标准化到 `0..100`；weight 必须为有限非负数。
- 当批次提供 `sources` 时，Candidate 的 `source_ids` 必须能在批次来源表中找到。

## 4. 序列化口径

`CandidateBatch.to_record()` 返回 JSON-friendly dict，用于后续 ScreenSnapshot、Artifact、API 和 golden tests：

- datetime 均使用 ISO 8601。
- `InstrumentId` 输出 canonical id、market、exchange 和 asset type。
- score records 以 layer value 作为 key，例如 `l2_deterministic`。
- nested metadata、details 和 raw payload 在对象内冻结，在序列化时转换为普通 dict/list。
- `candidate_count` 从候选 tuple 派生，不接受外部硬编码。

## 5. 与 ScreeningProvider 的关系

`ScreeningProvider` 仍返回 raw provider candidates；`CandidateBatch` 不修改 `AlphaSiftScreeningAdapter`，不把 AlphaSift 内部类型暴露给 Application/Domain。

桥接函数只复制 `ScreeningResult` 的稳定字段：

- provider id/version 与 provider run id
- strategy id/version 与 market
- concrete dataset versions
- snapshot / after-filter counts
- requested/received/discovered 时间
- warnings/source errors
- trace id、platform run id、stage id
- LLM overlay enabled/coverage

raw candidates 到标准 Candidate 的具体映射策略留给后续 ScreenDefinition / pipeline 任务，不在本任务中实现。

## 6. 明确未做事项

- 未实现 `FactorDefinition`、因子 DSL、因子计算 DAG、基础因子或 Factor Evaluation。
- 未实现 Historical Universe、ScreenDefinition、L0~L4 pipeline、ScreenSnapshot、Quant Screening API 或 Screen Lab。
- 未启动 Quant Core。
- 未启动正式回测。
- 未启动 Evidence Agent。
- 未调用真实 Provider。
- 未调用真实 LLM。
- 未实现 Worker execution loop，未接入 Celery/Redis 实际执行。
- 未迁移 DSA runtime source，未移动 `upstream/dsa-v3.26.1` tag。

## 7. 本地验证

| 验证 | 结果 |
|---|---|
| `uv run --extra core --extra dev python -m pytest tests/application/test_candidate_batch_contract.py -q` | Red：`1 error`，缺少 `serenity_alpha_lab.application.candidate_batch`；Green：`3 passed` |
| `uv run --extra core --extra dev python -m pytest tests/application/test_candidate_batch_contract.py tests/application/test_screening_provider_contract.py tests/integrations/test_alphasift_screening_adapter.py tests/architecture/test_architecture_boundaries.py -q` | PASS：`25 passed` |
| `uv run --extra core --extra dev python -m pytest -q` | PASS：`255 passed, 3 skipped` |
| `uv run --extra core --extra dev python -m compileall src tests` | PASS |
| `scripts/verify-python-dependency-lock.sh` | PASS：`Resolved 298 packages` |
| `git diff --check` | PASS |
| `git rev-parse upstream/dsa-v3.26.1` | `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a` |

最终测试结果将同步记录在 `AEV-053`。
