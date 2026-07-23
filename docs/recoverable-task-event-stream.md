# 可恢复任务事件流记录

> 任务：`SAL-P2-019` 实现可恢复任务事件流<br>
> 日期：2026-07-23<br>
> 实现 checkpoint：本次实现提交生成后由状态同步提交回填实际 hash<br>
> 代码：`src/serenity_alpha_lab/services/task_event_stream.py`；`src/serenity_alpha_lab/repositories/persistent_task_backend.py`<br>
> 测试：`tests/services/test_task_event_stream.py`<br>
> 范围：持久化/暴露 `RunEvent`、SSE `Last-Event-ID` 补发、queued orphan redispatch、stalled lease requeue 和临时 Artifact 清理；不启动完整 Worker execution loop、正式 API/前端页面、Quant Core、正式回测、Evidence Agent、真实 Provider/LLM 调用或 DSA runtime source migration。

## 1. 结论

`SAL-P2-019` 在 `PersistentTaskBackend` 的数据库权威任务事件基础上，新增可恢复事件流 primitives。浏览器或调用方可以用 SSE `Last-Event-ID` 按单调事件 ID 补发 task/run 事件；Run lifecycle 事件通过 `serenity_run_events` 持久化；Reconciler 只修复投递/租约状态，不执行任务 handler，也不把 queue 状态当作权威。

本任务补齐 `SAL-P2-018` 留出的 SSE 恢复和孤儿 Reconciler 边界。完整 Worker runtime、正式 FastAPI SSE endpoint、前端页面、Quant Core、正式回测和 Evidence Agent 继续留给后续任务。

## 2. 实现内容

| 能力 | 实现 |
|---|---|
| RunEvent 持久化 | `PersistentTaskBackend.record_run_event()` / `subscribe_run_events()` 使用 `serenity_run_events` 保存 `run_id + sequence`、`EventKind`、时间、消息和 `stage_id`。 |
| SSE 补发 | `TaskEventStreamService.task_events()` 复用 `TaskBackend.subscribe(after_event_id)`，`run_events()` 复用持久 backend 的 `subscribe_run_events(after_event_id)`。 |
| Last-Event-ID 校验 | `parse_last_event_id()` 只接受非负整数字符串；非法游标抛出 `ValidationProblem`，可由既有 ProblemDetails 映射。 |
| Trace-safe payload | SSE data 只暴露 scalar-safe 字段和脱敏后的 event payload；可注入 `TraceContext` 并写入 `trace_id`。 |
| queued orphan redispatch | `redispatch_queued_orphans()` 从数据库重建小型 `TaskCommand`，仅投递 `task_id/run_id/task_type` 引用，并追加 `task.redispatched` 事件；任务状态仍为 `queued`。 |
| stalled lease requeue | `TaskEventReconciler` 调用既有 `requeue_expired_leases()`，把过期 `running` 任务恢复为 `queued`，保留 `stalled` 与 `failed` 区分。 |
| 重复投递防副作用 | duplicate queue delivery 只会竞争数据库 lease；测试覆盖两个 queued 任务被领取后第三次领取返回 `None`。 |
| 临时 Artifact 清理 | Reconciler 只清理配置的 `tmp` roots 中过期文件，不触碰 blob 或 manifest roots。 |

## 3. 数据库权威边界

- Task 事件继续由 `serenity_task_backend_events` 按 `task_id + sequence` 追加保存，SSE task 补发完全依赖 `TaskBackend.subscribe(after_event_id)`。
- Run 事件由 `serenity_run_events` 按 `run_id + sequence` 追加保存，保留 P1 `RunEvent` 领域模型，不新增第二套 Run 状态机。
- Queue message id 只作诊断字段；redispatch 只追加审计事件，不把 Celery/Redis delivery state 写成任务权威状态。
- Reconciler 不执行任务 handler，不调用 Provider/LLM，不发布 Dataset，不生成 Evidence，也不启动 Quant Core。

## 4. 范围限制

- 未引入 FastAPI endpoint、Web EventSource 页面、Celery worker loop、Redis namespace 配置或 Compose service。
- 未执行真实 Provider、LLM、Quant Core、正式回测、Evidence Agent 或 DSA runtime source 调用。
- 未移动 `upstream/dsa-v3.26.1` tag，未提交 `.worktrees`、`.cache`、pycache、node_modules、static 或 Playwright artifacts。
- Temporary cleanup 只对调用方显式传入的 tmp roots 生效，不扫描或删除 Artifact blob/manifests。

## 5. 验证证据

| 阶段 | 命令 | 结果 |
|---|---|---|
| Red | `uv run --extra core --extra dev python -m pytest tests/services/test_task_event_stream.py -q` | 先因缺少 `serenity_alpha_lab.services.task_event_stream` 失败。 |
| Target | `uv run --extra core --extra dev python -m pytest tests/services/test_task_event_stream.py -q` | `8 passed`。 |
| Related | `uv run --extra core --extra dev python -m pytest tests/services/test_task_event_stream.py tests/repositories/test_persistent_task_backend.py tests/application/test_task_backend_contract.py tests/application/test_api_errors.py tests/repositories/test_database_profile.py tests/repositories/test_repository_contract.py tests/architecture/test_architecture_boundaries.py -q` | `40 passed, 3 skipped`。 |
| Full | `uv run --extra core --extra dev python -m pytest -q` | `233 passed, 3 skipped`。 |
| Compile | `uv run --extra core --extra dev python -m compileall -q src/serenity_alpha_lab tests` | PASS。 |
| Lock | `scripts/verify-python-dependency-lock.sh` | PASS。 |
| Diff | `git diff --check` | PASS。 |
| Tag | `git rev-parse upstream/dsa-v3.26.1` | `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`。 |

## 6. 后续交接

- `SAL-P2-020` 可以基于 P2 Dataset、Provider、PostgreSQL profile、PersistentTaskBackend 和本任务事件流证据执行 Gate G2 评审。
- 后续正式 API/SSE endpoint 应薄封装 `TaskEventStreamService`，不要重新实现事件 cursor、脱敏或 ProblemDetails 语义。
- 后续 Worker runtime 应继续只调用 `PersistentTaskBackend` 的 lease/heartbeat/complete/fail/requeue/redispatch primitives，不直接以 Celery/Redis 状态作为权威。
