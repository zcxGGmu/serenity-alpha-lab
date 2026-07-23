# FactorDefinition 版本模型记录

> 任务：`SAL-P3-005` 实现 FactorDefinition 版本模型<br>
> 日期：2026-07-23<br>
> 上游基线：DSA `v3.26.1 @ e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`<br>
> Gate 入口：G2 已通过；G3 未通过<br>
> 结论：`APPROVED FOR SAL-P3-006 FACTOR DSL CONTRACT`

## 1. 交付结论

`SAL-P3-005` 已建立平台侧 `FactorDefinition` 版本模型和本地定义仓库。该模型只描述因子定义、输入、窗口、缺失策略、后处理、实现哈希和版本生命周期，不执行 DSL、不计算因子值、不启动 DAG/cache、Qlib、正式回测或 Evidence Agent。

新增模块：

```text
src/serenity_alpha_lab/quant/factors/definitions.py
```

导出入口：

```text
src/serenity_alpha_lab/quant/factors/__init__.py
```

## 2. 契约对象

核心对象：

- `FactorDefinition`：因子定义聚合，包含 `definition_id`、`semantic_version`、公式、输入、窗口、缺失策略、后处理、方向、分类、实现哈希、spec hash、状态和发布元数据。
- `FactorFormula`：保存公式表达式、公式语言和目标 engine version；本任务不解析或执行表达式。
- `FactorInput`：声明输入字段、Dataset 名称、具体 Dataset Version、字段名、数据类型和 metadata；Dataset Version 必须是 `dsv_*`，拒绝 `latest`。
- `FactorWindow`：声明窗口名称、长度、单位和 `min_periods`。
- `MissingValuePolicy`：声明缺失值策略，支持 `drop`、`forward_fill`、`fill_constant` 和 `zero`；`fill_constant` 必须显式给出 `fill_value`。
- `PostProcessingStep`：保存后处理步骤名和参数；本任务只版本化配置，不执行 winsorize/zscore/neutralize。
- `FactorDefinitionRetirement`：独立退休记录，用于表达 retired 生命周期而不修改 published manifest。
- `FactorDefinitionAuditEvent`：保存 draft/publish/retire 审计事件。

## 3. 生命周期

生命周期状态：

```text
draft -> published -> retired
```

行为规则：

- Draft 可通过 `LocalFactorDefinitionRepository.save_draft()` 覆盖同一 `definition_id + semantic_version` 草稿。
- Published 通过 `publish_draft()` 生成不可变 `fdv_*` 版本，`version_id` 由 canonical spec hash 派生。
- 同一 `definition_id + semantic_version` 一旦发布，不允许指向不同 spec hash；再次发布相同内容保持幂等。
- Retired 通过 `retire_version()` 写入独立 retirement record；`get_version()` 仍返回原始 published manifest，`version_status()` 才显示 retired。
- Audit log 追加 `draft_saved`、`published`、`retired` 事件；不把 queue 或外部状态作为定义权威。

## 4. 关键校验

- `semantic_version` 必须是 `MAJOR.MINOR.PATCH` 形式。
- 所有 `FactorInput.dataset_version` 必须通过 `DatasetVersionRef.version()` 校验，`latest` alias 被拒绝。
- `implementation_hash` 和 `spec_hash` 必须是 `sha256:<64 lowercase hex>`。
- `FactorWindow.length` 和 `min_periods` 必须为正整数，且 `min_periods <= length`。
- `created_at`、`published_at` 和 `retired_at` 必须为 timezone-aware datetime。
- nested metadata 和 post-process parameters 在对象中冻结，`to_record()` 输出 JSON-friendly dict。

## 5. 明确未做事项

- 未实现因子 DSL parser、AST、validator、compiler 或算子白名单；该范围属于 `SAL-P3-006`。
- 未实现基础因子、横截面后处理执行、Factor Evaluation、DAG/cache、Historical Universe、ScreenDefinition、ScreenSnapshot、Quant Screening API 或 Screen Lab。
- 未启动 Quant Core。
- 未启动正式回测。
- 未启动 Evidence Agent。
- 未调用真实 Provider。
- 未调用真实 LLM。
- 未实现 Worker execution loop，未接入 Celery/Redis 实际执行。
- 未迁移 DSA runtime source，未移动 `upstream/dsa-v3.26.1` tag。

## 6. 本地验证

| 验证 | 结果 |
|---|---|
| `uv run --extra core --extra dev python -m pytest tests/quant/test_factor_definition_contract.py -q` | Red：`1 error`，缺少 `serenity_alpha_lab.quant.factors.definitions`；Green：`3 passed` |
| `uv run --extra core --extra dev python -m pytest tests/quant/test_factor_definition_contract.py tests/application/test_candidate_batch_contract.py tests/application/test_screening_provider_contract.py tests/integrations/test_alphasift_screening_adapter.py tests/architecture/test_architecture_boundaries.py -q` | PASS：`28 passed` |
| `uv run --extra core --extra dev python -m pytest -q` | PASS：`258 passed, 3 skipped` |
| `uv run --extra core --extra dev python -m compileall src tests` | PASS |
| `scripts/verify-python-dependency-lock.sh` | PASS：`Resolved 298 packages` |
| `git diff --check` | PASS |
| `git rev-parse upstream/dsa-v3.26.1` | `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a` |

最终完整验证结果同步记录在 `AEV-054`。
