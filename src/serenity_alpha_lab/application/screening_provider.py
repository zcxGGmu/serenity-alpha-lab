from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from math import isfinite
from types import MappingProxyType
from typing import Any, Protocol, runtime_checkable

from serenity_alpha_lab.application.tracing import current_trace_context
from serenity_alpha_lab.datasets.catalog import DatasetCatalogError, DatasetVersionRef


SCREENING_PROVIDER_CONTRACT_VERSION = "1.0.0"
SCREENING_RAW_RESULT_SCHEMA_NAME = "screening.raw_candidates"
SCREENING_RAW_RESULT_SCHEMA_VERSION = "0.1.0"

ClockFn = Callable[[], datetime]


class ScreeningProviderErrorCategory(StrEnum):
    TIMEOUT = "timeout"
    UNAVAILABLE = "unavailable"
    INVALID_REQUEST = "invalid_request"
    SCHEMA_DRIFT = "schema_drift"
    DATA_INVALID = "data_invalid"
    PERMANENT = "permanent"


class ScreeningProviderError(RuntimeError):
    def __init__(
        self,
        *,
        category: ScreeningProviderErrorCategory | str,
        provider_id: str,
        operation: str,
        message: str,
        retry_after_seconds: float | None = None,
    ) -> None:
        normalized_category = ScreeningProviderErrorCategory(category)
        normalized_provider_id = _required_string("provider_id", provider_id)
        normalized_operation = _required_string("operation", operation)
        normalized_message = _required_string("message", message)
        if retry_after_seconds is not None:
            if type(retry_after_seconds) not in {int, float} or not isfinite(float(retry_after_seconds)):
                raise ValueError("retry_after_seconds must be finite")
            if float(retry_after_seconds) < 0:
                raise ValueError("retry_after_seconds cannot be negative")
            if normalized_category is not ScreeningProviderErrorCategory.TIMEOUT:
                raise ValueError("retry_after_seconds is only valid for timeout errors")

        self.category = normalized_category
        self.provider_id = normalized_provider_id
        self.operation = normalized_operation
        self.message = normalized_message
        self.retry_after_seconds = None if retry_after_seconds is None else float(retry_after_seconds)
        super().__init__(normalized_message)

    @property
    def is_retryable(self) -> bool:
        return self.category in {
            ScreeningProviderErrorCategory.TIMEOUT,
            ScreeningProviderErrorCategory.UNAVAILABLE,
        }


@dataclass(frozen=True, slots=True)
class ScreeningProviderStatus:
    provider_id: str
    available: bool
    provider_version: str
    contract_version: str
    strategy_count: int
    checked_at: datetime
    message: str | None = None
    trace_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "provider_id", _required_string("provider_id", self.provider_id))
        object.__setattr__(self, "provider_version", _required_string("provider_version", self.provider_version))
        object.__setattr__(self, "contract_version", _required_string("contract_version", self.contract_version))
        if type(self.available) is not bool:
            raise ScreeningProviderError(
                category=ScreeningProviderErrorCategory.SCHEMA_DRIFT,
                provider_id=self.provider_id,
                operation="status",
                message="screening provider status available must be boolean",
            )
        if type(self.strategy_count) is not int or self.strategy_count < 0:
            raise ScreeningProviderError(
                category=ScreeningProviderErrorCategory.SCHEMA_DRIFT,
                provider_id=self.provider_id,
                operation="status",
                message="screening provider strategy_count cannot be negative",
            )
        _require_aware_datetime("checked_at", self.checked_at)
        object.__setattr__(self, "message", _optional_string(self.message))
        object.__setattr__(self, "trace_id", _optional_string(self.trace_id))


@dataclass(frozen=True, slots=True)
class ScreeningStrategy:
    strategy_id: str
    name: str
    description: str
    version: str
    category: str = "uncategorized"
    tags: Sequence[str] = ()
    market_scope: Sequence[str] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "strategy_id", _required_string("strategy_id", self.strategy_id))
        object.__setattr__(self, "name", _required_string("name", self.name))
        object.__setattr__(self, "description", _required_string("description", self.description))
        object.__setattr__(self, "version", _required_string("version", self.version))
        object.__setattr__(self, "category", _required_string("category", self.category))
        object.__setattr__(self, "tags", _unique_string_tuple("tag", self.tags))
        object.__setattr__(self, "market_scope", _unique_string_tuple("market", self.market_scope))

    def supports_market(self, market: str) -> bool:
        return not self.market_scope or _required_string("market", market) in self.market_scope


@dataclass(frozen=True, slots=True)
class ScreeningRequest:
    strategy_id: str
    market: str
    dataset_versions: Mapping[str, str]
    max_results: int = 20
    use_llm_overlay: bool = False
    timeout_seconds: float = 30.0
    context: Mapping[str, Any] = field(default_factory=dict)
    requested_at: datetime | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "strategy_id", _required_string("strategy_id", self.strategy_id))
        object.__setattr__(self, "market", _required_string("market", self.market))
        object.__setattr__(self, "dataset_versions", _normalize_dataset_versions(self.dataset_versions))
        if type(self.max_results) is not int or self.max_results <= 0:
            raise _invalid_request("max_results must be a positive integer")
        if type(self.use_llm_overlay) is not bool:
            raise _invalid_request("use_llm_overlay must be boolean")
        if type(self.timeout_seconds) not in {int, float} or not isfinite(float(self.timeout_seconds)):
            raise _invalid_request("timeout_seconds must be finite")
        if float(self.timeout_seconds) <= 0:
            raise _invalid_request("timeout_seconds must be positive")
        object.__setattr__(self, "timeout_seconds", float(self.timeout_seconds))
        object.__setattr__(self, "context", _freeze_mapping(self.context))
        if self.requested_at is not None:
            _require_aware_datetime("requested_at", self.requested_at)


@dataclass(frozen=True, slots=True)
class ScreeningResult:
    provider_id: str
    strategy_id: str
    strategy_version: str
    market: str
    dataset_versions: Mapping[str, str]
    candidates: Sequence[Mapping[str, Any]]
    candidate_count: int
    snapshot_count: int
    after_filter_count: int
    provider_run_id: str
    requested_at: datetime
    received_at: datetime
    contract_version: str = SCREENING_PROVIDER_CONTRACT_VERSION
    provider_version: str = ""
    schema_name: str = SCREENING_RAW_RESULT_SCHEMA_NAME
    schema_version: str = SCREENING_RAW_RESULT_SCHEMA_VERSION
    warnings: Sequence[str] = ()
    source_errors: Sequence[str] = ()
    llm_overlay_enabled: bool = False
    llm_coverage: float | None = None
    trace_id: str | None = None
    platform_run_id: str | None = None
    stage_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "provider_id", _required_string("provider_id", self.provider_id))
        object.__setattr__(self, "strategy_id", _required_string("strategy_id", self.strategy_id))
        object.__setattr__(self, "strategy_version", _required_string("strategy_version", self.strategy_version))
        object.__setattr__(self, "market", _required_string("market", self.market))
        object.__setattr__(self, "dataset_versions", _normalize_dataset_versions(self.dataset_versions))
        object.__setattr__(self, "candidates", tuple(_freeze_mapping(candidate) for candidate in self.candidates))
        _require_non_negative_int("candidate_count", self.candidate_count)
        _require_non_negative_int("snapshot_count", self.snapshot_count)
        _require_non_negative_int("after_filter_count", self.after_filter_count)
        object.__setattr__(self, "provider_run_id", _required_string("provider_run_id", self.provider_run_id))
        _require_aware_datetime("requested_at", self.requested_at)
        _require_aware_datetime("received_at", self.received_at)
        if self.received_at < self.requested_at:
            raise ScreeningProviderError(
                category=ScreeningProviderErrorCategory.DATA_INVALID,
                provider_id=self.provider_id,
                operation="screen",
                message="received_at cannot be before requested_at",
            )
        object.__setattr__(self, "contract_version", _required_string("contract_version", self.contract_version))
        object.__setattr__(self, "provider_version", _optional_string(self.provider_version) or "")
        object.__setattr__(self, "schema_name", _required_string("schema_name", self.schema_name))
        object.__setattr__(self, "schema_version", _required_string("schema_version", self.schema_version))
        object.__setattr__(self, "warnings", _string_tuple("warning", self.warnings))
        object.__setattr__(self, "source_errors", _string_tuple("source_error", self.source_errors))
        if type(self.llm_overlay_enabled) is not bool:
            raise ScreeningProviderError(
                category=ScreeningProviderErrorCategory.DATA_INVALID,
                provider_id=self.provider_id,
                operation="screen",
                message="llm_overlay_enabled must be boolean",
            )
        if self.llm_coverage is not None:
            if type(self.llm_coverage) not in {int, float} or not isfinite(float(self.llm_coverage)):
                raise ScreeningProviderError(
                    category=ScreeningProviderErrorCategory.DATA_INVALID,
                    provider_id=self.provider_id,
                    operation="screen",
                    message="llm_coverage must be finite",
                )
            object.__setattr__(self, "llm_coverage", float(self.llm_coverage))
        object.__setattr__(self, "trace_id", _optional_string(self.trace_id))
        object.__setattr__(self, "platform_run_id", _optional_string(self.platform_run_id))
        object.__setattr__(self, "stage_id", _optional_string(self.stage_id))


@runtime_checkable
class ScreeningProvider(Protocol):
    provider_id: str

    def status(self) -> ScreeningProviderStatus:
        """Return non-sensitive provider status."""

    def list_strategies(self) -> tuple[ScreeningStrategy, ...]:
        """Return available screening strategies."""

    def screen(self, request: ScreeningRequest) -> ScreeningResult:
        """Run one screening request and return normalized raw candidates."""


class FakeScreeningProvider:
    provider_id = "fake_screening"

    def __init__(
        self,
        *,
        strategies: Sequence[ScreeningStrategy] = (),
        candidates: Mapping[str, Sequence[Mapping[str, Any]]] | None = None,
        clock: ClockFn | None = None,
        provider_version: str = "fixture",
    ) -> None:
        self._clock = clock or (lambda: datetime.now(UTC))
        self._provider_version = _required_string("provider_version", provider_version)
        self._strategies = tuple(strategies)
        for strategy in self._strategies:
            if type(strategy) is not ScreeningStrategy:
                raise ScreeningProviderError(
                    category=ScreeningProviderErrorCategory.DATA_INVALID,
                    provider_id=self.provider_id,
                    operation="strategies",
                    message="fake strategies must contain ScreeningStrategy values",
                )
        self._strategy_by_id = {strategy.strategy_id: strategy for strategy in self._strategies}
        if len(self._strategy_by_id) != len(self._strategies):
            raise ScreeningProviderError(
                category=ScreeningProviderErrorCategory.INVALID_REQUEST,
                provider_id=self.provider_id,
                operation="strategies",
                message="duplicate screening strategy ids are not allowed",
            )
        self._candidates = {
            strategy_id: tuple(_freeze_mapping(candidate) for candidate in strategy_candidates)
            for strategy_id, strategy_candidates in dict(candidates or {}).items()
        }

    def status(self) -> ScreeningProviderStatus:
        context = current_trace_context()
        return ScreeningProviderStatus(
            provider_id=self.provider_id,
            available=True,
            provider_version=self._provider_version,
            contract_version=SCREENING_PROVIDER_CONTRACT_VERSION,
            strategy_count=len(self._strategies),
            checked_at=_ensure_utc(self._clock()),
            trace_id=context.trace_id if context is not None else None,
        )

    def list_strategies(self) -> tuple[ScreeningStrategy, ...]:
        return self._strategies

    def screen(self, request: ScreeningRequest) -> ScreeningResult:
        if type(request) is not ScreeningRequest:
            raise ScreeningProviderError(
                category=ScreeningProviderErrorCategory.INVALID_REQUEST,
                provider_id=self.provider_id,
                operation="screen",
                message="request must be a ScreeningRequest",
            )
        strategy = self._strategy_by_id.get(request.strategy_id)
        if strategy is None:
            raise ScreeningProviderError(
                category=ScreeningProviderErrorCategory.INVALID_REQUEST,
                provider_id=self.provider_id,
                operation="screen",
                message=f"Unknown screening strategy: {request.strategy_id}",
            )
        if not strategy.supports_market(request.market):
            raise ScreeningProviderError(
                category=ScreeningProviderErrorCategory.INVALID_REQUEST,
                provider_id=self.provider_id,
                operation="screen",
                message=f"Strategy {request.strategy_id} does not support market {request.market}",
            )

        requested_at = _ensure_utc(request.requested_at or self._clock())
        received_at = _ensure_utc(self._clock())
        context = current_trace_context()
        candidates = self._candidates.get(request.strategy_id, ())[: request.max_results]
        return ScreeningResult(
            provider_id=self.provider_id,
            provider_version=self._provider_version,
            strategy_id=strategy.strategy_id,
            strategy_version=strategy.version,
            market=request.market,
            dataset_versions=request.dataset_versions,
            candidates=candidates,
            candidate_count=len(candidates),
            snapshot_count=len(self._candidates.get(request.strategy_id, ())),
            after_filter_count=len(self._candidates.get(request.strategy_id, ())),
            provider_run_id=f"fake-{strategy.strategy_id}-{received_at.isoformat()}",
            requested_at=requested_at,
            received_at=received_at,
            llm_overlay_enabled=request.use_llm_overlay,
            trace_id=context.trace_id if context is not None else None,
            platform_run_id=context.run_id if context is not None else None,
            stage_id=context.stage_id if context is not None else None,
        )


def _normalize_dataset_versions(dataset_versions: Mapping[str, str]) -> Mapping[str, str]:
    if not isinstance(dataset_versions, Mapping):
        raise _invalid_request("dataset_versions must be a mapping of dataset name to concrete Dataset Version id")
    if not dataset_versions:
        raise _invalid_request("dataset_versions are required and must reference concrete Dataset Version ids")
    normalized: dict[str, str] = {}
    for dataset_name, version_id in dataset_versions.items():
        name = _required_string("dataset_name", dataset_name)
        version = _required_string("dataset_version", version_id)
        if version.strip().lower() == "latest":
            raise _invalid_request("screening requires concrete Dataset Version ids; latest alias is not allowed")
        try:
            DatasetVersionRef.version(version)
        except DatasetCatalogError as exc:
            raise _invalid_request(
                f"screening requires concrete Dataset Version ids; invalid {name}: {version}"
            ) from exc
        normalized[name] = version
    return MappingProxyType(normalized)


def _invalid_request(message: str) -> ScreeningProviderError:
    return ScreeningProviderError(
        category=ScreeningProviderErrorCategory.INVALID_REQUEST,
        provider_id="screening_provider",
        operation="request",
        message=message,
    )


def _freeze_mapping(mapping: Mapping[str, Any]) -> Mapping[str, Any]:
    if not isinstance(mapping, Mapping):
        raise ScreeningProviderError(
            category=ScreeningProviderErrorCategory.DATA_INVALID,
            provider_id="screening_provider",
            operation="freeze",
            message="value must be a mapping",
        )
    return MappingProxyType({str(key): _freeze_value(value) for key, value in mapping.items()})


def _freeze_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return _freeze_mapping(value)
    if isinstance(value, list | tuple):
        return tuple(_freeze_value(item) for item in value)
    if isinstance(value, set | frozenset):
        return tuple(sorted(_freeze_value(item) for item in value))
    if isinstance(value, bytearray):
        return bytes(value)
    return value


def _required_string(field_name: str, value: object) -> str:
    if type(value) is not str:
        raise ScreeningProviderError(
            category=ScreeningProviderErrorCategory.INVALID_REQUEST,
            provider_id="screening_provider",
            operation="request",
            message=f"{field_name} is required",
        )
    stripped = value.strip()
    if not stripped:
        raise ScreeningProviderError(
            category=ScreeningProviderErrorCategory.INVALID_REQUEST,
            provider_id="screening_provider",
            operation="request",
            message=f"{field_name} is required",
        )
    return stripped


def _optional_string(value: object) -> str | None:
    if value is None:
        return None
    return _required_string("optional string", value)


def _string_tuple(field_name: str, values: Sequence[str]) -> tuple[str, ...]:
    return tuple(_required_string(field_name, value) for value in values)


def _unique_string_tuple(field_name: str, values: Sequence[str]) -> tuple[str, ...]:
    normalized = _string_tuple(field_name, values)
    deduped = tuple(dict.fromkeys(normalized))
    if len(deduped) != len(normalized):
        raise ScreeningProviderError(
            category=ScreeningProviderErrorCategory.INVALID_REQUEST,
            provider_id="screening_provider",
            operation="request",
            message=f"duplicate {field_name} values are not allowed",
        )
    return deduped


def _require_aware_datetime(field_name: str, value: datetime) -> None:
    if type(value) is not datetime or value.tzinfo is None or value.utcoffset() is None:
        raise ScreeningProviderError(
            category=ScreeningProviderErrorCategory.INVALID_REQUEST,
            provider_id="screening_provider",
            operation="request",
            message=f"{field_name} must be timezone-aware",
        )


def _require_non_negative_int(field_name: str, value: int) -> None:
    if type(value) is not int or value < 0:
        raise ScreeningProviderError(
            category=ScreeningProviderErrorCategory.DATA_INVALID,
            provider_id="screening_provider",
            operation="screen",
            message=f"{field_name} cannot be negative",
        )


def _ensure_utc(value: datetime) -> datetime:
    _require_aware_datetime("datetime", value)
    return value.astimezone(UTC)


__all__ = [
    "SCREENING_PROVIDER_CONTRACT_VERSION",
    "SCREENING_RAW_RESULT_SCHEMA_NAME",
    "SCREENING_RAW_RESULT_SCHEMA_VERSION",
    "FakeScreeningProvider",
    "ScreeningProvider",
    "ScreeningProviderError",
    "ScreeningProviderErrorCategory",
    "ScreeningProviderStatus",
    "ScreeningRequest",
    "ScreeningResult",
    "ScreeningStrategy",
]
