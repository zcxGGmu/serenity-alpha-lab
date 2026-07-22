from __future__ import annotations

import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from serenity_alpha_lab.application.api_errors import ApiErrorCode, problem_from_exception
from serenity_alpha_lab.application.tracing import TraceContext
from serenity_alpha_lab.datasets.fundamentals import (
    FUNDAMENTALS_CONTENT_TYPE,
    FUNDAMENTALS_FIELD_SCHEMA,
    FUNDAMENTALS_PARTITION_KEYS,
    FUNDAMENTALS_SCHEMA_NAME,
    FUNDAMENTALS_SCHEMA_VERSION,
    FundamentalPeriodType,
    FundamentalQueryPurpose,
    FundamentalsDataset,
    FundamentalsDatasetError,
    TemporalConfidence,
)
from serenity_alpha_lab.datasets.instrument_master import (
    InstrumentListingStatus,
    InstrumentMasterDataset,
    InstrumentMasterRecord,
)
from serenity_alpha_lab.domain.artifacts import ArtifactRetentionTier
from serenity_alpha_lab.domain.instruments import InstrumentId
from serenity_alpha_lab.domain.providers import DataBatch, Provenance, ProviderCapability
from serenity_alpha_lab.repositories.local_artifact_store import LocalArtifactStore


SHANGHAI = ZoneInfo("Asia/Shanghai")
NOW = datetime(2026, 7, 22, 10, 0, tzinfo=UTC)
FETCHED_AT = datetime(2026, 5, 10, 2, 30, tzinfo=UTC)
SOURCE_TIMESTAMP = datetime(2026, 5, 10, 1, 30, tzinfo=UTC)
FRESH_UNTIL = datetime(2026, 5, 10, 3, 30, tzinfo=UTC)
RAW_SHA256 = "A1" * 32
DECISION_20260501 = datetime(2026, 5, 1, 9, 30, tzinfo=SHANGHAI)
DECISION_20260515 = datetime(2026, 5, 15, 9, 30, tzinfo=SHANGHAI)


def cn_stock(symbol: str) -> InstrumentId:
    return InstrumentId.parse(symbol)


def cn_dt(day: date, hour: int, minute: int = 0) -> datetime:
    return datetime(day.year, day.month, day.day, hour, minute, tzinfo=SHANGHAI)


def make_instrument_master() -> InstrumentMasterDataset:
    return InstrumentMasterDataset.from_records(
        [
            InstrumentMasterRecord(
                instrument_id=cn_stock("600519.XSHG"),
                name="贵州茅台",
                currency="CNY",
                listing_status=InstrumentListingStatus.ACTIVE,
                listed_on=date(2001, 8, 27),
                delisted_on=None,
                is_st=False,
                board="主板",
                industries=(),
                provider_mappings=(),
                valid_from=date(2001, 8, 27),
                source_bronze_artifact_id="art_bronze_instrument_master_fund_001",
            )
        ],
        created_at=NOW,
        trace_id="trace-master-fundamentals",
        run_id="run-master-fundamentals",
        stage_id="stage-master-fundamentals",
    )


def make_provider_batch(records: list[dict[str, object]] | None = None) -> DataBatch[dict[str, object]]:
    provenance = Provenance(
        provider_id="dsa:FundamentalFixture",
        provider_version="fixture-1.0",
        operation=ProviderCapability.FUNDAMENTALS,
        request_parameters={
            "instrument_ids": ["600519.XSHG"],
            "as_of": DECISION_20260515.isoformat(),
        },
        requested_at=FETCHED_AT - timedelta(minutes=10),
        fetched_at=FETCHED_AT,
        raw_response_sha256=RAW_SHA256,
        field_lineage={
            "instrument_id": "fixture.instrument_id",
            "period_end": "fixture.period_end",
            "item": "fixture.item",
            "value": "fixture.value",
            "announced_at": "fixture.announced_at",
            "available_at": "fixture.available_at",
            "revision": "fixture.revision",
        },
        source_timestamp=SOURCE_TIMESTAMP,
        trace_id="trace-provider-fundamentals",
        run_id="run-provider-fundamentals",
        stage_id="stage-provider-fundamentals",
    )
    return DataBatch(
        records=records if records is not None else provider_rows(),
        schema_name="market.fundamentals.dsa_compatibility",
        schema_version="1.0.0",
        provenance=provenance,
        fresh_until=FRESH_UNTIL,
    )


def provider_rows() -> list[dict[str, object]]:
    return [
        {
            "instrument_id": "600519.XSHG",
            "period_end": "2025-12-31",
            "period_type": "annual",
            "item": "roe",
            "value": 0.282,
            "unit": "ratio",
            "revision": 1,
            "fiscal_year": 2025,
            "announced_at": cn_dt(date(2026, 4, 28), 20, 0),
            "available_at": cn_dt(date(2026, 4, 29), 9, 30),
            "ingested_at": cn_dt(date(2026, 4, 29), 10, 5),
            "currency": "CNY",
            "accounting_standard": "CAS",
            "source": "FundamentalFixture",
            "temporal_confidence": "exact",
        },
        {
            "instrument_id": "600519.XSHG",
            "period_end": "2025-12-31",
            "period_type": "annual",
            "item": "roe",
            "value": 0.279,
            "unit": "ratio",
            "revision": 2,
            "fiscal_year": 2025,
            "announced_at": cn_dt(date(2026, 5, 9), 20, 0),
            "available_at": cn_dt(date(2026, 5, 10), 9, 30),
            "ingested_at": cn_dt(date(2026, 5, 10), 10, 0),
            "currency": "CNY",
            "accounting_standard": "CAS",
            "source": "FundamentalFixture",
            "temporal_confidence": "exact",
        },
        {
            "instrument_id": "600519.XSHG",
            "period_end": "2026-03-31",
            "period_type": "quarterly",
            "item": "roe",
            "value": 0.074,
            "unit": "ratio",
            "revision": 1,
            "fiscal_year": 2026,
            "fiscal_quarter": 1,
            "announced_at": cn_dt(date(2026, 6, 1), 20, 0),
            "available_at": cn_dt(date(2026, 6, 2), 9, 30),
            "ingested_at": cn_dt(date(2026, 6, 2), 10, 0),
            "currency": "CNY",
            "accounting_standard": "CAS",
            "source": "FundamentalFixture",
            "temporal_confidence": "exact",
        },
        {
            "instrument_id": "600519.XSHG",
            "period_end": "2026-01-05",
            "period_type": "snapshot",
            "item": "pe_ttm",
            "value": 24.5,
            "unit": "multiple",
            "revision": 1,
            "available_at": cn_dt(date(2026, 1, 5), 9, 30),
            "ingested_at": cn_dt(date(2026, 1, 5), 9, 30),
            "source": "LegacyFundamentalSnapshot",
            "temporal_confidence": "unknown",
        },
    ]


def make_dataset(records: list[dict[str, object]] | None = None) -> FundamentalsDataset:
    return FundamentalsDataset.from_provider_batch(
        make_provider_batch(records),
        instrument_master=make_instrument_master(),
        source_bronze_artifact_id="art_bronze_dsa_fundamentals_001",
        created_at=NOW,
        trace_id="trace-fundamentals-001",
        run_id="run-fundamentals-001",
        stage_id="stage-fundamentals-build",
    )


def test_fundamentals_publish_artifact_and_enforce_latest_as_of_pit_query(tmp_path: Path) -> None:
    dataset = make_dataset()
    store = LocalArtifactStore(tmp_path / "artifacts")

    first_revision = dataset.latest_as_of(
        cn_stock("600519.XSHG"),
        item="roe",
        decision_time=DECISION_20260501,
    )
    second_revision = dataset.latest_as_of(
        "600519.XSHG",
        item="roe",
        decision_time=DECISION_20260515,
    )
    history = dataset.history_for_item(
        cn_stock("600519.XSHG"),
        item="roe",
        start_period=date(2025, 1, 1),
        end_period=date(2026, 12, 31),
        decision_time=DECISION_20260515,
    )
    artifact = dataset.publish(
        store,
        produced_by_run_id="run-fundamentals-001",
        produced_by_stage_id="stage-fundamentals-build",
    )
    second_artifact = dataset.publish(
        store,
        produced_by_run_id="run-fundamentals-001",
        produced_by_stage_id="stage-fundamentals-build",
    )
    payload = json.loads(store.get_bytes(artifact.artifact_id).decode("utf-8"))
    roe_payload = next(record for record in payload["records"] if record["item"] == "roe" and record["revision"] == 2)

    assert FUNDAMENTALS_PARTITION_KEYS == ("market", "period_year")
    assert FUNDAMENTALS_FIELD_SCHEMA["available_at"] == "timestamp[us, tz=UTC]"
    assert FUNDAMENTALS_FIELD_SCHEMA["revision"] == "int64"
    assert FUNDAMENTALS_FIELD_SCHEMA["temporal_confidence"] == "utf8"

    assert first_revision.period_end == date(2025, 12, 31)
    assert first_revision.period_type is FundamentalPeriodType.ANNUAL
    assert first_revision.value == 0.282
    assert first_revision.revision == 1
    assert first_revision.available_at == cn_dt(date(2026, 4, 29), 9, 30)
    assert first_revision.temporal_confidence is TemporalConfidence.EXACT

    assert second_revision.period_end == date(2025, 12, 31)
    assert second_revision.value == 0.279
    assert second_revision.revision == 2
    assert [record.revision for record in history] == [1, 2]
    assert dataset.latest_as_of(cn_stock("600519.XSHG"), item="roe", decision_time=DECISION_20260515).period_end == date(
        2025,
        12,
        31,
    )
    assert all(record.available_at <= DECISION_20260515 for record in dataset.records_for_instrument(
        cn_stock("600519.XSHG"),
        decision_time=DECISION_20260515,
    ))

    assert artifact.artifact_id == second_artifact.artifact_id
    assert artifact.schema_name == FUNDAMENTALS_SCHEMA_NAME
    assert artifact.schema_version == FUNDAMENTALS_SCHEMA_VERSION
    assert artifact.content_type == FUNDAMENTALS_CONTENT_TYPE
    assert artifact.retention_tier is ArtifactRetentionTier.STANDARD
    assert payload["schema_name"] == FUNDAMENTALS_SCHEMA_NAME
    assert payload["schema_version"] == FUNDAMENTALS_SCHEMA_VERSION
    assert payload["record_count"] == 4
    assert payload["trace_id"] == "trace-fundamentals-001"
    assert payload["run_id"] == "run-fundamentals-001"
    assert payload["stage_id"] == "stage-fundamentals-build"
    assert payload["partition_keys"] == ["market", "period_year"]
    assert payload["provider_ids"] == ["dsa:FundamentalFixture"]
    assert payload["source_bronze_artifact_ids"] == ["art_bronze_dsa_fundamentals_001"]
    assert roe_payload["announced_at"] == cn_dt(date(2026, 5, 9), 20, 0).isoformat()
    assert roe_payload["available_at"] == cn_dt(date(2026, 5, 10), 9, 30).isoformat()
    assert roe_payload["ingested_at"] == cn_dt(date(2026, 5, 10), 10, 0).isoformat()
    assert roe_payload["provider_raw_response_sha256"] == RAW_SHA256.lower()
    assert roe_payload["field_lineage"]["value"] == "fixture.value"
    assert roe_payload["partition"] == {"market": "cn", "period_year": "2025"}


def test_fundamentals_unknown_temporal_confidence_is_research_only() -> None:
    dataset = make_dataset()

    display_record = dataset.latest_as_of(
        cn_stock("600519.XSHG"),
        item="pe_ttm",
        decision_time=DECISION_20260501,
        purpose=FundamentalQueryPurpose.RESEARCH_DISPLAY,
    )

    assert display_record.announced_at is None
    assert display_record.temporal_confidence is TemporalConfidence.UNKNOWN
    assert display_record.is_formal_backtest_eligible is False

    with pytest.raises(FundamentalsDatasetError, match="unknown temporal confidence"):
        dataset.latest_as_of(
            cn_stock("600519.XSHG"),
            item="pe_ttm",
            decision_time=DECISION_20260501,
            purpose=FundamentalQueryPurpose.FORMAL_BACKTEST,
        )


def test_fundamentals_reject_invalid_timing_keys_and_problem_details_mapping() -> None:
    duplicate = [provider_rows()[0], provider_rows()[0]]
    available_before_announcement = [
        {
            **provider_rows()[0],
            "available_at": cn_dt(date(2026, 4, 28), 19, 0),
        }
    ]
    naive_ingested_at = [
        {
            **provider_rows()[0],
            "ingested_at": datetime(2026, 4, 29, 10, 5),
        }
    ]
    missing_instrument = [
        {
            **provider_rows()[0],
            "instrument_id": "000002.XSHE",
        }
    ]
    exact_without_announced = [
        {
            **provider_rows()[0],
            "announced_at": None,
            "temporal_confidence": "exact",
        }
    ]

    with pytest.raises(FundamentalsDatasetError, match="Duplicate fundamental key"):
        make_dataset(duplicate)

    with pytest.raises(FundamentalsDatasetError, match="available_at cannot be before announced_at"):
        make_dataset(available_before_announcement)

    with pytest.raises(FundamentalsDatasetError, match="ingested_at must be timezone-aware"):
        make_dataset(naive_ingested_at)

    with pytest.raises(FundamentalsDatasetError, match="instrument_id must exist"):
        make_dataset(missing_instrument)

    with pytest.raises(FundamentalsDatasetError, match="announced_at is required") as exc:
        make_dataset(exact_without_announced)

    problem = problem_from_exception(exc.value, trace_context=TraceContext(trace_id="trace-fundamentals-err"))
    assert problem.status == 422
    assert problem.code is ApiErrorCode.VALIDATION_ERROR
    assert problem.trace_id == "trace-fundamentals-err"

    with pytest.raises(FundamentalsDatasetError, match="source_bronze_artifact_id is required"):
        FundamentalsDataset.from_provider_batch(
            make_provider_batch(),
            instrument_master=make_instrument_master(),
            source_bronze_artifact_id="",
            created_at=NOW,
        )


def test_fundamentals_merge_incremental_replaces_matching_primary_keys() -> None:
    initial = make_dataset([provider_rows()[0]])
    incremental = make_dataset(
        [
            {
                **provider_rows()[0],
                "value": 0.281,
            },
            provider_rows()[1],
        ]
    )

    merged = initial.merge_incremental(
        incremental,
        created_at=NOW + timedelta(minutes=1),
        run_id="run-fundamentals-merge",
        stage_id="stage-fundamentals-merge",
    )

    assert len(merged.records) == 2
    assert merged.created_at == NOW + timedelta(minutes=1)
    assert merged.run_id == "run-fundamentals-merge"
    assert merged.stage_id == "stage-fundamentals-merge"
    assert (
        merged.latest_as_of(cn_stock("600519.XSHG"), item="roe", decision_time=DECISION_20260501).value
        == 0.281
    )
    assert (
        merged.latest_as_of(cn_stock("600519.XSHG"), item="roe", decision_time=DECISION_20260515).revision
        == 2
    )
