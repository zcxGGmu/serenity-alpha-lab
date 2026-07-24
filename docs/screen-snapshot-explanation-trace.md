# ScreenSnapshot 与解释轨迹记录

> 任务：`SAL-P3-013` 实现 ScreenSnapshot 与解释轨迹<br>
> 日期：2026-07-24<br>
> 上游基线：DSA `v3.26.1 @ e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`<br>
> Gate 入口：G2 已通过；G3 未通过<br>
> 结论：`APPROVED FOR SAL-P3-014 QUANT SCREENING API`

## 1. 交付结论

`SAL-P3-013` 已建立平台侧结果快照 `ScreenSnapshot` 和结构化解释轨迹。该层只把 `SAL-P3-012` 的 `ScreenPipelineSnapshot` 投影为结果查询、解释和比较可消费的 deterministic schema，不改变 L0~L4 pipeline 执行逻辑，不启动 Quant Screening API、Screen Lab UI、Worker runtime、Quant Core/Qlib、正式组合回测、Evidence Agent、真实 Provider/LLM 调用或 DSA runtime source migration。

新增模块：

```text
src/serenity_alpha_lab/quant/screening/snapshot.py
```

新增测试：

```text
tests/quant/test_screen_snapshot.py
```

## 2. 契约对象

核心对象：

- `ScreenSnapshot`：冻结 `quant.screen_snapshot@1.0.0` 结果快照，绑定 `ScreenPipelineSnapshot.pipeline_snapshot_id`、`ScreenDefinition.definition_version_id`、`as_of`、具体 Dataset Version、trace/run/stage 和结果行。
- `ScreenSnapshotResult`：每只证券一行，表达 `passed` 或 `failed`、rank、failed stage、final score、分层 scores、factor contributions、reason codes、source rank、industry 和结构化解释步骤。
- `ScreenExplanationStep`：权威解释单元，包含 stage、rule id、reason、authoritative 标记、scores、factor contributions、source ids 和 details。
- `ScreenSnapshotComparison`：本地 deterministic comparison helper，比较两个 snapshot 的 passed set、状态变化、rank 变化和 score delta。
- `publish_screen_snapshot()`：复用 P1 `ArtifactStore` 发布 deterministic JSON。

## 3. 结果 Schema 语义

`ScreenSnapshot` 的 `screen_snapshot_id` 从完整结果 payload 稳定哈希派生，格式为 `ssn_<32 hex>`。payload 包含：

- `schema_name = quant.screen_snapshot`
- `schema_version = 1.0.0`
- `contract_version = quant.screen_snapshot@1.0.0`
- `pipeline_snapshot_id`
- `definition_version_id`
- `as_of`
- `dataset_versions`
- `trace_id` / `run_id` / `stage_id`
- `passed_count` / `failed_count`
- `results`
- `results_by_instrument`

所有 Dataset Version 必须是具体 `dsv_*`，`latest` 被拒绝。passed 结果的 rank 必须连续；failed 结果必须包含 `failed_stage` 且不能携带 rank；同一 snapshot 内每个 `InstrumentId` 只能出现一次。

## 4. 权威解释轨迹

结构化解释是权威判断来源，人类 summary 只用于展示，不可覆盖结构化字段。

Passed 证券默认包含五个 replayable steps：

| Stage | Rule ID | 语义 |
|---|---|---|
| `l0_universe` | `l0_universe_member` | 通过 L0 Historical Universe 成员和硬过滤 |
| `l1_provider` | `l1_provider_candidate_present` | 出现在 L1 Provider candidate batch |
| `l2_factor` | `l2_factor_values_available` | 具备所有 deterministic factor values |
| `l3_llm_overlay` | `l3_llm_overlay_recorded` | LLM overlay 只在硬过滤后记录，不能重新纳入被排除证券 |
| `l4_final` | `l4_final_passed` | 通过 deterministic final screen gates |

Failed 证券直接继承 pipeline exclusion 的 `failed_stage`、`rule_id`、`reason`、scores 和 factor contributions。例如 L0 排除保留 `l0_universe_member`，L4 行业约束排除保留 `max_per_industry`。这些结构化字段可重放，且比任何展示文本优先。

## 5. 对比查询

`compare_screen_snapshots(previous, current)` 是本地纯函数，不访问数据库/API。当前比较口径：

- `added`：当前 passed set 新增证券。
- `removed`：前一 passed set 中当前不再入选证券。
- `retained`：两个 passed set 的交集。
- `status_changes`：同一证券在两个 snapshot 中 `passed/failed` 状态变化。
- `rank_changes`：retained passed 证券排名变化。
- `score_deltas`：retained passed 证券 final score 差异。

该 helper 为 `SAL-P3-014` API 和 `SAL-P3-015` Screen Lab 准备稳定领域语义，但本任务不实现分页、持久化查询、HTTP API 或 UI。

## 6. Artifact 发布

`publish_screen_snapshot()` 使用：

- schema name：`quant.screen_snapshot`
- schema version：`1.0.0`
- content type：`application/vnd.serenity.quant.screen-snapshot+json`

同一 snapshot 重复发布得到相同 Artifact ID 和 SHA-256。发布 metadata 使用 `run_id/stage_id` 或显式 override；缺少 produced run id 会拒绝发布，沿用 P1 ArtifactStore 规则。

## 7. 明确未做事项

- 未实现 Quant Screening API、OpenAPI、Idempotency-Key、分页或 repository。
- 未实现 Screen Lab UI、结果详情抽屉或比较页面。
- 未启动 Quant Core、Qlib Adapter、Portfolio Backtest、Portfolio Ledger、Risk Engine 或正式组合回测。
- 未启动 Evidence Agent、引用验证、报告 Agent 或真实 LLM 调用。
- 未调用真实 Provider、真实 AlphaSift runtime、真实 LLM 或 Worker execution loop。
- 未迁移 DSA runtime source，未移动 `upstream/dsa-v3.26.1` tag。

## 8. 本地验证

| 验证 | 结果 |
|---|---|
| `.venv/bin/python -m pytest tests/quant/test_screen_snapshot.py -q` | Red：初始缺少 `serenity_alpha_lab.quant.screening.snapshot` 时 `1 error`；Green：`3 passed` |
| `.venv/bin/python -m pytest tests/quant/test_screen_snapshot.py tests/quant/test_screen_definition_pipeline.py tests/quant/test_historical_universe.py tests/quant/test_factor_post_processing.py tests/application/test_candidate_batch_contract.py tests/application/test_screening_provider_contract.py tests/integrations/test_alphasift_screening_adapter.py tests/architecture/test_architecture_boundaries.py -q` | PASS：`39 passed` |
| `.venv/bin/python -m pytest -q` | PASS：`302 passed, 3 skipped` |
| `.venv/bin/python -m compileall src tests` | PASS |
| `scripts/verify-python-dependency-lock.sh` | PASS：`Resolved 298 packages` |
| `git diff --check` | PASS |
| `git rev-parse upstream/dsa-v3.26.1` | PASS：`e8a9ca7742e8cb2498c8f491dd76d239b3064e1a` |

最终完整验证结果同步记录在 `AEV-062`。
