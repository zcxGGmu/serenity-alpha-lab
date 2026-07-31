from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, fields, is_dataclass
from datetime import date, datetime
from enum import StrEnum
from math import isfinite
from types import MappingProxyType
from typing import Generic, Protocol, TypeVar, cast, runtime_checkable

from serenity_alpha_lab.domain.artifacts import ArtifactUri
from serenity_alpha_lab.domain.instruments import AssetType, Exchange, InstrumentId, Market


class ProviderCapability(StrEnum):
    INSTRUMENTS = "instruments"
    TRADING_CALENDAR = "trading_calendar"
    DAILY_BARS = "daily_bars"
    FUNDAMENTALS = "fundamentals"


@dataclass(frozen=True, slots=True)
class Capability:
    capability: ProviderCapability
    schema_name: str
    schema_version: str
    markets: Sequence[Market | str] = ()
    frequency: str | None = None
    fields: Sequence[str] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "capability", ProviderCapability(self.capability))
        object.__setattr__(self, "schema_name", _required_string("schema_name", self.schema_name))
        object.__setattr__(self, "schema_version", _required_string("schema_version", self.schema_version))
        object.__setattr__(self, "markets", _unique_tuple(Market(market) for market in self.markets))
        object.__setattr__(self, "frequency", _optional_string(self.frequency))
        object.__setattr__(
            self,
            "fields",
            _unique_tuple(_required_string("field", field) for field in self.fields),
        )


@dataclass(frozen=True, slots=True)
class ProviderCapabilities:
    capabilities: Sequence[Capability] = ()

    def __post_init__(self) -> None:
        normalized = tuple(self.capabilities)
        for declaration in normalized:
            if type(declaration) is not Capability:
                raise TypeError("ProviderCapabilities requires Capability declarations")
        identities = [declaration.capability for declaration in normalized]
        duplicates = {identity for identity in identities if identities.count(identity) > 1}
        if duplicates:
            values = ", ".join(sorted(identity.value for identity in duplicates))
            raise ValueError(f"Duplicate provider capability declarations: {values}")
        object.__setattr__(self, "capabilities", normalized)

    @property
    def declarations(self) -> tuple[Capability, ...]:
        return tuple(self.capabilities)

    def supports(
        self,
        capability: ProviderCapability | str,
        market: Market | str | None = None,
    ) -> bool:
        declaration = self.get(capability)
        if declaration is None:
            return False
        if market is None or not declaration.markets:
            return True
        return Market(market) in declaration.markets

    def get(self, capability: ProviderCapability | str) -> Capability | None:
        normalized = ProviderCapability(capability)
        return next(
            (declaration for declaration in self.capabilities if declaration.capability is normalized),
            None,
        )


@dataclass(frozen=True, slots=True)
class ProviderWarning:
    code: str
    message: str
    fields: Sequence[str] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "code", _required_string("code", self.code))
        object.__setattr__(self, "message", _required_string("message", self.message))
        object.__setattr__(
            self,
            "fields",
            _unique_tuple(_required_string("field", field) for field in self.fields),
        )


@dataclass(frozen=True, slots=True)
class Provenance:
    """Origin metadata for a provider result.

    Request parameter values cross this domain boundary already sanitized. The
    mapping is defensively copied so callers cannot mutate recorded provenance.
    """

    provider_id: str
    operation: ProviderCapability | str
    request_parameters: Mapping[str, object]
    requested_at: datetime
    fetched_at: datetime
    raw_response_sha256: str
    field_lineage: Mapping[str, str]
    provider_version: str | None = None
    source_timestamp: datetime | None = None
    trace_id: str | None = None
    run_id: str | None = None
    stage_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "provider_id", _required_string("provider_id", self.provider_id))
        object.__setattr__(self, "provider_version", _optional_string(self.provider_version))
        object.__setattr__(self, "operation", _required_string("operation", str(self.operation)))
        object.__setattr__(
            self,
            "request_parameters",
            _freeze_request_parameters(self.request_parameters),
        )
        _require_aware_datetime("requested_at", self.requested_at)
        _require_aware_datetime("fetched_at", self.fetched_at)
        object.__setattr__(
            self,
            "raw_response_sha256",
            ArtifactUri.for_sha256(self.raw_response_sha256).digest,
        )
        object.__setattr__(
            self,
            "field_lineage",
            _freeze_field_lineage(self.field_lineage),
        )
        if self.source_timestamp is not None:
            _require_aware_datetime("source_timestamp", self.source_timestamp)
        object.__setattr__(self, "trace_id", _optional_string(self.trace_id))
        object.__setattr__(self, "run_id", _optional_string(self.run_id))
        object.__setattr__(self, "stage_id", _optional_string(self.stage_id))


T = TypeVar("T")
TItem = TypeVar("TItem")


@dataclass(frozen=True, slots=True)
class DataBatch(Generic[T]):
    records: Sequence[T]
    schema_name: str
    schema_version: str
    provenance: Provenance
    fresh_until: datetime
    warnings: Sequence[ProviderWarning] = ()

    def __post_init__(self) -> None:
        if type(self.provenance) is not Provenance:
            raise TypeError("DataBatch provenance must be Provenance")
        object.__setattr__(
            self,
            "records",
            tuple(cast(T, _freeze_value(record)) for record in self.records),
        )
        object.__setattr__(self, "schema_name", _required_string("schema_name", self.schema_name))
        object.__setattr__(self, "schema_version", _required_string("schema_version", self.schema_version))
        _require_aware_datetime("fresh_until", self.fresh_until)
        normalized_warnings = tuple(self.warnings)
        for warning in normalized_warnings:
            if type(warning) is not ProviderWarning:
                raise TypeError("DataBatch warnings must be ProviderWarning")
        object.__setattr__(self, "warnings", normalized_warnings)

    def is_stale(self, *, at: datetime) -> bool:
        _require_aware_datetime("at", at)
        return at > self.fresh_until


class ProviderErrorCategory(StrEnum):
    RETRYABLE = "retryable"
    RATE_LIMITED = "rate_limited"
    AUTH = "auth"
    SCHEMA_DRIFT = "schema_drift"
    DATA_INVALID = "data_invalid"
    PERMANENT = "permanent"


class ProviderError(RuntimeError):
    def __init__(
        self,
        *,
        category: ProviderErrorCategory | str,
        provider_id: str,
        operation: ProviderCapability | str,
        message: str,
        retry_after_seconds: float | None = None,
    ) -> None:
        normalized_category = ProviderErrorCategory(category)
        normalized_provider_id = _required_string("provider_id", provider_id)
        normalized_operation = _required_string("operation", str(operation))
        normalized_message = _required_string("message", message)
        if retry_after_seconds is not None:
            if not isfinite(retry_after_seconds):
                raise ValueError("retry_after_seconds must be finite")
            if retry_after_seconds < 0:
                raise ValueError("retry_after_seconds cannot be negative")
            if normalized_category is not ProviderErrorCategory.RATE_LIMITED:
                raise ValueError("retry_after_seconds is only valid for rate_limited errors")

        self.category = normalized_category
        self.provider_id = normalized_provider_id
        self.operation = normalized_operation
        self.message = normalized_message
        self.retry_after_seconds = retry_after_seconds
        super().__init__(normalized_message)

    @property
    def is_retryable(self) -> bool:
        return self.category in {
            ProviderErrorCategory.RETRYABLE,
            ProviderErrorCategory.RATE_LIMITED,
        }


@runtime_checkable
class MarketDataProvider(Protocol):
    provider_id: str

    def capabilities(self) -> ProviderCapabilities:
        """Return the provider's declared market-data capabilities."""

    def list_instruments(self, as_of: date) -> DataBatch[Mapping[str, object]]:
        """Return instruments known to the provider at the requested date."""

    def get_calendar(self, start: date, end: date) -> DataBatch[Mapping[str, object]]:
        """Return trading-calendar records for the inclusive date range."""

    def get_daily_bars(
        self,
        instruments: Sequence[InstrumentId],
        start: date,
        end: date,
    ) -> DataBatch[Mapping[str, object]]:
        """Return daily bars for canonical instruments and a date range."""

    def get_fundamentals(
        self,
        instruments: Sequence[InstrumentId],
        as_of: datetime,
    ) -> DataBatch[Mapping[str, object]]:
        """Return fundamental records available at the requested timestamp."""


def _required_string(field_name: str, value: object) -> str:
    if type(value) is not str:
        raise TypeError(f"{field_name} must be a string")
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} is required")
    return normalized


def _optional_string(value: object | None) -> str | None:
    if value is None:
        return None
    if type(value) is not str:
        raise TypeError("optional string value must be a string")
    normalized = value.strip()
    return normalized or None


def _require_aware_datetime(field_name: str, value: datetime) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")


def _unique_tuple(values: Iterable[TItem]) -> tuple[TItem, ...]:
    return tuple(dict.fromkeys(values))


def _freeze_request_parameters(parameters: Mapping[str, object]) -> Mapping[str, object]:
    normalized: dict[str, object] = {}
    for key, value in parameters.items():
        normalized_key = _required_string("request parameter key", _freeze_value(key))
        normalized[normalized_key] = _freeze_value(value)
    return MappingProxyType(normalized)


def _freeze_field_lineage(lineage: Mapping[str, str]) -> Mapping[str, str]:
    normalized: dict[str, str] = {}
    for key, value in lineage.items():
        normalized_key = _required_string("field lineage key", _freeze_value(key))
        normalized[normalized_key] = _required_string("field lineage value", _freeze_value(value))
    return MappingProxyType(normalized)


_IMMUTABLE_SCALAR_TYPES = frozenset(
    {
        type(None),
        bool,
        int,
        float,
        str,
        bytes,
        date,
        datetime,
    }
)
_IMMUTABLE_ENUM_TYPES = frozenset(
    {
        ProviderCapability,
        ProviderErrorCategory,
        Market,
        Exchange,
        AssetType,
    }
)


def _freeze_value(value: object) -> object:
    if isinstance(value, bytearray):
        return bytes(value)
    value_type = type(value)
    if value_type in _IMMUTABLE_SCALAR_TYPES or value_type in _IMMUTABLE_ENUM_TYPES:
        return value
    if isinstance(value, Mapping):
        return MappingProxyType({_freeze_value(key): _freeze_value(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_value(item) for item in value)
    if isinstance(value, (set, frozenset)):
        return frozenset(_freeze_value(item) for item in value)
    if _is_frozen_dataclass_instance(value):
        for field in fields(value):
            field_value = getattr(value, field.name)
            frozen_field_value = _freeze_value(field_value)
            if type(frozen_field_value) is not type(field_value) or frozen_field_value != field_value:
                raise TypeError(
                    f"Frozen dataclass {type(value).__name__} contains mutable field {field.name!r}"
                )
        return value
    raise TypeError(f"Unsupported provider value type: {type(value).__name__}")


def _is_frozen_dataclass_instance(value: object) -> bool:
    if isinstance(value, type) or not is_dataclass(value):
        return False
    parameters = getattr(type(value), "__dataclass_params__", None)
    return bool(parameters is not None and parameters.frozen)


__all__ = [
    "Capability",
    "DataBatch",
    "MarketDataProvider",
    "Provenance",
    "ProviderCapabilities",
    "ProviderCapability",
    "ProviderError",
    "ProviderErrorCategory",
    "ProviderWarning",
]
