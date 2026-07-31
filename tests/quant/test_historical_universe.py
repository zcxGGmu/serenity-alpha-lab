from __future__ import annotations

import json
from datetime import UTC, date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from serenity_alpha_lab.datasets.instrument_master import (
    IndustryClassification,
    InstrumentListingStatus,
    InstrumentMasterDataset,
    InstrumentMasterRecord,
)
from serenity_alpha_lab.datasets.raw_daily_bars import RawDailyBar, RawDailyBarsDataset
from serenity_alpha_lab.datasets.trading_calendar import (
    MarketSession,
    TradingCalendarDataset,
    TradingSessionStatus,
)
from serenity_alpha_lab.domain.instruments import InstrumentId, Market
from serenity_alpha_lab.quant.screening.universe import (
    HISTORICAL_UNIVERSE_CONTENT_TYPE,
    HISTORICAL_UNIVERSE_SCHEMA_NAME,
    HISTORICAL_UNIVERSE_SCHEMA_VERSION,
    HistoricalUniverseError,
    InstrumentTradeStatus,
    UniverseDefinition,
    UniverseInstrumentTradeStatus,
    build_historical_universe_snapshot,
    publish_historical_universe_snapshot,
)
from serenity_alpha_lab.repositories.local_artifact_store import LocalArtifactStore


NOW = datetime(2026, 7, 24, 10, 0, tzinfo=UTC)
SHANGHAI = ZoneInfo("Asia/Shanghai")
INSTRUMENT_MASTER_VERSION = "dsv_" + "1" * 32
TRADING_CALENDAR_VERSION = "dsv_" + "2" * 32
RAW_BARS_VERSION = "dsv_" + "3" * 32
TRADE_STATUS_VERSION = "dsv_" + "4" * 32


def test_universe_definition_requires_concrete_dataset_versions() -> None:
    definition = _definition()

    assert definition.contract_version == "quant.historical_universe@1.0.0"
    assert definition.dataset_versions == {
        "instrument_master": INSTRUMENT_MASTER_VERSION,
        "raw_daily_bars": RAW_BARS_VERSION,
        "trading_calendar": TRADING_CALENDAR_VERSION,
        "instrument_trade_status": TRADE_STATUS_VERSION,
    }
    assert definition.min_listing_trading_days == 3
    assert definition.exclude_st is True
    assert definition.exclude_suspended is True
    assert definition.require_daily_bar is True
    assert definition.to_record()["markets"] == ["cn"]

    with pytest.raises(HistoricalUniverseError, match="concrete Dataset Version"):
        _definition(dataset_versions={"instrument_master": "latest"})

    with pytest.raises(HistoricalUniverseError, match="required dataset version"):
        _definition(dataset_versions={"instrument_master": INSTRUMENT_MASTER_VERSION})


def test_historical_universe_applies_listing_st_suspension_and_data_rules() -> None:
    snapshot = build_historical_universe_snapshot(
        _definition(),
        as_of=date(2026, 7, 21),
        instrument_master=_instrument_master(),
        trading_calendar=_calendar(),
        raw_daily_bars=_raw_bars(),
        trade_statuses=_trade_statuses(),
        created_at=NOW,
        trace_id="trace-historical-universe",
        run_id="run-historical-universe",
        stage_id="stage-historical-universe-build",
    )

    assert snapshot.universe_version_id.startswith("dsv_")
    assert [member.instrument_id for member in snapshot.members] == ["600519.XSHG"]
    assert snapshot.member_count == 1
    assert snapshot.exclusion_count == 5
    assert snapshot.dataset_versions["instrument_master"] == INSTRUMENT_MASTER_VERSION
    assert snapshot.as_of == date(2026, 7, 21)
    assert snapshot.markets == (Market.CN,)

    exclusions_by_instrument = {
        exclusion.instrument_id: exclusion for exclusion in snapshot.exclusions
    }
    assert exclusions_by_instrument["000001.XSHE"].rule_id == "min_listing_trading_days"
    assert exclusions_by_instrument["600087.XSHG"].rule_id == "not_st"
    assert exclusions_by_instrument["600088.XSHG"].rule_id == "listing_status_active"
    assert exclusions_by_instrument["600089.XSHG"].rule_id == "not_suspended"
    assert exclusions_by_instrument["600090.XSHG"].rule_id == "daily_bar_available"

    for exclusion in snapshot.exclusions:
        assert exclusion.rule_id
        assert exclusion.rule_version == "1.0.0"
        assert exclusion.evidence
        assert all(item.dataset_version.startswith("dsv_") for item in exclusion.evidence)
        assert all(item.source_bronze_artifact_id for item in exclusion.evidence)

    record = snapshot.to_record()
    assert record["schema_name"] == HISTORICAL_UNIVERSE_SCHEMA_NAME
    assert record["schema_version"] == HISTORICAL_UNIVERSE_SCHEMA_VERSION
    assert record["members"][0]["instrument_id"] == "600519.XSHG"
    assert record["exclusions"][0]["instrument_id"] == "000001.XSHE"
    json.dumps(record, sort_keys=True)


def test_historical_universe_uses_point_in_time_status_not_current_status() -> None:
    old_date_snapshot = build_historical_universe_snapshot(
        _definition(min_listing_trading_days=1),
        as_of=date(2026, 7, 17),
        instrument_master=_instrument_master(),
        trading_calendar=_calendar(),
        raw_daily_bars=_raw_bars(),
        trade_statuses=_trade_statuses(),
        created_at=NOW,
    )
    later_snapshot = build_historical_universe_snapshot(
        _definition(min_listing_trading_days=1),
        as_of=date(2026, 7, 22),
        instrument_master=_instrument_master(),
        trading_calendar=_calendar(),
        raw_daily_bars=_raw_bars(),
        trade_statuses=_trade_statuses(),
        created_at=NOW,
    )

    old_members = {member.instrument_id for member in old_date_snapshot.members}
    later_members = {member.instrument_id for member in later_snapshot.members}
    later_exclusions = {exclusion.instrument_id: exclusion.rule_id for exclusion in later_snapshot.exclusions}

    assert "600088.XSHG" in old_members
    assert later_exclusions["600088.XSHG"] == "listing_status_active"
    assert "600087.XSHG" in later_members
    assert "600087.XSHG" not in old_members


def test_historical_universe_snapshot_publishes_deterministic_artifact(tmp_path: Path) -> None:
    snapshot = build_historical_universe_snapshot(
        _definition(),
        as_of=date(2026, 7, 21),
        instrument_master=_instrument_master(),
        trading_calendar=_calendar(),
        raw_daily_bars=_raw_bars(),
        trade_statuses=_trade_statuses(),
        created_at=NOW,
        run_id="run-historical-universe",
        stage_id="stage-historical-universe-build",
    )
    store = LocalArtifactStore(tmp_path / "artifacts")

    artifact = publish_historical_universe_snapshot(snapshot, store)
    repeated = publish_historical_universe_snapshot(snapshot, store)
    payload = json.loads(store.get_bytes(artifact.artifact_id).decode("utf-8"))

    assert repeated.artifact_id == artifact.artifact_id
    assert artifact.schema_name == HISTORICAL_UNIVERSE_SCHEMA_NAME
    assert artifact.schema_version == HISTORICAL_UNIVERSE_SCHEMA_VERSION
    assert artifact.content_type == HISTORICAL_UNIVERSE_CONTENT_TYPE
    assert artifact.produced_by_run_id == "run-historical-universe"
    assert artifact.produced_by_stage_id == "stage-historical-universe-build"
    assert payload["universe_version_id"] == snapshot.universe_version_id
    assert payload["member_count"] == 1
    assert payload["exclusion_count"] == 5


def _definition(**overrides) -> UniverseDefinition:
    values = {
        "definition_id": "cn_l0_historical_universe",
        "semantic_version": "1.0.0",
        "markets": (Market.CN,),
        "dataset_versions": {
            "instrument_master": INSTRUMENT_MASTER_VERSION,
            "trading_calendar": TRADING_CALENDAR_VERSION,
            "raw_daily_bars": RAW_BARS_VERSION,
            "instrument_trade_status": TRADE_STATUS_VERSION,
        },
        "min_listing_trading_days": 3,
        "exclude_st": True,
        "exclude_suspended": True,
        "require_daily_bar": True,
        "created_at": NOW,
        "created_by_run_id": "run-historical-universe",
    }
    values.update(overrides)
    return UniverseDefinition(**values)


def _instrument_master() -> InstrumentMasterDataset:
    records = [
        _instrument_record(
            "600519.XSHG",
            name="贵州茅台",
            listed_on=date(2001, 8, 27),
            valid_from=date(2001, 8, 27),
            source="art_bronze_master_moutai",
        ),
        _instrument_record(
            "000001.XSHE",
            name="平安银行",
            listed_on=date(2026, 7, 20),
            valid_from=date(2026, 7, 20),
            source="art_bronze_master_new_listing",
        ),
        _instrument_record(
            "600087.XSHG",
            name="历史ST",
            listed_on=date(2000, 1, 4),
            valid_from=date(2020, 1, 1),
            valid_to=date(2026, 7, 22),
            is_st=True,
            source="art_bronze_master_st_old",
        ),
        _instrument_record(
            "600087.XSHG",
            name="历史ST",
            listed_on=date(2000, 1, 4),
            valid_from=date(2026, 7, 22),
            is_st=False,
            source="art_bronze_master_st_removed",
        ),
        _instrument_record(
            "600088.XSHG",
            name="历史退市",
            listed_on=date(2000, 1, 4),
            valid_from=date(2020, 1, 1),
            valid_to=date(2026, 7, 20),
            source="art_bronze_master_active_before_delist",
        ),
        _instrument_record(
            "600088.XSHG",
            name="历史退市",
            listed_on=date(2000, 1, 4),
            valid_from=date(2026, 7, 20),
            listing_status=InstrumentListingStatus.DELISTED,
            delisted_on=date(2026, 7, 20),
            source="art_bronze_master_delisted",
        ),
        _instrument_record(
            "600089.XSHG",
            name="停牌样本",
            listed_on=date(2000, 1, 4),
            valid_from=date(2020, 1, 1),
            source="art_bronze_master_suspended",
        ),
        _instrument_record(
            "600090.XSHG",
            name="缺日线样本",
            listed_on=date(2000, 1, 4),
            valid_from=date(2020, 1, 1),
            source="art_bronze_master_no_bar",
        ),
    ]
    return InstrumentMasterDataset.from_records(
        records,
        created_at=NOW,
        trace_id="trace-instrument-master",
        run_id="run-instrument-master",
        stage_id="stage-instrument-master",
    )


def _instrument_record(
    instrument_id: str,
    *,
    name: str,
    listed_on: date,
    valid_from: date,
    source: str,
    valid_to: date | None = None,
    listing_status: InstrumentListingStatus = InstrumentListingStatus.ACTIVE,
    delisted_on: date | None = None,
    is_st: bool = False,
) -> InstrumentMasterRecord:
    return InstrumentMasterRecord(
        instrument_id=InstrumentId.parse(instrument_id),
        name=name,
        currency="CNY",
        listing_status=listing_status,
        listed_on=listed_on,
        delisted_on=delisted_on,
        is_st=is_st,
        board="主板",
        industries=(
            IndustryClassification(
                system="SW",
                version="2021",
                level1="综合",
                valid_from=date(2021, 1, 1),
            ),
        ),
        provider_mappings=(),
        valid_from=valid_from,
        valid_to=valid_to,
        source_bronze_artifact_id=source,
    )


def _calendar() -> TradingCalendarDataset:
    sessions = [
        _cn_session(date(2026, 7, 17), "art_bronze_calendar_20260717"),
        _cn_session(date(2026, 7, 20), "art_bronze_calendar_20260720"),
        _cn_session(date(2026, 7, 21), "art_bronze_calendar_20260721"),
        _cn_session(date(2026, 7, 22), "art_bronze_calendar_20260722"),
    ]
    return TradingCalendarDataset.from_sessions(
        sessions,
        created_at=NOW,
        trace_id="trace-calendar",
        run_id="run-calendar",
        stage_id="stage-calendar",
    )


def _cn_session(trade_date: date, source: str) -> MarketSession:
    return MarketSession(
        market=Market.CN,
        trade_date=trade_date,
        timezone="Asia/Shanghai",
        status=TradingSessionStatus.OPEN,
        open_at=datetime(trade_date.year, trade_date.month, trade_date.day, 9, 30, tzinfo=SHANGHAI),
        close_at=datetime(trade_date.year, trade_date.month, trade_date.day, 15, 0, tzinfo=SHANGHAI),
        break_start_at=datetime(trade_date.year, trade_date.month, trade_date.day, 11, 30, tzinfo=SHANGHAI),
        break_end_at=datetime(trade_date.year, trade_date.month, trade_date.day, 13, 0, tzinfo=SHANGHAI),
        source_bronze_artifact_id=source,
    )


def _raw_bars() -> RawDailyBarsDataset:
    instruments = (
        "600519.XSHG",
        "000001.XSHE",
        "600087.XSHG",
        "600088.XSHG",
        "600089.XSHG",
    )
    records = [
        _bar(instrument_id, trade_date)
        for instrument_id in instruments
        for trade_date in (date(2026, 7, 17), date(2026, 7, 20), date(2026, 7, 21), date(2026, 7, 22))
    ]
    return RawDailyBarsDataset.from_records(
        records,
        created_at=NOW,
        trace_id="trace-raw-bars",
        run_id="run-raw-bars",
        stage_id="stage-raw-bars",
    )


def _bar(instrument_id: str, trade_date: date) -> RawDailyBar:
    return RawDailyBar(
        instrument_id=InstrumentId.parse(instrument_id),
        trade_date=trade_date,
        provider_id="akshare",
        open=10.0,
        high=11.0,
        low=9.5,
        close=10.5,
        volume=1000.0,
        amount=10500.0,
        provider_source="akshare",
        provider_source_timestamp=NOW,
        provider_raw_response_sha256="a" * 64,
        field_lineage={"close": "close", "amount": "amount"},
        source_bronze_artifact_id=f"art_bronze_bar_{instrument_id}_{trade_date.isoformat()}",
    )


def _trade_statuses() -> tuple[UniverseInstrumentTradeStatus, ...]:
    return (
        UniverseInstrumentTradeStatus(
            instrument_id="600089.XSHG",
            trade_date=date(2026, 7, 21),
            status=InstrumentTradeStatus.SUSPENDED,
            reason="exchange_suspension",
            source_bronze_artifact_id="art_bronze_trade_status_suspended",
        ),
        UniverseInstrumentTradeStatus(
            instrument_id="600089.XSHG",
            trade_date=date(2026, 7, 22),
            status=InstrumentTradeStatus.TRADABLE,
            reason="resumed",
            source_bronze_artifact_id="art_bronze_trade_status_resumed",
        ),
    )
