# ScreenDefinition 与 L0-L4 Pipeline 记录

> 任务：`SAL-P3-012` 实现 ScreenDefinition 与 L0~L4 Pipeline<br>
> 日期：2026-07-24<br>
> 上游基线：DSA `v3.26.1 @ e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`<br>
> Gate 入口：G2 已通过；G3 未通过<br>
> 结论：`APPROVED FOR SAL-P3-013 SCREEN SNAPSHOT`

## 1. 交付结论

`SAL-P3-012` 已建立平台侧版本化 `ScreenDefinition` 和确定性 L0~L4 筛选 Pipeline。该层只编排已存在的离线契约：Historical Universe、CandidateBatch、后处理因子结果和 ArtifactStore，不启动真实 AlphaSift/Provider/LLM、Worker runtime、Quant Core/Qlib、正式组合回测、Evidence Agent 或 API/UI。

新增模块：

```text
src/serenity_alpha_lab/quant/screening/pipeline.py
```

新增测试：

```text
tests/quant/test_screen_definition_pipeline.py
```

## 2. ScreenDefinition 版本模型

核心对象：

- `ScreenDefinition`：冻结 `quant.screen_pipeline@1.0.0` 定义，绑定市场、具体 Dataset Version、L1 Provider、L2 Factor、L3 LLM overlay 和 L4 risk gate 参数。
- `ScreenProviderStageSpec`：绑定 provider、strategy、strategy version、provider 分数权重和最大候选数。
- `ScreenFactorStageSpec` / `ScreenFactorSpec`：绑定 `fdv_*` factor version、权重、方向和 L2 分数权重。
- `ScreenLlmOverlayStageSpec`：明确 overlay 是否启用及权重；关闭时权重必须为 0。
- `ScreenRiskGateSpec`：当前只承载 deterministic screen gate：`top_n` 与 `max_per_industry`。

`ScreenDefinition.definition_version_id` 使用行为配置稳定哈希派生，格式为 `sdv_<32 hex>`。修改权重、因子、Provider 策略、LLM overlay、约束或 Dataset Version 都会产生新版本。审计字段如 `created_at` 和 `created_by_run_id` 不参与行为版本哈希。

## 3. Dataset 与发布约束

`ScreenDefinition.dataset_versions` 必须全部是具体 `dsv_*` Dataset Version；`latest` 被拒绝。正式 `run_screen_pipeline()` 只接受 `status=published` 的定义，并校验：

- `UniverseSnapshot.universe_version_id` 与定义中的 `universe` Dataset Version 一致。
- `CandidateBatch` 的 provider、strategy 和 strategy version 与定义一致。
- `CandidateBatch.dataset_versions` 中与定义同名的数据集版本必须一致。
- `CandidateBatch.market` 属于定义市场。
- 每个 factor result 的 `factor_values` Dataset Version 与定义一致。
- `as_of` 与 L0 universe snapshot 日期一致。

## 4. L0~L4 阶段语义

| Stage | 输入 | 语义 | 是否可被 LLM 覆盖 |
|---|---|---|---|
| L0 Universe | `UniverseSnapshot` + provider candidates | 只保留 L0 历史股票池成员；非成员按 `l0_universe_member` 硬排除 | 否 |
| L1 Provider | `CandidateBatch` | universe 成员必须出现在 provider candidate batch，否则按 `l1_provider_candidate_missing` 排除 | 否 |
| L2 Factor | `CrossSectionPostProcessingResult` | 按 factor 权重合成 raw factor score，并在当次候选内归一到 0~100 | 否 |
| L3 LLM Overlay | `CandidateBatch` L3 score | 只对已通过 L0/L1/L2 的候选加可选 overlay 分数 | 否 |
| L4 Final | deterministic risk gate | 按 provider/factor/overlay 权重计算最终分，并执行 `top_n`、`max_per_industry` | 否 |

每个阶段生成 `ScreenPipelineStageTrace`，记录输入、输出和排除数量。候选最终输出为 `ScreenPipelineCandidate`；排除输出为 `ScreenPipelineExclusion`，包含 failed stage、rule id、reason、已有分数和因子贡献。

## 5. Artifact 发布

`ScreenPipelineSnapshot.pipeline_snapshot_id` 从完整 pipeline payload 稳定哈希派生，格式为 `sps_<32 hex>`。`publish_screen_pipeline_snapshot()` 使用既有 `ArtifactStore` 发布 deterministic JSON：

- schema name：`quant.screen_pipeline_snapshot`
- schema version：`1.0.0`
- content type：`application/vnd.serenity.quant.screen-pipeline+json`

同一 snapshot 重复发布得到相同 Artifact ID 和 SHA-256。

## 6. 明确未做事项

- 未实现 `ScreenSnapshot` 结果 Schema、完整解释轨迹或 comparison query；该范围属于 `SAL-P3-013`。
- 未实现 Quant Screening API、Screen Lab、Worker execution loop 或持久 screen run repository。
- 未执行真实 AlphaSift、真实 Provider、真实 LLM、Quant Core/Qlib、正式组合回测或 Evidence Agent。
- 未迁移 DSA runtime source，未移动 `upstream/dsa-v3.26.1` tag。

## 7. 本地验证

| 验证 | 结果 |
|---|---|
| `.venv/bin/python -m pytest tests/quant/test_screen_definition_pipeline.py -q` | Red：初始缺少 `serenity_alpha_lab.quant.screening.pipeline` 时 `1 error`；回归 Red：临时移除 CandidateBatch dataset version guard 时 `1 failed, 2 passed`；Green：`3 passed` |
| `.venv/bin/python -m pytest tests/quant/test_screen_definition_pipeline.py tests/quant/test_historical_universe.py tests/quant/test_factor_post_processing.py tests/quant/test_factor_dag_cache.py tests/application/test_candidate_batch_contract.py tests/application/test_screening_provider_contract.py tests/integrations/test_alphasift_screening_adapter.py tests/architecture/test_architecture_boundaries.py -q` | PASS：`44 passed` |
| `.venv/bin/python -m pytest -q` | PASS：`299 passed, 3 skipped` |
| `.venv/bin/python -m compileall src tests` | PASS |
| `scripts/verify-python-dependency-lock.sh` | PASS：`Resolved 298 packages` |
| `git diff --check` | PASS |
| `git rev-parse upstream/dsa-v3.26.1` | PASS：`e8a9ca7742e8cb2498c8f491dd76d239b3064e1a` |

最终完整验证结果同步记录在 `AEV-061`。
