from __future__ import annotations

import shutil
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from types import MappingProxyType

from serenity_alpha_lab.datasets.catalog import (
    DatasetFileManifest,
    DatasetVersionManifest,
    LocalDatasetCatalog,
)
from serenity_alpha_lab.datasets.quality import DataQualityReport, DataQualityStatus
from serenity_alpha_lab.domain.artifacts import ArtifactManifest, ArtifactRetentionTier, ArtifactStore


class DatasetPublicationError(ValueError):
    """Raised when a Dataset publication request violates the quality gate contract."""


class DatasetPublicationStatus(StrEnum):
    PUBLISHED = "published"
    HELD = "held"
    QUARANTINED = "quarantined"
    BLOCKED = "blocked"


@dataclass(frozen=True, slots=True)
class DatasetPublicationRequest:
    dataset_name: str
    schema_name: str
    schema_version: str
    files: Sequence[DatasetFileManifest]
    quality_report: DataQualityReport
    created_at: datetime
    created_by_run_id: str
    created_by_stage_id: str | None = None
    trace_id: str | None = None
    previous_version_id: str | None = None
    input_version_ids: Sequence[str] = ()
    alias_scope: str = "global"
    version_id: str | None = None
    metadata: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "dataset_name", _required_string("dataset_name", self.dataset_name))
        object.__setattr__(self, "schema_name", _required_string("schema_name", self.schema_name))
        object.__setattr__(self, "schema_version", _required_string("schema_version", self.schema_version))
        if type(self.quality_report) is not DataQualityReport:
            raise DatasetPublicationError("quality_report must be a DataQualityReport")
        if self.quality_report.dataset_name != self.dataset_name:
            raise DatasetPublicationError("quality_report dataset_name must match request dataset_name")
        if self.quality_report.schema_name != self.schema_name:
            raise DatasetPublicationError("quality_report schema_name must match request schema_name")
        if self.quality_report.schema_version != self.schema_version:
            raise DatasetPublicationError("quality_report schema_version must match request schema_version")
        files = tuple(self.files)
        if not files:
            raise DatasetPublicationError("files are required")
        for file_manifest in files:
            if type(file_manifest) is not DatasetFileManifest:
                raise DatasetPublicationError("files must contain DatasetFileManifest values")
        object.__setattr__(self, "files", files)
        object.__setattr__(self, "created_by_run_id", _required_string("created_by_run_id", self.created_by_run_id))
        object.__setattr__(self, "alias_scope", _required_string("alias_scope", self.alias_scope))
        object.__setattr__(self, "input_version_ids", tuple(self.input_version_ids))
        metadata: dict[str, str] = {}
        for key, value in self.metadata.items():
            metadata[_required_string("metadata key", key)] = _required_string("metadata value", value)
        object.__setattr__(self, "metadata", MappingProxyType(metadata))


@dataclass(frozen=True, slots=True)
class DatasetPublicationResult:
    manifest: DatasetVersionManifest
    status: DatasetPublicationStatus
    quality_report_artifact: ArtifactManifest | None
    latest_updated: bool
    quarantine_record: Mapping[str, object] | None = None

    def __post_init__(self) -> None:
        if type(self.manifest) is not DatasetVersionManifest:
            raise DatasetPublicationError("manifest must be a DatasetVersionManifest")
        object.__setattr__(self, "status", DatasetPublicationStatus(self.status))
        if self.quality_report_artifact is not None and type(self.quality_report_artifact) is not ArtifactManifest:
            raise DatasetPublicationError("quality_report_artifact must be an ArtifactManifest")
        if type(self.latest_updated) is not bool:
            raise DatasetPublicationError("latest_updated must be a bool")
        if self.quarantine_record is not None:
            object.__setattr__(self, "quarantine_record", MappingProxyType(dict(self.quarantine_record)))


@dataclass(slots=True)
class QualityGatedDatasetPublisher:
    catalog: LocalDatasetCatalog
    artifact_store: ArtifactStore

    def __post_init__(self) -> None:
        if type(self.catalog) is not LocalDatasetCatalog:
            raise DatasetPublicationError("catalog must be a LocalDatasetCatalog")

    def publish(self, request: DatasetPublicationRequest) -> DatasetPublicationResult:
        if type(request) is not DatasetPublicationRequest:
            raise DatasetPublicationError("request must be a DatasetPublicationRequest")
        try:
            publication_status = _publication_status_for_quality(request.quality_report.status)
            quality_report_artifact = request.quality_report.publish(
                self.artifact_store,
                produced_by_run_id=request.created_by_run_id,
                produced_by_stage_id=request.quality_report.stage_id or request.created_by_stage_id,
                retention_tier=ArtifactRetentionTier.STANDARD,
            )
            metadata = dict(request.metadata)
            metadata.update(request.quality_report.manifest_metadata(report_artifact=quality_report_artifact))
            metadata["publication_status"] = publication_status.value
            manifest = self.catalog.publish_version(
                dataset_name=request.dataset_name,
                schema_name=request.schema_name,
                schema_version=request.schema_version,
                files=request.files,
                created_at=request.created_at,
                created_by_run_id=request.created_by_run_id,
                created_by_stage_id=request.created_by_stage_id,
                trace_id=request.trace_id,
                previous_version_id=request.previous_version_id,
                input_version_ids=request.input_version_ids,
                alias_scope=request.alias_scope,
                update_latest=False,
                version_id=request.version_id,
                metadata=metadata,
            )
            if publication_status is DatasetPublicationStatus.PUBLISHED:
                self.catalog.promote_to_latest(manifest.version_id, alias_scope=request.alias_scope)
                return DatasetPublicationResult(
                    manifest=manifest,
                    status=publication_status,
                    quality_report_artifact=quality_report_artifact,
                    latest_updated=True,
                )

            quarantine_record = self.catalog.record_quarantine(
                _quarantine_record_for(
                    manifest,
                    request=request,
                    publication_status=publication_status,
                    quality_report_artifact=quality_report_artifact,
                )
            )
            return DatasetPublicationResult(
                manifest=manifest,
                status=publication_status,
                quality_report_artifact=quality_report_artifact,
                latest_updated=False,
                quarantine_record=quarantine_record,
            )
        except Exception:
            cleanup_temporary_paths(self.catalog.tmp_root, _tmp_root_for(self.artifact_store))
            raise


def cleanup_temporary_paths(*roots: Path | str | None) -> None:
    """Remove files below explicit temporary roots without deleting the roots themselves."""

    for root in roots:
        if root is None:
            continue
        path = Path(root)
        if not path.exists():
            continue
        for child in path.iterdir():
            if child.is_dir() and not child.is_symlink():
                shutil.rmtree(child)
                continue
            child.unlink(missing_ok=True)


def _publication_status_for_quality(status: DataQualityStatus) -> DatasetPublicationStatus:
    quality_status = DataQualityStatus(status)
    if quality_status is DataQualityStatus.PASSED:
        return DatasetPublicationStatus.PUBLISHED
    if quality_status is DataQualityStatus.WARNING:
        return DatasetPublicationStatus.HELD
    if quality_status is DataQualityStatus.QUARANTINE:
        return DatasetPublicationStatus.QUARANTINED
    return DatasetPublicationStatus.BLOCKED


def _quarantine_record_for(
    manifest: DatasetVersionManifest,
    *,
    request: DatasetPublicationRequest,
    publication_status: DatasetPublicationStatus,
    quality_report_artifact: ArtifactManifest,
) -> dict[str, object]:
    report = request.quality_report
    return {
        "dataset_name": manifest.dataset_name,
        "alias_scope": request.alias_scope,
        "version_id": manifest.version_id,
        "created_at": request.created_at.isoformat(),
        "created_by_run_id": request.created_by_run_id,
        "created_by_stage_id": request.created_by_stage_id,
        "trace_id": request.trace_id,
        "quality_status": report.status.value,
        "publication_status": publication_status.value,
        "quality_rule_set_version": report.rule_set_version,
        "quality_report_artifact_id": quality_report_artifact.artifact_id,
        "quality_report_sha256": quality_report_artifact.sha256,
        "quality_issue_counts": report.issue_counts,
        "quality_issue_count_total": len(report.issues),
    }


def _tmp_root_for(artifact_store: ArtifactStore) -> Path | None:
    tmp_root = getattr(artifact_store, "tmp_root", None)
    if tmp_root is None:
        return None
    return Path(tmp_root)


def _required_string(field_name: str, value: object | None) -> str:
    if type(value) is not str:
        raise DatasetPublicationError(f"{field_name} is required")
    normalized = value.strip()
    if not normalized:
        raise DatasetPublicationError(f"{field_name} is required")
    return normalized


__all__ = [
    "DatasetPublicationError",
    "DatasetPublicationRequest",
    "DatasetPublicationResult",
    "DatasetPublicationStatus",
    "QualityGatedDatasetPublisher",
    "cleanup_temporary_paths",
]
