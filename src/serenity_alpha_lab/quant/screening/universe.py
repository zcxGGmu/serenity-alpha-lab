from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import StrEnum
from types import MappingProxyType

from serenity_alpha_lab.datasets.instrument_master import (
    InstrumentListingStatus,
    InstrumentMasterDataset,
    InstrumentMasterRecord,
)
from serenity_alpha_lab.datasets.raw_daily_bars import RawDailyBarsDataset
from serenity_alpha_lab.datasets.trading_calendar import TradingCalendarDataset
from serenity_alpha_lab.domain.artifacts import (
    ArtifactManifest,
    ArtifactRetentionTier,
    ArtifactStore,
)
from serenity_alpha_lab.domain.instruments import InstrumentId, Market


HISTORICAL_UNIVERSE_CONTRACT_VERSION = "quant.historical_universe@1.0.0"
HISTORICAL_UNIVERSE_SCHEMA_NAME = "quant.historical_universe_snapshot"
HISTORICAL_UNIVERSE_SCHEMA_VERSION = "1.0.0"
HISTORICAL_UNIVERSE_CONTENT_TYPE = "application/vnd.serenity.quant.historical-universe+json"
UNIVERSE_RULE_VERSION = "1.0.0"

_DATASET_VERSION_RE = re.compile(r"^dsv_[0-9a-f]{32,64}$")
_REQUIRED_DATASET_VERSION_KEYS = (
    "instrument_master",
    "trading_calendar",
    "raw_daily_bars",
    "instrument_trade_status",
)


class HistoricalUniverseError(ValueError):
    """Raised when Historical Universe inputs violate the L0 universe contract."""


class UniverseRuleSeverity(StrEnum):
    HARD_EXCLUDE = "hard_exclude"
    WARNING = "warning"


class InstrumentTradeStatus(StrEnum):
    TRADABLE = "tradable"
    SUSPENDED = "suspended"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class UniverseDataEvidence:
    dataset_name: str
    dataset_version: str
    source_bronze_artifact_id: str
    field_name: str
    observed_value: object

    def __post_init__(self) -> None:
        object.__setattr__(self, "dataset_name", _required_string("dataset_name", self.dataset_name))
        object.__setattr__(
            self,
            "dataset_version",
            _validate_dataset_version(self.dataset_version, field_name="dataset_version"),
        )
        object.__setattr__(
            self,
            "source_bronze_artifact_id",
            _required_string("source_bronze_artifact_id", self.source_bronze_artifact_id),
        )
        object.__setattr__(self, "field_name", _required_string("field_name", self.field_name))

    def to_record(self) -> dict[str, object]:
        return {
            "dataset_name": self.dataset_name,
            "dataset_version": self.dataset_version,
            "source_bronze_artifact_id": self.source_bronze_artifact_id,
            "field_name": self.field_name,
            "observed_value": self.observed_value,
        }


@dataclass(frozen=True, slots=True)
class UniverseInstrumentTradeStatus:
    instrument_id: str
    trade_date: date
    status: InstrumentTradeStatus | str
    source_bronze_artifact_id: str
    reason: str | None = None

    def __post_init__(self) -> None:
        instrument = _coerce_instrument_id(self.instrument_id)
        _require_date("trade_date", self.trade_date)
        object.__setattr__(self, "instrument_id", instrument.canonical)
        object.__setattr__(self, "status", InstrumentTradeStatus(self.status))
        object.__setattr__(
            self,
            "source_bronze_artifact_id",
            _required_string("source_bronze_artifact_id", self.source_bronze_artifact_id),
        )
        object.__setattr__(self, "reason", _optional_string(self.reason))

    @property
    def key(self) -> tuple[str, date]:
        return (self.instrument_id, self.trade_date)

    def to_record(self) -> dict[str, object]:
        return {
            "instrument_id": self.instrument_id,
            "trade_date": self.trade_date.isoformat(),
            "status": self.status.value,
            "reason": self.reason,
            "source_bronze_artifact_id": self.source_bronze_artifact_id,
        }


@dataclass(frozen=True, slots=True)
class UniverseDefinition:
    definition_id: str
    semantic_version: str
    markets: Sequence[Market | str]
    dataset_versions: Mapping[str, str]
    created_at: datetime
    created_by_run_id: str
    min_listing_trading_days: int = 1
    exclude_st: bool = True
    exclude_suspended: bool = True
    require_daily_bar: bool = True
    contract_version: str = HISTORICAL_UNIVERSE_CONTRACT_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "definition_id", _required_string("definition_id", self.definition_id))
        object.__setattr__(self, "semantic_version", _required_string("semantic_version", self.semantic_version))
        object.__setattr__(self, "contract_version", _required_string("contract_version", self.contract_version))
        _require_aware_datetime("created_at", self.created_at)
        object.__setattr__(
            self,
            "created_by_run_id",
            _required_string("created_by_run_id", self.created_by_run_id),
        )
        markets = tuple(Market(market) for market in self.markets)
        if not markets:
            raise HistoricalUniverseError("markets are required")
        if len(set(markets)) != len(markets):
            raise HistoricalUniverseError("markets cannot contain duplicates")
        object.__setattr__(self, "markets", tuple(sorted(markets, key=lambda market: market.value)))

        if type(self.min_listing_trading_days) is not int or self.min_listing_trading_days < 0:
            raise HistoricalUniverseError("min_listing_trading_days must be a non-negative integer")
        for flag_name in ("exclude_st", "exclude_suspended", "require_daily_bar"):
            if type(getattr(self, flag_name)) is not bool:
                raise HistoricalUniverseError(f"{flag_name} must be a bool")

        dataset_versions = _normalize_dataset_versions(self.dataset_versions)
        object.__setattr__(self, "dataset_versions", MappingProxyType(dataset_versions))

    def to_record(self) -> dict[str, object]:
        return {
            "contract_version": self.contract_version,
            "definition_id": self.definition_id,
            "semantic_version": self.semantic_version,
            "markets": [market.value for market in self.markets],
            "dataset_versions": dict(self.dataset_versions),
            "min_listing_trading_days": self.min_listing_trading_days,
            "exclude_st": self.exclude_st,
            "exclude_suspended": self.exclude_suspended,
            "require_daily_bar": self.require_daily_bar,
            "created_at": self.created_at.isoformat(),
            "created_by_run_id": self.created_by_run_id,
        }


@dataclass(frozen=True, slots=True)
class UniverseMember:
    instrument_id: str
    market: Market | str
    exchange: str
    listed_on: date
    listing_trading_days: int
    evidence: Sequence[UniverseDataEvidence]

    def __post_init__(self) -> None:
        instrument = _coerce_instrument_id(self.instrument_id)
        object.__setattr__(self, "instrument_id", instrument.canonical)
        object.__setattr__(self, "market", Market(self.market))
        object.__setattr__(self, "exchange", _required_string("exchange", self.exchange))
        _require_date("listed_on", self.listed_on)
        if type(self.listing_trading_days) is not int or self.listing_trading_days < 0:
            raise HistoricalUniverseError("listing_trading_days must be a non-negative integer")
        evidence = _normalize_evidence(self.evidence)
        object.__setattr__(self, "evidence", evidence)

    def to_record(self) -> dict[str, object]:
        return {
            "instrument_id": self.instrument_id,
            "market": self.market.value,
            "exchange": self.exchange,
            "listed_on": self.listed_on.isoformat(),
            "listing_trading_days": self.listing_trading_days,
            "evidence": [item.to_record() for item in self.evidence],
        }


@dataclass(frozen=True, slots=True)
class UniverseExclusion:
    instrument_id: str
    rule_id: str
    reason: str
    evidence: Sequence[UniverseDataEvidence]
    rule_version: str = UNIVERSE_RULE_VERSION
    severity: UniverseRuleSeverity | str = UniverseRuleSeverity.HARD_EXCLUDE

    def __post_init__(self) -> None:
        instrument = _coerce_instrument_id(self.instrument_id)
        object.__setattr__(self, "instrument_id", instrument.canonical)
        object.__setattr__(self, "rule_id", _required_string("rule_id", self.rule_id))
        object.__setattr__(self, "rule_version", _required_string("rule_version", self.rule_version))
        object.__setattr__(self, "severity", UniverseRuleSeverity(self.severity))
        object.__setattr__(self, "reason", _required_string("reason", self.reason))
        evidence = _normalize_evidence(self.evidence)
        if not evidence:
            raise HistoricalUniverseError("universe exclusion evidence is required")
        object.__setattr__(self, "evidence", evidence)

    def to_record(self) -> dict[str, object]:
        return {
            "instrument_id": self.instrument_id,
            "rule_id": self.rule_id,
            "rule_version": self.rule_version,
            "severity": self.severity.value,
            "reason": self.reason,
            "evidence": [item.to_record() for item in self.evidence],
        }


@dataclass(frozen=True, slots=True)
class UniverseSnapshot:
    definition: UniverseDefinition
    as_of: date
    members: Sequence[UniverseMember]
    exclusions: Sequence[UniverseExclusion]
    created_at: datetime
    trace_id: str | None = None
    run_id: str | None = None
    stage_id: str | None = None
    universe_version_id: str | None = None
    _markets: tuple[Market, ...] = field(init=False, repr=False, compare=False)
    _dataset_versions: Mapping[str, str] = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if type(self.definition) is not UniverseDefinition:
            raise HistoricalUniverseError("definition must be a UniverseDefinition")
        _require_date("as_of", self.as_of)
        _require_aware_datetime("created_at", self.created_at)
        object.__setattr__(self, "trace_id", _optional_string(self.trace_id))
        object.__setattr__(self, "run_id", _optional_string(self.run_id))
        object.__setattr__(self, "stage_id", _optional_string(self.stage_id))
        object.__setattr__(self, "_markets", self.definition.markets)
        object.__setattr__(self, "_dataset_versions", self.definition.dataset_versions)

        members = tuple(self.members)
        exclusions = tuple(self.exclusions)
        for member in members:
            if type(member) is not UniverseMember:
                raise HistoricalUniverseError("members must contain UniverseMember values")
        for exclusion in exclusions:
            if type(exclusion) is not UniverseExclusion:
                raise HistoricalUniverseError("exclusions must contain UniverseExclusion values")
        object.__setattr__(self, "members", tuple(sorted(members, key=lambda item: item.instrument_id)))
        object.__setattr__(self, "exclusions", tuple(sorted(exclusions, key=lambda item: item.instrument_id)))

        universe_version_id = self.universe_version_id
        if universe_version_id is None:
            universe_version_id = _derive_universe_version_id(self._version_payload())
        else:
            universe_version_id = _validate_dataset_version(universe_version_id, field_name="universe_version_id")
        object.__setattr__(self, "universe_version_id", universe_version_id)

    @property
    def markets(self) -> tuple[Market, ...]:
        return self._markets

    @property
    def dataset_versions(self) -> Mapping[str, str]:
        return self._dataset_versions

    @property
    def member_count(self) -> int:
        return len(self.members)

    @property
    def exclusion_count(self) -> int:
        return len(self.exclusions)

    def to_json_bytes(self) -> bytes:
        return json.dumps(
            self.to_record(),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")

    def to_record(self) -> dict[str, object]:
        payload = self._version_payload()
        payload["universe_version_id"] = self.universe_version_id
        return payload

    def _version_payload(self) -> dict[str, object]:
        return {
            "schema_name": HISTORICAL_UNIVERSE_SCHEMA_NAME,
            "schema_version": HISTORICAL_UNIVERSE_SCHEMA_VERSION,
            "contract_version": self.definition.contract_version,
            "definition": self.definition.to_record(),
            "definition_id": self.definition.definition_id,
            "definition_version": self.definition.semantic_version,
            "as_of": self.as_of.isoformat(),
            "markets": [market.value for market in self.markets],
            "dataset_versions": dict(self.dataset_versions),
            "created_at": self.created_at.isoformat(),
            "trace_id": self.trace_id,
            "run_id": self.run_id,
            "stage_id": self.stage_id,
            "member_count": self.member_count,
            "exclusion_count": self.exclusion_count,
            "members": [member.to_record() for member in self.members],
            "exclusions": [exclusion.to_record() for exclusion in self.exclusions],
        }

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
            schema_name=HISTORICAL_UNIVERSE_SCHEMA_NAME,
            schema_version=HISTORICAL_UNIVERSE_SCHEMA_VERSION,
            content_type=HISTORICAL_UNIVERSE_CONTENT_TYPE,
            produced_by_run_id=run_id,
            produced_by_stage_id=stage_id,
            retention_tier=retention_tier,
            created_at=self.created_at,
        )


@dataclass(frozen=True, slots=True)
class _DailyBarAvailability:
    instruments: frozenset[str]
    source_bronze_artifact_id: str


def build_historical_universe_snapshot(
    definition: UniverseDefinition,
    *,
    as_of: date,
    instrument_master: InstrumentMasterDataset,
    trading_calendar: TradingCalendarDataset,
    raw_daily_bars: RawDailyBarsDataset | None = None,
    trade_statuses: Iterable[UniverseInstrumentTradeStatus] = (),
    created_at: datetime,
    trace_id: str | None = None,
    run_id: str | None = None,
    stage_id: str | None = None,
) -> UniverseSnapshot:
    if type(definition) is not UniverseDefinition:
        raise HistoricalUniverseError("definition must be a UniverseDefinition")
    if type(instrument_master) is not InstrumentMasterDataset:
        raise HistoricalUniverseError("instrument_master must be an InstrumentMasterDataset")
    if type(trading_calendar) is not TradingCalendarDataset:
        raise HistoricalUniverseError("trading_calendar must be a TradingCalendarDataset")
    if definition.require_daily_bar and type(raw_daily_bars) is not RawDailyBarsDataset:
        raise HistoricalUniverseError("raw_daily_bars must be provided when require_daily_bar is true")
    _require_date("as_of", as_of)
    _require_aware_datetime("created_at", created_at)
    _validate_markets_are_trading(definition, trading_calendar, as_of)

    status_by_key = _index_trade_statuses(trade_statuses)
    bar_availability = _bar_availability_by_market(definition, raw_daily_bars, as_of)
    members: list[UniverseMember] = []
    exclusions: list[UniverseExclusion] = []

    for market in definition.markets:
        records = instrument_master.query_as_of(as_of, market=market, include_inactive=True)
        for record in sorted(records, key=lambda item: item.instrument_id.canonical):
            exclusion = _first_exclusion(
                definition=definition,
                record=record,
                as_of=as_of,
                trading_calendar=trading_calendar,
                status=status_by_key.get((record.instrument_id.canonical, as_of)),
                bar_availability=bar_availability.get(market, _DailyBarAvailability(frozenset(), "")),
            )
            if exclusion is not None:
                exclusions.append(exclusion)
                continue
            members.append(_member_from_record(definition, record, as_of, trading_calendar))

    return UniverseSnapshot(
        definition=definition,
        as_of=as_of,
        members=tuple(members),
        exclusions=tuple(exclusions),
        created_at=created_at,
        trace_id=trace_id,
        run_id=run_id,
        stage_id=stage_id,
    )


def publish_historical_universe_snapshot(
    snapshot: UniverseSnapshot,
    artifact_store: ArtifactStore,
    *,
    produced_by_run_id: str | None = None,
    produced_by_stage_id: str | None = None,
    retention_tier: ArtifactRetentionTier = ArtifactRetentionTier.STANDARD,
) -> ArtifactManifest:
    if type(snapshot) is not UniverseSnapshot:
        raise HistoricalUniverseError("snapshot must be a UniverseSnapshot")
    return snapshot.publish(
        artifact_store,
        produced_by_run_id=produced_by_run_id,
        produced_by_stage_id=produced_by_stage_id,
        retention_tier=retention_tier,
    )


def _first_exclusion(
    *,
    definition: UniverseDefinition,
    record: InstrumentMasterRecord,
    as_of: date,
    trading_calendar: TradingCalendarDataset,
    status: UniverseInstrumentTradeStatus | None,
    bar_availability: _DailyBarAvailability,
) -> UniverseExclusion | None:
    master_version = definition.dataset_versions["instrument_master"]
    if record.listing_status is not InstrumentListingStatus.ACTIVE:
        return _exclusion(
            record,
            "listing_status_active",
            f"listing_status is {record.listing_status.value}",
            _master_evidence(master_version, record, "listing_status", record.listing_status.value),
        )
    if record.delisted_on is not None and record.delisted_on <= as_of:
        return _exclusion(
            record,
            "listing_status_active",
            f"delisted_on is {record.delisted_on.isoformat()}",
            _master_evidence(master_version, record, "delisted_on", record.delisted_on.isoformat()),
        )
    listing_days = _listing_trading_days(record, as_of, trading_calendar)
    if listing_days < definition.min_listing_trading_days:
        return _exclusion(
            record,
            "min_listing_trading_days",
            f"listing trading days {listing_days} < {definition.min_listing_trading_days}",
            (
                _master_evidence(master_version, record, "listed_on", record.listed_on.isoformat()),
                _calendar_evidence(definition, trading_calendar, "listing_trading_days", listing_days),
            ),
        )
    if definition.exclude_st and record.is_st:
        return _exclusion(
            record,
            "not_st",
            "instrument is marked ST as of decision date",
            _master_evidence(master_version, record, "is_st", record.is_st),
        )
    if definition.exclude_suspended and status is not None and status.status is InstrumentTradeStatus.SUSPENDED:
        return _exclusion(
            record,
            "not_suspended",
            status.reason or "instrument is suspended as of decision date",
            UniverseDataEvidence(
                dataset_name="instrument_trade_status",
                dataset_version=definition.dataset_versions["instrument_trade_status"],
                source_bronze_artifact_id=status.source_bronze_artifact_id,
                field_name="status",
                observed_value=status.status.value,
            ),
        )
    if definition.require_daily_bar and record.instrument_id.canonical not in bar_availability.instruments:
        return _exclusion(
            record,
            "daily_bar_available",
            "raw daily bar missing for decision date",
            UniverseDataEvidence(
                dataset_name="raw_daily_bars",
                dataset_version=definition.dataset_versions["raw_daily_bars"],
                source_bronze_artifact_id=bar_availability.source_bronze_artifact_id
                or "dataset_version:" + definition.dataset_versions["raw_daily_bars"],
                field_name="instrument_id",
                observed_value=f"{record.instrument_id.canonical} missing on {as_of.isoformat()}",
            ),
        )
    return None


def _member_from_record(
    definition: UniverseDefinition,
    record: InstrumentMasterRecord,
    as_of: date,
    trading_calendar: TradingCalendarDataset,
) -> UniverseMember:
    listing_days = _listing_trading_days(record, as_of, trading_calendar)
    return UniverseMember(
        instrument_id=record.instrument_id.canonical,
        market=record.market,
        exchange=record.exchange.value,
        listed_on=record.listed_on,
        listing_trading_days=listing_days,
        evidence=(
            _master_evidence(
                definition.dataset_versions["instrument_master"],
                record,
                "listing_status",
                record.listing_status.value,
            ),
            _calendar_evidence(definition, trading_calendar, "listing_trading_days", listing_days),
        ),
    )


def _exclusion(
    record: InstrumentMasterRecord,
    rule_id: str,
    reason: str,
    evidence: UniverseDataEvidence | Sequence[UniverseDataEvidence],
) -> UniverseExclusion:
    if type(evidence) is UniverseDataEvidence:
        evidence_values = (evidence,)
    else:
        evidence_values = tuple(evidence)
    return UniverseExclusion(
        instrument_id=record.instrument_id.canonical,
        rule_id=rule_id,
        reason=reason,
        evidence=evidence_values,
    )


def _master_evidence(
    dataset_version: str,
    record: InstrumentMasterRecord,
    field_name: str,
    observed_value: object,
) -> UniverseDataEvidence:
    return UniverseDataEvidence(
        dataset_name="instrument_master",
        dataset_version=dataset_version,
        source_bronze_artifact_id=record.source_bronze_artifact_id,
        field_name=field_name,
        observed_value=observed_value,
    )


def _calendar_evidence(
    definition: UniverseDefinition,
    trading_calendar: TradingCalendarDataset,
    field_name: str,
    observed_value: object,
) -> UniverseDataEvidence:
    return UniverseDataEvidence(
        dataset_name="trading_calendar",
        dataset_version=definition.dataset_versions["trading_calendar"],
        source_bronze_artifact_id=";".join(trading_calendar.source_bronze_artifact_ids),
        field_name=field_name,
        observed_value=observed_value,
    )


def _listing_trading_days(
    record: InstrumentMasterRecord,
    as_of: date,
    trading_calendar: TradingCalendarDataset,
) -> int:
    if record.listed_on > as_of:
        return 0
    return len(trading_calendar.trading_days(record.market, record.listed_on, as_of))


def _validate_markets_are_trading(
    definition: UniverseDefinition,
    trading_calendar: TradingCalendarDataset,
    as_of: date,
) -> None:
    for market in definition.markets:
        try:
            is_trading_day = trading_calendar.is_trading_day(market, as_of)
        except Exception as exc:
            raise HistoricalUniverseError(
                f"as_of must exist in Trading Calendar: {market.value} {as_of.isoformat()}"
            ) from exc
        if not is_trading_day:
            raise HistoricalUniverseError(f"as_of must be a trading day: {market.value} {as_of.isoformat()}")


def _bar_availability_by_market(
    definition: UniverseDefinition,
    raw_daily_bars: RawDailyBarsDataset | None,
    as_of: date,
) -> Mapping[Market, _DailyBarAvailability]:
    if raw_daily_bars is None:
        return MappingProxyType({})
    values: dict[Market, _DailyBarAvailability] = {}
    for market in definition.markets:
        bars = raw_daily_bars.bars_for_market(market, as_of)
        source_ids = {bar.source_bronze_artifact_id for bar in bars}
        if not source_ids:
            source_ids = set(raw_daily_bars.source_bronze_artifact_ids)
        values[market] = _DailyBarAvailability(
            instruments=frozenset(bar.instrument_id.canonical for bar in bars),
            source_bronze_artifact_id=";".join(sorted(source_ids)),
        )
    return MappingProxyType(values)


def _index_trade_statuses(
    statuses: Iterable[UniverseInstrumentTradeStatus],
) -> Mapping[tuple[str, date], UniverseInstrumentTradeStatus]:
    indexed: dict[tuple[str, date], UniverseInstrumentTradeStatus] = {}
    for status in statuses:
        if type(status) is not UniverseInstrumentTradeStatus:
            raise HistoricalUniverseError("trade_statuses must contain UniverseInstrumentTradeStatus values")
        if status.key in indexed:
            instrument_id, trade_date = status.key
            raise HistoricalUniverseError(f"duplicate trade status: {instrument_id} {trade_date.isoformat()}")
        indexed[status.key] = status
    return MappingProxyType(indexed)


def _normalize_dataset_versions(dataset_versions: Mapping[str, str]) -> dict[str, str]:
    normalized: dict[str, str] = {}
    for key, value in dataset_versions.items():
        normalized[_required_string("dataset version key", key)] = _validate_dataset_version(
            value,
            field_name=f"dataset_versions[{key}]",
        )
    for required_key in _REQUIRED_DATASET_VERSION_KEYS:
        if required_key not in normalized:
            raise HistoricalUniverseError(f"required dataset version missing: {required_key}")
    return dict(sorted(normalized.items()))


def _normalize_evidence(evidence: Sequence[UniverseDataEvidence]) -> tuple[UniverseDataEvidence, ...]:
    values = tuple(evidence)
    for item in values:
        if type(item) is not UniverseDataEvidence:
            raise HistoricalUniverseError("evidence must contain UniverseDataEvidence values")
    return values


def _derive_universe_version_id(payload: Mapping[str, object]) -> str:
    content = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return f"dsv_{hashlib.sha256(content).hexdigest()[:32]}"


def _coerce_instrument_id(value: InstrumentId | str) -> InstrumentId:
    if type(value) is InstrumentId:
        return value
    if type(value) is str:
        try:
            return InstrumentId.parse(value)
        except Exception as exc:
            raise HistoricalUniverseError(f"instrument_id is invalid: {value!r}") from exc
    raise HistoricalUniverseError("instrument_id must be an InstrumentId or canonical string")


def _validate_dataset_version(value: object, *, field_name: str) -> str:
    text = _required_string(field_name, value)
    if text == "latest" or not _DATASET_VERSION_RE.fullmatch(text):
        raise HistoricalUniverseError(f"{field_name} must be a concrete Dataset Version id")
    return text


def _require_date(field_name: str, value: object) -> None:
    if type(value) is not date:
        raise HistoricalUniverseError(f"{field_name} must be a date")


def _require_aware_datetime(field_name: str, value: object) -> None:
    if type(value) is not datetime or value.tzinfo is None or value.utcoffset() is None:
        raise HistoricalUniverseError(f"{field_name} must be timezone-aware")


def _required_string(field_name: str, value: object | None) -> str:
    if type(value) is not str:
        raise HistoricalUniverseError(f"{field_name} is required")
    normalized = value.strip()
    if not normalized:
        raise HistoricalUniverseError(f"{field_name} is required")
    return normalized


def _optional_string(value: object | None) -> str | None:
    if value is None:
        return None
    if type(value) is not str:
        raise HistoricalUniverseError("optional string value must be a string")
    normalized = value.strip()
    return normalized or None


__all__ = [
    "HISTORICAL_UNIVERSE_CONTENT_TYPE",
    "HISTORICAL_UNIVERSE_CONTRACT_VERSION",
    "HISTORICAL_UNIVERSE_SCHEMA_NAME",
    "HISTORICAL_UNIVERSE_SCHEMA_VERSION",
    "InstrumentTradeStatus",
    "HistoricalUniverseError",
    "UniverseDataEvidence",
    "UniverseDefinition",
    "UniverseExclusion",
    "UniverseInstrumentTradeStatus",
    "UniverseMember",
    "UniverseRuleSeverity",
    "UniverseSnapshot",
    "build_historical_universe_snapshot",
    "publish_historical_universe_snapshot",
]
