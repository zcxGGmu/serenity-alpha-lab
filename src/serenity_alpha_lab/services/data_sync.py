from __future__ import annotations

import hashlib
import json
import os
import re
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import StrEnum
from pathlib import Path
from types import MappingProxyType
from urllib.parse import quote

from serenity_alpha_lab.datasets.catalog import LocalDatasetCatalog
from serenity_alpha_lab.datasets.trading_calendar import TradingCalendarDataset, TradingCalendarDatasetError
from serenity_alpha_lab.domain.instruments import Market
from serenity_alpha_lab.domain.run_lifecycle import EventKind, Run
from serenity_alpha_lab.integrations.data.provider_policy import (
    ProviderPolicyStatus,
    ProviderSelectionResult,
)


_DATASET_VERSION_ID_RE = re.compile(r"^dsv_[0-9a-f]{32,64}$")


class DataSyncError(ValueError):
    """Raised when data sync planning or execution state is invalid."""


class DataSyncStateStoreError(DataSyncError):
    """Raised when checkpoint or lock state cannot be persisted safely."""


class DataSyncMode(StrEnum):
    INCREMENTAL = "incremental"
    BACKFILL = "backfill"


@dataclass(frozen=True, slots=True)
class DataSyncScope:
    dataset_name: str
    market: Market | str
    alias_scope: str = "global"

    @classmethod
    def from_record(cls, record: Mapping[str, object]) -> DataSyncScope:
        return cls(
            dataset_name=str(record["dataset_name"]),
            market=str(record["market"]),
            alias_scope=str(record.get("alias_scope", "global")),
        )

    def __post_init__(self) -> None:
        object.__setattr__(self, "dataset_name", _required_string("dataset_name", self.dataset_name))
        object.__setattr__(self, "market", Market(self.market))
        object.__setattr__(self, "alias_scope", _required_string("alias_scope", self.alias_scope))

    @property
    def key(self) -> str:
        return f"{self.dataset_name}:{self.market.value}:{self.alias_scope}"

    def to_record(self) -> dict[str, object]:
        return {
            "dataset_name": self.dataset_name,
            "market": self.market.value,
            "alias_scope": self.alias_scope,
        }


@dataclass(frozen=True, slots=True)
class DataSyncLock:
    scope: DataSyncScope
    owner_run_id: str
    token: str
    acquired_at: datetime

    @classmethod
    def new(cls, scope: DataSyncScope, *, owner_run_id: str, acquired_at: datetime) -> DataSyncLock:
        token_payload = f"{scope.key}:{owner_run_id}:{acquired_at.isoformat()}:{uuid.uuid4().hex}"
        return cls(
            scope=scope,
            owner_run_id=owner_run_id,
            token=hashlib.sha256(token_payload.encode("utf-8")).hexdigest(),
            acquired_at=acquired_at,
        )

    @classmethod
    def from_record(cls, record: Mapping[str, object]) -> DataSyncLock:
        return cls(
            scope=DataSyncScope.from_record(record["scope"]),  # type: ignore[arg-type]
            owner_run_id=str(record["owner_run_id"]),
            token=str(record["token"]),
            acquired_at=datetime.fromisoformat(str(record["acquired_at"])),
        )

    def __post_init__(self) -> None:
        if type(self.scope) is not DataSyncScope:
            raise DataSyncStateStoreError("scope must be a DataSyncScope")
        object.__setattr__(self, "owner_run_id", _required_string("owner_run_id", self.owner_run_id))
        object.__setattr__(self, "token", _required_string("token", self.token))
        _require_aware_datetime("acquired_at", self.acquired_at)

    def to_record(self) -> dict[str, object]:
        return {
            "scope": self.scope.to_record(),
            "owner_run_id": self.owner_run_id,
            "token": self.token,
            "acquired_at": self.acquired_at.isoformat(),
        }


@dataclass(frozen=True, slots=True)
class DataSyncCheckpoint:
    scope: DataSyncScope
    completed_trade_dates: Sequence[date] = ()
    last_completed_trade_date: date | None = None
    last_successful_version_id: str | None = None
    failed_trade_dates: Mapping[str, str] = field(default_factory=dict)
    updated_at: datetime | None = None
    trace_id: str | None = None
    run_id: str | None = None
    stage_id: str | None = None
    last_provider_policy_status: str | None = None
    last_provider_id: str | None = None
    last_fallback_trace: Mapping[str, object] | None = None

    @classmethod
    def empty(cls, scope: DataSyncScope, *, updated_at: datetime) -> DataSyncCheckpoint:
        return cls(scope=scope, updated_at=updated_at)

    @classmethod
    def from_record(cls, record: Mapping[str, object]) -> DataSyncCheckpoint:
        return cls(
            scope=DataSyncScope.from_record(record["scope"]),  # type: ignore[arg-type]
            completed_trade_dates=tuple(date.fromisoformat(str(value)) for value in record.get("completed_trade_dates", ())),
            last_completed_trade_date=_optional_date_from_record(record.get("last_completed_trade_date")),
            last_successful_version_id=_optional_version_id(record.get("last_successful_version_id")),
            failed_trade_dates={str(key): str(value) for key, value in dict(record.get("failed_trade_dates", {})).items()},
            updated_at=datetime.fromisoformat(str(record["updated_at"])) if record.get("updated_at") else None,
            trace_id=_optional_string(record.get("trace_id")),
            run_id=_optional_string(record.get("run_id")),
            stage_id=_optional_string(record.get("stage_id")),
            last_provider_policy_status=_optional_string(record.get("last_provider_policy_status")),
            last_provider_id=_optional_string(record.get("last_provider_id")),
            last_fallback_trace=dict(record["last_fallback_trace"]) if record.get("last_fallback_trace") else None,
        )

    def __post_init__(self) -> None:
        if type(self.scope) is not DataSyncScope:
            raise DataSyncStateStoreError("scope must be a DataSyncScope")
        completed = tuple(sorted(dict.fromkeys(_require_date_value("completed_trade_date", value) for value in self.completed_trade_dates)))
        object.__setattr__(self, "completed_trade_dates", completed)
        last_completed = self.last_completed_trade_date
        if last_completed is not None:
            last_completed = _require_date_value("last_completed_trade_date", last_completed)
        elif completed:
            last_completed = max(completed)
        if last_completed is not None and last_completed not in completed:
            raise DataSyncStateStoreError("last_completed_trade_date must be one of completed_trade_dates")
        object.__setattr__(self, "last_completed_trade_date", last_completed)
        object.__setattr__(
            self,
            "last_successful_version_id",
            _optional_version_id(self.last_successful_version_id),
        )
        failed: dict[str, str] = {}
        for key, value in self.failed_trade_dates.items():
            failed[_date_key(key)] = _required_string("failure reason", value)
        object.__setattr__(self, "failed_trade_dates", MappingProxyType(dict(sorted(failed.items()))))
        if self.updated_at is not None:
            _require_aware_datetime("updated_at", self.updated_at)
        object.__setattr__(self, "trace_id", _optional_string(self.trace_id))
        object.__setattr__(self, "run_id", _optional_string(self.run_id))
        object.__setattr__(self, "stage_id", _optional_string(self.stage_id))
        object.__setattr__(self, "last_provider_policy_status", _optional_string(self.last_provider_policy_status))
        object.__setattr__(self, "last_provider_id", _optional_string(self.last_provider_id))
        if self.last_fallback_trace is not None:
            object.__setattr__(
                self,
                "last_fallback_trace",
                MappingProxyType(json.loads(json.dumps(self.last_fallback_trace, sort_keys=True))),
            )

    def record_success(
        self,
        *,
        trade_date: date,
        dataset_version_id: str,
        provider_selection: ProviderSelectionResult,
        occurred_at: datetime,
    ) -> DataSyncCheckpoint:
        normalized_date = _require_date_value("trade_date", trade_date)
        version_id = _validate_version_id(dataset_version_id)
        _require_aware_datetime("occurred_at", occurred_at)
        completed = tuple(sorted(set(self.completed_trade_dates).union({normalized_date})))
        failed = dict(self.failed_trade_dates)
        failed.pop(normalized_date.isoformat(), None)
        should_advance_version = self.last_completed_trade_date is None or normalized_date >= self.last_completed_trade_date
        return DataSyncCheckpoint(
            scope=self.scope,
            completed_trade_dates=completed,
            last_completed_trade_date=max(completed),
            last_successful_version_id=version_id if should_advance_version else self.last_successful_version_id,
            failed_trade_dates=failed,
            updated_at=occurred_at,
            trace_id=provider_selection.trace.trace_id,
            run_id=provider_selection.trace.run_id,
            stage_id=provider_selection.trace.stage_id,
            last_provider_policy_status=provider_selection.status.value,
            last_provider_id=provider_selection.selected_provider_id,
            last_fallback_trace=provider_selection.trace.to_record(),
        )

    def record_failure(
        self,
        *,
        trade_date: date,
        reason: str,
        provider_selection: ProviderSelectionResult,
        occurred_at: datetime,
    ) -> DataSyncCheckpoint:
        normalized_date = _require_date_value("trade_date", trade_date)
        _require_aware_datetime("occurred_at", occurred_at)
        failed = dict(self.failed_trade_dates)
        failed[normalized_date.isoformat()] = _required_string("failure reason", reason)
        return DataSyncCheckpoint(
            scope=self.scope,
            completed_trade_dates=self.completed_trade_dates,
            last_completed_trade_date=self.last_completed_trade_date,
            last_successful_version_id=self.last_successful_version_id,
            failed_trade_dates=failed,
            updated_at=occurred_at,
            trace_id=provider_selection.trace.trace_id,
            run_id=provider_selection.trace.run_id,
            stage_id=provider_selection.trace.stage_id,
            last_provider_policy_status=provider_selection.status.value,
            last_provider_id=provider_selection.selected_provider_id,
            last_fallback_trace=provider_selection.trace.to_record(),
        )

    def to_record(self) -> dict[str, object]:
        return {
            "scope": self.scope.to_record(),
            "completed_trade_dates": [value.isoformat() for value in self.completed_trade_dates],
            "last_completed_trade_date": (
                self.last_completed_trade_date.isoformat() if self.last_completed_trade_date else None
            ),
            "last_successful_version_id": self.last_successful_version_id,
            "failed_trade_dates": dict(self.failed_trade_dates),
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "trace_id": self.trace_id,
            "run_id": self.run_id,
            "stage_id": self.stage_id,
            "last_provider_policy_status": self.last_provider_policy_status,
            "last_provider_id": self.last_provider_id,
            "last_fallback_trace": dict(self.last_fallback_trace) if self.last_fallback_trace else None,
        }


@dataclass(frozen=True, slots=True)
class DataSyncPlan:
    scope: DataSyncScope
    mode: DataSyncMode | str
    trade_dates: Sequence[date]
    skipped_non_trading_dates: Sequence[date] = ()
    lookback_window: int = 0
    previous_version_id: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    as_of: date | None = None

    def __post_init__(self) -> None:
        if type(self.scope) is not DataSyncScope:
            raise DataSyncError("scope must be a DataSyncScope")
        object.__setattr__(self, "mode", DataSyncMode(self.mode))
        object.__setattr__(self, "trade_dates", _sorted_unique_dates("trade_dates", self.trade_dates))
        object.__setattr__(
            self,
            "skipped_non_trading_dates",
            _sorted_unique_dates("skipped_non_trading_dates", self.skipped_non_trading_dates),
        )
        if type(self.lookback_window) is not int or self.lookback_window < 0:
            raise DataSyncError("lookback_window cannot be negative")
        object.__setattr__(self, "previous_version_id", _optional_version_id(self.previous_version_id))
        object.__setattr__(self, "start_date", _optional_date_value("start_date", self.start_date))
        object.__setattr__(self, "end_date", _optional_date_value("end_date", self.end_date))
        object.__setattr__(self, "as_of", _optional_date_value("as_of", self.as_of))


@dataclass(frozen=True, slots=True)
class DataBackfillCommand:
    scope: DataSyncScope
    start_date: date
    end_date: date
    include_completed: bool = False

    def __post_init__(self) -> None:
        if type(self.scope) is not DataSyncScope:
            raise DataSyncError("scope must be a DataSyncScope")
        start = _require_date_value("start_date", self.start_date)
        end = _require_date_value("end_date", self.end_date)
        if end < start:
            raise DataSyncError("end_date must be on or after start_date")
        if type(self.include_completed) is not bool:
            raise DataSyncError("include_completed must be a bool")


@dataclass(frozen=True, slots=True)
class DataSyncTradeDateResult:
    trade_date: date
    provider_selection: ProviderSelectionResult
    dataset_version_id: str | None

    def __post_init__(self) -> None:
        object.__setattr__(self, "trade_date", _require_date_value("trade_date", self.trade_date))
        if type(self.provider_selection) is not ProviderSelectionResult:
            raise DataSyncError("provider_selection must be a ProviderSelectionResult")
        if self.provider_selection.status is ProviderPolicyStatus.SELECTED:
            object.__setattr__(
                self,
                "dataset_version_id",
                _validate_version_id(self.dataset_version_id),
            )
        else:
            object.__setattr__(self, "dataset_version_id", _optional_version_id(self.dataset_version_id))

    @property
    def status(self) -> ProviderPolicyStatus:
        return self.provider_selection.status

    @property
    def failure_reason(self) -> str:
        return self.status.value


class LocalDataSyncStateStore:
    """Filesystem-backed checkpoint and lock store for local/offline sync runs."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)

    @property
    def checkpoints_root(self) -> Path:
        return self.root / "checkpoints"

    @property
    def locks_root(self) -> Path:
        return self.root / "locks"

    @property
    def tmp_root(self) -> Path:
        return self.root / "tmp"

    def load_checkpoint(self, scope: DataSyncScope) -> DataSyncCheckpoint | None:
        path = self.checkpoint_path_for(scope)
        try:
            return DataSyncCheckpoint.from_record(json.loads(path.read_text(encoding="utf-8")))
        except FileNotFoundError:
            return None
        except json.JSONDecodeError as exc:
            raise DataSyncStateStoreError(f"Data sync checkpoint is not valid JSON: {scope.key}") from exc

    def save_checkpoint(self, checkpoint: DataSyncCheckpoint) -> DataSyncCheckpoint:
        if type(checkpoint) is not DataSyncCheckpoint:
            raise DataSyncStateStoreError("checkpoint must be a DataSyncCheckpoint")
        _write_json_atomic(self.checkpoint_path_for(checkpoint.scope), checkpoint.to_record(), tmp_root=self.tmp_root)
        return checkpoint

    def acquire_lock(
        self,
        scope: DataSyncScope,
        *,
        owner_run_id: str,
        acquired_at: datetime,
    ) -> DataSyncLock:
        lock = DataSyncLock.new(scope, owner_run_id=owner_run_id, acquired_at=acquired_at)
        path = self.lock_path_for(scope)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.tmp_root.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(lock.to_record(), ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8") + b"\n"
        try:
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
        except FileExistsError as exc:
            raise DataSyncStateStoreError(f"Data sync scope already locked: {scope.key}") from exc
        with os.fdopen(fd, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        return lock

    def current_lock(self, scope: DataSyncScope) -> DataSyncLock | None:
        path = self.lock_path_for(scope)
        try:
            return DataSyncLock.from_record(json.loads(path.read_text(encoding="utf-8")))
        except FileNotFoundError:
            return None
        except json.JSONDecodeError as exc:
            raise DataSyncStateStoreError(f"Data sync lock is not valid JSON: {scope.key}") from exc

    def release_lock(self, lock: DataSyncLock) -> None:
        if type(lock) is not DataSyncLock:
            raise DataSyncStateStoreError("lock must be a DataSyncLock")
        current = self.current_lock(lock.scope)
        if current is None:
            return
        if current != lock:
            raise DataSyncStateStoreError(f"Data sync lock token mismatch: {lock.scope.key}")
        self.lock_path_for(lock.scope).unlink(missing_ok=True)

    def checkpoint_path_for(self, scope: DataSyncScope) -> Path:
        return self.checkpoints_root / _scope_path(scope) / "checkpoint.json"

    def lock_path_for(self, scope: DataSyncScope) -> Path:
        return self.locks_root / _scope_path(scope) / "lock.json"


@dataclass(frozen=True, slots=True)
class DataSyncScheduler:
    calendar: TradingCalendarDataset
    state_store: LocalDataSyncStateStore

    def __post_init__(self) -> None:
        if type(self.calendar) is not TradingCalendarDataset:
            raise DataSyncError("calendar must be a TradingCalendarDataset")
        if type(self.state_store) is not LocalDataSyncStateStore:
            raise DataSyncError("state_store must be a LocalDataSyncStateStore")

    def plan_incremental(
        self,
        *,
        scope: DataSyncScope,
        as_of: date,
        lookback_window: int = 1,
        catalog: LocalDatasetCatalog | None = None,
    ) -> DataSyncPlan:
        _validate_lookback_window(lookback_window)
        checkpoint = self.state_store.load_checkpoint(scope)
        latest_trade_date = self.calendar.previous_trading_day(scope.market, as_of, inclusive=True)
        start_date = self._incremental_start_date(scope, latest_trade_date, lookback_window, checkpoint)
        trade_dates = self._trading_days_or_empty(scope.market, start_date, latest_trade_date)
        skipped = self._skipped_non_trading_dates(scope.market, start_date, as_of)
        return DataSyncPlan(
            scope=scope,
            mode=DataSyncMode.INCREMENTAL,
            trade_dates=trade_dates,
            skipped_non_trading_dates=skipped,
            lookback_window=lookback_window,
            previous_version_id=_previous_version_id(scope, checkpoint, catalog),
            start_date=start_date,
            end_date=latest_trade_date,
            as_of=as_of,
        )

    def plan_backfill(self, command: DataBackfillCommand) -> DataSyncPlan:
        if type(command) is not DataBackfillCommand:
            raise DataSyncError("command must be a DataBackfillCommand")
        checkpoint = self.state_store.load_checkpoint(command.scope)
        completed = set(checkpoint.completed_trade_dates) if checkpoint is not None else set()
        trading_days = self.calendar.trading_days(command.scope.market, command.start_date, command.end_date)
        if command.include_completed:
            planned = trading_days
        else:
            planned = tuple(day for day in trading_days if day not in completed)
        return DataSyncPlan(
            scope=command.scope,
            mode=DataSyncMode.BACKFILL,
            trade_dates=planned,
            skipped_non_trading_dates=self._skipped_non_trading_dates(
                command.scope.market,
                command.start_date,
                command.end_date,
            ),
            previous_version_id=checkpoint.last_successful_version_id if checkpoint is not None else None,
            start_date=command.start_date,
            end_date=command.end_date,
        )

    def _incremental_start_date(
        self,
        scope: DataSyncScope,
        latest_trade_date: date,
        lookback_window: int,
        checkpoint: DataSyncCheckpoint | None,
    ) -> date:
        if checkpoint is None or checkpoint.last_completed_trade_date is None:
            return latest_trade_date
        if lookback_window == 0:
            try:
                return self.calendar.next_trading_day(scope.market, checkpoint.last_completed_trade_date)
            except TradingCalendarDatasetError:
                return latest_trade_date
        current = checkpoint.last_completed_trade_date
        for _ in range(lookback_window - 1):
            try:
                current = self.calendar.previous_trading_day(scope.market, current)
            except TradingCalendarDatasetError:
                break
        return current

    def _trading_days_or_empty(self, market: Market, start: date, end: date) -> tuple[date, ...]:
        if end < start:
            return ()
        return self.calendar.trading_days(market, start, end)

    def _skipped_non_trading_dates(self, market: Market, start: date, end: date) -> tuple[date, ...]:
        if end < start:
            return ()
        return tuple(
            session.trade_date
            for session in self.calendar.sessions_for_market(market, start, end, include_closed=True)
            if not session.is_trading_day
        )


@dataclass(slots=True)
class DataSyncRun:
    scope: DataSyncScope
    plan: DataSyncPlan
    state_store: LocalDataSyncStateStore
    run: Run
    stage_id: str
    lock: DataSyncLock

    @classmethod
    def start(
        cls,
        *,
        scope: DataSyncScope,
        plan: DataSyncPlan,
        state_store: LocalDataSyncStateStore,
        run_id: str,
        idempotency_key: str,
        started_at: datetime,
    ) -> DataSyncRun:
        if type(plan) is not DataSyncPlan:
            raise DataSyncError("plan must be a DataSyncPlan")
        if plan.scope != scope:
            raise DataSyncError("plan scope must match run scope")
        if type(state_store) is not LocalDataSyncStateStore:
            raise DataSyncError("state_store must be a LocalDataSyncStateStore")
        lock = state_store.acquire_lock(scope, owner_run_id=run_id, acquired_at=started_at)
        run = Run.start(
            run_id=run_id,
            run_type="data_sync",
            idempotency_key=idempotency_key,
            started_at=started_at,
        )
        stage_id = f"{run_id}:data-sync"
        run.start_stage(stage_id=stage_id, name="data_sync", started_at=started_at)
        return cls(scope=scope, plan=plan, state_store=state_store, run=run, stage_id=stage_id, lock=lock)

    def record_trade_date_result(self, result: DataSyncTradeDateResult, *, occurred_at: datetime) -> DataSyncCheckpoint:
        if type(result) is not DataSyncTradeDateResult:
            raise DataSyncError("result must be a DataSyncTradeDateResult")
        if result.trade_date not in self.plan.trade_dates:
            raise DataSyncError(f"trade_date is not in plan: {result.trade_date.isoformat()}")
        checkpoint = self.state_store.load_checkpoint(self.scope) or DataSyncCheckpoint.empty(
            self.scope,
            updated_at=occurred_at,
        )
        if result.status is ProviderPolicyStatus.SELECTED:
            checkpoint = checkpoint.record_success(
                trade_date=result.trade_date,
                dataset_version_id=result.dataset_version_id or "",
                provider_selection=result.provider_selection,
                occurred_at=occurred_at,
            )
        else:
            checkpoint = checkpoint.record_failure(
                trade_date=result.trade_date,
                reason=result.failure_reason,
                provider_selection=result.provider_selection,
                occurred_at=occurred_at,
            )
        self.state_store.save_checkpoint(checkpoint)
        self.run.record_stage_event(
            self.stage_id,
            EventKind.INFO,
            message=f"{result.trade_date.isoformat()} {result.status.value}",
            occurred_at=occurred_at,
        )
        return checkpoint

    def complete(self, *, completed_at: datetime) -> None:
        try:
            self.run.complete_stage(self.stage_id, completed_at=completed_at)
            self.run.complete(completed_at=completed_at)
        finally:
            self.state_store.release_lock(self.lock)

    def fail(self, *, reason: str, failed_at: datetime) -> None:
        try:
            self.run.fail_stage(self.stage_id, reason=reason, failed_at=failed_at)
            self.run.fail(reason=reason, failed_at=failed_at)
        finally:
            self.state_store.release_lock(self.lock)


def _previous_version_id(
    scope: DataSyncScope,
    checkpoint: DataSyncCheckpoint | None,
    catalog: LocalDatasetCatalog | None,
) -> str | None:
    if checkpoint is not None and checkpoint.last_successful_version_id is not None:
        return checkpoint.last_successful_version_id
    if catalog is None:
        return None
    if not catalog.alias_path_for(scope.dataset_name, scope.alias_scope).exists():
        return None
    return catalog.resolve_latest(scope.dataset_name, scope.alias_scope).version_id


def _scope_path(scope: DataSyncScope) -> Path:
    return (
        Path(_safe_path_part(scope.dataset_name))
        / _safe_path_part(scope.market.value)
        / _safe_path_part(scope.alias_scope)
    )


def _write_json_atomic(path: Path, record: Mapping[str, object], *, tmp_root: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_root.mkdir(parents=True, exist_ok=True)
    tmp_path = tmp_root / f"{path.stem}.{uuid.uuid4().hex}.tmp"
    try:
        payload = json.dumps(record, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8")
        with tmp_path.open("wb") as handle:
            handle.write(payload)
            handle.write(b"\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, path)
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise
    finally:
        tmp_path.unlink(missing_ok=True)


def _sorted_unique_dates(field_name: str, values: Sequence[date]) -> tuple[date, ...]:
    return tuple(sorted(dict.fromkeys(_require_date_value(field_name, value) for value in values)))


def _optional_date_from_record(value: object | None) -> date | None:
    if value is None:
        return None
    return date.fromisoformat(str(value))


def _optional_date_value(field_name: str, value: object | None) -> date | None:
    if value is None:
        return None
    return _require_date_value(field_name, value)


def _require_date_value(field_name: str, value: object) -> date:
    if type(value) is not date:
        raise DataSyncError(f"{field_name} must be a date")
    return value


def _date_key(value: object) -> str:
    if type(value) is date:
        return value.isoformat()
    if type(value) is str:
        return date.fromisoformat(value).isoformat()
    raise DataSyncStateStoreError("failed_trade_dates keys must be date strings")


def _validate_version_id(value: object | None) -> str:
    if type(value) is not str:
        raise DataSyncError("dataset_version_id is required")
    normalized = value.strip().lower()
    if not _DATASET_VERSION_ID_RE.fullmatch(normalized):
        raise DataSyncError("dataset_version_id must match dsv_<32-64 lowercase sha256 hex chars>")
    return normalized


def _optional_version_id(value: object | None) -> str | None:
    if value is None:
        return None
    return _validate_version_id(value)


def _validate_lookback_window(value: int) -> None:
    if type(value) is not int or value < 0:
        raise DataSyncError("lookback_window cannot be negative")


def _required_string(field_name: str, value: object | None) -> str:
    if type(value) is not str:
        raise DataSyncError(f"{field_name} is required")
    normalized = value.strip()
    if not normalized:
        raise DataSyncError(f"{field_name} is required")
    return normalized


def _optional_string(value: object | None) -> str | None:
    if value is None:
        return None
    if type(value) is not str:
        raise DataSyncError("optional string value must be a string")
    normalized = value.strip()
    return normalized or None


def _require_aware_datetime(field_name: str, value: object) -> None:
    if type(value) is not datetime or value.tzinfo is None or value.utcoffset() is None:
        raise DataSyncError(f"{field_name} must be timezone-aware")


def _safe_path_part(value: str) -> str:
    return quote(value, safe="")


__all__ = [
    "DataBackfillCommand",
    "DataSyncCheckpoint",
    "DataSyncError",
    "DataSyncLock",
    "DataSyncMode",
    "DataSyncPlan",
    "DataSyncRun",
    "DataSyncScheduler",
    "DataSyncScope",
    "DataSyncStateStoreError",
    "DataSyncTradeDateResult",
    "LocalDataSyncStateStore",
]
