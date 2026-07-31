from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Callable, Mapping, Protocol


ClockFn = Callable[[], datetime]


class TaskBackendError(RuntimeError):
    """Base error for task backend operations."""


class TaskNotFound(TaskBackendError):
    """Raised when a task id is unknown to the backend."""


class TaskAlreadyExists(TaskBackendError):
    """Raised when an explicit task id conflicts with an existing task."""


class TaskBackendCapabilityError(TaskBackendError):
    """Raised when a backend cannot provide a requested operation."""


class TaskStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCEL_REQUESTED = "cancel_requested"
    CANCELLED = "cancelled"


TERMINAL_TASK_STATUSES = frozenset(
    {TaskStatus.SUCCEEDED, TaskStatus.FAILED, TaskStatus.CANCELLED}
)


@dataclass(frozen=True, slots=True)
class TaskCommand:
    run_id: str
    task_type: str
    payload: Mapping[str, Any] = field(default_factory=dict)
    idempotency_key: str | None = None
    task_id: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.run_id.strip():
            raise TaskBackendError("run_id is required")
        if not self.task_type.strip():
            raise TaskBackendError("task_type is required")
        object.__setattr__(self, "payload", dict(self.payload))
        object.__setattr__(self, "metadata", dict(self.metadata))


@dataclass(frozen=True, slots=True)
class TaskRef:
    task_id: str
    run_id: str
    status: TaskStatus


@dataclass(frozen=True, slots=True)
class TaskEvent:
    event_id: str
    task_id: str
    run_id: str
    kind: str
    occurred_at: datetime
    status: TaskStatus
    message: str | None = None
    payload: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "payload", dict(self.payload))


@dataclass(frozen=True, slots=True)
class TaskSnapshot:
    task_id: str
    run_id: str
    task_type: str
    status: TaskStatus
    submitted_at: datetime
    payload: Mapping[str, Any] = field(default_factory=dict)
    progress: int = 0
    message: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    result: Mapping[str, Any] | None = None
    error: str | None = None
    idempotency_key: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "payload", dict(self.payload))
        object.__setattr__(self, "metadata", dict(self.metadata))
        if self.result is not None:
            object.__setattr__(self, "result", dict(self.result))


class TaskBackend(Protocol):
    """Application port for task submission, status lookup, cancellation, and events."""

    def submit(self, command: TaskCommand) -> TaskRef:
        """Submit a task command and return a stable reference."""

    def get(self, task_id: str) -> TaskSnapshot:
        """Return a task snapshot."""

    def request_cancel(self, task_id: str) -> TaskSnapshot:
        """Request task cancellation and return the resulting snapshot."""

    def subscribe(self, task_id: str, after_event_id: str | None = None) -> tuple[TaskEvent, ...]:
        """Return task events after an optional monotonic event id."""


class InMemoryTaskBackend:
    """Deterministic in-memory TaskBackend for desktop, tests, and local facades."""

    def __init__(self, *, clock: ClockFn | None = None) -> None:
        self._clock = clock or (lambda: datetime.now(UTC))
        self._lock = threading.RLock()
        self._snapshots: dict[str, TaskSnapshot] = {}
        self._events: dict[str, list[TaskEvent]] = {}
        self._idempotency_index: dict[str, str] = {}

    def submit(self, command: TaskCommand) -> TaskRef:
        with self._lock:
            if command.idempotency_key and command.idempotency_key in self._idempotency_index:
                return self._ref_for(self._idempotency_index[command.idempotency_key])

            task_id = command.task_id or uuid.uuid4().hex
            if task_id in self._snapshots:
                raise TaskAlreadyExists(f"Task already exists: {task_id}")

            submitted_at = self._clock()
            snapshot = TaskSnapshot(
                task_id=task_id,
                run_id=command.run_id,
                task_type=command.task_type,
                status=TaskStatus.QUEUED,
                submitted_at=submitted_at,
                payload=command.payload,
                message="queued",
                idempotency_key=command.idempotency_key,
                metadata=command.metadata,
            )
            self._snapshots[task_id] = snapshot
            self._events[task_id] = []
            if command.idempotency_key:
                self._idempotency_index[command.idempotency_key] = task_id
            self._append_event_locked(snapshot, "task.submitted", occurred_at=submitted_at, message="queued")
            return self._ref_for(task_id)

    def get(self, task_id: str) -> TaskSnapshot:
        with self._lock:
            return self._require_snapshot(task_id)

    def request_cancel(self, task_id: str) -> TaskSnapshot:
        with self._lock:
            snapshot = self._require_snapshot(task_id)
            if snapshot.status in TERMINAL_TASK_STATUSES:
                return snapshot

            occurred_at = self._clock()
            updated = replace(
                snapshot,
                status=TaskStatus.CANCELLED,
                completed_at=occurred_at,
                message="cancelled",
            )
            self._snapshots[task_id] = updated
            self._append_event_locked(updated, "task.cancelled", occurred_at=occurred_at, message="cancelled")
            return updated

    def subscribe(self, task_id: str, after_event_id: str | None = None) -> tuple[TaskEvent, ...]:
        with self._lock:
            self._require_snapshot(task_id)
            after = int(after_event_id) if after_event_id is not None else 0
            return tuple(event for event in self._events[task_id] if int(event.event_id) > after)

    def mark_running(self, task_id: str, *, message: str = "running") -> TaskSnapshot:
        with self._lock:
            snapshot = self._require_snapshot(task_id)
            if snapshot.status in TERMINAL_TASK_STATUSES:
                return snapshot
            occurred_at = self._clock()
            updated = replace(
                snapshot,
                status=TaskStatus.RUNNING,
                started_at=snapshot.started_at or occurred_at,
                message=message,
            )
            self._snapshots[task_id] = updated
            self._append_event_locked(updated, "task.started", occurred_at=occurred_at, message=message)
            return updated

    def complete(
        self,
        task_id: str,
        *,
        result: Mapping[str, Any] | None = None,
        message: str = "succeeded",
    ) -> TaskSnapshot:
        with self._lock:
            snapshot = self._require_snapshot(task_id)
            occurred_at = self._clock()
            updated = replace(
                snapshot,
                status=TaskStatus.SUCCEEDED,
                completed_at=occurred_at,
                result=result,
                progress=100,
                message=message,
            )
            self._snapshots[task_id] = updated
            self._append_event_locked(updated, "task.succeeded", occurred_at=occurred_at, message=message)
            return updated

    def fail(self, task_id: str, *, error: str, message: str = "failed") -> TaskSnapshot:
        with self._lock:
            snapshot = self._require_snapshot(task_id)
            occurred_at = self._clock()
            updated = replace(
                snapshot,
                status=TaskStatus.FAILED,
                completed_at=occurred_at,
                error=error,
                message=message,
            )
            self._snapshots[task_id] = updated
            self._append_event_locked(
                updated,
                "task.failed",
                occurred_at=occurred_at,
                message=message,
                payload={"error": error},
            )
            return updated

    def _ref_for(self, task_id: str) -> TaskRef:
        snapshot = self._require_snapshot(task_id)
        return TaskRef(task_id=snapshot.task_id, run_id=snapshot.run_id, status=snapshot.status)

    def _require_snapshot(self, task_id: str) -> TaskSnapshot:
        try:
            return self._snapshots[task_id]
        except KeyError as exc:
            raise TaskNotFound(f"Task not found: {task_id}") from exc

    def _append_event_locked(
        self,
        snapshot: TaskSnapshot,
        kind: str,
        *,
        occurred_at: datetime,
        message: str | None = None,
        payload: Mapping[str, Any] | None = None,
    ) -> TaskEvent:
        event = TaskEvent(
            event_id=str(len(self._events[snapshot.task_id]) + 1),
            task_id=snapshot.task_id,
            run_id=snapshot.run_id,
            kind=kind,
            occurred_at=occurred_at,
            status=snapshot.status,
            message=message,
            payload=payload or {},
        )
        self._events[snapshot.task_id].append(event)
        return event


def task_status_from_legacy(value: str) -> TaskStatus:
    aliases = {
        "pending": TaskStatus.QUEUED,
        "queued": TaskStatus.QUEUED,
        "processing": TaskStatus.RUNNING,
        "running": TaskStatus.RUNNING,
        "completed": TaskStatus.SUCCEEDED,
        "succeeded": TaskStatus.SUCCEEDED,
        "failed": TaskStatus.FAILED,
        "cancel_requested": TaskStatus.CANCEL_REQUESTED,
        "cancelled": TaskStatus.CANCELLED,
    }
    try:
        return aliases[value]
    except KeyError as exc:
        raise TaskBackendError(f"Unknown legacy task status: {value}") from exc
