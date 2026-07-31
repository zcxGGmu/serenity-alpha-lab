from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from serenity_alpha_lab.application.task_backend import (
    InMemoryTaskBackend,
    TaskAlreadyExists,
    TaskCommand,
    TaskNotFound,
    TaskStatus,
)


class DeterministicClock:
    def __init__(self) -> None:
        self._now = datetime(2026, 7, 20, 11, 0, tzinfo=UTC)

    def __call__(self) -> datetime:
        value = self._now
        self._now += timedelta(seconds=1)
        return value


def make_backend() -> InMemoryTaskBackend:
    return InMemoryTaskBackend(clock=DeterministicClock())


def make_command(**overrides) -> TaskCommand:
    values = {
        "run_id": "run-task-001",
        "task_type": "research.analysis",
        "payload": {"symbol": "600519.XSHG"},
        "idempotency_key": "research:600519.XSHG:2026-07-20",
    }
    values.update(overrides)
    return TaskCommand(**values)


def test_task_backend_submit_get_and_subscribe_contract() -> None:
    backend = make_backend()

    ref = backend.submit(make_command())
    snapshot = backend.get(ref.task_id)
    events = backend.subscribe(ref.task_id)

    assert ref.task_id
    assert ref.run_id == "run-task-001"
    assert ref.status is TaskStatus.QUEUED
    assert snapshot.status is TaskStatus.QUEUED
    assert snapshot.progress == 0
    assert snapshot.payload == {"symbol": "600519.XSHG"}
    assert [event.kind for event in events] == ["task.submitted"]
    assert [event.event_id for event in events] == ["1"]


def test_task_backend_cancel_and_resume_subscription_after_event_id() -> None:
    backend = make_backend()
    ref = backend.submit(make_command())

    cancelled = backend.request_cancel(ref.task_id)
    replay = backend.subscribe(ref.task_id, after_event_id="1")

    assert cancelled.status is TaskStatus.CANCELLED
    assert [event.kind for event in replay] == ["task.cancelled"]
    assert replay[0].status is TaskStatus.CANCELLED


def test_task_backend_reuses_task_for_same_idempotency_key() -> None:
    backend = make_backend()
    first = backend.submit(make_command())
    second = backend.submit(make_command(payload={"symbol": "600519.XSHG"}))

    assert second == first
    assert len(backend.subscribe(first.task_id)) == 1


def test_task_backend_rejects_conflicting_explicit_task_id_and_unknown_get() -> None:
    backend = make_backend()
    backend.submit(make_command(task_id="task-fixed-001"))

    with pytest.raises(TaskAlreadyExists):
        backend.submit(make_command(task_id="task-fixed-001", idempotency_key="different-key"))

    with pytest.raises(TaskNotFound):
        backend.get("missing-task")
