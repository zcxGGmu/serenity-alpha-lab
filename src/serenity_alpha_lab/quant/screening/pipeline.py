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

from serenity_alpha_lab.application.candidate_batch import (
    Candidate,
    CandidateBatch,
    CandidateScoreLayer,
)
from serenity_alpha_lab.datasets.catalog import DatasetCatalogError, DatasetVersionRef
from serenity_alpha_lab.domain.artifacts import ArtifactManifest, ArtifactRetentionTier, ArtifactStore
from serenity_alpha_lab.domain.instruments import InstrumentId, Market
from serenity_alpha_lab.quant.factors.post_processing import CrossSectionPostProcessingResult
from serenity_alpha_lab.quant.screening.universe import UniverseSnapshot


SCREEN_PIPELINE_CONTRACT_VERSION = "quant.screen_pipeline@1.0.0"
SCREEN_DEFINITION_SCHEMA_NAME = "quant.screen_definition"
SCREEN_DEFINITION_SCHEMA_VERSION = "1.0.0"
SCREEN_PIPELINE_SNAPSHOT_SCHEMA_NAME = "quant.screen_pipeline_snapshot"
SCREEN_PIPELINE_SNAPSHOT_SCHEMA_VERSION = "1.0.0"
SCREEN_PIPELINE_CONTENT_TYPE = "application/vnd.serenity.quant.screen-pipeline+json"
SCREEN_PIPELINE_ENGINE_VERSION = "screen_pipeline@1.0.0"

_SCREEN_DEFINITION_VERSION_RE = re.compile(r"^sdv_[0-9a-f]{32,64}$")
_FACTOR_VERSION_RE = re.compile(r"^fdv_[0-9a-f]{32,64}$")


class ScreenPipelineError(ValueError):
    """Raised when ScreenDefinition or L0-L4 pipeline inputs are invalid."""


class ScreenDefinitionStatus(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"
    RETIRED = "retired"


class ScreenPipelineStage(StrEnum):
    L0_UNIVERSE = "l0_universe"
    L1_PROVIDER = "l1_provider"
    L2_FACTOR = "l2_factor"
    L3_LLM_OVERLAY = "l3_llm_overlay"
    L4_FINAL = "l4_final"


class ScreenFactorDirection(StrEnum):
    HIGHER_IS_BETTER = "higher_is_better"
    LOWER_IS_BETTER = "lower_is_better"


@dataclass(frozen=True, slots=True)
class ScreenProviderStageSpec:
    provider_id: str
    strategy_id: str
    strategy_version: str
    score_weight: float
    max_candidates: int

    def __post_init__(self) -> None:
        object.__setattr__(self, "provider_id", _required_string("provider_id", self.provider_id))
        object.__setattr__(self, "strategy_id", _required_string("strategy_id", self.strategy_id))
        object.__setattr__(self, "strategy_version", _required_string("strategy_version", self.strategy_version))
        object.__setattr__(self, "score_weight", _finite_float("score_weight", self.score_weight, minimum=0.0))
        if type(self.max_candidates) is not int or self.max_candidates <= 0:
            raise ScreenPipelineError("max_candidates must be a positive integer")

    def to_record(self) -> dict[str, object]:
        return {
            "provider_id": self.provider_id,
            "strategy_id": self.strategy_id,
            "strategy_version": self.strategy_version,
            "score_weight": self.score_weight,
            "max_candidates": self.max_candidates,
        }


@dataclass(frozen=True, slots=True)
class ScreenFactorSpec:
    factor_definition_id: str
    factor_version_id: str
    weight: float
    direction: ScreenFactorDirection | str = ScreenFactorDirection.HIGHER_IS_BETTER

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "factor_definition_id",
            _required_string("factor_definition_id", self.factor_definition_id),
        )
        object.__setattr__(self, "factor_version_id", _validate_factor_version(self.factor_version_id))
        object.__setattr__(self, "weight", _finite_float("weight", self.weight, minimum=0.0))
        if self.weight <= 0:
            raise ScreenPipelineError("factor weight must be positive")
        object.__setattr__(self, "direction", ScreenFactorDirection(self.direction))

    def to_record(self) -> dict[str, object]:
        return {
            "factor_definition_id": self.factor_definition_id,
            "factor_version_id": self.factor_version_id,
            "weight": self.weight,
            "direction": self.direction.value,
        }


@dataclass(frozen=True, slots=True)
class ScreenFactorStageSpec:
    factors: Sequence[ScreenFactorSpec]
    score_weight: float

    def __post_init__(self) -> None:
        factors = tuple(self.factors)
        if not factors:
            raise ScreenPipelineError("factor stage requires at least one factor")
        factor_ids = [factor.factor_definition_id for factor in factors]
        if len(set(factor_ids)) != len(factor_ids):
            raise ScreenPipelineError("duplicate screen factor ids are not allowed")
        for factor in factors:
            if type(factor) is not ScreenFactorSpec:
                raise ScreenPipelineError("factors must contain ScreenFactorSpec values")
        object.__setattr__(self, "factors", factors)
        object.__setattr__(self, "score_weight", _finite_float("score_weight", self.score_weight, minimum=0.0))

    def to_record(self) -> dict[str, object]:
        return {
            "score_weight": self.score_weight,
            "factors": [factor.to_record() for factor in self.factors],
        }


@dataclass(frozen=True, slots=True)
class ScreenLlmOverlayStageSpec:
    enabled: bool = False
    score_weight: float = 0.0

    def __post_init__(self) -> None:
        if type(self.enabled) is not bool:
            raise ScreenPipelineError("llm overlay enabled must be a bool")
        object.__setattr__(self, "score_weight", _finite_float("score_weight", self.score_weight, minimum=0.0))
        if not self.enabled and self.score_weight != 0.0:
            raise ScreenPipelineError("disabled llm overlay must use score_weight=0")

    def to_record(self) -> dict[str, object]:
        return {"enabled": self.enabled, "score_weight": self.score_weight}


@dataclass(frozen=True, slots=True)
class ScreenRiskGateSpec:
    top_n: int
    max_per_industry: int | None = None

    def __post_init__(self) -> None:
        if type(self.top_n) is not int or self.top_n <= 0:
            raise ScreenPipelineError("top_n must be a positive integer")
        if self.max_per_industry is not None and (
            type(self.max_per_industry) is not int or self.max_per_industry <= 0
        ):
            raise ScreenPipelineError("max_per_industry must be a positive integer")

    def to_record(self) -> dict[str, object]:
        record: dict[str, object] = {"top_n": self.top_n}
        if self.max_per_industry is not None:
            record["max_per_industry"] = self.max_per_industry
        return record


@dataclass(frozen=True, slots=True)
class ScreenDefinition:
    definition_id: str
    semantic_version: str
    status: ScreenDefinitionStatus | str
    markets: Sequence[Market | str]
    dataset_versions: Mapping[str, str]
    provider_stage: ScreenProviderStageSpec
    factor_stage: ScreenFactorStageSpec
    llm_overlay_stage: ScreenLlmOverlayStageSpec
    risk_gate: ScreenRiskGateSpec
    created_at: datetime
    created_by_run_id: str
    definition_version_id: str | None = None
    contract_version: str = SCREEN_PIPELINE_CONTRACT_VERSION
    schema_name: str = SCREEN_DEFINITION_SCHEMA_NAME
    schema_version: str = SCREEN_DEFINITION_SCHEMA_VERSION
    engine_version: str = SCREEN_PIPELINE_ENGINE_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "definition_id", _required_string("definition_id", self.definition_id))
        object.__setattr__(self, "semantic_version", _required_string("semantic_version", self.semantic_version))
        object.__setattr__(self, "status", ScreenDefinitionStatus(self.status))
        markets = tuple(Market(market) for market in self.markets)
        if not markets:
            raise ScreenPipelineError("markets are required")
        if len(set(markets)) != len(markets):
            raise ScreenPipelineError("markets cannot contain duplicates")
        object.__setattr__(self, "markets", tuple(sorted(markets, key=lambda market: market.value)))
        object.__setattr__(self, "dataset_versions", _normalize_dataset_versions(self.dataset_versions))
        if type(self.provider_stage) is not ScreenProviderStageSpec:
            raise ScreenPipelineError("provider_stage must be a ScreenProviderStageSpec")
        if type(self.factor_stage) is not ScreenFactorStageSpec:
            raise ScreenPipelineError("factor_stage must be a ScreenFactorStageSpec")
        if type(self.llm_overlay_stage) is not ScreenLlmOverlayStageSpec:
            raise ScreenPipelineError("llm_overlay_stage must be a ScreenLlmOverlayStageSpec")
        if type(self.risk_gate) is not ScreenRiskGateSpec:
            raise ScreenPipelineError("risk_gate must be a ScreenRiskGateSpec")
        _require_aware_datetime("created_at", self.created_at)
        object.__setattr__(self, "created_by_run_id", _required_string("created_by_run_id", self.created_by_run_id))
        object.__setattr__(self, "contract_version", _required_string("contract_version", self.contract_version))
        object.__setattr__(self, "schema_name", _required_string("schema_name", self.schema_name))
        object.__setattr__(self, "schema_version", _required_string("schema_version", self.schema_version))
        object.__setattr__(self, "engine_version", _required_string("engine_version", self.engine_version))

        version_id = self.definition_version_id
        if version_id is None:
            version_id = _stable_id("sdv", self._version_payload())
        else:
            version_id = _validate_screen_definition_version(version_id)
        object.__setattr__(self, "definition_version_id", version_id)

    def to_record(self) -> dict[str, object]:
        record = self._version_payload()
        record.update(
            {
                "definition_version_id": self.definition_version_id,
                "status": self.status.value,
                "created_at": self.created_at.isoformat(),
                "created_by_run_id": self.created_by_run_id,
            }
        )
        return record

    def _version_payload(self) -> dict[str, object]:
        return {
            "contract_version": self.contract_version,
            "schema_name": self.schema_name,
            "schema_version": self.schema_version,
            "engine_version": self.engine_version,
            "definition_id": self.definition_id,
            "semantic_version": self.semantic_version,
            "markets": [market.value for market in self.markets],
            "dataset_versions": dict(self.dataset_versions),
            "provider_stage": self.provider_stage.to_record(),
            "factor_stage": self.factor_stage.to_record(),
            "llm_overlay_stage": self.llm_overlay_stage.to_record(),
            "risk_gate": self.risk_gate.to_record(),
        }


@dataclass(frozen=True, slots=True)
class ScreenPipelineStageTrace:
    stage: ScreenPipelineStage | str
    input_count: int
    output_count: int
    excluded_count: int
    warnings: Sequence[str] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "stage", ScreenPipelineStage(self.stage))
        _require_non_negative_int("input_count", self.input_count)
        _require_non_negative_int("output_count", self.output_count)
        _require_non_negative_int("excluded_count", self.excluded_count)
        object.__setattr__(self, "warnings", _string_tuple("warning", self.warnings))

    def to_record(self) -> dict[str, object]:
        return {
            "stage": self.stage.value,
            "input_count": self.input_count,
            "output_count": self.output_count,
            "excluded_count": self.excluded_count,
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True, slots=True)
class ScreenPipelineCandidate:
    instrument_id: str
    rank: int
    final_score: float
    scores: Mapping[str, float]
    factor_contributions: Mapping[str, float]
    industry: str | None = None
    source_rank: int | None = None
    reason_codes: Sequence[str] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "instrument_id", _canonical_instrument_id(self.instrument_id))
        if type(self.rank) is not int or self.rank <= 0:
            raise ScreenPipelineError("rank must be a positive integer")
        object.__setattr__(self, "final_score", _finite_float("final_score", self.final_score))
        object.__setattr__(self, "scores", _freeze_numeric_mapping(self.scores))
        object.__setattr__(self, "factor_contributions", _freeze_numeric_mapping(self.factor_contributions))
        object.__setattr__(self, "industry", _optional_string(self.industry))
        if self.source_rank is not None and (type(self.source_rank) is not int or self.source_rank <= 0):
            raise ScreenPipelineError("source_rank must be a positive integer")
        object.__setattr__(self, "reason_codes", _string_tuple("reason_code", self.reason_codes))

    def to_record(self) -> dict[str, object]:
        record: dict[str, object] = {
            "instrument_id": self.instrument_id,
            "rank": self.rank,
            "final_score": self.final_score,
            "scores": dict(self.scores),
            "factor_contributions": dict(self.factor_contributions),
            "reason_codes": list(self.reason_codes),
        }
        if self.industry is not None:
            record["industry"] = self.industry
        if self.source_rank is not None:
            record["source_rank"] = self.source_rank
        return record


@dataclass(frozen=True, slots=True)
class ScreenPipelineExclusion:
    instrument_id: str
    failed_stage: ScreenPipelineStage | str
    rule_id: str
    reason: str
    scores: Mapping[str, float] = field(default_factory=dict)
    factor_contributions: Mapping[str, float] = field(default_factory=dict)
    source_rank: int | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "instrument_id", _canonical_instrument_id(self.instrument_id))
        object.__setattr__(self, "failed_stage", ScreenPipelineStage(self.failed_stage))
        object.__setattr__(self, "rule_id", _required_string("rule_id", self.rule_id))
        object.__setattr__(self, "reason", _required_string("reason", self.reason))
        object.__setattr__(self, "scores", _freeze_numeric_mapping(self.scores))
        object.__setattr__(self, "factor_contributions", _freeze_numeric_mapping(self.factor_contributions))
        if self.source_rank is not None and (type(self.source_rank) is not int or self.source_rank <= 0):
            raise ScreenPipelineError("source_rank must be a positive integer")

    def to_record(self) -> dict[str, object]:
        record: dict[str, object] = {
            "instrument_id": self.instrument_id,
            "failed_stage": self.failed_stage.value,
            "rule_id": self.rule_id,
            "reason": self.reason,
            "scores": dict(self.scores),
            "factor_contributions": dict(self.factor_contributions),
        }
        if self.source_rank is not None:
            record["source_rank"] = self.source_rank
        return record


@dataclass(frozen=True, slots=True)
class ScreenPipelineSnapshot:
    definition: ScreenDefinition
    as_of: date
    universe_version_id: str
    candidate_batch_id: str
    passed_candidates: Sequence[ScreenPipelineCandidate]
    exclusions: Sequence[ScreenPipelineExclusion]
    stage_traces: Sequence[ScreenPipelineStageTrace]
    created_at: datetime
    trace_id: str | None = None
    run_id: str | None = None
    stage_id: str | None = None
    pipeline_snapshot_id: str | None = None

    def __post_init__(self) -> None:
        if type(self.definition) is not ScreenDefinition:
            raise ScreenPipelineError("definition must be a ScreenDefinition")
        object.__setattr__(
            self,
            "universe_version_id",
            _validate_dataset_version(self.universe_version_id, field_name="universe_version_id"),
        )
        object.__setattr__(self, "candidate_batch_id", _required_string("candidate_batch_id", self.candidate_batch_id))
        _require_date("as_of", self.as_of)
        _require_aware_datetime("created_at", self.created_at)
        object.__setattr__(self, "trace_id", _optional_string(self.trace_id))
        object.__setattr__(self, "run_id", _optional_string(self.run_id))
        object.__setattr__(self, "stage_id", _optional_string(self.stage_id))

        passed = tuple(self.passed_candidates)
        for candidate in passed:
            if type(candidate) is not ScreenPipelineCandidate:
                raise ScreenPipelineError("passed_candidates must contain ScreenPipelineCandidate values")
        if [candidate.rank for candidate in passed] != list(range(1, len(passed) + 1)):
            raise ScreenPipelineError("passed candidate ranks must be contiguous")
        object.__setattr__(self, "passed_candidates", passed)

        exclusions = tuple(self.exclusions)
        for exclusion in exclusions:
            if type(exclusion) is not ScreenPipelineExclusion:
                raise ScreenPipelineError("exclusions must contain ScreenPipelineExclusion values")
        object.__setattr__(
            self,
            "exclusions",
            tuple(sorted(exclusions, key=lambda item: (item.failed_stage.value, item.instrument_id, item.rule_id))),
        )

        stage_traces = tuple(self.stage_traces)
        for trace in stage_traces:
            if type(trace) is not ScreenPipelineStageTrace:
                raise ScreenPipelineError("stage_traces must contain ScreenPipelineStageTrace values")
        object.__setattr__(self, "stage_traces", stage_traces)

        snapshot_id = self.pipeline_snapshot_id
        if snapshot_id is None:
            snapshot_id = _stable_id("sps", self._identity_record())
        else:
            snapshot_id = _required_string("pipeline_snapshot_id", snapshot_id)
        object.__setattr__(self, "pipeline_snapshot_id", snapshot_id)

    @property
    def definition_version_id(self) -> str:
        return self.definition.definition_version_id

    @property
    def dataset_versions(self) -> Mapping[str, str]:
        return self.definition.dataset_versions

    @property
    def passed_count(self) -> int:
        return len(self.passed_candidates)

    @property
    def exclusion_count(self) -> int:
        return len(self.exclusions)

    def to_json_bytes(self) -> bytes:
        return json.dumps(self.to_record(), ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")

    def to_record(self) -> dict[str, object]:
        record = self._identity_record()
        record["pipeline_snapshot_id"] = self.pipeline_snapshot_id
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
            schema_name=SCREEN_PIPELINE_SNAPSHOT_SCHEMA_NAME,
            schema_version=SCREEN_PIPELINE_SNAPSHOT_SCHEMA_VERSION,
            content_type=SCREEN_PIPELINE_CONTENT_TYPE,
            produced_by_run_id=run_id,
            produced_by_stage_id=stage_id,
            retention_tier=retention_tier,
            created_at=self.created_at,
        )

    def _identity_record(self) -> dict[str, object]:
        return {
            "schema_name": SCREEN_PIPELINE_SNAPSHOT_SCHEMA_NAME,
            "schema_version": SCREEN_PIPELINE_SNAPSHOT_SCHEMA_VERSION,
            "contract_version": SCREEN_PIPELINE_CONTRACT_VERSION,
            "engine_version": self.definition.engine_version,
            "definition": self.definition.to_record(),
            "definition_version_id": self.definition.definition_version_id,
            "as_of": self.as_of.isoformat(),
            "universe_version_id": self.universe_version_id,
            "candidate_batch_id": self.candidate_batch_id,
            "dataset_versions": dict(self.definition.dataset_versions),
            "created_at": self.created_at.isoformat(),
            "trace_id": self.trace_id,
            "run_id": self.run_id,
            "stage_id": self.stage_id,
            "passed_count": self.passed_count,
            "exclusion_count": self.exclusion_count,
            "passed_candidates": [candidate.to_record() for candidate in self.passed_candidates],
            "exclusions": [exclusion.to_record() for exclusion in self.exclusions],
            "stage_traces": [trace.to_record() for trace in self.stage_traces],
        }


@dataclass(slots=True)
class _WorkingCandidate:
    candidate: Candidate
    scores: dict[str, float]
    factor_contributions: dict[str, float]
    factor_raw_score: float = 0.0
    industry: str | None = None

    @property
    def instrument_id(self) -> str:
        return self.candidate.instrument.canonical

    @property
    def source_rank(self) -> int:
        return self.candidate.rank


def run_screen_pipeline(
    definition: ScreenDefinition,
    *,
    as_of: date,
    universe_snapshot: UniverseSnapshot,
    candidate_batch: CandidateBatch,
    factor_results: Mapping[str, CrossSectionPostProcessingResult],
    created_at: datetime,
    trace_id: str | None = None,
    run_id: str | None = None,
    stage_id: str | None = None,
) -> ScreenPipelineSnapshot:
    if type(definition) is not ScreenDefinition:
        raise ScreenPipelineError("definition must be a ScreenDefinition")
    if definition.status is not ScreenDefinitionStatus.PUBLISHED:
        raise ScreenPipelineError("formal runs require a published ScreenDefinition")
    _require_date("as_of", as_of)
    _require_aware_datetime("created_at", created_at)
    if type(universe_snapshot) is not UniverseSnapshot:
        raise ScreenPipelineError("universe_snapshot must be a UniverseSnapshot")
    if type(candidate_batch) is not CandidateBatch:
        raise ScreenPipelineError("candidate_batch must be a CandidateBatch")
    if not isinstance(factor_results, Mapping):
        raise ScreenPipelineError("factor_results must map factor ids to CrossSectionPostProcessingResult values")
    if universe_snapshot.as_of != as_of:
        raise ScreenPipelineError("universe_snapshot.as_of must equal pipeline as_of")
    expected_universe_version = definition.dataset_versions.get("universe")
    if expected_universe_version is not None and universe_snapshot.universe_version_id != expected_universe_version:
        raise ScreenPipelineError("universe snapshot version does not match ScreenDefinition")
    if Market(candidate_batch.market) not in definition.markets:
        raise ScreenPipelineError("candidate batch market is outside ScreenDefinition markets")
    _validate_provider_batch(definition, candidate_batch)

    provider_candidates = tuple(candidate_batch.candidates[: definition.provider_stage.max_candidates])
    working_by_id = _working_candidates(provider_candidates)
    universe_member_ids = {member.instrument_id for member in universe_snapshot.members}
    universe_exclusions = {exclusion.instrument_id: exclusion for exclusion in universe_snapshot.exclusions}
    exclusions: list[ScreenPipelineExclusion] = []
    stage_traces: list[ScreenPipelineStageTrace] = []

    l0_survivors: list[_WorkingCandidate] = []
    for candidate in working_by_id.values():
        if candidate.instrument_id in universe_member_ids:
            l0_survivors.append(candidate)
            continue
        universe_reason = universe_exclusions.get(candidate.instrument_id)
        exclusions.append(
            ScreenPipelineExclusion(
                instrument_id=candidate.instrument_id,
                failed_stage=ScreenPipelineStage.L0_UNIVERSE,
                rule_id="l0_universe_member",
                reason=(
                    "instrument failed L0 Historical Universe"
                    if universe_reason is None
                    else universe_reason.reason
                ),
                scores=candidate.scores,
                source_rank=candidate.source_rank,
            )
        )
    stage_traces.append(
        ScreenPipelineStageTrace(
            stage=ScreenPipelineStage.L0_UNIVERSE,
            input_count=len(provider_candidates),
            output_count=len(l0_survivors),
            excluded_count=len(provider_candidates) - len(l0_survivors),
        )
    )

    l1_survivors = sorted(l0_survivors, key=lambda item: item.candidate.rank)
    provider_ids = {candidate.instrument_id for candidate in l1_survivors}
    missing_from_provider = sorted(universe_member_ids - provider_ids)
    for instrument_id in missing_from_provider:
        exclusions.append(
            ScreenPipelineExclusion(
                instrument_id=instrument_id,
                failed_stage=ScreenPipelineStage.L1_PROVIDER,
                rule_id="l1_provider_candidate_missing",
                reason="instrument was in L0 universe but absent from the provider candidate batch",
            )
        )
    stage_traces.append(
        ScreenPipelineStageTrace(
            stage=ScreenPipelineStage.L1_PROVIDER,
            input_count=len(universe_member_ids),
            output_count=len(l1_survivors),
            excluded_count=len(missing_from_provider),
        )
    )

    factor_maps = _factor_value_maps(definition, factor_results, as_of)
    l2_survivors: list[_WorkingCandidate] = []
    for candidate in l1_survivors:
        missing_factor_ids = [
            factor.factor_definition_id
            for factor in definition.factor_stage.factors
            if candidate.instrument_id not in factor_maps[factor.factor_definition_id]
        ]
        if missing_factor_ids:
            exclusions.append(
                ScreenPipelineExclusion(
                    instrument_id=candidate.instrument_id,
                    failed_stage=ScreenPipelineStage.L2_FACTOR,
                    rule_id="l2_factor_value_missing",
                    reason=f"missing factor values: {', '.join(missing_factor_ids)}",
                    scores=candidate.scores,
                    source_rank=candidate.source_rank,
                )
            )
            continue
        _apply_factor_scores(candidate, definition, factor_maps)
        l2_survivors.append(candidate)
    _normalize_l2_scores(l2_survivors)
    stage_traces.append(
        ScreenPipelineStageTrace(
            stage=ScreenPipelineStage.L2_FACTOR,
            input_count=len(l1_survivors),
            output_count=len(l2_survivors),
            excluded_count=len(l1_survivors) - len(l2_survivors),
        )
    )

    for candidate in l2_survivors:
        if definition.llm_overlay_stage.enabled:
            candidate.scores[ScreenPipelineStage.L3_LLM_OVERLAY.value] = (
                candidate.scores.get(CandidateScoreLayer.L3_LLM_OVERLAY.value, 0.0)
                if candidate_batch.llm_overlay_enabled
                else 0.0
            )
    stage_traces.append(
        ScreenPipelineStageTrace(
            stage=ScreenPipelineStage.L3_LLM_OVERLAY,
            input_count=len(l2_survivors),
            output_count=len(l2_survivors),
            excluded_count=0,
        )
    )

    passed, l4_exclusions = _apply_l4_gate(definition, l2_survivors)
    exclusions.extend(l4_exclusions)
    stage_traces.append(
        ScreenPipelineStageTrace(
            stage=ScreenPipelineStage.L4_FINAL,
            input_count=len(l2_survivors),
            output_count=len(passed),
            excluded_count=len(l4_exclusions),
        )
    )

    return ScreenPipelineSnapshot(
        definition=definition,
        as_of=as_of,
        universe_version_id=universe_snapshot.universe_version_id,
        candidate_batch_id=candidate_batch.batch_id,
        passed_candidates=tuple(passed),
        exclusions=tuple(exclusions),
        stage_traces=tuple(stage_traces),
        created_at=created_at,
        trace_id=trace_id,
        run_id=run_id,
        stage_id=stage_id,
    )


def publish_screen_pipeline_snapshot(
    snapshot: ScreenPipelineSnapshot,
    artifact_store: ArtifactStore,
    *,
    produced_by_run_id: str | None = None,
    produced_by_stage_id: str | None = None,
    retention_tier: ArtifactRetentionTier = ArtifactRetentionTier.STANDARD,
) -> ArtifactManifest:
    if type(snapshot) is not ScreenPipelineSnapshot:
        raise ScreenPipelineError("snapshot must be a ScreenPipelineSnapshot")
    return snapshot.publish(
        artifact_store,
        produced_by_run_id=produced_by_run_id,
        produced_by_stage_id=produced_by_stage_id,
        retention_tier=retention_tier,
    )


def _validate_provider_batch(definition: ScreenDefinition, candidate_batch: CandidateBatch) -> None:
    provider_stage = definition.provider_stage
    if candidate_batch.provider_id != provider_stage.provider_id:
        raise ScreenPipelineError("candidate batch provider_id does not match ScreenDefinition")
    if candidate_batch.strategy_id != provider_stage.strategy_id:
        raise ScreenPipelineError("candidate batch strategy_id does not match ScreenDefinition")
    if candidate_batch.strategy_version != provider_stage.strategy_version:
        raise ScreenPipelineError("candidate batch strategy_version does not match ScreenDefinition")
    for dataset_name, batch_version in candidate_batch.dataset_versions.items():
        expected_version = definition.dataset_versions.get(dataset_name)
        if expected_version is not None and batch_version != expected_version:
            raise ScreenPipelineError(f"candidate batch dataset version mismatch: {dataset_name}")


def _working_candidates(candidates: Sequence[Candidate]) -> Mapping[str, _WorkingCandidate]:
    values: dict[str, _WorkingCandidate] = {}
    for candidate in candidates:
        if type(candidate) is not Candidate:
            raise ScreenPipelineError("candidate batch must contain Candidate values")
        instrument_id = candidate.instrument.canonical
        if instrument_id in values:
            raise ScreenPipelineError(f"duplicate candidate instrument_id: {instrument_id}")
        values[instrument_id] = _WorkingCandidate(
            candidate=candidate,
            scores=_candidate_scores(candidate),
            factor_contributions={},
            industry=_candidate_industry(candidate),
        )
    return MappingProxyType(values)


def _candidate_scores(candidate: Candidate) -> dict[str, float]:
    return {layer.value: score.score for layer, score in candidate.scores.items()}


def _candidate_industry(candidate: Candidate) -> str | None:
    value = candidate.raw_payload.get("industry") if isinstance(candidate.raw_payload, Mapping) else None
    return _optional_string(value)


def _factor_value_maps(
    definition: ScreenDefinition,
    factor_results: Mapping[str, CrossSectionPostProcessingResult],
    as_of: date,
) -> dict[str, dict[str, tuple[float, str | None]]]:
    values: dict[str, dict[str, tuple[float, str | None]]] = {}
    for factor in definition.factor_stage.factors:
        result = factor_results.get(factor.factor_definition_id)
        if type(result) is not CrossSectionPostProcessingResult:
            raise ScreenPipelineError(f"factor result missing: {factor.factor_definition_id}")
        expected_factor_values_version = definition.dataset_versions.get("factor_values")
        if (
            expected_factor_values_version is not None
            and result.dataset_versions.get("factor_values") != expected_factor_values_version
        ):
            raise ScreenPipelineError(f"factor result version mismatch: {factor.factor_definition_id}")
        factor_values: dict[str, tuple[float, str | None]] = {}
        for value in result.processed_values:
            if value.trade_date != as_of:
                continue
            industry = _optional_string(value.exposures.get("industry")) if isinstance(value.exposures, Mapping) else None
            factor_values[value.instrument_id] = (value.processed_value, industry)
        values[factor.factor_definition_id] = factor_values
    return values


def _apply_factor_scores(
    candidate: _WorkingCandidate,
    definition: ScreenDefinition,
    factor_maps: Mapping[str, Mapping[str, tuple[float, str | None]]],
) -> None:
    total_weight = sum(factor.weight for factor in definition.factor_stage.factors)
    raw = 0.0
    for factor in definition.factor_stage.factors:
        value, industry = factor_maps[factor.factor_definition_id][candidate.instrument_id]
        signed_value = -value if factor.direction is ScreenFactorDirection.LOWER_IS_BETTER else value
        contribution = signed_value * factor.weight / total_weight
        candidate.factor_contributions[factor.factor_definition_id] = contribution
        raw += contribution
        if candidate.industry is None and industry is not None:
            candidate.industry = industry
    candidate.factor_raw_score = raw


def _normalize_l2_scores(candidates: Sequence[_WorkingCandidate]) -> None:
    if not candidates:
        return
    raw_values = [candidate.factor_raw_score for candidate in candidates]
    low = min(raw_values)
    high = max(raw_values)
    if high == low:
        for candidate in candidates:
            candidate.scores[ScreenPipelineStage.L2_FACTOR.value] = 50.0
        return
    for candidate in candidates:
        candidate.scores[ScreenPipelineStage.L2_FACTOR.value] = (
            (candidate.factor_raw_score - low) / (high - low) * 100.0
        )


def _apply_l4_gate(
    definition: ScreenDefinition,
    candidates: Sequence[_WorkingCandidate],
) -> tuple[list[ScreenPipelineCandidate], list[ScreenPipelineExclusion]]:
    scored = sorted(
        ((_final_score(definition, candidate), candidate) for candidate in candidates),
        key=lambda item: (-item[0], item[1].instrument_id),
    )
    passed: list[ScreenPipelineCandidate] = []
    exclusions: list[ScreenPipelineExclusion] = []
    industry_counts: dict[str, int] = {}
    for final_score, candidate in scored:
        candidate.scores[ScreenPipelineStage.L4_FINAL.value] = final_score
        industry = candidate.industry or "__unknown__"
        if (
            definition.risk_gate.max_per_industry is not None
            and industry_counts.get(industry, 0) >= definition.risk_gate.max_per_industry
        ):
            exclusions.append(
                ScreenPipelineExclusion(
                    instrument_id=candidate.instrument_id,
                    failed_stage=ScreenPipelineStage.L4_FINAL,
                    rule_id="max_per_industry",
                    reason=f"industry {industry} exceeds max_per_industry",
                    scores=candidate.scores,
                    factor_contributions=candidate.factor_contributions,
                    source_rank=candidate.source_rank,
                )
            )
            continue
        if len(passed) >= definition.risk_gate.top_n:
            exclusions.append(
                ScreenPipelineExclusion(
                    instrument_id=candidate.instrument_id,
                    failed_stage=ScreenPipelineStage.L4_FINAL,
                    rule_id="top_n",
                    reason=f"candidate rank exceeds top_n={definition.risk_gate.top_n}",
                    scores=candidate.scores,
                    factor_contributions=candidate.factor_contributions,
                    source_rank=candidate.source_rank,
                )
            )
            continue
        industry_counts[industry] = industry_counts.get(industry, 0) + 1
        passed.append(
            ScreenPipelineCandidate(
                instrument_id=candidate.instrument_id,
                rank=len(passed) + 1,
                final_score=final_score,
                scores=candidate.scores,
                factor_contributions=candidate.factor_contributions,
                industry=industry,
                source_rank=candidate.source_rank,
                reason_codes=tuple(reason.code for reason in candidate.candidate.reasons),
            )
        )
    return passed, exclusions


def _final_score(definition: ScreenDefinition, candidate: _WorkingCandidate) -> float:
    provider_weight = definition.provider_stage.score_weight
    factor_weight = definition.factor_stage.score_weight
    llm_weight = definition.llm_overlay_stage.score_weight if definition.llm_overlay_stage.enabled else 0.0
    total_weight = provider_weight + factor_weight + llm_weight
    if total_weight <= 0:
        raise ScreenPipelineError("at least one screen score weight must be positive")
    return (
        provider_weight * candidate.scores[CandidateScoreLayer.L1_PROVIDER.value]
        + factor_weight * candidate.scores[ScreenPipelineStage.L2_FACTOR.value]
        + llm_weight * candidate.scores.get(ScreenPipelineStage.L3_LLM_OVERLAY.value, 0.0)
    ) / total_weight


def _normalize_dataset_versions(dataset_versions: Mapping[str, str]) -> Mapping[str, str]:
    if not isinstance(dataset_versions, Mapping):
        raise ScreenPipelineError("dataset_versions must map names to concrete Dataset Version ids")
    if not dataset_versions:
        raise ScreenPipelineError("dataset_versions are required")
    normalized = {
        _required_string("dataset name", name): _validate_dataset_version(version, field_name="dataset_version")
        for name, version in dataset_versions.items()
    }
    return MappingProxyType(dict(sorted(normalized.items())))


def _validate_dataset_version(value: object, *, field_name: str) -> str:
    version = _required_string(field_name, value)
    if version.lower() == "latest":
        raise ScreenPipelineError("ScreenDefinition requires concrete Dataset Version ids; latest is not allowed")
    try:
        DatasetVersionRef.version(version)
    except (DatasetCatalogError, ValueError) as exc:
        raise ScreenPipelineError(f"{field_name} must be a concrete Dataset Version id") from exc
    return version


def _validate_factor_version(value: object) -> str:
    version = _required_string("factor_version_id", value)
    if not _FACTOR_VERSION_RE.fullmatch(version):
        raise ScreenPipelineError("factor_version_id must be a concrete fdv_* version id")
    return version


def _validate_screen_definition_version(value: object) -> str:
    version = _required_string("definition_version_id", value)
    if not _SCREEN_DEFINITION_VERSION_RE.fullmatch(version):
        raise ScreenPipelineError("definition_version_id must be an sdv_* version id")
    return version


def _stable_id(prefix: str, payload: Mapping[str, object]) -> str:
    content = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return f"{prefix}_{hashlib.sha256(content).hexdigest()[:32]}"


def _canonical_instrument_id(value: str) -> str:
    return InstrumentId.parse(_required_string("instrument_id", value)).canonical


def _required_string(field_name: str, value: object) -> str:
    if type(value) is not str:
        raise ScreenPipelineError(f"{field_name} is required")
    stripped = value.strip()
    if not stripped:
        raise ScreenPipelineError(f"{field_name} is required")
    return stripped


def _optional_string(value: object | None) -> str | None:
    if value is None:
        return None
    if type(value) is not str:
        raise ScreenPipelineError("optional string must be a string")
    stripped = value.strip()
    return stripped or None


def _finite_float(
    field_name: str,
    value: object,
    *,
    minimum: float | None = None,
    maximum: float | None = None,
) -> float:
    if type(value) not in {int, float} or not isfinite(float(value)):
        raise ScreenPipelineError(f"{field_name} must be finite")
    normalized = float(value)
    if minimum is not None and normalized < minimum:
        raise ScreenPipelineError(f"{field_name} must be >= {minimum}")
    if maximum is not None and normalized > maximum:
        raise ScreenPipelineError(f"{field_name} must be <= {maximum}")
    return normalized


def _freeze_numeric_mapping(values: Mapping[str, float]) -> Mapping[str, float]:
    if not isinstance(values, Mapping):
        raise ScreenPipelineError("numeric mapping is required")
    return MappingProxyType(
        {
            _required_string("mapping key", key): _finite_float("mapping value", value)
            for key, value in values.items()
        }
    )


def _string_tuple(field_name: str, values: Sequence[str]) -> tuple[str, ...]:
    if isinstance(values, str):
        raise ScreenPipelineError(f"{field_name} values must be a sequence")
    return tuple(_required_string(field_name, value) for value in values)


def _require_non_negative_int(field_name: str, value: int) -> None:
    if type(value) is not int or value < 0:
        raise ScreenPipelineError(f"{field_name} cannot be negative")


def _require_date(field_name: str, value: object) -> None:
    if type(value) is not date:
        raise ScreenPipelineError(f"{field_name} must be a date")


def _require_aware_datetime(field_name: str, value: object) -> None:
    if type(value) is not datetime or value.tzinfo is None or value.utcoffset() is None:
        raise ScreenPipelineError(f"{field_name} must be timezone-aware")


__all__ = [
    "SCREEN_DEFINITION_SCHEMA_NAME",
    "SCREEN_DEFINITION_SCHEMA_VERSION",
    "SCREEN_PIPELINE_CONTENT_TYPE",
    "SCREEN_PIPELINE_CONTRACT_VERSION",
    "SCREEN_PIPELINE_ENGINE_VERSION",
    "SCREEN_PIPELINE_SNAPSHOT_SCHEMA_NAME",
    "SCREEN_PIPELINE_SNAPSHOT_SCHEMA_VERSION",
    "ScreenDefinition",
    "ScreenDefinitionStatus",
    "ScreenFactorDirection",
    "ScreenFactorSpec",
    "ScreenFactorStageSpec",
    "ScreenLlmOverlayStageSpec",
    "ScreenPipelineCandidate",
    "ScreenPipelineError",
    "ScreenPipelineExclusion",
    "ScreenPipelineSnapshot",
    "ScreenPipelineStage",
    "ScreenPipelineStageTrace",
    "ScreenProviderStageSpec",
    "ScreenRiskGateSpec",
    "publish_screen_pipeline_snapshot",
    "run_screen_pipeline",
]
