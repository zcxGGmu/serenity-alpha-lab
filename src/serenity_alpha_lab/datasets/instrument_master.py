from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum

from serenity_alpha_lab.domain.artifacts import (
    ArtifactManifest,
    ArtifactRetentionTier,
    ArtifactStore,
)
from serenity_alpha_lab.domain.instruments import (
    AssetType,
    Exchange,
    InstrumentId,
    Market,
    ProviderSymbolMapping,
)


INSTRUMENT_MASTER_SCHEMA_NAME = "dataset.instrument_master"
INSTRUMENT_MASTER_SCHEMA_VERSION = "1.0.0"
INSTRUMENT_MASTER_CONTENT_TYPE = "application/vnd.serenity.dataset.instrument-master+json"


class InstrumentMasterDatasetError(ValueError):
    """Raised when instrument master records violate the Dataset contract."""


class InstrumentListingStatus(StrEnum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DELISTED = "delisted"
    PRELISTED = "prelisted"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class IndustryClassification:
    system: str
    version: str
    level1: str
    valid_from: date
    level2: str | None = None
    level3: str | None = None
    valid_to: date | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "system", _required_string("industry system", self.system))
        object.__setattr__(self, "version", _required_string("industry version", self.version))
        object.__setattr__(self, "level1", _required_string("industry level1", self.level1))
        object.__setattr__(self, "level2", _optional_string(self.level2))
        object.__setattr__(self, "level3", _optional_string(self.level3))
        _require_date("valid_from", self.valid_from)
        _validate_validity_window(self.valid_from, self.valid_to, "industry validity")

    def is_effective_on(self, as_of: date) -> bool:
        _require_date("as_of", as_of)
        return _contains_date(self.valid_from, self.valid_to, as_of)

    def to_record(self) -> dict[str, object]:
        return {
            "system": self.system,
            "version": self.version,
            "level1": self.level1,
            "level2": self.level2,
            "level3": self.level3,
            "valid_from": self.valid_from.isoformat(),
            "valid_to": self.valid_to.isoformat() if self.valid_to else None,
        }


@dataclass(frozen=True, slots=True)
class ProviderSymbolValidity:
    mapping: ProviderSymbolMapping
    valid_from: date
    source_bronze_artifact_id: str
    valid_to: date | None = None

    def __post_init__(self) -> None:
        if type(self.mapping) is not ProviderSymbolMapping:
            raise InstrumentMasterDatasetError("provider mapping must be a ProviderSymbolMapping")
        _require_date("valid_from", self.valid_from)
        _validate_validity_window(self.valid_from, self.valid_to, "provider mapping validity")
        object.__setattr__(
            self,
            "source_bronze_artifact_id",
            _required_string("source_bronze_artifact_id", self.source_bronze_artifact_id),
        )

    @property
    def provider(self) -> str:
        return self.mapping.provider

    @property
    def symbol(self) -> str:
        return self.mapping.symbol

    @property
    def instrument_id(self) -> InstrumentId:
        return self.mapping.instrument_id

    def is_effective_on(self, as_of: date) -> bool:
        _require_date("as_of", as_of)
        return _contains_date(self.valid_from, self.valid_to, as_of)

    def to_record(self) -> dict[str, object]:
        return {
            "provider": self.provider,
            "symbol": self.symbol,
            "instrument_id": self.instrument_id.canonical,
            "valid_from": self.valid_from.isoformat(),
            "valid_to": self.valid_to.isoformat() if self.valid_to else None,
            "source_bronze_artifact_id": self.source_bronze_artifact_id,
        }


@dataclass(frozen=True, slots=True)
class InstrumentMasterRecord:
    instrument_id: InstrumentId
    name: str
    currency: str
    listing_status: InstrumentListingStatus | str
    listed_on: date
    delisted_on: date | None
    is_st: bool
    board: str
    industries: Sequence[IndustryClassification]
    provider_mappings: Sequence[ProviderSymbolValidity]
    valid_from: date
    source_bronze_artifact_id: str
    valid_to: date | None = None

    def __post_init__(self) -> None:
        if type(self.instrument_id) is not InstrumentId:
            raise InstrumentMasterDatasetError("instrument_id must be an InstrumentId")
        object.__setattr__(self, "name", _required_string("name", self.name))
        object.__setattr__(self, "currency", _required_string("currency", self.currency).upper())
        object.__setattr__(self, "listing_status", InstrumentListingStatus(self.listing_status))
        _require_date("listed_on", self.listed_on)
        if self.delisted_on is not None:
            _require_date("delisted_on", self.delisted_on)
            if self.delisted_on < self.listed_on:
                raise InstrumentMasterDatasetError("delisted_on cannot be before listed_on")
        if type(self.is_st) is not bool:
            raise InstrumentMasterDatasetError("is_st must be a bool")
        object.__setattr__(self, "board", _required_string("board", self.board))
        object.__setattr__(
            self,
            "source_bronze_artifact_id",
            _required_string("source_bronze_artifact_id", self.source_bronze_artifact_id),
        )
        _require_date("valid_from", self.valid_from)
        _validate_validity_window(self.valid_from, self.valid_to, "instrument validity")

        industries = tuple(self.industries)
        for industry in industries:
            if type(industry) is not IndustryClassification:
                raise InstrumentMasterDatasetError("industries must contain IndustryClassification records")
        object.__setattr__(self, "industries", industries)

        provider_mappings = tuple(self.provider_mappings)
        for provider_mapping in provider_mappings:
            if type(provider_mapping) is not ProviderSymbolValidity:
                raise InstrumentMasterDatasetError("provider_mappings must contain ProviderSymbolValidity records")
            if provider_mapping.instrument_id != self.instrument_id:
                raise InstrumentMasterDatasetError("provider mapping instrument_id must match record instrument_id")
        _validate_provider_mapping_windows(provider_mappings)
        object.__setattr__(self, "provider_mappings", provider_mappings)

    @property
    def market(self) -> Market:
        return self.instrument_id.market

    @property
    def exchange(self) -> Exchange:
        return self.instrument_id.exchange

    @property
    def asset_type(self) -> AssetType:
        return self.instrument_id.asset_type

    @property
    def active_industries(self) -> tuple[IndustryClassification, ...]:
        return tuple(self.industries)

    def is_effective_on(self, as_of: date) -> bool:
        _require_date("as_of", as_of)
        return _contains_date(self.valid_from, self.valid_to, as_of)

    def provider_mapping_as_of(self, provider: str, as_of: date) -> ProviderSymbolValidity | None:
        provider_id = _required_string("provider", provider).lower()
        matches = [
            mapping
            for mapping in self.provider_mappings
            if mapping.provider.lower() == provider_id and mapping.is_effective_on(as_of)
        ]
        if len(matches) > 1:
            raise InstrumentMasterDatasetError(
                f"Multiple provider mappings for {self.instrument_id.canonical} provider {provider_id}"
            )
        return matches[0] if matches else None

    def to_record(self) -> dict[str, object]:
        return {
            "instrument_id": self.instrument_id.canonical,
            "market": self.market.value,
            "exchange": self.exchange.value,
            "symbol": self.instrument_id.symbol,
            "asset_type": self.asset_type.value,
            "name": self.name,
            "currency": self.currency,
            "listing_status": self.listing_status.value,
            "listed_on": self.listed_on.isoformat(),
            "delisted_on": self.delisted_on.isoformat() if self.delisted_on else None,
            "is_st": self.is_st,
            "board": self.board,
            "industries": [industry.to_record() for industry in self.industries],
            "provider_mappings": [mapping.to_record() for mapping in self.provider_mappings],
            "valid_from": self.valid_from.isoformat(),
            "valid_to": self.valid_to.isoformat() if self.valid_to else None,
            "source_bronze_artifact_id": self.source_bronze_artifact_id,
        }


@dataclass(frozen=True, slots=True)
class InstrumentMasterDataset:
    records: Sequence[InstrumentMasterRecord]
    created_at: datetime
    trace_id: str | None = None
    run_id: str | None = None
    stage_id: str | None = None

    @classmethod
    def from_records(
        cls,
        records: Iterable[InstrumentMasterRecord],
        *,
        created_at: datetime,
        trace_id: str | None = None,
        run_id: str | None = None,
        stage_id: str | None = None,
    ) -> InstrumentMasterDataset:
        return cls(
            records=tuple(records),
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

        records = tuple(self.records)
        if not records:
            raise InstrumentMasterDatasetError("instrument master records are required")
        for record in records:
            if type(record) is not InstrumentMasterRecord:
                raise InstrumentMasterDatasetError("records must contain InstrumentMasterRecord values")
        _validate_record_keys_and_windows(records)
        object.__setattr__(
            self,
            "records",
            tuple(sorted(records, key=lambda record: (record.instrument_id.canonical, record.valid_from))),
        )

    def query_as_of(
        self,
        as_of: date,
        *,
        market: Market | str | None = None,
        include_inactive: bool = True,
    ) -> tuple[InstrumentMasterRecord, ...]:
        _require_date("as_of", as_of)
        market_filter = Market(market) if market is not None else None
        records = [
            record
            for record in self.records
            if record.is_effective_on(as_of)
            and (market_filter is None or record.market is market_filter)
            and (include_inactive or record.listing_status is InstrumentListingStatus.ACTIVE)
        ]
        return tuple(records)

    def get(self, instrument_id: InstrumentId | str, *, as_of: date) -> InstrumentMasterRecord:
        instrument = _coerce_instrument_id(instrument_id)
        matches = [record for record in self.query_as_of(as_of) if record.instrument_id == instrument]
        if not matches:
            raise InstrumentMasterDatasetError(f"Instrument not found as of {as_of.isoformat()}: {instrument.canonical}")
        if len(matches) > 1:
            raise InstrumentMasterDatasetError(
                f"Multiple instrument records found as of {as_of.isoformat()}: {instrument.canonical}"
            )
        return matches[0]

    def provider_mapping_as_of(
        self,
        instrument_id: InstrumentId | str,
        *,
        provider: str,
        as_of: date,
    ) -> ProviderSymbolValidity:
        record = self.get(instrument_id, as_of=as_of)
        mapping = record.provider_mapping_as_of(provider, as_of)
        if mapping is None:
            raise InstrumentMasterDatasetError(
                f"Provider mapping not found as of {as_of.isoformat()}: "
                f"{record.instrument_id.canonical} {provider}"
            )
        return mapping

    def to_json_bytes(self) -> bytes:
        payload = {
            "schema_name": INSTRUMENT_MASTER_SCHEMA_NAME,
            "schema_version": INSTRUMENT_MASTER_SCHEMA_VERSION,
            "created_at": self.created_at.isoformat(),
            "trace_id": self.trace_id,
            "run_id": self.run_id,
            "stage_id": self.stage_id,
            "record_count": len(self.records),
            "source_bronze_artifact_ids": sorted(self.source_bronze_artifact_ids),
            "records": [record.to_record() for record in self.records],
        }
        return json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")

    @property
    def source_bronze_artifact_ids(self) -> tuple[str, ...]:
        source_ids: set[str] = set()
        for record in self.records:
            source_ids.add(record.source_bronze_artifact_id)
            source_ids.update(mapping.source_bronze_artifact_id for mapping in record.provider_mappings)
        return tuple(sorted(source_ids))

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
            schema_name=INSTRUMENT_MASTER_SCHEMA_NAME,
            schema_version=INSTRUMENT_MASTER_SCHEMA_VERSION,
            content_type=INSTRUMENT_MASTER_CONTENT_TYPE,
            produced_by_run_id=run_id,
            produced_by_stage_id=stage_id,
            retention_tier=retention_tier,
            created_at=self.created_at,
        )


def _coerce_instrument_id(value: InstrumentId | str) -> InstrumentId:
    if type(value) is InstrumentId:
        return value
    if type(value) is str:
        return InstrumentId.parse(value)
    raise InstrumentMasterDatasetError("instrument_id must be an InstrumentId or canonical string")


def _validate_record_keys_and_windows(records: Sequence[InstrumentMasterRecord]) -> None:
    keys: set[tuple[str, date]] = set()
    by_instrument: dict[str, list[InstrumentMasterRecord]] = defaultdict(list)
    for record in records:
        key = (record.instrument_id.canonical, record.valid_from)
        if key in keys:
            raise InstrumentMasterDatasetError(f"Duplicate instrument master key: {key[0]} {key[1].isoformat()}")
        keys.add(key)
        by_instrument[record.instrument_id.canonical].append(record)

    for instrument, instrument_records in by_instrument.items():
        ordered = sorted(instrument_records, key=lambda record: record.valid_from)
        for previous, current in zip(ordered, ordered[1:]):
            if previous.valid_to is None or current.valid_from < previous.valid_to:
                raise InstrumentMasterDatasetError(f"overlapping instrument validity for {instrument}")


def _validate_provider_mapping_windows(provider_mappings: Sequence[ProviderSymbolValidity]) -> None:
    by_provider: dict[str, list[ProviderSymbolValidity]] = defaultdict(list)
    for mapping in provider_mappings:
        by_provider[mapping.provider.lower()].append(mapping)

    for provider, mappings in by_provider.items():
        ordered = sorted(mappings, key=lambda mapping: mapping.valid_from)
        for previous, current in zip(ordered, ordered[1:]):
            if previous.valid_to is None or current.valid_from < previous.valid_to:
                raise InstrumentMasterDatasetError(f"overlapping provider mapping validity for {provider}")


def _contains_date(valid_from: date, valid_to: date | None, as_of: date) -> bool:
    return valid_from <= as_of and (valid_to is None or as_of < valid_to)


def _validate_validity_window(valid_from: date, valid_to: date | None, label: str) -> None:
    if valid_to is not None:
        _require_date("valid_to", valid_to)
        if valid_to <= valid_from:
            raise InstrumentMasterDatasetError(f"{label} valid_to must be after valid_from")


def _require_date(field_name: str, value: object) -> None:
    if type(value) is not date:
        raise InstrumentMasterDatasetError(f"{field_name} must be a date")


def _require_aware_datetime(field_name: str, value: datetime) -> None:
    if type(value) is not datetime or value.tzinfo is None or value.utcoffset() is None:
        raise InstrumentMasterDatasetError(f"{field_name} must be timezone-aware")


def _required_string(field_name: str, value: object | None) -> str:
    if type(value) is not str:
        raise InstrumentMasterDatasetError(f"{field_name} is required")
    normalized = value.strip()
    if not normalized:
        raise InstrumentMasterDatasetError(f"{field_name} is required")
    return normalized


def _optional_string(value: object | None) -> str | None:
    if value is None:
        return None
    if type(value) is not str:
        raise InstrumentMasterDatasetError("optional string value must be a string")
    normalized = value.strip()
    return normalized or None


__all__ = [
    "INSTRUMENT_MASTER_CONTENT_TYPE",
    "INSTRUMENT_MASTER_SCHEMA_NAME",
    "INSTRUMENT_MASTER_SCHEMA_VERSION",
    "IndustryClassification",
    "InstrumentListingStatus",
    "InstrumentMasterDataset",
    "InstrumentMasterDatasetError",
    "InstrumentMasterRecord",
    "ProviderSymbolValidity",
]
