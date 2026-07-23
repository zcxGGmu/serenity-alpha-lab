from __future__ import annotations

import json
import uuid
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any, Protocol

from sqlalchemy import (
    Column,
    Integer,
    MetaData,
    PrimaryKeyConstraint,
    String,
    Table,
    UniqueConstraint,
    and_,
    func,
    insert,
    select,
    update,
)
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.types import JSON

from serenity_alpha_lab.application.task_backend import (
    TERMINAL_TASK_STATUSES,
    TaskAlreadyExists,
    TaskBackendCapabilityError,
    TaskBackendError,
    TaskCommand,
    TaskEvent,
    TaskNotFound,
    TaskRef,
    TaskSnapshot,
    TaskStatus,
)
from serenity_alpha_lab.domain.run_lifecycle import EventKind, RunEvent


ClockFn = Callable[[], datetime]


class TaskQueueRouter(Protocol):
    """Infrastructure adapter that dispatches a persisted task reference to a queue."""

    def enqueue(
        self,
        command: TaskCommand,
        *,
        task_id: str,
        queue_name: str,
        routing_key: str,
    ) -> str | None:
        """Send a small task reference to the queue and return provider message id when available."""


@dataclass(frozen=True, slots=True)
class TaskQueueRoute:
    task_type: str
    queue_name: str
    routing_key: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "task_type", _required_string("task_type", self.task_type))
        object.__setattr__(self, "queue_name", _required_string("queue_name", self.queue_name))
        object.__setattr__(self, "routing_key", _required_string("routing_key", self.routing_key))


@dataclass(frozen=True, slots=True)
class TaskLease:
    task_id: str
    run_id: str
    task_type: str
    queue_name: str
    routing_key: str
    worker_id: str
    lease_expires_at: datetime
    snapshot: TaskSnapshot


class CeleryTaskQueueRouter:
    """Queue router for an injected Celery app.

    Celery and Redis remain infrastructure choices configured by the caller. This adapter only
    needs an object exposing Celery's `send_task(...)` shape, which keeps the application layer
    free from Celery imports while still exercising queue routing in tests.
    """

    def __init__(self, celery_app: Any, *, task_name: str) -> None:
        self._celery_app = celery_app
        self._task_name = _required_string("task_name", task_name)

    def enqueue(
        self,
        command: TaskCommand,
        *,
        task_id: str,
        queue_name: str,
        routing_key: str,
    ) -> str | None:
        result = self._celery_app.send_task(
            self._task_name,
            args=[task_id],
            kwargs={
                "task_id": task_id,
                "run_id": command.run_id,
                "task_type": command.task_type,
            },
            queue=queue_name,
            routing_key=routing_key,
            task_id=task_id,
        )
        message_id = getattr(result, "id", None)
        return str(message_id) if message_id is not None else None


class NoopTaskQueueRouter:
    """Deterministic router used when a caller wants persistence without external dispatch."""

    def enqueue(
        self,
        command: TaskCommand,
        *,
        task_id: str,
        queue_name: str,
        routing_key: str,
    ) -> str | None:
        return None


_TASK_METADATA = MetaData()

_TASK_RUNS_TABLE = Table(
    "serenity_task_backend_runs",
    _TASK_METADATA,
    Column("task_id", String(96), primary_key=True),
    Column("run_id", String(128), nullable=False),
    Column("task_type", String(160), nullable=False),
    Column("status", String(32), nullable=False),
    Column("submitted_at_utc", String(40), nullable=False),
    Column("started_at_utc", String(40), nullable=True),
    Column("completed_at_utc", String(40), nullable=True),
    Column("payload_json", JSON(), nullable=False),
    Column("progress", Integer(), nullable=False),
    Column("message", String(1024), nullable=True),
    Column("result_json", JSON(), nullable=True),
    Column("error", String(2048), nullable=True),
    Column("idempotency_key", String(255), nullable=True),
    Column("metadata_json", JSON(), nullable=False),
    Column("queue_name", String(80), nullable=False),
    Column("routing_key", String(160), nullable=False),
    Column("queue_message_id", String(255), nullable=True),
    Column("lease_owner", String(160), nullable=True),
    Column("lease_expires_at_utc", String(40), nullable=True),
    Column("heartbeat_at_utc", String(40), nullable=True),
    Column("attempt", Integer(), nullable=False),
    UniqueConstraint("idempotency_key", name="uq_serenity_task_backend_runs_idempotency_key"),
)

_TASK_EVENTS_TABLE = Table(
    "serenity_task_backend_events",
    _TASK_METADATA,
    Column("task_id", String(96), nullable=False),
    Column("sequence", Integer(), nullable=False),
    Column("run_id", String(128), nullable=False),
    Column("kind", String(160), nullable=False),
    Column("occurred_at_utc", String(40), nullable=False),
    Column("status", String(32), nullable=False),
    Column("message", String(1024), nullable=True),
    Column("payload_json", JSON(), nullable=False),
    PrimaryKeyConstraint("task_id", "sequence", name="pk_serenity_task_backend_events"),
)

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


class PersistentTaskBackend:
    """SQLAlchemy-backed TaskBackend with database-authoritative task state."""

    def __init__(
        self,
        engine: Engine,
        *,
        queue_router: TaskQueueRouter | None = None,
        routes: Sequence[TaskQueueRoute] = (),
        default_route: TaskQueueRoute | None = None,
        clock: ClockFn | None = None,
    ) -> None:
        self._engine = engine
        self._queue_router = queue_router or NoopTaskQueueRouter()
        self._routes = {route.task_type: route for route in routes}
        self._default_route = default_route or TaskQueueRoute(
            task_type="*",
            queue_name="default",
            routing_key="default",
        )
        self._clock = clock or (lambda: datetime.now(UTC))

    def create_schema(self) -> None:
        _TASK_METADATA.create_all(
            self._engine,
            tables=[_TASK_RUNS_TABLE, _TASK_EVENTS_TABLE, _RUN_EVENTS_TABLE],
        )

    def submit(self, command: TaskCommand) -> TaskRef:
        task_id = command.task_id or uuid.uuid4().hex
        route = self._route_for(command.task_type)
        now = self._now()

        with self._engine.begin() as connection:
            if command.idempotency_key:
                existing = self._row_by_idempotency_key(connection, command.idempotency_key)
                if existing is not None:
                    return _ref_from_row(existing)

            if self._row_by_task_id(connection, task_id) is not None:
                raise TaskAlreadyExists(f"Task already exists: {task_id}")

            values = {
                "task_id": task_id,
                "run_id": command.run_id,
                "task_type": command.task_type,
                "status": TaskStatus.QUEUED.value,
                "submitted_at_utc": _datetime_to_record(now),
                "started_at_utc": None,
                "completed_at_utc": None,
                "payload_json": _normalize_json_value(command.payload),
                "progress": 0,
                "message": "queued",
                "result_json": None,
                "error": None,
                "idempotency_key": command.idempotency_key,
                "metadata_json": _normalize_json_value(command.metadata),
                "queue_name": route.queue_name,
                "routing_key": route.routing_key,
                "queue_message_id": None,
                "lease_owner": None,
                "lease_expires_at_utc": None,
                "heartbeat_at_utc": None,
                "attempt": 0,
            }
            try:
                connection.execute(insert(_TASK_RUNS_TABLE).values(**values))
            except IntegrityError as exc:
                raise TaskAlreadyExists(f"Task already exists: {task_id}") from exc
            self._append_event(
                connection,
                task_id=task_id,
                run_id=command.run_id,
                kind="task.submitted",
                occurred_at=now,
                status=TaskStatus.QUEUED,
                message="queued",
                payload={"queue_name": route.queue_name, "routing_key": route.routing_key},
            )

        try:
            queue_message_id = self._queue_router.enqueue(
                command,
                task_id=task_id,
                queue_name=route.queue_name,
                routing_key=route.routing_key,
            )
        except Exception as exc:  # pragma: no cover - defensive path covered by behavior callers.
            self._record_dispatch_failure(task_id, exc)
            raise TaskBackendCapabilityError(f"Task queue dispatch failed: {exc.__class__.__name__}") from exc

        if queue_message_id:
            with self._engine.begin() as connection:
                connection.execute(
                    update(_TASK_RUNS_TABLE)
                    .where(_TASK_RUNS_TABLE.c.task_id == task_id)
                    .values(queue_message_id=queue_message_id)
                )

        return TaskRef(task_id=task_id, run_id=command.run_id, status=TaskStatus.QUEUED)

    def get(self, task_id: str) -> TaskSnapshot:
        with self._engine.connect() as connection:
            row = self._require_row_by_task_id(connection, task_id)
        return _snapshot_from_row(row)

    def request_cancel(self, task_id: str) -> TaskSnapshot:
        now = self._now()
        with self._engine.begin() as connection:
            row = self._require_row_by_task_id(connection, task_id)
            snapshot = _snapshot_from_row(row)
            if snapshot.status in TERMINAL_TASK_STATUSES or snapshot.status is TaskStatus.CANCEL_REQUESTED:
                return snapshot

            connection.execute(
                update(_TASK_RUNS_TABLE)
                .where(_TASK_RUNS_TABLE.c.task_id == task_id)
                .values(
                    status=TaskStatus.CANCEL_REQUESTED.value,
                    message="cancel requested",
                    heartbeat_at_utc=_datetime_to_record(now),
                )
            )
            self._append_event(
                connection,
                task_id=task_id,
                run_id=snapshot.run_id,
                kind="task.cancel_requested",
                occurred_at=now,
                status=TaskStatus.CANCEL_REQUESTED,
                message="cancel requested",
            )
            return _snapshot_from_row(self._require_row_by_task_id(connection, task_id))

    def subscribe(self, task_id: str, after_event_id: str | None = None) -> tuple[TaskEvent, ...]:
        after = int(after_event_id) if after_event_id is not None else 0
        with self._engine.connect() as connection:
            self._require_row_by_task_id(connection, task_id)
            rows = (
                connection.execute(
                    select(_TASK_EVENTS_TABLE)
                    .where(
                        and_(
                            _TASK_EVENTS_TABLE.c.task_id == task_id,
                            _TASK_EVENTS_TABLE.c.sequence > after,
                        )
                    )
                    .order_by(_TASK_EVENTS_TABLE.c.sequence)
                )
                .mappings()
                .all()
            )
        return tuple(_event_from_row(row) for row in rows)

    def record_run_event(self, event: RunEvent) -> RunEvent:
        values = _run_event_to_record(event)
        with self._engine.begin() as connection:
            existing = self._run_event_row(connection, event.run_id, event.sequence)
            if existing is not None:
                persisted = _run_event_from_row(existing)
                if persisted == event:
                    return persisted
                raise TaskBackendCapabilityError(
                    f"Run event sequence conflict: {event.run_id}:{event.sequence}"
                )
            try:
                connection.execute(insert(_RUN_EVENTS_TABLE).values(**values))
            except IntegrityError as exc:
                raise TaskBackendCapabilityError(
                    f"Run event sequence conflict: {event.run_id}:{event.sequence}"
                ) from exc
        return event

    def subscribe_run_events(self, run_id: str, after_event_id: str | None = None) -> tuple[RunEvent, ...]:
        after = int(after_event_id) if after_event_id is not None else 0
        normalized_run_id = _required_string("run_id", run_id)
        with self._engine.connect() as connection:
            rows = (
                connection.execute(
                    select(_RUN_EVENTS_TABLE)
                    .where(
                        and_(
                            _RUN_EVENTS_TABLE.c.run_id == normalized_run_id,
                            _RUN_EVENTS_TABLE.c.sequence > after,
                        )
                    )
                    .order_by(_RUN_EVENTS_TABLE.c.sequence)
                )
                .mappings()
                .all()
            )
        return tuple(_run_event_from_row(row) for row in rows)

    def acquire_next(
        self,
        *,
        worker_id: str,
        queues: Sequence[str],
        lease_seconds: int,
    ) -> TaskLease | None:
        worker = _required_string("worker_id", worker_id)
        queue_names = tuple(_required_string("queue", queue) for queue in queues)
        if not queue_names:
            raise TaskBackendError("at least one queue is required")
        if lease_seconds <= 0:
            raise TaskBackendError("lease_seconds must be positive")

        now = self._now()
        lease_expires_at = now + timedelta(seconds=lease_seconds)
        with self._engine.begin() as connection:
            row = (
                connection.execute(
                    select(_TASK_RUNS_TABLE)
                    .where(
                        and_(
                            _TASK_RUNS_TABLE.c.status == TaskStatus.QUEUED.value,
                            _TASK_RUNS_TABLE.c.queue_name.in_(queue_names),
                        )
                    )
                    .order_by(_TASK_RUNS_TABLE.c.submitted_at_utc, _TASK_RUNS_TABLE.c.task_id)
                    .limit(1)
                )
                .mappings()
                .one_or_none()
            )
            if row is None:
                return None

            connection.execute(
                update(_TASK_RUNS_TABLE)
                .where(_TASK_RUNS_TABLE.c.task_id == row["task_id"])
                .values(
                    status=TaskStatus.RUNNING.value,
                    started_at_utc=row["started_at_utc"] or _datetime_to_record(now),
                    message="running",
                    lease_owner=worker,
                    lease_expires_at_utc=_datetime_to_record(lease_expires_at),
                    heartbeat_at_utc=_datetime_to_record(now),
                    attempt=int(row["attempt"]) + 1,
                )
            )
            self._append_event(
                connection,
                task_id=str(row["task_id"]),
                run_id=str(row["run_id"]),
                kind="task.started",
                occurred_at=now,
                status=TaskStatus.RUNNING,
                message="running",
                payload={"worker_id": worker, "lease_expires_at": lease_expires_at.isoformat()},
            )
            updated = self._require_row_by_task_id(connection, str(row["task_id"]))
        return _lease_from_row(updated, worker_id=worker)

    def heartbeat(self, task_id: str, *, worker_id: str, lease_seconds: int) -> TaskSnapshot:
        worker = _required_string("worker_id", worker_id)
        if lease_seconds <= 0:
            raise TaskBackendError("lease_seconds must be positive")
        now = self._now()
        lease_expires_at = now + timedelta(seconds=lease_seconds)
        with self._engine.begin() as connection:
            row = self._require_leased_row(connection, task_id, worker_id=worker)
            connection.execute(
                update(_TASK_RUNS_TABLE)
                .where(_TASK_RUNS_TABLE.c.task_id == task_id)
                .values(
                    lease_expires_at_utc=_datetime_to_record(lease_expires_at),
                    heartbeat_at_utc=_datetime_to_record(now),
                    message="running",
                )
            )
            self._append_event(
                connection,
                task_id=task_id,
                run_id=str(row["run_id"]),
                kind="task.heartbeat",
                occurred_at=now,
                status=TaskStatus.RUNNING,
                message="heartbeat",
                payload={"worker_id": worker, "lease_expires_at": lease_expires_at.isoformat()},
            )
            return _snapshot_from_row(self._require_row_by_task_id(connection, task_id))

    def complete(
        self,
        task_id: str,
        *,
        worker_id: str,
        result: Mapping[str, Any] | None = None,
        message: str = "succeeded",
    ) -> TaskSnapshot:
        worker = _required_string("worker_id", worker_id)
        now = self._now()
        with self._engine.begin() as connection:
            row = self._require_leased_row(connection, task_id, worker_id=worker)
            connection.execute(
                update(_TASK_RUNS_TABLE)
                .where(_TASK_RUNS_TABLE.c.task_id == task_id)
                .values(
                    status=TaskStatus.SUCCEEDED.value,
                    completed_at_utc=_datetime_to_record(now),
                    progress=100,
                    result_json=_normalize_json_value(result) if result is not None else None,
                    message=message,
                    error=None,
                    lease_owner=None,
                    lease_expires_at_utc=None,
                    heartbeat_at_utc=_datetime_to_record(now),
                )
            )
            self._append_event(
                connection,
                task_id=task_id,
                run_id=str(row["run_id"]),
                kind="task.succeeded",
                occurred_at=now,
                status=TaskStatus.SUCCEEDED,
                message=message,
                payload={"worker_id": worker},
            )
            return _snapshot_from_row(self._require_row_by_task_id(connection, task_id))

    def fail(self, task_id: str, *, worker_id: str, error: str, message: str = "failed") -> TaskSnapshot:
        worker = _required_string("worker_id", worker_id)
        now = self._now()
        with self._engine.begin() as connection:
            row = self._require_leased_row(connection, task_id, worker_id=worker)
            connection.execute(
                update(_TASK_RUNS_TABLE)
                .where(_TASK_RUNS_TABLE.c.task_id == task_id)
                .values(
                    status=TaskStatus.FAILED.value,
                    completed_at_utc=_datetime_to_record(now),
                    error=_required_string("error", error),
                    message=message,
                    lease_owner=None,
                    lease_expires_at_utc=None,
                    heartbeat_at_utc=_datetime_to_record(now),
                )
            )
            self._append_event(
                connection,
                task_id=task_id,
                run_id=str(row["run_id"]),
                kind="task.failed",
                occurred_at=now,
                status=TaskStatus.FAILED,
                message=message,
                payload={"worker_id": worker, "error": error},
            )
            return _snapshot_from_row(self._require_row_by_task_id(connection, task_id))

    def requeue_expired_leases(self, *, now: datetime, worker_id: str = "reconciler") -> int:
        cutoff = _datetime_to_record(_require_aware_datetime("now", now))
        reconciler = _required_string("worker_id", worker_id)
        requeued = 0
        with self._engine.begin() as connection:
            rows = (
                connection.execute(
                    select(_TASK_RUNS_TABLE)
                    .where(
                        and_(
                            _TASK_RUNS_TABLE.c.status == TaskStatus.RUNNING.value,
                            _TASK_RUNS_TABLE.c.lease_expires_at_utc.is_not(None),
                            _TASK_RUNS_TABLE.c.lease_expires_at_utc < cutoff,
                        )
                    )
                    .order_by(_TASK_RUNS_TABLE.c.lease_expires_at_utc, _TASK_RUNS_TABLE.c.task_id)
                )
                .mappings()
                .all()
            )
            for row in rows:
                task_id = str(row["task_id"])
                connection.execute(
                    update(_TASK_RUNS_TABLE)
                    .where(_TASK_RUNS_TABLE.c.task_id == task_id)
                    .values(
                        status=TaskStatus.QUEUED.value,
                        message="requeued",
                        lease_owner=None,
                        lease_expires_at_utc=None,
                        heartbeat_at_utc=cutoff,
                    )
                )
                self._append_event(
                    connection,
                    task_id=task_id,
                    run_id=str(row["run_id"]),
                    kind="task.requeued",
                    occurred_at=now,
                    status=TaskStatus.QUEUED,
                    message="requeued",
                    payload={"worker_id": reconciler, "previous_worker_id": row["lease_owner"]},
                )
                requeued += 1
        return requeued

    def redispatch_queued_orphans(
        self,
        *,
        now: datetime,
        orphan_age_seconds: int,
        worker_id: str = "reconciler",
    ) -> int:
        if orphan_age_seconds < 0:
            raise TaskBackendError("orphan_age_seconds must be non-negative")
        occurred_at = _require_aware_datetime("now", now)
        cutoff = _datetime_to_record(occurred_at - timedelta(seconds=orphan_age_seconds))
        reconciler = _required_string("worker_id", worker_id)
        with self._engine.connect() as connection:
            rows = (
                connection.execute(
                    select(_TASK_RUNS_TABLE)
                    .where(
                        and_(
                            _TASK_RUNS_TABLE.c.status == TaskStatus.QUEUED.value,
                            _TASK_RUNS_TABLE.c.submitted_at_utc <= cutoff,
                        )
                    )
                    .order_by(_TASK_RUNS_TABLE.c.submitted_at_utc, _TASK_RUNS_TABLE.c.task_id)
                )
                .mappings()
                .all()
            )

        redispatched = 0
        for row in rows:
            task_id = str(row["task_id"])
            command = _command_from_row(row)
            try:
                queue_message_id = self._queue_router.enqueue(
                    command,
                    task_id=task_id,
                    queue_name=str(row["queue_name"]),
                    routing_key=str(row["routing_key"]),
                )
            except Exception as exc:  # pragma: no cover - defensive path depends on caller router.
                with self._engine.begin() as connection:
                    current = self._row_by_task_id(connection, task_id)
                    if current is not None and TaskStatus(str(current["status"])) is TaskStatus.QUEUED:
                        self._append_event(
                            connection,
                            task_id=task_id,
                            run_id=str(row["run_id"]),
                            kind="task.redispatch_failed",
                            occurred_at=occurred_at,
                            status=TaskStatus.QUEUED,
                            message="redispatch failed",
                            payload={"worker_id": reconciler, "error": exc.__class__.__name__},
                        )
                continue

            with self._engine.begin() as connection:
                current = self._row_by_task_id(connection, task_id)
                if current is None or TaskStatus(str(current["status"])) is not TaskStatus.QUEUED:
                    continue
                values: dict[str, Any] = {"heartbeat_at_utc": _datetime_to_record(occurred_at)}
                if queue_message_id:
                    values["queue_message_id"] = queue_message_id
                connection.execute(
                    update(_TASK_RUNS_TABLE)
                    .where(_TASK_RUNS_TABLE.c.task_id == task_id)
                    .values(**values)
                )
                self._append_event(
                    connection,
                    task_id=task_id,
                    run_id=str(row["run_id"]),
                    kind="task.redispatched",
                    occurred_at=occurred_at,
                    status=TaskStatus.QUEUED,
                    message="redispatched",
                    payload={"worker_id": reconciler, "queue_message_id": queue_message_id},
                )
                redispatched += 1
        return redispatched

    def _route_for(self, task_type: str) -> TaskQueueRoute:
        return self._routes.get(task_type) or self._default_route

    def _now(self) -> datetime:
        return _require_aware_datetime("clock", self._clock())

    def _row_by_idempotency_key(self, connection: Connection, idempotency_key: str) -> Mapping[str, Any] | None:
        return (
            connection.execute(
                select(_TASK_RUNS_TABLE).where(
                    _TASK_RUNS_TABLE.c.idempotency_key == _required_string("idempotency_key", idempotency_key)
                )
            )
            .mappings()
            .one_or_none()
        )

    def _row_by_task_id(self, connection: Connection, task_id: str) -> Mapping[str, Any] | None:
        return (
            connection.execute(
                select(_TASK_RUNS_TABLE).where(_TASK_RUNS_TABLE.c.task_id == _required_string("task_id", task_id))
            )
            .mappings()
            .one_or_none()
        )

    def _require_row_by_task_id(self, connection: Connection, task_id: str) -> Mapping[str, Any]:
        row = self._row_by_task_id(connection, task_id)
        if row is None:
            raise TaskNotFound(f"Task not found: {task_id}")
        return row

    def _require_leased_row(self, connection: Connection, task_id: str, *, worker_id: str) -> Mapping[str, Any]:
        row = self._require_row_by_task_id(connection, task_id)
        if TaskStatus(str(row["status"])) is not TaskStatus.RUNNING:
            raise TaskBackendCapabilityError(f"Task is not running: {task_id}")
        if row["lease_owner"] != worker_id:
            raise TaskBackendCapabilityError(f"Task lease is owned by another worker: {task_id}")
        return row

    def _append_event(
        self,
        connection: Connection,
        *,
        task_id: str,
        run_id: str,
        kind: str,
        occurred_at: datetime,
        status: TaskStatus,
        message: str | None = None,
        payload: Mapping[str, Any] | None = None,
    ) -> TaskEvent:
        next_sequence = (
            connection.execute(
                select(func.coalesce(func.max(_TASK_EVENTS_TABLE.c.sequence), 0) + 1).where(
                    _TASK_EVENTS_TABLE.c.task_id == task_id
                )
            ).scalar_one()
            or 1
        )
        values = {
            "task_id": task_id,
            "sequence": int(next_sequence),
            "run_id": run_id,
            "kind": _required_string("kind", kind),
            "occurred_at_utc": _datetime_to_record(occurred_at),
            "status": status.value,
            "message": message,
            "payload_json": _normalize_json_value(payload or {}),
        }
        connection.execute(insert(_TASK_EVENTS_TABLE).values(**values))
        return _event_from_row(values)

    def _record_dispatch_failure(self, task_id: str, exc: Exception) -> None:
        now = self._now()
        with self._engine.begin() as connection:
            row = self._require_row_by_task_id(connection, task_id)
            message = f"queue dispatch failed: {exc.__class__.__name__}"
            connection.execute(
                update(_TASK_RUNS_TABLE)
                .where(_TASK_RUNS_TABLE.c.task_id == task_id)
                .values(
                    status=TaskStatus.FAILED.value,
                    completed_at_utc=_datetime_to_record(now),
                    error=message,
                    message=message,
                )
            )
            self._append_event(
                connection,
                task_id=task_id,
                run_id=str(row["run_id"]),
                kind="task.dispatch_failed",
                occurred_at=now,
                status=TaskStatus.FAILED,
                message=message,
            )

    def _run_event_row(self, connection: Connection, run_id: str, sequence: int) -> Mapping[str, Any] | None:
        return (
            connection.execute(
                select(_RUN_EVENTS_TABLE).where(
                    and_(
                        _RUN_EVENTS_TABLE.c.run_id == _required_string("run_id", run_id),
                        _RUN_EVENTS_TABLE.c.sequence == int(sequence),
                    )
                )
            )
            .mappings()
            .one_or_none()
        )


def _ref_from_row(row: Mapping[str, Any]) -> TaskRef:
    return TaskRef(task_id=str(row["task_id"]), run_id=str(row["run_id"]), status=TaskStatus(str(row["status"])))


def _snapshot_from_row(row: Mapping[str, Any]) -> TaskSnapshot:
    return TaskSnapshot(
        task_id=str(row["task_id"]),
        run_id=str(row["run_id"]),
        task_type=str(row["task_type"]),
        status=TaskStatus(str(row["status"])),
        submitted_at=_datetime_from_record(row["submitted_at_utc"]),
        payload=_json_mapping(row["payload_json"]),
        progress=int(row["progress"]),
        message=row["message"],
        started_at=_optional_datetime(row["started_at_utc"]),
        completed_at=_optional_datetime(row["completed_at_utc"]),
        result=_json_mapping(row["result_json"]) if row["result_json"] is not None else None,
        error=row["error"],
        idempotency_key=row["idempotency_key"],
        metadata=_json_mapping(row["metadata_json"]),
    )


def _lease_from_row(row: Mapping[str, Any], *, worker_id: str) -> TaskLease:
    return TaskLease(
        task_id=str(row["task_id"]),
        run_id=str(row["run_id"]),
        task_type=str(row["task_type"]),
        queue_name=str(row["queue_name"]),
        routing_key=str(row["routing_key"]),
        worker_id=worker_id,
        lease_expires_at=_datetime_from_record(row["lease_expires_at_utc"]),
        snapshot=_snapshot_from_row(row),
    )


def _event_from_row(row: Mapping[str, Any]) -> TaskEvent:
    return TaskEvent(
        event_id=str(row["sequence"]),
        task_id=str(row["task_id"]),
        run_id=str(row["run_id"]),
        kind=str(row["kind"]),
        occurred_at=_datetime_from_record(row["occurred_at_utc"]),
        status=TaskStatus(str(row["status"])),
        message=row["message"],
        payload=_json_mapping(row["payload_json"]),
    )


def _run_event_to_record(event: RunEvent) -> dict[str, Any]:
    return {
        "run_id": _required_string("run_id", event.run_id),
        "sequence": int(event.sequence),
        "kind": event.kind.value,
        "occurred_at_utc": _datetime_to_record(event.occurred_at),
        "message": event.message,
        "stage_id": event.stage_id,
    }


def _run_event_from_row(row: Mapping[str, Any]) -> RunEvent:
    return RunEvent(
        run_id=str(row["run_id"]),
        sequence=int(row["sequence"]),
        kind=EventKind(str(row["kind"])),
        occurred_at=_datetime_from_record(row["occurred_at_utc"]),
        message=str(row["message"]),
        stage_id=row["stage_id"],
    )


def _command_from_row(row: Mapping[str, Any]) -> TaskCommand:
    return TaskCommand(
        run_id=str(row["run_id"]),
        task_type=str(row["task_type"]),
        payload=_json_mapping(row["payload_json"]),
        idempotency_key=row["idempotency_key"],
        task_id=str(row["task_id"]),
        metadata=_json_mapping(row["metadata_json"]),
    )


def _json_mapping(value: Any) -> Mapping[str, Any]:
    if value is None:
        return {}
    if isinstance(value, str):
        loaded = json.loads(value)
        return dict(loaded)
    return dict(value)


def _required_string(field_name: str, value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise TaskBackendError(f"{field_name} is required")
    return value


def _require_aware_datetime(field_name: str, value: datetime) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise TaskBackendError(f"{field_name} must be timezone-aware")
    return value.astimezone(UTC)


def _datetime_to_record(value: datetime) -> str:
    return _require_aware_datetime("datetime", value).isoformat()


def _datetime_from_record(value: Any) -> datetime:
    return datetime.fromisoformat(str(value)).astimezone(UTC)


def _optional_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    return _datetime_from_record(value)


def _normalize_json_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, datetime):
        return _require_aware_datetime("datetime", value).isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Mapping):
        return {str(key): _normalize_json_value(item) for key, item in value.items()}
    if isinstance(value, tuple | list):
        return [_normalize_json_value(item) for item in value]
    return value


__all__ = [
    "CeleryTaskQueueRouter",
    "NoopTaskQueueRouter",
    "PersistentTaskBackend",
    "TaskLease",
    "TaskQueueRoute",
    "TaskQueueRouter",
]
