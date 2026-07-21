from __future__ import annotations

import json
from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from serenity_alpha_lab.application.api_errors import ApiErrorCode, problem_from_exception
from serenity_alpha_lab.application.tracing import TraceContext
from serenity_alpha_lab.domain.artifacts import ArtifactRetentionTier
from serenity_alpha_lab.domain.instruments import InstrumentId, Market, ProviderSymbolMapping
from serenity_alpha_lab.repositories.local_artifact_store import LocalArtifactStore


NOW = datetime(2026, 7, 21, 10, 0, tzinfo=UTC)


def cn_stock(symbol: str) -> InstrumentId:
    return InstrumentId.parse(symbol)


def make_dataset():
    from serenity_alpha_lab.datasets.instrument_master import (
        IndustryClassification,
        InstrumentListingStatus,
        InstrumentMasterDataset,
        InstrumentMasterRecord,
        ProviderSymbolValidity,
    )

    moutai = cn_stock("600519.XSHG")
    changyou = cn_stock("600087.XSHG")
    return InstrumentMasterDataset.from_records(
        [
            InstrumentMasterRecord(
                instrument_id=moutai,
                name="贵州茅台",
                currency="CNY",
                listing_status=InstrumentListingStatus.ACTIVE,
                listed_on=date(2001, 8, 27),
                delisted_on=None,
                is_st=False,
                board="主板",
                industries=(
                    IndustryClassification(
                        system="SW",
                        version="2021",
                        level1="食品饮料",
                        level2="白酒",
                        valid_from=date(2021, 1, 1),
                    ),
                ),
                provider_mappings=(
                    ProviderSymbolValidity(
                        mapping=ProviderSymbolMapping(
                            provider="akshare",
                            symbol="SH600519",
                            instrument_id=moutai,
                        ),
                        valid_from=date(2001, 8, 27),
                        valid_to=date(2025, 1, 1),
                        source_bronze_artifact_id="art_bronze_akshare_instruments_001",
                    ),
                    ProviderSymbolValidity(
                        mapping=ProviderSymbolMapping(
                            provider="akshare",
                            symbol="600519",
                            instrument_id=moutai,
                        ),
                        valid_from=date(2025, 1, 1),
                        source_bronze_artifact_id="art_bronze_akshare_instruments_002",
                    ),
                    ProviderSymbolValidity(
                        mapping=ProviderSymbolMapping(
                            provider="yahoo",
                            symbol="600519.SS",
                            instrument_id=moutai,
                        ),
                        valid_from=date(2001, 8, 27),
                        source_bronze_artifact_id="art_bronze_yahoo_instruments_001",
                    ),
                ),
                valid_from=date(2001, 8, 27),
                source_bronze_artifact_id="art_bronze_instrument_master_001",
            ),
            InstrumentMasterRecord(
                instrument_id=changyou,
                name="长航油运",
                currency="CNY",
                listing_status=InstrumentListingStatus.ACTIVE,
                listed_on=date(1997, 6, 12),
                delisted_on=None,
                is_st=True,
                board="主板",
                industries=(
                    IndustryClassification(
                        system="SW",
                        version="2021",
                        level1="交通运输",
                        level2="航运港口",
                        valid_from=date(2021, 1, 1),
                    ),
                ),
                provider_mappings=(
                    ProviderSymbolValidity(
                        mapping=ProviderSymbolMapping(
                            provider="akshare",
                            symbol="SH600087",
                            instrument_id=changyou,
                        ),
                        valid_from=date(1997, 6, 12),
                        source_bronze_artifact_id="art_bronze_akshare_instruments_003",
                    ),
                ),
                valid_from=date(1997, 6, 12),
                valid_to=date(2014, 6, 5),
                source_bronze_artifact_id="art_bronze_instrument_master_002",
            ),
            InstrumentMasterRecord(
                instrument_id=changyou,
                name="长航油运",
                currency="CNY",
                listing_status=InstrumentListingStatus.DELISTED,
                listed_on=date(1997, 6, 12),
                delisted_on=date(2014, 6, 5),
                is_st=False,
                board="主板",
                industries=(
                    IndustryClassification(
                        system="SW",
                        version="2021",
                        level1="交通运输",
                        level2="航运港口",
                        valid_from=date(2021, 1, 1),
                    ),
                ),
                provider_mappings=(),
                valid_from=date(2014, 6, 5),
                source_bronze_artifact_id="art_bronze_instrument_master_003",
            ),
        ],
        created_at=NOW,
        trace_id="trace-instrument-master-001",
        run_id="run-instrument-master-001",
        stage_id="stage-instrument-master-build",
    )


def test_instrument_master_publishes_artifact_and_queries_as_of(tmp_path: Path) -> None:
    from serenity_alpha_lab.datasets.instrument_master import (
        INSTRUMENT_MASTER_CONTENT_TYPE,
        INSTRUMENT_MASTER_SCHEMA_NAME,
        INSTRUMENT_MASTER_SCHEMA_VERSION,
        InstrumentListingStatus,
    )

    dataset = make_dataset()
    store = LocalArtifactStore(tmp_path / "artifacts")

    current_moutai = dataset.get(cn_stock("600519.XSHG"), as_of=date(2026, 7, 21))
    delisted_changyou = dataset.get(cn_stock("600087.XSHG"), as_of=date(2015, 1, 1))
    current_mapping = dataset.provider_mapping_as_of(
        cn_stock("600519.XSHG"),
        provider="akshare",
        as_of=date(2026, 7, 21),
    )
    historical_mapping = dataset.provider_mapping_as_of(
        cn_stock("600519.XSHG"),
        provider="akshare",
        as_of=date(2024, 12, 31),
    )

    artifact = dataset.publish(
        store,
        produced_by_run_id="run-instrument-master-001",
        produced_by_stage_id="stage-instrument-master-build",
    )
    second_artifact = dataset.publish(
        store,
        produced_by_run_id="run-instrument-master-001",
        produced_by_stage_id="stage-instrument-master-build",
    )
    payload = json.loads(store.get_bytes(artifact.artifact_id).decode("utf-8"))

    assert current_moutai.name == "贵州茅台"
    assert current_moutai.listing_status is InstrumentListingStatus.ACTIVE
    assert current_moutai.market is Market.CN
    assert current_moutai.exchange.value == "XSHG"
    assert current_moutai.active_industries[0].level1 == "食品饮料"
    assert current_moutai.source_bronze_artifact_id == "art_bronze_instrument_master_001"

    assert delisted_changyou.listing_status is InstrumentListingStatus.DELISTED
    assert delisted_changyou.delisted_on == date(2014, 6, 5)
    assert [record.instrument_id.canonical for record in dataset.query_as_of(date(2013, 1, 1))] == [
        "600087.XSHG",
        "600519.XSHG",
    ]

    assert current_mapping.symbol == "600519"
    assert current_mapping.source_bronze_artifact_id == "art_bronze_akshare_instruments_002"
    assert historical_mapping.symbol == "SH600519"
    assert historical_mapping.valid_to == date(2025, 1, 1)

    assert artifact.artifact_id == second_artifact.artifact_id
    assert artifact.sha256 == second_artifact.sha256
    assert artifact.schema_name == INSTRUMENT_MASTER_SCHEMA_NAME
    assert artifact.schema_version == INSTRUMENT_MASTER_SCHEMA_VERSION
    assert artifact.content_type == INSTRUMENT_MASTER_CONTENT_TYPE
    assert artifact.retention_tier is ArtifactRetentionTier.STANDARD
    assert artifact.produced_by_run_id == "run-instrument-master-001"
    assert artifact.produced_by_stage_id == "stage-instrument-master-build"

    assert payload["schema_name"] == INSTRUMENT_MASTER_SCHEMA_NAME
    assert payload["schema_version"] == INSTRUMENT_MASTER_SCHEMA_VERSION
    assert payload["trace_id"] == "trace-instrument-master-001"
    assert payload["run_id"] == "run-instrument-master-001"
    assert payload["stage_id"] == "stage-instrument-master-build"
    assert payload["records"][0]["instrument_id"] == "600087.XSHG"
    assert payload["records"][0]["source_bronze_artifact_id"] == "art_bronze_instrument_master_002"
    moutai_payload = next(record for record in payload["records"] if record["instrument_id"] == "600519.XSHG")
    assert moutai_payload["provider_mappings"][0]["source_bronze_artifact_id"].startswith("art_bronze_")


def test_instrument_master_rejects_duplicate_keys_and_overlapping_validity() -> None:
    from serenity_alpha_lab.datasets.instrument_master import (
        InstrumentListingStatus,
        InstrumentMasterDataset,
        InstrumentMasterDatasetError,
        InstrumentMasterRecord,
    )

    instrument = cn_stock("600519.XSHG")
    first = InstrumentMasterRecord(
        instrument_id=instrument,
        name="贵州茅台",
        currency="CNY",
        listing_status=InstrumentListingStatus.ACTIVE,
        listed_on=date(2001, 8, 27),
        delisted_on=None,
        is_st=False,
        board="主板",
        industries=(),
        provider_mappings=(),
        valid_from=date(2020, 1, 1),
        valid_to=date(2022, 1, 1),
        source_bronze_artifact_id="art_bronze_instrument_master_001",
    )
    duplicate_key = InstrumentMasterRecord(
        instrument_id=instrument,
        name="贵州茅台",
        currency="CNY",
        listing_status=InstrumentListingStatus.ACTIVE,
        listed_on=date(2001, 8, 27),
        delisted_on=None,
        is_st=False,
        board="主板",
        industries=(),
        provider_mappings=(),
        valid_from=date(2020, 1, 1),
        source_bronze_artifact_id="art_bronze_instrument_master_002",
    )
    overlapping = InstrumentMasterRecord(
        instrument_id=instrument,
        name="贵州茅台",
        currency="CNY",
        listing_status=InstrumentListingStatus.ACTIVE,
        listed_on=date(2001, 8, 27),
        delisted_on=None,
        is_st=False,
        board="主板",
        industries=(),
        provider_mappings=(),
        valid_from=date(2021, 1, 1),
        source_bronze_artifact_id="art_bronze_instrument_master_003",
    )

    with pytest.raises(InstrumentMasterDatasetError, match="Duplicate instrument master key"):
        InstrumentMasterDataset.from_records([first, duplicate_key], created_at=NOW)

    with pytest.raises(InstrumentMasterDatasetError, match="overlapping instrument validity"):
        InstrumentMasterDataset.from_records([first, overlapping], created_at=NOW)


def test_instrument_master_rejects_invalid_provider_mapping_windows_and_lineage() -> None:
    from serenity_alpha_lab.datasets.instrument_master import (
        InstrumentListingStatus,
        InstrumentMasterDataset,
        InstrumentMasterDatasetError,
        InstrumentMasterRecord,
        ProviderSymbolValidity,
    )

    instrument = cn_stock("600519.XSHG")
    other = cn_stock("000001.XSHE")
    overlapping_provider_windows = (
        ProviderSymbolValidity(
            mapping=ProviderSymbolMapping(provider="akshare", symbol="SH600519", instrument_id=instrument),
            valid_from=date(2020, 1, 1),
            valid_to=date(2022, 1, 1),
            source_bronze_artifact_id="art_bronze_provider_mapping_001",
        ),
        ProviderSymbolValidity(
            mapping=ProviderSymbolMapping(provider="akshare", symbol="600519", instrument_id=instrument),
            valid_from=date(2021, 1, 1),
            source_bronze_artifact_id="art_bronze_provider_mapping_002",
        ),
    )

    with pytest.raises(InstrumentMasterDatasetError, match="source_bronze_artifact_id is required") as exc:
        InstrumentMasterRecord(
            instrument_id=instrument,
            name="贵州茅台",
            currency="CNY",
            listing_status=InstrumentListingStatus.ACTIVE,
            listed_on=date(2001, 8, 27),
            delisted_on=None,
            is_st=False,
            board="主板",
            industries=(),
            provider_mappings=(),
            valid_from=date(2020, 1, 1),
            source_bronze_artifact_id="",
        )

    problem = problem_from_exception(exc.value, trace_context=TraceContext(trace_id="trace-dataset-err"))
    assert problem.status == 422
    assert problem.code is ApiErrorCode.VALIDATION_ERROR
    assert problem.trace_id == "trace-dataset-err"

    with pytest.raises(InstrumentMasterDatasetError, match="provider mapping instrument_id"):
        InstrumentMasterRecord(
            instrument_id=instrument,
            name="贵州茅台",
            currency="CNY",
            listing_status=InstrumentListingStatus.ACTIVE,
            listed_on=date(2001, 8, 27),
            delisted_on=None,
            is_st=False,
            board="主板",
            industries=(),
            provider_mappings=(
                ProviderSymbolValidity(
                    mapping=ProviderSymbolMapping(provider="akshare", symbol="SZ000001", instrument_id=other),
                    valid_from=date(2020, 1, 1),
                    source_bronze_artifact_id="art_bronze_provider_mapping_003",
                ),
            ),
            valid_from=date(2020, 1, 1),
            source_bronze_artifact_id="art_bronze_instrument_master_001",
        )

    with pytest.raises(InstrumentMasterDatasetError, match="overlapping provider mapping validity"):
        InstrumentMasterRecord(
            instrument_id=instrument,
            name="贵州茅台",
            currency="CNY",
            listing_status=InstrumentListingStatus.ACTIVE,
            listed_on=date(2001, 8, 27),
            delisted_on=None,
            is_st=False,
            board="主板",
            industries=(),
            provider_mappings=overlapping_provider_windows,
            valid_from=date(2020, 1, 1),
            source_bronze_artifact_id="art_bronze_instrument_master_001",
        )
