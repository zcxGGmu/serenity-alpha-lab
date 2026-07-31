from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from math import isfinite
from types import MappingProxyType
from typing import Any

from serenity_alpha_lab.application.screening_provider import ScreeningResult
from serenity_alpha_lab.datasets.catalog import DatasetCatalogError, DatasetVersionRef
from serenity_alpha_lab.domain.instruments import InstrumentId


CANDIDATE_BATCH_CONTRACT_VERSION = "1.0.0"
CANDIDATE_BATCH_SCHEMA_NAME = "screening.candidate_batch"
CANDIDATE_BATCH_SCHEMA_VERSION = "1.0.0"


class CandidateBatchError(ValueError):
    """Raised when standardized candidate batch contract data is invalid."""


class CandidateScoreLayer(StrEnum):
    L1_PROVIDER = "l1_provider"
    L2_DETERMINISTIC = "l2_deterministic"
    L3_LLM_OVERLAY = "l3_llm_overlay"


class CandidateSourceType(StrEnum):
    SCREENING_PROVIDER = "screening_provider"
    DATASET = "dataset"
    RULE = "rule"
    LLM_OVERLAY = "llm_overlay"
    RAW_PAYLOAD = "raw_payload"


@dataclass(frozen=True, slots=True)
class CandidateSource:
    source_id: str
    source_type: CandidateSourceType | str
    dataset_name: str | None = None
    dataset_version: str | None = None
    provider_id: str | None = None
    artifact_uri: str | None = None
    observed_at: datetime | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_id", _required_string("source_id", self.source_id))
        object.__setattr__(self, "source_type", CandidateSourceType(self.source_type))
        object.__setattr__(self, "dataset_name", _optional_string(self.dataset_name))
        if self.dataset_version is not None:
            object.__setattr__(self, "dataset_version", _validate_dataset_version(self.dataset_version))
        object.__setattr__(self, "provider_id", _optional_string(self.provider_id))
        object.__setattr__(self, "artifact_uri", _optional_string(self.artifact_uri))
        if self.source_type is CandidateSourceType.DATASET:
            if self.dataset_name is None or self.dataset_version is None:
                raise CandidateBatchError("dataset sources require dataset_name and concrete Dataset Version")
        if self.observed_at is not None:
            _require_aware_datetime("observed_at", self.observed_at)
        object.__setattr__(self, "metadata", _freeze_mapping(self.metadata))

    def to_record(self) -> dict[str, Any]:
        record: dict[str, Any] = {
            "source_id": self.source_id,
            "source_type": self.source_type.value,
        }
        _set_if_present(record, "dataset_name", self.dataset_name)
        _set_if_present(record, "dataset_version", self.dataset_version)
        _set_if_present(record, "provider_id", self.provider_id)
        _set_if_present(record, "artifact_uri", self.artifact_uri)
        if self.observed_at is not None:
            record["observed_at"] = self.observed_at.isoformat()
        if self.metadata:
            record["metadata"] = _thaw_value(self.metadata)
        return record


@dataclass(frozen=True, slots=True)
class CandidateReason:
    code: str
    layer: CandidateScoreLayer | str
    message: str = ""
    direction: str = "neutral"
    weight: float | None = None
    source_ids: Sequence[str] = ()
    details: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "code", _required_string("code", self.code))
        object.__setattr__(self, "layer", CandidateScoreLayer(self.layer))
        object.__setattr__(self, "message", _optional_text(self.message))
        direction = _required_string("direction", self.direction).lower()
        if direction not in {"positive", "negative", "neutral"}:
            raise CandidateBatchError("direction must be positive, negative, or neutral")
        object.__setattr__(self, "direction", direction)
        if self.weight is not None:
            object.__setattr__(self, "weight", _finite_float("weight", self.weight, minimum=0.0))
        object.__setattr__(self, "source_ids", _string_tuple("source_id", self.source_ids))
        object.__setattr__(self, "details", _freeze_mapping(self.details))

    def to_record(self) -> dict[str, Any]:
        record: dict[str, Any] = {
            "code": self.code,
            "layer": self.layer.value,
            "message": self.message,
            "direction": self.direction,
            "source_ids": list(self.source_ids),
        }
        _set_if_present(record, "weight", self.weight)
        if self.details:
            record["details"] = _thaw_value(self.details)
        return record


@dataclass(frozen=True, slots=True)
class CandidateLayerScore:
    layer: CandidateScoreLayer | str
    score: float
    raw_score: float | None = None
    weight: float | None = None
    source_id: str | None = None
    reason_codes: Sequence[str] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "layer", CandidateScoreLayer(self.layer))
        object.__setattr__(self, "score", _finite_float("score", self.score, minimum=0.0, maximum=100.0))
        if self.raw_score is not None:
            object.__setattr__(self, "raw_score", _finite_float("raw_score", self.raw_score))
        if self.weight is not None:
            object.__setattr__(self, "weight", _finite_float("weight", self.weight, minimum=0.0))
        object.__setattr__(self, "source_id", _optional_string(self.source_id))
        object.__setattr__(self, "reason_codes", _string_tuple("reason_code", self.reason_codes))
        object.__setattr__(self, "metadata", _freeze_mapping(self.metadata))

    def to_record(self) -> dict[str, Any]:
        record: dict[str, Any] = {
            "layer": self.layer.value,
            "score": self.score,
            "reason_codes": list(self.reason_codes),
        }
        _set_if_present(record, "raw_score", self.raw_score)
        _set_if_present(record, "weight", self.weight)
        _set_if_present(record, "source_id", self.source_id)
        if self.metadata:
            record["metadata"] = _thaw_value(self.metadata)
        return record


@dataclass(frozen=True, slots=True)
class Candidate:
    instrument: InstrumentId
    rank: int
    final_score: float
    scores: Sequence[CandidateLayerScore] | Mapping[CandidateScoreLayer | str, CandidateLayerScore]
    name: str | None = None
    reasons: Sequence[CandidateReason] = ()
    source_ids: Sequence[str] = ()
    raw_payload: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if type(self.instrument) is not InstrumentId:
            raise CandidateBatchError("instrument must be an InstrumentId")
        if type(self.rank) is not int or self.rank <= 0:
            raise CandidateBatchError("rank must be a positive integer")
        object.__setattr__(
            self,
            "final_score",
            _finite_float("final_score", self.final_score, minimum=0.0, maximum=100.0),
        )
        object.__setattr__(self, "name", _optional_string(self.name))
        object.__setattr__(self, "scores", _normalize_scores(self.scores))
        missing_layers = [
            layer.name
            for layer in (CandidateScoreLayer.L1_PROVIDER, CandidateScoreLayer.L2_DETERMINISTIC)
            if layer not in self.scores
        ]
        if missing_layers:
            raise CandidateBatchError(f"candidate scores must include {', '.join(missing_layers)}")
        reasons = tuple(self.reasons)
        for reason in reasons:
            if type(reason) is not CandidateReason:
                raise CandidateBatchError("reasons must contain CandidateReason values")
        object.__setattr__(self, "reasons", reasons)
        object.__setattr__(self, "source_ids", _string_tuple("source_id", self.source_ids))
        object.__setattr__(self, "raw_payload", _freeze_mapping(self.raw_payload))

    def score(self, layer: CandidateScoreLayer | str) -> CandidateLayerScore:
        normalized_layer = CandidateScoreLayer(layer)
        try:
            return self.scores[normalized_layer]
        except KeyError as exc:
            raise CandidateBatchError(f"candidate score not found: {normalized_layer.value}") from exc

    def to_record(self) -> dict[str, Any]:
        record: dict[str, Any] = {
            "instrument_id": self.instrument.canonical,
            "market": self.instrument.market.value,
            "exchange": self.instrument.exchange.value,
            "asset_type": self.instrument.asset_type.value,
            "rank": self.rank,
            "final_score": self.final_score,
            "scores": {
                layer.value: score.to_record()
                for layer, score in sorted(self.scores.items(), key=lambda item: item[0].value)
            },
            "reasons": [reason.to_record() for reason in self.reasons],
            "source_ids": list(self.source_ids),
        }
        _set_if_present(record, "name", self.name)
        if self.raw_payload:
            record["raw_payload"] = _thaw_value(self.raw_payload)
        return record


@dataclass(frozen=True, slots=True)
class CandidateBatch:
    batch_id: str
    provider_id: str
    strategy_id: str
    strategy_version: str
    market: str
    dataset_versions: Mapping[str, str]
    source_snapshot_at: datetime
    discovered_at: datetime
    candidates: Sequence[Candidate]
    snapshot_count: int
    after_filter_count: int
    provider_version: str = ""
    requested_at: datetime | None = None
    received_at: datetime | None = None
    provider_run_id: str | None = None
    sources: Sequence[CandidateSource] = ()
    contract_version: str = CANDIDATE_BATCH_CONTRACT_VERSION
    schema_name: str = CANDIDATE_BATCH_SCHEMA_NAME
    schema_version: str = CANDIDATE_BATCH_SCHEMA_VERSION
    warnings: Sequence[str] = ()
    source_errors: Sequence[str] = ()
    llm_overlay_enabled: bool = False
    llm_coverage: float | None = None
    trace_id: str | None = None
    platform_run_id: str | None = None
    stage_id: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "batch_id", _required_string("batch_id", self.batch_id))
        object.__setattr__(self, "provider_id", _required_string("provider_id", self.provider_id))
        object.__setattr__(self, "provider_version", _optional_text(self.provider_version))
        object.__setattr__(self, "strategy_id", _required_string("strategy_id", self.strategy_id))
        object.__setattr__(self, "strategy_version", _required_string("strategy_version", self.strategy_version))
        object.__setattr__(self, "market", _required_string("market", self.market))
        object.__setattr__(self, "dataset_versions", _normalize_dataset_versions(self.dataset_versions))
        _require_aware_datetime("source_snapshot_at", self.source_snapshot_at)
        _require_aware_datetime("discovered_at", self.discovered_at)
        if self.discovered_at < self.source_snapshot_at:
            raise CandidateBatchError("discovered_at cannot be before source_snapshot_at")
        if self.requested_at is not None:
            _require_aware_datetime("requested_at", self.requested_at)
        if self.received_at is not None:
            _require_aware_datetime("received_at", self.received_at)
        if self.requested_at is not None and self.received_at is not None and self.received_at < self.requested_at:
            raise CandidateBatchError("received_at cannot be before requested_at")
        _require_non_negative_int("snapshot_count", self.snapshot_count)
        _require_non_negative_int("after_filter_count", self.after_filter_count)
        if self.after_filter_count > self.snapshot_count:
            raise CandidateBatchError("after_filter_count cannot exceed snapshot_count")
        object.__setattr__(self, "provider_run_id", _optional_string(self.provider_run_id))
        sources = tuple(self.sources)
        for source in sources:
            if type(source) is not CandidateSource:
                raise CandidateBatchError("sources must contain CandidateSource values")
        source_ids = {source.source_id for source in sources}
        if len(source_ids) != len(sources):
            raise CandidateBatchError("duplicate source ids are not allowed")
        object.__setattr__(self, "sources", sources)
        candidates = tuple(self.candidates)
        for candidate in candidates:
            if type(candidate) is not Candidate:
                raise CandidateBatchError("candidates must contain Candidate values")
        _validate_candidate_ranks(candidates)
        for candidate in candidates:
            if CandidateScoreLayer.L3_LLM_OVERLAY in candidate.scores and not self.llm_overlay_enabled:
                raise CandidateBatchError("L3_LLM_OVERLAY requires llm_overlay_enabled=True")
            if source_ids:
                unknown_sources = [source_id for source_id in candidate.source_ids if source_id not in source_ids]
                if unknown_sources:
                    raise CandidateBatchError(f"candidate references unknown source ids: {', '.join(unknown_sources)}")
        object.__setattr__(self, "candidates", candidates)
        object.__setattr__(self, "contract_version", _required_string("contract_version", self.contract_version))
        object.__setattr__(self, "schema_name", _required_string("schema_name", self.schema_name))
        object.__setattr__(self, "schema_version", _required_string("schema_version", self.schema_version))
        object.__setattr__(self, "warnings", _string_tuple("warning", self.warnings))
        object.__setattr__(self, "source_errors", _string_tuple("source_error", self.source_errors))
        if type(self.llm_overlay_enabled) is not bool:
            raise CandidateBatchError("llm_overlay_enabled must be boolean")
        if self.llm_coverage is not None:
            object.__setattr__(
                self,
                "llm_coverage",
                _finite_float("llm_coverage", self.llm_coverage, minimum=0.0, maximum=1.0),
            )
        object.__setattr__(self, "trace_id", _optional_string(self.trace_id))
        object.__setattr__(self, "platform_run_id", _optional_string(self.platform_run_id))
        object.__setattr__(self, "stage_id", _optional_string(self.stage_id))
        object.__setattr__(self, "metadata", _freeze_mapping(self.metadata))

    @property
    def candidate_count(self) -> int:
        return len(self.candidates)

    def to_record(self) -> dict[str, Any]:
        record: dict[str, Any] = {
            "batch_id": self.batch_id,
            "contract_version": self.contract_version,
            "schema_name": self.schema_name,
            "schema_version": self.schema_version,
            "provider_id": self.provider_id,
            "provider_version": self.provider_version,
            "strategy_id": self.strategy_id,
            "strategy_version": self.strategy_version,
            "market": self.market,
            "dataset_versions": dict(self.dataset_versions),
            "source_snapshot_at": self.source_snapshot_at.isoformat(),
            "discovered_at": self.discovered_at.isoformat(),
            "candidate_count": self.candidate_count,
            "snapshot_count": self.snapshot_count,
            "after_filter_count": self.after_filter_count,
            "candidates": [candidate.to_record() for candidate in self.candidates],
            "sources": [source.to_record() for source in self.sources],
            "warnings": list(self.warnings),
            "source_errors": list(self.source_errors),
            "llm_overlay_enabled": self.llm_overlay_enabled,
        }
        _set_datetime_if_present(record, "requested_at", self.requested_at)
        _set_datetime_if_present(record, "received_at", self.received_at)
        _set_if_present(record, "provider_run_id", self.provider_run_id)
        _set_if_present(record, "llm_coverage", self.llm_coverage)
        _set_if_present(record, "trace_id", self.trace_id)
        _set_if_present(record, "platform_run_id", self.platform_run_id)
        _set_if_present(record, "stage_id", self.stage_id)
        if self.metadata:
            record["metadata"] = _thaw_value(self.metadata)
        return record


def candidate_batch_from_screening_result(
    result: ScreeningResult,
    *,
    candidates: Sequence[Candidate],
    source_snapshot_at: datetime,
    sources: Sequence[CandidateSource] = (),
    batch_id: str | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> CandidateBatch:
    if type(result) is not ScreeningResult:
        raise CandidateBatchError("result must be a ScreeningResult")
    return CandidateBatch(
        batch_id=batch_id or f"cb_{result.provider_id}_{result.strategy_id}_{result.received_at.isoformat()}",
        provider_id=result.provider_id,
        provider_version=result.provider_version,
        strategy_id=result.strategy_id,
        strategy_version=result.strategy_version,
        market=result.market,
        dataset_versions=result.dataset_versions,
        source_snapshot_at=source_snapshot_at,
        discovered_at=result.received_at,
        requested_at=result.requested_at,
        received_at=result.received_at,
        provider_run_id=result.provider_run_id,
        snapshot_count=result.snapshot_count,
        after_filter_count=result.after_filter_count,
        candidates=candidates,
        sources=sources,
        warnings=result.warnings,
        source_errors=result.source_errors,
        llm_overlay_enabled=result.llm_overlay_enabled,
        llm_coverage=result.llm_coverage,
        trace_id=result.trace_id,
        platform_run_id=result.platform_run_id,
        stage_id=result.stage_id,
        metadata=metadata or {},
    )


def _normalize_scores(
    scores: Sequence[CandidateLayerScore] | Mapping[CandidateScoreLayer | str, CandidateLayerScore],
) -> Mapping[CandidateScoreLayer, CandidateLayerScore]:
    if isinstance(scores, Mapping):
        score_values = tuple(scores.values())
    else:
        score_values = tuple(scores)
    normalized: dict[CandidateScoreLayer, CandidateLayerScore] = {}
    for score in score_values:
        if type(score) is not CandidateLayerScore:
            raise CandidateBatchError("scores must contain CandidateLayerScore values")
        if score.layer in normalized:
            raise CandidateBatchError(f"duplicate score layer: {score.layer.value}")
        normalized[score.layer] = score
    return MappingProxyType(normalized)


def _validate_candidate_ranks(candidates: Sequence[Candidate]) -> None:
    ranks = [candidate.rank for candidate in candidates]
    if len(set(ranks)) != len(ranks):
        raise CandidateBatchError("duplicate candidate ranks are not allowed")
    if ranks != sorted(ranks):
        raise CandidateBatchError("candidates must be ordered by ascending rank")


def _normalize_dataset_versions(dataset_versions: Mapping[str, str]) -> Mapping[str, str]:
    if not isinstance(dataset_versions, Mapping):
        raise CandidateBatchError("dataset_versions must map dataset names to concrete Dataset Version ids")
    if not dataset_versions:
        raise CandidateBatchError("dataset_versions are required and must reference concrete Dataset Version ids")
    normalized: dict[str, str] = {}
    for dataset_name, version_id in dataset_versions.items():
        name = _required_string("dataset_name", dataset_name)
        normalized[name] = _validate_dataset_version(version_id)
    return MappingProxyType(normalized)


def _validate_dataset_version(version_id: str) -> str:
    version = _required_string("dataset_version", version_id)
    if version.lower() == "latest":
        raise CandidateBatchError("CandidateBatch requires concrete Dataset Version ids; latest alias is not allowed")
    try:
        DatasetVersionRef.version(version)
    except DatasetCatalogError as exc:
        raise CandidateBatchError(f"CandidateBatch requires concrete Dataset Version ids; invalid {version}") from exc
    return version


def _required_string(field_name: str, value: object) -> str:
    if type(value) is not str:
        raise CandidateBatchError(f"{field_name} is required")
    stripped = value.strip()
    if not stripped:
        raise CandidateBatchError(f"{field_name} is required")
    return stripped


def _optional_string(value: object) -> str | None:
    if value is None:
        return None
    return _required_string("optional string", value)


def _optional_text(value: object) -> str:
    if value is None:
        return ""
    if type(value) is not str:
        raise CandidateBatchError("optional text must be a string")
    return value.strip()


def _string_tuple(field_name: str, values: Sequence[str]) -> tuple[str, ...]:
    if isinstance(values, str):
        raise CandidateBatchError(f"{field_name} values must be a sequence")
    return tuple(_required_string(field_name, value) for value in values)


def _finite_float(
    field_name: str,
    value: float,
    *,
    minimum: float | None = None,
    maximum: float | None = None,
) -> float:
    if type(value) not in {int, float} or not isfinite(float(value)):
        raise CandidateBatchError(f"{field_name} must be finite")
    normalized = float(value)
    if minimum is not None and normalized < minimum:
        raise CandidateBatchError(f"{field_name} must be >= {minimum}")
    if maximum is not None and normalized > maximum:
        raise CandidateBatchError(f"{field_name} must be <= {maximum}")
    return normalized


def _require_non_negative_int(field_name: str, value: int) -> None:
    if type(value) is not int or value < 0:
        raise CandidateBatchError(f"{field_name} cannot be negative")


def _require_aware_datetime(field_name: str, value: datetime) -> None:
    if type(value) is not datetime or value.tzinfo is None or value.utcoffset() is None:
        raise CandidateBatchError(f"{field_name} must be timezone-aware")


def _freeze_mapping(mapping: Mapping[str, Any]) -> Mapping[str, Any]:
    if not isinstance(mapping, Mapping):
        raise CandidateBatchError("value must be a mapping")
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


def _thaw_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _thaw_value(inner) for key, inner in value.items()}
    if isinstance(value, tuple):
        return [_thaw_value(item) for item in value]
    if isinstance(value, bytes):
        return value.decode("utf-8")
    return value


def _set_if_present(record: dict[str, Any], key: str, value: Any) -> None:
    if value is not None:
        record[key] = value


def _set_datetime_if_present(record: dict[str, Any], key: str, value: datetime | None) -> None:
    if value is not None:
        record[key] = value.isoformat()


__all__ = [
    "CANDIDATE_BATCH_CONTRACT_VERSION",
    "CANDIDATE_BATCH_SCHEMA_NAME",
    "CANDIDATE_BATCH_SCHEMA_VERSION",
    "Candidate",
    "CandidateBatch",
    "CandidateBatchError",
    "CandidateLayerScore",
    "CandidateReason",
    "CandidateScoreLayer",
    "CandidateSource",
    "CandidateSourceType",
    "candidate_batch_from_screening_result",
]
