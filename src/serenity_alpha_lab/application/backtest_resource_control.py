from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from types import MappingProxyType
from typing import Any, Callable

from serenity_alpha_lab.application.backtest_run import (
    BacktestRunRecord,
    BacktestRunRequest,
    BacktestRunOrchestrator,
)
from serenity_alpha_lab.domain.artifacts import ArtifactManifest, ArtifactRetentionTier, ArtifactStore
from serenity_alpha_lab.integrations.qlib.runtime_policy import (
    QlibRuntimeIsolationPolicy,
    default_qlib_runtime_policy,
)
from serenity_alpha_lab.quant.backtest.artifacts import BacktestArtifactState


BACKTEST_RUN_RESOURCE_CONTROL_CONTRACT_VERSION = "application.backtest_resource_control@1.0.0"
BACKTEST_RUN_CHECKPOINT_SCHEMA_NAME = "quant.backtest_run_checkpoint"
BACKTEST_RUN_CHECKPOINT_SCHEMA_VERSION = "1.0.0"
BACKTEST_RUN_CHECKPOINT_CONTENT_TYPE = "application/vnd.serenity.quant.backtest-run-checkpoint+json"
BACKTEST_RUN_RESOURCE_SUPERVISOR_VERSION = "cn_a_share_backtest_resource_supervisor@1.0.0"

_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")

ClockFn = Callable[[], datetime]


class BacktestRunResourceControlError(ValueError):
    """Raised when BacktestRun resource-control contracts are invalid."""


class BacktestRunExecutionStatus(StrEnum):
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    TIMED_OUT = "timed_out"
    CANCELLED = "cancelled"
    OOM_KILLED = "oom_killed"


class BacktestRunChildProcessStatus(StrEnum):
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    OOM_KILLED = "oom_killed"


@dataclass(frozen=True, slots=True)
class BacktestRunResourcePolicy:
    queue_name: str = "worker-quant"
    process_isolation: str = "dedicated_process"
    max_cpu_cores: int = 2
    max_memory_mb: int = 4096
    wall_clock_timeout_seconds: int = 3600
    heartbeat_interval_seconds: int = 15
    checkpoint_interval_seconds: int = 300
    max_output_bytes: int = 512 * 1024 * 1024

    def __post_init__(self) -> None:
        object.__setattr__(self, "queue_name", _required_string("queue_name", self.queue_name))
        object.__setattr__(self, "process_isolation", _required_string("process_isolation", self.process_isolation))
        for field_name in (
            "max_cpu_cores",
            "max_memory_mb",
            "wall_clock_timeout_seconds",
            "heartbeat_interval_seconds",
            "checkpoint_interval_seconds",
            "max_output_bytes",
        ):
            _require_positive_int(field_name, getattr(self, field_name))
        if self.checkpoint_interval_seconds < self.heartbeat_interval_seconds:
            raise BacktestRunResourceControlError(
                "checkpoint_interval_seconds must be greater than or equal to heartbeat interval"
            )

    @classmethod
    def from_qlib_runtime_policy(cls, policy: QlibRuntimeIsolationPolicy | None = None) -> BacktestRunResourcePolicy:
        resolved = policy or default_qlib_runtime_policy()
        if type(resolved) is not QlibRuntimeIsolationPolicy:
            raise BacktestRunResourceControlError("policy must be a QlibRuntimeIsolationPolicy")
        return cls(
            queue_name=resolved.queue_name,
            process_isolation=resolved.process_isolation,
            max_cpu_cores=resolved.max_cpu_cores,
            max_memory_mb=resolved.max_memory_mb,
            wall_clock_timeout_seconds=resolved.wall_clock_timeout_seconds,
            heartbeat_interval_seconds=resolved.heartbeat_interval_seconds,
            checkpoint_interval_seconds=resolved.checkpoint_interval_seconds,
        )

    def to_record(self) -> dict[str, object]:
        return {
            "queue_name": self.queue_name,
            "process_isolation": self.process_isolation,
            "max_cpu_cores": self.max_cpu_cores,
            "max_memory_mb": self.max_memory_mb,
            "wall_clock_timeout_seconds": self.wall_clock_timeout_seconds,
            "heartbeat_interval_seconds": self.heartbeat_interval_seconds,
            "checkpoint_interval_seconds": self.checkpoint_interval_seconds,
            "max_output_bytes": self.max_output_bytes,
        }


@dataclass(frozen=True, slots=True)
class BacktestRunChildProcessSnapshot:
    process_id: str
    status: BacktestRunChildProcessStatus | str
    observed_at: datetime
    stage_id: str
    progress_pct: int
    exit_code: int | None = None
    memory_peak_mb: int = 0
    output_size_bytes: int = 0
    partial_output_artifact_ids: Sequence[str] = ()
    result_request: BacktestRunRequest | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "process_id", _required_string("process_id", self.process_id))
        object.__setattr__(self, "status", _enum_value(BacktestRunChildProcessStatus, "status", self.status))
        _require_aware_datetime("observed_at", self.observed_at)
        object.__setattr__(self, "stage_id", _required_string("stage_id", self.stage_id))
        if type(self.progress_pct) is not int or self.progress_pct < 0 or self.progress_pct > 100:
            raise BacktestRunResourceControlError("progress_pct must be an integer between 0 and 100")
        if self.exit_code is not None and type(self.exit_code) is not int:
            raise BacktestRunResourceControlError("exit_code must be an integer when provided")
        _require_non_negative_int("memory_peak_mb", self.memory_peak_mb)
        _require_non_negative_int("output_size_bytes", self.output_size_bytes)
        object.__setattr__(self, "partial_output_artifact_ids", _string_tuple("partial_output_artifact_id", self.partial_output_artifact_ids))
        if self.result_request is not None and type(self.result_request) is not BacktestRunRequest:
            raise BacktestRunResourceControlError("result_request must be a BacktestRunRequest")

    def resource_usage_record(self) -> dict[str, object]:
        return {
            "exit_code": self.exit_code,
            "memory_peak_mb": self.memory_peak_mb,
            "output_size_bytes": self.output_size_bytes,
        }


@dataclass(frozen=True, slots=True)
class BacktestRunCheckpoint:
    checkpoint_id: str
    sequence: int
    run_id: str
    trace_id: str
    status: BacktestRunExecutionStatus | str
    reason: str
    stage_id: str
    observed_at: datetime
    process_id: str
    progress_pct: int
    artifact_state: BacktestArtifactState | str
    partial_output_artifact_ids: Sequence[str]
    resource_usage: Mapping[str, Any]
    artifact_manifest: ArtifactManifest
    next_allowed_stage_id: str
    schema_name: str = BACKTEST_RUN_CHECKPOINT_SCHEMA_NAME
    schema_version: str = BACKTEST_RUN_CHECKPOINT_SCHEMA_VERSION
    contract_version: str = BACKTEST_RUN_RESOURCE_CONTROL_CONTRACT_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "checkpoint_id", _required_string("checkpoint_id", self.checkpoint_id))
        if type(self.sequence) is not int or self.sequence <= 0:
            raise BacktestRunResourceControlError("sequence must be a positive integer")
        object.__setattr__(self, "run_id", _required_string("run_id", self.run_id))
        object.__setattr__(self, "trace_id", _required_string("trace_id", self.trace_id))
        object.__setattr__(self, "status", _enum_value(BacktestRunExecutionStatus, "status", self.status))
        object.__setattr__(self, "reason", _required_string("reason", self.reason))
        object.__setattr__(self, "stage_id", _required_string("stage_id", self.stage_id))
        _require_aware_datetime("observed_at", self.observed_at)
        object.__setattr__(self, "process_id", _required_string("process_id", self.process_id))
        if type(self.progress_pct) is not int or self.progress_pct < 0 or self.progress_pct > 100:
            raise BacktestRunResourceControlError("progress_pct must be an integer between 0 and 100")
        object.__setattr__(self, "artifact_state", _enum_value(BacktestArtifactState, "artifact_state", self.artifact_state))
        object.__setattr__(self, "partial_output_artifact_ids", _string_tuple("partial_output_artifact_id", self.partial_output_artifact_ids))
        object.__setattr__(self, "resource_usage", _freeze_mapping(self.resource_usage))
        if type(self.artifact_manifest) is not ArtifactManifest:
            raise BacktestRunResourceControlError("artifact_manifest must be an ArtifactManifest")
        object.__setattr__(self, "next_allowed_stage_id", _required_string("next_allowed_stage_id", self.next_allowed_stage_id))

    def to_record(self) -> dict[str, object]:
        return {
            "schema_name": self.schema_name,
            "schema_version": self.schema_version,
            "contract_version": self.contract_version,
            "checkpoint_id": self.checkpoint_id,
            "sequence": self.sequence,
            "run_id": self.run_id,
            "trace_id": self.trace_id,
            "status": self.status.value,
            "reason": self.reason,
            "stage_id": self.stage_id,
            "observed_at": self.observed_at.isoformat(),
            "process_id": self.process_id,
            "progress_pct": self.progress_pct,
            "artifact_state": self.artifact_state.value,
            "partial_output_artifact_ids": list(self.partial_output_artifact_ids),
            "resource_usage": _thaw_value(self.resource_usage),
            "artifact": self.artifact_manifest.to_record(),
            "resume": {"next_allowed_stage_id": self.next_allowed_stage_id},
        }


@dataclass(frozen=True, slots=True)
class BacktestRunExecutionRecord:
    run_id: str
    trace_id: str
    idempotency_key: str
    status: BacktestRunExecutionStatus | str
    resource_policy: BacktestRunResourcePolicy
    started_at: datetime
    observed_at: datetime
    request: BacktestRunRequest = field(repr=False)
    process_id: str | None = None
    final_record: BacktestRunRecord | None = None
    checkpoints: Sequence[BacktestRunCheckpoint] = ()
    failure_reason: str | None = None
    termination_requested: bool = False
    termination_reason: str | None = None
    cancel_requested_at: datetime | None = None
    contract_version: str = BACKTEST_RUN_RESOURCE_CONTROL_CONTRACT_VERSION
    supervisor_version: str = BACKTEST_RUN_RESOURCE_SUPERVISOR_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "run_id", _required_string("run_id", self.run_id))
        object.__setattr__(self, "trace_id", _required_string("trace_id", self.trace_id))
        object.__setattr__(self, "idempotency_key", _required_string("idempotency_key", self.idempotency_key))
        object.__setattr__(self, "status", _enum_value(BacktestRunExecutionStatus, "status", self.status))
        if type(self.resource_policy) is not BacktestRunResourcePolicy:
            raise BacktestRunResourceControlError("resource_policy must be a BacktestRunResourcePolicy")
        _require_aware_datetime("started_at", self.started_at)
        _require_aware_datetime("observed_at", self.observed_at)
        if type(self.request) is not BacktestRunRequest:
            raise BacktestRunResourceControlError("request must be a BacktestRunRequest")
        object.__setattr__(self, "process_id", _optional_string(self.process_id))
        if self.final_record is not None and type(self.final_record) is not BacktestRunRecord:
            raise BacktestRunResourceControlError("final_record must be a BacktestRunRecord")
        checkpoints = tuple(self.checkpoints)
        for checkpoint in checkpoints:
            if type(checkpoint) is not BacktestRunCheckpoint:
                raise BacktestRunResourceControlError("checkpoints must contain BacktestRunCheckpoint values")
        object.__setattr__(self, "checkpoints", checkpoints)
        object.__setattr__(self, "failure_reason", _optional_string(self.failure_reason))
        if type(self.termination_requested) is not bool:
            raise BacktestRunResourceControlError("termination_requested must be boolean")
        object.__setattr__(self, "termination_reason", _optional_string(self.termination_reason))
        if self.cancel_requested_at is not None:
            _require_aware_datetime("cancel_requested_at", self.cancel_requested_at)

    def to_record(self) -> dict[str, object]:
        return {
            "contract_version": self.contract_version,
            "supervisor_version": self.supervisor_version,
            "run_id": self.run_id,
            "trace_id": self.trace_id,
            "idempotency_key": self.idempotency_key,
            "status": self.status.value,
            "process_id": self.process_id,
            "started_at": self.started_at.isoformat(),
            "observed_at": self.observed_at.isoformat(),
            "resource_policy": self.resource_policy.to_record(),
            "failure_reason": self.failure_reason,
            "termination_requested": self.termination_requested,
            "termination_reason": self.termination_reason,
            "cancel_requested_at": self.cancel_requested_at.isoformat() if self.cancel_requested_at else None,
            "checkpoint_artifact_ids": [checkpoint.artifact_manifest.artifact_id for checkpoint in self.checkpoints],
            "final_run_id": self.final_record.run_id if self.final_record is not None else None,
            "runtime": _runtime_boundary_record(),
        }


class InMemoryBacktestRunExecutionRepository:
    def __init__(self) -> None:
        self._records: dict[str, BacktestRunExecutionRecord] = {}

    def save(self, record: BacktestRunExecutionRecord) -> BacktestRunExecutionRecord:
        if type(record) is not BacktestRunExecutionRecord:
            raise BacktestRunResourceControlError("record must be a BacktestRunExecutionRecord")
        self._records[record.run_id] = record
        return record

    def get(self, run_id: str) -> BacktestRunExecutionRecord:
        normalized = _required_string("run_id", run_id)
        try:
            return self._records[normalized]
        except KeyError as exc:
            raise BacktestRunResourceControlError(f"BacktestRun execution not found: {normalized}") from exc


class BacktestRunResourceSupervisor:
    def __init__(
        self,
        *,
        execution_repository: InMemoryBacktestRunExecutionRepository,
        artifact_store: ArtifactStore,
        finalizer: BacktestRunOrchestrator,
        clock: ClockFn | None = None,
    ) -> None:
        if type(execution_repository) is not InMemoryBacktestRunExecutionRepository:
            raise BacktestRunResourceControlError(
                "execution_repository must be an InMemoryBacktestRunExecutionRepository"
            )
        if type(finalizer) is not BacktestRunOrchestrator:
            raise BacktestRunResourceControlError("finalizer must be a BacktestRunOrchestrator")
        self._repository = execution_repository
        self._artifact_store = artifact_store
        self._finalizer = finalizer
        self._clock = clock or (lambda: datetime.now(UTC))

    def start(
        self,
        *,
        request: BacktestRunRequest,
        resource_policy: BacktestRunResourcePolicy | None = None,
    ) -> BacktestRunExecutionRecord:
        if type(request) is not BacktestRunRequest:
            raise BacktestRunResourceControlError("request must be a BacktestRunRequest")
        policy = resource_policy or BacktestRunResourcePolicy.from_qlib_runtime_policy()
        record = BacktestRunExecutionRecord(
            run_id=request.run_id,
            trace_id=request.trace_id,
            idempotency_key=request.idempotency_key,
            status=BacktestRunExecutionStatus.RUNNING,
            resource_policy=policy,
            started_at=request.submitted_at,
            observed_at=request.submitted_at,
            request=request,
        )
        return self._repository.save(record)

    def request_cancel(
        self,
        run_id: str,
        *,
        reason: str = "cancel_requested",
        requested_at: datetime | None = None,
    ) -> BacktestRunExecutionRecord:
        record = self._repository.get(run_id)
        if record.status is not BacktestRunExecutionStatus.RUNNING:
            return record
        cancelled = replace(
            record,
            termination_reason=_required_string("reason", reason),
            cancel_requested_at=requested_at or self._clock(),
        )
        return self._repository.save(cancelled)

    def observe(
        self,
        run_id: str,
        snapshot: BacktestRunChildProcessSnapshot,
    ) -> BacktestRunExecutionRecord:
        if type(snapshot) is not BacktestRunChildProcessSnapshot:
            raise BacktestRunResourceControlError("snapshot must be a BacktestRunChildProcessSnapshot")
        record = self._repository.get(run_id)
        if record.status is not BacktestRunExecutionStatus.RUNNING:
            return record

        if record.cancel_requested_at is not None:
            return self._terminal_with_checkpoint(
                record=record,
                snapshot=snapshot,
                status=BacktestRunExecutionStatus.CANCELLED,
                reason=record.termination_reason or "cancel_requested",
                artifact_state=BacktestArtifactState.PARTIAL,
                termination_requested=True,
                failure_reason=None,
            )

        if self._timed_out(record, snapshot):
            return self._terminal_with_checkpoint(
                record=record,
                snapshot=snapshot,
                status=BacktestRunExecutionStatus.TIMED_OUT,
                reason="timeout",
                artifact_state=BacktestArtifactState.PARTIAL,
                termination_requested=True,
                failure_reason="timeout",
            )

        if snapshot.status is BacktestRunChildProcessStatus.SUCCEEDED:
            final_request = snapshot.result_request or record.request
            final_record = self._finalizer.finalize(final_request)
            checkpoint = self._publish_checkpoint(
                record=record,
                snapshot=snapshot,
                status=BacktestRunExecutionStatus.SUCCEEDED,
                reason="succeeded",
                artifact_state=BacktestArtifactState.FORMAL,
            )
            completed = replace(
                record,
                status=BacktestRunExecutionStatus.SUCCEEDED,
                process_id=snapshot.process_id,
                observed_at=snapshot.observed_at,
                final_record=final_record,
                checkpoints=(*record.checkpoints, checkpoint),
            )
            return self._repository.save(completed)

        if snapshot.status is BacktestRunChildProcessStatus.OOM_KILLED:
            return self._terminal_with_checkpoint(
                record=record,
                snapshot=snapshot,
                status=BacktestRunExecutionStatus.OOM_KILLED,
                reason="oom_killed",
                artifact_state=BacktestArtifactState.PARTIAL,
                termination_requested=False,
                failure_reason="oom_killed",
            )

        if snapshot.status is BacktestRunChildProcessStatus.FAILED:
            return self._terminal_with_checkpoint(
                record=record,
                snapshot=snapshot,
                status=BacktestRunExecutionStatus.FAILED,
                reason="failed",
                artifact_state=BacktestArtifactState.PARTIAL,
                termination_requested=False,
                failure_reason="failed",
            )

        running = replace(
            record,
            process_id=snapshot.process_id,
            observed_at=snapshot.observed_at,
        )
        return self._repository.save(running)

    def _terminal_with_checkpoint(
        self,
        *,
        record: BacktestRunExecutionRecord,
        snapshot: BacktestRunChildProcessSnapshot,
        status: BacktestRunExecutionStatus,
        reason: str,
        artifact_state: BacktestArtifactState,
        termination_requested: bool,
        failure_reason: str | None,
    ) -> BacktestRunExecutionRecord:
        checkpoint = self._publish_checkpoint(
            record=record,
            snapshot=snapshot,
            status=status,
            reason=reason,
            artifact_state=artifact_state,
        )
        updated = replace(
            record,
            status=status,
            process_id=snapshot.process_id,
            observed_at=snapshot.observed_at,
            checkpoints=(*record.checkpoints, checkpoint),
            failure_reason=failure_reason,
            termination_requested=termination_requested,
            termination_reason=reason if termination_requested else record.termination_reason,
        )
        return self._repository.save(updated)

    def _publish_checkpoint(
        self,
        *,
        record: BacktestRunExecutionRecord,
        snapshot: BacktestRunChildProcessSnapshot,
        status: BacktestRunExecutionStatus,
        reason: str,
        artifact_state: BacktestArtifactState,
    ) -> BacktestRunCheckpoint:
        sequence = len(record.checkpoints) + 1
        checkpoint_id = _stable_id(
            "btrc",
            {
                "run_id": record.run_id,
                "sequence": sequence,
                "status": status.value,
                "reason": reason,
                "stage_id": snapshot.stage_id,
                "observed_at": snapshot.observed_at.isoformat(),
            },
        )
        payload = {
            "schema_name": BACKTEST_RUN_CHECKPOINT_SCHEMA_NAME,
            "schema_version": BACKTEST_RUN_CHECKPOINT_SCHEMA_VERSION,
            "contract_version": BACKTEST_RUN_RESOURCE_CONTROL_CONTRACT_VERSION,
            "supervisor_version": BACKTEST_RUN_RESOURCE_SUPERVISOR_VERSION,
            "checkpoint_id": checkpoint_id,
            "sequence": sequence,
            "run_id": record.run_id,
            "trace_id": record.trace_id,
            "idempotency_key": record.idempotency_key,
            "status": status.value,
            "reason": reason,
            "stage_id": snapshot.stage_id,
            "observed_at": snapshot.observed_at.isoformat(),
            "process_id": snapshot.process_id,
            "progress_pct": snapshot.progress_pct,
            "artifact_state": artifact_state.value,
            "partial_output_artifact_ids": list(snapshot.partial_output_artifact_ids),
            "resource_policy": record.resource_policy.to_record(),
            "resource_usage": snapshot.resource_usage_record(),
            "resume": {"next_allowed_stage_id": snapshot.stage_id},
            "runtime": _runtime_boundary_record(),
        }
        manifest = self._artifact_store.put_bytes(
            _canonical_json_bytes(payload),
            schema_name=BACKTEST_RUN_CHECKPOINT_SCHEMA_NAME,
            schema_version=BACKTEST_RUN_CHECKPOINT_SCHEMA_VERSION,
            content_type=BACKTEST_RUN_CHECKPOINT_CONTENT_TYPE,
            produced_by_run_id=record.run_id,
            produced_by_stage_id=snapshot.stage_id,
            retention_tier=ArtifactRetentionTier.STANDARD,
            created_at=snapshot.observed_at,
        )
        return BacktestRunCheckpoint(
            checkpoint_id=checkpoint_id,
            sequence=sequence,
            run_id=record.run_id,
            trace_id=record.trace_id,
            status=status,
            reason=reason,
            stage_id=snapshot.stage_id,
            observed_at=snapshot.observed_at,
            process_id=snapshot.process_id,
            progress_pct=snapshot.progress_pct,
            artifact_state=artifact_state,
            partial_output_artifact_ids=snapshot.partial_output_artifact_ids,
            resource_usage=snapshot.resource_usage_record(),
            artifact_manifest=manifest,
            next_allowed_stage_id=snapshot.stage_id,
        )

    @staticmethod
    def _timed_out(record: BacktestRunExecutionRecord, snapshot: BacktestRunChildProcessSnapshot) -> bool:
        elapsed = (snapshot.observed_at - record.started_at).total_seconds()
        return (
            snapshot.status is BacktestRunChildProcessStatus.RUNNING
            and elapsed > record.resource_policy.wall_clock_timeout_seconds
        )


def _runtime_boundary_record() -> dict[str, bool]:
    return {
        "resource_controls_started": True,
        "api_route_started": False,
        "quant_lab_started": False,
        "evidence_agent_started": False,
        "worker_loop_started": False,
        "real_provider_calls_started": False,
        "real_llm_calls_started": False,
        "qlib_runtime_started": False,
    }


def _stable_id(prefix: str, record: Mapping[str, Any]) -> str:
    return f"{prefix}_{hashlib.sha256(_canonical_json_bytes(record)).hexdigest()[:32]}"


def _canonical_json_bytes(payload: Mapping[str, Any]) -> bytes:
    return json.dumps(_json_ready(payload), ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _json_ready(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, StrEnum):
        return value.value
    if isinstance(value, Mapping):
        return {str(key): _json_ready(item) for key, item in value.items()}
    if isinstance(value, tuple | list):
        return [_json_ready(item) for item in value]
    return value


def _freeze_mapping(value: Mapping[str, Any]) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise BacktestRunResourceControlError("mapping value must be a Mapping")
    return MappingProxyType({str(key): _freeze_value(item) for key, item in value.items()})


def _freeze_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({str(key): _freeze_value(item) for key, item in value.items()})
    if isinstance(value, list | tuple):
        return tuple(_freeze_value(item) for item in value)
    return value


def _thaw_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw_value(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw_value(item) for item in value]
    return _json_ready(value)


def _string_tuple(field_name: str, values: Sequence[str]) -> tuple[str, ...]:
    return tuple(_required_string(field_name, str(value)) for value in values)


def _enum_value(enum_type: type[StrEnum], field_name: str, value: object) -> Any:
    try:
        return value if isinstance(value, enum_type) else enum_type(str(value))
    except ValueError as exc:
        raise BacktestRunResourceControlError(f"{field_name} has invalid value: {value}") from exc


def _optional_string(value: object | None) -> str | None:
    if value is None:
        return None
    return _required_string("value", value)


def _required_string(field_name: str, value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise BacktestRunResourceControlError(f"{field_name} must be a non-empty string")
    return value.strip()


def _require_positive_int(field_name: str, value: object) -> None:
    if type(value) is not int or value <= 0:
        raise BacktestRunResourceControlError(f"{field_name} must be a positive integer")


def _require_non_negative_int(field_name: str, value: object) -> None:
    if type(value) is not int or value < 0:
        raise BacktestRunResourceControlError(f"{field_name} must be a non-negative integer")


def _require_aware_datetime(field_name: str, value: object) -> None:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise BacktestRunResourceControlError(f"{field_name} must be a timezone-aware datetime")


def _validate_sha256(field_name: str, value: object) -> str:
    text = _required_string(field_name, value)
    if not _SHA256_RE.fullmatch(text):
        raise BacktestRunResourceControlError(f"{field_name} must be sha256:<64 hex>")
    return text


__all__ = [
    "BACKTEST_RUN_CHECKPOINT_CONTENT_TYPE",
    "BACKTEST_RUN_CHECKPOINT_SCHEMA_NAME",
    "BACKTEST_RUN_CHECKPOINT_SCHEMA_VERSION",
    "BACKTEST_RUN_RESOURCE_CONTROL_CONTRACT_VERSION",
    "BACKTEST_RUN_RESOURCE_SUPERVISOR_VERSION",
    "BacktestRunCheckpoint",
    "BacktestRunChildProcessSnapshot",
    "BacktestRunChildProcessStatus",
    "BacktestRunExecutionRecord",
    "BacktestRunExecutionStatus",
    "BacktestRunResourceControlError",
    "BacktestRunResourcePolicy",
    "BacktestRunResourceSupervisor",
    "InMemoryBacktestRunExecutionRepository",
]
