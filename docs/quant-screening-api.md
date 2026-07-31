# Quant Screening API 记录

> 任务：`SAL-P3-014` 实现 Quant Screening API<br>
> 日期：2026-07-24<br>
> 上游基线：DSA `v3.26.1 @ e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`<br>
> Gate 入口：G2 已通过；G3 未通过<br>
> 结论：`APPROVED FOR SAL-P3-015 SCREEN LAB`

## 1. 交付结论

`SAL-P3-014` 已建立平台侧 Quant Screening API 契约层。该层位于 `application` 边界，提供框架无关的 `/api/v1/quant` route metadata、factor/screen definition 创建响应、screen run `202 Accepted` 响应、稳定分页结果、单证券结果查询和 snapshot comparison 语义，供后续 DSA/FastAPI facade 与 Screen Lab UI 接入。

新增模块：

```text
src/serenity_alpha_lab/application/quant_screening_api.py
```

新增测试：

```text
tests/application/test_quant_screening_api.py
```

本任务不启动真实 AlphaSift、真实 Provider、真实 LLM、Worker execution loop、Quant Core/Qlib、正式组合回测、Evidence Agent、Screen Lab UI 或 DSA runtime source migration。

## 2. Route metadata

`QUANT_SCREENING_API_ROUTES` 冻结以下 API 形状，用于后续 FastAPI/OpenAPI facade：

| Method | Path | Status | 语义 |
|---|---|---:|---|
| `POST` | `/api/v1/quant/factor-definitions` | `201` | 创建/登记因子定义草稿或版本记录 |
| `POST` | `/api/v1/quant/screen-definitions` | `201` | 创建/登记筛选定义版本记录 |
| `POST` | `/api/v1/quant/screen-runs` | `202` | 创建筛选运行引用，要求 `Idempotency-Key` |
| `GET` | `/api/v1/quant/screen-runs/{run_id}` | `200` | 查询运行引用、任务状态和结果锚点 |
| `GET` | `/api/v1/quant/screen-runs/{run_id}/results` | `200` | 分页查询 ScreenSnapshot 结果行 |
| `GET` | `/api/v1/quant/screen-runs/{run_id}/results/{instrument_id}` | `200` | 查询单只证券的 passed/failed-stage 解释行 |
| `GET` | `/api/v1/quant/screen-runs/{run_id}/comparison` | `200` | 比较两个 ScreenSnapshot 的 passed set、状态、rank 和 score delta |

当前实现为 framework-neutral service，不直接注册 FastAPI router。后续 facade 必须复用这些 route metadata、DTO 和错误语义，而不是重新发明一套不兼容响应。

## 3. 契约对象

核心对象：

- `QuantApiRoute`：冻结 method/path/operation id/status 元数据。
- `QuantApiResponse`：JSON-ready response body + headers 容器。
- `QuantScreeningRunRequest`：创建 run 的请求契约，必须绑定 `screen_definition_id`、`sdv_*` definition version、`as_of`、具体 `dsv_*` Dataset Versions 和既有 `ScreenSnapshot`。
- `QuantScreeningRunRecord`：保存 `run_id`、`task_id`、`TaskStatus`、`Idempotency-Key`、`ScreenSnapshot`、trace/run/stage、Artifact manifest 和 request hash。
- `InMemoryQuantScreeningRepository`：测试/desktop preview 用的确定性内存仓库，保存 FactorDefinition、ScreenDefinition 和 run records。
- `QuantScreeningApiService`：应用层 facade，提供 definition create、run create、result page、result row 和 comparison 查询。

`QuantScreeningRunRequest.from_snapshot()` 是当前离线契约入口：它把 `SAL-P3-013` 的 `ScreenSnapshot` 注册为 API 可查询结果，不执行新的筛选计算。后续 Worker/调度任务可用同一 request/record 语义接入真实异步执行，但必须继续通过 `TaskBackend`、Run/Stage/Event、Trace 和 Artifact 边界。

## 4. Idempotency 与任务语义

`create_screen_run()` 必须提供非空 `Idempotency-Key`：

- 首次请求根据 `Idempotency-Key + request_hash` 生成稳定 `run_qs_*` run id。
- 请求通过 `TaskBackend.submit(TaskCommand(..., task_type="quant.screen.run"))` 创建 queued task 引用。
- 相同 `Idempotency-Key` + 相同 request hash 会 replay 原始 `202 Accepted` 响应，不重复创建 task。
- 相同 `Idempotency-Key` + 不同 request hash 会拒绝，防止用户把幂等 key 误用于不同筛选输入。

`202` 响应必须显式包含：

- `run_id` / `task_id` / `status` / `run_type`
- `screen_definition_version_id` / `screen_snapshot_id` / `pipeline_snapshot_id`
- `as_of` 和具体 `dataset_versions`
- `schema.name = quant.screen_snapshot`、`schema.version = 1.0.0`
- `trace.trace_id`、API run id 和 `stage_id`
- 可选 Artifact manifest

## 5. 结果分页与比较

`get_screen_run_results()` 只读取已注册 `ScreenSnapshot.results`，并保持 `ScreenSnapshot` 自身排序：passed 行按连续 rank，failed 行按 failed stage / instrument / rule 排列。

分页语义：

- `cursor=None` 从第一行开始。
- `cursor` 是非负整数 offset 字符串。
- `page_size` 必须为正整数。
- 响应写出 `page_size`、当前 `cursor`、`next_cursor` 和 `total_count`。

每个结果页都必须携带 `as_of`、`dataset_versions`、`schema`、`trace`、snapshot/pipeline id 和可选 Artifact manifest，避免 UI 或后续 Agent 把结果行脱离数据版本和运行血缘展示。

`compare_screen_runs(previous_run_id, current_run_id)` 复用 `compare_screen_snapshots()`，输出 schema `quant.screen_snapshot_comparison@1.0.0`。比较仍是本地 deterministic helper，不访问外部数据、不混合不同 Dataset Version 的语义判断，也不代表回测或组合风险评估。

## 6. ProblemDetails 边界

本任务复用 `application.api_errors.problem_from_exception()` 的既有行为：

- `QuantScreeningApiError` 继承 `ValueError`，在 API 边界映射为 `validation_error` / HTTP `422`。
- 未找到 screen run、无效 cursor、空 `Idempotency-Key`、`latest` Dataset alias 和版本不匹配都通过稳定 ProblemDetails 边界对外表达。
- Trace ID 继续由 P1 `TraceContext` / middleware 层注入；本 service 只在响应 body 中显式保留 trace/run/stage。

## 7. 明确未做事项

- 未实现真实 FastAPI router 注册、DSA endpoint facade 或 OpenAPI snapshot 刷新；本任务只冻结 framework-neutral API contract。
- 未实现 Screen Lab UI、定义编辑页面、结果表格、详情抽屉或比较页面；该范围属于 `SAL-P3-015`。
- 未执行真实 AlphaSift、真实 Provider、真实 LLM、Factor Engine、Quant Core/Qlib 或 Worker loop。
- 未实现正式组合回测、Portfolio Ledger、Risk Engine、Evidence Agent 或报告引用链路。
- 未迁移 DSA runtime source，未移动 `upstream/dsa-v3.26.1` tag。

## 8. 本地验证

| 验证 | 结果 |
|---|---|
| `.venv/bin/python -m pytest tests/application/test_quant_screening_api.py -q` | Red：`1 error`，缺少 `serenity_alpha_lab.application.quant_screening_api`；Green：`5 passed` |
| `.venv/bin/python -m pytest tests/application/test_quant_screening_api.py tests/quant/test_screen_snapshot.py tests/quant/test_screen_definition_pipeline.py tests/quant/test_factor_evaluation.py tests/quant/test_factor_definition_contract.py tests/application/test_task_backend_contract.py tests/application/test_api_errors.py tests/application/test_trace_context.py tests/architecture/test_architecture_boundaries.py -q` | PASS：`45 passed` |
| `.venv/bin/python -m pytest -q` | PASS：`307 passed, 3 skipped` |
| `.venv/bin/python -m compileall src tests` | PASS |
| `scripts/verify-python-dependency-lock.sh` | PASS：`Resolved 298 packages` |
| `git diff --check` | PASS |
| `git rev-parse upstream/dsa-v3.26.1` | PASS：`e8a9ca7742e8cb2498c8f491dd76d239b3064e1a` |

最终完整验证结果同步记录在 `AEV-063`。
