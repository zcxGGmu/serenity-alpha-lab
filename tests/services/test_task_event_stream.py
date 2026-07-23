from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy.engine import Engine

from serenity_alpha_lab.application.api_errors import ValidationProblem
from serenity_alpha_lab.application.config_profiles import load_runtime_settings
from serenity_alpha_lab.application.task_backend import TaskCommand, TaskStatus
from serenity_alpha_lab.application.tracing import TraceContext
from serenity_alpha_lab.domain.run_lifecycle import EventKind, RunEvent
from serenity_alpha_lab.repositories.database import create_database_engine, resolve_database_profile
from serenity_alpha_lab.repositories.persistent_task_backend import (
    CeleryTaskQueueRouter,
    PersistentTaskBackend,
    TaskQueueRoute,
)
from serenity_alpha_lab.services.task_event_stream import (
    TaskEventReconciler,
    TaskEventStreamService,
    parse_last_event_id,
)


class DeterministicClock:
    def __init__(self) -> None:
        self._now = datetime(2026, 7, 23, 10, 0, tzinfo=UTC)

    def __call__(self) -> datetime:
        value = self._now
        self._now += timedelta(seconds=1)
        return value


@dataclass(frozen=True, slots=True)
class FakeAsyncResult:
    id: str


class FakeCeleryApp:
    def __init__(self) -> None:
        self.sent: list[dict[str, Any]] = []

    def send_task(
        self,
        task_name: str,
        *,
        args: list[Any],
        kwargs: dict[str, Any],
        queue: str,
        routing_key: str,
        task_id: str,
    ) -> FakeAsyncResult:
        self.sent.append(
            {
                "task_name": task_name,
                "args": args,
                "kwargs": kwargs,
                "queue": queue,
                "routing_key": routing_key,
                "task_id": task_id,
            }
        )
        return FakeAsyncResult(id=f"celery-{task_id}-{len(self.sent)}")


@pytest.fixture
def sqlite_engine(tmp_path: Path) -> Engine:
    settings = load_runtime_settings(
        {
            "SERENITY_PROFILE": "ci",
            "SERENITY_DATABASE_URL": f"sqlite:///{tmp_path / 'task-event-stream.sqlite'}",
        }
    )
    engine = create_database_engine(resolve_database_profile(settings))
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def clock() -> DeterministicClock:
    return DeterministicClock()


def make_backend(
    engine: Engine,
    *,
    clock: DeterministicClock,
    celery_app: FakeCeleryApp | None = None,
) -> tuple[PersistentTaskBackend, FakeCeleryApp]:
    app = celery_app or FakeCeleryApp()
    backend = PersistentTaskBackend(
        engine,
        queue_router=CeleryTaskQueueRouter(
            app,
            task_name="serenity_alpha_lab.worker.execute_task",
        ),
        routes=(TaskQueueRoute(task_type="data.sync.daily", queue_name="data", routing_key="data.sync"),),
        clock=clock,
    )
    backend.create_schema()
    return backend, app


def make_command(**overrides: Any) -> TaskCommand:
    values = {
        "run_id": "run-event-stream-001",
        "task_type": "data.sync.daily",
        "payload": {"dataset_name": "bars_1d_raw", "market": "cn"},
        "idempotency_key": "data.sync.daily:cn:2026-07-23",
        "metadata": {"trace_id": "trace-event-stream-001"},
    }
    values.update(overrides)
    return TaskCommand(**values)


def test_task_event_stream_replays_after_last_event_id_and_encodes_sse(
    sqlite_engine: Engine,
    clock: DeterministicClock,
) -> None:
    backend, _ = make_backend(sqlite_engine, clock=clock)
    ref = backend.submit(make_command())
    backend.request_cancel(ref.task_id)

    stream = TaskEventStreamService(task_backend=backend)
    frames = stream.task_events(
        ref.task_id,
        last_event_id="1",
        trace_context=TraceContext(trace_id="trace-stream-001", run_id=ref.run_id),
    )

    assert [frame.id for frame in frames] == ["2"]
    assert frames[0].event == "task.cancel_requested"
    assert frames[0].data["task_id"] == ref.task_id
    assert frames[0].data["run_id"] == ref.run_id
    assert frames[0].data["status"] == "cancel_requested"
    assert frames[0].data["trace_id"] == "trace-stream-001"
    encoded = frames[0].encode()
    assert "id: 2\n" in encoded
    assert "event: task.cancel_requested\n" in encoded
    assert encoded.endswith("\n\n")


@pytest.mark.parametrize("raw", ["abc", "-1", "1.5", ""])
def test_task_event_stream_rejects_invalid_last_event_id(raw: str) -> None:
    with pytest.raises(ValidationProblem, match="Last-Event-ID"):
        parse_last_event_id(raw)


def test_persistent_backend_persists_run_events_after_restart(
    sqlite_engine: Engine,
    clock: DeterministicClock,
) -> None:
    backend, app = make_backend(sqlite_engine, clock=clock)
    first = RunEvent(
        run_id="run-stream-001",
        sequence=1,
        kind=EventKind.RUN_STARTED,
        occurred_at=clock(),
        message="started",
    )
    second = RunEvent(
        run_id="run-stream-001",
        sequence=2,
        kind=EventKind.INFO,
        occurred_at=clock(),
        message="checkpoint ready",
        stage_id="stage-sync",
    )

    backend.record_run_event(first)
    backend.record_run_event(second)
    restarted, _ = make_backend(sqlite_engine, clock=clock, celery_app=app)

    assert restarted.subscribe_run_events("run-stream-001") == (first, second)
    stream = TaskEventStreamService(task_backend=restarted)
    frames = stream.run_events("run-stream-001", last_event_id="1")
    assert [frame.id for frame in frames] == ["2"]
    assert frames[0].event == "info"
    assert frames[0].data["stage_id"] == "stage-sync"


def test_reconciler_redispatches_queued_orphans_and_requeues_stalled_leases(
    sqlite_engine: Engine,
    clock: DeterministicClock,
) -> None:
    backend, app = make_backend(sqlite_engine, clock=clock)
    stalled = backend.submit(make_command(task_id="task-stalled"))
    lease = backend.acquire_next(worker_id="worker-data-1", queues=("data",), lease_seconds=1)
    assert lease is not None
    orphan = backend.submit(
        make_command(
            task_id="task-orphan",
            idempotency_key="data.sync.daily:cn:orphan",
        )
    )

    reconciler = TaskEventReconciler(backend=backend)
    summary = reconciler.reconcile(
        now=lease.lease_expires_at + timedelta(seconds=1),
        queued_orphan_age_seconds=0,
    )

    assert summary.queued_orphans_redispatched == 1
    assert summary.stalled_tasks_requeued == 1
    assert summary.problems == ()
    assert backend.get(orphan.task_id).status is TaskStatus.QUEUED
    assert backend.get(stalled.task_id).status is TaskStatus.QUEUED
    assert len(app.sent) == 3
    assert [event.kind for event in backend.subscribe(orphan.task_id)] == [
        "task.submitted",
        "task.redispatched",
    ]
    assert [event.kind for event in backend.subscribe(stalled.task_id)] == [
        "task.submitted",
        "task.started",
        "task.requeued",
    ]
    first_retry = backend.acquire_next(worker_id="worker-data-2", queues=("data",), lease_seconds=30)
    second_retry = backend.acquire_next(worker_id="worker-data-3", queues=("data",), lease_seconds=30)
    third_retry = backend.acquire_next(worker_id="worker-data-4", queues=("data",), lease_seconds=30)
    assert first_retry is not None
    assert second_retry is not None
    assert {first_retry.task_id, second_retry.task_id} == {orphan.task_id, stalled.task_id}
    assert third_retry is None


def test_reconciler_cleans_only_old_temporary_artifacts(
    sqlite_engine: Engine,
    clock: DeterministicClock,
    tmp_path: Path,
) -> None:
    backend, _ = make_backend(sqlite_engine, clock=clock)
    tmp_root = tmp_path / "artifact-store" / "tmp"
    blob_root = tmp_path / "artifact-store" / "blobs"
    manifest_root = tmp_path / "artifact-store" / "manifests"
    tmp_root.mkdir(parents=True)
    blob_root.mkdir(parents=True)
    manifest_root.mkdir(parents=True)
    old_tmp = tmp_root / "old.tmp"
    fresh_tmp = tmp_root / "fresh.tmp"
    blob = blob_root / "blob"
    manifest = manifest_root / "manifest.json"
    for path in (old_tmp, fresh_tmp, blob, manifest):
        path.write_text("keep-or-clean", encoding="utf-8")
    old_timestamp = datetime(2026, 7, 22, 10, 0, tzinfo=UTC).timestamp()
    fresh_timestamp = datetime(2026, 7, 23, 9, 59, tzinfo=UTC).timestamp()
    os.utime(old_tmp, (old_timestamp, old_timestamp))
    os.utime(fresh_tmp, (fresh_timestamp, fresh_timestamp))

    reconciler = TaskEventReconciler(backend=backend, artifact_tmp_roots=(tmp_root,))
    summary = reconciler.reconcile(
        now=datetime(2026, 7, 23, 10, 0, tzinfo=UTC),
        queued_orphan_age_seconds=60,
        temporary_artifact_age_seconds=3600,
    )

    assert summary.temporary_artifacts_removed == 1
    assert not old_tmp.exists()
    assert fresh_tmp.exists()
    assert blob.exists()
    assert manifest.exists()
