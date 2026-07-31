from __future__ import annotations

import hashlib
import json
import os
import re
import uuid
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from types import MappingProxyType
from urllib.parse import quote

from serenity_alpha_lab.datasets.schema_registry import ArrowSchemaRegistry, default_dataset_schema_registry
from serenity_alpha_lab.domain.artifacts import ArtifactManifest, ArtifactUri


_DATASET_VERSION_ID_RE = re.compile(r"^dsv_[0-9a-f]{32,64}$")
_SHA256_WITH_ALGORITHM_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


class DatasetCatalogError(ValueError):
    """Raised when Dataset Catalog metadata violates the immutable version contract."""


class DatasetReferencePurpose(StrEnum):
    DISCOVERY = "discovery"
    RESEARCH_DISPLAY = "research_display"
    FORMAL_EXPERIMENT = "formal_experiment"


class DatasetVersionRefKind(StrEnum):
    VERSION = "version"
    LATEST = "latest"


@dataclass(frozen=True, slots=True)
class DatasetFileManifest:
    artifact_id: str
    uri: str
    sha256: str
    size_bytes: int
    schema_name: str
    schema_version: str
    content_type: str
    row_count: int
    partition_values: Mapping[str, str] = field(default_factory=dict)

    @classmethod
    def from_artifact(
        cls,
        artifact: ArtifactManifest,
        *,
        row_count: int,
        partition_values: Mapping[str, str] | None = None,
    ) -> DatasetFileManifest:
        if type(artifact) is not ArtifactManifest:
            raise DatasetCatalogError("artifact must be an ArtifactManifest")
        return cls(
            artifact_id=artifact.artifact_id,
            uri=str(artifact.uri),
            sha256=artifact.sha256,
            size_bytes=artifact.size_bytes,
            schema_name=artifact.schema_name,
            schema_version=artifact.schema_version,
            content_type=artifact.content_type,
            row_count=row_count,
            partition_values={} if partition_values is None else partition_values,
        )

    @classmethod
    def from_record(cls, record: Mapping[str, object]) -> DatasetFileManifest:
        return cls(
            artifact_id=str(record["artifact_id"]),
            uri=str(record["uri"]),
            sha256=str(record["sha256"]),
            size_bytes=int(record["size_bytes"]),
            schema_name=str(record["schema_name"]),
            schema_version=str(record["schema_version"]),
            content_type=str(record["content_type"]),
            row_count=int(record["row_count"]),
            partition_values={str(key): str(value) for key, value in dict(record.get("partition_values", {})).items()},
        )

    def __post_init__(self) -> None:
        object.__setattr__(self, "artifact_id", _required_string("artifact_id", self.artifact_id))
        object.__setattr__(self, "uri", _required_string("uri", self.uri))
        parsed_uri = ArtifactUri.parse(self.uri)
        object.__setattr__(self, "sha256", ArtifactUri.for_sha256(self.sha256).digest)
        if parsed_uri.digest != self.sha256:
            raise DatasetCatalogError("file uri digest must match sha256")
        if type(self.size_bytes) is not int or self.size_bytes < 0:
            raise DatasetCatalogError("size_bytes cannot be negative")
        object.__setattr__(self, "schema_name", _required_string("schema_name", self.schema_name))
        object.__setattr__(self, "schema_version", _required_string("schema_version", self.schema_version))
        object.__setattr__(self, "content_type", _required_string("content_type", self.content_type))
        if type(self.row_count) is not int or self.row_count < 0:
            raise DatasetCatalogError("row_count cannot be negative")
        partition_values: dict[str, str] = {}
        for key, value in self.partition_values.items():
            partition_values[_required_string("partition key", key)] = _required_string("partition value", value)
        object.__setattr__(self, "partition_values", MappingProxyType(partition_values))

    def to_record(self) -> dict[str, object]:
        return {
            "artifact_id": self.artifact_id,
            "uri": self.uri,
            "sha256": self.sha256,
            "size_bytes": self.size_bytes,
            "schema_name": self.schema_name,
            "schema_version": self.schema_version,
            "content_type": self.content_type,
            "row_count": self.row_count,
            "partition_values": dict(self.partition_values),
        }


@dataclass(frozen=True, slots=True)
class DatasetVersionManifest:
    dataset_name: str
    version_id: str
    schema_name: str
    schema_version: str
    schema_hash: str
    content_type: str
    created_at: datetime
    created_by_run_id: str
    files: Sequence[DatasetFileManifest]
    created_by_stage_id: str | None = None
    trace_id: str | None = None
    previous_version_id: str | None = None
    input_version_ids: Sequence[str] = ()
    metadata: Mapping[str, str] = field(default_factory=dict)

    @classmethod
    def from_record(cls, record: Mapping[str, object]) -> DatasetVersionManifest:
        return cls(
            dataset_name=str(record["dataset_name"]),
            version_id=str(record["version_id"]),
            schema_name=str(record["schema_name"]),
            schema_version=str(record["schema_version"]),
            schema_hash=str(record["schema_hash"]),
            content_type=str(record["content_type"]),
            created_at=datetime.fromisoformat(str(record["created_at"])),
            created_by_run_id=str(record["created_by_run_id"]),
            created_by_stage_id=_coerce_optional_record_string(record.get("created_by_stage_id")),
            trace_id=_coerce_optional_record_string(record.get("trace_id")),
            previous_version_id=_coerce_optional_record_string(record.get("previous_version_id")),
            input_version_ids=tuple(str(value) for value in record.get("input_version_ids", ())),
            files=tuple(DatasetFileManifest.from_record(item) for item in record["files"]),  # type: ignore[index]
            metadata={str(key): str(value) for key, value in dict(record.get("metadata", {})).items()},
        )

    def __post_init__(self) -> None:
        object.__setattr__(self, "dataset_name", _required_string("dataset_name", self.dataset_name))
        object.__setattr__(self, "version_id", _validate_version_id(self.version_id))
        object.__setattr__(self, "schema_name", _required_string("schema_name", self.schema_name))
        object.__setattr__(self, "schema_version", _required_string("schema_version", self.schema_version))
        object.__setattr__(self, "schema_hash", _validate_schema_hash(self.schema_hash))
        object.__setattr__(self, "content_type", _required_string("content_type", self.content_type))
        _require_aware_datetime("created_at", self.created_at)
        object.__setattr__(self, "created_by_run_id", _required_string("created_by_run_id", self.created_by_run_id))
        object.__setattr__(self, "created_by_stage_id", _optional_string(self.created_by_stage_id))
        object.__setattr__(self, "trace_id", _optional_string(self.trace_id))
        object.__setattr__(
            self,
            "previous_version_id",
            _validate_optional_version_id(self.previous_version_id, field_name="previous_version_id"),
        )

        files = tuple(self.files)
        if not files:
            raise DatasetCatalogError("dataset version files are required")
        artifact_ids: set[str] = set()
        file_hashes: set[str] = set()
        for file_manifest in files:
            if type(file_manifest) is not DatasetFileManifest:
                raise DatasetCatalogError("files must contain DatasetFileManifest values")
            if file_manifest.schema_name != self.schema_name:
                raise DatasetCatalogError("file schema_name must match dataset schema_name")
            if file_manifest.schema_version != self.schema_version:
                raise DatasetCatalogError("file schema_version must match dataset schema_version")
            if file_manifest.content_type != self.content_type:
                raise DatasetCatalogError("file content_type must match dataset content_type")
            if file_manifest.artifact_id in artifact_ids:
                raise DatasetCatalogError(f"duplicate dataset file artifact_id: {file_manifest.artifact_id}")
            if file_manifest.sha256 in file_hashes:
                raise DatasetCatalogError(f"duplicate dataset file sha256: {file_manifest.sha256}")
            artifact_ids.add(file_manifest.artifact_id)
            file_hashes.add(file_manifest.sha256)
        object.__setattr__(self, "files", tuple(sorted(files, key=lambda item: item.artifact_id)))

        input_version_ids = tuple(
            _validate_version_id(version_id, field_name="input_version_id") for version_id in self.input_version_ids
        )
        if len(set(input_version_ids)) != len(input_version_ids):
            raise DatasetCatalogError("input_version_ids cannot contain duplicates")
        if self.previous_version_id and self.previous_version_id == self.version_id:
            raise DatasetCatalogError("previous_version_id cannot equal version_id")
        if self.version_id in input_version_ids:
            raise DatasetCatalogError("input_version_ids cannot include version_id")
        object.__setattr__(self, "input_version_ids", tuple(sorted(input_version_ids)))

        metadata: dict[str, str] = {}
        for key, value in self.metadata.items():
            metadata[_required_string("metadata key", key)] = _required_string("metadata value", value)
        object.__setattr__(self, "metadata", MappingProxyType(metadata))

    @property
    def row_count(self) -> int:
        return sum(file_manifest.row_count for file_manifest in self.files)

    @property
    def file_hashes(self) -> tuple[str, ...]:
        return tuple(file_manifest.sha256 for file_manifest in self.files)

    def to_record(self) -> dict[str, object]:
        return {
            "dataset_name": self.dataset_name,
            "version_id": self.version_id,
            "schema_name": self.schema_name,
            "schema_version": self.schema_version,
            "schema_hash": self.schema_hash,
            "content_type": self.content_type,
            "created_at": self.created_at.isoformat(),
            "created_by_run_id": self.created_by_run_id,
            "created_by_stage_id": self.created_by_stage_id,
            "trace_id": self.trace_id,
            "previous_version_id": self.previous_version_id,
            "input_version_ids": list(self.input_version_ids),
            "row_count": self.row_count,
            "file_hashes": list(self.file_hashes),
            "files": [file_manifest.to_record() for file_manifest in self.files],
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True, slots=True)
class DatasetVersionRef:
    kind: DatasetVersionRefKind
    version_id: str | None = None
    dataset_name: str | None = None
    alias_scope: str | None = None

    @classmethod
    def version(cls, version_id: str) -> DatasetVersionRef:
        return cls(kind=DatasetVersionRefKind.VERSION, version_id=version_id)

    @classmethod
    def latest(cls, dataset_name: str, *, alias_scope: str = "global") -> DatasetVersionRef:
        return cls(kind=DatasetVersionRefKind.LATEST, dataset_name=dataset_name, alias_scope=alias_scope)

    def __post_init__(self) -> None:
        object.__setattr__(self, "kind", DatasetVersionRefKind(self.kind))
        if self.kind is DatasetVersionRefKind.VERSION:
            object.__setattr__(self, "version_id", _validate_version_id(self.version_id))
            object.__setattr__(self, "dataset_name", _optional_string(self.dataset_name))
            object.__setattr__(self, "alias_scope", _optional_string(self.alias_scope))
            return
        object.__setattr__(self, "version_id", _optional_string(self.version_id))
        if self.version_id is not None:
            raise DatasetCatalogError("latest reference cannot include version_id")
        object.__setattr__(self, "dataset_name", _required_string("dataset_name", self.dataset_name))
        object.__setattr__(self, "alias_scope", _required_string("alias_scope", self.alias_scope))


class LocalDatasetCatalog:
    """Filesystem-backed Dataset Catalog with immutable version records and mutable aliases."""

    def __init__(self, root: str | Path, *, schema_registry: ArrowSchemaRegistry | None = None) -> None:
        self.root = Path(root)
        self.schema_registry = schema_registry if schema_registry is not None else default_dataset_schema_registry()

    @property
    def version_root(self) -> Path:
        return self.root / "versions"

    @property
    def alias_root(self) -> Path:
        return self.root / "aliases"

    @property
    def quarantine_root(self) -> Path:
        return self.root / "quarantine"

    @property
    def tmp_root(self) -> Path:
        return self.root / "tmp"

    def publish_version(
        self,
        *,
        dataset_name: str,
        schema_name: str,
        schema_version: str,
        files: Iterable[DatasetFileManifest],
        created_at: datetime,
        created_by_run_id: str,
        created_by_stage_id: str | None = None,
        trace_id: str | None = None,
        previous_version_id: str | None = None,
        input_version_ids: Iterable[str] = (),
        alias_scope: str = "global",
        update_latest: bool = True,
        version_id: str | None = None,
        metadata: Mapping[str, str] | None = None,
    ) -> DatasetVersionManifest:
        schema_declaration = self.schema_registry.get(schema_name, schema_version)
        content_type = _required_string("schema content_type", schema_declaration.content_type)
        normalized_dataset_name = _required_string("dataset_name", dataset_name)
        if normalized_dataset_name != schema_declaration.schema_name:
            raise DatasetCatalogError("dataset_name must match schema declaration name")

        if previous_version_id is not None:
            self.get_version(previous_version_id)
        input_ids = tuple(input_version_ids)
        for input_version_id in input_ids:
            self.get_version(input_version_id)

        file_tuple = tuple(files)
        candidate_record = {
            "dataset_name": normalized_dataset_name,
            "schema_name": schema_declaration.schema_name,
            "schema_version": schema_declaration.schema_version,
            "schema_hash": schema_declaration.schema_hash,
            "content_type": content_type,
            "created_at": created_at.isoformat(),
            "created_by_run_id": created_by_run_id,
            "created_by_stage_id": created_by_stage_id,
            "trace_id": trace_id,
            "previous_version_id": previous_version_id,
            "input_version_ids": sorted(input_ids),
            "files": [file_manifest.to_record() for file_manifest in sorted(file_tuple, key=lambda item: item.artifact_id)],
            "metadata": dict(metadata or {}),
        }
        resolved_version_id = _validate_optional_version_id(version_id) or _derive_version_id(candidate_record)
        manifest_kwargs = dict(candidate_record)
        manifest_kwargs["created_at"] = created_at
        manifest_kwargs["files"] = tuple(sorted(file_tuple, key=lambda item: item.artifact_id))
        manifest = DatasetVersionManifest(**manifest_kwargs, version_id=resolved_version_id)
        self._publish_manifest_record(manifest)
        if update_latest:
            self._publish_latest_alias(manifest, alias_scope=alias_scope)
        return manifest

    def get_version(self, version_id: str) -> DatasetVersionManifest:
        normalized_version_id = _validate_version_id(version_id)
        path = self.version_path_for(normalized_version_id)
        try:
            return DatasetVersionManifest.from_record(json.loads(path.read_text(encoding="utf-8")))
        except FileNotFoundError as exc:
            raise DatasetCatalogError(f"Dataset version not found: {normalized_version_id}") from exc
        except json.JSONDecodeError as exc:
            raise DatasetCatalogError(f"Dataset version manifest is not valid JSON: {normalized_version_id}") from exc

    def list_versions(self, dataset_name: str | None = None) -> tuple[DatasetVersionManifest, ...]:
        if not self.version_root.exists():
            return ()
        dataset_filter = _optional_string(dataset_name)
        versions = [
            self.get_version(path.stem)
            for path in sorted(self.version_root.glob("*.json"))
            if path.is_file()
        ]
        if dataset_filter is not None:
            versions = [version for version in versions if version.dataset_name == dataset_filter]
        return tuple(sorted(versions, key=lambda item: (item.created_at, item.version_id)))

    def resolve_latest(self, dataset_name: str, alias_scope: str = "global") -> DatasetVersionManifest:
        alias_path = self.alias_path_for(dataset_name, alias_scope)
        try:
            record = json.loads(alias_path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise DatasetCatalogError(f"Latest alias not found: {dataset_name} {alias_scope}") from exc
        except json.JSONDecodeError as exc:
            raise DatasetCatalogError(f"Latest alias is not valid JSON: {dataset_name} {alias_scope}") from exc
        if record.get("dataset_name") != dataset_name:
            raise DatasetCatalogError("latest alias dataset_name mismatch")
        if record.get("alias_scope") != alias_scope:
            raise DatasetCatalogError("latest alias scope mismatch")
        return self.get_version(str(record["version_id"]))

    def resolve_for_run(
        self,
        reference: DatasetVersionRef,
        *,
        purpose: DatasetReferencePurpose,
    ) -> DatasetVersionManifest:
        if type(reference) is not DatasetVersionRef:
            raise DatasetCatalogError("reference must be a DatasetVersionRef")
        resolved_purpose = DatasetReferencePurpose(purpose)
        if reference.kind is DatasetVersionRefKind.LATEST:
            if resolved_purpose is DatasetReferencePurpose.FORMAL_EXPERIMENT:
                raise DatasetCatalogError("latest alias cannot be used as a formal experiment input")
            return self.resolve_latest(reference.dataset_name or "", reference.alias_scope or "global")
        return self.get_version(reference.version_id or "")

    def promote_to_latest(self, version_id: str, alias_scope: str = "global") -> DatasetVersionManifest:
        manifest = self.get_version(version_id)
        self._publish_latest_alias(manifest, alias_scope=alias_scope)
        return manifest

    def record_quarantine(self, record: Mapping[str, object]) -> Mapping[str, object]:
        normalized = self._normalize_quarantine_record(record)
        path = self.quarantine_path_for(
            str(normalized["dataset_name"]),
            str(normalized["alias_scope"]),
            str(normalized["version_id"]),
        )
        payload = _canonical_json_bytes(normalized)
        if path.exists():
            existing = json.loads(path.read_text(encoding="utf-8"))
            if _canonical_json_bytes(existing) != payload:
                raise DatasetCatalogError(
                    f"Dataset quarantine record {normalized['version_id']} already exists with different content"
                )
            return MappingProxyType(existing)
        _write_json_atomic(path, normalized, tmp_root=self.tmp_root)
        return MappingProxyType(normalized)

    def list_quarantine_records(
        self,
        dataset_name: str | None = None,
        alias_scope: str | None = None,
    ) -> tuple[Mapping[str, object], ...]:
        if not self.quarantine_root.exists():
            return ()
        dataset_filter = _optional_string(dataset_name)
        scope_filter = _optional_string(alias_scope)
        records: list[Mapping[str, object]] = []
        for path in sorted(self.quarantine_root.glob("*/*/*.json")):
            if not path.is_file():
                continue
            record = json.loads(path.read_text(encoding="utf-8"))
            if dataset_filter is not None and record.get("dataset_name") != dataset_filter:
                continue
            if scope_filter is not None and record.get("alias_scope") != scope_filter:
                continue
            records.append(MappingProxyType(record))
        return tuple(
            sorted(
                records,
                key=lambda item: (
                    str(item.get("created_at", "")),
                    str(item.get("dataset_name", "")),
                    str(item.get("version_id", "")),
                ),
            )
        )

    def version_path_for(self, version_id: str) -> Path:
        return self.version_root / f"{_validate_version_id(version_id)}.json"

    def alias_path_for(self, dataset_name: str, alias_scope: str = "global") -> Path:
        return (
            self.alias_root
            / _safe_path_part(_required_string("dataset_name", dataset_name))
            / _safe_path_part(_required_string("alias_scope", alias_scope))
            / "latest.json"
        )

    def quarantine_path_for(self, dataset_name: str, alias_scope: str, version_id: str) -> Path:
        return (
            self.quarantine_root
            / _safe_path_part(_required_string("dataset_name", dataset_name))
            / _safe_path_part(_required_string("alias_scope", alias_scope))
            / f"{_validate_version_id(version_id)}.json"
        )

    def _normalize_quarantine_record(self, record: Mapping[str, object]) -> dict[str, object]:
        dataset_name = _required_string("dataset_name", record.get("dataset_name"))
        alias_scope = _required_string("alias_scope", record.get("alias_scope"))
        version_id = _validate_version_id(record.get("version_id"))
        self.get_version(version_id)
        normalized = dict(record)
        normalized["dataset_name"] = dataset_name
        normalized["alias_scope"] = alias_scope
        normalized["version_id"] = version_id
        normalized["quality_status"] = _required_string("quality_status", normalized.get("quality_status"))
        normalized["publication_status"] = _required_string(
            "publication_status",
            normalized.get("publication_status"),
        )
        normalized["created_at"] = _required_string("created_at", normalized.get("created_at"))
        return normalized

    def _publish_manifest_record(self, manifest: DatasetVersionManifest) -> None:
        path = self.version_path_for(manifest.version_id)
        record = manifest.to_record()
        payload = _canonical_json_bytes(record)
        if path.exists():
            existing = self.get_version(manifest.version_id)
            existing_payload = _canonical_json_bytes(existing.to_record())
            if existing_payload != payload:
                raise DatasetCatalogError(f"Dataset version {manifest.version_id} already exists with different manifest")
            return
        _write_json_atomic(path, record, tmp_root=self.tmp_root)

    def _publish_latest_alias(self, manifest: DatasetVersionManifest, *, alias_scope: str) -> None:
        normalized_scope = _required_string("alias_scope", alias_scope)
        record = {
            "dataset_name": manifest.dataset_name,
            "alias_scope": normalized_scope,
            "alias": "latest",
            "version_id": manifest.version_id,
            "updated_at": manifest.created_at.isoformat(),
            "updated_by_run_id": manifest.created_by_run_id,
            "updated_by_stage_id": manifest.created_by_stage_id,
        }
        _write_json_atomic(self.alias_path_for(manifest.dataset_name, normalized_scope), record, tmp_root=self.tmp_root)


def _derive_version_id(record_without_version: Mapping[str, object]) -> str:
    payload = _canonical_json_bytes(record_without_version)
    return f"dsv_{hashlib.sha256(payload).hexdigest()[:32]}"


def _canonical_json_bytes(record: Mapping[str, object]) -> bytes:
    return json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _write_json_atomic(path: Path, record: Mapping[str, object], *, tmp_root: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_root.mkdir(parents=True, exist_ok=True)
    token = uuid.uuid4().hex
    tmp_path = tmp_root / f"{path.stem}.{token}.tmp"
    try:
        payload = json.dumps(record, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8")
        with tmp_path.open("wb") as handle:
            handle.write(payload)
            handle.write(b"\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, path)
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise
    finally:
        tmp_path.unlink(missing_ok=True)


def _safe_path_part(value: str) -> str:
    return quote(value, safe="")


def _validate_version_id(value: object | None, *, field_name: str = "version_id") -> str:
    if type(value) is not str:
        raise DatasetCatalogError(f"{field_name} is required")
    normalized = value.strip().lower()
    if not _DATASET_VERSION_ID_RE.fullmatch(normalized):
        raise DatasetCatalogError(f"{field_name} must match dsv_<32-64 lowercase sha256 hex chars>")
    return normalized


def _validate_optional_version_id(value: object | None, *, field_name: str = "version_id") -> str | None:
    if value is None:
        return None
    return _validate_version_id(value, field_name=field_name)


def _validate_schema_hash(value: object | None) -> str:
    if type(value) is not str:
        raise DatasetCatalogError("schema_hash is required")
    normalized = value.strip().lower()
    if not _SHA256_WITH_ALGORITHM_RE.fullmatch(normalized):
        raise DatasetCatalogError("schema_hash must match sha256:<64 lowercase hex chars>")
    return normalized


def _required_string(field_name: str, value: object | None) -> str:
    if type(value) is not str:
        raise DatasetCatalogError(f"{field_name} is required")
    normalized = value.strip()
    if not normalized:
        raise DatasetCatalogError(f"{field_name} is required")
    return normalized


def _optional_string(value: object | None) -> str | None:
    if value is None:
        return None
    if type(value) is not str:
        raise DatasetCatalogError("optional string value must be a string")
    normalized = value.strip()
    return normalized or None


def _coerce_optional_record_string(value: object | None) -> str | None:
    if value is None:
        return None
    return str(value)


def _require_aware_datetime(field_name: str, value: object) -> None:
    if type(value) is not datetime or value.tzinfo is None or value.utcoffset() is None:
        raise DatasetCatalogError(f"{field_name} must be timezone-aware")


__all__ = [
    "DatasetCatalogError",
    "DatasetFileManifest",
    "DatasetReferencePurpose",
    "DatasetVersionManifest",
    "DatasetVersionRef",
    "DatasetVersionRefKind",
    "LocalDatasetCatalog",
]
