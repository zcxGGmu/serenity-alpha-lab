from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime
from enum import StrEnum


class RunLifecycleError(ValueError):
    """Base error for invalid run lifecycle operations."""


class InvalidTransition(RunLifecycleError):
    """Raised when a run or stage transition is not allowed."""


class IdempotencyConflict(RunLifecycleError):
    """Raised when an idempotency key is reused for a different request."""


class RunStatus(StrEnum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StageStatus(StrEnum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class EventKind(StrEnum):
    RUN_STARTED = "run.started"
    RUN_COMPLETED = "run.completed"
    RUN_FAILED = "run.failed"
    RUN_CANCELLED = "run.cancelled"
    STAGE_STARTED = "stage.started"
    STAGE_COMPLETED = "stage.completed"
    STAGE_FAILED = "stage.failed"
    STAGE_CANCELLED = "stage.cancelled"
    INFO = "info"


TERMINAL_RUN_STATUSES = frozenset({RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.CANCELLED})
TERMINAL_STAGE_STATUSES = frozenset({StageStatus.COMPLETED, StageStatus.FAILED, StageStatus.CANCELLED})


@dataclass(frozen=True, slots=True)
class RunEvent:
    run_id: str
    sequence: int
    kind: EventKind
    occurred_at: datetime
    message: str = ""
    stage_id: str | None = None


@dataclass(frozen=True, slots=True)
class Stage:
    stage_id: str
    name: str
    status: StageStatus
    attempt: int
    started_at: datetime
    completed_at: datetime | None = None
    failed_at: datetime | None = None
    failure_reason: str | None = None


@dataclass(slots=True)
class Run:
    run_id: str
    run_type: str
    idempotency_key: str
    status: RunStatus
    attempt: int
    started_at: datetime
    parent_run_id: str | None = None
    completed_at: datetime | None = None
    failed_at: datetime | None = None
    failure_reason: str | None = None
    _stages: list[Stage] = field(default_factory=list, repr=False)
    _events: list[RunEvent] = field(default_factory=list, repr=False)
    _next_sequence: int = field(default=1, repr=False)

    @classmethod
    def start(
        cls,
        *,
        run_id: str,
        run_type: str,
        idempotency_key: str,
        started_at: datetime,
        attempt: int = 1,
        parent_run_id: str | None = None,
    ) -> Run:
        run = cls(
            run_id=run_id,
            run_type=run_type,
            idempotency_key=idempotency_key,
            status=RunStatus.RUNNING,
            attempt=attempt,
            parent_run_id=parent_run_id,
            started_at=started_at,
        )
        run._append_event(EventKind.RUN_STARTED, occurred_at=started_at)
        return run

    @property
    def stages(self) -> tuple[Stage, ...]:
        return tuple(self._stages)

    @property
    def events(self) -> tuple[RunEvent, ...]:
        return tuple(self._events)

    def start_stage(self, *, stage_id: str, name: str, started_at: datetime) -> Stage:
        self._ensure_active()
        if self._find_stage(stage_id) is not None:
            raise InvalidTransition(f"Stage already exists: {stage_id}")

        stage = Stage(
            stage_id=stage_id,
            name=name,
            status=StageStatus.RUNNING,
            attempt=self.attempt,
            started_at=started_at,
        )
        self._stages.append(stage)
        self._append_event(EventKind.STAGE_STARTED, stage_id=stage_id, occurred_at=started_at)
        return stage

    def record_stage_event(
        self,
        stage_id: str,
        kind: EventKind,
        *,
        message: str,
        occurred_at: datetime,
    ) -> RunEvent:
        self._ensure_active()
        stage = self._require_stage(stage_id)
        if stage.status in TERMINAL_STAGE_STATUSES:
            raise InvalidTransition(f"Stage is terminal: {stage_id}")
        return self._append_event(kind, stage_id=stage_id, message=message, occurred_at=occurred_at)

    def complete_stage(self, stage_id: str, *, completed_at: datetime) -> Stage:
        self._ensure_active()
        stage = self._require_stage(stage_id)
        if stage.status is not StageStatus.RUNNING:
            raise InvalidTransition(f"Only running stages can complete: {stage_id}")

        updated = replace(stage, status=StageStatus.COMPLETED, completed_at=completed_at)
        self._replace_stage(updated)
        self._append_event(EventKind.STAGE_COMPLETED, stage_id=stage_id, occurred_at=completed_at)
        return updated

    def fail_stage(self, stage_id: str, *, reason: str, failed_at: datetime) -> Stage:
        self._ensure_active()
        stage = self._require_stage(stage_id)
        if stage.status is not StageStatus.RUNNING:
            raise InvalidTransition(f"Only running stages can fail: {stage_id}")

        updated = replace(stage, status=StageStatus.FAILED, failed_at=failed_at, failure_reason=reason)
        self._replace_stage(updated)
        self._append_event(EventKind.STAGE_FAILED, stage_id=stage_id, message=reason, occurred_at=failed_at)
        return updated

    def complete(self, *, completed_at: datetime) -> None:
        self._ensure_active()
        running = [stage.stage_id for stage in self._stages if stage.status is StageStatus.RUNNING]
        if running:
            raise InvalidTransition(f"Cannot complete run with running stages: {', '.join(running)}")

        self.status = RunStatus.COMPLETED
        self.completed_at = completed_at
        self._append_event(EventKind.RUN_COMPLETED, occurred_at=completed_at)

    def fail(self, *, reason: str, failed_at: datetime) -> None:
        self._ensure_active()
        self.status = RunStatus.FAILED
        self.failed_at = failed_at
        self.failure_reason = reason
        self._append_event(EventKind.RUN_FAILED, message=reason, occurred_at=failed_at)

    def cancel(self, *, reason: str, cancelled_at: datetime) -> None:
        self._ensure_active()
        self.status = RunStatus.CANCELLED
        self.failure_reason = reason
        self._append_event(EventKind.RUN_CANCELLED, message=reason, occurred_at=cancelled_at)

    def retry(self, *, new_run_id: str, started_at: datetime) -> Run:
        if self.status not in {RunStatus.FAILED, RunStatus.CANCELLED}:
            raise InvalidTransition("Only failed or cancelled runs can be retried")
        return Run.start(
            run_id=new_run_id,
            run_type=self.run_type,
            idempotency_key=self.idempotency_key,
            started_at=started_at,
            attempt=self.attempt + 1,
            parent_run_id=self.run_id,
        )

    def same_idempotent_request(self, other: Run) -> bool:
        if self.idempotency_key != other.idempotency_key:
            return False
        if self.run_type != other.run_type:
            raise IdempotencyConflict(
                f"Idempotency key {self.idempotency_key!r} was reused for different run types"
            )
        return True

    def _append_event(
        self,
        kind: EventKind,
        *,
        occurred_at: datetime,
        message: str = "",
        stage_id: str | None = None,
    ) -> RunEvent:
        event = RunEvent(
            run_id=self.run_id,
            sequence=self._next_sequence,
            kind=kind,
            occurred_at=occurred_at,
            message=message,
            stage_id=stage_id,
        )
        self._events.append(event)
        self._next_sequence += 1
        return event

    def _ensure_active(self) -> None:
        if self.status in TERMINAL_RUN_STATUSES:
            raise InvalidTransition(f"Run is terminal: {self.status}")

    def _find_stage(self, stage_id: str) -> Stage | None:
        return next((stage for stage in self._stages if stage.stage_id == stage_id), None)

    def _require_stage(self, stage_id: str) -> Stage:
        stage = self._find_stage(stage_id)
        if stage is None:
            raise InvalidTransition(f"Unknown stage: {stage_id}")
        return stage

    def _replace_stage(self, updated: Stage) -> None:
        for index, stage in enumerate(self._stages):
            if stage.stage_id == updated.stage_id:
                self._stages[index] = updated
                return
        raise InvalidTransition(f"Unknown stage: {updated.stage_id}")
