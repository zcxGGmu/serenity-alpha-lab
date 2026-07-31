from __future__ import annotations

import json
from datetime import UTC, date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from serenity_alpha_lab.application.api_errors import ApiErrorCode, problem_from_exception
from serenity_alpha_lab.application.tracing import TraceContext
from serenity_alpha_lab.domain.artifacts import ArtifactRetentionTier
from serenity_alpha_lab.domain.instruments import Market
from serenity_alpha_lab.repositories.local_artifact_store import LocalArtifactStore
from serenity_alpha_lab.datasets.trading_calendar import (
    TRADING_CALENDAR_CONTENT_TYPE,
    TRADING_CALENDAR_SCHEMA_NAME,
    TRADING_CALENDAR_SCHEMA_VERSION,
    MarketSession,
    TradingCalendarDataset,
    TradingCalendarDatasetError,
    TradingSessionStatus,
    market_timezone,
)


NOW = datetime(2026, 7, 21, 10, 0, tzinfo=UTC)
SHANGHAI = ZoneInfo("Asia/Shanghai")


def cn_dt(day: date, hour: int, minute: int = 0) -> datetime:
    return datetime(day.year, day.month, day.day, hour, minute, tzinfo=SHANGHAI)


def cn_session(
    trade_date: date,
    *,
    status: TradingSessionStatus = TradingSessionStatus.OPEN,
    open_at: datetime | None = None,
    close_at: datetime | None = None,
    break_start_at: datetime | None = None,
    break_end_at: datetime | None = None,
    source_bronze_artifact_id: str = "art_bronze_cn_calendar_001",
    note: str | None = None,
) -> MarketSession:
    return MarketSession(
        market=Market.CN,
        trade_date=trade_date,
        timezone="Asia/Shanghai",
        status=status,
        open_at=open_at,
        close_at=close_at,
        break_start_at=break_start_at,
        break_end_at=break_end_at,
        source_bronze_artifact_id=source_bronze_artifact_id,
        note=note,
    )


def regular_cn_session(trade_date: date, source_id: str) -> MarketSession:
    return cn_session(
        trade_date,
        open_at=cn_dt(trade_date, 9, 30),
        close_at=cn_dt(trade_date, 15, 0),
        break_start_at=cn_dt(trade_date, 11, 30),
        break_end_at=cn_dt(trade_date, 13, 0),
        source_bronze_artifact_id=source_id,
    )


def make_calendar() -> TradingCalendarDataset:
    return TradingCalendarDataset.from_sessions(
        [
            cn_session(
                date(2026, 2, 17),
                status=TradingSessionStatus.CLOSED,
                source_bronze_artifact_id="art_bronze_cn_spring_festival_2026",
                note="Spring Festival holiday",
            ),
            regular_cn_session(date(2026, 7, 20), "art_bronze_cn_calendar_20260720"),
            regular_cn_session(date(2026, 7, 21), "art_bronze_cn_calendar_20260721"),
            cn_session(
                date(2026, 7, 22),
                status=TradingSessionStatus.HALF_DAY,
                open_at=cn_dt(date(2026, 7, 22), 9, 30),
                close_at=cn_dt(date(2026, 7, 22), 11, 30),
                source_bronze_artifact_id="art_bronze_cn_half_day_20260722",
                note="Synthetic half-day fixture for exceptional session handling",
            ),
            cn_session(
                date(2026, 7, 23),
                status=TradingSessionStatus.AD_HOC_CLOSED,
                source_bronze_artifact_id="art_bronze_cn_typhoon_20260723",
                note="Synthetic ad-hoc closure fixture",
            ),
        ],
        created_at=NOW,
        trace_id="trace-calendar-001",
        run_id="run-calendar-001",
        stage_id="stage-calendar-build",
    )


def test_trading_calendar_publishes_artifact_and_queries_sessions(tmp_path: Path) -> None:
    calendar = make_calendar()
    store = LocalArtifactStore(tmp_path / "artifacts")

    session = calendar.get(Market.CN, date(2026, 7, 21))
    holiday = calendar.get("cn", date(2026, 2, 17))
    artifact = calendar.publish(
        store,
        produced_by_run_id="run-calendar-001",
        produced_by_stage_id="stage-calendar-build",
    )
    second_artifact = calendar.publish(
        store,
        produced_by_run_id="run-calendar-001",
        produced_by_stage_id="stage-calendar-build",
    )
    payload = json.loads(store.get_bytes(artifact.artifact_id).decode("utf-8"))

    assert market_timezone(Market.CN).key == "Asia/Shanghai"
    assert session.market is Market.CN
    assert session.timezone == "Asia/Shanghai"
    assert session.is_trading_day is True
    assert session.open_at_utc == datetime(2026, 7, 21, 1, 30, tzinfo=UTC)
    assert session.close_at_utc == datetime(2026, 7, 21, 7, 0, tzinfo=UTC)
    assert session.break_start_at_utc == datetime(2026, 7, 21, 3, 30, tzinfo=UTC)
    assert session.break_end_at_utc == datetime(2026, 7, 21, 5, 0, tzinfo=UTC)

    assert holiday.is_trading_day is False
    assert holiday.open_at is None
    assert calendar.is_trading_day(Market.CN, date(2026, 2, 17)) is False
    assert calendar.trading_days(Market.CN, date(2026, 7, 20), date(2026, 7, 23)) == (
        date(2026, 7, 20),
        date(2026, 7, 21),
        date(2026, 7, 22),
    )
    assert [item.trade_date for item in calendar.sessions_for_market(Market.CN, date(2026, 7, 20), date(2026, 7, 23), include_closed=False)] == [
        date(2026, 7, 20),
        date(2026, 7, 21),
        date(2026, 7, 22),
    ]
    assert calendar.next_trading_day(Market.CN, date(2026, 7, 20)) == date(2026, 7, 21)
    assert calendar.next_trading_day(Market.CN, date(2026, 7, 20), inclusive=True) == date(2026, 7, 20)
    assert calendar.previous_trading_day(Market.CN, date(2026, 7, 23)) == date(2026, 7, 22)
    assert calendar.previous_trading_day(Market.CN, date(2026, 7, 22), inclusive=True) == date(2026, 7, 22)

    assert artifact.artifact_id == second_artifact.artifact_id
    assert artifact.sha256 == second_artifact.sha256
    assert artifact.schema_name == TRADING_CALENDAR_SCHEMA_NAME
    assert artifact.schema_version == TRADING_CALENDAR_SCHEMA_VERSION
    assert artifact.content_type == TRADING_CALENDAR_CONTENT_TYPE
    assert artifact.retention_tier is ArtifactRetentionTier.STANDARD
    assert artifact.produced_by_run_id == "run-calendar-001"
    assert artifact.produced_by_stage_id == "stage-calendar-build"

    assert payload["schema_name"] == TRADING_CALENDAR_SCHEMA_NAME
    assert payload["schema_version"] == TRADING_CALENDAR_SCHEMA_VERSION
    assert payload["trace_id"] == "trace-calendar-001"
    assert payload["run_id"] == "run-calendar-001"
    assert payload["stage_id"] == "stage-calendar-build"
    assert payload["record_count"] == 5
    assert "art_bronze_cn_calendar_20260721" in payload["source_bronze_artifact_ids"]
    assert payload["records"][0]["market"] == "cn"
    assert payload["records"][0]["trade_date"] == "2026-02-17"
    assert payload["records"][0]["status"] == "closed"
    assert payload["records"][2]["open_at_utc"] == "2026-07-21T01:30:00+00:00"


def test_trading_calendar_converts_utc_timestamps_to_market_sessions() -> None:
    calendar = make_calendar()

    assert calendar.is_open_at(Market.CN, datetime(2026, 7, 21, 1, 20, tzinfo=UTC)) is False
    assert calendar.is_open_at(Market.CN, datetime(2026, 7, 21, 1, 35, tzinfo=UTC)) is True
    assert calendar.is_open_at(Market.CN, datetime(2026, 7, 21, 4, 0, tzinfo=UTC)) is False
    assert calendar.is_open_at(Market.CN, datetime(2026, 7, 21, 6, 0, tzinfo=UTC)) is True
    assert calendar.is_open_at(Market.CN, datetime(2026, 7, 21, 7, 5, tzinfo=UTC)) is False
    assert calendar.is_open_at(Market.CN, datetime(2026, 7, 22, 1, 40, tzinfo=UTC)) is True
    assert calendar.is_open_at(Market.CN, datetime(2026, 7, 22, 5, 0, tzinfo=UTC)) is False
    assert calendar.is_open_at(Market.CN, datetime(2026, 2, 17, 2, 0, tzinfo=UTC)) is False

    with pytest.raises(TradingCalendarDatasetError, match="at must be timezone-aware"):
        calendar.is_open_at(Market.CN, datetime(2026, 7, 21, 9, 35))


def test_trading_calendar_rejects_invalid_sessions_and_maps_to_problem_details() -> None:
    with pytest.raises(TradingCalendarDatasetError, match="Duplicate trading calendar key"):
        TradingCalendarDataset.from_sessions(
            [
                regular_cn_session(date(2026, 7, 21), "art_bronze_cn_calendar_001"),
                regular_cn_session(date(2026, 7, 21), "art_bronze_cn_calendar_002"),
            ],
            created_at=NOW,
        )

    with pytest.raises(TradingCalendarDatasetError, match="source_bronze_artifact_id is required") as exc:
        cn_session(
            date(2026, 7, 21),
            open_at=cn_dt(date(2026, 7, 21), 9, 30),
            close_at=cn_dt(date(2026, 7, 21), 15, 0),
            source_bronze_artifact_id="",
        )

    problem = problem_from_exception(exc.value, trace_context=TraceContext(trace_id="trace-calendar-err"))
    assert problem.status == 422
    assert problem.code is ApiErrorCode.VALIDATION_ERROR
    assert problem.trace_id == "trace-calendar-err"

    with pytest.raises(TradingCalendarDatasetError, match="open_at must be timezone-aware"):
        cn_session(
            date(2026, 7, 21),
            open_at=datetime(2026, 7, 21, 9, 30),
            close_at=cn_dt(date(2026, 7, 21), 15, 0),
        )

    with pytest.raises(TradingCalendarDatasetError, match="timezone must match market timezone"):
        MarketSession(
            market=Market.CN,
            trade_date=date(2026, 7, 21),
            timezone="America/New_York",
            status=TradingSessionStatus.OPEN,
            open_at=datetime(2026, 7, 21, 9, 30, tzinfo=ZoneInfo("America/New_York")),
            close_at=datetime(2026, 7, 21, 15, 0, tzinfo=ZoneInfo("America/New_York")),
            source_bronze_artifact_id="art_bronze_wrong_tz",
        )

    with pytest.raises(TradingCalendarDatasetError, match="trading sessions require open_at and close_at"):
        cn_session(date(2026, 7, 21), open_at=cn_dt(date(2026, 7, 21), 9, 30), close_at=None)

    with pytest.raises(TradingCalendarDatasetError, match="closed sessions cannot carry open_at or close_at"):
        cn_session(
            date(2026, 7, 21),
            status=TradingSessionStatus.CLOSED,
            open_at=cn_dt(date(2026, 7, 21), 9, 30),
            close_at=cn_dt(date(2026, 7, 21), 15, 0),
        )

    with pytest.raises(TradingCalendarDatasetError, match="break window must be within open and close"):
        cn_session(
            date(2026, 7, 21),
            open_at=cn_dt(date(2026, 7, 21), 9, 30),
            close_at=cn_dt(date(2026, 7, 21), 15, 0),
            break_start_at=cn_dt(date(2026, 7, 21), 15, 0),
            break_end_at=cn_dt(date(2026, 7, 21), 16, 0),
        )
