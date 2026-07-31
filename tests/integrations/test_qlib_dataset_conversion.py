from __future__ import annotations

import ast
import json
from datetime import UTC, date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from serenity_alpha_lab.datasets.catalog import DatasetFileManifest, DatasetVersionManifest
from serenity_alpha_lab.datasets.corporate_actions import (
    ADJUSTED_DAILY_BARS_CONTENT_TYPE,
    ADJUSTED_DAILY_BARS_SCHEMA_NAME,
    ADJUSTED_DAILY_BARS_SCHEMA_VERSION,
    AdjustmentMode,
    AdjustedDailyBar,
    AdjustedDailyBarsDataset,
)
from serenity_alpha_lab.datasets.instrument_master import (
    INSTRUMENT_MASTER_CONTENT_TYPE,
    INSTRUMENT_MASTER_SCHEMA_NAME,
    INSTRUMENT_MASTER_SCHEMA_VERSION,
    InstrumentListingStatus,
    InstrumentMasterDataset,
    InstrumentMasterRecord,
)
from serenity_alpha_lab.datasets.trading_calendar import (
    TRADING_CALENDAR_CONTENT_TYPE,
    TRADING_CALENDAR_SCHEMA_NAME,
    TRADING_CALENDAR_SCHEMA_VERSION,
    MarketSession,
    TradingCalendarDataset,
    TradingSessionStatus,
)
from serenity_alpha_lab.domain.artifacts import ArtifactRetentionTier
from serenity_alpha_lab.domain.instruments import InstrumentId, Market
from serenity_alpha_lab.integrations.qlib.dataset_converter import (
    QLIB_CALENDAR_SCHEMA_NAME,
    QLIB_DATASET_CONVERSION_SCHEMA_NAME,
    QLIB_FEATURE_SCHEMA_NAME,
    QLIB_FIELD_MAPPING_SCHEMA_NAME,
    QLIB_INSTRUMENT_SCHEMA_NAME,
    QlibDatasetConversionError,
    QlibDatasetConversionSpec,
    convert_datasets_to_qlib,
)
from serenity_alpha_lab.repositories.local_artifact_store import LocalArtifactStore


NOW = datetime(2026, 7, 25, 10, 0, tzinfo=UTC)
SOURCE_TIMESTAMP = datetime(2026, 7, 25, 8, 0, tzinfo=UTC)
SHANGHAI = ZoneInfo("Asia/Shanghai")
RAW_SHA256 = "12" * 32
VERSION_IDS = {
    "trading_calendar": "dsv_" + "1" * 32,
    "instrument_master": "dsv_" + "2" * 32,
    "adjusted_daily_bars": "dsv_" + "3" * 32,
}


def cn_stock(symbol: str) -> InstrumentId:
    return InstrumentId.parse(symbol)


def cn_dt(day: date, hour: int, minute: int = 0) -> datetime:
    return datetime(day.year, day.month, day.day, hour, minute, tzinfo=SHANGHAI)


def make_calendar() -> TradingCalendarDataset:
    sessions = []
    for day in (date(2026, 7, 20), date(2026, 7, 21)):
        sessions.append(
            MarketSession(
                market=Market.CN,
                trade_date=day,
                timezone="Asia/Shanghai",
                status=TradingSessionStatus.OPEN,
                open_at=cn_dt(day, 9, 30),
                close_at=cn_dt(day, 15, 0),
                break_start_at=cn_dt(day, 11, 30),
                break_end_at=cn_dt(day, 13, 0),
                source_bronze_artifact_id=f"art_bronze_calendar_{day:%Y%m%d}",
            )
        )
    sessions.append(
        MarketSession(
            market=Market.CN,
            trade_date=date(2026, 7, 22),
            timezone="Asia/Shanghai",
            status=TradingSessionStatus.CLOSED,
            source_bronze_artifact_id="art_bronze_calendar_closed_20260722",
        )
    )
    return TradingCalendarDataset.from_sessions(
        sessions,
        created_at=NOW,
        trace_id="trace-calendar-qlib",
        run_id="run-calendar-qlib",
        stage_id="stage-calendar-qlib",
    )


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
                source_bronze_artifact_id="art_bronze_master_600519",
            ),
            InstrumentMasterRecord(
                instrument_id=cn_stock("000001.XSHE"),
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
                source_bronze_artifact_id="art_bronze_master_000001",
            ),
        ],
        created_at=NOW,
        trace_id="trace-master-qlib",
        run_id="run-master-qlib",
        stage_id="stage-master-qlib",
    )


def make_adjusted_bars() -> AdjustedDailyBarsDataset:
    records = []
    prices = {
        "600519.XSHG": (100.0, 101.0),
        "000001.XSHE": (12.0, 12.2),
    }
    for instrument_id, closes in prices.items():
        instrument = cn_stock(instrument_id)
        for offset, day in enumerate((date(2026, 7, 20), date(2026, 7, 21))):
            close = closes[offset]
            records.append(
                AdjustedDailyBar(
                    instrument_id=instrument,
                    trade_date=day,
                    provider_id="dsa:EfinanceFetcher",
                    adjustment=AdjustmentMode.BACKWARD,
                    adjustment_factor=1.0 + offset * 0.01,
                    open=close - 0.5,
                    high=close + 1.0,
                    low=close - 1.0,
                    close=close,
                    raw_open=close - 0.5,
                    raw_high=close + 1.0,
                    raw_low=close - 1.0,
                    raw_close=close,
                    volume=1000.0 + offset,
                    amount=close * 1000.0,
                    provider_source="EfinanceFetcher",
                    provider_source_timestamp=SOURCE_TIMESTAMP,
                    provider_raw_response_sha256=RAW_SHA256,
                    field_lineage={
                        "open": "dataset.bars_1d_adjusted.open",
                        "high": "dataset.bars_1d_adjusted.high",
                        "low": "dataset.bars_1d_adjusted.low",
                        "close": "dataset.bars_1d_adjusted.close",
                        "volume": "dataset.bars_1d_adjusted.volume",
                        "amount": "dataset.bars_1d_adjusted.amount",
                        "adjustment_factor": "dataset.bars_1d_adjusted.adjustment_factor",
                    },
                    source_raw_bronze_artifact_id="art_bronze_raw_qlib",
                    source_corporate_action_artifact_ids=("art_bronze_ca_qlib",),
                    currency="CNY",
                )
            )
    return AdjustedDailyBarsDataset.from_records(
        records,
        created_at=NOW,
        trace_id="trace-adjusted-qlib",
        run_id="run-adjusted-qlib",
        stage_id="stage-adjusted-qlib",
    )


def make_manifest(
    store: LocalArtifactStore,
    *,
    dataset_key: str,
    schema_name: str,
    schema_version: str,
    content_type: str,
    quality_status: str = "passed",
    publication_status: str = "published",
) -> DatasetVersionManifest:
    artifact = store.put_bytes(
        f'{{"dataset_key":"{dataset_key}"}}'.encode("utf-8"),
        schema_name=schema_name,
        schema_version=schema_version,
        content_type=content_type,
        produced_by_run_id="run-source-dataset",
        produced_by_stage_id="stage-source-dataset",
        retention_tier=ArtifactRetentionTier.STANDARD,
        created_at=NOW,
    )
    return DatasetVersionManifest(
        dataset_name=schema_name,
        version_id=VERSION_IDS[dataset_key],
        schema_name=schema_name,
        schema_version=schema_version,
        schema_hash="sha256:" + dataset_key.encode("utf-8").hex().ljust(64, "0")[:64],
        content_type=content_type,
        created_at=NOW,
        created_by_run_id="run-source-dataset",
        created_by_stage_id="stage-source-dataset",
        trace_id="trace-source-dataset",
        files=(DatasetFileManifest.from_artifact(artifact, row_count=2),),
        metadata={
            "quality_status": quality_status,
            "publication_status": publication_status,
            "quality_rule_set_version": "dq-fixture",
        },
    )


def make_manifests(store: LocalArtifactStore) -> dict[str, DatasetVersionManifest]:
    return {
        "trading_calendar": make_manifest(
            store,
            dataset_key="trading_calendar",
            schema_name=TRADING_CALENDAR_SCHEMA_NAME,
            schema_version=TRADING_CALENDAR_SCHEMA_VERSION,
            content_type=TRADING_CALENDAR_CONTENT_TYPE,
        ),
        "instrument_master": make_manifest(
            store,
            dataset_key="instrument_master",
            schema_name=INSTRUMENT_MASTER_SCHEMA_NAME,
            schema_version=INSTRUMENT_MASTER_SCHEMA_VERSION,
            content_type=INSTRUMENT_MASTER_CONTENT_TYPE,
        ),
        "adjusted_daily_bars": make_manifest(
            store,
            dataset_key="adjusted_daily_bars",
            schema_name=ADJUSTED_DAILY_BARS_SCHEMA_NAME,
            schema_version=ADJUSTED_DAILY_BARS_SCHEMA_VERSION,
            content_type=ADJUSTED_DAILY_BARS_CONTENT_TYPE,
        ),
    }


def make_spec(manifests: dict[str, DatasetVersionManifest]) -> QlibDatasetConversionSpec:
    return QlibDatasetConversionSpec(
        market=Market.CN,
        start=date(2026, 7, 20),
        end=date(2026, 7, 21),
        dataset_manifests=manifests,
        provider_id="dsa:EfinanceFetcher",
        adjustment=AdjustmentMode.BACKWARD,
        created_at=NOW,
        trace_id="trace-qlib-conversion",
        run_id="run-qlib-conversion",
        stage_id="stage-qlib-conversion",
    )


def test_converts_passed_platform_datasets_to_qlib_calendar_instrument_feature_and_lineage(
    tmp_path: Path,
) -> None:
    store = LocalArtifactStore(tmp_path / "artifacts")
    manifests = make_manifests(store)

    bundle = convert_datasets_to_qlib(
        make_spec(manifests),
        trading_calendar=make_calendar(),
        instrument_master=make_instrument_master(),
        adjusted_daily_bars=make_adjusted_bars(),
    )

    assert bundle.calendar == ("2026-07-20", "2026-07-21")
    assert [record.qlib_symbol for record in bundle.instruments] == ["SH600519", "SZ000001"]
    assert bundle.instruments[0].start_date == date(2026, 7, 20)
    assert bundle.instruments[0].end_date == date(2026, 7, 21)

    feature_records = [record.to_record() for record in bundle.features]
    assert [(row["qlib_symbol"], row["trade_date"]) for row in feature_records] == [
        ("SH600519", "2026-07-20"),
        ("SH600519", "2026-07-21"),
        ("SZ000001", "2026-07-20"),
        ("SZ000001", "2026-07-21"),
    ]
    assert feature_records[0]["values"]["$close"] == 100.0
    assert feature_records[1]["values"]["$factor"] == 1.01
    assert feature_records[0]["lineage"]["$close"]["platform_field"] == "close"
    assert feature_records[0]["lineage"]["$close"]["source"] == "dataset.bars_1d_adjusted.close"

    mapping_records = [mapping.to_record() for mapping in bundle.field_mappings]
    assert {
        (record["direction"], record["platform_field"], record["qlib_field"])
        for record in mapping_records
    } >= {
        ("platform_to_qlib", "close", "$close"),
        ("qlib_to_platform", "close", "$close"),
        ("platform_to_qlib", "instrument_id", "qlib_symbol"),
    }
    assert bundle.source_dataset_versions == {key: manifest.version_id for key, manifest in manifests.items()}
    assert bundle.conversion_id.startswith("qdc_")


def test_publishes_deterministic_calendar_instrument_feature_mapping_and_summary_artifacts(
    tmp_path: Path,
) -> None:
    store = LocalArtifactStore(tmp_path / "artifacts")
    manifests = make_manifests(store)
    bundle = convert_datasets_to_qlib(
        make_spec(manifests),
        trading_calendar=make_calendar(),
        instrument_master=make_instrument_master(),
        adjusted_daily_bars=make_adjusted_bars(),
    )

    published = bundle.publish(store)
    repeated = bundle.publish(store)

    assert published.calendar.artifact_id == repeated.calendar.artifact_id
    assert published.instruments.artifact_id == repeated.instruments.artifact_id
    assert published.features.artifact_id == repeated.features.artifact_id
    assert published.field_mapping.artifact_id == repeated.field_mapping.artifact_id
    assert published.summary.artifact_id == repeated.summary.artifact_id

    assert published.calendar.schema_name == QLIB_CALENDAR_SCHEMA_NAME
    assert published.instruments.schema_name == QLIB_INSTRUMENT_SCHEMA_NAME
    assert published.features.schema_name == QLIB_FEATURE_SCHEMA_NAME
    assert published.field_mapping.schema_name == QLIB_FIELD_MAPPING_SCHEMA_NAME
    assert published.summary.schema_name == QLIB_DATASET_CONVERSION_SCHEMA_NAME

    summary = json.loads(store.get_bytes(published.summary.artifact_id).decode("utf-8"))
    assert summary["conversion_id"] == bundle.conversion_id
    assert summary["source_dataset_versions"] == bundle.source_dataset_versions
    assert summary["artifacts"]["features"]["row_count"] == 4
    assert "records" not in summary["artifacts"]["features"]
    assert summary["runtime"]["qlib_runtime_started"] is False
    assert summary["runtime"]["formal_backtest_started"] is False

    calendar_text = store.get_bytes(published.calendar.artifact_id).decode("utf-8")
    instrument_text = store.get_bytes(published.instruments.artifact_id).decode("utf-8")
    feature_payload = json.loads(store.get_bytes(published.features.artifact_id).decode("utf-8"))

    assert calendar_text == "2026-07-20\n2026-07-21\n"
    assert instrument_text.splitlines()[0] == "SH600519\t2026-07-20\t2026-07-21"
    assert feature_payload["records"][0]["qlib_symbol"] == "SH600519"


def test_instrument_metadata_resolves_at_last_feature_date_for_delisted_coverage(
    tmp_path: Path,
) -> None:
    store = LocalArtifactStore(tmp_path / "artifacts")
    manifests = make_manifests(store)
    active_master = make_instrument_master()
    active_600519 = next(record for record in active_master.records if record.instrument_id.canonical == "600519.XSHG")
    delisted_master = InstrumentMasterDataset.from_records(
        [
            active_600519,
            InstrumentMasterRecord(
                instrument_id=cn_stock("000001.XSHE"),
                name="平安银行退市样例",
                currency="CNY",
                listing_status=InstrumentListingStatus.DELISTED,
                listed_on=date(1991, 4, 3),
                delisted_on=date(2026, 7, 20),
                is_st=False,
                board="主板",
                industries=(),
                provider_mappings=(),
                valid_from=date(1991, 4, 3),
                valid_to=date(2026, 7, 21),
                source_bronze_artifact_id="art_bronze_master_000001_delisted",
            ),
        ],
        created_at=NOW,
        trace_id="trace-master-delisted-qlib",
        run_id="run-master-delisted-qlib",
        stage_id="stage-master-delisted-qlib",
    )
    adjusted_records = tuple(
        record
        for record in make_adjusted_bars().records
        if record.instrument_id.canonical != "000001.XSHE" or record.trade_date == date(2026, 7, 20)
    )

    bundle = convert_datasets_to_qlib(
        make_spec(manifests),
        trading_calendar=make_calendar(),
        instrument_master=delisted_master,
        adjusted_daily_bars=AdjustedDailyBarsDataset.from_records(
            adjusted_records,
            created_at=NOW,
            trace_id="trace-adjusted-delisted-qlib",
            run_id="run-adjusted-delisted-qlib",
            stage_id="stage-adjusted-delisted-qlib",
        ),
    )

    assert [
        (record.qlib_symbol, record.name, record.start_date, record.end_date)
        for record in bundle.instruments
    ] == [
        ("SH600519", "贵州茅台", date(2026, 7, 20), date(2026, 7, 21)),
        ("SZ000001", "平安银行退市样例", date(2026, 7, 20), date(2026, 7, 20)),
    ]


@pytest.mark.parametrize(
    ("quality_status", "publication_status"),
    [("warning", "held"), ("quarantine", "quarantined"), ("blocking", "blocked")],
)
def test_rejects_dataset_versions_that_are_not_passed_and_published(
    tmp_path: Path,
    quality_status: str,
    publication_status: str,
) -> None:
    store = LocalArtifactStore(tmp_path / "artifacts")
    manifests = make_manifests(store)
    manifests["adjusted_daily_bars"] = make_manifest(
        store,
        dataset_key="adjusted_daily_bars",
        schema_name=ADJUSTED_DAILY_BARS_SCHEMA_NAME,
        schema_version=ADJUSTED_DAILY_BARS_SCHEMA_VERSION,
        content_type=ADJUSTED_DAILY_BARS_CONTENT_TYPE,
        quality_status=quality_status,
        publication_status=publication_status,
    )

    with pytest.raises(QlibDatasetConversionError, match="passed.*published"):
        convert_datasets_to_qlib(
            make_spec(manifests),
            trading_calendar=make_calendar(),
            instrument_master=make_instrument_master(),
            adjusted_daily_bars=make_adjusted_bars(),
        )


def test_rejects_dataset_schema_mismatch_before_conversion(tmp_path: Path) -> None:
    store = LocalArtifactStore(tmp_path / "artifacts")
    manifests = make_manifests(store)
    manifests["adjusted_daily_bars"] = make_manifest(
        store,
        dataset_key="adjusted_daily_bars",
        schema_name=TRADING_CALENDAR_SCHEMA_NAME,
        schema_version=TRADING_CALENDAR_SCHEMA_VERSION,
        content_type=TRADING_CALENDAR_CONTENT_TYPE,
    )

    with pytest.raises(QlibDatasetConversionError, match="adjusted_daily_bars.*dataset.bars_1d_adjusted"):
        convert_datasets_to_qlib(
            make_spec(manifests),
            trading_calendar=make_calendar(),
            instrument_master=make_instrument_master(),
            adjusted_daily_bars=make_adjusted_bars(),
        )


def test_converter_module_does_not_import_qlib_runtime_or_web_frameworks() -> None:
    module_path = Path("src/serenity_alpha_lab/integrations/qlib/dataset_converter.py")
    tree = ast.parse(module_path.read_text(encoding="utf-8"), filename=str(module_path))
    imported_roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_roots.update(alias.name.split(".", maxsplit=1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_roots.add(node.module.split(".", maxsplit=1)[0])

    assert imported_roots.isdisjoint({"qlib", "pyqlib", "fastapi", "sqlalchemy"})
