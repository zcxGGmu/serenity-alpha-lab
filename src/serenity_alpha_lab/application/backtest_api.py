from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from datetime import UTC, date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any, Callable

from serenity_alpha_lab.application.backtest_resource_control import (
    BacktestRunChildProcessSnapshot,
    BacktestRunExecutionRecord,
    BacktestRunExecutionStatus,
    BacktestRunResourceControlError,
    BacktestRunResourcePolicy,
    BacktestRunResourceSupervisor,
)
from serenity_alpha_lab.application.backtest_run import (
    BACKTEST_RUN_TYPE,
    BacktestRunRecord,
    BacktestRunRequest,
)
from serenity_alpha_lab.application.task_backend import (
    InMemoryTaskBackend,
    TaskBackend,
    TaskCommand,
    TaskRef,
    TaskSnapshot,
)
from serenity_alpha_lab.domain.artifacts import ArtifactManifest, ArtifactStore
from serenity_alpha_lab.quant.backtest.artifacts import (
    BacktestArtifactKind,
    BacktestOutputArtifact,
)


BACKTEST_API_CONTRACT_VERSION = "application.formal_backtest_api@1.0.0"
BACKTEST_API_RUN_SCHEMA_NAME = "quant.backtest_api_run"
BACKTEST_API_RUN_SCHEMA_VERSION = "1.0.0"
FORMAL_BACKTEST_TASK_TYPE = "quant.backtest.run"
FORMAL_BACKTEST_EVALUATION_TYPE = "portfolio_backtest"

ClockFn = Callable[[], datetime]


class BacktestApiError(ValueError):
    """Raised when formal portfolio backtest API contracts are violated."""


@dataclass(frozen=True, slots=True)
class BacktestApiRoute:
    method: str
    path: str
    operation_id: str
    response_status: int

    def __post_init__(self) -> None:
        object.__setattr__(self, "method", _required_string("method", self.method).upper())
        object.__setattr__(self, "path", _required_string("path", self.path))
        object.__setattr__(self, "operation_id", _required_string("operation_id", self.operation_id))
        if type(self.response_status) is not int or self.response_status < 100 or self.response_status > 599:
            raise BacktestApiError("response_status must be a valid HTTP status code")

    def to_record(self) -> dict[str, object]:
        return {
            "method": self.method,
            "path": self.path,
            "operation_id": self.operation_id,
            "response_status": self.response_status,
        }


@dataclass(frozen=True, slots=True)
class BacktestApiResponse:
    status_code: int
    body: Mapping[str, Any]
    headers: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if type(self.status_code) is not int or self.status_code < 100 or self.status_code > 599:
            raise BacktestApiError("status_code must be a valid HTTP status code")
        json.dumps(self.body, sort_keys=True, default=_json_default)
        object.__setattr__(self, "body", _json_ready(self.body))
        object.__setattr__(self, "headers", dict(self.headers))


@dataclass(frozen=True, slots=True)
class BacktestArtifactAccessSubject:
    subject_id: str
    roles: Sequence[str] = ()
    allowed_run_ids: Sequence[str] = ()
    allowed_artifact_ids: Sequence[str] = ()
    is_admin: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "subject_id", _required_string("subject_id", self.subject_id))
        object.__setattr__(self, "roles", _string_tuple("role", self.roles))
        object.__setattr__(self, "allowed_run_ids", _string_tuple("allowed_run_id", self.allowed_run_ids))
        object.__setattr__(self, "allowed_artifact_ids", _string_tuple("allowed_artifact_id", self.allowed_artifact_ids))
        if type(self.is_admin) is not bool:
            raise BacktestApiError("is_admin must be boolean")


class BacktestArtifactAccessPolicy:
    def can_download(
        self,
        *,
        subject: BacktestArtifactAccessSubject,
        run_id: str,
        artifact_manifest: ArtifactManifest,
    ) -> bool:
        if type(subject) is not BacktestArtifactAccessSubject:
            raise BacktestApiError("subject must be a BacktestArtifactAccessSubject")
        if type(artifact_manifest) is not ArtifactManifest:
            raise BacktestApiError("artifact_manifest must be an ArtifactManifest")
        if subject.is_admin:
            return True
        return run_id in subject.allowed_run_ids and artifact_manifest.artifact_id in subject.allowed_artifact_ids


@dataclass(frozen=True, slots=True)
class BacktestApiRunRecord:
    run_id: str
    task_id: str
    task_type: str
    idempotency_key: str
    request_hash: str
    request: BacktestRunRequest = field(repr=False)
    execution_record: BacktestRunExecutionRecord = field(repr=False)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    contract_version: str = BACKTEST_API_CONTRACT_VERSION
    schema_name: str = BACKTEST_API_RUN_SCHEMA_NAME
    schema_version: str = BACKTEST_API_RUN_SCHEMA_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "run_id", _required_string("run_id", self.run_id))
        object.__setattr__(self, "task_id", _required_string("task_id", self.task_id))
        object.__setattr__(self, "task_type", _required_string("task_type", self.task_type))
        object.__setattr__(self, "idempotency_key", _required_string("Idempotency-Key", self.idempotency_key))
        object.__setattr__(self, "request_hash", _required_string("request_hash", self.request_hash))
        if type(self.request) is not BacktestRunRequest:
            raise BacktestApiError("request must be a BacktestRunRequest")
        if type(self.execution_record) is not BacktestRunExecutionRecord:
            raise BacktestApiError("execution_record must be a BacktestRunExecutionRecord")
        _require_aware_datetime("created_at", self.created_at)
        object.__setattr__(self, "contract_version", _required_string("contract_version", self.contract_version))
        object.__setattr__(self, "schema_name", _required_string("schema_name", self.schema_name))
        object.__setattr__(self, "schema_version", _required_string("schema_version", self.schema_version))

    def with_execution_record(self, execution_record: BacktestRunExecutionRecord) -> BacktestApiRunRecord:
        return replace(self, execution_record=execution_record)


class InMemoryBacktestApiRepository:
    def __init__(self) -> None:
        self._by_run_id: dict[str, BacktestApiRunRecord] = {}
        self._by_idempotency_key: dict[str, str] = {}

    def save(self, record: BacktestApiRunRecord) -> None:
        if type(record) is not BacktestApiRunRecord:
            raise BacktestApiError("record must be a BacktestApiRunRecord")
        self._by_run_id[record.run_id] = record
        self._by_idempotency_key[record.idempotency_key] = record.run_id

    def get(self, run_id: str) -> BacktestApiRunRecord:
        normalized = _required_string("run_id", run_id)
        try:
            return self._by_run_id[normalized]
        except KeyError as exc:
            raise BacktestApiError(f"formal BacktestRun not found: {normalized}") from exc

    def get_by_idempotency_key(self, idempotency_key: str) -> BacktestApiRunRecord | None:
        run_id = self._by_idempotency_key.get(_required_string("Idempotency-Key", idempotency_key))
        return self._by_run_id[run_id] if run_id is not None else None


class FormalBacktestApiService:
    """Framework-neutral API facade for SAL-P4-020 formal portfolio backtest endpoints."""

    def __init__(
        self,
        *,
        repository: InMemoryBacktestApiRepository | None = None,
        task_backend: TaskBackend | None = None,
        resource_supervisor: BacktestRunResourceSupervisor,
        artifact_store: ArtifactStore,
        artifact_access_policy: BacktestArtifactAccessPolicy | None = None,
        clock: ClockFn | None = None,
        trace_id: str | None = None,
    ) -> None:
        if type(resource_supervisor) is not BacktestRunResourceSupervisor:
            raise BacktestApiError("resource_supervisor must be a BacktestRunResourceSupervisor")
        self._repository = repository or InMemoryBacktestApiRepository()
        self._task_backend = task_backend or InMemoryTaskBackend()
        self._resource_supervisor = resource_supervisor
        self._artifact_store = artifact_store
        self._artifact_access_policy = artifact_access_policy or BacktestArtifactAccessPolicy()
        self._clock = clock or (lambda: datetime.now(UTC))
        self._trace_id = trace_id

    def create_backtest_run(
        self,
        request: BacktestRunRequest,
        *,
        idempotency_key: str,
        resource_policy: BacktestRunResourcePolicy | None = None,
    ) -> BacktestApiResponse:
        if type(request) is not BacktestRunRequest:
            raise BacktestApiError("request must be a BacktestRunRequest")
        idempotency_key = _required_string("Idempotency-Key", idempotency_key)
        if request.idempotency_key != idempotency_key:
            raise BacktestApiError("Idempotency-Key must match BacktestRunRequest idempotency_key")
        request_hash = _request_hash(request)
        existing = self._repository.get_by_idempotency_key(idempotency_key)
        if existing is not None:
            if existing.request_hash != request_hash:
                raise BacktestApiError("Idempotency-Key was reused for a different BacktestRun API request")
            return self._accepted_response(existing)

        task_ref = self._submit_task(request=request, idempotency_key=idempotency_key)
        execution_record = self._resource_supervisor.start(request=request, resource_policy=resource_policy)
        record = BacktestApiRunRecord(
            run_id=request.run_id,
            task_id=task_ref.task_id,
            task_type=FORMAL_BACKTEST_TASK_TYPE,
            idempotency_key=idempotency_key,
            request_hash=request_hash,
            request=request,
            execution_record=execution_record,
            created_at=self._clock(),
        )
        self._repository.save(record)
        return self._accepted_response(record)

    def observe_backtest_run(
        self,
        run_id: str,
        snapshot: BacktestRunChildProcessSnapshot,
    ) -> BacktestApiResponse:
        record = self._repository.get(run_id)
        execution_record = self._resource_supervisor.observe(run_id, snapshot)
        updated = record.with_execution_record(execution_record)
        self._repository.save(updated)
        if execution_record.status is BacktestRunExecutionStatus.SUCCEEDED:
            _complete_task(
                self._task_backend,
                record.task_id,
                result={"run_id": record.run_id, "final_run_id": execution_record.final_record.run_id if execution_record.final_record else None},
            )
        elif execution_record.status in {
            BacktestRunExecutionStatus.FAILED,
            BacktestRunExecutionStatus.TIMED_OUT,
            BacktestRunExecutionStatus.OOM_KILLED,
        }:
            _fail_task(self._task_backend, record.task_id, error=execution_record.failure_reason or execution_record.status.value)
        return self._status_response(updated)

    def get_backtest_run(self, run_id: str) -> BacktestApiResponse:
        return self._status_response(self._repository.get(run_id))

    def cancel_backtest_run(self, run_id: str, *, reason: str = "cancel_requested") -> BacktestApiResponse:
        record = self._repository.get(run_id)
        self._task_backend.request_cancel(record.task_id)
        execution_record = self._resource_supervisor.request_cancel(record.run_id, reason=reason, requested_at=self._clock())
        updated = record.with_execution_record(execution_record)
        self._repository.save(updated)
        return BacktestApiResponse(
            status_code=202,
            body=self._status_body(updated),
            headers={"Location": f"/api/v1/quant/backtest-runs/{record.run_id}", "Idempotency-Key": record.idempotency_key},
        )

    def get_backtest_metrics(self, run_id: str) -> BacktestApiResponse:
        return self._single_artifact_payload_response(run_id, BacktestArtifactKind.METRICS)

    def get_backtest_audit(self, run_id: str) -> BacktestApiResponse:
        return self._single_artifact_payload_response(run_id, BacktestArtifactKind.AUDIT)

    def list_backtest_orders(
        self,
        run_id: str,
        *,
        page_size: int = 100,
        cursor: str | None = None,
    ) -> BacktestApiResponse:
        return self._table_response(run_id, BacktestArtifactKind.ORDERS, page_size=page_size, cursor=cursor)

    def list_backtest_positions(
        self,
        run_id: str,
        *,
        page_size: int = 100,
        cursor: str | None = None,
    ) -> BacktestApiResponse:
        return self._table_response(run_id, BacktestArtifactKind.POSITIONS, page_size=page_size, cursor=cursor)

    def download_backtest_artifact(
        self,
        run_id: str,
        artifact_kind: BacktestArtifactKind | str,
        *,
        subject: BacktestArtifactAccessSubject,
    ) -> BacktestApiResponse:
        record = self._repository.get(run_id)
        output = self._output_for(record, _artifact_kind(artifact_kind))
        if not self._artifact_access_policy.can_download(
            subject=subject,
            run_id=record.run_id,
            artifact_manifest=output.artifact_manifest,
        ):
            raise BacktestApiError("subject is not authorized to download this BacktestArtifact")
        return BacktestApiResponse(
            status_code=200,
            body={
                **self._base_body(record),
                "artifact": output.to_record(),
                "payload": self._artifact_payload(output),
            },
            headers={},
        )

    def _accepted_response(self, record: BacktestApiRunRecord) -> BacktestApiResponse:
        return BacktestApiResponse(
            status_code=202,
            body=self._status_body(record),
            headers={
                "Location": f"/api/v1/quant/backtest-runs/{record.run_id}",
                "Idempotency-Key": record.idempotency_key,
            },
        )

    def _status_response(self, record: BacktestApiRunRecord) -> BacktestApiResponse:
        return BacktestApiResponse(status_code=200, body=self._status_body(record), headers={})

    def _status_body(self, record: BacktestApiRunRecord) -> dict[str, Any]:
        task = self._task_backend.get(record.task_id)
        body = {
            **self._base_body(record),
            "created_at": record.created_at.isoformat(),
            "submitted_at": record.request.submitted_at.isoformat(),
            "task_id": record.task_id,
            "task_type": record.task_type,
            "task_status": task.status.value,
            "execution_status": record.execution_record.status.value,
            "termination_reason": record.execution_record.termination_reason,
            "cancel_requested_at": (
                record.execution_record.cancel_requested_at.isoformat()
                if record.execution_record.cancel_requested_at is not None
                else None
            ),
            "requested_mode": record.request.requested_mode.value,
            "effective_mode": record.execution_record.final_record.effective_mode.value if record.execution_record.final_record else record.request.requested_mode.value,
            "code_state": record.request.code_state.value,
            "patch_hash": record.request.patch_hash,
            "resource_policy": record.execution_record.resource_policy.to_record(),
            "spec": {
                "spec_id": record.request.spec.spec_id,
                "spec_hash": record.request.spec.spec_hash,
                "dataset_versions": dict(record.request.spec.dataset.dataset_versions),
                "dataset_hashes": dict(record.request.spec.dataset.dataset_hashes),
            },
            "trace": {
                "trace_id": record.request.trace_id or self._trace_id,
                "run_id": record.run_id,
                "stage_id": record.execution_record.process_id,
            },
            "runtime": _runtime_boundary_record(),
        }
        final_record = record.execution_record.final_record
        if final_record is not None:
            body.update(_final_record_body(final_record))
        return body

    def _base_body(self, record: BacktestApiRunRecord) -> dict[str, Any]:
        return {
            "contract_version": record.contract_version,
            "schema": {"name": record.schema_name, "version": record.schema_version},
            "run_id": record.run_id,
            "run_type": BACKTEST_RUN_TYPE,
            "evaluation_type": FORMAL_BACKTEST_EVALUATION_TYPE,
            "request_hash": record.request_hash,
        }

    def _submit_task(self, *, request: BacktestRunRequest, idempotency_key: str) -> TaskRef:
        return self._task_backend.submit(
            TaskCommand(
                run_id=request.run_id,
                task_type=FORMAL_BACKTEST_TASK_TYPE,
                payload={
                    "contract_version": BACKTEST_API_CONTRACT_VERSION,
                    "run_type": BACKTEST_RUN_TYPE,
                    "evaluation_type": FORMAL_BACKTEST_EVALUATION_TYPE,
                    "requested_mode": request.requested_mode.value,
                    "spec_id": request.spec.spec_id,
                    "spec_hash": request.spec.spec_hash,
                    "dataset_versions": dict(request.spec.dataset.dataset_versions),
                    "dataset_hashes": dict(request.spec.dataset.dataset_hashes),
                    "engine_version": request.engine_version,
                },
                idempotency_key=idempotency_key,
                metadata={
                    "queue": "worker-quant",
                    "resource_supervisor": "required",
                    "worker_loop_started": False,
                },
            )
        )

    def _single_artifact_payload_response(
        self,
        run_id: str,
        artifact_kind: BacktestArtifactKind,
    ) -> BacktestApiResponse:
        record = self._repository.get(run_id)
        output = self._output_for(record, artifact_kind)
        return BacktestApiResponse(
            status_code=200,
            body={
                **self._base_body(record),
                "artifact": output.to_record(),
                "payload": self._artifact_payload(output),
            },
            headers={},
        )

    def _table_response(
        self,
        run_id: str,
        artifact_kind: BacktestArtifactKind,
        *,
        page_size: int,
        cursor: str | None,
    ) -> BacktestApiResponse:
        record = self._repository.get(run_id)
        output = self._output_for(record, artifact_kind)
        rows = _artifact_rows(self._artifact_payload(output))
        page = _paginate_rows(rows, page_size=page_size, cursor=cursor)
        return BacktestApiResponse(
            status_code=200,
            body={
                **self._base_body(record),
                "artifact": output.to_record(),
                "pagination": page["pagination"],
                "rows": page["rows"],
            },
            headers={},
        )

    def _output_for(
        self,
        record: BacktestApiRunRecord,
        artifact_kind: BacktestArtifactKind,
    ) -> BacktestOutputArtifact:
        final_record = record.execution_record.final_record
        if final_record is None:
            raise BacktestApiError("formal BacktestRun has no final artifact bundle yet")
        try:
            return final_record.artifact_bundle.outputs[artifact_kind]
        except KeyError as exc:
            raise BacktestApiError(f"BacktestArtifact kind not found: {artifact_kind.value}") from exc

    def _artifact_payload(self, output: BacktestOutputArtifact) -> Any:
        raw = self._artifact_store.get_bytes(output.artifact_id)
        try:
            return json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise BacktestApiError(f"BacktestArtifact is not JSON: {output.artifact_id}") from exc


def _final_record_body(record: BacktestRunRecord) -> dict[str, Any]:
    outputs = record.artifact_bundle.outputs
    return {
        "final_status": record.status.value,
        "effective_mode": record.effective_mode.value,
        "eligible_for_ranking": record.eligible_for_ranking,
        "warning_codes": list(record.warning_codes),
        "artifact_bundle": {
            "bundle_id": record.artifact_bundle.bundle_id,
            "state": record.artifact_bundle.state.value,
            "output_artifact_ids": [output.artifact_id for output in outputs.values()],
        },
        "summary_artifact": record.summary_artifact.to_record(),
        "metrics_artifact": outputs[BacktestArtifactKind.METRICS].to_record(),
        "audit_artifact": outputs[BacktestArtifactKind.AUDIT].to_record(),
    }


def _artifact_rows(payload: Any) -> list[Mapping[str, Any]]:
    if isinstance(payload, list):
        rows = payload
    elif isinstance(payload, Mapping) and isinstance(payload.get("rows"), list):
        rows = payload["rows"]
    else:
        raise BacktestApiError("BacktestArtifact payload does not contain table rows")
    if not all(isinstance(row, Mapping) for row in rows):
        raise BacktestApiError("BacktestArtifact rows must contain objects")
    return [dict(row) for row in rows]


def _paginate_rows(
    rows: Sequence[Mapping[str, Any]],
    *,
    page_size: int,
    cursor: str | None,
) -> dict[str, Any]:
    if type(page_size) is not int or page_size <= 0:
        raise BacktestApiError("page_size must be a positive integer")
    start = _cursor_to_offset(cursor)
    end = min(start + page_size, len(rows))
    return {
        "pagination": {
            "page_size": page_size,
            "cursor": cursor,
            "next_cursor": str(end) if end < len(rows) else None,
            "total_count": len(rows),
        },
        "rows": [dict(row) for row in rows[start:end]],
    }


def _cursor_to_offset(cursor: str | None) -> int:
    if cursor is None:
        return 0
    if type(cursor) is not str or not cursor.strip():
        raise BacktestApiError("cursor must be a non-negative integer offset")
    try:
        offset = int(cursor)
    except ValueError as exc:
        raise BacktestApiError("cursor must be a non-negative integer offset") from exc
    if offset < 0:
        raise BacktestApiError("cursor must be a non-negative integer offset")
    return offset


def _complete_task(task_backend: TaskBackend, task_id: str, *, result: Mapping[str, Any]) -> TaskSnapshot | None:
    complete = getattr(task_backend, "complete", None)
    if complete is None:
        return None
    return complete(task_id, result=result, message="succeeded")


def _fail_task(task_backend: TaskBackend, task_id: str, *, error: str) -> TaskSnapshot | None:
    fail = getattr(task_backend, "fail", None)
    if fail is None:
        return None
    return fail(task_id, error=error, message="failed")


def _request_hash(request: BacktestRunRequest) -> str:
    return "sha256:" + hashlib.sha256(_canonical_json_bytes(request.request_payload())).hexdigest()


def _canonical_json_bytes(payload: Mapping[str, Any]) -> bytes:
    return json.dumps(_json_ready(payload), ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _runtime_boundary_record() -> dict[str, bool]:
    return {
        "formal_backtest_api_started": True,
        "resource_controls_started": True,
        "quant_lab_started": False,
        "evidence_agent_started": False,
        "worker_loop_started": False,
        "real_provider_calls_started": False,
        "real_llm_calls_started": False,
        "qlib_runtime_started": False,
        "legacy_signal_evaluation_started": False,
    }


def _artifact_kind(value: BacktestArtifactKind | str) -> BacktestArtifactKind:
    try:
        return value if isinstance(value, BacktestArtifactKind) else BacktestArtifactKind(str(value))
    except ValueError as exc:
        raise BacktestApiError(f"artifact_kind has invalid value: {value}") from exc


def _string_tuple(field_name: str, values: Sequence[str]) -> tuple[str, ...]:
    if isinstance(values, str):
        raise BacktestApiError(f"{field_name}s must be a sequence")
    return tuple(_required_string(field_name, str(value)) for value in values)


def _required_string(field_name: str, value: object) -> str:
    if type(value) is not str or not value.strip():
        raise BacktestApiError(f"{field_name} is required")
    return value.strip()


def _require_aware_datetime(field_name: str, value: object) -> None:
    if type(value) is not datetime or value.tzinfo is None or value.utcoffset() is None:
        raise BacktestApiError(f"{field_name} must be timezone-aware")


def _json_ready(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime | date):
        return value.isoformat()
    if isinstance(value, StrEnum):
        return value.value
    if isinstance(value, Mapping):
        return {str(key): _json_ready(item) for key, item in value.items()}
    if isinstance(value, tuple | list):
        return [_json_ready(item) for item in value]
    return value


def _json_default(value: Any) -> str:
    return str(_json_ready(value))


FORMAL_BACKTEST_API_ROUTES: tuple[BacktestApiRoute, ...] = (
    BacktestApiRoute("POST", "/api/v1/quant/backtest-runs", "createFormalBacktestRun", 202),
    BacktestApiRoute("GET", "/api/v1/quant/backtest-runs/{run_id}", "getFormalBacktestRun", 200),
    BacktestApiRoute("GET", "/api/v1/quant/backtest-runs/{run_id}/metrics", "getFormalBacktestMetrics", 200),
    BacktestApiRoute("GET", "/api/v1/quant/backtest-runs/{run_id}/orders", "listFormalBacktestOrders", 200),
    BacktestApiRoute("GET", "/api/v1/quant/backtest-runs/{run_id}/positions", "listFormalBacktestPositions", 200),
    BacktestApiRoute("GET", "/api/v1/quant/backtest-runs/{run_id}/audit", "getFormalBacktestAudit", 200),
    BacktestApiRoute(
        "GET",
        "/api/v1/quant/backtest-runs/{run_id}/artifacts/{artifact_kind}",
        "downloadFormalBacktestArtifact",
        200,
    ),
    BacktestApiRoute("POST", "/api/v1/quant/backtest-runs/{run_id}/cancel", "cancelFormalBacktestRun", 202),
)


__all__ = [
    "BACKTEST_API_CONTRACT_VERSION",
    "BACKTEST_API_RUN_SCHEMA_NAME",
    "BACKTEST_API_RUN_SCHEMA_VERSION",
    "FORMAL_BACKTEST_API_ROUTES",
    "FORMAL_BACKTEST_EVALUATION_TYPE",
    "FORMAL_BACKTEST_TASK_TYPE",
    "BacktestApiError",
    "BacktestApiResponse",
    "BacktestApiRoute",
    "BacktestApiRunRecord",
    "BacktestArtifactAccessPolicy",
    "BacktestArtifactAccessSubject",
    "FormalBacktestApiService",
    "InMemoryBacktestApiRepository",
]
