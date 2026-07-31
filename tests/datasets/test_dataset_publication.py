from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from serenity_alpha_lab.datasets import (
    RAW_DAILY_BARS_CONTENT_TYPE,
    RAW_DAILY_BARS_SCHEMA_NAME,
    RAW_DAILY_BARS_SCHEMA_VERSION,
    DatasetFileManifest,
    default_dataset_schema_registry,
)
from serenity_alpha_lab.datasets.publication import (
    DatasetPublicationRequest,
    DatasetPublicationStatus,
    QualityGatedDatasetPublisher,
)
from serenity_alpha_lab.datasets.quality import (
    DataQualityIssue,
    DataQualityReport,
    DataQualitySeverity,
    DataQualityStatus,
)
from serenity_alpha_lab.domain.artifacts import ArtifactManifest, ArtifactRetentionTier
from serenity_alpha_lab.repositories.local_artifact_store import LocalArtifactStore
from serenity_alpha_lab.datasets.catalog import LocalDatasetCatalog


NOW = datetime(2026, 7, 23, 10, 0, tzinfo=UTC)


def make_artifact_store(root: Path) -> LocalArtifactStore:
    return LocalArtifactStore(root / "artifacts")


def make_catalog(root: Path) -> LocalDatasetCatalog:
    return LocalDatasetCatalog(root / "catalog", schema_registry=default_dataset_schema_registry())


def put_dataset_artifact(
    store: LocalArtifactStore,
    *,
    payload: bytes = b'{"records":[{"instrument_id":"600519.XSHG","trade_date":"2026-07-22"}]}',
    run_id: str = "run-publication-001",
    stage_id: str = "stage-build-dataset",
    created_at: datetime = NOW,
) -> ArtifactManifest:
    return store.put_bytes(
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


def make_report(status: DataQualityStatus, *, run_id: str = "run-publication-001") -> DataQualityReport:
    schema = default_dataset_schema_registry().get(RAW_DAILY_BARS_SCHEMA_NAME, RAW_DAILY_BARS_SCHEMA_VERSION)
    severity_by_status = {
        DataQualityStatus.WARNING: DataQualitySeverity.WARNING,
        DataQualityStatus.QUARANTINE: DataQualitySeverity.QUARANTINE,
        DataQualityStatus.BLOCKING: DataQualitySeverity.BLOCKING,
    }
    issues = ()
    if status is not DataQualityStatus.PASSED:
        severity = severity_by_status[status]
        issues = (
            DataQualityIssue(
                rule_id=f"publication.{status.value}",
                rule_version="1.0.0",
                severity=severity,
                dataset_name=RAW_DAILY_BARS_SCHEMA_NAME,
                message=f"Publication fixture issue for {status.value}.",
                dataset_version_id=None,
                partition_values={"market": "cn", "year": "2026", "month": "07"},
                field_name="close",
                primary_key={
                    "instrument_id": "600519.XSHG",
                    "trade_date": "2026-07-22",
                    "provider_id": "dsa:EfinanceFetcher",
                },
                observed_value=status.value,
                expected_value="passed",
                sample={"instrument_id": "600519.XSHG", "close": 101.0},
            ),
        )
    return DataQualityReport(
        dataset_name=RAW_DAILY_BARS_SCHEMA_NAME,
        schema_name=RAW_DAILY_BARS_SCHEMA_NAME,
        schema_version=RAW_DAILY_BARS_SCHEMA_VERSION,
        schema_hash=schema.schema_hash,
        rule_set_version="dq-p2-013.1",
        generated_at=NOW,
        records_evaluated=1,
        issues=issues,
        trace_id="trace-publication-001",
        run_id=run_id,
        stage_id="stage-quality-report",
    )


def make_request(
    data_artifact: ArtifactManifest,
    report: DataQualityReport,
    *,
    previous_version_id: str | None = None,
    run_id: str = "run-publication-001",
) -> DatasetPublicationRequest:
    return DatasetPublicationRequest(
        dataset_name=RAW_DAILY_BARS_SCHEMA_NAME,
        schema_name=RAW_DAILY_BARS_SCHEMA_NAME,
        schema_version=RAW_DAILY_BARS_SCHEMA_VERSION,
        files=(make_file(data_artifact),),
        quality_report=report,
        created_at=NOW,
        created_by_run_id=run_id,
        created_by_stage_id="stage-build-dataset",
        trace_id="trace-publication-001",
        previous_version_id=previous_version_id,
        alias_scope="cn",
        metadata={"provider_policy": "fixture-only"},
    )


def test_passed_quality_promotes_version_to_latest_and_records_metadata(tmp_path: Path) -> None:
    artifact_store = make_artifact_store(tmp_path)
    catalog = make_catalog(tmp_path)
    publisher = QualityGatedDatasetPublisher(catalog=catalog, artifact_store=artifact_store)
    data_artifact = put_dataset_artifact(artifact_store)

    result = publisher.publish(make_request(data_artifact, make_report(DataQualityStatus.PASSED)))

    assert result.status is DatasetPublicationStatus.PUBLISHED
    assert result.latest_updated is True
    assert result.quality_report_artifact is not None
    assert catalog.resolve_latest(RAW_DAILY_BARS_SCHEMA_NAME, "cn") == result.manifest
    assert result.manifest.metadata["quality_status"] == "passed"
    assert result.manifest.metadata["publication_status"] == "published"
    assert result.manifest.metadata["quality_report_artifact_id"] == result.quality_report_artifact.artifact_id
    assert result.manifest.metadata["quality_report_sha256"] == result.quality_report_artifact.sha256
    assert catalog.list_quarantine_records(RAW_DAILY_BARS_SCHEMA_NAME, "cn") == ()


@pytest.mark.parametrize(
    ("quality_status", "publication_status"),
    [
        (DataQualityStatus.WARNING, DatasetPublicationStatus.HELD),
        (DataQualityStatus.QUARANTINE, DatasetPublicationStatus.QUARANTINED),
        (DataQualityStatus.BLOCKING, DatasetPublicationStatus.BLOCKED),
    ],
)
def test_warning_quarantine_and_blocking_versions_do_not_replace_latest(
    tmp_path: Path,
    quality_status: DataQualityStatus,
    publication_status: DatasetPublicationStatus,
) -> None:
    artifact_store = make_artifact_store(tmp_path)
    catalog = make_catalog(tmp_path)
    publisher = QualityGatedDatasetPublisher(catalog=catalog, artifact_store=artifact_store)
    passed_artifact = put_dataset_artifact(artifact_store, payload=b'{"records":[{"close":101.0}]}')
    old_latest = publisher.publish(make_request(passed_artifact, make_report(DataQualityStatus.PASSED))).manifest
    held_artifact = put_dataset_artifact(
        artifact_store,
        payload=f'{{"records":[{{"close":"{quality_status.value}"}}]}}'.encode("utf-8"),
        run_id=f"run-publication-{quality_status.value}",
    )

    result = publisher.publish(
        make_request(
            held_artifact,
            make_report(quality_status, run_id=f"run-publication-{quality_status.value}"),
            previous_version_id=old_latest.version_id,
            run_id=f"run-publication-{quality_status.value}",
        )
    )

    assert result.status is publication_status
    assert result.latest_updated is False
    assert catalog.resolve_latest(RAW_DAILY_BARS_SCHEMA_NAME, "cn") == old_latest
    assert result.manifest.metadata["quality_status"] == quality_status.value
    assert result.manifest.metadata["publication_status"] == publication_status.value

    quarantine_records = catalog.list_quarantine_records(RAW_DAILY_BARS_SCHEMA_NAME, "cn")
    assert len(quarantine_records) == 1
    quarantine_record = quarantine_records[0]
    assert quarantine_record["dataset_name"] == RAW_DAILY_BARS_SCHEMA_NAME
    assert quarantine_record["version_id"] == result.manifest.version_id
    assert quarantine_record["quality_status"] == quality_status.value
    assert quarantine_record["publication_status"] == publication_status.value


def test_failed_publication_keeps_old_latest_and_cleans_tmp_files(tmp_path: Path, monkeypatch) -> None:
    artifact_store = make_artifact_store(tmp_path)
    catalog = make_catalog(tmp_path)
    publisher = QualityGatedDatasetPublisher(catalog=catalog, artifact_store=artifact_store)
    old_artifact = put_dataset_artifact(artifact_store, payload=b'{"records":[{"close":101.0}]}')
    old_latest = publisher.publish(make_request(old_artifact, make_report(DataQualityStatus.PASSED))).manifest
    failing_artifact = put_dataset_artifact(artifact_store, payload=b'{"records":[{"close":102.0}]}')
    catalog.tmp_root.mkdir(parents=True, exist_ok=True)
    artifact_store.tmp_root.mkdir(parents=True, exist_ok=True)
    (catalog.tmp_root / "stale-catalog.tmp").write_text("stale", encoding="utf-8")
    (artifact_store.tmp_root / "stale-artifact.tmp").write_text("stale", encoding="utf-8")

    def fail_latest_promotion(version_id: str, alias_scope: str = "global"):
        raise OSError(f"simulated latest promotion failure for {version_id} {alias_scope}")

    monkeypatch.setattr(catalog, "promote_to_latest", fail_latest_promotion)

    with pytest.raises(OSError, match="simulated latest promotion failure"):
        publisher.publish(make_request(failing_artifact, make_report(DataQualityStatus.PASSED)))

    assert catalog.resolve_latest(RAW_DAILY_BARS_SCHEMA_NAME, "cn") == old_latest
    assert list(catalog.tmp_root.iterdir()) == []
    assert list(artifact_store.tmp_root.iterdir()) == []
