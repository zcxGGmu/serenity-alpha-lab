# Recoverable Task Event Stream Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete `SAL-P2-019` by exposing recoverable task/run event streams with SSE `Last-Event-ID` replay, persisted `RunEvent` records, and a database-authoritative orphan/stalled reconciler.

**Architecture:** Extend `PersistentTaskBackend` as the database authority for task events and run events, then add a framework-neutral service that formats replayable SSE frames and reconciles only queued/running task state through existing lease primitives. Reconciler redispatches queued orphans by small task references, requeues expired leases as stalled work, and cleans only temporary artifact files without touching blobs/manifests.

**Tech Stack:** Python 3.11, SQLAlchemy Core, existing `TaskBackend`/`PersistentTaskBackend`, domain `RunEvent`, application `ProblemDetails` and `TraceContext`, local `ArtifactStore` temporary directory semantics, pytest.

---

## Files

- Modify: `src/serenity_alpha_lab/repositories/persistent_task_backend.py`
  - Add `serenity_run_events` table, `record_run_event()`, `subscribe_run_events()`, and queued-orphan redispatch support.
- Create: `src/serenity_alpha_lab/services/task_event_stream.py`
  - Add SSE frame DTOs, `Last-Event-ID` parsing, task/run event stream services, reconciler, and temporary artifact cleanup.
- Modify: `src/serenity_alpha_lab/services/__init__.py`
  - Export task event stream service symbols.
- Modify: `src/serenity_alpha_lab/repositories/__init__.py`
  - Export any new persistent backend DTOs used across tests/docs.
- Create: `tests/services/test_task_event_stream.py`
  - Cover SSE replay, invalid `Last-Event-ID`, run event persistence after restart, queued orphan redispatch, expired lease requeue/stalled distinction, and temporary cleanup boundaries.
- Modify: `docs/recoverable-task-event-stream.md`
  - Add acceptance evidence and scope boundaries for `SAL-P2-019`.
- Modify: `docs/development-progress-checklist.md`, `docs/development-status.md`, `tasks/todo.md`
  - Sync task status, evidence register, decision register, and next-session prompt after verification.

## Task 1: Red Tests

**Files:**
- Create: `tests/services/test_task_event_stream.py`

- [ ] **Step 1: Write failing SSE replay and Last-Event-ID tests**

```python
def test_task_event_stream_replays_after_last_event_id(sqlite_engine, clock):
    backend, _ = make_backend(sqlite_engine, clock=clock)
    ref = backend.submit(make_command())
    backend.request_cancel(ref.task_id)

    stream = TaskEventStreamService(task_backend=backend)
    frames = stream.task_events(ref.task_id, last_event_id="1")

    assert [frame.id for frame in frames] == ["2"]
    assert frames[0].event == "task.cancel_requested"
    assert frames[0].data["status"] == "cancel_requested"
```

- [ ] **Step 2: Write failing ProblemDetails-compatible validation test**

```python
def test_task_event_stream_rejects_invalid_last_event_id(sqlite_engine, clock):
    backend, _ = make_backend(sqlite_engine, clock=clock)
    ref = backend.submit(make_command())

    stream = TaskEventStreamService(task_backend=backend)

    with pytest.raises(ValidationProblem, match="Last-Event-ID"):
        stream.task_events(ref.task_id, last_event_id="not-an-int")
```

- [ ] **Step 3: Write failing RunEvent persistence test**

```python
def test_persistent_backend_persists_run_events_after_restart(sqlite_engine, clock):
    backend, _ = make_backend(sqlite_engine, clock=clock)
    run_event = RunEvent(
        run_id="run-stream-001",
        sequence=1,
        kind=EventKind.RUN_STARTED,
        occurred_at=clock(),
        message="started",
    )

    backend.record_run_event(run_event)
    restarted, _ = make_backend(sqlite_engine, clock=clock)

    assert restarted.subscribe_run_events("run-stream-001") == (run_event,)
```

- [ ] **Step 4: Write failing Reconciler and temporary cleanup tests**

```python
def test_reconciler_redispatches_queued_orphans_and_requeues_stalled_leases(sqlite_engine, clock, tmp_path):
    backend, app = make_backend(sqlite_engine, clock=clock)
    queued = backend.submit(make_command(task_id="task-orphan"))
    running = backend.submit(make_command(task_id="task-stalled", idempotency_key="stalled"))
    lease = backend.acquire_next(worker_id="worker-1", queues=("data",), lease_seconds=1)
    assert lease is not None

    reconciler = TaskEventReconciler(
        backend=backend,
        artifact_tmp_roots=(tmp_path / "artifacts" / "tmp",),
    )
    summary = reconciler.reconcile(
        now=lease.lease_expires_at + timedelta(seconds=1),
        queued_orphan_age_seconds=0,
    )

    assert summary.queued_orphans_redispatched == 1
    assert summary.stalled_tasks_requeued == 1
    assert backend.get(queued.task_id).status is TaskStatus.QUEUED
    assert backend.get(running.task_id).status is TaskStatus.QUEUED
```

- [ ] **Step 5: Run tests and confirm Red**

Run: `uv run --extra core --extra dev python -m pytest tests/services/test_task_event_stream.py -q`

Expected: FAIL because `serenity_alpha_lab.services.task_event_stream` and new persistent backend methods do not exist.

## Task 2: Persistent Backend Extensions

**Files:**
- Modify: `src/serenity_alpha_lab/repositories/persistent_task_backend.py`
- Modify: `src/serenity_alpha_lab/repositories/__init__.py`

- [ ] **Step 1: Add run event table to existing metadata**

```python
_RUN_EVENTS_TABLE = Table(
    "serenity_run_events",
    _TASK_METADATA,
    Column("run_id", String(128), nullable=False),
    Column("sequence", Integer(), nullable=False),
    Column("kind", String(160), nullable=False),
    Column("occurred_at_utc", String(40), nullable=False),
    Column("message", String(1024), nullable=False),
    Column("stage_id", String(128), nullable=True),
    PrimaryKeyConstraint("run_id", "sequence", name="pk_serenity_run_events"),
)
```

- [ ] **Step 2: Include run events in schema creation**

Update `create_schema()` so it creates `_TASK_RUNS_TABLE`, `_TASK_EVENTS_TABLE`, and `_RUN_EVENTS_TABLE`.

- [ ] **Step 3: Add `record_run_event()` and `subscribe_run_events()`**

Use `RunEvent` and `EventKind` from `domain.run_lifecycle`, preserve the event sequence supplied by the domain object, and support `after_event_id` with the same monotonic semantics as `TaskBackend.subscribe()`.

- [ ] **Step 4: Add queued orphan redispatch**

Add `redispatch_queued_orphans(now, orphan_age_seconds, worker_id="reconciler")` that selects non-terminal `queued` tasks older than the cutoff, reconstructs `TaskCommand` from the persisted row, calls the injected queue router, updates `queue_message_id` if present, and appends `task.redispatched` without changing task status.

- [ ] **Step 5: Run target tests**

Run: `uv run --extra core --extra dev python -m pytest tests/repositories/test_persistent_task_backend.py tests/services/test_task_event_stream.py -q`

Expected: newly added service tests progress past missing backend methods; existing P2-018 tests still pass.

## Task 3: Event Stream Service

**Files:**
- Create: `src/serenity_alpha_lab/services/task_event_stream.py`
- Modify: `src/serenity_alpha_lab/services/__init__.py`

- [ ] **Step 1: Add SSE frame DTO**

```python
@dataclass(frozen=True, slots=True)
class ServerSentEvent:
    id: str
    event: str
    data: Mapping[str, Any]
    retry_ms: int | None = None

    def encode(self) -> str:
        payload = json.dumps(dict(self.data), sort_keys=True, default=str)
        lines = [f"id: {self.id}", f"event: {self.event}"]
        if self.retry_ms is not None:
            lines.append(f"retry: {self.retry_ms}")
        lines.append(f"data: {payload}")
        return "\n".join(lines) + "\n\n"
```

- [ ] **Step 2: Parse `Last-Event-ID`**

Implement `parse_last_event_id(value)` so `None` maps to `None`, non-negative integers are returned as normalized strings, and invalid values raise `ValidationProblem("Last-Event-ID must be a non-negative integer")`.

- [ ] **Step 3: Expose task and run events**

`TaskEventStreamService.task_events()` should call `TaskBackend.subscribe(task_id, after_event_id=...)` and map every `TaskEvent` to `ServerSentEvent`. `TaskEventStreamService.run_events()` should call persistent backend `subscribe_run_events()` when available and map every `RunEvent` to SSE.

- [ ] **Step 4: Include trace-safe data**

SSE data should include only scalar-safe fields: `task_id`, `run_id`, `kind`, `status`, `message`, `occurred_at`, `payload`, `trace_id`, and optional `stage_id`; redact payload through existing `redact_sensitive_data()`.

- [ ] **Step 5: Run service tests**

Run: `uv run --extra core --extra dev python -m pytest tests/services/test_task_event_stream.py -q`

Expected: PASS.

## Task 4: Reconciler

**Files:**
- Create: `src/serenity_alpha_lab/services/task_event_stream.py`
- Test: `tests/services/test_task_event_stream.py`

- [ ] **Step 1: Add `TaskEventReconcilerSummary`**

Include `stalled_tasks_requeued`, `queued_orphans_redispatched`, `temporary_artifacts_removed`, and `problems` as immutable fields.

- [ ] **Step 2: Add `TaskEventReconciler.reconcile()`**

Call `backend.requeue_expired_leases(now=...)` for stalled running tasks and `backend.redispatch_queued_orphans(now=..., orphan_age_seconds=...)` for queued orphan delivery recovery when the backend supports it.

- [ ] **Step 3: Clean temporary artifacts only**

Delete files beneath configured `artifact_tmp_roots` whose `mtime` is older than `temporary_artifact_age_seconds`; never delete blob or manifest roots.

- [ ] **Step 4: Preserve failure semantics**

Do not mark stalled work as `failed`; requeue it so a worker can retry from checkpoint. Do not alter terminal `failed/succeeded/cancelled` tasks.

- [ ] **Step 5: Run target and related tests**

Run: `uv run --extra core --extra dev python -m pytest tests/services/test_task_event_stream.py tests/repositories/test_persistent_task_backend.py tests/application/test_task_backend_contract.py tests/application/test_api_errors.py tests/architecture/test_architecture_boundaries.py -q`

Expected: PASS with existing skips only.

## Task 5: Documentation, Verification, and Checkpoint

**Files:**
- Create: `docs/recoverable-task-event-stream.md`
- Modify: `docs/development-progress-checklist.md`
- Modify: `docs/development-status.md`
- Modify: `tasks/todo.md`

- [ ] **Step 1: Write acceptance evidence document**

Document implementation, scope boundaries, verification commands, and no-early-Quant/Evidence/Provider constraints.

- [ ] **Step 2: Update task ledgers**

Mark `SAL-P2-019` as `DONE`, set P2 to `19/20`, total to `48/129`, add `DEC-046` and `AEV-048`, and make `SAL-P2-020` the next task.

- [ ] **Step 3: Run verification**

Run:

```bash
uv run --extra core --extra dev python -m pytest tests/services/test_task_event_stream.py -q
uv run --extra core --extra dev python -m pytest tests/services/test_task_event_stream.py tests/repositories/test_persistent_task_backend.py tests/application/test_task_backend_contract.py tests/application/test_api_errors.py tests/repositories/test_database_profile.py tests/repositories/test_repository_contract.py tests/architecture/test_architecture_boundaries.py -q
uv run --extra core --extra dev python -m pytest -q
uv run --extra core --extra dev python -m compileall -q src/serenity_alpha_lab tests
scripts/verify-python-dependency-lock.sh
git diff --check
git rev-parse upstream/dsa-v3.26.1
```

Expected: target, related, full, compile, lock, diff, and immutable tag checks pass.

- [ ] **Step 4: Commit**

Stage only `SAL-P2-019` files and commit with a Chinese checkpoint message using the project template.
