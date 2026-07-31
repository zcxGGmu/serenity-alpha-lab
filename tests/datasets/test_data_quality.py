from __future__ import annotations

import json
from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from serenity_alpha_lab.application.api_errors import ApiErrorCode, problem_from_exception
from serenity_alpha_lab.application.tracing import TraceContext
from serenity_alpha_lab.datasets import (
    ADJUSTED_DAILY_BARS_CONTENT_TYPE,
    ADJUSTED_DAILY_BARS_SCHEMA_NAME,
    ADJUSTED_DAILY_BARS_SCHEMA_VERSION,
    RAW_DAILY_BARS_CONTENT_TYPE,
    RAW_DAILY_BARS_SCHEMA_NAME,
    RAW_DAILY_BARS_SCHEMA_VERSION,
    DatasetFileManifest,
    default_dataset_schema_registry,
)
from serenity_alpha_lab.datasets.catalog import LocalDatasetCatalog
from serenity_alpha_lab.datasets.quality import (
    AdjustmentFactorJumpRule,
    DataQualityEngine,
    DataQualityReport,
    DataQualitySeverity,
    DataQualityStatus,
    DataQualityRuleError,
    NonNegativeFieldRule,
    NullRatioDriftRule,
    OhlcRelationshipRule,
    QualityDatasetSnapshot,
    ReturnOutlierRule,
    SchemaFieldRule,
    TradingContinuityRule,
    UniquePrimaryKeyRule,
    VolumeSpikeRule,
)
from serenity_alpha_lab.domain.artifacts import ArtifactRetentionTier
from serenity_alpha_lab.repositories.local_artifact_store import LocalArtifactStore


NOW = datetime(2026, 7, 22, 10, 0, tzinfo=UTC)


def raw_schema():
    return default_dataset_schema_registry().get(RAW_DAILY_BARS_SCHEMA_NAME, RAW_DAILY_BARS_SCHEMA_VERSION)


def adjusted_schema():
    return default_dataset_schema_registry().get(
        ADJUSTED_DAILY_BARS_SCHEMA_NAME,
        ADJUSTED_DAILY_BARS_SCHEMA_VERSION,
    )


def raw_row(
    instrument_id: str,
    trade_date: str,
    *,
    open: object = 100.0,
    high: object = 102.0,
    low: object = 99.0,
    close: object = 101.0,
    volume: object = 1000.0,
    amount: object = 101000.0,
    provider_id: str = "dsa:EfinanceFetcher",
) -> dict[str, object]:
    return {
        "instrument_id": instrument_id,
        "market": "cn",
        "exchange": "XSHG" if instrument_id.endswith(".XSHG") else "XSHE",
        "trade_date": trade_date,
        "provider_id": provider_id,
        "provider_source": "EfinanceFetcher",
        "open": open,
        "high": high,
        "low": low,
        "close": close,
        "volume": volume,
        "amount": amount,
        "currency": "CNY",
        "adjustment": "unadjusted",
        "provider_source_timestamp": "2026-07-22T08:00:00+00:00",
        "provider_raw_response_sha256": "a" * 64,
        "source_bronze_artifact_id": "art_bronze_raw_daily_quality_001",
        "partition": {"market": "cn", "year": "2026", "month": "07"},
    }


def adjusted_row(
    trade_date: str,
    *,
    adjustment_factor: float,
) -> dict[str, object]:
    row = raw_row("600519.XSHG", trade_date)
    row.update(
        {
            "adjustment": "forward",
            "adjustment_factor": adjustment_factor,
            "raw_open": row["open"],
            "raw_high": row["high"],
            "raw_low": row["low"],
            "raw_close": row["close"],
            "source_raw_bronze_artifact_id": "art_bronze_raw_daily_quality_001",
            "source_corporate_action_artifact_ids": ["art_bronze_ca_quality_001"],
        }
    )
    row.pop("source_bronze_artifact_id")
    return row


def make_snapshot(
    records: list[dict[str, object]],
    *,
    dataset_version_id: str | None = "dsv_" + "1" * 32,
) -> QualityDatasetSnapshot:
    return QualityDatasetSnapshot.from_records(
        dataset_name=RAW_DAILY_BARS_SCHEMA_NAME,
        schema_declaration=raw_schema(),
        records=records,
        dataset_version_id=dataset_version_id,
    )


def test_quality_engine_reports_blocking_schema_key_ohlc_and_null_drift() -> None:
    records = [
        raw_row("600519.XSHG", "2026-07-20", close=101.0),
        raw_row("600519.XSHG", "2026-07-20", close=101.5),
        raw_row("600519.XSHG", "2026-07-21", open=105.0, high=104.0, low=99.0, close=103.0, volume=-1.0),
        raw_row("000001.XSHE", "2026-07-21", amount=None),
    ]
    engine = DataQualityEngine(
        rule_set_version="dq-p2-012.1",
        rules=(
            UniquePrimaryKeyRule(),
            SchemaFieldRule(),
            OhlcRelationshipRule(),
            NonNegativeFieldRule(fields=("volume", "amount")),
            NullRatioDriftRule(
                baseline_null_ratios={"amount": 0.0},
                max_delta=0.10,
                severity=DataQualitySeverity.QUARANTINE,
            ),
        ),
    )

    report = engine.evaluate(make_snapshot(records), generated_at=NOW, trace_id="trace-quality-001")

    assert report.status is DataQualityStatus.BLOCKING
    assert report.issue_counts == {"warning": 0, "quarantine": 1, "blocking": 4}
    assert {issue.rule_id for issue in report.issues} == {
        "schema.required_fields_and_types",
        "primary_key.unique",
        "bars.ohlc_relationship",
        "fields.non_negative",
        "fields.null_ratio_drift",
    }
    duplicate = next(issue for issue in report.issues if issue.rule_id == "primary_key.unique")
    assert duplicate.primary_key == {
        "instrument_id": "600519.XSHG",
        "trade_date": "2026-07-20",
        "provider_id": "dsa:EfinanceFetcher",
    }
    assert duplicate.partition_values == {"market": "cn", "month": "07", "year": "2026"}
    assert duplicate.sample["close"] == 101.5
    null_drift = next(issue for issue in report.issues if issue.rule_id == "fields.null_ratio_drift")
    assert null_drift.severity is DataQualitySeverity.QUARANTINE
    assert null_drift.field_name == "amount"
    assert null_drift.primary_key == {
        "instrument_id": "000001.XSHE",
        "trade_date": "2026-07-21",
        "provider_id": "dsa:EfinanceFetcher",
    }
    assert null_drift.partition_values == {"market": "cn", "month": "07", "year": "2026"}
    assert null_drift.sample["instrument_id"] == "000001.XSHE"
    assert null_drift.dataset_name == RAW_DAILY_BARS_SCHEMA_NAME
    assert null_drift.dataset_version_id == "dsv_" + "1" * 32


def test_quality_engine_detects_continuity_outliers_factor_jumps_and_publishes_report(tmp_path: Path) -> None:
    raw_snapshot = make_snapshot(
        [
            raw_row("600519.XSHG", "2026-07-17", close=100.0, volume=1000.0),
            raw_row("600519.XSHG", "2026-07-21", close=130.0, volume=5000.0),
        ]
    )
    adjusted_snapshot = QualityDatasetSnapshot.from_records(
        dataset_name=ADJUSTED_DAILY_BARS_SCHEMA_NAME,
        schema_declaration=adjusted_schema(),
        records=[
            adjusted_row("2026-07-20", adjustment_factor=1.0),
            adjusted_row("2026-07-21", adjustment_factor=1.5),
        ],
    )
    engine = DataQualityEngine(
        rule_set_version="dq-p2-012.2",
        rules=(
            TradingContinuityRule(
                expected_trade_dates_by_market={"cn": (date(2026, 7, 17), date(2026, 7, 20), date(2026, 7, 21))}
            ),
            ReturnOutlierRule(max_abs_return=0.10, severity=DataQualitySeverity.WARNING),
            VolumeSpikeRule(max_multiple=3.0, severity=DataQualitySeverity.WARNING),
        ),
    )
    adjusted_engine = DataQualityEngine(
        rule_set_version="dq-p2-012.2",
        rules=(AdjustmentFactorJumpRule(max_abs_pct_change=0.20, severity=DataQualitySeverity.QUARANTINE),),
    )

    raw_report = engine.evaluate(raw_snapshot, generated_at=NOW, run_id="run-quality-001")
    adjusted_report = adjusted_engine.evaluate(adjusted_snapshot, generated_at=NOW, run_id="run-quality-001")
    store = LocalArtifactStore(tmp_path / "artifacts")
    artifact = raw_report.publish(
        store,
        produced_by_run_id="run-quality-001",
        produced_by_stage_id="stage-quality-report",
    )
    payload = json.loads(store.get_bytes(artifact.artifact_id).decode("utf-8"))

    assert raw_report.status is DataQualityStatus.QUARANTINE
    assert raw_report.issue_counts == {"warning": 2, "quarantine": 1, "blocking": 0}
    assert [issue.rule_id for issue in raw_report.issues] == [
        "bars.trading_continuity",
        "bars.return_outlier",
        "bars.volume_spike",
    ]
    assert raw_report.issues[0].field_name == "trade_date"
    assert raw_report.issues[0].observed_value == "missing:2026-07-20"
    assert adjusted_report.status is DataQualityStatus.QUARANTINE
    assert adjusted_report.issues[0].rule_id == "adjusted_bars.factor_jump"
    assert artifact.schema_name == DataQualityReport.REPORT_SCHEMA_NAME
    assert artifact.schema_version == DataQualityReport.REPORT_SCHEMA_VERSION
    assert artifact.content_type == DataQualityReport.REPORT_CONTENT_TYPE
    assert artifact.retention_tier is ArtifactRetentionTier.STANDARD
    assert payload["dataset_name"] == RAW_DAILY_BARS_SCHEMA_NAME
    assert payload["quality_status"] == "quarantine"
    assert payload["issues"][0]["partition_values"] == {"market": "cn", "month": "07", "year": "2026"}


def test_quality_report_metadata_can_be_recorded_in_dataset_manifest(tmp_path: Path) -> None:
    artifact_store = LocalArtifactStore(tmp_path / "artifacts")
    data_artifact = artifact_store.put_bytes(
        b'{"records":[{"instrument_id":"600519.XSHG"}]}',
        schema_name=RAW_DAILY_BARS_SCHEMA_NAME,
        schema_version=RAW_DAILY_BARS_SCHEMA_VERSION,
        content_type=RAW_DAILY_BARS_CONTENT_TYPE,
        produced_by_run_id="run-quality-manifest",
        produced_by_stage_id="stage-dataset-build",
        retention_tier=ArtifactRetentionTier.STANDARD,
        created_at=NOW,
    )
    report = DataQualityEngine(
        rule_set_version="dq-p2-012.3",
        rules=(ReturnOutlierRule(max_abs_return=0.01, severity=DataQualitySeverity.WARNING),),
    ).evaluate(
        make_snapshot(
            [
                raw_row("600519.XSHG", "2026-07-20", close=100.0),
                raw_row("600519.XSHG", "2026-07-21", close=102.0),
            ],
            dataset_version_id=None,
        ),
        generated_at=NOW,
    )
    report_artifact = report.publish(
        artifact_store,
        produced_by_run_id="run-quality-manifest",
        produced_by_stage_id="stage-quality-report",
    )
    catalog = LocalDatasetCatalog(tmp_path / "catalog", schema_registry=default_dataset_schema_registry())

    version = catalog.publish_version(
        dataset_name=RAW_DAILY_BARS_SCHEMA_NAME,
        schema_name=RAW_DAILY_BARS_SCHEMA_NAME,
        schema_version=RAW_DAILY_BARS_SCHEMA_VERSION,
        files=(
            DatasetFileManifest.from_artifact(
                data_artifact,
                row_count=2,
                partition_values={"market": "cn", "year": "2026", "month": "07"},
            ),
        ),
        created_at=NOW,
        created_by_run_id="run-quality-manifest",
        created_by_stage_id="stage-dataset-build",
        metadata=report.manifest_metadata(report_artifact=report_artifact),
    )

    assert version.metadata["quality_status"] == "warning"
    assert version.metadata["quality_rule_set_version"] == "dq-p2-012.3"
    assert version.metadata["quality_report_artifact_id"] == report_artifact.artifact_id
    assert version.metadata["quality_issue_count_warning"] == "1"
    assert version.metadata["quality_issue_count_quarantine"] == "0"
    assert version.metadata["quality_issue_count_blocking"] == "0"


def test_quality_rule_errors_map_to_problem_details() -> None:
    with pytest.raises(DataQualityRuleError, match="rule_set_version is required") as exc:
        DataQualityEngine(rule_set_version="", rules=(UniquePrimaryKeyRule(),))

    problem = problem_from_exception(exc.value, trace_context=TraceContext(trace_id="trace-quality-err"))
    assert problem.status == 422
    assert problem.code is ApiErrorCode.VALIDATION_ERROR
    assert problem.trace_id == "trace-quality-err"
