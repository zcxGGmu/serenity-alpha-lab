from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import pytest

from serenity_alpha_lab.application.task_backend import (
    TaskBackendCapabilityError,
    TaskCommand,
    TaskStatus,
)
from serenity_alpha_lab.integrations.dsa.task_backend import DsaAnalysisTaskQueueBackend


@dataclass
class FakeTaskInfo:
    task_id: str
    trace_id: str
    status: str = "pending"
    progress: int = 0
    message: str | None = "queued"

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "trace_id": self.trace_id,
            "status": self.status,
            "progress": self.progress,
            "message": self.message,
            "stock_code": "600519",
            "report_type": "detailed",
            "analysis_phase": "auto",
            "created_at": datetime(2026, 7, 20, 11, 15, tzinfo=UTC).isoformat(),
            "started_at": None,
            "completed_at": None,
            "error": None,
        }


class FakeDsaQueue:
    def __init__(self) -> None:
        self.submissions: list[dict[str, Any]] = []
        self.tasks: dict[str, FakeTaskInfo] = {}
        self.flow_events: dict[str, list[dict[str, Any]]] = {}

    def submit_background_task(self, run_task, **kwargs):
        task_id = kwargs["task_id"] or "legacy-task-001"
        self.submissions.append({"run_task": run_task, **kwargs})
        task = FakeTaskInfo(task_id=task_id, trace_id=kwargs["trace_id"])
        self.tasks[task_id] = task
        self.flow_events[task_id] = [{"kind": "task.submitted", "message": task.message}]
        return task

    def get_task(self, task_id: str):
        return self.tasks.get(task_id)

    def request_cancel_task(self, task_id: str) -> None:
        task = self.tasks[task_id]
        task.status = "cancelled"
        task.message = "cancelled"
        self.flow_events[task_id].append({"kind": "task.cancelled", "message": "cancelled"})

    def get_task_flow_events(self, task_id: str):
        return list(self.flow_events.get(task_id, []))


def make_command() -> TaskCommand:
    return TaskCommand(
        run_id="run-dsa-001",
        task_type="dsa.analysis.background",
        task_id="task-dsa-001",
        payload={
            "stock_code": "600519",
            "stock_name": "贵州茅台",
            "report_type": "detailed",
            "message": "queued",
        },
    )


def test_dsa_task_backend_facade_submits_via_injected_queue_and_handler() -> None:
    queue = FakeDsaQueue()
    called: list[TaskCommand] = []
    backend = DsaAnalysisTaskQueueBackend(
        queue,
        handlers={"dsa.analysis.background": lambda command: called.append(command)},
    )

    ref = backend.submit(make_command())
    snapshot = backend.get(ref.task_id)

    assert ref.task_id == "task-dsa-001"
    assert ref.status is TaskStatus.QUEUED
    assert snapshot.run_id == "run-dsa-001"
    assert snapshot.payload["stock_code"] == "600519"
    assert queue.submissions[0]["stock_code"] == "600519"
    queue.submissions[0]["run_task"]()
    assert called == [make_command()]


def test_dsa_task_backend_facade_cancel_and_subscribe() -> None:
    queue = FakeDsaQueue()
    backend = DsaAnalysisTaskQueueBackend(
        queue,
        handlers={"dsa.analysis.background": lambda command: None},
    )
    ref = backend.submit(make_command())

    cancelled = backend.request_cancel(ref.task_id)
    events = backend.subscribe(ref.task_id, after_event_id="1")

    assert cancelled.status is TaskStatus.CANCELLED
    assert [event.kind for event in events] == ["task.cancelled"]


def test_dsa_task_backend_facade_requires_registered_handler() -> None:
    backend = DsaAnalysisTaskQueueBackend(FakeDsaQueue(), handlers={})

    with pytest.raises(TaskBackendCapabilityError, match="No DSA handler"):
        backend.submit(make_command())
