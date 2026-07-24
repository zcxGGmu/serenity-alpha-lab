from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from enum import StrEnum
from types import MappingProxyType
from typing import Any, Callable

from serenity_alpha_lab.application.task_backend import (
    InMemoryTaskBackend,
    TaskBackend,
    TaskCommand,
    TaskRef,
    TaskStatus,
)
from serenity_alpha_lab.datasets.catalog import DatasetCatalogError, DatasetVersionRef
from serenity_alpha_lab.domain.artifacts import ArtifactManifest
from serenity_alpha_lab.domain.instruments import InstrumentId
from serenity_alpha_lab.quant.factors.definitions import (
    FACTOR_DEFINITION_SCHEMA_NAME,
    FactorDefinition,
)
from serenity_alpha_lab.quant.screening.pipeline import (
    SCREEN_DEFINITION_SCHEMA_NAME,
    SCREEN_DEFINITION_SCHEMA_VERSION,
    ScreenDefinition,
)
from serenity_alpha_lab.quant.screening.snapshot import (
    SCREEN_SNAPSHOT_SCHEMA_NAME,
    SCREEN_SNAPSHOT_SCHEMA_VERSION,
    ScreenSnapshot,
    compare_screen_snapshots,
)


QUANT_SCREENING_API_CONTRACT_VERSION = "application.quant_screening_api@1.0.0"
QUANT_SCREENING_RUN_TASK_TYPE = "quant.screen.run"
QUANT_SCREENING_COMPARISON_SCHEMA_NAME = "quant.screen_snapshot_comparison"
QUANT_SCREENING_COMPARISON_SCHEMA_VERSION = "1.0.0"

_SCREEN_DEFINITION_VERSION_RE = re.compile(r"^sdv_[0-9a-f]{32,64}$")


class QuantScreeningApiError(ValueError):
    """Raised when Quant Screening API contract input is invalid."""


class QuantScreeningRunMode(StrEnum):
    PREVIEW = "preview"
    FORMAL = "formal"


@dataclass(frozen=True, slots=True)
class QuantApiRoute:
    method: str
    path: str
    operation_id: str
    response_status: int

    def __post_init__(self) -> None:
        object.__setattr__(self, "method", _required_string("method", self.method).upper())
        object.__setattr__(self, "path", _required_string("path", self.path))
        object.__setattr__(self, "operation_id", _required_string("operation_id", self.operation_id))
        if type(self.response_status) is not int or self.response_status < 100 or self.response_status > 599:
            raise QuantScreeningApiError("response_status must be a valid HTTP status code")

    def to_record(self) -> dict[str, object]:
        return {
            "method": self.method,
            "path": self.path,
            "operation_id": self.operation_id,
            "response_status": self.response_status,
        }


@dataclass(frozen=True, slots=True)
class QuantApiResponse:
    status_code: int
    body: Mapping[str, Any]
    headers: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if type(self.status_code) is not int or self.status_code < 100 or self.status_code > 599:
            raise QuantScreeningApiError("status_code must be a valid HTTP status code")
        json.dumps(self.body, sort_keys=True, default=_json_default)
        object.__setattr__(self, "body", _json_ready(self.body))
        object.__setattr__(self, "headers", dict(self.headers))


@dataclass(frozen=True, slots=True)
class QuantScreeningRunRequest:
    screen_definition_id: str
    screen_definition_version_id: str
    as_of: date
    dataset_versions: Mapping[str, str]
    screen_snapshot: ScreenSnapshot
    run_mode: QuantScreeningRunMode | str = QuantScreeningRunMode.PREVIEW
    submitted_by: str | None = None
    artifact_manifest: ArtifactManifest | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def from_snapshot(
        cls,
        *,
        screen_definition_id: str,
        screen_definition_version_id: str,
        snapshot: ScreenSnapshot,
        run_mode: QuantScreeningRunMode | str = QuantScreeningRunMode.PREVIEW,
        submitted_by: str | None = None,
        artifact_manifest: ArtifactManifest | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> QuantScreeningRunRequest:
        return cls(
            screen_definition_id=screen_definition_id,
            screen_definition_version_id=screen_definition_version_id,
            as_of=snapshot.as_of,
            dataset_versions=snapshot.dataset_versions,
            screen_snapshot=snapshot,
            run_mode=run_mode,
            submitted_by=submitted_by,
            artifact_manifest=artifact_manifest,
            metadata=metadata or {},
        )

    def __post_init__(self) -> None:
        object.__setattr__(self, "screen_definition_id", _required_string("screen_definition_id", self.screen_definition_id))
        object.__setattr__(
            self,
            "screen_definition_version_id",
            _validate_screen_definition_version(self.screen_definition_version_id),
        )
        _require_date("as_of", self.as_of)
        object.__setattr__(self, "dataset_versions", _normalize_dataset_versions(self.dataset_versions))
        if type(self.screen_snapshot) is not ScreenSnapshot:
            raise QuantScreeningApiError("screen_snapshot must be a ScreenSnapshot")
        if self.screen_snapshot.definition_version_id != self.screen_definition_version_id:
            raise QuantScreeningApiError("screen_snapshot definition_version_id must match request")
        if self.screen_snapshot.as_of != self.as_of:
            raise QuantScreeningApiError("screen_snapshot as_of must match request")
        if dict(self.screen_snapshot.dataset_versions) != dict(self.dataset_versions):
            raise QuantScreeningApiError("screen_snapshot dataset_versions must match request")
        object.__setattr__(self, "run_mode", QuantScreeningRunMode(self.run_mode))
        object.__setattr__(self, "submitted_by", _optional_string(self.submitted_by))
        if self.artifact_manifest is not None and type(self.artifact_manifest) is not ArtifactManifest:
            raise QuantScreeningApiError("artifact_manifest must be an ArtifactManifest")
        object.__setattr__(self, "metadata", _freeze_json_mapping(self.metadata))

    @property
    def request_hash(self) -> str:
        return hashlib.sha256(self._identity_json().encode("utf-8")).hexdigest()

    def to_task_payload(self) -> dict[str, Any]:
        return {
            "contract_version": QUANT_SCREENING_API_CONTRACT_VERSION,
            "run_mode": self.run_mode.value,
            "screen_definition_id": self.screen_definition_id,
            "screen_definition_version_id": self.screen_definition_version_id,
            "as_of": self.as_of.isoformat(),
            "dataset_versions": dict(self.dataset_versions),
            "screen_snapshot_id": self.screen_snapshot.screen_snapshot_id,
            "pipeline_snapshot_id": self.screen_snapshot.pipeline_snapshot_id,
            "artifact": self.artifact_manifest.to_record() if self.artifact_manifest is not None else None,
            "metadata": _thaw_value(self.metadata),
        }

    def _identity_json(self) -> str:
        return json.dumps(self.to_task_payload(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))


@dataclass(frozen=True, slots=True)
class QuantScreeningRunRecord:
    run_id: str
    task_id: str
    status: TaskStatus | str
    request_hash: str
    idempotency_key: str
    task_type: str
    run_mode: QuantScreeningRunMode | str
    screen_definition_id: str
    screen_definition_version_id: str
    as_of: date
    dataset_versions: Mapping[str, str]
    screen_snapshot: ScreenSnapshot
    created_at: datetime
    trace_id: str
    stage_id: str
    submitted_by: str | None = None
    artifact_manifest: ArtifactManifest | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "run_id", _required_string("run_id", self.run_id))
        object.__setattr__(self, "task_id", _required_string("task_id", self.task_id))
        object.__setattr__(self, "status", TaskStatus(self.status))
        object.__setattr__(self, "request_hash", _required_string("request_hash", self.request_hash))
        object.__setattr__(self, "idempotency_key", _required_string("idempotency_key", self.idempotency_key))
        object.__setattr__(self, "task_type", _required_string("task_type", self.task_type))
        object.__setattr__(self, "run_mode", QuantScreeningRunMode(self.run_mode))
        object.__setattr__(self, "screen_definition_id", _required_string("screen_definition_id", self.screen_definition_id))
        object.__setattr__(
            self,
            "screen_definition_version_id",
            _validate_screen_definition_version(self.screen_definition_version_id),
        )
        _require_date("as_of", self.as_of)
        object.__setattr__(self, "dataset_versions", _normalize_dataset_versions(self.dataset_versions))
        if type(self.screen_snapshot) is not ScreenSnapshot:
            raise QuantScreeningApiError("screen_snapshot must be a ScreenSnapshot")
        _require_aware_datetime("created_at", self.created_at)
        object.__setattr__(self, "trace_id", _required_string("trace_id", self.trace_id))
        object.__setattr__(self, "stage_id", _required_string("stage_id", self.stage_id))
        object.__setattr__(self, "submitted_by", _optional_string(self.submitted_by))
        if self.artifact_manifest is not None and type(self.artifact_manifest) is not ArtifactManifest:
            raise QuantScreeningApiError("artifact_manifest must be an ArtifactManifest")

    def accepted_body(self) -> dict[str, Any]:
        return {
            "contract_version": QUANT_SCREENING_API_CONTRACT_VERSION,
            "run_id": self.run_id,
            "task_id": self.task_id,
            "task_type": self.task_type,
            "status": self.status.value,
            "run_type": self.task_type,
            "run_mode": self.run_mode.value,
            "screen_definition_id": self.screen_definition_id,
            "screen_definition_version_id": self.screen_definition_version_id,
            "screen_snapshot_id": self.screen_snapshot.screen_snapshot_id,
            "pipeline_snapshot_id": self.screen_snapshot.pipeline_snapshot_id,
            "as_of": self.as_of.isoformat(),
            "dataset_versions": dict(self.dataset_versions),
            "schema": {"name": self.screen_snapshot.schema_name, "version": self.screen_snapshot.schema_version},
            "trace": self.trace_record(),
            "artifact": self.artifact_manifest.to_record() if self.artifact_manifest is not None else None,
            "created_at": self.created_at.isoformat(),
            "submitted_by": self.submitted_by,
        }

    def trace_record(self) -> dict[str, str]:
        return {"trace_id": self.trace_id, "run_id": self.run_id, "stage_id": self.stage_id}


class InMemoryQuantScreeningRepository:
    """Small deterministic store for Quant Screening API contract tests and desktop previews."""

    def __init__(self) -> None:
        self._factor_definitions: dict[str, FactorDefinition] = {}
        self._screen_definitions: dict[str, ScreenDefinition] = {}
        self._runs: dict[str, QuantScreeningRunRecord] = {}
        self._idempotency_index: dict[str, str] = {}

    def save_factor_definition(self, definition: FactorDefinition) -> None:
        if type(definition) is not FactorDefinition:
            raise QuantScreeningApiError("definition must be a FactorDefinition")
        self._factor_definitions[_factor_definition_key(definition)] = definition

    def save_screen_definition(self, definition: ScreenDefinition) -> None:
        if type(definition) is not ScreenDefinition:
            raise QuantScreeningApiError("definition must be a ScreenDefinition")
        self._screen_definitions[definition.definition_version_id] = definition

    def get_screen_definition(self, version_id: str) -> ScreenDefinition:
        version_id = _validate_screen_definition_version(version_id)
        try:
            return self._screen_definitions[version_id]
        except KeyError as exc:
            raise QuantScreeningApiError(f"screen definition not found: {version_id}") from exc

    def save_run(self, record: QuantScreeningRunRecord) -> None:
        if type(record) is not QuantScreeningRunRecord:
            raise QuantScreeningApiError("record must be a QuantScreeningRunRecord")
        self._runs[record.run_id] = record
        self._idempotency_index[record.idempotency_key] = record.run_id

    def get_run(self, run_id: str) -> QuantScreeningRunRecord:
        run_id = _required_string("run_id", run_id)
        try:
            return self._runs[run_id]
        except KeyError as exc:
            raise QuantScreeningApiError(f"screen run not found: {run_id}") from exc

    def get_run_by_idempotency_key(self, idempotency_key: str) -> QuantScreeningRunRecord | None:
        run_id = self._idempotency_index.get(_required_string("Idempotency-Key", idempotency_key))
        return self._runs[run_id] if run_id is not None else None


class QuantScreeningApiService:
    """Framework-neutral API facade for SAL-P3-014 Quant Screening endpoints."""

    def __init__(
        self,
        *,
        repository: InMemoryQuantScreeningRepository | None = None,
        task_backend: TaskBackend | None = None,
        clock: Callable[[], datetime] | None = None,
        trace_id: str | None = None,
    ) -> None:
        self._repository = repository or InMemoryQuantScreeningRepository()
        self._task_backend = task_backend or InMemoryTaskBackend()
        self._clock = clock or (lambda: datetime.now(UTC))
        self._trace_id = trace_id

    def create_factor_definition(self, definition: FactorDefinition) -> QuantApiResponse:
        if type(definition) is not FactorDefinition:
            raise QuantScreeningApiError("definition must be a FactorDefinition")
        self._repository.save_factor_definition(definition)
        body = {
            "contract_version": QUANT_SCREENING_API_CONTRACT_VERSION,
            "schema": {"name": definition.schema_name, "version": definition.schema_version},
            "factor_definition": definition.to_record(),
            "trace": self._trace_record(run_id=definition.created_by_run_id, stage_id=None),
        }
        return QuantApiResponse(
            status_code=201,
            body=body,
            headers={"Location": f"/api/v1/quant/factor-definitions/{_factor_definition_key(definition)}"},
        )

    def create_screen_definition(self, definition: ScreenDefinition) -> QuantApiResponse:
        if type(definition) is not ScreenDefinition:
            raise QuantScreeningApiError("definition must be a ScreenDefinition")
        self._repository.save_screen_definition(definition)
        body = {
            "contract_version": QUANT_SCREENING_API_CONTRACT_VERSION,
            "schema": {"name": SCREEN_DEFINITION_SCHEMA_NAME, "version": SCREEN_DEFINITION_SCHEMA_VERSION},
            "screen_definition": definition.to_record(),
            "trace": self._trace_record(run_id=definition.created_by_run_id, stage_id=None),
        }
        return QuantApiResponse(
            status_code=201,
            body=body,
            headers={"Location": f"/api/v1/quant/screen-definitions/{definition.definition_version_id}"},
        )

    def create_screen_run(
        self,
        request: QuantScreeningRunRequest,
        *,
        idempotency_key: str,
    ) -> QuantApiResponse:
        if type(request) is not QuantScreeningRunRequest:
            raise QuantScreeningApiError("request must be a QuantScreeningRunRequest")
        idempotency_key = _required_string("Idempotency-Key", idempotency_key)
        existing = self._repository.get_run_by_idempotency_key(idempotency_key)
        if existing is not None:
            if existing.request_hash != request.request_hash:
                raise QuantScreeningApiError("Idempotency-Key was reused for a different Quant Screening request")
            return self._accepted_response(existing)

        definition = self._repository.get_screen_definition(request.screen_definition_version_id)
        if definition.definition_id != request.screen_definition_id:
            raise QuantScreeningApiError("screen_definition_id does not match the stored ScreenDefinition")

        run_id = _stable_id("run_qs", {"idempotency_key": idempotency_key, "request_hash": request.request_hash})
        task_ref = self._submit_screen_task(run_id=run_id, request=request, idempotency_key=idempotency_key)
        trace_id = request.screen_snapshot.trace_id or self._trace_id or _stable_id("trace", {"run_id": run_id})
        stage_id = request.screen_snapshot.stage_id or "stage-quant-screening-api"
        record = QuantScreeningRunRecord(
            run_id=run_id,
            task_id=task_ref.task_id,
            status=task_ref.status,
            request_hash=request.request_hash,
            idempotency_key=idempotency_key,
            task_type=QUANT_SCREENING_RUN_TASK_TYPE,
            run_mode=request.run_mode,
            screen_definition_id=request.screen_definition_id,
            screen_definition_version_id=request.screen_definition_version_id,
            as_of=request.as_of,
            dataset_versions=request.dataset_versions,
            screen_snapshot=request.screen_snapshot,
            artifact_manifest=request.artifact_manifest,
            created_at=self._clock(),
            trace_id=trace_id,
            stage_id=stage_id,
            submitted_by=request.submitted_by,
        )
        self._repository.save_run(record)
        return self._accepted_response(record)

    def get_screen_run(self, run_id: str) -> QuantApiResponse:
        record = self._repository.get_run(run_id)
        return QuantApiResponse(status_code=200, body=record.accepted_body(), headers={})

    def get_screen_run_results(
        self,
        run_id: str,
        *,
        page_size: int = 100,
        cursor: str | None = None,
    ) -> QuantApiResponse:
        record = self._repository.get_run(run_id)
        start = _cursor_to_offset(cursor)
        if type(page_size) is not int or page_size <= 0:
            raise QuantScreeningApiError("page_size must be a positive integer")
        results = tuple(record.screen_snapshot.results)
        end = min(start + page_size, len(results))
        next_cursor = str(end) if end < len(results) else None
        body = self._result_base_body(record)
        body.update(
            {
                "pagination": {
                    "page_size": page_size,
                    "cursor": cursor,
                    "next_cursor": next_cursor,
                    "total_count": len(results),
                },
                "results": [result.to_record() for result in results[start:end]],
            }
        )
        return QuantApiResponse(status_code=200, body=body, headers={})

    def get_screen_run_result(self, run_id: str, instrument_id: str) -> QuantApiResponse:
        record = self._repository.get_run(run_id)
        result = record.screen_snapshot.result_for(instrument_id)
        body = self._result_base_body(record)
        body["result"] = result.to_record()
        return QuantApiResponse(status_code=200, body=body, headers={})

    def compare_screen_runs(self, previous_run_id: str, current_run_id: str) -> QuantApiResponse:
        previous = self._repository.get_run(previous_run_id)
        current = self._repository.get_run(current_run_id)
        comparison = compare_screen_snapshots(previous.screen_snapshot, current.screen_snapshot)
        body = {
            "contract_version": QUANT_SCREENING_API_CONTRACT_VERSION,
            "schema": {
                "name": QUANT_SCREENING_COMPARISON_SCHEMA_NAME,
                "version": QUANT_SCREENING_COMPARISON_SCHEMA_VERSION,
            },
            "previous_run_id": previous.run_id,
            "current_run_id": current.run_id,
            "previous_screen_snapshot_id": previous.screen_snapshot.screen_snapshot_id,
            "current_screen_snapshot_id": current.screen_snapshot.screen_snapshot_id,
            "as_of": current.as_of.isoformat(),
            "dataset_versions": dict(current.dataset_versions),
            "trace": current.trace_record(),
            "comparison": comparison.to_record(),
        }
        return QuantApiResponse(status_code=200, body=body, headers={})

    def _accepted_response(self, record: QuantScreeningRunRecord) -> QuantApiResponse:
        return QuantApiResponse(
            status_code=202,
            body=record.accepted_body(),
            headers={
                "Location": f"/api/v1/quant/screen-runs/{record.run_id}",
                "Idempotency-Key": record.idempotency_key,
            },
        )

    def _submit_screen_task(
        self,
        *,
        run_id: str,
        request: QuantScreeningRunRequest,
        idempotency_key: str,
    ) -> TaskRef:
        return self._task_backend.submit(
            TaskCommand(
                run_id=run_id,
                task_type=QUANT_SCREENING_RUN_TASK_TYPE,
                payload=request.to_task_payload(),
                idempotency_key=idempotency_key,
                metadata={
                    "screen_definition_version_id": request.screen_definition_version_id,
                    "screen_snapshot_id": request.screen_snapshot.screen_snapshot_id,
                    "run_mode": request.run_mode.value,
                },
            )
        )

    def _result_base_body(self, record: QuantScreeningRunRecord) -> dict[str, Any]:
        snapshot = record.screen_snapshot
        return {
            "contract_version": QUANT_SCREENING_API_CONTRACT_VERSION,
            "schema": {"name": snapshot.schema_name, "version": snapshot.schema_version},
            "run_id": record.run_id,
            "task_id": record.task_id,
            "status": record.status.value,
            "screen_definition_id": record.screen_definition_id,
            "screen_definition_version_id": record.screen_definition_version_id,
            "screen_snapshot_id": snapshot.screen_snapshot_id,
            "pipeline_snapshot_id": snapshot.pipeline_snapshot_id,
            "as_of": record.as_of.isoformat(),
            "dataset_versions": dict(record.dataset_versions),
            "trace": record.trace_record(),
            "artifact": record.artifact_manifest.to_record() if record.artifact_manifest is not None else None,
        }

    def _trace_record(self, *, run_id: str | None, stage_id: str | None) -> dict[str, str | None]:
        return {"trace_id": self._trace_id, "run_id": run_id, "stage_id": stage_id}


def _factor_definition_key(definition: FactorDefinition) -> str:
    return f"{definition.definition_id}@{definition.semantic_version}"


def _cursor_to_offset(cursor: str | None) -> int:
    if cursor is None:
        return 0
    if type(cursor) is not str or not cursor.strip():
        raise QuantScreeningApiError("cursor must be a non-negative integer offset")
    try:
        offset = int(cursor)
    except ValueError as exc:
        raise QuantScreeningApiError("cursor must be a non-negative integer offset") from exc
    if offset < 0:
        raise QuantScreeningApiError("cursor must be a non-negative integer offset")
    return offset


def _normalize_dataset_versions(dataset_versions: Mapping[str, str]) -> Mapping[str, str]:
    if not isinstance(dataset_versions, Mapping):
        raise QuantScreeningApiError("dataset_versions must map names to concrete Dataset Version ids")
    if not dataset_versions:
        raise QuantScreeningApiError("dataset_versions are required")
    normalized = {
        _required_string("dataset name", name): _validate_dataset_version(version)
        for name, version in dataset_versions.items()
    }
    return MappingProxyType(dict(sorted(normalized.items())))


def _validate_dataset_version(value: object) -> str:
    version = _required_string("dataset_version", value)
    if version.lower() == "latest":
        raise QuantScreeningApiError("Quant Screening API requires concrete Dataset Version ids; latest is not allowed")
    try:
        DatasetVersionRef.version(version)
    except (DatasetCatalogError, ValueError) as exc:
        raise QuantScreeningApiError("Quant Screening API requires concrete Dataset Version ids") from exc
    return version


def _validate_screen_definition_version(value: object) -> str:
    version = _required_string("screen_definition_version_id", value)
    if not _SCREEN_DEFINITION_VERSION_RE.fullmatch(version):
        raise QuantScreeningApiError("screen_definition_version_id must be sdv_<hex>")
    return version


def _stable_id(prefix: str, payload: Mapping[str, object]) -> str:
    content = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=_json_default, separators=(",", ":"))
    return f"{prefix}_{hashlib.sha256(content.encode('utf-8')).hexdigest()[:32]}"


def _require_date(field_name: str, value: object) -> None:
    if type(value) is not date:
        raise QuantScreeningApiError(f"{field_name} must be a date")


def _required_string(field_name: str, value: object) -> str:
    if type(value) is not str:
        raise QuantScreeningApiError(f"{field_name} is required")
    stripped = value.strip()
    if not stripped:
        raise QuantScreeningApiError(f"{field_name} is required")
    return stripped


def _optional_string(value: str | None) -> str | None:
    if value is None:
        return None
    return _required_string("value", value)


def _require_aware_datetime(field_name: str, value: object) -> None:
    if type(value) is not datetime or value.tzinfo is None or value.utcoffset() is None:
        raise QuantScreeningApiError(f"{field_name} must be timezone-aware")


def _freeze_json_mapping(value: Mapping[str, Any]) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise QuantScreeningApiError("value must be a mapping")
    json.dumps(value, sort_keys=True, default=_json_default)
    return MappingProxyType({str(key): _freeze_value(item) for key, item in value.items()})


def _freeze_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return _freeze_json_mapping(value)
    if isinstance(value, list):
        return tuple(_freeze_value(item) for item in value)
    if isinstance(value, tuple):
        return tuple(_freeze_value(item) for item in value)
    return value


def _thaw_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw_value(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw_value(item) for item in value]
    return value


def _json_ready(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_ready(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_json_ready(item) for item in value]
    if isinstance(value, list):
        return [_json_ready(item) for item in value]
    return value


def _json_default(value: Any) -> str:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, InstrumentId):
        return value.canonical
    return str(value)


QUANT_SCREENING_API_ROUTES: tuple[QuantApiRoute, ...] = (
    QuantApiRoute("POST", "/api/v1/quant/factor-definitions", "createQuantFactorDefinition", 201),
    QuantApiRoute("POST", "/api/v1/quant/screen-definitions", "createQuantScreenDefinition", 201),
    QuantApiRoute("POST", "/api/v1/quant/screen-runs", "createQuantScreenRun", 202),
    QuantApiRoute("GET", "/api/v1/quant/screen-runs/{run_id}", "getQuantScreenRun", 200),
    QuantApiRoute("GET", "/api/v1/quant/screen-runs/{run_id}/results", "listQuantScreenRunResults", 200),
    QuantApiRoute(
        "GET",
        "/api/v1/quant/screen-runs/{run_id}/results/{instrument_id}",
        "getQuantScreenRunResult",
        200,
    ),
    QuantApiRoute("GET", "/api/v1/quant/screen-runs/{run_id}/comparison", "compareQuantScreenRuns", 200),
)
