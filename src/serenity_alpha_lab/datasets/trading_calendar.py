from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from enum import StrEnum
from types import MappingProxyType
from zoneinfo import ZoneInfo

from serenity_alpha_lab.domain.artifacts import (
    ArtifactManifest,
    ArtifactRetentionTier,
    ArtifactStore,
)
from serenity_alpha_lab.domain.instruments import Market


TRADING_CALENDAR_SCHEMA_NAME = "dataset.trading_calendar"
TRADING_CALENDAR_SCHEMA_VERSION = "1.0.0"
TRADING_CALENDAR_CONTENT_TYPE = "application/vnd.serenity.dataset.trading-calendar+json"


class TradingCalendarDatasetError(ValueError):
    """Raised when trading calendar records violate the Dataset contract."""


class TradingSessionStatus(StrEnum):
    OPEN = "open"
    HALF_DAY = "half_day"
    CLOSED = "closed"
    AD_HOC_CLOSED = "ad_hoc_closed"
    SUSPENDED = "suspended"


_MARKET_TIMEZONES: Mapping[Market, str] = MappingProxyType(
    {
        Market.CN: "Asia/Shanghai",
        Market.HK: "Asia/Hong_Kong",
        Market.US: "America/New_York",
        Market.JP: "Asia/Tokyo",
        Market.KR: "Asia/Seoul",
        Market.TW: "Asia/Taipei",
    }
)
_TRADING_STATUSES = frozenset({TradingSessionStatus.OPEN, TradingSessionStatus.HALF_DAY})


def market_timezone(market: Market | str) -> ZoneInfo:
    normalized = _coerce_market(market)
    return ZoneInfo(_MARKET_TIMEZONES[normalized])


@dataclass(frozen=True, slots=True)
class MarketSession:
    market: Market | str
    trade_date: date
    timezone: str
    status: TradingSessionStatus | str
    source_bronze_artifact_id: str
    open_at: datetime | None = None
    close_at: datetime | None = None
    break_start_at: datetime | None = None
    break_end_at: datetime | None = None
    note: str | None = None

    def __post_init__(self) -> None:
        market = _coerce_market(self.market)
        _require_date("trade_date", self.trade_date)
        timezone = _required_string("timezone", self.timezone)
        expected_timezone = _MARKET_TIMEZONES[market]
        if timezone != expected_timezone:
            raise TradingCalendarDatasetError("timezone must match market timezone")
        zone = ZoneInfo(timezone)
        status = TradingSessionStatus(self.status)

        object.__setattr__(self, "market", market)
        object.__setattr__(self, "timezone", timezone)
        object.__setattr__(self, "status", status)
        object.__setattr__(
            self,
            "source_bronze_artifact_id",
            _required_string("source_bronze_artifact_id", self.source_bronze_artifact_id),
        )
        object.__setattr__(self, "note", _optional_string(self.note))

        open_at = _normalize_session_datetime("open_at", self.open_at, self.trade_date, zone)
        close_at = _normalize_session_datetime("close_at", self.close_at, self.trade_date, zone)
        break_start_at = _normalize_session_datetime(
            "break_start_at",
            self.break_start_at,
            self.trade_date,
            zone,
        )
        break_end_at = _normalize_session_datetime(
            "break_end_at",
            self.break_end_at,
            self.trade_date,
            zone,
        )

        if status in _TRADING_STATUSES:
            if open_at is None or close_at is None:
                raise TradingCalendarDatasetError("trading sessions require open_at and close_at")
            if close_at <= open_at:
                raise TradingCalendarDatasetError("close_at must be after open_at")
            _validate_break_window(open_at, close_at, break_start_at, break_end_at)
        else:
            if open_at is not None or close_at is not None or break_start_at is not None or break_end_at is not None:
                raise TradingCalendarDatasetError("closed sessions cannot carry open_at or close_at")

        object.__setattr__(self, "open_at", open_at)
        object.__setattr__(self, "close_at", close_at)
        object.__setattr__(self, "break_start_at", break_start_at)
        object.__setattr__(self, "break_end_at", break_end_at)

    @property
    def is_trading_day(self) -> bool:
        return self.status in _TRADING_STATUSES

    @property
    def open_at_utc(self) -> datetime | None:
        return self.open_at.astimezone(UTC) if self.open_at else None

    @property
    def close_at_utc(self) -> datetime | None:
        return self.close_at.astimezone(UTC) if self.close_at else None

    @property
    def break_start_at_utc(self) -> datetime | None:
        return self.break_start_at.astimezone(UTC) if self.break_start_at else None

    @property
    def break_end_at_utc(self) -> datetime | None:
        return self.break_end_at.astimezone(UTC) if self.break_end_at else None

    def is_open_at(self, at: datetime) -> bool:
        _require_aware_datetime("at", at)
        if not self.is_trading_day or self.open_at is None or self.close_at is None:
            return False
        local_at = at.astimezone(ZoneInfo(self.timezone))
        if local_at.date() != self.trade_date:
            return False
        if not (self.open_at <= local_at < self.close_at):
            return False
        if self.break_start_at is not None and self.break_end_at is not None:
            return not (self.break_start_at <= local_at < self.break_end_at)
        return True

    def to_record(self) -> dict[str, object]:
        return {
            "market": self.market.value,
            "trade_date": self.trade_date.isoformat(),
            "timezone": self.timezone,
            "status": self.status.value,
            "is_trading_day": self.is_trading_day,
            "open_at": self.open_at.isoformat() if self.open_at else None,
            "close_at": self.close_at.isoformat() if self.close_at else None,
            "break_start_at": self.break_start_at.isoformat() if self.break_start_at else None,
            "break_end_at": self.break_end_at.isoformat() if self.break_end_at else None,
            "open_at_utc": self.open_at_utc.isoformat() if self.open_at_utc else None,
            "close_at_utc": self.close_at_utc.isoformat() if self.close_at_utc else None,
            "break_start_at_utc": self.break_start_at_utc.isoformat() if self.break_start_at_utc else None,
            "break_end_at_utc": self.break_end_at_utc.isoformat() if self.break_end_at_utc else None,
            "source_bronze_artifact_id": self.source_bronze_artifact_id,
            "note": self.note,
        }


@dataclass(frozen=True, slots=True)
class TradingCalendarDataset:
    sessions: Sequence[MarketSession]
    created_at: datetime
    trace_id: str | None = None
    run_id: str | None = None
    stage_id: str | None = None
    _session_by_key: Mapping[tuple[Market, date], MarketSession] = field(init=False, repr=False, compare=False)
    _sessions_by_market: Mapping[Market, tuple[MarketSession, ...]] = field(init=False, repr=False, compare=False)

    @classmethod
    def from_sessions(
        cls,
        sessions: Iterable[MarketSession],
        *,
        created_at: datetime,
        trace_id: str | None = None,
        run_id: str | None = None,
        stage_id: str | None = None,
    ) -> TradingCalendarDataset:
        return cls(
            sessions=tuple(sessions),
            created_at=created_at,
            trace_id=trace_id,
            run_id=run_id,
            stage_id=stage_id,
        )

    def __post_init__(self) -> None:
        _require_aware_datetime("created_at", self.created_at)
        object.__setattr__(self, "trace_id", _optional_string(self.trace_id))
        object.__setattr__(self, "run_id", _optional_string(self.run_id))
        object.__setattr__(self, "stage_id", _optional_string(self.stage_id))

        sessions = tuple(self.sessions)
        if not sessions:
            raise TradingCalendarDatasetError("trading calendar sessions are required")
        for session in sessions:
            if type(session) is not MarketSession:
                raise TradingCalendarDatasetError("sessions must contain MarketSession values")

        session_by_key: dict[tuple[Market, date], MarketSession] = {}
        sessions_by_market: dict[Market, list[MarketSession]] = defaultdict(list)
        for session in sessions:
            key = (session.market, session.trade_date)
            if key in session_by_key:
                raise TradingCalendarDatasetError(
                    f"Duplicate trading calendar key: {session.market.value} {session.trade_date.isoformat()}"
                )
            session_by_key[key] = session
            sessions_by_market[session.market].append(session)

        sorted_sessions = tuple(sorted(sessions, key=lambda item: (item.market.value, item.trade_date)))
        frozen_by_market = {
            market: tuple(sorted(market_sessions, key=lambda item: item.trade_date))
            for market, market_sessions in sessions_by_market.items()
        }
        object.__setattr__(self, "sessions", sorted_sessions)
        object.__setattr__(self, "_session_by_key", MappingProxyType(dict(session_by_key)))
        object.__setattr__(self, "_sessions_by_market", MappingProxyType(frozen_by_market))

    def get(self, market: Market | str, trade_date: date) -> MarketSession:
        normalized_market = _coerce_market(market)
        _require_date("trade_date", trade_date)
        try:
            return self._session_by_key[(normalized_market, trade_date)]
        except KeyError as exc:
            raise TradingCalendarDatasetError(
                f"Calendar session not found: {normalized_market.value} {trade_date.isoformat()}"
            ) from exc

    def sessions_for_market(
        self,
        market: Market | str,
        start: date,
        end: date,
        *,
        include_closed: bool = True,
    ) -> tuple[MarketSession, ...]:
        normalized_market = _coerce_market(market)
        _validate_date_range(start, end)
        if type(include_closed) is not bool:
            raise TradingCalendarDatasetError("include_closed must be a bool")
        sessions = self._sessions_by_market.get(normalized_market, ())
        return tuple(
            session
            for session in sessions
            if start <= session.trade_date <= end and (include_closed or session.is_trading_day)
        )

    def trading_days(self, market: Market | str, start: date, end: date) -> tuple[date, ...]:
        return tuple(
            session.trade_date
            for session in self.sessions_for_market(market, start, end, include_closed=False)
        )

    def is_trading_day(self, market: Market | str, trade_date: date) -> bool:
        return self.get(market, trade_date).is_trading_day

    def next_trading_day(
        self,
        market: Market | str,
        after: date,
        *,
        inclusive: bool = False,
    ) -> date:
        normalized_market = _coerce_market(market)
        _require_date("after", after)
        for session in self._sessions_by_market.get(normalized_market, ()):
            if not session.is_trading_day:
                continue
            if session.trade_date > after or (inclusive and session.trade_date == after):
                return session.trade_date
        raise TradingCalendarDatasetError(f"Next trading day not found after {after.isoformat()}")

    def previous_trading_day(
        self,
        market: Market | str,
        before: date,
        *,
        inclusive: bool = False,
    ) -> date:
        normalized_market = _coerce_market(market)
        _require_date("before", before)
        for session in reversed(self._sessions_by_market.get(normalized_market, ())):
            if not session.is_trading_day:
                continue
            if session.trade_date < before or (inclusive and session.trade_date == before):
                return session.trade_date
        raise TradingCalendarDatasetError(f"Previous trading day not found before {before.isoformat()}")

    def is_open_at(self, market: Market | str, at: datetime) -> bool:
        normalized_market = _coerce_market(market)
        _require_aware_datetime("at", at)
        local_date = at.astimezone(market_timezone(normalized_market)).date()
        session = self._session_by_key.get((normalized_market, local_date))
        return session.is_open_at(at) if session is not None else False

    @property
    def source_bronze_artifact_ids(self) -> tuple[str, ...]:
        return tuple(sorted({session.source_bronze_artifact_id for session in self.sessions}))

    def to_json_bytes(self) -> bytes:
        payload = {
            "schema_name": TRADING_CALENDAR_SCHEMA_NAME,
            "schema_version": TRADING_CALENDAR_SCHEMA_VERSION,
            "created_at": self.created_at.isoformat(),
            "trace_id": self.trace_id,
            "run_id": self.run_id,
            "stage_id": self.stage_id,
            "record_count": len(self.sessions),
            "source_bronze_artifact_ids": list(self.source_bronze_artifact_ids),
            "records": [session.to_record() for session in self.sessions],
        }
        return json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")

    def publish(
        self,
        artifact_store: ArtifactStore,
        *,
        produced_by_run_id: str | None = None,
        produced_by_stage_id: str | None = None,
        retention_tier: ArtifactRetentionTier = ArtifactRetentionTier.STANDARD,
    ) -> ArtifactManifest:
        run_id = _required_string("produced_by_run_id", produced_by_run_id or self.run_id)
        stage_id = produced_by_stage_id if produced_by_stage_id is not None else self.stage_id
        return artifact_store.put_bytes(
            self.to_json_bytes(),
            schema_name=TRADING_CALENDAR_SCHEMA_NAME,
            schema_version=TRADING_CALENDAR_SCHEMA_VERSION,
            content_type=TRADING_CALENDAR_CONTENT_TYPE,
            produced_by_run_id=run_id,
            produced_by_stage_id=stage_id,
            retention_tier=retention_tier,
            created_at=self.created_at,
        )


def _coerce_market(value: Market | str) -> Market:
    try:
        return Market(value)
    except ValueError as exc:
        raise TradingCalendarDatasetError(f"Unsupported market: {value}") from exc


def _validate_date_range(start: date, end: date) -> None:
    _require_date("start", start)
    _require_date("end", end)
    if end < start:
        raise TradingCalendarDatasetError("end must be on or after start")


def _validate_break_window(
    open_at: datetime,
    close_at: datetime,
    break_start_at: datetime | None,
    break_end_at: datetime | None,
) -> None:
    if (break_start_at is None) != (break_end_at is None):
        raise TradingCalendarDatasetError("break_start_at and break_end_at must be provided together")
    if break_start_at is None or break_end_at is None:
        return
    if not (open_at < break_start_at < break_end_at < close_at):
        raise TradingCalendarDatasetError("break window must be within open and close")


def _normalize_session_datetime(
    field_name: str,
    value: datetime | None,
    trade_date: date,
    zone: ZoneInfo,
) -> datetime | None:
    if value is None:
        return None
    _require_aware_datetime(field_name, value)
    if getattr(value.tzinfo, "key", None) != zone.key:
        raise TradingCalendarDatasetError(f"{field_name} timezone must be {zone.key}")
    if value.astimezone(zone).date() != trade_date:
        raise TradingCalendarDatasetError(f"{field_name} local date must equal trade_date")
    return value


def _require_date(field_name: str, value: object) -> None:
    if type(value) is not date:
        raise TradingCalendarDatasetError(f"{field_name} must be a date")


def _require_aware_datetime(field_name: str, value: object) -> None:
    if type(value) is not datetime or value.tzinfo is None or value.utcoffset() is None:
        raise TradingCalendarDatasetError(f"{field_name} must be timezone-aware")


def _required_string(field_name: str, value: object | None) -> str:
    if type(value) is not str:
        raise TradingCalendarDatasetError(f"{field_name} is required")
    normalized = value.strip()
    if not normalized:
        raise TradingCalendarDatasetError(f"{field_name} is required")
    return normalized


def _optional_string(value: object | None) -> str | None:
    if value is None:
        return None
    if type(value) is not str:
        raise TradingCalendarDatasetError("optional string value must be a string")
    normalized = value.strip()
    return normalized or None


__all__ = [
    "TRADING_CALENDAR_CONTENT_TYPE",
    "TRADING_CALENDAR_SCHEMA_NAME",
    "TRADING_CALENDAR_SCHEMA_VERSION",
    "MarketSession",
    "TradingCalendarDataset",
    "TradingCalendarDatasetError",
    "TradingSessionStatus",
    "market_timezone",
]
