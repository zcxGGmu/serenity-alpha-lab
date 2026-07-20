from __future__ import annotations

import hashlib
import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from serenity_alpha_lab.domain.artifacts import (
    ArtifactIntegrityError,
    ArtifactManifest,
    ArtifactNotFound,
    ArtifactRetentionTier,
    ArtifactUri,
)


class LocalArtifactStore:
    """Filesystem-backed ArtifactStore with manifest-last atomic publishing."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)

    @property
    def blob_root(self) -> Path:
        return self.root / "blobs" / "sha256"

    @property
    def manifest_root(self) -> Path:
        return self.root / "manifests"

    @property
    def tmp_root(self) -> Path:
        return self.root / "tmp"

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
        sha256 = hashlib.sha256(content).hexdigest()
        manifest = ArtifactManifest.create(
            sha256=sha256,
            size_bytes=len(content),
            schema_name=schema_name,
            schema_version=schema_version,
            content_type=content_type,
            produced_by_run_id=produced_by_run_id,
            produced_by_stage_id=produced_by_stage_id,
            retention_tier=retention_tier,
            created_at=created_at,
        )
        self._ensure_directories()

        manifest_path = self.manifest_path_for(manifest.artifact_id)
        if manifest_path.exists():
            return self.get_manifest(manifest.artifact_id)

        blob_path = self.blob_path_for(manifest.sha256)
        blob_existed = blob_path.exists()
        blob_published = False
        token = uuid.uuid4().hex
        blob_tmp = self.tmp_root / f"{manifest.artifact_id}.{token}.blob.tmp"
        manifest_tmp = self.tmp_root / f"{manifest.artifact_id}.{token}.manifest.tmp"

        try:
            if not blob_existed:
                blob_path.parent.mkdir(parents=True, exist_ok=True)
                self._write_bytes(blob_tmp, content)
            self._write_json(manifest_tmp, manifest.to_record())

            if not blob_existed:
                os.replace(blob_tmp, blob_path)
                blob_published = True
            os.replace(manifest_tmp, manifest_path)
        except Exception:
            self._cleanup_tmp(blob_tmp, manifest_tmp)
            if blob_published and not blob_existed:
                blob_path.unlink(missing_ok=True)
            raise
        finally:
            self._cleanup_tmp(blob_tmp, manifest_tmp)

        return manifest

    def get_bytes(self, artifact_id: str) -> bytes:
        manifest = self.get_manifest(artifact_id)
        path = self.blob_path_for(manifest.sha256)
        try:
            content = path.read_bytes()
        except FileNotFoundError as exc:
            raise ArtifactNotFound(f"Artifact blob not found: {artifact_id}") from exc

        if len(content) != manifest.size_bytes:
            raise ArtifactIntegrityError(f"Artifact size mismatch: {artifact_id}")
        actual_sha256 = hashlib.sha256(content).hexdigest()
        if actual_sha256 != manifest.sha256:
            raise ArtifactIntegrityError(f"Artifact hash mismatch: {artifact_id}")
        return content

    def get_manifest(self, artifact_id: str) -> ArtifactManifest:
        path = self.manifest_path_for(artifact_id)
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise ArtifactNotFound(f"Artifact manifest not found: {artifact_id}") from exc
        except json.JSONDecodeError as exc:
            raise ArtifactIntegrityError(f"Artifact manifest is not valid JSON: {artifact_id}") from exc
        return ArtifactManifest.from_record(record)

    def list_manifests(self) -> list[ArtifactManifest]:
        if not self.manifest_root.exists():
            return []
        return [self.get_manifest(path.stem) for path in sorted(self.manifest_root.glob("*.json"))]

    def blob_path_for(self, sha256: str) -> Path:
        digest = ArtifactUri.for_sha256(sha256).digest
        return self.blob_root / digest[:2] / f"{digest}.blob"

    def manifest_path_for(self, artifact_id: str) -> Path:
        return self.manifest_root / f"{artifact_id}.json"

    def _ensure_directories(self) -> None:
        self.blob_root.mkdir(parents=True, exist_ok=True)
        self.manifest_root.mkdir(parents=True, exist_ok=True)
        self.tmp_root.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _write_bytes(path: Path, content: bytes) -> None:
        with path.open("wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())

    @staticmethod
    def _write_json(path: Path, record: dict[str, Any]) -> None:
        payload = json.dumps(record, indent=2, sort_keys=True).encode("utf-8")
        with path.open("wb") as handle:
            handle.write(payload)
            handle.write(b"\n")
            handle.flush()
            os.fsync(handle.fileno())

    @staticmethod
    def _cleanup_tmp(*paths: Path) -> None:
        for path in paths:
            path.unlink(missing_ok=True)
