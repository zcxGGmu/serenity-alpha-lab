# PersistentTaskBackend 记录

> 任务：`SAL-P2-018` 实现 PersistentTaskBackend<br>
> 日期：2026-07-23<br>
> 代码：`src/serenity_alpha_lab/repositories/persistent_task_backend.py`<br>
> 测试：`tests/repositories/test_persistent_task_backend.py`<br>
> 范围：数据库权威任务状态、追加事件、Celery/Redis 队列路由边界、Worker lease/heartbeat/requeue primitives；不启动完整 Worker execution loop、API/SSE、Quant Core、正式回测、Evidence Agent、真实 Provider/LLM 调用或 DSA runtime source migration。

## 1. 结论

`PersistentTaskBackend` 已按 `TaskBackend` Protocol 增加 SQLAlchemy 持久实现。任务状态、快照和事件由数据库表 `serenity_task_backend_runs` 与 `serenity_task_backend_events` 作为权威来源；Celery/Redis 只通过注入式 `CeleryTaskQueueRouter` 接收小型任务引用，不保存业务大对象，也不作为前端状态、审计或恢复的权威。

本任务补齐 `SAL-P2-017` 留出的持久任务边界，但仍只提供后端 primitives：提交、查询、事件回放、取消请求、Worker 领取、心跳、完成、失败和过期租约重投。完整 Worker runtime、SSE `Last-Event-ID` 恢复、孤儿 Reconciler API、Quant/Agent 执行和真实 Provider 调用留给后续任务。

## 2. 实现内容

| 能力 | 实现 |
|---|---|
| 持久快照 | `PersistentTaskBackend.submit/get/request_cancel/subscribe()` 使用 SQLAlchemy 表持久化任务快照和事件。 |
| 幂等提交 | `idempotency_key` 命中时返回既有 `TaskRef`，不重复队列投递；显式 `task_id` 冲突抛出 `TaskAlreadyExists`。 |
| 队列路由 | `TaskQueueRoute` 按 `task_type` 映射 `queue_name` 和 `routing_key`；`CeleryTaskQueueRouter` 调用注入式 Celery app 的 `send_task()`，payload 只包含 `task_id/run_id/task_type`。 |
| 追加事件 | 每个 task 的事件 sequence 单调递增，支持 `subscribe(after_event_id=...)` 补发。 |
| 取消请求 | `request_cancel()` 将非终态任务置为 `cancel_requested` 并追加 `task.cancel_requested`，不伪造 Worker 已停止。 |
| Worker lease | `acquire_next()` 只领取 `queued` 状态任务，记录 `lease_owner`、`lease_expires_at`、heartbeat 和 attempt。 |
| 心跳与终态 | `heartbeat()` 延长租约；`complete()` / `fail()` 校验 lease owner 后写入终态、结果/错误和事件。 |
| 异常恢复 | `requeue_expired_leases()` 把过期 `running` 任务恢复为 `queued`，追加 `task.requeued`，允许其他 Worker 安全重试。 |

## 3. 数据库权威边界

- 数据库记录是 Run/Event 权威：`TaskSnapshot` 和 `TaskEvent` 均从持久表重建，后端重启后仍可查询同一任务。
- 队列只负责投递：`queue_message_id` 仅作诊断字段；队列状态不参与 `get()` / `subscribe()` 的权威判断。
- 事件只追加：状态变化通过新事件记录，前端或后续 SSE 恢复只能按事件 sequence 补发。
- 大对象不入队列：DataFrame、Prompt 全文、Provider 原始响应、报告和大结果必须继续走 Artifact/Dataset 边界。

## 4. 范围限制

- 未引入新的 Celery 或 Redis direct dependency；当前以注入式 Celery-like app 适配部署侧已配置的 broker，避免 application/domain 层感知基础设施。
- 未实现完整 Worker loop、task handler registry、API endpoint、SSE、孤儿 Reconciler、Compose service 或 Redis namespace 配置。
- 未执行真实 Provider、LLM、Quant Core、正式回测、Evidence Agent 或 DSA runtime source 调用。
- 未移动 `upstream/dsa-v3.26.1` tag，未提交 `.worktrees`、`.cache`、pycache、node_modules、static 或 Playwright artifacts。

## 5. 验证证据

| 阶段 | 命令 | 结果 |
|---|---|---|
| Red | `uv run --extra core --extra dev python -m pytest tests/repositories/test_persistent_task_backend.py -q` | 先因缺少 `serenity_alpha_lab.repositories.persistent_task_backend` 失败。 |
| Target | `uv run --extra core --extra dev python -m pytest tests/repositories/test_persistent_task_backend.py -q` | `5 passed`。 |
| Related | `uv run --extra core --extra dev python -m pytest tests/repositories/test_persistent_task_backend.py tests/application/test_task_backend_contract.py tests/integrations/test_dsa_task_backend_facade.py tests/repositories/test_database_profile.py tests/repositories/test_repository_contract.py tests/application/test_api_errors.py tests/architecture/test_architecture_boundaries.py -q` | `35 passed, 3 skipped`。 |
| Full | `uv run --extra core --extra dev python -m pytest -q` | `225 passed, 3 skipped`。 |
| Compile | `uv run --extra core --extra dev python -m compileall -q src/serenity_alpha_lab tests` | PASS。 |
| Lock | `scripts/verify-python-dependency-lock.sh` | PASS。 |
| Diff | `git diff --check` | PASS。 |
| Tag | `git rev-parse upstream/dsa-v3.26.1` | `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`。 |

## 6. 后续交接

- `SAL-P2-019` 可基于本事件表实现 SSE `Last-Event-ID`、孤儿任务 Reconciler、stalled 与 failed 区分、以及临时 Artifact 清理。
- 后续 Worker runtime 应只调用本任务提供的 lease/heartbeat/complete/fail/requeue primitives，不直接读取 Celery/Redis 状态作为权威。
- 后续真实 Provider 调用仍必须通过 profile guard、离线契约和 fallback trace 接入，不得绕过 `ProviderPolicy` 与 Dataset 质量门禁。
