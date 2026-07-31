from __future__ import annotations

import hashlib
import json
import re
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from math import isfinite
from pathlib import Path
from types import MappingProxyType
from typing import Any
from urllib.parse import quote

from serenity_alpha_lab.datasets.catalog import DatasetCatalogError, DatasetVersionRef


FACTOR_DEFINITION_CONTRACT_VERSION = "1.0.0"
FACTOR_DEFINITION_SCHEMA_NAME = "quant.factor_definition"
FACTOR_DEFINITION_SCHEMA_VERSION = "1.0.0"

_FACTOR_VERSION_ID_RE = re.compile(r"^fdv_[0-9a-f]{32,64}$")
_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_SEMANTIC_VERSION_RE = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+(?:[-+][0-9A-Za-z.-]+)?$")


class FactorDefinitionError(ValueError):
    """Raised when a FactorDefinition contract or repository operation is invalid."""


class FactorDefinitionStatus(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"
    RETIRED = "retired"


class FactorDirection(StrEnum):
    HIGHER_IS_BETTER = "higher_is_better"
    LOWER_IS_BETTER = "lower_is_better"
    NEUTRAL = "neutral"


class FactorInputKind(StrEnum):
    DATASET_FIELD = "dataset_field"
    FACTOR_VALUE = "factor_value"


class MissingValueStrategy(StrEnum):
    DROP = "drop"
    FORWARD_FILL = "forward_fill"
    FILL_CONSTANT = "fill_constant"
    ZERO = "zero"


@dataclass(frozen=True, slots=True)
class FactorFormula:
    expression: str
    language: str = "serenity_factor_dsl"
    engine_version: str = "draft"

    @classmethod
    def from_record(cls, record: Mapping[str, object]) -> FactorFormula:
        return cls(
            expression=str(record["expression"]),
            language=str(record.get("language", "serenity_factor_dsl")),
            engine_version=str(record.get("engine_version", "draft")),
        )

    def __post_init__(self) -> None:
        object.__setattr__(self, "expression", _required_string("formula expression", self.expression))
        object.__setattr__(self, "language", _required_string("formula language", self.language))
        object.__setattr__(self, "engine_version", _required_string("formula engine_version", self.engine_version))

    def to_record(self) -> dict[str, str]:
        return {
            "expression": self.expression,
            "language": self.language,
            "engine_version": self.engine_version,
        }


@dataclass(frozen=True, slots=True)
class FactorInput:
    input_id: str
    dataset_name: str
    dataset_version: str
    field_name: str
    kind: FactorInputKind | str = FactorInputKind.DATASET_FIELD
    data_type: str | None = None
    required: bool = True
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def from_record(cls, record: Mapping[str, object]) -> FactorInput:
        return cls(
            input_id=str(record["input_id"]),
            dataset_name=str(record["dataset_name"]),
            dataset_version=str(record["dataset_version"]),
            field_name=str(record["field_name"]),
            kind=str(record.get("kind", FactorInputKind.DATASET_FIELD.value)),
            data_type=_optional_record_string(record.get("data_type")),
            required=bool(record.get("required", True)),
            metadata=dict(record.get("metadata", {})),
        )

    def __post_init__(self) -> None:
        object.__setattr__(self, "input_id", _required_string("input_id", self.input_id))
        object.__setattr__(self, "dataset_name", _required_string("dataset_name", self.dataset_name))
        object.__setattr__(self, "dataset_version", _validate_dataset_version(self.dataset_version))
        object.__setattr__(self, "field_name", _required_string("field_name", self.field_name))
        object.__setattr__(self, "kind", FactorInputKind(self.kind))
        object.__setattr__(self, "data_type", _optional_string(self.data_type))
        if type(self.required) is not bool:
            raise FactorDefinitionError("input required must be boolean")
        object.__setattr__(self, "metadata", _freeze_mapping(self.metadata))

    def to_record(self) -> dict[str, Any]:
        record: dict[str, Any] = {
            "input_id": self.input_id,
            "kind": self.kind.value,
            "dataset_name": self.dataset_name,
            "dataset_version": self.dataset_version,
            "field_name": self.field_name,
            "required": self.required,
        }
        _set_if_present(record, "data_type", self.data_type)
        if self.metadata:
            record["metadata"] = _thaw_value(self.metadata)
        return record


@dataclass(frozen=True, slots=True)
class FactorWindow:
    name: str
    length: int
    unit: str = "trading_day"
    min_periods: int | None = None

    @classmethod
    def from_record(cls, record: Mapping[str, object]) -> FactorWindow:
        return cls(
            name=str(record["name"]),
            length=int(record["length"]),
            unit=str(record.get("unit", "trading_day")),
            min_periods=None if record.get("min_periods") is None else int(record["min_periods"]),
        )

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", _required_string("window name", self.name))
        if type(self.length) is not int or self.length <= 0:
            raise FactorDefinitionError("window length must be a positive integer")
        object.__setattr__(self, "unit", _required_string("window unit", self.unit))
        if self.min_periods is not None:
            if type(self.min_periods) is not int or self.min_periods <= 0:
                raise FactorDefinitionError("window min_periods must be a positive integer")
            if self.min_periods > self.length:
                raise FactorDefinitionError("window min_periods cannot exceed length")

    def to_record(self) -> dict[str, Any]:
        record: dict[str, Any] = {
            "name": self.name,
            "length": self.length,
            "unit": self.unit,
        }
        _set_if_present(record, "min_periods", self.min_periods)
        return record


@dataclass(frozen=True, slots=True)
class MissingValuePolicy:
    strategy: MissingValueStrategy | str
    fill_value: float | str | None = None
    max_missing_ratio: float | None = None

    @classmethod
    def from_record(cls, record: Mapping[str, object]) -> MissingValuePolicy:
        return cls(
            strategy=str(record["strategy"]),
            fill_value=record.get("fill_value"),  # type: ignore[arg-type]
            max_missing_ratio=None if record.get("max_missing_ratio") is None else float(record["max_missing_ratio"]),
        )

    def __post_init__(self) -> None:
        object.__setattr__(self, "strategy", MissingValueStrategy(self.strategy))
        if self.strategy is MissingValueStrategy.FILL_CONSTANT and self.fill_value is None:
            raise FactorDefinitionError("fill_value is required when strategy is fill_constant")
        if self.strategy is not MissingValueStrategy.FILL_CONSTANT and self.fill_value is not None:
            raise FactorDefinitionError("fill_value is only valid when strategy is fill_constant")
        if self.fill_value is not None:
            if type(self.fill_value) in {int, float}:
                if not isfinite(float(self.fill_value)):
                    raise FactorDefinitionError("fill_value must be finite")
                object.__setattr__(self, "fill_value", float(self.fill_value))
            elif type(self.fill_value) is str:
                object.__setattr__(self, "fill_value", _required_string("fill_value", self.fill_value))
            else:
                raise FactorDefinitionError("fill_value must be numeric or string")
        if self.max_missing_ratio is not None:
            object.__setattr__(
                self,
                "max_missing_ratio",
                _finite_float("max_missing_ratio", self.max_missing_ratio, minimum=0.0, maximum=1.0),
            )

    def to_record(self) -> dict[str, Any]:
        record: dict[str, Any] = {"strategy": self.strategy.value}
        _set_if_present(record, "fill_value", self.fill_value)
        _set_if_present(record, "max_missing_ratio", self.max_missing_ratio)
        return record


@dataclass(frozen=True, slots=True)
class PostProcessingStep:
    method: str
    parameters: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def from_record(cls, record: Mapping[str, object]) -> PostProcessingStep:
        return cls(
            method=str(record["method"]),
            parameters=dict(record.get("parameters", {})),
        )

    def __post_init__(self) -> None:
        object.__setattr__(self, "method", _required_string("post_process method", self.method))
        object.__setattr__(self, "parameters", _freeze_mapping(self.parameters))

    def to_record(self) -> dict[str, Any]:
        return {
            "method": self.method,
            "parameters": _thaw_value(self.parameters),
        }


@dataclass(frozen=True, slots=True)
class FactorDefinitionRetirement:
    version_id: str
    retired_at: datetime
    retired_by_run_id: str
    reason: str
    trace_id: str | None = None

    @classmethod
    def from_record(cls, record: Mapping[str, object]) -> FactorDefinitionRetirement:
        return cls(
            version_id=str(record["version_id"]),
            retired_at=datetime.fromisoformat(str(record["retired_at"])),
            retired_by_run_id=str(record["retired_by_run_id"]),
            reason=str(record["reason"]),
            trace_id=_optional_record_string(record.get("trace_id")),
        )

    def __post_init__(self) -> None:
        object.__setattr__(self, "version_id", _validate_version_id(self.version_id))
        _require_aware_datetime("retired_at", self.retired_at)
        object.__setattr__(self, "retired_by_run_id", _required_string("retired_by_run_id", self.retired_by_run_id))
        object.__setattr__(self, "reason", _required_string("reason", self.reason))
        object.__setattr__(self, "trace_id", _optional_string(self.trace_id))

    @property
    def status(self) -> FactorDefinitionStatus:
        return FactorDefinitionStatus.RETIRED

    def to_record(self) -> dict[str, Any]:
        record: dict[str, Any] = {
            "version_id": self.version_id,
            "status": self.status.value,
            "retired_at": self.retired_at.isoformat(),
            "retired_by_run_id": self.retired_by_run_id,
            "reason": self.reason,
        }
        _set_if_present(record, "trace_id", self.trace_id)
        return record


@dataclass(frozen=True, slots=True)
class FactorDefinitionAuditEvent:
    action: str
    definition_id: str
    semantic_version: str
    created_at: datetime
    actor_run_id: str
    version_id: str | None = None
    details: Mapping[str, Any] = field(default_factory=dict)
    event_id: str | None = None

    @classmethod
    def from_record(cls, record: Mapping[str, object]) -> FactorDefinitionAuditEvent:
        return cls(
            action=str(record["action"]),
            definition_id=str(record["definition_id"]),
            semantic_version=str(record["semantic_version"]),
            version_id=_optional_record_string(record.get("version_id")),
            created_at=datetime.fromisoformat(str(record["created_at"])),
            actor_run_id=str(record["actor_run_id"]),
            details=dict(record.get("details", {})),
            event_id=_optional_record_string(record.get("event_id")),
        )

    def __post_init__(self) -> None:
        object.__setattr__(self, "action", _required_string("action", self.action))
        object.__setattr__(self, "definition_id", _required_string("definition_id", self.definition_id))
        object.__setattr__(self, "semantic_version", _validate_semantic_version(self.semantic_version))
        if self.version_id is not None:
            object.__setattr__(self, "version_id", _validate_version_id(self.version_id))
        _require_aware_datetime("created_at", self.created_at)
        object.__setattr__(self, "actor_run_id", _required_string("actor_run_id", self.actor_run_id))
        object.__setattr__(self, "details", _freeze_mapping(self.details))
        event_id = self.event_id or _derive_audit_event_id(self)
        object.__setattr__(self, "event_id", _required_string("event_id", event_id))

    def to_record(self) -> dict[str, Any]:
        record: dict[str, Any] = {
            "event_id": self.event_id,
            "action": self.action,
            "definition_id": self.definition_id,
            "semantic_version": self.semantic_version,
            "created_at": self.created_at.isoformat(),
            "actor_run_id": self.actor_run_id,
            "details": _thaw_value(self.details),
        }
        _set_if_present(record, "version_id", self.version_id)
        return record


@dataclass(frozen=True, slots=True)
class FactorDefinition:
    definition_id: str
    semantic_version: str
    name: str
    description: str
    category: str
    direction: FactorDirection
    formula: FactorFormula
    inputs: tuple[FactorInput, ...]
    windows: tuple[FactorWindow, ...]
    missing_value_policy: MissingValuePolicy
    post_process: tuple[PostProcessingStep, ...]
    implementation_hash: str
    created_at: datetime
    created_by_run_id: str
    source_commit: str
    status: FactorDefinitionStatus = FactorDefinitionStatus.DRAFT
    contract_version: str = FACTOR_DEFINITION_CONTRACT_VERSION
    schema_name: str = FACTOR_DEFINITION_SCHEMA_NAME
    schema_version: str = FACTOR_DEFINITION_SCHEMA_VERSION
    version_id: str | None = None
    spec_hash: str | None = None
    published_at: datetime | None = None
    published_by_run_id: str | None = None
    published_by_stage_id: str | None = None
    trace_id: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def draft(
        cls,
        *,
        definition_id: str,
        semantic_version: str,
        name: str,
        description: str,
        category: str,
        direction: FactorDirection | str,
        formula: FactorFormula,
        inputs: Sequence[FactorInput],
        windows: Sequence[FactorWindow] = (),
        missing_value_policy: MissingValuePolicy | None = None,
        post_process: Sequence[PostProcessingStep] = (),
        implementation_hash: str,
        created_at: datetime,
        created_by_run_id: str,
        source_commit: str,
        metadata: Mapping[str, Any] | None = None,
    ) -> FactorDefinition:
        return cls(
            definition_id=definition_id,
            semantic_version=semantic_version,
            name=name,
            description=description,
            category=category,
            direction=FactorDirection(direction),
            formula=formula,
            inputs=tuple(inputs),
            windows=tuple(windows),
            missing_value_policy=missing_value_policy or MissingValuePolicy(strategy=MissingValueStrategy.DROP),
            post_process=tuple(post_process),
            implementation_hash=implementation_hash,
            created_at=created_at,
            created_by_run_id=created_by_run_id,
            source_commit=source_commit,
            status=FactorDefinitionStatus.DRAFT,
            metadata=metadata or {},
        )

    @classmethod
    def from_record(cls, record: Mapping[str, object]) -> FactorDefinition:
        return cls(
            definition_id=str(record["definition_id"]),
            semantic_version=str(record["semantic_version"]),
            name=str(record["name"]),
            description=str(record["description"]),
            category=str(record["category"]),
            direction=FactorDirection(str(record["direction"])),
            formula=FactorFormula.from_record(record["formula"]),  # type: ignore[arg-type]
            inputs=tuple(FactorInput.from_record(item) for item in record["inputs"]),  # type: ignore[index]
            windows=tuple(FactorWindow.from_record(item) for item in record.get("windows", ())),  # type: ignore[arg-type]
            missing_value_policy=MissingValuePolicy.from_record(record["missing_value_policy"]),  # type: ignore[arg-type]
            post_process=tuple(
                PostProcessingStep.from_record(item) for item in record.get("post_process", ())  # type: ignore[arg-type]
            ),
            implementation_hash=str(record["implementation_hash"]),
            created_at=datetime.fromisoformat(str(record["created_at"])),
            created_by_run_id=str(record["created_by_run_id"]),
            source_commit=str(record["source_commit"]),
            status=FactorDefinitionStatus(str(record.get("status", FactorDefinitionStatus.DRAFT.value))),
            contract_version=str(record.get("contract_version", FACTOR_DEFINITION_CONTRACT_VERSION)),
            schema_name=str(record.get("schema_name", FACTOR_DEFINITION_SCHEMA_NAME)),
            schema_version=str(record.get("schema_version", FACTOR_DEFINITION_SCHEMA_VERSION)),
            version_id=_optional_record_string(record.get("version_id")),
            spec_hash=_optional_record_string(record.get("spec_hash")),
            published_at=None
            if record.get("published_at") is None
            else datetime.fromisoformat(str(record["published_at"])),
            published_by_run_id=_optional_record_string(record.get("published_by_run_id")),
            published_by_stage_id=_optional_record_string(record.get("published_by_stage_id")),
            trace_id=_optional_record_string(record.get("trace_id")),
            metadata=dict(record.get("metadata", {})),
        )

    def __post_init__(self) -> None:
        object.__setattr__(self, "definition_id", _required_string("definition_id", self.definition_id))
        object.__setattr__(self, "semantic_version", _validate_semantic_version(self.semantic_version))
        object.__setattr__(self, "name", _required_string("name", self.name))
        object.__setattr__(self, "description", _required_string("description", self.description))
        object.__setattr__(self, "category", _required_string("category", self.category))
        object.__setattr__(self, "direction", FactorDirection(self.direction))
        if type(self.formula) is not FactorFormula:
            raise FactorDefinitionError("formula must be a FactorFormula")
        inputs = tuple(self.inputs)
        if not inputs:
            raise FactorDefinitionError("factor inputs are required")
        input_ids: set[str] = set()
        for input_spec in inputs:
            if type(input_spec) is not FactorInput:
                raise FactorDefinitionError("inputs must contain FactorInput values")
            if input_spec.input_id in input_ids:
                raise FactorDefinitionError(f"duplicate input_id: {input_spec.input_id}")
            input_ids.add(input_spec.input_id)
        object.__setattr__(self, "inputs", inputs)
        windows = tuple(self.windows)
        window_names: set[str] = set()
        for window in windows:
            if type(window) is not FactorWindow:
                raise FactorDefinitionError("windows must contain FactorWindow values")
            if window.name in window_names:
                raise FactorDefinitionError(f"duplicate window name: {window.name}")
            window_names.add(window.name)
        object.__setattr__(self, "windows", windows)
        if type(self.missing_value_policy) is not MissingValuePolicy:
            raise FactorDefinitionError("missing_value_policy must be a MissingValuePolicy")
        post_process = tuple(self.post_process)
        for step in post_process:
            if type(step) is not PostProcessingStep:
                raise FactorDefinitionError("post_process must contain PostProcessingStep values")
        object.__setattr__(self, "post_process", post_process)
        object.__setattr__(self, "implementation_hash", _validate_sha256("implementation_hash", self.implementation_hash))
        _require_aware_datetime("created_at", self.created_at)
        object.__setattr__(self, "created_by_run_id", _required_string("created_by_run_id", self.created_by_run_id))
        object.__setattr__(self, "source_commit", _required_string("source_commit", self.source_commit))
        object.__setattr__(self, "status", FactorDefinitionStatus(self.status))
        object.__setattr__(self, "contract_version", _required_string("contract_version", self.contract_version))
        object.__setattr__(self, "schema_name", _required_string("schema_name", self.schema_name))
        object.__setattr__(self, "schema_version", _required_string("schema_version", self.schema_version))
        spec_hash = self.spec_hash or _derive_spec_hash(self._spec_record())
        object.__setattr__(self, "spec_hash", _validate_sha256("spec_hash", spec_hash))

        if self.status is FactorDefinitionStatus.DRAFT:
            if self.version_id is not None:
                raise FactorDefinitionError("draft definitions cannot include version_id")
            if self.published_at is not None or self.published_by_run_id is not None:
                raise FactorDefinitionError("draft definitions cannot include published metadata")
        else:
            version_id = self.version_id or _derive_version_id(self.spec_hash)
            object.__setattr__(self, "version_id", _validate_version_id(version_id))
            if self.published_at is None:
                raise FactorDefinitionError("published definitions require published_at")
            _require_aware_datetime("published_at", self.published_at)
            object.__setattr__(
                self,
                "published_by_run_id",
                _required_string("published_by_run_id", self.published_by_run_id),
            )
            object.__setattr__(self, "published_by_stage_id", _optional_string(self.published_by_stage_id))
        object.__setattr__(self, "trace_id", _optional_string(self.trace_id))
        object.__setattr__(self, "metadata", _freeze_mapping(self.metadata))

    @property
    def dataset_versions(self) -> Mapping[str, str]:
        versions: dict[str, str] = {}
        for input_spec in self.inputs:
            existing = versions.get(input_spec.dataset_name)
            if existing is not None and existing != input_spec.dataset_version:
                raise FactorDefinitionError(f"dataset {input_spec.dataset_name} has conflicting versions")
            versions[input_spec.dataset_name] = input_spec.dataset_version
        return MappingProxyType(versions)

    def publish(
        self,
        *,
        published_at: datetime,
        published_by_run_id: str,
        published_by_stage_id: str | None = None,
        trace_id: str | None = None,
    ) -> FactorDefinition:
        if self.status is not FactorDefinitionStatus.DRAFT:
            raise FactorDefinitionError("only draft definitions can be published")
        return FactorDefinition(
            definition_id=self.definition_id,
            semantic_version=self.semantic_version,
            name=self.name,
            description=self.description,
            category=self.category,
            direction=self.direction,
            formula=self.formula,
            inputs=self.inputs,
            windows=self.windows,
            missing_value_policy=self.missing_value_policy,
            post_process=self.post_process,
            implementation_hash=self.implementation_hash,
            created_at=self.created_at,
            created_by_run_id=self.created_by_run_id,
            source_commit=self.source_commit,
            status=FactorDefinitionStatus.PUBLISHED,
            contract_version=self.contract_version,
            schema_name=self.schema_name,
            schema_version=self.schema_version,
            version_id=_derive_version_id(self.spec_hash),
            spec_hash=self.spec_hash,
            published_at=published_at,
            published_by_run_id=published_by_run_id,
            published_by_stage_id=published_by_stage_id,
            trace_id=trace_id or self.trace_id,
            metadata=self.metadata,
        )

    def to_record(self) -> dict[str, Any]:
        record: dict[str, Any] = {
            "contract_version": self.contract_version,
            "schema_name": self.schema_name,
            "schema_version": self.schema_version,
            "definition_id": self.definition_id,
            "semantic_version": self.semantic_version,
            "version_id": self.version_id,
            "status": self.status.value,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "direction": self.direction.value,
            "formula": self.formula.to_record(),
            "inputs": [input_spec.to_record() for input_spec in self.inputs],
            "windows": [window.to_record() for window in self.windows],
            "missing_value_policy": self.missing_value_policy.to_record(),
            "post_process": [step.to_record() for step in self.post_process],
            "dataset_versions": dict(self.dataset_versions),
            "implementation_hash": self.implementation_hash,
            "spec_hash": self.spec_hash,
            "created_at": self.created_at.isoformat(),
            "created_by_run_id": self.created_by_run_id,
            "source_commit": self.source_commit,
            "published_at": self.published_at.isoformat() if self.published_at is not None else None,
            "published_by_run_id": self.published_by_run_id,
            "published_by_stage_id": self.published_by_stage_id,
            "trace_id": self.trace_id,
            "metadata": _thaw_value(self.metadata),
        }
        return record

    def _spec_record(self) -> dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "schema_name": self.schema_name,
            "schema_version": self.schema_version,
            "definition_id": self.definition_id,
            "semantic_version": self.semantic_version,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "direction": self.direction.value,
            "formula": self.formula.to_record(),
            "inputs": [input_spec.to_record() for input_spec in self.inputs],
            "windows": [window.to_record() for window in self.windows],
            "missing_value_policy": self.missing_value_policy.to_record(),
            "post_process": [step.to_record() for step in self.post_process],
            "implementation_hash": self.implementation_hash,
            "source_commit": self.source_commit,
        }


class LocalFactorDefinitionRepository:
    """Filesystem repository for FactorDefinition drafts, immutable versions and audit records."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)

    @property
    def draft_root(self) -> Path:
        return self.root / "drafts"

    @property
    def version_root(self) -> Path:
        return self.root / "versions"

    @property
    def semantic_index_root(self) -> Path:
        return self.root / "semantic-index"

    @property
    def retirement_root(self) -> Path:
        return self.root / "retirements"

    @property
    def audit_path(self) -> Path:
        return self.root / "audit" / "events.jsonl"

    @property
    def tmp_root(self) -> Path:
        return self.root / "tmp"

    def save_draft(self, definition: FactorDefinition) -> FactorDefinition:
        if type(definition) is not FactorDefinition:
            raise FactorDefinitionError("definition must be a FactorDefinition")
        if definition.status is not FactorDefinitionStatus.DRAFT:
            raise FactorDefinitionError("only draft definitions can be saved as drafts")
        _write_json_atomic(self.draft_path_for(definition.definition_id, definition.semantic_version), definition.to_record(), self.tmp_root)
        self._append_audit_event(
            action="draft_saved",
            definition=definition,
            created_at=definition.created_at,
            actor_run_id=definition.created_by_run_id,
            details={"spec_hash": definition.spec_hash},
        )
        return definition

    def get_draft(self, definition_id: str, semantic_version: str) -> FactorDefinition:
        return self._read_definition(self.draft_path_for(definition_id, semantic_version), "draft")

    def publish_draft(
        self,
        definition_id: str,
        semantic_version: str,
        *,
        published_at: datetime,
        published_by_run_id: str,
        published_by_stage_id: str | None = None,
        trace_id: str | None = None,
    ) -> FactorDefinition:
        draft = self.get_draft(definition_id, semantic_version)
        published = draft.publish(
            published_at=published_at,
            published_by_run_id=published_by_run_id,
            published_by_stage_id=published_by_stage_id,
            trace_id=trace_id,
        )
        index_path = self.semantic_index_path_for(published.definition_id, published.semantic_version)
        existing_version_id = self._read_semantic_index(index_path)
        if existing_version_id is not None and existing_version_id != published.version_id:
            raise FactorDefinitionError("published semantic version cannot be modified")

        self._publish_version_record(published)
        if existing_version_id is None:
            _write_json_atomic(
                index_path,
                {
                    "definition_id": published.definition_id,
                    "semantic_version": published.semantic_version,
                    "version_id": published.version_id,
                    "spec_hash": published.spec_hash,
                    "published_at": published.published_at.isoformat() if published.published_at else None,
                },
                self.tmp_root,
            )
            self._append_audit_event(
                action="published",
                definition=published,
                created_at=published_at,
                actor_run_id=published_by_run_id,
                details={"spec_hash": published.spec_hash},
            )
        return published

    def get_version(self, version_id: str) -> FactorDefinition:
        return self._read_definition(self.version_path_for(version_id), "version")

    def version_for_semantic(self, definition_id: str, semantic_version: str) -> str:
        version_id = self._read_semantic_index(self.semantic_index_path_for(definition_id, semantic_version))
        if version_id is None:
            raise FactorDefinitionError(f"published semantic version not found: {definition_id}@{semantic_version}")
        return version_id

    def retire_version(
        self,
        version_id: str,
        *,
        retired_at: datetime,
        retired_by_run_id: str,
        reason: str,
        trace_id: str | None = None,
    ) -> FactorDefinitionRetirement:
        definition = self.get_version(version_id)
        retirement = FactorDefinitionRetirement(
            version_id=definition.version_id or version_id,
            retired_at=retired_at,
            retired_by_run_id=retired_by_run_id,
            reason=reason,
            trace_id=trace_id,
        )
        path = self.retirement_path_for(version_id)
        if path.exists():
            existing = FactorDefinitionRetirement.from_record(json.loads(path.read_text(encoding="utf-8")))
            if _canonical_json_bytes(existing.to_record()) != _canonical_json_bytes(retirement.to_record()):
                raise FactorDefinitionError(f"factor definition retirement already exists: {version_id}")
            return existing
        _write_json_atomic(path, retirement.to_record(), self.tmp_root)
        self._append_audit_event(
            action="retired",
            definition=definition,
            created_at=retired_at,
            actor_run_id=retired_by_run_id,
            details={"reason": reason, "trace_id": trace_id},
        )
        return retirement

    def version_status(self, version_id: str) -> FactorDefinitionStatus:
        self.get_version(version_id)
        if self.retirement_path_for(version_id).exists():
            return FactorDefinitionStatus.RETIRED
        return FactorDefinitionStatus.PUBLISHED

    def list_audit_events(self) -> tuple[FactorDefinitionAuditEvent, ...]:
        if not self.audit_path.exists():
            return ()
        events: list[FactorDefinitionAuditEvent] = []
        for line in self.audit_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                events.append(FactorDefinitionAuditEvent.from_record(json.loads(line)))
        return tuple(events)

    def draft_path_for(self, definition_id: str, semantic_version: str) -> Path:
        return (
            self.draft_root
            / _safe_path_part(_required_string("definition_id", definition_id))
            / f"{_safe_path_part(_validate_semantic_version(semantic_version))}.json"
        )

    def version_path_for(self, version_id: str) -> Path:
        return self.version_root / f"{_validate_version_id(version_id)}.json"

    def semantic_index_path_for(self, definition_id: str, semantic_version: str) -> Path:
        return (
            self.semantic_index_root
            / _safe_path_part(_required_string("definition_id", definition_id))
            / f"{_safe_path_part(_validate_semantic_version(semantic_version))}.json"
        )

    def retirement_path_for(self, version_id: str) -> Path:
        return self.retirement_root / f"{_validate_version_id(version_id)}.json"

    def _read_definition(self, path: Path, label: str) -> FactorDefinition:
        try:
            return FactorDefinition.from_record(json.loads(path.read_text(encoding="utf-8")))
        except FileNotFoundError as exc:
            raise FactorDefinitionError(f"factor definition {label} not found: {path.stem}") from exc
        except json.JSONDecodeError as exc:
            raise FactorDefinitionError(f"factor definition {label} is not valid JSON: {path}") from exc

    def _publish_version_record(self, definition: FactorDefinition) -> None:
        if definition.version_id is None:
            raise FactorDefinitionError("published definition requires version_id")
        path = self.version_path_for(definition.version_id)
        payload = _canonical_json_bytes(definition.to_record())
        if path.exists():
            existing = self.get_version(definition.version_id)
            if _canonical_json_bytes(existing.to_record()) != payload:
                raise FactorDefinitionError(f"factor definition version already exists with different content: {definition.version_id}")
            return
        _write_json_atomic(path, definition.to_record(), self.tmp_root)

    def _read_semantic_index(self, path: Path) -> str | None:
        if not path.exists():
            return None
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise FactorDefinitionError(f"factor definition semantic index is not valid JSON: {path}") from exc
        return _validate_version_id(record.get("version_id"))

    def _append_audit_event(
        self,
        *,
        action: str,
        definition: FactorDefinition,
        created_at: datetime,
        actor_run_id: str,
        details: Mapping[str, Any],
    ) -> None:
        event = FactorDefinitionAuditEvent(
            action=action,
            definition_id=definition.definition_id,
            semantic_version=definition.semantic_version,
            version_id=definition.version_id,
            created_at=created_at,
            actor_run_id=actor_run_id,
            details=details,
        )
        self.audit_path.parent.mkdir(parents=True, exist_ok=True)
        with self.audit_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event.to_record(), ensure_ascii=False, sort_keys=True, separators=(",", ":")))
            handle.write("\n")


def _validate_dataset_version(version_id: str) -> str:
    version = _required_string("dataset_version", version_id)
    if version.lower() == "latest":
        raise FactorDefinitionError("FactorDefinition requires concrete Dataset Version ids; latest alias is not allowed")
    try:
        DatasetVersionRef.version(version)
    except DatasetCatalogError as exc:
        raise FactorDefinitionError(f"FactorDefinition requires concrete Dataset Version ids; invalid {version}") from exc
    return version


def _validate_semantic_version(value: object) -> str:
    version = _required_string("semantic_version", value)
    if not _SEMANTIC_VERSION_RE.fullmatch(version):
        raise FactorDefinitionError("semantic_version must use MAJOR.MINOR.PATCH")
    return version


def _validate_version_id(value: object | None) -> str:
    if type(value) is not str:
        raise FactorDefinitionError("version_id is required")
    normalized = value.strip().lower()
    if not _FACTOR_VERSION_ID_RE.fullmatch(normalized):
        raise FactorDefinitionError("version_id must match fdv_<32-64 lowercase sha256 hex chars>")
    return normalized


def _validate_sha256(field_name: str, value: object) -> str:
    digest = _required_string(field_name, value).lower()
    if not _SHA256_RE.fullmatch(digest):
        raise FactorDefinitionError(f"{field_name} must match sha256:<64 lowercase hex chars>")
    return digest


def _required_string(field_name: str, value: object) -> str:
    if type(value) is not str:
        raise FactorDefinitionError(f"{field_name} is required")
    stripped = value.strip()
    if not stripped:
        raise FactorDefinitionError(f"{field_name} is required")
    return stripped


def _optional_string(value: object) -> str | None:
    if value is None:
        return None
    return _required_string("optional string", value)


def _optional_record_string(value: object | None) -> str | None:
    if value is None:
        return None
    return str(value)


def _finite_float(
    field_name: str,
    value: float,
    *,
    minimum: float | None = None,
    maximum: float | None = None,
) -> float:
    if type(value) not in {int, float} or not isfinite(float(value)):
        raise FactorDefinitionError(f"{field_name} must be finite")
    normalized = float(value)
    if minimum is not None and normalized < minimum:
        raise FactorDefinitionError(f"{field_name} must be >= {minimum}")
    if maximum is not None and normalized > maximum:
        raise FactorDefinitionError(f"{field_name} must be <= {maximum}")
    return normalized


def _require_aware_datetime(field_name: str, value: datetime) -> None:
    if type(value) is not datetime or value.tzinfo is None or value.utcoffset() is None:
        raise FactorDefinitionError(f"{field_name} must be timezone-aware")


def _freeze_mapping(mapping: Mapping[str, Any]) -> Mapping[str, Any]:
    if not isinstance(mapping, Mapping):
        raise FactorDefinitionError("value must be a mapping")
    return MappingProxyType({str(key): _freeze_value(value) for key, value in mapping.items()})


def _freeze_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return _freeze_mapping(value)
    if isinstance(value, list | tuple):
        return tuple(_freeze_value(item) for item in value)
    if isinstance(value, set | frozenset):
        return tuple(sorted(_freeze_value(item) for item in value))
    if isinstance(value, bytearray):
        return bytes(value)
    return value


def _thaw_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _thaw_value(inner) for key, inner in value.items()}
    if isinstance(value, tuple):
        return [_thaw_value(item) for item in value]
    if isinstance(value, bytes):
        return value.decode("utf-8")
    return value


def _set_if_present(record: dict[str, Any], key: str, value: Any) -> None:
    if value is not None:
        record[key] = value


def _derive_spec_hash(record: Mapping[str, object]) -> str:
    return f"sha256:{hashlib.sha256(_canonical_json_bytes(record)).hexdigest()}"


def _derive_version_id(spec_hash: str | None) -> str:
    digest = _validate_sha256("spec_hash", spec_hash)
    return f"fdv_{digest.removeprefix('sha256:')[:32]}"


def _derive_audit_event_id(event: FactorDefinitionAuditEvent) -> str:
    payload = {
        "action": event.action,
        "definition_id": event.definition_id,
        "semantic_version": event.semantic_version,
        "version_id": event.version_id,
        "created_at": event.created_at.isoformat(),
        "actor_run_id": event.actor_run_id,
        "details": _thaw_value(event.details),
    }
    return f"fde_{hashlib.sha256(_canonical_json_bytes(payload)).hexdigest()[:32]}"


def _canonical_json_bytes(record: Mapping[str, object]) -> bytes:
    return json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _write_json_atomic(path: Path, record: Mapping[str, object], tmp_root: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_root.mkdir(parents=True, exist_ok=True)
    tmp_path = tmp_root / f"{path.stem}.{uuid.uuid4().hex}.tmp"
    try:
        tmp_path.write_text(json.dumps(record, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        tmp_path.replace(path)
    finally:
        tmp_path.unlink(missing_ok=True)


def _safe_path_part(value: str) -> str:
    return quote(value, safe="")


__all__ = [
    "FACTOR_DEFINITION_CONTRACT_VERSION",
    "FACTOR_DEFINITION_SCHEMA_NAME",
    "FACTOR_DEFINITION_SCHEMA_VERSION",
    "FactorDefinition",
    "FactorDefinitionAuditEvent",
    "FactorDefinitionError",
    "FactorDefinitionRetirement",
    "FactorDefinitionStatus",
    "FactorDirection",
    "FactorFormula",
    "FactorInput",
    "FactorInputKind",
    "FactorWindow",
    "LocalFactorDefinitionRepository",
    "MissingValuePolicy",
    "MissingValueStrategy",
    "PostProcessingStep",
]
