# 筛选性能与复现验收记录

> 任务：`SAL-P3-016` 筛选性能与复现验收<br>
> 日期：2026-07-25<br>
> 上游基线：DSA `v3.26.1 @ e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`<br>
> Gate 入口：G2 已通过；G3 未通过<br>
> 结论：`APPROVED FOR SAL-P3-017 GATE G3 REVIEW`

## 1. 交付结论

`SAL-P3-016` 已建立平台侧筛选性能、容量、增量和复现验收契约。该层只消费既有 `ScreenSnapshot`、`ScreenPipelineStageTrace`、Dataset Version、Trace/Run/Stage 和 ArtifactStore，不改变 ScreenDefinition Pipeline、Quant Screening API 或 Screen Lab 语义。

新增模块：

```text
src/serenity_alpha_lab/quant/screening/performance.py
```

新增测试：

```text
tests/quant/test_screen_performance_reproducibility.py
```

本任务同步修复一个导入边界问题：`application.__init__` 对 Quant Screening API 改为 lazy export，避免直接导入 `serenity_alpha_lab.quant.screening` 时经 `pipeline -> application -> quant_screening_api -> pipeline` 形成循环初始化；原有 `from serenity_alpha_lab.application import QuantScreeningApiService` 仍可通过 lazy `__getattr__` 使用。

## 2. SLO 与容量预算

`default_a_share_screening_budget()` 固化首期 P3 验收预算：

| 预算项 | 阈值 | 来源 |
|---|---:|---|
| 普通筛选总耗时 | `<= 3,000ms` | 架构方案 API 性能目标：普通筛选 P95 `< 3s` |
| 缓存/结果查询耗时 | `<= 500ms` | 架构方案 API 性能目标：缓存命中查询 P95 `< 500ms` |
| 峰值内存 | `<= 512MB` | P3 离线验收容量预算，用于阻断无界内存增长 |
| 结果行数 | `<= 6,000` | 全 A 股候选规模预算 |
| 增量重算比例 | `<= 15%` | 建立因子/DAG/cache 变更后的增量验收口径 |

这些阈值是 P3 contract baseline，不等同于发布级压测；后续 G6/RC 可按真实硬件、并发和生产 Dataset 扩充。

## 3. 契约对象

核心对象：

- `ScreenPerformanceBudget`：记录筛选、查询、内存、结果行和增量重算阈值。
- `ScreenStagePerformanceSample`：从 `ScreenPipelineStageTrace` 复用 stage/input/output/excluded 口径，补充耗时和峰值内存。
- `ScreenIncrementalBaseline`：记录变更 Dataset Version、可选 factor version、交易日和本次重算候选比例。
- `ScreenRunBundle`：固定 run bundle，包含代码版本、engine version、`sdv_*` ScreenDefinition、`dsv_*` Dataset Version、`ScreenSnapshot`/pipeline id、schema、trace/run/stage、Artifact 和 canonical result hash。
- `ScreenReproducibilityCheck`：比较两次同输入 run 的 canonical result hash，并记录 mismatch reasons。
- `ScreenPerformanceReport`：汇总预算、观测值、阶段样本、增量 baseline、复现检查和 failure codes，并可通过 `ArtifactStore` 发布 deterministic JSON。

## 4. 结果哈希与复现口径

`screen_result_hash()` 使用 canonical JSON + SHA-256，字段包括：

- `code_version`
- `engine_version`
- `screen_definition_version_id`
- `as_of`
- 具体 `dataset_versions`
- `ScreenSnapshot` schema
- passed/failed counts
- canonical `ScreenSnapshot.results`

该 hash 不包含 wall-clock `created_at`、trace id、run id、stage id、`screen_snapshot_id` 或 `pipeline_snapshot_id`，因此同一 Dataset/Definition/Engine/结果行在不同 run metadata 下仍应得到相同 result hash。固定 Run Bundle 会保留这些 run-specific ids 以便审计，但不把它们混入复现判断。

## 5. Artifact 输出

`publish_screen_performance_report()` 使用：

- schema name：`quant.screen_performance_reproducibility`
- schema version：`1.0.0`
- content type：`application/vnd.serenity.quant.screen-performance+json`

同一 report 重复发布得到相同 Artifact ID 和 SHA-256。发布继续复用 P1 `ArtifactStore` 的内容寻址与 manifest-last 原子发布语义。

## 6. 明确未做事项

- 未执行真实全市场 Provider/AlphaSift/LLM 调用。
- 未实现 Worker execution loop、Celery/Redis handler、真实调度或生产监控。
- 未执行因子值计算、Quant Core/Qlib、Portfolio Backtest、Portfolio Ledger、Risk Engine 或正式组合回测。
- 未启动 Evidence Agent、引用验证、报告 Agent 或真实模型调用。
- 未迁移 DSA runtime source，未移动 `upstream/dsa-v3.26.1` tag。

## 7. 本地验证

| 验证 | 结果 |
|---|---|
| `.venv/bin/python -m pytest tests/quant/test_screen_performance_reproducibility.py -q` | Red：初始暴露 `application.__init__` / `quant.screening.pipeline` 循环导入；修复 lazy export 后 Red 为缺少 `serenity_alpha_lab.quant.screening.performance`；Green：`3 passed` |
| `.venv/bin/python -m pytest tests/quant/test_screen_performance_reproducibility.py tests/quant/test_screen_snapshot.py tests/quant/test_screen_definition_pipeline.py tests/application/test_quant_screening_api.py tests/application/test_task_backend_contract.py tests/application/test_api_errors.py tests/application/test_trace_context.py tests/architecture/test_architecture_boundaries.py -q` | PASS：`41 passed` |
| `.venv/bin/python -m pytest -q` | PASS：`310 passed, 3 skipped` |
| `.venv/bin/python -m compileall src tests` | PASS |
| `scripts/verify-python-dependency-lock.sh` | PASS：`Resolved 298 packages` |
| `scripts/apply-dsa-baseline-patches.sh --check-only` | PASS：`0001..0004` already applied |
| `git rev-parse upstream/dsa-v3.26.1` | PASS：`e8a9ca7742e8cb2498c8f491dd76d239b3064e1a` |
| `git diff --check` | PASS |
| `.venv/bin/python - <<'PY' ... import serenity_alpha_lab.quant.screening / performance / application ... PY` | PASS：直接导入 `quant.screening`、`quant.screening.performance` 和 lazy `application.QuantScreeningApiService` |

本地 senior review 发现并修复一处报告一致性问题：`observed.result_row_count` 改为使用 `ScreenSnapshot` 实际结果行数，而不是最后一个 pipeline stage sample 的 `output + excluded`。代码审查子代理 dispatch 多次被 host wrapper 以空 optional fields 拒绝，故本次以本地审查与上述新鲜验证作为收尾证据。
