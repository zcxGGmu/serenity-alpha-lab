from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any, Protocol


_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class ArtifactError(ValueError):
    """Base error for artifact contract violations."""


class InvalidArtifactUri(ArtifactError):
    """Raised when an artifact URI is not content-addressed by SHA-256."""


class ArtifactNotFound(ArtifactError):
    """Raised when an artifact record is not present in a store."""


class ArtifactIntegrityError(ArtifactError):
    """Raised when stored bytes no longer match their manifest."""


class ArtifactRetentionTier(StrEnum):
    TEMPORARY = "temporary"
    STANDARD = "standard"
    ARCHIVE = "archive"
    LEGAL_HOLD = "legal_hold"


@dataclass(frozen=True, slots=True)
class ArtifactUri:
    algorithm: str
    digest: str

    @classmethod
    def for_sha256(cls, digest: str) -> ArtifactUri:
        normalized = digest.lower()
        if not _SHA256_RE.fullmatch(normalized):
            raise InvalidArtifactUri("Artifact URI digest must be a 64-character SHA-256 hex value")
        return cls(algorithm="sha256", digest=normalized)

    @classmethod
    def parse(cls, value: str) -> ArtifactUri:
        prefix = "artifact://sha256/"
        if not value.startswith(prefix):
            raise InvalidArtifactUri("Artifact URI must use artifact://sha256/<digest>")
        return cls.for_sha256(value.removeprefix(prefix))

    def __str__(self) -> str:
        return f"artifact://{self.algorithm}/{self.digest}"


@dataclass(frozen=True, slots=True)
class ArtifactManifest:
    artifact_id: str
    uri: ArtifactUri
    sha256: str
    size_bytes: int
    schema_name: str
    schema_version: str
    content_type: str
    produced_by_run_id: str
    retention_tier: ArtifactRetentionTier
    created_at: datetime
    produced_by_stage_id: str | None = None

    @classmethod
    def create(
        cls,
        *,
        sha256: str,
        size_bytes: int,
        schema_name: str,
        schema_version: str,
        content_type: str,
        produced_by_run_id: str,
        retention_tier: ArtifactRetentionTier,
        created_at: datetime,
        produced_by_stage_id: str | None = None,
    ) -> ArtifactManifest:
        uri = ArtifactUri.for_sha256(sha256)
        cls._validate_required("schema_name", schema_name)
        cls._validate_required("schema_version", schema_version)
        cls._validate_required("content_type", content_type)
        cls._validate_required("produced_by_run_id", produced_by_run_id)
        if size_bytes < 0:
            raise ArtifactError("Artifact size cannot be negative")

        artifact_id = cls._derive_artifact_id(
            uri.digest,
            schema_name,
            schema_version,
            content_type,
            produced_by_run_id,
            produced_by_stage_id,
            retention_tier,
        )
        return cls(
            artifact_id=artifact_id,
            uri=uri,
            sha256=uri.digest,
            size_bytes=size_bytes,
            schema_name=schema_name,
            schema_version=schema_version,
            content_type=content_type,
            produced_by_run_id=produced_by_run_id,
            produced_by_stage_id=produced_by_stage_id,
            retention_tier=retention_tier,
            created_at=created_at,
        )

    @classmethod
    def from_record(cls, record: dict[str, Any]) -> ArtifactManifest:
        return cls(
            artifact_id=str(record["artifact_id"]),
            uri=ArtifactUri.parse(str(record["uri"])),
            sha256=ArtifactUri.for_sha256(str(record["sha256"])).digest,
            size_bytes=int(record["size_bytes"]),
            schema_name=str(record["schema_name"]),
            schema_version=str(record["schema_version"]),
            content_type=str(record["content_type"]),
            produced_by_run_id=str(record["produced_by_run_id"]),
            produced_by_stage_id=record.get("produced_by_stage_id"),
            retention_tier=ArtifactRetentionTier(str(record["retention_tier"])),
            created_at=datetime.fromisoformat(str(record["created_at"])),
        )

    def to_record(self) -> dict[str, Any]:
        return {
            "artifact_id": self.artifact_id,
            "uri": str(self.uri),
            "sha256": self.sha256,
            "size_bytes": self.size_bytes,
            "schema_name": self.schema_name,
            "schema_version": self.schema_version,
            "content_type": self.content_type,
            "produced_by_run_id": self.produced_by_run_id,
            "produced_by_stage_id": self.produced_by_stage_id,
            "retention_tier": self.retention_tier.value,
            "created_at": self.created_at.isoformat(),
        }

    @staticmethod
    def _validate_required(field_name: str, value: str) -> None:
        if not value.strip():
            raise ArtifactError(f"{field_name} is required")

    @staticmethod
    def _derive_artifact_id(
        sha256: str,
        schema_name: str,
        schema_version: str,
        content_type: str,
        produced_by_run_id: str,
        produced_by_stage_id: str | None,
        retention_tier: ArtifactRetentionTier,
    ) -> str:
        source = "\0".join(
            [
                "artifact-v1",
                sha256,
                schema_name,
                schema_version,
                content_type,
                produced_by_run_id,
                produced_by_stage_id or "",
                retention_tier.value,
            ]
        )
        return f"art_{hashlib.sha256(source.encode('utf-8')).hexdigest()[:32]}"


class ArtifactStore(Protocol):
    """Port for publishing and reading immutable artifacts."""

    def put_bytes(
        self,
        content: bytes,
        *,
        schema_name: str,
        schema_version: str,
        content_type: str,
        produced_by_run_id: str,
        retention_tier: ArtifactRetentionTier,
        created_at: datetime,
        produced_by_stage_id: str | None = None,
    ) -> ArtifactManifest:
        """Publish content and return a queryable artifact manifest."""

    def get_bytes(self, artifact_id: str) -> bytes:
        """Return content bytes after validating them against the manifest."""

    def get_manifest(self, artifact_id: str) -> ArtifactManifest:
        """Return the published manifest for an artifact."""
