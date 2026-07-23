from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from math import isfinite
from types import MappingProxyType

from serenity_alpha_lab.datasets.quality import DataQualityStatus
from serenity_alpha_lab.domain.instruments import Market
from serenity_alpha_lab.domain.providers import DataBatch, ProviderCapability, ProviderError


class ProviderPolicyError(ValueError):
    """Raised when a Provider Policy request or decision is invalid."""


class ProviderPolicyStatus(StrEnum):
    SELECTED = "selected"
    QUARANTINED = "quarantined"
    EXHAUSTED = "exhausted"


class ProviderFallbackAttemptStatus(StrEnum):
    SELECTED = "selected"
    REJECTED = "rejected"
    QUARANTINED = "quarantined"


@dataclass(frozen=True, slots=True)
class ProviderPolicySource:
    provider_id: str
    markets: Sequence[Market | str]
    capabilities: Sequence[ProviderCapability | str]
    quality_score: float = 1.0

    def __post_init__(self) -> None:
        object.__setattr__(self, "provider_id", _provider_id(self.provider_id))
        object.__setattr__(self, "markets", _unique_tuple(Market(market) for market in self.markets))
        object.__setattr__(
            self,
            "capabilities",
            _unique_tuple(ProviderCapability(capability) for capability in self.capabilities),
        )
        if not self.markets:
            raise ProviderPolicyError("source markets are required")
        if not self.capabilities:
            raise ProviderPolicyError("source capabilities are required")
        if type(self.quality_score) not in {int, float} or not isfinite(float(self.quality_score)):
            raise ProviderPolicyError("source quality_score must be finite")
        if float(self.quality_score) < 0:
            raise ProviderPolicyError("source quality_score cannot be negative")
        object.__setattr__(self, "quality_score", float(self.quality_score))

    def supports(self, *, market: Market, capability: ProviderCapability) -> bool:
        return market in self.markets and capability in self.capabilities

    def to_record(self) -> dict[str, object]:
        return {
            "provider_id": self.provider_id,
            "markets": [market.value for market in self.markets],
            "capabilities": [capability.value for capability in self.capabilities],
            "quality_score": self.quality_score,
        }


@dataclass(frozen=True, slots=True)
class ProviderPolicy:
    policy_id: str
    market: Market | str
    dataset: str
    priority: Sequence[str]
    sources: Mapping[str, ProviderPolicySource]
    cross_check_provider_id: str | None = None
    max_close_diff_bps: float | None = None

    @classmethod
    def from_mapping(cls, mapping: Mapping[str, object]) -> ProviderPolicy:
        policy_id = _required_string("policy_id", mapping.get("policy_id"))
        market = Market(_required_string("market", mapping.get("market")))
        dataset = _required_string("dataset", mapping.get("dataset"))
        raw_priority = mapping.get("priority")
        if not isinstance(raw_priority, Sequence) or isinstance(raw_priority, (str, bytes)):
            raise ProviderPolicyError("priority must be a sequence")
        priority = tuple(_provider_id(provider_id) for provider_id in raw_priority)

        raw_sources = mapping.get("sources")
        if not isinstance(raw_sources, Mapping):
            raise ProviderPolicyError("sources must be a mapping")
        sources: dict[str, ProviderPolicySource] = {}
        for provider_id, source_config in raw_sources.items():
            normalized_provider = _provider_id(provider_id)
            if not isinstance(source_config, Mapping):
                raise ProviderPolicyError("source config must be a mapping")
            raw_markets = source_config.get("markets")
            raw_capabilities = source_config.get("capabilities")
            if not isinstance(raw_markets, Sequence) or isinstance(raw_markets, (str, bytes)):
                raise ProviderPolicyError("source markets must be a sequence")
            if not isinstance(raw_capabilities, Sequence) or isinstance(raw_capabilities, (str, bytes)):
                raise ProviderPolicyError("source capabilities must be a sequence")
            sources[normalized_provider] = ProviderPolicySource(
                provider_id=normalized_provider,
                markets=tuple(raw_markets),
                capabilities=tuple(raw_capabilities),
                quality_score=float(source_config.get("quality_score", 1.0)),
            )

        validation = mapping.get("validation") or {}
        if not isinstance(validation, Mapping):
            raise ProviderPolicyError("validation must be a mapping")
        cross_check_provider = _optional_provider_id(validation.get("cross_check_provider"))
        raw_max_close_diff_bps = validation.get("max_close_diff_bps")
        max_close_diff_bps = None if raw_max_close_diff_bps is None else float(raw_max_close_diff_bps)

        return cls(
            policy_id=policy_id,
            market=market,
            dataset=dataset,
            priority=priority,
            sources=sources,
            cross_check_provider_id=cross_check_provider,
            max_close_diff_bps=max_close_diff_bps,
        )

    def __post_init__(self) -> None:
        object.__setattr__(self, "policy_id", _required_string("policy_id", self.policy_id))
        object.__setattr__(self, "market", Market(self.market))
        object.__setattr__(self, "dataset", _required_string("dataset", self.dataset))
        priority = tuple(_provider_id(provider_id) for provider_id in self.priority)
        if not priority:
            raise ProviderPolicyError("priority is required")
        object.__setattr__(self, "priority", priority)

        sources: dict[str, ProviderPolicySource] = {}
        for provider_id, source in self.sources.items():
            normalized_provider = _provider_id(provider_id)
            if type(source) is not ProviderPolicySource:
                raise ProviderPolicyError("sources must contain ProviderPolicySource values")
            if source.provider_id != normalized_provider:
                raise ProviderPolicyError("source key must match source provider_id")
            sources[normalized_provider] = source
        missing_sources = [provider_id for provider_id in priority if provider_id not in sources]
        if missing_sources:
            raise ProviderPolicyError(f"priority providers missing source config: {', '.join(missing_sources)}")
        object.__setattr__(self, "sources", MappingProxyType(sources))

        object.__setattr__(self, "cross_check_provider_id", _optional_provider_id(self.cross_check_provider_id))
        if self.max_close_diff_bps is not None:
            if type(self.max_close_diff_bps) not in {int, float} or not isfinite(float(self.max_close_diff_bps)):
                raise ProviderPolicyError("max_close_diff_bps must be finite")
            if float(self.max_close_diff_bps) < 0:
                raise ProviderPolicyError("max_close_diff_bps cannot be negative")
            object.__setattr__(self, "max_close_diff_bps", float(self.max_close_diff_bps))

    def ordered_provider_ids(self, request: ProviderSelectionRequest) -> tuple[str, ...]:
        if request.market is not self.market:
            return ()
        return tuple(
            provider_id
            for provider_id in self.priority
            if self.sources[provider_id].supports(market=request.market, capability=request.capability)
        )

    def to_record(self) -> dict[str, object]:
        return {
            "policy_id": self.policy_id,
            "market": self.market.value,
            "dataset": self.dataset,
            "priority": list(self.priority),
            "sources": {
                provider_id: self.sources[provider_id].to_record()
                for provider_id in sorted(self.sources)
            },
            "validation": {
                "cross_check_provider": self.cross_check_provider_id,
                "max_close_diff_bps": self.max_close_diff_bps,
            },
        }


@dataclass(frozen=True, slots=True)
class ProviderSelectionRequest:
    market: Market | str
    capability: ProviderCapability | str
    dataset_name: str
    required_fields: Sequence[str]
    evaluation_time: datetime
    trace_id: str | None = None
    run_id: str | None = None
    stage_id: str | None = None
    quality_status_by_provider: Mapping[str, DataQualityStatus | str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "market", Market(self.market))
        object.__setattr__(self, "capability", ProviderCapability(self.capability))
        object.__setattr__(self, "dataset_name", _required_string("dataset_name", self.dataset_name))
        required_fields = _unique_tuple(_required_string("required field", field) for field in self.required_fields)
        if not required_fields:
            raise ProviderPolicyError("required_fields are required")
        object.__setattr__(self, "required_fields", required_fields)
        _require_aware_datetime("evaluation_time", self.evaluation_time)
        object.__setattr__(self, "trace_id", _optional_string(self.trace_id))
        object.__setattr__(self, "run_id", _optional_string(self.run_id))
        object.__setattr__(self, "stage_id", _optional_string(self.stage_id))
        quality: dict[str, DataQualityStatus] = {}
        for provider_id, status in self.quality_status_by_provider.items():
            quality[_provider_id(provider_id)] = DataQualityStatus(status)
        object.__setattr__(self, "quality_status_by_provider", MappingProxyType(quality))


@dataclass(frozen=True, slots=True)
class ProviderFallbackAttempt:
    provider_id: str
    status: ProviderFallbackAttemptStatus | str
    reason: str | None = None
    provider_error_category: str | None = None
    message: str | None = None
    missing_fields: Sequence[str] = ()
    quality_status: DataQualityStatus | str | None = None
    fresh_until: datetime | None = None
    source_timestamp: datetime | None = None
    raw_response_sha256: str | None = None
    quality_score: float | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "provider_id", _provider_id(self.provider_id))
        object.__setattr__(self, "status", ProviderFallbackAttemptStatus(self.status))
        object.__setattr__(self, "reason", _optional_string(self.reason))
        object.__setattr__(self, "provider_error_category", _optional_string(self.provider_error_category))
        object.__setattr__(self, "message", _optional_string(self.message))
        object.__setattr__(
            self,
            "missing_fields",
            _unique_tuple(_required_string("missing field", field) for field in self.missing_fields),
        )
        if self.quality_status is not None:
            object.__setattr__(self, "quality_status", DataQualityStatus(self.quality_status))
        if self.fresh_until is not None:
            _require_aware_datetime("fresh_until", self.fresh_until)
        if self.source_timestamp is not None:
            _require_aware_datetime("source_timestamp", self.source_timestamp)
        object.__setattr__(self, "raw_response_sha256", _optional_string(self.raw_response_sha256))
        if self.quality_score is not None:
            if type(self.quality_score) not in {int, float} or not isfinite(float(self.quality_score)):
                raise ProviderPolicyError("quality_score must be finite")
            object.__setattr__(self, "quality_score", float(self.quality_score))

    def to_record(self) -> dict[str, object]:
        return {
            "provider_id": self.provider_id,
            "status": self.status.value,
            "reason": self.reason,
            "provider_error_category": self.provider_error_category,
            "message": self.message,
            "missing_fields": list(self.missing_fields),
            "quality_status": None if self.quality_status is None else self.quality_status.value,
            "fresh_until": None if self.fresh_until is None else self.fresh_until.isoformat(),
            "source_timestamp": None if self.source_timestamp is None else self.source_timestamp.isoformat(),
            "raw_response_sha256": self.raw_response_sha256,
            "quality_score": self.quality_score,
        }


@dataclass(frozen=True, slots=True)
class ProviderConflictRecord:
    field_name: str
    primary_key: Mapping[str, str]
    provider_values: Mapping[str, float]
    observed_diff_bps: float
    threshold_bps: float
    resolution: str = "quarantine"

    def __post_init__(self) -> None:
        object.__setattr__(self, "field_name", _required_string("field_name", self.field_name))
        object.__setattr__(self, "primary_key", _freeze_string_mapping(self.primary_key))
        provider_values: dict[str, float] = {}
        for provider_id, value in self.provider_values.items():
            provider_values[_provider_id(provider_id)] = _required_number("provider value", value)
        if len(provider_values) < 2:
            raise ProviderPolicyError("provider_values must contain at least two providers")
        object.__setattr__(self, "provider_values", MappingProxyType(provider_values))
        object.__setattr__(self, "observed_diff_bps", _non_negative_number("observed_diff_bps", self.observed_diff_bps))
        object.__setattr__(self, "threshold_bps", _non_negative_number("threshold_bps", self.threshold_bps))
        object.__setattr__(self, "resolution", _required_string("resolution", self.resolution))

    def to_record(self) -> dict[str, object]:
        return {
            "field_name": self.field_name,
            "primary_key": dict(self.primary_key),
            "provider_values": dict(self.provider_values),
            "observed_diff_bps": self.observed_diff_bps,
            "threshold_bps": self.threshold_bps,
            "resolution": self.resolution,
        }


@dataclass(frozen=True, slots=True)
class ProviderFallbackTrace:
    policy_id: str
    dataset_name: str
    market: Market | str
    capability: ProviderCapability | str
    status: ProviderPolicyStatus | str
    attempted_order: Sequence[str]
    attempts: Sequence[ProviderFallbackAttempt]
    selected_provider_id: str | None = None
    conflicts: Sequence[ProviderConflictRecord] = ()
    trace_id: str | None = None
    run_id: str | None = None
    stage_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "policy_id", _required_string("policy_id", self.policy_id))
        object.__setattr__(self, "dataset_name", _required_string("dataset_name", self.dataset_name))
        object.__setattr__(self, "market", Market(self.market))
        object.__setattr__(self, "capability", ProviderCapability(self.capability))
        object.__setattr__(self, "status", ProviderPolicyStatus(self.status))
        object.__setattr__(self, "attempted_order", tuple(_provider_id(provider_id) for provider_id in self.attempted_order))
        attempts = tuple(self.attempts)
        for attempt in attempts:
            if type(attempt) is not ProviderFallbackAttempt:
                raise ProviderPolicyError("attempts must contain ProviderFallbackAttempt values")
        object.__setattr__(self, "attempts", attempts)
        object.__setattr__(self, "selected_provider_id", _optional_provider_id(self.selected_provider_id))
        conflicts = tuple(self.conflicts)
        for conflict in conflicts:
            if type(conflict) is not ProviderConflictRecord:
                raise ProviderPolicyError("conflicts must contain ProviderConflictRecord values")
        object.__setattr__(self, "conflicts", conflicts)
        object.__setattr__(self, "trace_id", _optional_string(self.trace_id))
        object.__setattr__(self, "run_id", _optional_string(self.run_id))
        object.__setattr__(self, "stage_id", _optional_string(self.stage_id))

    def to_record(self) -> dict[str, object]:
        return {
            "policy_id": self.policy_id,
            "dataset_name": self.dataset_name,
            "market": self.market.value,
            "capability": self.capability.value,
            "status": self.status.value,
            "attempted_order": list(self.attempted_order),
            "attempts": [attempt.to_record() for attempt in self.attempts],
            "selected_provider_id": self.selected_provider_id,
            "conflicts": [conflict.to_record() for conflict in self.conflicts],
            "trace_id": self.trace_id,
            "run_id": self.run_id,
            "stage_id": self.stage_id,
        }


@dataclass(frozen=True, slots=True)
class ProviderSelectionResult:
    status: ProviderPolicyStatus | str
    trace: ProviderFallbackTrace
    selected_batch: DataBatch[Mapping[str, object]] | None = None
    selected_provider_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "status", ProviderPolicyStatus(self.status))
        if type(self.trace) is not ProviderFallbackTrace:
            raise ProviderPolicyError("trace must be ProviderFallbackTrace")
        if self.selected_batch is not None and type(self.selected_batch) is not DataBatch:
            raise ProviderPolicyError("selected_batch must be a DataBatch")
        object.__setattr__(self, "selected_provider_id", _optional_provider_id(self.selected_provider_id))


@dataclass(frozen=True, slots=True)
class ProviderPolicyEngine:
    policy: ProviderPolicy

    def __post_init__(self) -> None:
        if type(self.policy) is not ProviderPolicy:
            raise ProviderPolicyError("policy must be ProviderPolicy")

    def select(
        self,
        request: ProviderSelectionRequest,
        *,
        provider_results: Mapping[str, DataBatch[Mapping[str, object]] | ProviderError],
    ) -> ProviderSelectionResult:
        if type(request) is not ProviderSelectionRequest:
            raise ProviderPolicyError("request must be ProviderSelectionRequest")
        if request.dataset_name != self.policy.dataset:
            raise ProviderPolicyError("request dataset_name must match policy dataset")
        normalized_results = {_provider_id(provider_id): result for provider_id, result in provider_results.items()}
        attempted_order = self.policy.ordered_provider_ids(request)
        attempts: list[ProviderFallbackAttempt] = []

        for provider_id in attempted_order:
            if provider_id not in normalized_results:
                continue
            source = self.policy.sources[provider_id]
            outcome = normalized_results[provider_id]
            if isinstance(outcome, ProviderError):
                attempts.append(_attempt_from_provider_error(source, outcome))
                continue
            if type(outcome) is not DataBatch:
                raise ProviderPolicyError("provider_results must contain DataBatch or ProviderError values")

            rejection = _rejection_for_batch(
                provider_id=provider_id,
                batch=outcome,
                request=request,
            )
            if rejection is not None:
                attempts.append(
                    _attempt_from_batch(
                        source,
                        outcome,
                        status=ProviderFallbackAttemptStatus.REJECTED,
                        reason=rejection.reason,
                        missing_fields=rejection.missing_fields,
                        quality_status=request.quality_status_by_provider.get(provider_id),
                    )
                )
                continue

            conflicts = _cross_provider_conflicts(
                provider_id=provider_id,
                batch=outcome,
                request=request,
                policy=self.policy,
                provider_results=normalized_results,
            )
            if conflicts:
                attempts.append(
                    _attempt_from_batch(
                        source,
                        outcome,
                        status=ProviderFallbackAttemptStatus.QUARANTINED,
                        reason="cross_provider_conflict",
                        quality_status=request.quality_status_by_provider.get(provider_id),
                    )
                )
                trace = _trace(
                    policy=self.policy,
                    request=request,
                    status=ProviderPolicyStatus.QUARANTINED,
                    attempted_order=attempted_order,
                    attempts=attempts,
                    conflicts=conflicts,
                    selected_provider_id=None,
                )
                return ProviderSelectionResult(
                    status=ProviderPolicyStatus.QUARANTINED,
                    trace=trace,
                    selected_batch=None,
                    selected_provider_id=None,
                )

            attempts.append(
                _attempt_from_batch(
                    source,
                    outcome,
                    status=ProviderFallbackAttemptStatus.SELECTED,
                    quality_status=request.quality_status_by_provider.get(provider_id),
                )
            )
            trace = _trace(
                policy=self.policy,
                request=request,
                status=ProviderPolicyStatus.SELECTED,
                attempted_order=attempted_order,
                attempts=attempts,
                selected_provider_id=provider_id,
            )
            return ProviderSelectionResult(
                status=ProviderPolicyStatus.SELECTED,
                trace=trace,
                selected_batch=outcome,
                selected_provider_id=provider_id,
            )

        trace = _trace(
            policy=self.policy,
            request=request,
            status=ProviderPolicyStatus.EXHAUSTED,
            attempted_order=attempted_order,
            attempts=attempts,
            selected_provider_id=None,
        )
        return ProviderSelectionResult(status=ProviderPolicyStatus.EXHAUSTED, trace=trace)


@dataclass(frozen=True, slots=True)
class _BatchRejection:
    reason: str
    missing_fields: tuple[str, ...] = ()


def _attempt_from_provider_error(source: ProviderPolicySource, error: ProviderError) -> ProviderFallbackAttempt:
    return ProviderFallbackAttempt(
        provider_id=source.provider_id,
        status=ProviderFallbackAttemptStatus.REJECTED,
        reason=f"provider_{error.category.value}",
        provider_error_category=error.category.value,
        message=error.message,
        quality_score=source.quality_score,
    )


def _attempt_from_batch(
    source: ProviderPolicySource,
    batch: DataBatch[Mapping[str, object]],
    *,
    status: ProviderFallbackAttemptStatus,
    reason: str | None = None,
    missing_fields: Sequence[str] = (),
    quality_status: DataQualityStatus | None = None,
) -> ProviderFallbackAttempt:
    return ProviderFallbackAttempt(
        provider_id=source.provider_id,
        status=status,
        reason=reason,
        missing_fields=missing_fields,
        quality_status=quality_status,
        fresh_until=batch.fresh_until,
        source_timestamp=batch.provenance.source_timestamp,
        raw_response_sha256=batch.provenance.raw_response_sha256,
        quality_score=source.quality_score,
    )


def _rejection_for_batch(
    *,
    provider_id: str,
    batch: DataBatch[Mapping[str, object]],
    request: ProviderSelectionRequest,
) -> _BatchRejection | None:
    if batch.is_stale(at=request.evaluation_time):
        return _BatchRejection(reason="stale")
    quality_status = request.quality_status_by_provider.get(provider_id)
    if quality_status in {DataQualityStatus.QUARANTINE, DataQualityStatus.BLOCKING}:
        return _BatchRejection(reason=f"quality_{quality_status.value}")
    missing_fields = _missing_fields(batch.records, request.required_fields)
    if missing_fields:
        return _BatchRejection(reason="missing_fields", missing_fields=missing_fields)
    return None


def _missing_fields(records: Sequence[Mapping[str, object]], required_fields: Sequence[str]) -> tuple[str, ...]:
    missing: list[str] = []
    for field_name in required_fields:
        if any(field_name not in record or record.get(field_name) is None for record in records):
            missing.append(field_name)
    return tuple(missing)


def _cross_provider_conflicts(
    *,
    provider_id: str,
    batch: DataBatch[Mapping[str, object]],
    request: ProviderSelectionRequest,
    policy: ProviderPolicy,
    provider_results: Mapping[str, DataBatch[Mapping[str, object]] | ProviderError],
) -> tuple[ProviderConflictRecord, ...]:
    cross_provider = policy.cross_check_provider_id
    threshold = policy.max_close_diff_bps
    if not cross_provider or threshold is None or cross_provider == provider_id:
        return ()
    cross_result = provider_results.get(cross_provider)
    if type(cross_result) is not DataBatch:
        return ()
    if _rejection_for_batch(provider_id=cross_provider, batch=cross_result, request=request) is not None:
        return ()

    conflicts: list[ProviderConflictRecord] = []
    cross_records_by_key = {_record_key(record): record for record in cross_result.records}
    for record in batch.records:
        key = _record_key(record)
        if key not in cross_records_by_key:
            continue
        if "close" not in record or "close" not in cross_records_by_key[key]:
            continue
        primary_close = _required_number("close", record["close"])
        cross_close = _required_number("close", cross_records_by_key[key]["close"])
        if primary_close == 0:
            continue
        diff_bps = abs(cross_close - primary_close) / abs(primary_close) * 10_000
        if diff_bps > threshold:
            conflicts.append(
                ProviderConflictRecord(
                    field_name="close",
                    primary_key=_primary_key_record(record),
                    provider_values={provider_id: primary_close, cross_provider: cross_close},
                    observed_diff_bps=diff_bps,
                    threshold_bps=threshold,
                )
            )
    return tuple(conflicts)


def _record_key(record: Mapping[str, object]) -> tuple[str, str]:
    instrument_id = _required_string("instrument_id", record.get("instrument_id"))
    trade_date = record.get("trade_date", record.get("date"))
    return (instrument_id, _required_string("date", trade_date))


def _primary_key_record(record: Mapping[str, object]) -> dict[str, str]:
    instrument_id, trade_date = _record_key(record)
    date_key = "trade_date" if "trade_date" in record else "date"
    return {"instrument_id": instrument_id, date_key: trade_date}


def _trace(
    *,
    policy: ProviderPolicy,
    request: ProviderSelectionRequest,
    status: ProviderPolicyStatus,
    attempted_order: Sequence[str],
    attempts: Sequence[ProviderFallbackAttempt],
    selected_provider_id: str | None,
    conflicts: Sequence[ProviderConflictRecord] = (),
) -> ProviderFallbackTrace:
    return ProviderFallbackTrace(
        policy_id=policy.policy_id,
        dataset_name=request.dataset_name,
        market=request.market,
        capability=request.capability,
        status=status,
        attempted_order=attempted_order,
        attempts=attempts,
        selected_provider_id=selected_provider_id,
        conflicts=conflicts,
        trace_id=request.trace_id,
        run_id=request.run_id,
        stage_id=request.stage_id,
    )


def _required_string(field_name: str, value: object | None) -> str:
    if type(value) is not str:
        raise ProviderPolicyError(f"{field_name} is required")
    normalized = value.strip()
    if not normalized:
        raise ProviderPolicyError(f"{field_name} is required")
    return normalized


def _optional_string(value: object | None) -> str | None:
    if value is None:
        return None
    normalized = _required_string("optional string", value)
    return normalized or None


def _provider_id(value: object) -> str:
    return _required_string("provider_id", value).lower()


def _optional_provider_id(value: object | None) -> str | None:
    if value is None:
        return None
    return _provider_id(value)


def _require_aware_datetime(field_name: str, value: object) -> None:
    if type(value) is not datetime or value.tzinfo is None or value.utcoffset() is None:
        raise ProviderPolicyError(f"{field_name} must be timezone-aware")


def _unique_tuple(values) -> tuple:
    return tuple(dict.fromkeys(values))


def _freeze_string_mapping(mapping: Mapping[str, str]) -> Mapping[str, str]:
    return MappingProxyType(
        {
            _required_string("mapping key", key): _required_string("mapping value", value)
            for key, value in sorted(mapping.items(), key=lambda item: str(item[0]))
        }
    )


def _required_number(field_name: str, value: object) -> float:
    if type(value) not in {int, float} or not isfinite(float(value)):
        raise ProviderPolicyError(f"{field_name} must be finite")
    return float(value)


def _non_negative_number(field_name: str, value: object) -> float:
    number = _required_number(field_name, value)
    if number < 0:
        raise ProviderPolicyError(f"{field_name} cannot be negative")
    return number


__all__ = [
    "ProviderConflictRecord",
    "ProviderFallbackAttempt",
    "ProviderFallbackAttemptStatus",
    "ProviderFallbackTrace",
    "ProviderPolicy",
    "ProviderPolicyEngine",
    "ProviderPolicyError",
    "ProviderPolicySource",
    "ProviderPolicyStatus",
    "ProviderSelectionRequest",
    "ProviderSelectionResult",
]
