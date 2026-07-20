from __future__ import annotations

from datetime import UTC, datetime

import pytest

from serenity_alpha_lab.domain.artifacts import (
    ArtifactManifest,
    ArtifactRetentionTier,
    ArtifactUri,
    InvalidArtifactUri,
)


NOW = datetime(2026, 7, 20, 10, 0, tzinfo=UTC)
SHA256 = "1f" * 32


def test_artifact_manifest_exposes_queryable_metadata() -> None:
    manifest = ArtifactManifest.create(
        sha256=SHA256,
        size_bytes=128,
        schema_name="research.report",
        schema_version="1.0.0",
        content_type="application/json",
        produced_by_run_id="run-001",
        produced_by_stage_id="stage-collect",
        retention_tier=ArtifactRetentionTier.STANDARD,
        created_at=NOW,
    )

    assert str(manifest.uri) == f"artifact://sha256/{SHA256}"
    assert manifest.sha256 == SHA256
    assert manifest.size_bytes == 128
    assert manifest.schema_name == "research.report"
    assert manifest.schema_version == "1.0.0"
    assert manifest.produced_by_run_id == "run-001"
    assert manifest.produced_by_stage_id == "stage-collect"
    assert manifest.retention_tier is ArtifactRetentionTier.STANDARD

    restored = ArtifactManifest.from_record(manifest.to_record())

    assert restored == manifest


def test_artifact_uri_rejects_non_sha256_content_address() -> None:
    with pytest.raises(InvalidArtifactUri):
        ArtifactUri.parse("file:///tmp/report.json")

    with pytest.raises(InvalidArtifactUri):
        ArtifactUri.parse("artifact://sha256/not-a-digest")
