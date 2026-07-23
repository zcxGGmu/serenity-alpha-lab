from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy.engine import Engine

from serenity_alpha_lab.application.config_profiles import load_runtime_settings
from serenity_alpha_lab.application.task_backend import (
    TaskAlreadyExists,
    TaskCommand,
    TaskStatus,
)
from serenity_alpha_lab.repositories.database import create_database_engine, resolve_database_profile
from serenity_alpha_lab.repositories.persistent_task_backend import (
    CeleryTaskQueueRouter,
    PersistentTaskBackend,
    TaskQueueRoute,
)


class DeterministicClock:
    def __init__(self) -> None:
        self._now = datetime(2026, 7, 23, 9, 30, tzinfo=UTC)

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
        return FakeAsyncResult(id=f"celery-{task_id}")


@pytest.fixture
def sqlite_engine(tmp_path: Path) -> Engine:
    settings = load_runtime_settings(
        {
            "SERENITY_PROFILE": "ci",
            "SERENITY_DATABASE_URL": f"sqlite:///{tmp_path / 'persistent-task-backend.sqlite'}",
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
        routes=(
            TaskQueueRoute(task_type="data.sync.daily", queue_name="data", routing_key="data.sync"),
            TaskQueueRoute(task_type="research.agent", queue_name="agent", routing_key="agent.research"),
        ),
        clock=clock,
    )
    backend.create_schema()
    return backend, app


def make_command(**overrides: Any) -> TaskCommand:
    values = {
        "run_id": "run-persistent-001",
        "task_type": "data.sync.daily",
        "payload": {"dataset_name": "bars_1d_raw", "market": "cn"},
        "idempotency_key": "data.sync.daily:cn:2026-07-23",
        "metadata": {"trace_id": "trace-persistent-001"},
    }
    values.update(overrides)
    return TaskCommand(**values)


def test_persistent_task_backend_survives_restart_and_routes_to_celery_queue(
    sqlite_engine: Engine,
    clock: DeterministicClock,
) -> None:
    backend, app = make_backend(sqlite_engine, clock=clock)

    ref = backend.submit(make_command())

    restarted, _ = make_backend(sqlite_engine, clock=clock, celery_app=app)
    snapshot = restarted.get(ref.task_id)
    events = restarted.subscribe(ref.task_id)

    assert ref.run_id == "run-persistent-001"
    assert ref.status is TaskStatus.QUEUED
    assert snapshot.status is TaskStatus.QUEUED
    assert snapshot.task_type == "data.sync.daily"
    assert snapshot.payload == {"dataset_name": "bars_1d_raw", "market": "cn"}
    assert snapshot.metadata == {"trace_id": "trace-persistent-001"}
    assert [event.event_id for event in events] == ["1"]
    assert [event.kind for event in events] == ["task.submitted"]
    assert app.sent == [
        {
            "task_name": "serenity_alpha_lab.worker.execute_task",
            "args": [ref.task_id],
            "kwargs": {
                "task_id": ref.task_id,
                "run_id": "run-persistent-001",
                "task_type": "data.sync.daily",
            },
            "queue": "data",
            "routing_key": "data.sync",
            "task_id": ref.task_id,
        }
    ]


def test_persistent_task_backend_replays_idempotency_without_duplicate_dispatch(
    sqlite_engine: Engine,
    clock: DeterministicClock,
) -> None:
    backend, app = make_backend(sqlite_engine, clock=clock)

    first = backend.submit(make_command())
    replay = backend.submit(make_command(payload={"dataset_name": "bars_1d_raw", "market": "cn"}))

    assert replay == first
    assert len(app.sent) == 1

    with pytest.raises(TaskAlreadyExists):
        backend.submit(
            make_command(
                task_id=first.task_id,
                idempotency_key="different-key",
            )
        )


def test_persistent_task_backend_records_cancel_request_as_database_event(
    sqlite_engine: Engine,
    clock: DeterministicClock,
) -> None:
    backend, _ = make_backend(sqlite_engine, clock=clock)
    ref = backend.submit(make_command(task_type="research.agent", idempotency_key="research:agent:001"))

    cancelled = backend.request_cancel(ref.task_id)
    replay = backend.subscribe(ref.task_id, after_event_id="1")

    assert cancelled.status is TaskStatus.CANCEL_REQUESTED
    assert cancelled.message == "cancel requested"
    assert [event.kind for event in replay] == ["task.cancel_requested"]
    assert replay[0].status is TaskStatus.CANCEL_REQUESTED


def test_persistent_task_backend_claims_heartbeats_and_completes_worker_lease(
    sqlite_engine: Engine,
    clock: DeterministicClock,
) -> None:
    backend, _ = make_backend(sqlite_engine, clock=clock)
    ref = backend.submit(make_command())

    lease = backend.acquire_next(worker_id="worker-data-1", queues=("data",), lease_seconds=30)
    assert lease is not None
    assert lease.task_id == ref.task_id
    assert lease.snapshot.status is TaskStatus.RUNNING
    assert lease.queue_name == "data"

    heartbeat = backend.heartbeat(ref.task_id, worker_id="worker-data-1", lease_seconds=60)
    completed = backend.complete(
        ref.task_id,
        worker_id="worker-data-1",
        result={"dataset_version_id": "dsv_" + "a" * 32},
        message="dataset published",
    )
    events = backend.subscribe(ref.task_id)

    assert heartbeat.status is TaskStatus.RUNNING
    assert completed.status is TaskStatus.SUCCEEDED
    assert completed.progress == 100
    assert completed.result == {"dataset_version_id": "dsv_" + "a" * 32}
    assert [event.kind for event in events] == [
        "task.submitted",
        "task.started",
        "task.heartbeat",
        "task.succeeded",
    ]


def test_persistent_task_backend_requeues_expired_leases_for_safe_worker_retry(
    sqlite_engine: Engine,
    clock: DeterministicClock,
) -> None:
    backend, _ = make_backend(sqlite_engine, clock=clock)
    ref = backend.submit(make_command())
    lease = backend.acquire_next(worker_id="worker-data-1", queues=("data",), lease_seconds=1)
    assert lease is not None

    requeued = backend.requeue_expired_leases(
        now=lease.lease_expires_at + timedelta(seconds=1),
        worker_id="reconciler",
    )
    retry_lease = backend.acquire_next(worker_id="worker-data-2", queues=("data",), lease_seconds=30)
    events = backend.subscribe(ref.task_id)

    assert requeued == 1
    assert retry_lease is not None
    assert retry_lease.task_id == ref.task_id
    assert retry_lease.snapshot.status is TaskStatus.RUNNING
    assert [event.kind for event in events] == [
        "task.submitted",
        "task.started",
        "task.requeued",
        "task.started",
    ]
