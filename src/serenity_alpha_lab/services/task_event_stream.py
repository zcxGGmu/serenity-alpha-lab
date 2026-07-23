from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from serenity_alpha_lab.application.api_errors import ValidationProblem
from serenity_alpha_lab.application.task_backend import TaskBackend, TaskBackendCapabilityError, TaskEvent
from serenity_alpha_lab.application.tracing import TraceContext, current_trace_context, redact_sensitive_data
from serenity_alpha_lab.domain.run_lifecycle import RunEvent


@dataclass(frozen=True, slots=True)
class ServerSentEvent:
    id: str
    event: str
    data: Mapping[str, Any]
    retry_ms: int | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "data", dict(self.data))

    def encode(self) -> str:
        payload = json.dumps(dict(self.data), sort_keys=True, default=str)
        lines = [f"id: {self.id}", f"event: {self.event}"]
        if self.retry_ms is not None:
            lines.append(f"retry: {self.retry_ms}")
        lines.append(f"data: {payload}")
        return "\n".join(lines) + "\n\n"


@dataclass(frozen=True, slots=True)
class TaskEventReconcilerSummary:
    stalled_tasks_requeued: int = 0
    queued_orphans_redispatched: int = 0
    temporary_artifacts_removed: int = 0
    problems: tuple[str, ...] = field(default_factory=tuple)


class TaskEventStreamService:
    """Framework-neutral recoverable task and run event stream adapter."""

    def __init__(self, *, task_backend: TaskBackend) -> None:
        self._task_backend = task_backend

    def task_events(
        self,
        task_id: str,
        *,
        last_event_id: str | None = None,
        trace_context: TraceContext | None = None,
        retry_ms: int | None = None,
    ) -> tuple[ServerSentEvent, ...]:
        after_event_id = parse_last_event_id(last_event_id)
        events = self._task_backend.subscribe(task_id, after_event_id=after_event_id)
        return tuple(
            _task_event_to_sse(event, trace_context=trace_context, retry_ms=retry_ms)
            for event in events
        )

    def run_events(
        self,
        run_id: str,
        *,
        last_event_id: str | None = None,
        trace_context: TraceContext | None = None,
        retry_ms: int | None = None,
    ) -> tuple[ServerSentEvent, ...]:
        after_event_id = parse_last_event_id(last_event_id)
        subscriber = getattr(self._task_backend, "subscribe_run_events", None)
        if subscriber is None:
            raise TaskBackendCapabilityError("Task backend does not expose persisted RunEvent stream")
        events = subscriber(run_id, after_event_id=after_event_id)
        return tuple(
            _run_event_to_sse(event, trace_context=trace_context, retry_ms=retry_ms)
            for event in events
        )


class TaskEventReconciler:
    """Recover queued/running task delivery state without executing task handlers."""

    def __init__(
        self,
        *,
        backend: Any,
        artifact_tmp_roots: Sequence[str | Path] = (),
    ) -> None:
        self._backend = backend
        self._artifact_tmp_roots = tuple(Path(root) for root in artifact_tmp_roots)

    def reconcile(
        self,
        *,
        now: datetime,
        queued_orphan_age_seconds: int,
        temporary_artifact_age_seconds: int | None = None,
        worker_id: str = "reconciler",
    ) -> TaskEventReconcilerSummary:
        occurred_at = _require_aware_datetime("now", now)
        problems: list[str] = []
        queued_orphans_redispatched = 0
        stalled_tasks_requeued = 0

        redispatch = getattr(self._backend, "redispatch_queued_orphans", None)
        if redispatch is not None:
            try:
                queued_orphans_redispatched = int(
                    redispatch(
                        now=occurred_at,
                        orphan_age_seconds=queued_orphan_age_seconds,
                        worker_id=worker_id,
                    )
                )
            except Exception as exc:  # pragma: no cover - defensive path for deployment routers.
                problems.append(f"queued orphan redispatch failed: {exc.__class__.__name__}")
        else:
            problems.append("backend does not support queued orphan redispatch")

        requeue = getattr(self._backend, "requeue_expired_leases", None)
        if requeue is not None:
            try:
                stalled_tasks_requeued = int(requeue(now=occurred_at, worker_id=worker_id))
            except Exception as exc:  # pragma: no cover - defensive path for deployment repositories.
                problems.append(f"stalled lease requeue failed: {exc.__class__.__name__}")
        else:
            problems.append("backend does not support stalled lease reconciliation")

        temporary_artifacts_removed = 0
        if temporary_artifact_age_seconds is not None:
            if temporary_artifact_age_seconds < 0:
                raise ValidationProblem("temporary_artifact_age_seconds must be non-negative")
            temporary_artifacts_removed = self._cleanup_temporary_artifacts(
                now=occurred_at,
                max_age_seconds=temporary_artifact_age_seconds,
                problems=problems,
            )

        return TaskEventReconcilerSummary(
            stalled_tasks_requeued=stalled_tasks_requeued,
            queued_orphans_redispatched=queued_orphans_redispatched,
            temporary_artifacts_removed=temporary_artifacts_removed,
            problems=tuple(problems),
        )

    def _cleanup_temporary_artifacts(
        self,
        *,
        now: datetime,
        max_age_seconds: int,
        problems: list[str],
    ) -> int:
        cutoff_timestamp = now.timestamp() - max_age_seconds
        removed = 0
        for root in self._artifact_tmp_roots:
            if not root.exists():
                continue
            for path in sorted(root.rglob("*")):
                if not path.is_file():
                    continue
                try:
                    if path.stat().st_mtime < cutoff_timestamp:
                        path.unlink()
                        removed += 1
                except OSError as exc:  # pragma: no cover - filesystem race protection.
                    problems.append(f"temporary artifact cleanup failed: {path.name}:{exc.__class__.__name__}")
        return removed


def parse_last_event_id(value: str | None) -> str | None:
    if value is None:
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ValidationProblem("Last-Event-ID must be a non-negative integer") from exc
    if parsed < 0 or str(parsed) != value:
        raise ValidationProblem("Last-Event-ID must be a non-negative integer")
    return str(parsed)


def _task_event_to_sse(
    event: TaskEvent,
    *,
    trace_context: TraceContext | None,
    retry_ms: int | None,
) -> ServerSentEvent:
    context = trace_context or current_trace_context()
    data: dict[str, Any] = {
        "task_id": event.task_id,
        "run_id": event.run_id,
        "kind": event.kind,
        "status": event.status.value,
        "message": event.message,
        "occurred_at": event.occurred_at.isoformat(),
        "payload": redact_sensitive_data(dict(event.payload)),
    }
    if context is not None:
        data["trace_id"] = context.trace_id
    return ServerSentEvent(
        id=event.event_id,
        event=event.kind,
        data=data,
        retry_ms=retry_ms,
    )


def _run_event_to_sse(
    event: RunEvent,
    *,
    trace_context: TraceContext | None,
    retry_ms: int | None,
) -> ServerSentEvent:
    context = trace_context or current_trace_context()
    data: dict[str, Any] = {
        "run_id": event.run_id,
        "kind": event.kind.value,
        "message": event.message,
        "occurred_at": event.occurred_at.isoformat(),
        "stage_id": event.stage_id,
    }
    if context is not None:
        data["trace_id"] = context.trace_id
    return ServerSentEvent(
        id=str(event.sequence),
        event=event.kind.value,
        data=data,
        retry_ms=retry_ms,
    )


def _require_aware_datetime(field_name: str, value: datetime) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise ValidationProblem(f"{field_name} must be timezone-aware")
    return value.astimezone(UTC)


__all__ = [
    "ServerSentEvent",
    "TaskEventReconciler",
    "TaskEventReconcilerSummary",
    "TaskEventStreamService",
    "parse_last_event_id",
]
