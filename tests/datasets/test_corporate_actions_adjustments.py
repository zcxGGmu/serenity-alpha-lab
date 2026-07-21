from __future__ import annotations

import json
import math
from datetime import UTC, date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from serenity_alpha_lab.application.api_errors import ApiErrorCode, problem_from_exception
from serenity_alpha_lab.application.tracing import TraceContext
from serenity_alpha_lab.datasets.corporate_actions import (
    ADJUSTED_DAILY_BARS_CONTENT_TYPE,
    ADJUSTED_DAILY_BARS_FIELD_SCHEMA,
    ADJUSTED_DAILY_BARS_SCHEMA_NAME,
    ADJUSTED_DAILY_BARS_SCHEMA_VERSION,
    CORPORATE_ACTIONS_CONTENT_TYPE,
    CORPORATE_ACTIONS_FIELD_SCHEMA,
    CORPORATE_ACTIONS_SCHEMA_NAME,
    CORPORATE_ACTIONS_SCHEMA_VERSION,
    AdjustmentMode,
    AdjustedDailyBarsDataset,
    CorporateAction,
    CorporateActionType,
    CorporateActionsDataset,
    CorporateActionsDatasetError,
)
from serenity_alpha_lab.datasets.instrument_master import (
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
from serenity_alpha_lab.domain.artifacts import ArtifactRetentionTier
from serenity_alpha_lab.domain.instruments import InstrumentId, Market
from serenity_alpha_lab.repositories.local_artifact_store import LocalArtifactStore


NOW = datetime(2026, 7, 22, 10, 0, tzinfo=UTC)
SOURCE_TIMESTAMP = datetime(2026, 7, 22, 8, 0, tzinfo=UTC)
RAW_SHA256 = "EF" * 32
ACTION_SHA256 = "AB" * 32
SHANGHAI = ZoneInfo("Asia/Shanghai")


def cn_stock(symbol: str) -> InstrumentId:
    return InstrumentId.parse(symbol)


def cn_dt(day: date, hour: int, minute: int = 0) -> datetime:
    return datetime(day.year, day.month, day.day, hour, minute, tzinfo=SHANGHAI)


def make_instrument_master() -> InstrumentMasterDataset:
    instrument = cn_stock("600519.XSHG")
    return InstrumentMasterDataset.from_records(
        [
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
                valid_from=date(2001, 8, 27),
                source_bronze_artifact_id="art_bronze_instrument_master_ca_001",
            )
        ],
        created_at=NOW,
        trace_id="trace-master-ca",
        run_id="run-master-ca",
        stage_id="stage-master-ca",
    )


def make_calendar() -> TradingCalendarDataset:
    return TradingCalendarDataset.from_sessions(
        [
            MarketSession(
                market=Market.CN,
                trade_date=day,
                timezone="Asia/Shanghai",
                status=TradingSessionStatus.OPEN if day != date(2026, 7, 22) else TradingSessionStatus.CLOSED,
                open_at=None if day == date(2026, 7, 22) else cn_dt(day, 9, 30),
                close_at=None if day == date(2026, 7, 22) else cn_dt(day, 15, 0),
                break_start_at=None if day == date(2026, 7, 22) else cn_dt(day, 11, 30),
                break_end_at=None if day == date(2026, 7, 22) else cn_dt(day, 13, 0),
                source_bronze_artifact_id=f"art_bronze_calendar_ca_{day:%Y%m%d}",
            )
            for day in (
                date(2026, 7, 17),
                date(2026, 7, 20),
                date(2026, 7, 21),
                date(2026, 7, 22),
            )
        ],
        created_at=NOW,
        trace_id="trace-calendar-ca",
        run_id="run-calendar-ca",
        stage_id="stage-calendar-ca",
    )


def make_raw_bars() -> RawDailyBarsDataset:
    instrument = cn_stock("600519.XSHG")
    raw_bars = [
        _raw_bar(instrument, date(2026, 7, 17), open=100.0, high=105.0, low=95.0, close=100.0),
        _raw_bar(instrument, date(2026, 7, 20), open=98.5, high=100.0, low=97.5, close=99.0),
        _raw_bar(instrument, date(2026, 7, 21), open=89.5, high=91.0, low=88.0, close=90.0),
    ]
    return RawDailyBarsDataset.from_records(
        raw_bars,
        created_at=NOW,
        trace_id="trace-raw-ca",
        run_id="run-raw-ca",
        stage_id="stage-raw-ca",
    )


def _raw_bar(
    instrument: InstrumentId,
    trade_date: date,
    *,
    open: float,
    high: float,
    low: float,
    close: float,
) -> RawDailyBar:
    return RawDailyBar(
        instrument_id=instrument,
        trade_date=trade_date,
        provider_id="dsa:EfinanceFetcher",
        open=open,
        high=high,
        low=low,
        close=close,
        volume=1000.0,
        amount=close * 1000.0,
        provider_source="EfinanceFetcher",
        provider_source_timestamp=SOURCE_TIMESTAMP,
        provider_raw_response_sha256=RAW_SHA256,
        field_lineage={"close": "dsa:EfinanceFetcher.close"},
        source_bronze_artifact_id="art_bronze_raw_daily_ca_001",
        currency="CNY",
    )


def make_corporate_actions(
    actions: list[CorporateAction] | None = None,
) -> CorporateActionsDataset:
    instrument = cn_stock("600519.XSHG")
    records = actions if actions is not None else [
        CorporateAction(
            instrument_id=instrument,
            ex_date=date(2026, 7, 20),
            action_type=CorporateActionType.CASH_DIVIDEND,
            provider_id="dsa:EfinanceFetcher",
            cash_dividend_per_share=2.0,
            currency="CNY",
            provider_source="EfinanceFetcher",
            provider_source_timestamp=SOURCE_TIMESTAMP,
            provider_raw_response_sha256=ACTION_SHA256,
            field_lineage={"cash_dividend_per_share": "dsa:EfinanceFetcher.cash_dividend"},
            source_bronze_artifact_id="art_bronze_ca_dividend_001",
        ),
        CorporateAction(
            instrument_id=instrument,
            ex_date=date(2026, 7, 21),
            action_type=CorporateActionType.BONUS_SHARE,
            provider_id="dsa:EfinanceFetcher",
            bonus_share_ratio=0.1,
            currency="CNY",
            provider_source="EfinanceFetcher",
            provider_source_timestamp=SOURCE_TIMESTAMP,
            provider_raw_response_sha256=ACTION_SHA256,
            field_lineage={"bonus_share_ratio": "dsa:EfinanceFetcher.bonus_share"},
            source_bronze_artifact_id="art_bronze_ca_bonus_001",
        ),
        CorporateAction(
            instrument_id=instrument,
            ex_date=date(2026, 7, 21),
            action_type=CorporateActionType.RIGHTS_ISSUE,
            provider_id="dsa:EfinanceFetcher",
            rights_issue_ratio=0.2,
            rights_issue_price=80.0,
            currency="CNY",
            provider_source="EfinanceFetcher",
            provider_source_timestamp=SOURCE_TIMESTAMP,
            provider_raw_response_sha256=ACTION_SHA256,
            field_lineage={
                "rights_issue_ratio": "dsa:EfinanceFetcher.rights_ratio",
                "rights_issue_price": "dsa:EfinanceFetcher.rights_price",
            },
            source_bronze_artifact_id="art_bronze_ca_rights_001",
        ),
    ]
    return CorporateActionsDataset.from_records(
        records,
        instrument_master=make_instrument_master(),
        trading_calendar=make_calendar(),
        created_at=NOW,
        trace_id="trace-ca-001",
        run_id="run-ca-001",
        stage_id="stage-ca-build",
    )


def test_corporate_actions_and_adjusted_bars_publish_artifacts_and_factors(tmp_path: Path) -> None:
    raw_bars = make_raw_bars()
    actions = make_corporate_actions()
    adjusted = AdjustedDailyBarsDataset.from_raw_bars(
        raw_bars,
        corporate_actions=actions,
        created_at=NOW,
        trace_id="trace-adjusted-001",
        run_id="run-adjusted-001",
        stage_id="stage-adjusted-build",
    )
    store = LocalArtifactStore(tmp_path / "artifacts")

    action_artifact = actions.publish(
        store,
        produced_by_run_id="run-ca-001",
        produced_by_stage_id="stage-ca-build",
    )
    adjusted_artifact = adjusted.publish(
        store,
        produced_by_run_id="run-adjusted-001",
        produced_by_stage_id="stage-adjusted-build",
    )
    second_adjusted_artifact = adjusted.publish(
        store,
        produced_by_run_id="run-adjusted-001",
        produced_by_stage_id="stage-adjusted-build",
    )
    action_payload = json.loads(store.get_bytes(action_artifact.artifact_id).decode("utf-8"))
    adjusted_payload = json.loads(store.get_bytes(adjusted_artifact.artifact_id).decode("utf-8"))

    assert CORPORATE_ACTIONS_FIELD_SCHEMA["cash_dividend_per_share"] == "float64"
    assert CORPORATE_ACTIONS_FIELD_SCHEMA["bonus_share_ratio"] == "float64"
    assert CORPORATE_ACTIONS_FIELD_SCHEMA["rights_issue_price"] == "float64"
    assert ADJUSTED_DAILY_BARS_FIELD_SCHEMA["adjustment_factor"] == "float64"

    assert [
        action.action_type
        for action in actions.actions_for_instrument(
            cn_stock("600519.XSHG"),
            date(2026, 7, 20),
            date(2026, 7, 21),
        )
    ] == [
        CorporateActionType.CASH_DIVIDEND,
        CorporateActionType.BONUS_SHARE,
        CorporateActionType.RIGHTS_ISSUE,
    ]
    assert [action.action_type for action in actions.actions_for_market(Market.CN, date(2026, 7, 21))] == [
        CorporateActionType.BONUS_SHARE,
        CorporateActionType.RIGHTS_ISSUE,
    ]

    cash_coefficient = 0.98
    bonus_rights_coefficient = (99.0 + 0.2 * 80.0) / (1.0 + 0.1 + 0.2) / 99.0
    expected_forward_20260717 = cash_coefficient * bonus_rights_coefficient
    expected_forward_20260720 = bonus_rights_coefficient
    expected_backward_20260721 = 1 / expected_forward_20260717
    noisy_actions = make_corporate_actions(
        [
            *actions.records,
            CorporateAction(
                instrument_id=cn_stock("600519.XSHG"),
                ex_date=date(2026, 7, 20),
                action_type=CorporateActionType.CASH_DIVIDEND,
                provider_id="dsa:OtherFetcher",
                cash_dividend_per_share=10.0,
                currency="CNY",
                provider_source="OtherFetcher",
                provider_source_timestamp=SOURCE_TIMESTAMP,
                provider_raw_response_sha256=ACTION_SHA256,
                field_lineage={"cash_dividend_per_share": "dsa:OtherFetcher.cash_dividend"},
                source_bronze_artifact_id="art_bronze_ca_other_provider",
            ),
        ]
    )
    noisy_adjusted = AdjustedDailyBarsDataset.from_raw_bars(
        raw_bars,
        corporate_actions=noisy_actions,
        created_at=NOW,
    )

    forward_20260717 = adjusted.get(
        cn_stock("600519.XSHG"),
        date(2026, 7, 17),
        provider_id="dsa:EfinanceFetcher",
        adjustment=AdjustmentMode.FORWARD,
    )
    forward_20260720 = adjusted.get(
        "600519.XSHG",
        date(2026, 7, 20),
        provider_id="dsa:EfinanceFetcher",
        adjustment="forward",
    )
    forward_20260721 = adjusted.get(
        cn_stock("600519.XSHG"),
        date(2026, 7, 21),
        provider_id="dsa:EfinanceFetcher",
        adjustment=AdjustmentMode.FORWARD,
    )
    backward_20260721 = adjusted.get(
        cn_stock("600519.XSHG"),
        date(2026, 7, 21),
        provider_id="dsa:EfinanceFetcher",
        adjustment=AdjustmentMode.BACKWARD,
    )

    assert math.isclose(forward_20260717.adjustment_factor, expected_forward_20260717)
    assert math.isclose(
        noisy_adjusted.get(
            cn_stock("600519.XSHG"),
            date(2026, 7, 17),
            provider_id="dsa:EfinanceFetcher",
            adjustment=AdjustmentMode.FORWARD,
        ).adjustment_factor,
        expected_forward_20260717,
    )
    assert math.isclose(forward_20260720.adjustment_factor, expected_forward_20260720)
    assert forward_20260721.adjustment_factor == 1.0
    assert math.isclose(backward_20260721.adjustment_factor, expected_backward_20260721)
    assert math.isclose(forward_20260717.close, 100.0 * expected_forward_20260717)
    assert math.isclose(forward_20260720.close, 99.0 * expected_forward_20260720)
    assert forward_20260721.close == 90.0
    assert math.isclose(backward_20260721.close, 90.0 * expected_backward_20260721)
    assert forward_20260717.volume == 1000.0
    assert forward_20260717.source_raw_bronze_artifact_id == "art_bronze_raw_daily_ca_001"
    assert forward_20260717.source_corporate_action_artifact_ids == (
        "art_bronze_ca_bonus_001",
        "art_bronze_ca_dividend_001",
        "art_bronze_ca_rights_001",
    )

    assert raw_bars.get(cn_stock("600519.XSHG"), date(2026, 7, 17), provider_id="dsa:EfinanceFetcher").close == 100.0
    assert [
        bar.adjustment
        for bar in adjusted.bars_for_instrument(
            cn_stock("600519.XSHG"),
            date(2026, 7, 17),
            date(2026, 7, 21),
            adjustment=AdjustmentMode.FORWARD,
        )
    ] == [
        AdjustmentMode.FORWARD,
        AdjustmentMode.FORWARD,
        AdjustmentMode.FORWARD,
    ]

    assert action_artifact.schema_name == CORPORATE_ACTIONS_SCHEMA_NAME
    assert action_artifact.schema_version == CORPORATE_ACTIONS_SCHEMA_VERSION
    assert action_artifact.content_type == CORPORATE_ACTIONS_CONTENT_TYPE
    assert action_artifact.retention_tier is ArtifactRetentionTier.STANDARD
    assert adjusted_artifact.artifact_id == second_adjusted_artifact.artifact_id
    assert adjusted_artifact.schema_name == ADJUSTED_DAILY_BARS_SCHEMA_NAME
    assert adjusted_artifact.schema_version == ADJUSTED_DAILY_BARS_SCHEMA_VERSION
    assert adjusted_artifact.content_type == ADJUSTED_DAILY_BARS_CONTENT_TYPE

    assert action_payload["schema_name"] == CORPORATE_ACTIONS_SCHEMA_NAME
    assert action_payload["record_count"] == 3
    assert action_payload["records"][0]["action_type"] == "cash_dividend"
    assert adjusted_payload["schema_name"] == ADJUSTED_DAILY_BARS_SCHEMA_NAME
    assert adjusted_payload["record_count"] == 6
    assert adjusted_payload["trace_id"] == "trace-adjusted-001"
    assert adjusted_payload["records"][0]["adjustment"] == "backward"
    assert adjusted_payload["records"][0]["raw_close"] == 100.0
    assert adjusted_payload["records"][0]["partition"] == {"market": "cn", "month": "07", "year": "2026"}


def test_corporate_actions_reject_invalid_events_and_problem_details_mapping() -> None:
    instrument = cn_stock("600519.XSHG")
    duplicate = [
        CorporateAction(
            instrument_id=instrument,
            ex_date=date(2026, 7, 20),
            action_type=CorporateActionType.CASH_DIVIDEND,
            provider_id="dsa:EfinanceFetcher",
            cash_dividend_per_share=2.0,
            currency="CNY",
            provider_source="EfinanceFetcher",
            provider_source_timestamp=SOURCE_TIMESTAMP,
            provider_raw_response_sha256=ACTION_SHA256,
            field_lineage={"cash_dividend_per_share": "dsa:EfinanceFetcher.cash_dividend"},
            source_bronze_artifact_id="art_bronze_ca_dividend_001",
        ),
        CorporateAction(
            instrument_id=instrument,
            ex_date=date(2026, 7, 20),
            action_type=CorporateActionType.CASH_DIVIDEND,
            provider_id="dsa:EfinanceFetcher",
            cash_dividend_per_share=3.0,
            currency="CNY",
            provider_source="EfinanceFetcher",
            provider_source_timestamp=SOURCE_TIMESTAMP,
            provider_raw_response_sha256=ACTION_SHA256,
            field_lineage={"cash_dividend_per_share": "dsa:EfinanceFetcher.cash_dividend"},
            source_bronze_artifact_id="art_bronze_ca_dividend_002",
        ),
    ]
    non_trading_day = [
        CorporateAction(
            instrument_id=instrument,
            ex_date=date(2026, 7, 22),
            action_type=CorporateActionType.CASH_DIVIDEND,
            provider_id="dsa:EfinanceFetcher",
            cash_dividend_per_share=2.0,
            currency="CNY",
            provider_source="EfinanceFetcher",
            provider_source_timestamp=SOURCE_TIMESTAMP,
            provider_raw_response_sha256=ACTION_SHA256,
            field_lineage={"cash_dividend_per_share": "dsa:EfinanceFetcher.cash_dividend"},
            source_bronze_artifact_id="art_bronze_ca_dividend_003",
        )
    ]

    with pytest.raises(CorporateActionsDatasetError, match="Duplicate corporate action key"):
        make_corporate_actions(duplicate)

    with pytest.raises(CorporateActionsDatasetError, match="ex_date must be a trading day"):
        make_corporate_actions(non_trading_day)

    with pytest.raises(CorporateActionsDatasetError, match="rights_issue_price is required"):
        CorporateAction(
            instrument_id=instrument,
            ex_date=date(2026, 7, 21),
            action_type=CorporateActionType.RIGHTS_ISSUE,
            provider_id="dsa:EfinanceFetcher",
            rights_issue_ratio=0.2,
            provider_source="EfinanceFetcher",
            provider_source_timestamp=SOURCE_TIMESTAMP,
            provider_raw_response_sha256=ACTION_SHA256,
            field_lineage={"rights_issue_ratio": "dsa:EfinanceFetcher.rights_ratio"},
            source_bronze_artifact_id="art_bronze_ca_rights_bad",
        )

    with pytest.raises(CorporateActionsDatasetError, match="cash dividend cannot exceed previous close") as exc:
        bad_actions = make_corporate_actions(
            [
                CorporateAction(
                    instrument_id=instrument,
                    ex_date=date(2026, 7, 20),
                    action_type=CorporateActionType.CASH_DIVIDEND,
                    provider_id="dsa:EfinanceFetcher",
                    cash_dividend_per_share=101.0,
                    currency="CNY",
                    provider_source="EfinanceFetcher",
                    provider_source_timestamp=SOURCE_TIMESTAMP,
                    provider_raw_response_sha256=ACTION_SHA256,
                    field_lineage={"cash_dividend_per_share": "dsa:EfinanceFetcher.cash_dividend"},
                    source_bronze_artifact_id="art_bronze_ca_dividend_bad",
                )
            ]
        )
        AdjustedDailyBarsDataset.from_raw_bars(make_raw_bars(), corporate_actions=bad_actions, created_at=NOW)

    problem = problem_from_exception(exc.value, trace_context=TraceContext(trace_id="trace-ca-err"))
    assert problem.status == 422
    assert problem.code is ApiErrorCode.VALIDATION_ERROR
    assert problem.trace_id == "trace-ca-err"


def test_adjusted_daily_bars_merge_incremental_replaces_matching_primary_keys() -> None:
    initial = AdjustedDailyBarsDataset.from_raw_bars(
        RawDailyBarsDataset.from_records(
            [
                _raw_bar(cn_stock("600519.XSHG"), date(2026, 7, 17), open=100.0, high=105.0, low=95.0, close=100.0),
            ],
            created_at=NOW,
            run_id="run-raw-initial",
        ),
        corporate_actions=CorporateActionsDataset.from_records(
            [],
            instrument_master=make_instrument_master(),
            trading_calendar=make_calendar(),
            created_at=NOW,
            run_id="run-ca-empty",
        ),
        created_at=NOW,
        run_id="run-adjusted-initial",
        stage_id="stage-adjusted-initial",
    )
    incremental = AdjustedDailyBarsDataset.from_raw_bars(
        RawDailyBarsDataset.from_records(
            [
                _raw_bar(cn_stock("600519.XSHG"), date(2026, 7, 17), open=101.0, high=106.0, low=96.0, close=101.0),
                _raw_bar(cn_stock("600519.XSHG"), date(2026, 7, 20), open=98.5, high=100.0, low=97.5, close=99.0),
            ],
            created_at=NOW,
            run_id="run-raw-incremental",
        ),
        corporate_actions=CorporateActionsDataset.from_records(
            [],
            instrument_master=make_instrument_master(),
            trading_calendar=make_calendar(),
            created_at=NOW,
            run_id="run-ca-empty",
        ),
        created_at=NOW,
        run_id="run-adjusted-incremental",
        stage_id="stage-adjusted-incremental",
    )

    merged = initial.merge_incremental(
        incremental,
        created_at=datetime(2026, 7, 22, 10, 1, tzinfo=UTC),
        run_id="run-adjusted-merge",
        stage_id="stage-adjusted-merge",
    )

    assert len(merged.records) == 4
    assert merged.created_at == datetime(2026, 7, 22, 10, 1, tzinfo=UTC)
    assert merged.run_id == "run-adjusted-merge"
    assert merged.stage_id == "stage-adjusted-merge"
    assert (
        merged.get(
            cn_stock("600519.XSHG"),
            date(2026, 7, 17),
            provider_id="dsa:EfinanceFetcher",
            adjustment=AdjustmentMode.FORWARD,
        ).close
        == 101.0
    )
    assert (
        merged.get(
            cn_stock("600519.XSHG"),
            date(2026, 7, 20),
            provider_id="dsa:EfinanceFetcher",
            adjustment=AdjustmentMode.BACKWARD,
        ).close
        == 99.0
    )
