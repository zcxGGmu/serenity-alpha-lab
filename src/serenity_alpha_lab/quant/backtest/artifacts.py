from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from types import MappingProxyType
from typing import Any

from serenity_alpha_lab.datasets.catalog import DatasetCatalogError, DatasetVersionRef
from serenity_alpha_lab.domain.artifacts import ArtifactManifest, ArtifactRetentionTier, ArtifactStore


BACKTEST_ARTIFACT_CONTRACT_VERSION = "quant.backtest_artifact@1.0.0"
BACKTEST_ARTIFACT_BUNDLE_SCHEMA_NAME = "quant.backtest_artifact_bundle"
BACKTEST_ARTIFACT_BUNDLE_SCHEMA_VERSION = "1.0.0"
BACKTEST_ARTIFACT_BUNDLE_CONTENT_TYPE = "application/vnd.serenity.quant.backtest-artifact-bundle+json"
BACKTEST_ARTIFACT_ENGINE_VERSION = "portfolio_backtest_artifacts@1.0.0"
BACKTEST_ARTIFACT_ENGINE_SCOPE = "formal_portfolio_backtest"

_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


class BacktestArtifactError(ValueError):
    """Raised when a formal BacktestArtifact output contract is invalid."""


class BacktestArtifactKind(StrEnum):
    ORDERS = "orders"
    EXECUTIONS = "executions"
    POSITIONS = "positions"
    CASH = "cash"
    EQUITY_CURVE = "equity_curve"
    METRICS = "metrics"
    AUDIT = "audit"


class BacktestArtifactState(StrEnum):
    PREVIEW = "preview"
    FORMAL = "formal"
    PARTIAL = "partial"
    INVALID = "invalid"


@dataclass(frozen=True, slots=True)
class BacktestOutputArtifact:
    kind: BacktestArtifactKind | str
    schema_name: str
    schema_version: str
    artifact_manifest: ArtifactManifest
    content_hash: str
    row_count: int
    partition_keys: Sequence[str] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "kind", _artifact_kind(self.kind))
        object.__setattr__(self, "schema_name", _required_string("schema_name", self.schema_name))
        object.__setattr__(self, "schema_version", _required_string("schema_version", self.schema_version))
        if type(self.artifact_manifest) is not ArtifactManifest:
            raise BacktestArtifactError("artifact_manifest must be an ArtifactManifest")
        content_hash = _validate_sha256("content_hash", self.content_hash)
        if content_hash != f"sha256:{self.artifact_manifest.sha256}":
            raise BacktestArtifactError("content_hash must match artifact manifest")
        if self.artifact_manifest.uri.digest != self.artifact_manifest.sha256:
            raise BacktestArtifactError("artifact manifest URI must match sha256")
        if type(self.row_count) is not int or self.row_count < 0:
            raise BacktestArtifactError("row_count cannot be negative")
        partition_keys = _string_tuple("partition_key", self.partition_keys)
        if len(set(partition_keys)) != len(partition_keys):
            raise BacktestArtifactError("partition_keys cannot contain duplicates")
        object.__setattr__(self, "content_hash", content_hash)
        object.__setattr__(self, "partition_keys", partition_keys)

    @property
    def artifact_id(self) -> str:
        return self.artifact_manifest.artifact_id

    def to_record(self) -> dict[str, object]:
        return {
            "kind": self.kind.value,
            "schema_name": self.schema_name,
            "schema_version": self.schema_version,
            "artifact_id": self.artifact_manifest.artifact_id,
            "artifact_uri": str(self.artifact_manifest.uri),
            "content_hash": self.content_hash,
            "sha256": self.artifact_manifest.sha256,
            "size_bytes": self.artifact_manifest.size_bytes,
            "content_type": self.artifact_manifest.content_type,
            "row_count": self.row_count,
            "partition_keys": list(self.partition_keys),
        }


@dataclass(frozen=True, slots=True)
class BacktestArtifactBundle:
    run_id: str
    spec_id: str
    spec_hash: str
    dataset_versions: Mapping[str, str]
    state: BacktestArtifactState | str
    outputs: Sequence[BacktestOutputArtifact] | Mapping[BacktestArtifactKind | str, BacktestOutputArtifact]
    created_at: datetime
    stage_id: str | None = None
    engine_version: str = BACKTEST_ARTIFACT_ENGINE_VERSION
    engine_scope: str = BACKTEST_ARTIFACT_ENGINE_SCOPE
    trace_id: str | None = None
    warnings: Sequence[str] = ()
    errors: Sequence[str] = ()
    bundle_id: str | None = None
    contract_version: str = BACKTEST_ARTIFACT_CONTRACT_VERSION
    schema_name: str = BACKTEST_ARTIFACT_BUNDLE_SCHEMA_NAME
    schema_version: str = BACKTEST_ARTIFACT_BUNDLE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "run_id", _required_string("run_id", self.run_id))
        object.__setattr__(self, "stage_id", _optional_string(self.stage_id))
        object.__setattr__(self, "spec_id", _required_string("spec_id", self.spec_id))
        object.__setattr__(self, "spec_hash", _validate_sha256("spec_hash", self.spec_hash))
        object.__setattr__(self, "dataset_versions", _normalize_dataset_versions(self.dataset_versions))
        object.__setattr__(self, "state", _artifact_state(self.state))
        object.__setattr__(self, "outputs", _normalize_outputs(self.outputs))
        _require_aware_datetime("created_at", self.created_at)
        object.__setattr__(self, "engine_version", _required_string("engine_version", self.engine_version))
        engine_scope = _required_string("engine_scope", self.engine_scope)
        if engine_scope == "legacy_signal_evaluation":
            raise BacktestArtifactError("legacy Signal Evaluation cannot be used as a formal BacktestArtifact scope")
        object.__setattr__(self, "engine_scope", engine_scope)
        object.__setattr__(self, "trace_id", _optional_string(self.trace_id))
        object.__setattr__(self, "warnings", _string_tuple("warning", self.warnings))
        object.__setattr__(self, "errors", _string_tuple("error", self.errors))
        object.__setattr__(self, "contract_version", _required_string("contract_version", self.contract_version))
        object.__setattr__(self, "schema_name", _required_string("schema_name", self.schema_name))
        object.__setattr__(self, "schema_version", _required_string("schema_version", self.schema_version))
        self._validate_state_payload()
        bundle_id = self.bundle_id or _stable_id("bta", self._identity_record(include_bundle_id=False))
        object.__setattr__(self, "bundle_id", _required_string("bundle_id", bundle_id))

    def to_json_bytes(self) -> bytes:
        return _canonical_json(self.to_record()).encode("utf-8")

    def to_record(self) -> dict[str, Any]:
        return self._identity_record(include_bundle_id=True)

    def publish(
        self,
        artifact_store: ArtifactStore,
        *,
        produced_by_run_id: str | None = None,
        produced_by_stage_id: str | None = None,
        retention_tier: ArtifactRetentionTier = ArtifactRetentionTier.STANDARD,
    ) -> ArtifactManifest:
        run_id = _required_string("produced_by_run_id", produced_by_run_id or self.run_id)
        stage_id = produced_by_stage_id if produced_by_stage_id is not None else self.stage_id
        return artifact_store.put_bytes(
            self.to_json_bytes(),
            schema_name=BACKTEST_ARTIFACT_BUNDLE_SCHEMA_NAME,
            schema_version=BACKTEST_ARTIFACT_BUNDLE_SCHEMA_VERSION,
            content_type=BACKTEST_ARTIFACT_BUNDLE_CONTENT_TYPE,
            produced_by_run_id=run_id,
            produced_by_stage_id=stage_id,
            retention_tier=retention_tier,
            created_at=self.created_at,
        )

    def _validate_state_payload(self) -> None:
        if self.state is BacktestArtifactState.PARTIAL and not self.warnings and not self.errors:
            raise BacktestArtifactError("partial bundles require warnings or errors")
        if self.state is BacktestArtifactState.INVALID and not self.errors:
            raise BacktestArtifactError("invalid bundles require errors")
        if self.state is BacktestArtifactState.FORMAL and self.errors:
            raise BacktestArtifactError("formal bundles cannot include errors")

    def _identity_record(self, *, include_bundle_id: bool) -> dict[str, Any]:
        record: dict[str, Any] = {
            "schema_name": self.schema_name,
            "schema_version": self.schema_version,
            "contract_version": self.contract_version,
            "engine": {
                "version": self.engine_version,
                "scope": self.engine_scope,
            },
            "state": self.state.value,
            "spec_id": self.spec_id,
            "spec_hash": self.spec_hash,
            "dataset_versions": dict(self.dataset_versions),
            "created_at": self.created_at.isoformat(),
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "trace": {
                "trace_id": self.trace_id,
                "run_id": self.run_id,
                "stage_id": self.stage_id,
            },
            "outputs": {kind.value: output.to_record() for kind, output in self.outputs.items()},
        }
        if include_bundle_id:
            record["bundle_id"] = self.bundle_id
        return record


def publish_backtest_artifact_bundle(
    bundle: BacktestArtifactBundle,
    artifact_store: ArtifactStore,
    *,
    produced_by_run_id: str | None = None,
    produced_by_stage_id: str | None = None,
    retention_tier: ArtifactRetentionTier = ArtifactRetentionTier.STANDARD,
) -> ArtifactManifest:
    if type(bundle) is not BacktestArtifactBundle:
        raise BacktestArtifactError("bundle must be a BacktestArtifactBundle")
    return bundle.publish(
        artifact_store,
        produced_by_run_id=produced_by_run_id,
        produced_by_stage_id=produced_by_stage_id,
        retention_tier=retention_tier,
    )


def _normalize_outputs(
    outputs: Sequence[BacktestOutputArtifact] | Mapping[BacktestArtifactKind | str, BacktestOutputArtifact],
) -> Mapping[BacktestArtifactKind, BacktestOutputArtifact]:
    if isinstance(outputs, Mapping):
        values = tuple(outputs.values())
    else:
        if isinstance(outputs, (str, bytes)):
            raise BacktestArtifactError("outputs must contain BacktestOutputArtifact values")
        values = tuple(outputs)
    if not values:
        raise BacktestArtifactError("outputs are required")

    normalized: dict[BacktestArtifactKind, BacktestOutputArtifact] = {}
    for output in values:
        if type(output) is not BacktestOutputArtifact:
            raise BacktestArtifactError("outputs must contain BacktestOutputArtifact values")
        if output.kind in normalized:
            raise BacktestArtifactError("outputs cannot contain duplicate kinds")
        normalized[output.kind] = output

    required = set(BacktestArtifactKind)
    missing = sorted(kind.value for kind in required.difference(normalized))
    if missing:
        raise BacktestArtifactError(f"required output kinds missing: {', '.join(missing)}")
    return MappingProxyType({kind: normalized[kind] for kind in BacktestArtifactKind})


def _normalize_dataset_versions(dataset_versions: Mapping[str, str]) -> Mapping[str, str]:
    if not isinstance(dataset_versions, Mapping):
        raise BacktestArtifactError("dataset_versions must map names to concrete Dataset Version ids")
    if not dataset_versions:
        raise BacktestArtifactError("dataset_versions are required")
    normalized = {
        _required_string("dataset name", name): _validate_dataset_version(version)
        for name, version in dataset_versions.items()
    }
    return MappingProxyType(dict(sorted(normalized.items())))


def _validate_dataset_version(value: object) -> str:
    version = _required_string("dataset_version", value)
    if version.lower() == "latest":
        raise BacktestArtifactError("BacktestArtifact requires concrete Dataset Version ids; latest is not allowed")
    try:
        DatasetVersionRef.version(version)
    except (DatasetCatalogError, ValueError) as exc:
        raise BacktestArtifactError("BacktestArtifact requires concrete Dataset Version ids") from exc
    return version


def _artifact_kind(value: BacktestArtifactKind | str) -> BacktestArtifactKind:
    try:
        return BacktestArtifactKind(value)
    except ValueError as exc:
        raise BacktestArtifactError("kind must be a valid BacktestArtifactKind") from exc


def _artifact_state(value: BacktestArtifactState | str) -> BacktestArtifactState:
    try:
        return BacktestArtifactState(value)
    except ValueError as exc:
        raise BacktestArtifactError("state must be one of preview, formal, partial or invalid") from exc


def _validate_sha256(field_name: str, value: object) -> str:
    digest = _required_string(field_name, value)
    if not _SHA256_RE.fullmatch(digest):
        raise BacktestArtifactError(f"{field_name} must match sha256:<64 lowercase hex chars>")
    return digest


def _string_tuple(field_name: str, values: Sequence[str]) -> tuple[str, ...]:
    if isinstance(values, str):
        raise BacktestArtifactError(f"{field_name}s must be a sequence")
    return tuple(_required_string(field_name, value) for value in values)


def _required_string(field_name: str, value: object) -> str:
    if type(value) is not str or not value.strip():
        raise BacktestArtifactError(f"{field_name} is required")
    return value


def _optional_string(value: object) -> str | None:
    if value is None:
        return None
    return _required_string("optional string", value)


def _require_aware_datetime(field_name: str, value: object) -> None:
    if type(value) is not datetime or value.tzinfo is None or value.utcoffset() is None:
        raise BacktestArtifactError(f"{field_name} must be a timezone-aware datetime")


def _stable_id(prefix: str, payload: Mapping[str, Any]) -> str:
    return f"{prefix}_{hashlib.sha256(_canonical_json(payload).encode('utf-8')).hexdigest()[:32]}"


def _canonical_json(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
