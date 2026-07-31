from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Callable, Mapping

from serenity_alpha_lab.application.task_backend import (
    TaskBackendCapabilityError,
    TaskCommand,
    TaskEvent,
    TaskNotFound,
    TaskRef,
    TaskSnapshot,
    task_status_from_legacy,
)


TaskHandler = Callable[[TaskCommand], Any]


class DsaAnalysisTaskQueueBackend:
    """TaskBackend facade for an injected DSA AnalysisTaskQueue-like object."""

    def __init__(self, queue: Any, *, handlers: Mapping[str, TaskHandler]) -> None:
        self._queue = queue
        self._handlers = dict(handlers)
        self._commands_by_task_id: dict[str, TaskCommand] = {}

    def submit(self, command: TaskCommand) -> TaskRef:
        handler = self._handlers.get(command.task_type)
        if handler is None:
            raise TaskBackendCapabilityError(f"No DSA handler registered for task_type={command.task_type!r}")

        def run_task() -> Any:
            return handler(command)

        task_info = self._queue.submit_background_task(
            run_task,
            stock_code=str(command.payload.get("stock_code", "unknown")),
            stock_name=command.payload.get("stock_name"),
            report_type=str(command.payload.get("report_type", "detailed")),
            message=command.payload.get("message", "queued"),
            task_id=command.task_id,
            trace_id=command.run_id,
        )
        snapshot = self._snapshot_from_legacy(task_info, command=command)
        self._commands_by_task_id[snapshot.task_id] = command
        return TaskRef(task_id=snapshot.task_id, run_id=snapshot.run_id, status=snapshot.status)

    def get(self, task_id: str) -> TaskSnapshot:
        task_info = self._queue.get_task(task_id)
        if task_info is None:
            raise TaskNotFound(f"Task not found: {task_id}")
        return self._snapshot_from_legacy(task_info, command=self._commands_by_task_id.get(task_id))

    def request_cancel(self, task_id: str) -> TaskSnapshot:
        if hasattr(self._queue, "request_cancel_task"):
            self._queue.request_cancel_task(task_id)
            return self.get(task_id)
        if hasattr(self._queue, "cancel_task"):
            self._queue.cancel_task(task_id)
            return self.get(task_id)
        raise TaskBackendCapabilityError("Injected DSA queue does not support cancellation")

    def subscribe(self, task_id: str, after_event_id: str | None = None) -> tuple[TaskEvent, ...]:
        if not hasattr(self._queue, "get_task_flow_events"):
            raise TaskBackendCapabilityError("Injected DSA queue does not expose task flow events")
        snapshot = self.get(task_id)
        after = int(after_event_id) if after_event_id is not None else 0
        events: list[TaskEvent] = []
        for index, event in enumerate(self._queue.get_task_flow_events(task_id), start=1):
            event_id = str(event.get("event_id") or index)
            if int(event_id) <= after:
                continue
            events.append(
                TaskEvent(
                    event_id=event_id,
                    task_id=task_id,
                    run_id=snapshot.run_id,
                    kind=str(event.get("kind") or event.get("type") or "task.event"),
                    occurred_at=_parse_datetime(event.get("occurred_at")) or snapshot.submitted_at,
                    status=task_status_from_legacy(str(event.get("status") or snapshot.status.value)),
                    message=event.get("message"),
                    payload=event,
                )
            )
        return tuple(events)

    def _snapshot_from_legacy(
        self,
        task_info: Any,
        *,
        command: TaskCommand | None = None,
    ) -> TaskSnapshot:
        record = task_info.to_dict() if hasattr(task_info, "to_dict") else dict(vars(task_info))
        task_id = str(record["task_id"])
        run_id = str(record.get("trace_id") or (command.run_id if command else task_id))
        task_type = command.task_type if command else "dsa.analysis"
        submitted_at = _parse_datetime(record.get("created_at")) or datetime.now(UTC)
        payload = dict(command.payload) if command else {}
        for key in ("stock_code", "stock_name", "report_type", "analysis_phase"):
            if key in record and record[key] is not None:
                payload.setdefault(key, record[key])

        return TaskSnapshot(
            task_id=task_id,
            run_id=run_id,
            task_type=task_type,
            status=task_status_from_legacy(str(record.get("status", "pending"))),
            submitted_at=submitted_at,
            started_at=_parse_datetime(record.get("started_at")),
            completed_at=_parse_datetime(record.get("completed_at")),
            progress=int(record.get("progress") or 0),
            message=record.get("message"),
            error=record.get("error"),
            payload=payload,
            idempotency_key=command.idempotency_key if command else None,
            metadata=command.metadata if command else {},
        )


def _parse_datetime(value: Any) -> datetime | None:
    if value is None or isinstance(value, datetime):
        return value
    if isinstance(value, str) and value:
        return datetime.fromisoformat(value)
    return None
