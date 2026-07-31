# TaskBackend 协议与 DSA 兼容 Facade 记录

> 任务：`SAL-P1-008` 抽取 TaskBackend<br>
> 日期：2026-07-20<br>
> Phase：P1 工程加固<br>
> Gate：G1 未通过<br>
> 范围：应用层 TaskBackend 协议、InMemory 实现、DSA `AnalysisTaskQueue` 注入式兼容 facade；不实现持久队列、Celery/Redis/PostgreSQL、Worker runtime、API endpoint 或 DSA 源码迁移。

## 目标

`TaskBackend` 把 API/Worker 与 DSA `AnalysisTaskQueue` 中的 in-process `ThreadPoolExecutor` 假设隔离开。P1 先冻结稳定协议和 desktop/test 可用的内存实现；后续 `PersistentTaskBackend`、Worker 和 API 迁移必须走同一端口。

## 应用层契约

`src/serenity_alpha_lab/application/task_backend.py` 定义：

| 类型 | 作用 |
|---|---|
| `TaskCommand` | 可序列化任务命令，包含 `run_id`、`task_type`、payload、可选 `task_id` 和 `idempotency_key`。 |
| `TaskRef` | 提交后返回的稳定引用：`task_id`、`run_id`、状态。 |
| `TaskSnapshot` | 查询用任务快照，包含状态、进度、payload、时间戳、result/error 和幂等 key。 |
| `TaskEvent` | 单调 `event_id` 的任务事件，用于 SSE/断线补发。 |
| `TaskBackend` | Protocol：`submit()`、`get()`、`request_cancel()`、`subscribe()`。 |
| `InMemoryTaskBackend` | 无线程池、无外部依赖的内存实现，用于 desktop/test 和后续本地兼容层。 |

状态枚举采用 Serenity 口径：`queued`、`running`、`succeeded`、`failed`、`cancel_requested`、`cancelled`。DSA legacy 状态通过 `task_status_from_legacy()` 映射。

## DSA Facade

`src/serenity_alpha_lab/integrations/dsa/task_backend.py` 提供 `DsaAnalysisTaskQueueBackend`：

- 通过构造函数注入 DSA-like queue，不在模块顶层导入 `src.services.task_queue`。
- 通过 `handlers: Mapping[str, Callable[[TaskCommand], Any]]` 将 `TaskCommand.task_type` 映射为 legacy queue 所需 callable，避免把不可序列化函数放进命令 payload。
- `submit()` 调用已注入 queue 的 `submit_background_task()`，并把 legacy `TaskInfo` 映射为 `TaskRef` / `TaskSnapshot`。
- `get()` 包裹 legacy `get_task()`，缺失时抛出 `TaskNotFound`。
- `request_cancel()` 只调用已注入对象上的 `request_cancel_task()` 或 `cancel_task()`；当前 DSA v3.26.1 没有正式 cancel API，缺失时抛出 `TaskBackendCapabilityError`，不伪造取消成功。
- `subscribe()` 从 `get_task_flow_events()` 读取事件并支持 `after_event_id` 过滤。

## 范围限制

- 不复制、不迁移 DSA `src/services/task_queue.py`。
- 不在 Serenity application 或 DSA facade 中直接导入 `ThreadPoolExecutor`。
- 不引入 Celery、Redis、PostgreSQL 任务状态表、Worker runtime、API endpoint、Quant Core、PIT Dataset 或正式回测。
- 现有 DSA queue 缺少标准 cancel API 的事实通过 capability error 暴露，后续迁移时由统一契约补齐。

## 验证

- Red：新增 `tests/application/test_task_backend_contract.py` 和 `tests/integrations/test_dsa_task_backend_facade.py` 后，目标测试因缺少 `serenity_alpha_lab.application.task_backend` 失败。
- Green：实现应用层 TaskBackend 与 DSA facade 后，`tests/application/test_task_backend_contract.py tests/integrations/test_dsa_task_backend_facade.py tests/architecture/test_architecture_boundaries.py` 通过 `12 passed`。
- 架构：`tests/architecture/test_architecture_boundaries.py` 新增检查，确认 `application` 与 `integrations/dsa` 不直接导入 `ThreadPoolExecutor`。
- 语法：`py_compile` 覆盖 application、integrations/dsa、目标测试和架构测试。
- Checkpoint：全量 `.cache/dsa-p0/venv/bin/python -m pytest -q` 通过 `66 passed`；`scripts/verify-python-dependency-lock.sh`、`git diff --check` 和 `git rev-parse upstream/dsa-v3.26.1` 通过。
