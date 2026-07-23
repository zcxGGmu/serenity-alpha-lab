from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from serenity_alpha_lab.datasets.raw_daily_bars import RAW_DAILY_BARS_SCHEMA_NAME
from serenity_alpha_lab.datasets.raw_daily_bars import RAW_DAILY_BARS_SCHEMA_VERSION
from serenity_alpha_lab.datasets.raw_daily_bars import RAW_DAILY_BARS_CONTENT_TYPE
from serenity_alpha_lab.datasets.catalog import DatasetFileManifest, LocalDatasetCatalog
from serenity_alpha_lab.datasets.trading_calendar import (
    MarketSession,
    TradingCalendarDataset,
    TradingSessionStatus,
)
from serenity_alpha_lab.domain.artifacts import ArtifactRetentionTier
from serenity_alpha_lab.domain.instruments import Market
from serenity_alpha_lab.domain.providers import ProviderCapability
from serenity_alpha_lab.integrations.data.provider_policy import (
    ProviderFallbackTrace,
    ProviderPolicyStatus,
    ProviderSelectionResult,
)
from serenity_alpha_lab.services.data_sync import (
    DataBackfillCommand,
    DataSyncCheckpoint,
    DataSyncScope,
    DataSyncScheduler,
    DataSyncStateStoreError,
    DataSyncTradeDateResult,
    DataSyncRun,
    LocalDataSyncStateStore,
)
from serenity_alpha_lab.repositories.local_artifact_store import LocalArtifactStore


NOW = datetime(2026, 7, 23, 8, 0, tzinfo=UTC)
SHANGHAI = ZoneInfo("Asia/Shanghai")
VERSION_20 = "dsv_" + "a" * 32
VERSION_21 = "dsv_" + "b" * 32


def cn_dt(day: date, hour: int, minute: int = 0) -> datetime:
    return datetime(day.year, day.month, day.day, hour, minute, tzinfo=SHANGHAI)


def open_cn_session(trade_date: date) -> MarketSession:
    return MarketSession(
        market=Market.CN,
        trade_date=trade_date,
        timezone="Asia/Shanghai",
        status=TradingSessionStatus.OPEN,
        open_at=cn_dt(trade_date, 9, 30),
        close_at=cn_dt(trade_date, 15, 0),
        break_start_at=cn_dt(trade_date, 11, 30),
        break_end_at=cn_dt(trade_date, 13, 0),
        source_bronze_artifact_id=f"art_bronze_calendar_{trade_date.isoformat()}",
    )


def closed_cn_session(trade_date: date) -> MarketSession:
    return MarketSession(
        market=Market.CN,
        trade_date=trade_date,
        timezone="Asia/Shanghai",
        status=TradingSessionStatus.CLOSED,
        source_bronze_artifact_id=f"art_bronze_calendar_closed_{trade_date.isoformat()}",
    )


def make_calendar() -> TradingCalendarDataset:
    return TradingCalendarDataset.from_sessions(
        [
            open_cn_session(date(2026, 7, 17)),
            open_cn_session(date(2026, 7, 20)),
            open_cn_session(date(2026, 7, 21)),
            closed_cn_session(date(2026, 7, 22)),
            open_cn_session(date(2026, 7, 23)),
        ],
        created_at=NOW,
        trace_id="trace-data-sync-calendar",
        run_id="run-data-sync-calendar",
        stage_id="stage-calendar-build",
    )


def make_scope() -> DataSyncScope:
    return DataSyncScope(
        dataset_name=RAW_DAILY_BARS_SCHEMA_NAME,
        market=Market.CN,
        alias_scope="cn",
    )


def make_store(tmp_path: Path) -> LocalDataSyncStateStore:
    return LocalDataSyncStateStore(tmp_path / "sync-state")


def save_checkpoint(
    store: LocalDataSyncStateStore,
    scope: DataSyncScope,
    *,
    completed: tuple[date, ...] = (date(2026, 7, 17), date(2026, 7, 20)),
    version_id: str = VERSION_20,
) -> DataSyncCheckpoint:
    checkpoint = DataSyncCheckpoint(
        scope=scope,
        completed_trade_dates=completed,
        last_completed_trade_date=max(completed) if completed else None,
        last_successful_version_id=version_id,
        updated_at=NOW,
        trace_id="trace-existing-sync",
        run_id="run-existing-sync",
        stage_id="stage-existing-sync",
    )
    store.save_checkpoint(checkpoint)
    return checkpoint


def test_incremental_plan_uses_checkpoint_lookback_and_skips_non_trading_as_of(tmp_path: Path) -> None:
    scope = make_scope()
    store = make_store(tmp_path)
    save_checkpoint(store, scope)
    scheduler = DataSyncScheduler(calendar=make_calendar(), state_store=store)

    plan = scheduler.plan_incremental(scope=scope, as_of=date(2026, 7, 22), lookback_window=1)

    assert plan.trade_dates == (date(2026, 7, 20), date(2026, 7, 21))
    assert plan.skipped_non_trading_dates == (date(2026, 7, 22),)
    assert plan.previous_version_id == VERSION_20
    assert plan.mode == "incremental"


def test_incremental_plan_uses_dataset_catalog_latest_when_checkpoint_has_no_version(tmp_path: Path) -> None:
    scope = make_scope()
    store = make_store(tmp_path)
    scheduler = DataSyncScheduler(calendar=make_calendar(), state_store=store)
    artifact_store = LocalArtifactStore(tmp_path / "artifacts")
    artifact = artifact_store.put_bytes(
        b'{"records":[{"instrument_id":"600519.XSHG","trade_date":"2026-07-21"}]}',
        schema_name=RAW_DAILY_BARS_SCHEMA_NAME,
        schema_version=RAW_DAILY_BARS_SCHEMA_VERSION,
        content_type=RAW_DAILY_BARS_CONTENT_TYPE,
        produced_by_run_id="run-catalog-latest",
        produced_by_stage_id="stage-catalog-latest",
        retention_tier=ArtifactRetentionTier.STANDARD,
        created_at=NOW,
    )
    catalog = LocalDatasetCatalog(tmp_path / "catalog")
    latest = catalog.publish_version(
        dataset_name=RAW_DAILY_BARS_SCHEMA_NAME,
        schema_name=RAW_DAILY_BARS_SCHEMA_NAME,
        schema_version=RAW_DAILY_BARS_SCHEMA_VERSION,
        files=(DatasetFileManifest.from_artifact(artifact, row_count=1),),
        created_at=NOW,
        created_by_run_id="run-catalog-latest",
        created_by_stage_id="stage-catalog-latest",
        alias_scope="cn",
    )

    plan = scheduler.plan_incremental(
        scope=scope,
        as_of=date(2026, 7, 21),
        lookback_window=0,
        catalog=catalog,
    )

    assert plan.trade_dates == (date(2026, 7, 21),)
    assert plan.previous_version_id == latest.version_id


def test_local_state_store_lock_prevents_concurrent_sync_runs(tmp_path: Path) -> None:
    scope = make_scope()
    store = make_store(tmp_path)

    first = store.acquire_lock(scope, owner_run_id="run-sync-a", acquired_at=NOW)
    with pytest.raises(DataSyncStateStoreError, match="already locked"):
        store.acquire_lock(scope, owner_run_id="run-sync-b", acquired_at=NOW)

    assert store.current_lock(scope) == first
    store.release_lock(first)
    assert store.current_lock(scope) is None

    second = store.acquire_lock(scope, owner_run_id="run-sync-b", acquired_at=NOW)
    assert second.owner_run_id == "run-sync-b"


def test_data_sync_run_records_idempotent_success_and_retries_failed_trade_date(tmp_path: Path) -> None:
    scope = make_scope()
    store = make_store(tmp_path)
    scheduler = DataSyncScheduler(calendar=make_calendar(), state_store=store)
    plan = scheduler.plan_backfill(
        DataBackfillCommand(
            scope=scope,
            start_date=date(2026, 7, 20),
            end_date=date(2026, 7, 21),
            include_completed=True,
        )
    )
    run = DataSyncRun.start(
        scope=scope,
        plan=plan,
        state_store=store,
        run_id="run-sync-001",
        idempotency_key="sync-bars-cn-20260720-20260721",
        started_at=NOW,
    )

    selected_20 = DataSyncTradeDateResult(
        trade_date=date(2026, 7, 20),
        provider_selection=_selection(ProviderPolicyStatus.SELECTED),
        dataset_version_id=VERSION_20,
    )
    run.record_trade_date_result(selected_20, occurred_at=NOW)
    run.record_trade_date_result(selected_20, occurred_at=NOW)

    exhausted_21 = DataSyncTradeDateResult(
        trade_date=date(2026, 7, 21),
        provider_selection=_selection(ProviderPolicyStatus.EXHAUSTED),
        dataset_version_id=None,
    )
    run.record_trade_date_result(exhausted_21, occurred_at=NOW)

    checkpoint = store.load_checkpoint(scope)
    assert checkpoint is not None
    assert checkpoint.completed_trade_dates == (date(2026, 7, 20),)
    assert checkpoint.last_completed_trade_date == date(2026, 7, 20)
    assert checkpoint.last_successful_version_id == VERSION_20
    assert checkpoint.failed_trade_dates == {"2026-07-21": "exhausted"}

    selected_21 = DataSyncTradeDateResult(
        trade_date=date(2026, 7, 21),
        provider_selection=_selection(ProviderPolicyStatus.SELECTED),
        dataset_version_id=VERSION_21,
    )
    run.record_trade_date_result(selected_21, occurred_at=NOW)
    run.complete(completed_at=NOW)

    checkpoint = store.load_checkpoint(scope)
    assert checkpoint is not None
    assert checkpoint.completed_trade_dates == (date(2026, 7, 20), date(2026, 7, 21))
    assert checkpoint.failed_trade_dates == {}
    assert checkpoint.last_completed_trade_date == date(2026, 7, 21)
    assert checkpoint.last_successful_version_id == VERSION_21
    assert store.current_lock(scope) is None
    assert run.run.events[-1].kind == "run.completed"


def test_backfill_command_plans_only_missing_trading_dates_by_default(tmp_path: Path) -> None:
    scope = make_scope()
    store = make_store(tmp_path)
    save_checkpoint(store, scope, completed=(date(2026, 7, 20),))
    scheduler = DataSyncScheduler(calendar=make_calendar(), state_store=store)

    missing_only = scheduler.plan_backfill(
        DataBackfillCommand(
            scope=scope,
            start_date=date(2026, 7, 17),
            end_date=date(2026, 7, 23),
        )
    )
    include_completed = scheduler.plan_backfill(
        DataBackfillCommand(
            scope=scope,
            start_date=date(2026, 7, 17),
            end_date=date(2026, 7, 23),
            include_completed=True,
        )
    )

    assert missing_only.trade_dates == (date(2026, 7, 17), date(2026, 7, 21), date(2026, 7, 23))
    assert include_completed.trade_dates == (
        date(2026, 7, 17),
        date(2026, 7, 20),
        date(2026, 7, 21),
        date(2026, 7, 23),
    )
    assert missing_only.skipped_non_trading_dates == (date(2026, 7, 22),)
    assert missing_only.previous_version_id == VERSION_20


def _selection(status: ProviderPolicyStatus) -> ProviderSelectionResult:
    trace = ProviderFallbackTrace(
        policy_id="cn-bars-fixture-policy",
        dataset_name="bars_1d",
        market=Market.CN,
        capability=ProviderCapability.DAILY_BARS,
        status=status,
        attempted_order=("akshare",),
        attempts=(),
        selected_provider_id="akshare" if status is ProviderPolicyStatus.SELECTED else None,
        trace_id="trace-data-sync-policy",
        run_id="run-sync-001",
        stage_id="stage-provider-policy",
    )
    return ProviderSelectionResult(
        status=status,
        trace=trace,
        selected_batch=None,
        selected_provider_id=trace.selected_provider_id,
    )
