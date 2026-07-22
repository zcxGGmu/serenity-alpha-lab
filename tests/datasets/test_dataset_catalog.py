from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path

import pytest

from serenity_alpha_lab.datasets import (
    RAW_DAILY_BARS_CONTENT_TYPE,
    RAW_DAILY_BARS_SCHEMA_NAME,
    RAW_DAILY_BARS_SCHEMA_VERSION,
    default_dataset_schema_registry,
)
from serenity_alpha_lab.datasets import catalog as catalog_module
from serenity_alpha_lab.datasets.catalog import (
    DatasetCatalogError,
    DatasetFileManifest,
    DatasetReferencePurpose,
    DatasetVersionRef,
    LocalDatasetCatalog,
)
from serenity_alpha_lab.domain.artifacts import ArtifactManifest, ArtifactRetentionTier
from serenity_alpha_lab.repositories.local_artifact_store import LocalArtifactStore


NOW = datetime(2026, 7, 22, 10, 0, tzinfo=UTC)
LATER = datetime(2026, 7, 22, 11, 0, tzinfo=UTC)


def put_dataset_artifact(
    artifact_store: LocalArtifactStore,
    payload: bytes = b'{"records":[{"instrument_id":"600519.XSHG"}]}',
    *,
    run_id: str = "run-dataset-catalog-001",
    stage_id: str = "stage-build-dataset",
    created_at: datetime = NOW,
) -> ArtifactManifest:
    return artifact_store.put_bytes(
        payload,
        schema_name=RAW_DAILY_BARS_SCHEMA_NAME,
        schema_version=RAW_DAILY_BARS_SCHEMA_VERSION,
        content_type=RAW_DAILY_BARS_CONTENT_TYPE,
        produced_by_run_id=run_id,
        produced_by_stage_id=stage_id,
        retention_tier=ArtifactRetentionTier.STANDARD,
        created_at=created_at,
    )


def make_file(artifact: ArtifactManifest, *, row_count: int = 1) -> DatasetFileManifest:
    return DatasetFileManifest.from_artifact(
        artifact,
        row_count=row_count,
        partition_values={"market": "cn", "year": "2026", "month": "07"},
    )


def make_catalog(root: Path) -> LocalDatasetCatalog:
    return LocalDatasetCatalog(root, schema_registry=default_dataset_schema_registry())


def publish_raw_daily_version(
    catalog: LocalDatasetCatalog,
    file_manifest: DatasetFileManifest,
    *,
    created_at: datetime = NOW,
    previous_version_id: str | None = None,
    input_version_ids: tuple[str, ...] = (),
    alias_scope: str = "cn",
    update_latest: bool = True,
    version_id: str | None = None,
):
    return catalog.publish_version(
        dataset_name=RAW_DAILY_BARS_SCHEMA_NAME,
        schema_name=RAW_DAILY_BARS_SCHEMA_NAME,
        schema_version=RAW_DAILY_BARS_SCHEMA_VERSION,
        files=(file_manifest,),
        created_at=created_at,
        created_by_run_id="run-dataset-catalog-001",
        created_by_stage_id="stage-build-dataset",
        trace_id="trace-dataset-catalog-001",
        previous_version_id=previous_version_id,
        input_version_ids=input_version_ids,
        alias_scope=alias_scope,
        update_latest=update_latest,
        version_id=version_id,
        metadata={"provider_policy": "fixture-only"},
    )


def test_catalog_publishes_immutable_version_manifest_and_latest_alias(tmp_path: Path) -> None:
    artifact_store = LocalArtifactStore(tmp_path / "artifacts")
    artifact = put_dataset_artifact(artifact_store)
    catalog = make_catalog(tmp_path / "catalog")

    version = publish_raw_daily_version(catalog, make_file(artifact, row_count=3))
    same_version = catalog.get_version(version.version_id)
    latest = catalog.resolve_latest(RAW_DAILY_BARS_SCHEMA_NAME, "cn")

    assert version.version_id.startswith("dsv_")
    assert version.dataset_name == RAW_DAILY_BARS_SCHEMA_NAME
    assert version.schema_hash == default_dataset_schema_registry().get(
        RAW_DAILY_BARS_SCHEMA_NAME,
        RAW_DAILY_BARS_SCHEMA_VERSION,
    ).schema_hash
    assert version.files[0].artifact_id == artifact.artifact_id
    assert version.files[0].sha256 == artifact.sha256
    assert version.files[0].row_count == 3
    assert version.row_count == 3
    assert same_version == version
    assert latest == version

    stored_payload = json.loads(catalog.version_path_for(version.version_id).read_text(encoding="utf-8"))
    assert stored_payload["schema_hash"] == version.schema_hash
    assert stored_payload["files"][0]["sha256"] == artifact.sha256
    assert stored_payload["metadata"] == {"provider_policy": "fixture-only"}


def test_manifest_records_lineage_previous_version_and_file_hashes(tmp_path: Path) -> None:
    artifact_store = LocalArtifactStore(tmp_path / "artifacts")
    first_artifact = put_dataset_artifact(artifact_store, b'{"records":[{"close":101.0}]}')
    second_artifact = put_dataset_artifact(artifact_store, b'{"records":[{"close":102.0}]}', created_at=LATER)
    catalog = make_catalog(tmp_path / "catalog")

    first = publish_raw_daily_version(catalog, make_file(first_artifact), update_latest=False)
    second = publish_raw_daily_version(
        catalog,
        make_file(second_artifact, row_count=2),
        created_at=LATER,
        previous_version_id=first.version_id,
        input_version_ids=(first.version_id,),
    )

    assert second.previous_version_id == first.version_id
    assert second.input_version_ids == (first.version_id,)
    assert second.file_hashes == (second_artifact.sha256,)
    assert catalog.list_versions(RAW_DAILY_BARS_SCHEMA_NAME) == (first, second)
    assert catalog.get_version(first.version_id).files[0].uri == str(first_artifact.uri)


def test_catalog_rejects_mutation_of_existing_dataset_version(tmp_path: Path) -> None:
    artifact_store = LocalArtifactStore(tmp_path / "artifacts")
    first_artifact = put_dataset_artifact(artifact_store, b'{"records":[{"close":101.0}]}')
    changed_artifact = put_dataset_artifact(artifact_store, b'{"records":[{"close":999.0}]}')
    catalog = make_catalog(tmp_path / "catalog")
    fixed_version_id = "dsv_" + "a" * 32

    first = publish_raw_daily_version(
        catalog,
        make_file(first_artifact),
        update_latest=False,
        version_id=fixed_version_id,
    )
    idempotent = publish_raw_daily_version(
        catalog,
        make_file(first_artifact),
        update_latest=False,
        version_id=fixed_version_id,
    )

    assert idempotent == first
    with pytest.raises(DatasetCatalogError, match="already exists with different manifest"):
        publish_raw_daily_version(
            catalog,
            make_file(changed_artifact),
            update_latest=False,
            version_id=fixed_version_id,
        )


def test_formal_run_resolution_requires_concrete_dataset_version(tmp_path: Path) -> None:
    artifact_store = LocalArtifactStore(tmp_path / "artifacts")
    artifact = put_dataset_artifact(artifact_store)
    catalog = make_catalog(tmp_path / "catalog")
    version = publish_raw_daily_version(catalog, make_file(artifact))

    research_ref = DatasetVersionRef.latest(RAW_DAILY_BARS_SCHEMA_NAME, alias_scope="cn")
    formal_ref = DatasetVersionRef.version(version.version_id)

    assert catalog.resolve_for_run(research_ref, purpose=DatasetReferencePurpose.RESEARCH_DISPLAY) == version
    assert catalog.resolve_for_run(formal_ref, purpose=DatasetReferencePurpose.FORMAL_EXPERIMENT) == version
    with pytest.raises(DatasetCatalogError, match="latest alias cannot be used"):
        catalog.resolve_for_run(research_ref, purpose=DatasetReferencePurpose.FORMAL_EXPERIMENT)


def test_latest_alias_update_is_separate_from_version_manifest_publish(tmp_path: Path, monkeypatch) -> None:
    artifact_store = LocalArtifactStore(tmp_path / "artifacts")
    first_artifact = put_dataset_artifact(artifact_store, b'{"records":[{"close":101.0}]}')
    second_artifact = put_dataset_artifact(artifact_store, b'{"records":[{"close":102.0}]}', created_at=LATER)
    catalog = make_catalog(tmp_path / "catalog")
    first = publish_raw_daily_version(catalog, make_file(first_artifact))
    original_replace = os.replace

    def fail_latest_alias_publish(src, dst) -> None:
        if Path(dst).name == "latest.json":
            raise OSError("simulated latest alias failure")
        original_replace(src, dst)

    monkeypatch.setattr(catalog_module.os, "replace", fail_latest_alias_publish)

    with pytest.raises(OSError, match="simulated latest alias failure"):
        publish_raw_daily_version(catalog, make_file(second_artifact), created_at=LATER)

    assert catalog.resolve_latest(RAW_DAILY_BARS_SCHEMA_NAME, "cn") == first
    assert len(catalog.list_versions(RAW_DAILY_BARS_SCHEMA_NAME)) == 2
