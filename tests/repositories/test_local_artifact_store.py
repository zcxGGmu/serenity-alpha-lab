from __future__ import annotations

import os
from datetime import UTC, datetime

import pytest

from serenity_alpha_lab.domain.artifacts import ArtifactIntegrityError, ArtifactRetentionTier
from serenity_alpha_lab.repositories import local_artifact_store as local_store_module
from serenity_alpha_lab.repositories.local_artifact_store import LocalArtifactStore


NOW = datetime(2026, 7, 20, 10, 30, tzinfo=UTC)


def write_report(store: LocalArtifactStore, payload: bytes = b'{"score": 0.87}'):
    return store.put_bytes(
        payload,
        schema_name="research.report",
        schema_version="1.0.0",
        content_type="application/json",
        produced_by_run_id="run-001",
        produced_by_stage_id="stage-collect",
        retention_tier=ArtifactRetentionTier.STANDARD,
        created_at=NOW,
    )


def test_local_store_publishes_queryable_manifest_and_hash_verified_content(tmp_path) -> None:
    store = LocalArtifactStore(tmp_path / "artifacts")

    manifest = write_report(store)

    assert manifest.sha256
    assert manifest.size_bytes == len(b'{"score": 0.87}')
    assert manifest.schema_name == "research.report"
    assert manifest.schema_version == "1.0.0"
    assert manifest.produced_by_run_id == "run-001"
    assert manifest.produced_by_stage_id == "stage-collect"
    assert manifest.retention_tier is ArtifactRetentionTier.STANDARD
    assert store.get_bytes(manifest.artifact_id) == b'{"score": 0.87}'
    assert store.get_manifest(manifest.artifact_id) == manifest


def test_local_store_reuses_same_artifact_record_for_idempotent_write(tmp_path) -> None:
    store = LocalArtifactStore(tmp_path / "artifacts")

    first = write_report(store)
    second = write_report(store)

    assert second == first
    assert [manifest.artifact_id for manifest in store.list_manifests()] == [first.artifact_id]


def test_failed_manifest_publish_does_not_expose_record_or_leave_temp_files(tmp_path, monkeypatch) -> None:
    store = LocalArtifactStore(tmp_path / "artifacts")
    original_replace = os.replace

    def fail_manifest_publish(src, dst) -> None:
        if "manifests" in os.fspath(dst):
            raise OSError("simulated manifest publish failure")
        original_replace(src, dst)

    monkeypatch.setattr(local_store_module.os, "replace", fail_manifest_publish)

    with pytest.raises(OSError, match="simulated manifest publish failure"):
        write_report(store)

    assert store.list_manifests() == []
    assert [path for path in store.manifest_root.rglob("*.json")] == []
    assert [path for path in store.blob_root.rglob("*") if path.is_file()] == []
    assert [path for path in store.tmp_root.rglob("*") if path.is_file()] == []


def test_local_store_detects_corrupt_content_by_manifest_hash(tmp_path) -> None:
    store = LocalArtifactStore(tmp_path / "artifacts")
    manifest = write_report(store)
    blob_path = store.blob_path_for(manifest.sha256)
    blob_path.write_bytes(b'{"score": 9.99}')

    with pytest.raises(ArtifactIntegrityError, match="hash mismatch"):
        store.get_bytes(manifest.artifact_id)
