from __future__ import annotations

import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from serenity_alpha_lab.application.api_errors import ApiErrorCode, problem_from_exception
from serenity_alpha_lab.application.tracing import TraceContext
from serenity_alpha_lab.datasets.instrument_master import (
    InstrumentListingStatus,
    InstrumentMasterDataset,
    InstrumentMasterRecord,
)
from serenity_alpha_lab.datasets.raw_daily_bars import (
    RAW_DAILY_BARS_CONTENT_TYPE,
    RAW_DAILY_BARS_FIELD_SCHEMA,
    RAW_DAILY_BARS_PARTITION_KEYS,
    RAW_DAILY_BARS_SCHEMA_NAME,
    RAW_DAILY_BARS_SCHEMA_VERSION,
    RawDailyBarsDataset,
    RawDailyBarsDatasetError,
)
from serenity_alpha_lab.datasets.trading_calendar import (
    MarketSession,
    TradingCalendarDataset,
    TradingSessionStatus,
)
from serenity_alpha_lab.domain.artifacts import ArtifactRetentionTier
from serenity_alpha_lab.domain.instruments import InstrumentId, Market
from serenity_alpha_lab.domain.providers import DataBatch, Provenance, ProviderCapability
from serenity_alpha_lab.repositories.local_artifact_store import LocalArtifactStore


NOW = datetime(2026, 7, 21, 10, 0, tzinfo=UTC)
FETCHED_AT = datetime(2026, 7, 21, 9, 5, tzinfo=UTC)
SOURCE_TIMESTAMP = datetime(2026, 7, 21, 8, 0, tzinfo=UTC)
FRESH_UNTIL = datetime(2026, 7, 21, 10, 5, tzinfo=UTC)
RAW_SHA256 = "CD" * 32
SHANGHAI = ZoneInfo("Asia/Shanghai")


def cn_stock(symbol: str) -> InstrumentId:
    return InstrumentId.parse(symbol)


def cn_dt(day: date, hour: int, minute: int = 0) -> datetime:
    return datetime(day.year, day.month, day.day, hour, minute, tzinfo=SHANGHAI)


def make_instrument_master() -> InstrumentMasterDataset:
    moutai = cn_stock("600519.XSHG")
    pingan = cn_stock("000001.XSHE")
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
                industries=(),
                provider_mappings=(),
                valid_from=date(2001, 8, 27),
                source_bronze_artifact_id="art_bronze_instrument_master_001",
            ),
            InstrumentMasterRecord(
                instrument_id=pingan,
                name="平安银行",
                currency="CNY",
                listing_status=InstrumentListingStatus.ACTIVE,
                listed_on=date(1991, 4, 3),
                delisted_on=None,
                is_st=False,
                board="主板",
                industries=(),
                provider_mappings=(),
                valid_from=date(1991, 4, 3),
                source_bronze_artifact_id="art_bronze_instrument_master_002",
            ),
        ],
        created_at=NOW,
        trace_id="trace-master-raw-bars",
        run_id="run-master-raw-bars",
        stage_id="stage-master-raw-bars",
    )


def make_calendar() -> TradingCalendarDataset:
    return TradingCalendarDataset.from_sessions(
        [
            MarketSession(
                market=Market.CN,
                trade_date=date(2026, 7, 17),
                timezone="Asia/Shanghai",
                status=TradingSessionStatus.OPEN,
                open_at=cn_dt(date(2026, 7, 17), 9, 30),
                close_at=cn_dt(date(2026, 7, 17), 15, 0),
                break_start_at=cn_dt(date(2026, 7, 17), 11, 30),
                break_end_at=cn_dt(date(2026, 7, 17), 13, 0),
                source_bronze_artifact_id="art_bronze_calendar_20260717",
            ),
            MarketSession(
                market=Market.CN,
                trade_date=date(2026, 7, 20),
                timezone="Asia/Shanghai",
                status=TradingSessionStatus.OPEN,
                open_at=cn_dt(date(2026, 7, 20), 9, 30),
                close_at=cn_dt(date(2026, 7, 20), 15, 0),
                break_start_at=cn_dt(date(2026, 7, 20), 11, 30),
                break_end_at=cn_dt(date(2026, 7, 20), 13, 0),
                source_bronze_artifact_id="art_bronze_calendar_20260720",
            ),
            MarketSession(
                market=Market.CN,
                trade_date=date(2026, 7, 21),
                timezone="Asia/Shanghai",
                status=TradingSessionStatus.OPEN,
                open_at=cn_dt(date(2026, 7, 21), 9, 30),
                close_at=cn_dt(date(2026, 7, 21), 15, 0),
                break_start_at=cn_dt(date(2026, 7, 21), 11, 30),
                break_end_at=cn_dt(date(2026, 7, 21), 13, 0),
                source_bronze_artifact_id="art_bronze_calendar_20260721",
            ),
            MarketSession(
                market=Market.CN,
                trade_date=date(2026, 7, 22),
                timezone="Asia/Shanghai",
                status=TradingSessionStatus.CLOSED,
                source_bronze_artifact_id="art_bronze_calendar_20260722_closed",
            ),
        ],
        created_at=NOW,
        trace_id="trace-calendar-raw-bars",
        run_id="run-calendar-raw-bars",
        stage_id="stage-calendar-raw-bars",
    )


def make_provider_batch(records: list[dict[str, object]] | None = None) -> DataBatch[dict[str, object]]:
    rows = records if records is not None else _provider_rows()
    provenance = Provenance(
        provider_id="dsa:EfinanceFetcher",
        provider_version="fixture-1.0",
        operation=ProviderCapability.DAILY_BARS,
        request_parameters={
            "instrument_ids": ["600519.XSHG", "000001.XSHE"],
            "start": "2026-07-17",
            "end": "2026-07-21",
        },
        requested_at=NOW - timedelta(minutes=10),
        fetched_at=FETCHED_AT,
        raw_response_sha256=RAW_SHA256,
        field_lineage={
            "instrument_id": "dsa:EfinanceFetcher.instrument_id",
            "date": "dsa:EfinanceFetcher.date",
            "open": "dsa:EfinanceFetcher.open",
            "high": "dsa:EfinanceFetcher.high",
            "low": "dsa:EfinanceFetcher.low",
            "close": "dsa:EfinanceFetcher.close",
            "volume": "dsa:EfinanceFetcher.volume",
            "amount": "dsa:EfinanceFetcher.amount",
            "source": "dsa:EfinanceFetcher.source",
        },
        source_timestamp=SOURCE_TIMESTAMP,
        trace_id="trace-provider-raw-bars",
        run_id="run-provider-raw-bars",
        stage_id="stage-provider-raw-bars",
    )
    return DataBatch(
        records=rows,
        schema_name="market.daily_bars.dsa_compatibility",
        schema_version="1.0.0",
        provenance=provenance,
        fresh_until=FRESH_UNTIL,
    )


def _provider_rows() -> list[dict[str, object]]:
    return [
        {
            "instrument_id": "600519.XSHG",
            "date": "2026-07-17",
            "open": 1680.0,
            "high": 1699.0,
            "low": 1675.0,
            "close": 1690.0,
            "volume": 100000.0,
            "amount": 168900000.0,
            "source": "EfinanceFetcher",
            "currency": "cny",
        },
        {
            "instrument_id": "600519.XSHG",
            "date": "2026-07-20",
            "open": 1691.0,
            "high": 1702.0,
            "low": 1688.0,
            "close": 1698.0,
            "volume": 120000.0,
            "amount": 203760000.0,
            "source": "EfinanceFetcher",
            "currency": "CNY",
        },
        {
            "instrument_id": "000001.XSHE",
            "date": "2026-07-20",
            "open": 12.10,
            "high": 12.30,
            "low": 12.00,
            "close": 12.20,
            "volume": 800000.0,
            "amount": 9760000.0,
            "source": "EfinanceFetcher",
            "currency": "CNY",
        },
    ]


def make_dataset(records: list[dict[str, object]] | None = None) -> RawDailyBarsDataset:
    return RawDailyBarsDataset.from_provider_batch(
        make_provider_batch(records),
        instrument_master=make_instrument_master(),
        trading_calendar=make_calendar(),
        source_bronze_artifact_id="art_bronze_dsa_daily_bars_001",
        created_at=NOW,
        trace_id="trace-raw-bars-001",
        run_id="run-raw-bars-001",
        stage_id="stage-raw-bars-build",
    )


def test_raw_daily_bars_publish_artifact_and_query_unadjusted_records(tmp_path: Path) -> None:
    dataset = make_dataset()
    store = LocalArtifactStore(tmp_path / "artifacts")

    moutai_20260720 = dataset.get(cn_stock("600519.XSHG"), date(2026, 7, 20), provider_id="dsa:EfinanceFetcher")
    artifact = dataset.publish(
        store,
        produced_by_run_id="run-raw-bars-001",
        produced_by_stage_id="stage-raw-bars-build",
    )
    second_artifact = dataset.publish(
        store,
        produced_by_run_id="run-raw-bars-001",
        produced_by_stage_id="stage-raw-bars-build",
    )
    payload = json.loads(store.get_bytes(artifact.artifact_id).decode("utf-8"))

    assert RAW_DAILY_BARS_PARTITION_KEYS == ("market", "year", "month")
    assert RAW_DAILY_BARS_FIELD_SCHEMA["amount"] == "float64"
    assert RAW_DAILY_BARS_FIELD_SCHEMA["adjustment"] == "utf8"

    assert moutai_20260720.instrument_id == cn_stock("600519.XSHG")
    assert moutai_20260720.trade_date == date(2026, 7, 20)
    assert moutai_20260720.adjustment == "unadjusted"
    assert moutai_20260720.open == 1691.0
    assert moutai_20260720.high == 1702.0
    assert moutai_20260720.low == 1688.0
    assert moutai_20260720.close == 1698.0
    assert moutai_20260720.volume == 120000.0
    assert moutai_20260720.amount == 203760000.0
    assert moutai_20260720.currency == "CNY"
    assert moutai_20260720.provider_id == "dsa:EfinanceFetcher"
    assert moutai_20260720.provider_source == "EfinanceFetcher"
    assert moutai_20260720.provider_raw_response_sha256 == RAW_SHA256.lower()
    assert moutai_20260720.provider_source_timestamp == SOURCE_TIMESTAMP
    assert moutai_20260720.field_lineage["close"] == "dsa:EfinanceFetcher.close"
    assert moutai_20260720.source_bronze_artifact_id == "art_bronze_dsa_daily_bars_001"
    assert moutai_20260720.partition_values == {"market": "cn", "year": "2026", "month": "07"}

    assert [bar.trade_date for bar in dataset.bars_for_instrument(cn_stock("600519.XSHG"), date(2026, 7, 1), date(2026, 7, 31))] == [
        date(2026, 7, 17),
        date(2026, 7, 20),
    ]
    assert [bar.instrument_id.canonical for bar in dataset.bars_for_market(Market.CN, date(2026, 7, 20))] == [
        "000001.XSHE",
        "600519.XSHG",
    ]
    assert [bar.trade_date for bar in dataset.bars_for_provider("dsa:EfinanceFetcher", date(2026, 7, 17), date(2026, 7, 20))] == [
        date(2026, 7, 17),
        date(2026, 7, 20),
        date(2026, 7, 20),
    ]

    assert artifact.artifact_id == second_artifact.artifact_id
    assert artifact.sha256 == second_artifact.sha256
    assert artifact.schema_name == RAW_DAILY_BARS_SCHEMA_NAME
    assert artifact.schema_version == RAW_DAILY_BARS_SCHEMA_VERSION
    assert artifact.content_type == RAW_DAILY_BARS_CONTENT_TYPE
    assert artifact.retention_tier is ArtifactRetentionTier.STANDARD
    assert artifact.produced_by_run_id == "run-raw-bars-001"
    assert artifact.produced_by_stage_id == "stage-raw-bars-build"

    assert payload["schema_name"] == RAW_DAILY_BARS_SCHEMA_NAME
    assert payload["schema_version"] == RAW_DAILY_BARS_SCHEMA_VERSION
    assert payload["record_count"] == 3
    assert payload["trace_id"] == "trace-raw-bars-001"
    assert payload["run_id"] == "run-raw-bars-001"
    assert payload["stage_id"] == "stage-raw-bars-build"
    assert payload["partition_keys"] == ["market", "year", "month"]
    assert payload["field_schema"]["provider_source_timestamp"] == "timestamp[us, tz=UTC]"
    assert payload["source_bronze_artifact_ids"] == ["art_bronze_dsa_daily_bars_001"]
    assert payload["provider_ids"] == ["dsa:EfinanceFetcher"]
    assert payload["records"][0]["instrument_id"] == "000001.XSHE"
    assert payload["records"][0]["trade_date"] == "2026-07-20"
    assert payload["records"][0]["adjustment"] == "unadjusted"
    assert payload["records"][0]["partition"] == {"market": "cn", "month": "07", "year": "2026"}


def test_raw_daily_bars_reject_invalid_keys_prices_calendar_and_lineage() -> None:
    duplicate = [_provider_rows()[0], _provider_rows()[0]]
    bad_ohlc = [{**_provider_rows()[0], "low": 1700.0}]
    negative_amount = [{**_provider_rows()[0], "amount": -1.0}]
    closed_day = [{**_provider_rows()[0], "date": "2026-07-22"}]
    missing_instrument = [{**_provider_rows()[0], "instrument_id": "000002.XSHE"}]
    missing_amount = [{key: value for key, value in _provider_rows()[0].items() if key != "amount"}]

    with pytest.raises(RawDailyBarsDatasetError, match="Duplicate raw daily bar key"):
        make_dataset(duplicate)

    with pytest.raises(RawDailyBarsDatasetError, match="OHLC relationship"):
        make_dataset(bad_ohlc)

    with pytest.raises(RawDailyBarsDatasetError, match="amount cannot be negative"):
        make_dataset(negative_amount)

    with pytest.raises(RawDailyBarsDatasetError, match="trade_date must be a trading day"):
        make_dataset(closed_day)

    with pytest.raises(RawDailyBarsDatasetError, match="instrument_id must exist"):
        make_dataset(missing_instrument)

    with pytest.raises(RawDailyBarsDatasetError, match="amount is required") as exc:
        make_dataset(missing_amount)

    problem = problem_from_exception(exc.value, trace_context=TraceContext(trace_id="trace-raw-bars-err"))
    assert problem.status == 422
    assert problem.code is ApiErrorCode.VALIDATION_ERROR
    assert problem.trace_id == "trace-raw-bars-err"

    with pytest.raises(RawDailyBarsDatasetError, match="source_bronze_artifact_id is required"):
        RawDailyBarsDataset.from_provider_batch(
            make_provider_batch(),
            instrument_master=make_instrument_master(),
            trading_calendar=make_calendar(),
            source_bronze_artifact_id="",
            created_at=NOW,
        )


def test_raw_daily_bars_merge_incremental_replaces_matching_primary_keys() -> None:
    initial = make_dataset([_provider_rows()[0]])
    updated_rows = [
        {
            **_provider_rows()[0],
            "close": 1695.0,
            "amount": 169500000.0,
        },
        {
            **_provider_rows()[1],
            "date": "2026-07-21",
            "close": 1700.0,
            "amount": 204000000.0,
        },
    ]
    incremental = make_dataset(updated_rows)

    merged = initial.merge_incremental(
        incremental,
        created_at=NOW + timedelta(minutes=1),
        run_id="run-raw-bars-merge",
        stage_id="stage-raw-bars-merge",
    )

    assert len(merged.records) == 2
    assert merged.created_at == NOW + timedelta(minutes=1)
    assert merged.run_id == "run-raw-bars-merge"
    assert merged.stage_id == "stage-raw-bars-merge"
    assert merged.get(cn_stock("600519.XSHG"), date(2026, 7, 17), provider_id="dsa:EfinanceFetcher").close == 1695.0
    assert merged.get(cn_stock("600519.XSHG"), date(2026, 7, 21), provider_id="dsa:EfinanceFetcher").close == 1700.0
