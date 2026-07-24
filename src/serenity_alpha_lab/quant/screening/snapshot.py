from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import StrEnum
from math import isfinite
from types import MappingProxyType
from typing import Any

from serenity_alpha_lab.datasets.catalog import DatasetCatalogError, DatasetVersionRef
from serenity_alpha_lab.domain.artifacts import ArtifactManifest, ArtifactRetentionTier, ArtifactStore
from serenity_alpha_lab.domain.instruments import InstrumentId
from serenity_alpha_lab.quant.screening.pipeline import (
    ScreenPipelineCandidate,
    ScreenPipelineExclusion,
    ScreenPipelineSnapshot,
    ScreenPipelineStage,
)


SCREEN_SNAPSHOT_CONTRACT_VERSION = "quant.screen_snapshot@1.0.0"
SCREEN_SNAPSHOT_SCHEMA_NAME = "quant.screen_snapshot"
SCREEN_SNAPSHOT_SCHEMA_VERSION = "1.0.0"
SCREEN_SNAPSHOT_CONTENT_TYPE = "application/vnd.serenity.quant.screen-snapshot+json"

_SCREEN_SNAPSHOT_ID_RE = re.compile(r"^ssn_[0-9a-f]{32}$")


class ScreenSnapshotError(ValueError):
    """Raised when result-facing screen snapshot data violates the contract."""


class ScreenSnapshotStatus(StrEnum):
    PASSED = "passed"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class ScreenExplanationStep:
    stage: ScreenPipelineStage | str
    rule_id: str
    reason: str
    authoritative: bool = True
    scores: Mapping[str, float] = field(default_factory=dict)
    factor_contributions: Mapping[str, float] = field(default_factory=dict)
    source_ids: Sequence[str] = ()
    details: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "stage", ScreenPipelineStage(self.stage))
        object.__setattr__(self, "rule_id", _required_string("rule_id", self.rule_id))
        object.__setattr__(self, "reason", _required_string("reason", self.reason))
        if type(self.authoritative) is not bool:
            raise ScreenSnapshotError("authoritative must be a bool")
        object.__setattr__(self, "scores", _freeze_numeric_mapping(self.scores))
        object.__setattr__(self, "factor_contributions", _freeze_numeric_mapping(self.factor_contributions))
        object.__setattr__(self, "source_ids", _string_tuple("source_id", self.source_ids))
        object.__setattr__(self, "details", _freeze_json_mapping(self.details))

    def to_record(self) -> dict[str, Any]:
        record: dict[str, Any] = {
            "stage": self.stage.value,
            "rule_id": self.rule_id,
            "reason": self.reason,
            "authoritative": self.authoritative,
            "scores": dict(self.scores),
            "factor_contributions": dict(self.factor_contributions),
            "source_ids": list(self.source_ids),
        }
        if self.details:
            record["details"] = _thaw_value(self.details)
        return record


@dataclass(frozen=True, slots=True)
class ScreenSnapshotResult:
    instrument_id: str
    status: ScreenSnapshotStatus | str
    explanation_steps: Sequence[ScreenExplanationStep]
    scores: Mapping[str, float] = field(default_factory=dict)
    factor_contributions: Mapping[str, float] = field(default_factory=dict)
    rank: int | None = None
    failed_stage: ScreenPipelineStage | str | None = None
    final_score: float | None = None
    source_rank: int | None = None
    industry: str | None = None
    reason_codes: Sequence[str] = ()
    summary: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "instrument_id", _canonical_instrument_id(self.instrument_id))
        object.__setattr__(self, "status", ScreenSnapshotStatus(self.status))
        object.__setattr__(self, "scores", _freeze_numeric_mapping(self.scores))
        object.__setattr__(self, "factor_contributions", _freeze_numeric_mapping(self.factor_contributions))
        if self.rank is not None and (type(self.rank) is not int or self.rank <= 0):
            raise ScreenSnapshotError("rank must be a positive integer")
        if self.final_score is not None:
            object.__setattr__(self, "final_score", _finite_float("final_score", self.final_score))
        if self.source_rank is not None and (type(self.source_rank) is not int or self.source_rank <= 0):
            raise ScreenSnapshotError("source_rank must be a positive integer")
        object.__setattr__(self, "industry", _optional_string(self.industry))
        object.__setattr__(self, "reason_codes", _string_tuple("reason_code", self.reason_codes))
        object.__setattr__(self, "summary", _optional_text(self.summary))

        failed_stage = self.failed_stage
        if failed_stage is not None:
            failed_stage = ScreenPipelineStage(failed_stage)
        object.__setattr__(self, "failed_stage", failed_stage)

        steps = tuple(self.explanation_steps)
        if not steps:
            raise ScreenSnapshotError("explanation_steps are required")
        for step in steps:
            if type(step) is not ScreenExplanationStep:
                raise ScreenSnapshotError("explanation_steps must contain ScreenExplanationStep values")
        object.__setattr__(self, "explanation_steps", steps)

        if self.status is ScreenSnapshotStatus.PASSED:
            if self.rank is None:
                raise ScreenSnapshotError("passed results require rank")
            if self.failed_stage is not None:
                raise ScreenSnapshotError("passed results cannot have failed_stage")
            if self.final_score is None:
                raise ScreenSnapshotError("passed results require final_score")
        else:
            if self.rank is not None:
                raise ScreenSnapshotError("failed results cannot have rank")
            if self.failed_stage is None:
                raise ScreenSnapshotError("failed results require failed_stage")

    def to_record(self) -> dict[str, Any]:
        record: dict[str, Any] = {
            "instrument_id": self.instrument_id,
            "status": self.status.value,
            "rank": self.rank,
            "failed_stage": self.failed_stage.value if self.failed_stage is not None else None,
            "final_score": self.final_score,
            "source_rank": self.source_rank,
            "industry": self.industry,
            "scores": dict(self.scores),
            "factor_contributions": dict(self.factor_contributions),
            "reason_codes": list(self.reason_codes),
            "summary": self.summary,
            "explanation_steps": [step.to_record() for step in self.explanation_steps],
        }
        return record


@dataclass(frozen=True, slots=True)
class ScreenSnapshot:
    pipeline_snapshot_id: str
    definition_version_id: str
    as_of: date
    dataset_versions: Mapping[str, str]
    results: Sequence[ScreenSnapshotResult]
    created_at: datetime
    trace_id: str | None = None
    run_id: str | None = None
    stage_id: str | None = None
    screen_snapshot_id: str | None = None
    contract_version: str = SCREEN_SNAPSHOT_CONTRACT_VERSION
    schema_name: str = SCREEN_SNAPSHOT_SCHEMA_NAME
    schema_version: str = SCREEN_SNAPSHOT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "pipeline_snapshot_id", _required_string("pipeline_snapshot_id", self.pipeline_snapshot_id))
        object.__setattr__(self, "definition_version_id", _required_string("definition_version_id", self.definition_version_id))
        _require_date("as_of", self.as_of)
        _require_aware_datetime("created_at", self.created_at)
        object.__setattr__(self, "dataset_versions", _normalize_dataset_versions(self.dataset_versions))
        object.__setattr__(self, "trace_id", _optional_string(self.trace_id))
        object.__setattr__(self, "run_id", _optional_string(self.run_id))
        object.__setattr__(self, "stage_id", _optional_string(self.stage_id))
        object.__setattr__(self, "contract_version", _required_string("contract_version", self.contract_version))
        object.__setattr__(self, "schema_name", _required_string("schema_name", self.schema_name))
        object.__setattr__(self, "schema_version", _required_string("schema_version", self.schema_version))

        results = tuple(self.results)
        if not results:
            raise ScreenSnapshotError("results are required")
        for result in results:
            if type(result) is not ScreenSnapshotResult:
                raise ScreenSnapshotError("results must contain ScreenSnapshotResult values")
        instrument_ids = [result.instrument_id for result in results]
        if len(set(instrument_ids)) != len(instrument_ids):
            raise ScreenSnapshotError("duplicate result instrument_id values are not allowed")

        passed = sorted(
            (result for result in results if result.status is ScreenSnapshotStatus.PASSED),
            key=lambda item: item.rank or 0,
        )
        if [result.rank for result in passed] != list(range(1, len(passed) + 1)):
            raise ScreenSnapshotError("passed result ranks must be contiguous")
        failed = sorted(
            (result for result in results if result.status is ScreenSnapshotStatus.FAILED),
            key=lambda item: ((item.failed_stage.value if item.failed_stage else ""), item.instrument_id),
        )
        object.__setattr__(self, "results", tuple(passed + failed))

        snapshot_id = self.screen_snapshot_id
        if snapshot_id is None:
            snapshot_id = _stable_id("ssn", self._identity_record())
        elif not _SCREEN_SNAPSHOT_ID_RE.fullmatch(snapshot_id):
            raise ScreenSnapshotError("screen_snapshot_id must be ssn_<hex>")
        object.__setattr__(self, "screen_snapshot_id", snapshot_id)

    @property
    def passed_count(self) -> int:
        return sum(1 for result in self.results if result.status is ScreenSnapshotStatus.PASSED)

    @property
    def failed_count(self) -> int:
        return sum(1 for result in self.results if result.status is ScreenSnapshotStatus.FAILED)

    @property
    def passed_instrument_ids(self) -> tuple[str, ...]:
        return tuple(result.instrument_id for result in self.results if result.status is ScreenSnapshotStatus.PASSED)

    def result_for(self, instrument_id: str) -> ScreenSnapshotResult:
        canonical = _canonical_instrument_id(instrument_id)
        for result in self.results:
            if result.instrument_id == canonical:
                return result
        raise ScreenSnapshotError(f"screen result not found: {canonical}")

    def to_json_bytes(self) -> bytes:
        return json.dumps(self.to_record(), ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")

    def to_record(self) -> dict[str, Any]:
        record = self._identity_record()
        record["screen_snapshot_id"] = self.screen_snapshot_id
        return record

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
            schema_name=SCREEN_SNAPSHOT_SCHEMA_NAME,
            schema_version=SCREEN_SNAPSHOT_SCHEMA_VERSION,
            content_type=SCREEN_SNAPSHOT_CONTENT_TYPE,
            produced_by_run_id=run_id,
            produced_by_stage_id=stage_id,
            retention_tier=retention_tier,
            created_at=self.created_at,
        )

    def _identity_record(self) -> dict[str, Any]:
        result_records = [result.to_record() for result in self.results]
        return {
            "schema_name": self.schema_name,
            "schema_version": self.schema_version,
            "contract_version": self.contract_version,
            "pipeline_snapshot_id": self.pipeline_snapshot_id,
            "definition_version_id": self.definition_version_id,
            "as_of": self.as_of.isoformat(),
            "dataset_versions": dict(self.dataset_versions),
            "created_at": self.created_at.isoformat(),
            "trace_id": self.trace_id,
            "run_id": self.run_id,
            "stage_id": self.stage_id,
            "passed_count": self.passed_count,
            "failed_count": self.failed_count,
            "results": result_records,
            "results_by_instrument": {result["instrument_id"]: result for result in result_records},
        }


@dataclass(frozen=True, slots=True)
class ScreenSnapshotStatusChange:
    instrument_id: str
    previous_status: ScreenSnapshotStatus | str
    current_status: ScreenSnapshotStatus | str

    def __post_init__(self) -> None:
        object.__setattr__(self, "instrument_id", _canonical_instrument_id(self.instrument_id))
        object.__setattr__(self, "previous_status", ScreenSnapshotStatus(self.previous_status))
        object.__setattr__(self, "current_status", ScreenSnapshotStatus(self.current_status))
        if self.previous_status is self.current_status:
            raise ScreenSnapshotError("status change requires different statuses")

    def to_record(self) -> dict[str, str]:
        return {
            "instrument_id": self.instrument_id,
            "previous_status": self.previous_status.value,
            "current_status": self.current_status.value,
        }


@dataclass(frozen=True, slots=True)
class ScreenSnapshotRankChange:
    instrument_id: str
    previous_rank: int
    current_rank: int

    def __post_init__(self) -> None:
        object.__setattr__(self, "instrument_id", _canonical_instrument_id(self.instrument_id))
        if type(self.previous_rank) is not int or self.previous_rank <= 0:
            raise ScreenSnapshotError("previous_rank must be a positive integer")
        if type(self.current_rank) is not int or self.current_rank <= 0:
            raise ScreenSnapshotError("current_rank must be a positive integer")
        if self.previous_rank == self.current_rank:
            raise ScreenSnapshotError("rank change requires different ranks")

    def to_record(self) -> dict[str, object]:
        return {
            "instrument_id": self.instrument_id,
            "previous_rank": self.previous_rank,
            "current_rank": self.current_rank,
            "delta": self.current_rank - self.previous_rank,
        }


@dataclass(frozen=True, slots=True)
class ScreenSnapshotScoreDelta:
    instrument_id: str
    previous_score: float
    current_score: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "instrument_id", _canonical_instrument_id(self.instrument_id))
        object.__setattr__(self, "previous_score", _finite_float("previous_score", self.previous_score))
        object.__setattr__(self, "current_score", _finite_float("current_score", self.current_score))

    @property
    def delta(self) -> float:
        return self.current_score - self.previous_score

    def to_record(self) -> dict[str, object]:
        return {
            "instrument_id": self.instrument_id,
            "previous_score": self.previous_score,
            "current_score": self.current_score,
            "delta": self.delta,
        }


@dataclass(frozen=True, slots=True)
class ScreenSnapshotComparison:
    previous_screen_snapshot_id: str
    current_screen_snapshot_id: str
    added: Sequence[str]
    removed: Sequence[str]
    retained: Sequence[str]
    status_changes: Sequence[ScreenSnapshotStatusChange] = ()
    rank_changes: Sequence[ScreenSnapshotRankChange] = ()
    score_deltas: Sequence[ScreenSnapshotScoreDelta] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "previous_screen_snapshot_id", _required_string("previous_screen_snapshot_id", self.previous_screen_snapshot_id))
        object.__setattr__(self, "current_screen_snapshot_id", _required_string("current_screen_snapshot_id", self.current_screen_snapshot_id))
        object.__setattr__(self, "added", _instrument_tuple("added", self.added))
        object.__setattr__(self, "removed", _instrument_tuple("removed", self.removed))
        object.__setattr__(self, "retained", _instrument_tuple("retained", self.retained))
        for field_name in ("status_changes", "rank_changes", "score_deltas"):
            object.__setattr__(self, field_name, tuple(getattr(self, field_name)))

    def score_delta_for(self, instrument_id: str) -> ScreenSnapshotScoreDelta:
        canonical = _canonical_instrument_id(instrument_id)
        for delta in self.score_deltas:
            if delta.instrument_id == canonical:
                return delta
        raise ScreenSnapshotError(f"score delta not found: {canonical}")

    def to_record(self) -> dict[str, Any]:
        return {
            "previous_screen_snapshot_id": self.previous_screen_snapshot_id,
            "current_screen_snapshot_id": self.current_screen_snapshot_id,
            "added": list(self.added),
            "removed": list(self.removed),
            "retained": list(self.retained),
            "status_changes": [change.to_record() for change in self.status_changes],
            "rank_changes": [change.to_record() for change in self.rank_changes],
            "score_deltas": [delta.to_record() for delta in self.score_deltas],
        }


def build_screen_snapshot(
    pipeline_snapshot: ScreenPipelineSnapshot,
    *,
    created_at: datetime,
    trace_id: str | None = None,
    run_id: str | None = None,
    stage_id: str | None = None,
) -> ScreenSnapshot:
    if type(pipeline_snapshot) is not ScreenPipelineSnapshot:
        raise ScreenSnapshotError("pipeline_snapshot must be a ScreenPipelineSnapshot")
    _require_aware_datetime("created_at", created_at)
    results = [
        _result_from_passed_candidate(candidate)
        for candidate in sorted(pipeline_snapshot.passed_candidates, key=lambda item: item.rank)
    ]
    results.extend(
        _result_from_exclusion(exclusion)
        for exclusion in sorted(
            pipeline_snapshot.exclusions,
            key=lambda item: (item.failed_stage.value, item.instrument_id, item.rule_id),
        )
    )
    return ScreenSnapshot(
        pipeline_snapshot_id=pipeline_snapshot.pipeline_snapshot_id,
        definition_version_id=pipeline_snapshot.definition_version_id,
        as_of=pipeline_snapshot.as_of,
        dataset_versions=pipeline_snapshot.dataset_versions,
        results=tuple(results),
        created_at=created_at,
        trace_id=trace_id or pipeline_snapshot.trace_id,
        run_id=run_id or pipeline_snapshot.run_id,
        stage_id=stage_id or pipeline_snapshot.stage_id,
    )


def publish_screen_snapshot(
    snapshot: ScreenSnapshot,
    artifact_store: ArtifactStore,
    *,
    produced_by_run_id: str | None = None,
    produced_by_stage_id: str | None = None,
    retention_tier: ArtifactRetentionTier = ArtifactRetentionTier.STANDARD,
) -> ArtifactManifest:
    if type(snapshot) is not ScreenSnapshot:
        raise ScreenSnapshotError("snapshot must be a ScreenSnapshot")
    return snapshot.publish(
        artifact_store,
        produced_by_run_id=produced_by_run_id,
        produced_by_stage_id=produced_by_stage_id,
        retention_tier=retention_tier,
    )


def compare_screen_snapshots(previous: ScreenSnapshot, current: ScreenSnapshot) -> ScreenSnapshotComparison:
    if type(previous) is not ScreenSnapshot or type(current) is not ScreenSnapshot:
        raise ScreenSnapshotError("previous and current must be ScreenSnapshot values")

    previous_results = {result.instrument_id: result for result in previous.results}
    current_results = {result.instrument_id: result for result in current.results}
    previous_passed = set(previous.passed_instrument_ids)
    current_passed = set(current.passed_instrument_ids)
    retained = sorted(previous_passed & current_passed)

    status_changes = tuple(
        ScreenSnapshotStatusChange(
            instrument_id=instrument_id,
            previous_status=previous_results[instrument_id].status,
            current_status=current_results[instrument_id].status,
        )
        for instrument_id in sorted(set(previous_results) & set(current_results))
        if previous_results[instrument_id].status is not current_results[instrument_id].status
    )
    rank_changes = tuple(
        ScreenSnapshotRankChange(
            instrument_id=instrument_id,
            previous_rank=previous_results[instrument_id].rank or 0,
            current_rank=current_results[instrument_id].rank or 0,
        )
        for instrument_id in retained
        if previous_results[instrument_id].rank != current_results[instrument_id].rank
    )
    score_deltas = tuple(
        ScreenSnapshotScoreDelta(
            instrument_id=instrument_id,
            previous_score=previous_results[instrument_id].final_score or 0.0,
            current_score=current_results[instrument_id].final_score or 0.0,
        )
        for instrument_id in retained
    )

    return ScreenSnapshotComparison(
        previous_screen_snapshot_id=previous.screen_snapshot_id,
        current_screen_snapshot_id=current.screen_snapshot_id,
        added=tuple(sorted(current_passed - previous_passed)),
        removed=tuple(sorted(previous_passed - current_passed)),
        retained=tuple(retained),
        status_changes=status_changes,
        rank_changes=rank_changes,
        score_deltas=score_deltas,
    )


def _result_from_passed_candidate(candidate: ScreenPipelineCandidate) -> ScreenSnapshotResult:
    if type(candidate) is not ScreenPipelineCandidate:
        raise ScreenSnapshotError("passed candidate must be a ScreenPipelineCandidate")
    return ScreenSnapshotResult(
        instrument_id=candidate.instrument_id,
        status=ScreenSnapshotStatus.PASSED,
        rank=candidate.rank,
        final_score=candidate.final_score,
        scores=candidate.scores,
        factor_contributions=candidate.factor_contributions,
        source_rank=candidate.source_rank,
        industry=candidate.industry,
        reason_codes=candidate.reason_codes,
        summary="instrument passed all screen stages",
        explanation_steps=_passed_steps(candidate),
    )


def _result_from_exclusion(exclusion: ScreenPipelineExclusion) -> ScreenSnapshotResult:
    if type(exclusion) is not ScreenPipelineExclusion:
        raise ScreenSnapshotError("exclusion must be a ScreenPipelineExclusion")
    return ScreenSnapshotResult(
        instrument_id=exclusion.instrument_id,
        status=ScreenSnapshotStatus.FAILED,
        failed_stage=exclusion.failed_stage,
        final_score=exclusion.scores.get("l4_final"),
        scores=exclusion.scores,
        factor_contributions=exclusion.factor_contributions,
        source_rank=exclusion.source_rank,
        reason_codes=(exclusion.rule_id,),
        summary=exclusion.reason,
        explanation_steps=(
            ScreenExplanationStep(
                stage=exclusion.failed_stage,
                rule_id=exclusion.rule_id,
                reason=exclusion.reason,
                authoritative=True,
                scores=exclusion.scores,
                factor_contributions=exclusion.factor_contributions,
                source_ids=(exclusion.rule_id,),
            ),
        ),
    )


def _passed_steps(candidate: ScreenPipelineCandidate) -> tuple[ScreenExplanationStep, ...]:
    return (
        ScreenExplanationStep(
            stage=ScreenPipelineStage.L0_UNIVERSE,
            rule_id="l0_universe_member",
            reason="instrument passed L0 Historical Universe membership and hard filters",
            scores=candidate.scores,
            factor_contributions=candidate.factor_contributions,
        ),
        ScreenExplanationStep(
            stage=ScreenPipelineStage.L1_PROVIDER,
            rule_id="l1_provider_candidate_present",
            reason="instrument appeared in the provider candidate batch",
            scores=candidate.scores,
            factor_contributions=candidate.factor_contributions,
        ),
        ScreenExplanationStep(
            stage=ScreenPipelineStage.L2_FACTOR,
            rule_id="l2_factor_values_available",
            reason="instrument had all required deterministic factor values",
            scores=candidate.scores,
            factor_contributions=candidate.factor_contributions,
        ),
        ScreenExplanationStep(
            stage=ScreenPipelineStage.L3_LLM_OVERLAY,
            rule_id="l3_llm_overlay_recorded",
            reason="LLM overlay score was recorded only after deterministic hard filters",
            scores=candidate.scores,
            factor_contributions=candidate.factor_contributions,
        ),
        ScreenExplanationStep(
            stage=ScreenPipelineStage.L4_FINAL,
            rule_id="l4_final_passed",
            reason="instrument passed deterministic final screen gates",
            scores=candidate.scores,
            factor_contributions=candidate.factor_contributions,
        ),
    )


def _normalize_dataset_versions(dataset_versions: Mapping[str, str]) -> Mapping[str, str]:
    if not isinstance(dataset_versions, Mapping):
        raise ScreenSnapshotError("dataset_versions must map names to concrete Dataset Version ids")
    if not dataset_versions:
        raise ScreenSnapshotError("dataset_versions are required")
    normalized = {
        _required_string("dataset name", name): _validate_dataset_version(version)
        for name, version in dataset_versions.items()
    }
    return MappingProxyType(dict(sorted(normalized.items())))


def _validate_dataset_version(value: object) -> str:
    version = _required_string("dataset_version", value)
    if version.lower() == "latest":
        raise ScreenSnapshotError("ScreenSnapshot requires concrete Dataset Version ids; latest is not allowed")
    try:
        DatasetVersionRef.version(version)
    except (DatasetCatalogError, ValueError) as exc:
        raise ScreenSnapshotError("ScreenSnapshot requires concrete Dataset Version ids") from exc
    return version


def _stable_id(prefix: str, payload: Mapping[str, object]) -> str:
    content = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return f"{prefix}_{hashlib.sha256(content).hexdigest()[:32]}"


def _canonical_instrument_id(value: str) -> str:
    return InstrumentId.parse(_required_string("instrument_id", value)).canonical


def _instrument_tuple(field_name: str, values: Sequence[str]) -> tuple[str, ...]:
    if isinstance(values, str):
        raise ScreenSnapshotError(f"{field_name} values must be a sequence")
    return tuple(_canonical_instrument_id(value) for value in values)


def _required_string(field_name: str, value: object) -> str:
    if type(value) is not str:
        raise ScreenSnapshotError(f"{field_name} is required")
    stripped = value.strip()
    if not stripped:
        raise ScreenSnapshotError(f"{field_name} is required")
    return stripped


def _optional_string(value: object | None) -> str | None:
    if value is None:
        return None
    if type(value) is not str:
        raise ScreenSnapshotError("optional string must be a string")
    stripped = value.strip()
    return stripped or None


def _optional_text(value: object) -> str:
    if value is None:
        return ""
    if type(value) is not str:
        raise ScreenSnapshotError("optional text must be a string")
    return value.strip()


def _finite_float(field_name: str, value: object) -> float:
    if type(value) not in {int, float} or not isfinite(float(value)):
        raise ScreenSnapshotError(f"{field_name} must be finite")
    return float(value)


def _freeze_numeric_mapping(values: Mapping[str, float]) -> Mapping[str, float]:
    if not isinstance(values, Mapping):
        raise ScreenSnapshotError("numeric mapping is required")
    return MappingProxyType(
        {
            _required_string("mapping key", key): _finite_float("mapping value", value)
            for key, value in values.items()
        }
    )


def _freeze_json_mapping(values: Mapping[str, Any]) -> Mapping[str, Any]:
    if not isinstance(values, Mapping):
        raise ScreenSnapshotError("mapping is required")
    return MappingProxyType({str(key): _freeze_value(value) for key, value in values.items()})


def _freeze_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({str(key): _freeze_value(child) for key, child in value.items()})
    if isinstance(value, list | tuple):
        return tuple(_freeze_value(child) for child in value)
    return value


def _thaw_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _thaw_value(child) for key, child in value.items()}
    if isinstance(value, tuple):
        return [_thaw_value(child) for child in value]
    return value


def _string_tuple(field_name: str, values: Sequence[str]) -> tuple[str, ...]:
    if isinstance(values, str):
        raise ScreenSnapshotError(f"{field_name} values must be a sequence")
    return tuple(_required_string(field_name, value) for value in values)


def _require_date(field_name: str, value: object) -> None:
    if type(value) is not date:
        raise ScreenSnapshotError(f"{field_name} must be a date")


def _require_aware_datetime(field_name: str, value: object) -> None:
    if type(value) is not datetime or value.tzinfo is None or value.utcoffset() is None:
        raise ScreenSnapshotError(f"{field_name} must be timezone-aware")


__all__ = [
    "SCREEN_SNAPSHOT_CONTENT_TYPE",
    "SCREEN_SNAPSHOT_CONTRACT_VERSION",
    "SCREEN_SNAPSHOT_SCHEMA_NAME",
    "SCREEN_SNAPSHOT_SCHEMA_VERSION",
    "ScreenExplanationStep",
    "ScreenSnapshot",
    "ScreenSnapshotComparison",
    "ScreenSnapshotError",
    "ScreenSnapshotRankChange",
    "ScreenSnapshotResult",
    "ScreenSnapshotScoreDelta",
    "ScreenSnapshotStatus",
    "ScreenSnapshotStatusChange",
    "build_screen_snapshot",
    "compare_screen_snapshots",
    "publish_screen_snapshot",
]
