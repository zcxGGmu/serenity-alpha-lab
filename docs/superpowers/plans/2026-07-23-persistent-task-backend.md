# PersistentTaskBackend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement `SAL-P2-018` by adding a database-authoritative `PersistentTaskBackend` with Celery/Redis queue routing boundaries, lease/heartbeat recovery semantics, and append-only task events.

**Architecture:** Keep `TaskBackend` as the application port and place the SQLAlchemy/Celery adapter in `repositories`, matching existing infrastructure boundaries. PostgreSQL/SQLite tables persist task snapshots and events as the source of truth; the queue router only dispatches small task references to worker queues. Worker execution, Quant Core, formal backtest, Evidence Agent, and real Provider calls remain out of scope.

**Tech Stack:** Python 3.11, SQLAlchemy 2.x, existing `TaskBackend` DTOs, existing database profile engine factory, optional injected Celery-like app with Redis broker outside tests.

---

### Task 1: Persistent Backend Contract Tests

**Files:**
- Create: `tests/repositories/test_persistent_task_backend.py`
- Modify: `tasks/todo.md`

- [ ] **Step 1: Write the failing persistence and routing tests**

```python
def test_persistent_task_backend_survives_backend_restart_and_routes_to_queue(sqlite_engine):
    backend = make_backend(sqlite_engine)
    ref = backend.submit(TaskCommand(run_id="run-001", task_type="data.sync.daily", payload={"dataset": "bars"}))
    restarted = make_backend(sqlite_engine)
    assert restarted.get(ref.task_id).status is TaskStatus.QUEUED
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --extra core --extra dev python -m pytest tests/repositories/test_persistent_task_backend.py -q`
Expected: FAIL during collection because `serenity_alpha_lab.repositories.persistent_task_backend` does not exist.

### Task 2: SQLAlchemy PersistentTaskBackend

**Files:**
- Create: `src/serenity_alpha_lab/repositories/persistent_task_backend.py`
- Modify: `src/serenity_alpha_lab/repositories/__init__.py`

- [ ] **Step 1: Add SQL tables and backend shell**

```python
class PersistentTaskBackend:
    def submit(self, command: TaskCommand) -> TaskRef: ...
    def get(self, task_id: str) -> TaskSnapshot: ...
    def request_cancel(self, task_id: str) -> TaskSnapshot: ...
    def subscribe(self, task_id: str, after_event_id: str | None = None) -> tuple[TaskEvent, ...]: ...
```

- [ ] **Step 2: Preserve TaskBackend invariants**

Implement idempotency-key replay, explicit task-id conflict detection, stable snapshots, and monotonic append-only event sequence.

- [ ] **Step 3: Run target tests**

Run: `uv run --extra core --extra dev python -m pytest tests/repositories/test_persistent_task_backend.py -q`
Expected: PASS.

### Task 3: Queue Routing And Lease Recovery

**Files:**
- Modify: `src/serenity_alpha_lab/repositories/persistent_task_backend.py`
- Modify: `tests/repositories/test_persistent_task_backend.py`

- [ ] **Step 1: Add queue routing DTOs**

```python
@dataclass(frozen=True)
class TaskQueueRoute:
    task_type: str
    queue_name: str
    routing_key: str
```

- [ ] **Step 2: Add injected Celery-like router**

Provide `CeleryTaskQueueRouter` that calls an injected app's `send_task(...)` without importing Celery in the application layer.

- [ ] **Step 3: Add lease, heartbeat, completion, failure and expired-lease requeue helpers**

Use database rows as authority and write events for `task.started`, `task.heartbeat`, `task.succeeded`, `task.failed`, `task.cancel_requested`, and `task.requeued`.

- [ ] **Step 4: Run target tests**

Run: `uv run --extra core --extra dev python -m pytest tests/repositories/test_persistent_task_backend.py -q`
Expected: PASS.

### Task 4: Evidence And Status Sync

**Files:**
- Create: `docs/persistent-task-backend.md`
- Modify: `docs/development-progress-checklist.md`
- Modify: `docs/development-status.md`
- Modify: `tasks/todo.md`

- [ ] **Step 1: Document acceptance evidence**

Record red/green evidence, database-authoritative state model, queue routing semantics, lease recovery behavior, and out-of-scope boundaries.

- [ ] **Step 2: Run full verification**

Run target, related repository/application/API/architecture suites, full pytest, compileall, lock drift, `git diff --check`, and immutable upstream tag checks.

- [ ] **Step 3: Commit checkpoint**

Stage only SAL-P2-018 files and create a Chinese checkpoint commit using the project template.
