from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from serenity_alpha_lab.application.evidence_bundle_builder import EvidenceBundle, EvidenceBundleRole
from serenity_alpha_lab.evidence.prompt_registry import AgentPromptRole, PromptRunBinding
from serenity_alpha_lab.evidence.schema import (
    ClaimComputationPolicy,
    ClaimKind,
    EvidenceEvaluationScope,
    EvidenceKind,
    EvidenceRecord,
    ReportCitation,
    ResearchClaim,
)


TECHNICAL_AGENT_CONTRACT_VERSION = "research.agent.technical@1.0.0"
TECHNICAL_AGENT_PROMPT_PAYLOAD_SCHEMA_NAME = "research.agent.technical_prompt_payload"
TECHNICAL_AGENT_OUTPUT_SCHEMA_NAME = "research.agent.technical_output_adapter"
TECHNICAL_AGENT_SCHEMA_VERSION = "1.0.0"

_ALLOWED_TECHNICAL_EVIDENCE_KINDS = frozenset(
    {
        EvidenceKind.SCREEN_SNAPSHOT,
        EvidenceKind.SCREEN_PIPELINE_SNAPSHOT,
        EvidenceKind.FACTOR_EVALUATION,
        EvidenceKind.FACTOR_CACHE_MANIFEST,
    }
)
_ALLOWED_TECHNICAL_SCOPE_BY_KIND = {
    EvidenceKind.SCREEN_SNAPSHOT: frozenset({EvidenceEvaluationScope.SCREENING}),
    EvidenceKind.SCREEN_PIPELINE_SNAPSHOT: frozenset({EvidenceEvaluationScope.SCREENING}),
    EvidenceKind.FACTOR_EVALUATION: frozenset({EvidenceEvaluationScope.FACTOR_EVALUATION}),
    EvidenceKind.FACTOR_CACHE_MANIFEST: frozenset({EvidenceEvaluationScope.DATASET_LINEAGE}),
}
_FORBIDDEN_ACTIONS = (
    "call_real_provider",
    "call_real_llm",
    "run_dsa_agent_tools",
    "fetch_realtime_quote",
    "fetch_daily_history",
    "recompute_technical_indicators",
    "recompute_factor_metrics",
    "recompute_backtest_metrics",
    "start_worker_loop",
    "initialize_qlib_runtime",
    "render_report",
    "place_or_simulate_trade",
)


class TechnicalAgentError(ValueError):
    """Raised when Technical Agent evidence or output violates the P5 contract."""


class TechnicalSignal(StrEnum):
    STRONG_BUY = "strong_buy"
    BUY = "buy"
    HOLD = "hold"
    SELL = "sell"
    STRONG_SELL = "strong_sell"


class TechnicalTrendAlignment(StrEnum):
    BULLISH = "bullish"
    NEUTRAL = "neutral"
    BEARISH = "bearish"


class TechnicalVolumeStatus(StrEnum):
    HEAVY = "heavy"
    NORMAL = "normal"
    LIGHT = "light"


@dataclass(frozen=True, slots=True)
class TechnicalAgentPromptRequest:
    run_id: str
    stage_id: str
    bundle: EvidenceBundle
    prompt_binding: PromptRunBinding

    def __post_init__(self) -> None:
        object.__setattr__(self, "run_id", _required_string("run_id", self.run_id))
        object.__setattr__(self, "stage_id", _required_string("stage_id", self.stage_id))
        if type(self.bundle) is not EvidenceBundle:
            raise TechnicalAgentError("bundle must be an EvidenceBundle")
        if type(self.prompt_binding) is not PromptRunBinding:
            raise TechnicalAgentError("prompt_binding must be a PromptRunBinding")
        if self.bundle.request.role is not EvidenceBundleRole.TECHNICAL:
            raise TechnicalAgentError("Technical Agent requires a technical EvidenceBundle")
        if self.prompt_binding.request.role is not AgentPromptRole.TECHNICAL:
            raise TechnicalAgentError("Technical Agent requires a technical prompt binding")
        if self.prompt_binding.request.run_id != self.run_id:
            raise TechnicalAgentError("prompt binding run_id must match the Technical Agent request")
        if self.prompt_binding.request.stage_id != self.stage_id:
            raise TechnicalAgentError("prompt binding stage_id must match the Technical Agent request")


@dataclass(frozen=True, slots=True)
class TechnicalAgentPromptPayload:
    bundle: EvidenceBundle
    prompt_binding: PromptRunBinding
    allowed_evidence_ids: tuple[str, ...]
    allowed_evidence_hashes: tuple[str, ...]
    forbidden_actions: tuple[str, ...] = _FORBIDDEN_ACTIONS
    contract_version: str = TECHNICAL_AGENT_CONTRACT_VERSION
    schema_name: str = TECHNICAL_AGENT_PROMPT_PAYLOAD_SCHEMA_NAME
    schema_version: str = TECHNICAL_AGENT_SCHEMA_VERSION

    @property
    def payload_hash(self) -> str:
        return _hash_record(self.to_record(include_hash=False))

    def to_record(self, *, include_hash: bool = True) -> dict[str, Any]:
        record = {
            "contract_version": self.contract_version,
            "schema_name": self.schema_name,
            "schema_version": self.schema_version,
            "run_id": self.prompt_binding.request.run_id,
            "stage_id": self.prompt_binding.request.stage_id,
            "bundle": self.bundle.to_prompt_payload(),
            "prompt_binding": self.prompt_binding.to_record(),
            "allowed_evidence_ids": list(self.allowed_evidence_ids),
            "allowed_evidence_hashes": list(self.allowed_evidence_hashes),
            "forbidden_actions": list(self.forbidden_actions),
        }
        if include_hash:
            record["payload_hash"] = self.payload_hash
        return record


@dataclass(frozen=True, slots=True)
class TechnicalAgentStructuredOutput:
    signal: TechnicalSignal
    confidence: float
    reasoning: str
    claims: Sequence[ResearchClaim]
    citations: Sequence[ReportCitation]
    key_levels: Mapping[str, float]
    trend_score: int
    ma_alignment: TechnicalTrendAlignment
    volume_status: TechnicalVolumeStatus
    pattern: str
    warnings: Sequence[str] = ()
    limitations: Sequence[str] = ()
    contract_version: str = TECHNICAL_AGENT_CONTRACT_VERSION
    schema_name: str = TECHNICAL_AGENT_OUTPUT_SCHEMA_NAME
    schema_version: str = TECHNICAL_AGENT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "signal", TechnicalSignal(self.signal))
        object.__setattr__(self, "confidence", _ratio("confidence", self.confidence))
        object.__setattr__(self, "reasoning", _required_string("reasoning", self.reasoning))
        claims = tuple(self.claims)
        citations = tuple(self.citations)
        for claim in claims:
            if type(claim) is not ResearchClaim:
                raise TechnicalAgentError("claims must contain ResearchClaim objects")
        for citation in citations:
            if type(citation) is not ReportCitation:
                raise TechnicalAgentError("citations must contain ReportCitation objects")
        object.__setattr__(self, "claims", claims)
        object.__setattr__(self, "citations", citations)
        object.__setattr__(self, "key_levels", _float_mapping("key_levels", self.key_levels))
        object.__setattr__(self, "trend_score", _int_range("trend_score", self.trend_score, minimum=0, maximum=100))
        object.__setattr__(self, "ma_alignment", TechnicalTrendAlignment(self.ma_alignment))
        object.__setattr__(self, "volume_status", TechnicalVolumeStatus(self.volume_status))
        object.__setattr__(self, "pattern", _required_string("pattern", self.pattern))
        object.__setattr__(self, "warnings", _string_tuple("warnings", self.warnings))
        object.__setattr__(self, "limitations", _string_tuple("limitations", self.limitations))
        object.__setattr__(self, "contract_version", _required_string("contract_version", self.contract_version))
        object.__setattr__(self, "schema_name", _required_string("schema_name", self.schema_name))
        object.__setattr__(self, "schema_version", _required_string("schema_version", self.schema_version))

    def to_record(self) -> dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "schema_name": self.schema_name,
            "schema_version": self.schema_version,
            "signal": self.signal.value,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "claims": [claim.to_record() for claim in self.claims],
            "citations": [citation.to_record() for citation in self.citations],
            "key_levels": dict(self.key_levels),
            "trend_score": self.trend_score,
            "ma_alignment": self.ma_alignment.value,
            "volume_status": self.volume_status.value,
            "pattern": self.pattern,
            "warnings": list(self.warnings),
            "limitations": list(self.limitations),
        }


@dataclass(frozen=True, slots=True)
class TechnicalAgentResult:
    prompt_payload: TechnicalAgentPromptPayload
    output: TechnicalAgentStructuredOutput
    contract_version: str = TECHNICAL_AGENT_CONTRACT_VERSION
    schema_name: str = "research.agent.technical_result"
    schema_version: str = TECHNICAL_AGENT_SCHEMA_VERSION

    def to_record(self) -> dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "schema_name": self.schema_name,
            "schema_version": self.schema_version,
            "prompt_payload_hash": self.prompt_payload.payload_hash,
            "bundle_id": self.prompt_payload.bundle.bundle_id,
            "prompt_binding_hash": self.prompt_payload.prompt_binding.binding_hash,
            "output": self.output.to_record(),
        }

    def to_dsa_compatible_opinion(self) -> dict[str, Any]:
        raw_data = self.output.to_record()
        raw_data.update(
            {
                "bundle_id": self.prompt_payload.bundle.bundle_id,
                "prompt_payload_hash": self.prompt_payload.payload_hash,
                "prompt_binding_hash": self.prompt_payload.prompt_binding.binding_hash,
                "allowed_evidence_ids": list(self.prompt_payload.allowed_evidence_ids),
            }
        )
        return {
            "agent_name": "technical",
            "signal": self.output.signal.value,
            "confidence": self.output.confidence,
            "reasoning": self.output.reasoning,
            "key_levels": dict(self.output.key_levels),
            "raw_data": raw_data,
        }

    def to_dsa_dashboard_fields(self) -> dict[str, Any]:
        return {
            "technical_analysis": self.output.reasoning,
            "trend_analysis": f"{self.output.ma_alignment.value} trend score {self.output.trend_score}/100",
            "ma_analysis": self.output.ma_alignment.value,
            "volume_analysis": self.output.volume_status.value,
            "pattern_analysis": self.output.pattern,
            "key_levels": dict(self.output.key_levels),
            "trend_status": {
                "ma_alignment": self.output.ma_alignment.value,
                "is_bullish": self.output.ma_alignment is TechnicalTrendAlignment.BULLISH,
                "trend_score": self.output.trend_score,
            },
            "volume_status": self.output.volume_status.value,
            "data_perspective": {
                "trend_status": {
                    "ma_alignment": self.output.ma_alignment.value,
                    "is_bullish": self.output.ma_alignment is TechnicalTrendAlignment.BULLISH,
                    "trend_score": self.output.trend_score,
                },
                "price_position": {
                    "current_price": self.output.key_levels.get("current_price"),
                    "ma5": self.output.key_levels.get("ma5"),
                    "ma10": self.output.key_levels.get("ma10"),
                    "ma20": self.output.key_levels.get("ma20"),
                    "bias_ma5": self.output.key_levels.get("bias_ma5"),
                    "bias_status": None,
                    "support_level": self.output.key_levels.get("support"),
                    "resistance_level": self.output.key_levels.get("resistance"),
                },
                "volume_analysis": {
                    "volume_ratio": None,
                    "volume_status": self.output.volume_status.value,
                    "turnover_rate": None,
                    "volume_meaning": "Derived from cited technical evidence; no realtime volume recomputation was performed.",
                },
            },
            "citations": [citation.to_record() for citation in self.output.citations],
        }


class EvidenceScopedTechnicalAgent:
    """Offline Technical Agent boundary over P5 EvidenceBundle and cited output."""

    def prepare_prompt_payload(self, request: TechnicalAgentPromptRequest) -> TechnicalAgentPromptPayload:
        if type(request) is not TechnicalAgentPromptRequest:
            raise TechnicalAgentError("request must be a TechnicalAgentPromptRequest")
        for item in request.bundle.items:
            _validate_allowed_evidence(item.evidence)
        return TechnicalAgentPromptPayload(
            bundle=request.bundle,
            prompt_binding=request.prompt_binding,
            allowed_evidence_ids=tuple(item.evidence.evidence_id for item in request.bundle.items),
            allowed_evidence_hashes=tuple(item.evidence.content_hash for item in request.bundle.items),
        )

    def finalize_output(
        self,
        prompt_payload: TechnicalAgentPromptPayload,
        output: TechnicalAgentStructuredOutput,
    ) -> TechnicalAgentResult:
        if type(prompt_payload) is not TechnicalAgentPromptPayload:
            raise TechnicalAgentError("prompt_payload must be a TechnicalAgentPromptPayload")
        if type(output) is not TechnicalAgentStructuredOutput:
            raise TechnicalAgentError("output must be a TechnicalAgentStructuredOutput")
        evidence_by_id = {item.evidence.evidence_id: item.evidence for item in prompt_payload.bundle.items}
        citations_by_id = {citation.citation_id: citation for citation in output.citations}
        if len(citations_by_id) != len(tuple(output.citations)):
            raise TechnicalAgentError("duplicate citation_id in Technical Agent output")

        for citation in output.citations:
            evidence = evidence_by_id.get(citation.evidence_id)
            if evidence is None:
                raise TechnicalAgentError(f"citation evidence_id is not included in the EvidenceBundle: {citation.evidence_id}")
            if evidence.artifact_hash and citation.artifact_hash != evidence.artifact_hash:
                raise TechnicalAgentError(f"citation artifact_hash does not match evidence: {citation.citation_id}")
            if evidence.dataset_versions and dict(citation.dataset_versions) != dict(evidence.dataset_versions):
                raise TechnicalAgentError(f"citation dataset_versions do not match evidence: {citation.citation_id}")
            if evidence.run_id and citation.run_id != evidence.run_id:
                raise TechnicalAgentError(f"citation run_id does not match evidence: {citation.citation_id}")
            if evidence.stage_id and citation.stage_id != evidence.stage_id:
                raise TechnicalAgentError(f"citation stage_id does not match evidence: {citation.citation_id}")
            if (
                citation.formula_version is not None
                and evidence.formula_versions
                and citation.formula_version not in set(evidence.formula_versions.values())
            ):
                raise TechnicalAgentError(f"citation formula_version does not match evidence: {citation.citation_id}")

        for claim in output.claims:
            for citation_id in claim.citation_ids:
                if citation_id not in citations_by_id:
                    raise TechnicalAgentError(f"claim references unknown citation_id: {citation_id}")
            if claim.kind is ClaimKind.NUMERIC_METRIC:
                if claim.computation_policy is not ClaimComputationPolicy.DETERMINISTIC_EVIDENCE:
                    raise TechnicalAgentError("Technical numeric claims must use deterministic_evidence")
                for citation_id in claim.citation_ids:
                    citation = citations_by_id[citation_id]
                    if citation.unit is None or citation.formula_version is None:
                        raise TechnicalAgentError("Technical numeric claim citations require unit and formula_version")
                    _validate_numeric_claim_citation(claim, citation)

        return TechnicalAgentResult(prompt_payload=prompt_payload, output=output)


def _validate_allowed_evidence(evidence: EvidenceRecord) -> None:
    if type(evidence) is not EvidenceRecord:
        raise TechnicalAgentError("EvidenceBundle items must contain EvidenceRecord objects")
    if evidence.kind not in _ALLOWED_TECHNICAL_EVIDENCE_KINDS:
        raise TechnicalAgentError(
            f"Technical Agent evidence allowlist rejected evidence kind: {evidence.kind.value}"
        )
    allowed_scopes = _ALLOWED_TECHNICAL_SCOPE_BY_KIND[evidence.kind]
    if evidence.evaluation_scope not in allowed_scopes:
        raise TechnicalAgentError(
            f"Technical Agent evidence scope rejected for {evidence.kind.value}: {evidence.evaluation_scope.value}"
        )
    if evidence.metadata.get("llm_recompute_allowed") is not False:
        raise TechnicalAgentError("Technical Agent evidence must disallow LLM recompute")


def _validate_numeric_claim_citation(claim: ResearchClaim, citation: ReportCitation) -> None:
    if claim.value != citation.cited_value:
        raise TechnicalAgentError(f"numeric claim cited_value mismatch: {claim.claim_id}")
    if claim.unit != citation.unit:
        raise TechnicalAgentError(f"numeric claim unit mismatch: {claim.claim_id}")
    if claim.formula_version != citation.formula_version:
        raise TechnicalAgentError(f"numeric claim formula_version mismatch: {claim.claim_id}")
    if dict(claim.dataset_versions) != dict(citation.dataset_versions):
        raise TechnicalAgentError(f"numeric claim dataset_versions mismatch: {claim.claim_id}")
    if citation.run_id is not None and claim.run_id != citation.run_id:
        raise TechnicalAgentError(f"numeric claim run_id mismatch: {claim.claim_id}")
    if citation.artifact_hash is not None and claim.artifact_hash != citation.artifact_hash:
        raise TechnicalAgentError(f"numeric claim artifact_hash mismatch: {claim.claim_id}")


def _required_string(field_name: str, value: str) -> str:
    if type(value) is not str or not value.strip():
        raise TechnicalAgentError(f"{field_name} is required")
    return value


def _ratio(field_name: str, value: float) -> float:
    if type(value) not in {int, float} or isinstance(value, bool):
        raise TechnicalAgentError(f"{field_name} must be numeric")
    normalized = float(value)
    if normalized < 0.0 or normalized > 1.0:
        raise TechnicalAgentError(f"{field_name} must be between 0 and 1")
    return normalized


def _int_range(field_name: str, value: int, *, minimum: int, maximum: int) -> int:
    if type(value) is not int or isinstance(value, bool):
        raise TechnicalAgentError(f"{field_name} must be an integer")
    if value < minimum or value > maximum:
        raise TechnicalAgentError(f"{field_name} must be between {minimum} and {maximum}")
    return value


def _float_mapping(field_name: str, value: Mapping[str, float]) -> dict[str, float]:
    if not isinstance(value, Mapping):
        raise TechnicalAgentError(f"{field_name} must be a mapping")
    normalized: dict[str, float] = {}
    for key, item in value.items():
        name = _required_string(f"{field_name} key", key)
        if type(item) not in {int, float} or isinstance(item, bool):
            raise TechnicalAgentError(f"{field_name}.{name} must be numeric")
        normalized[name] = float(item)
    return dict(sorted(normalized.items()))


def _string_tuple(field_name: str, value: Sequence[str]) -> tuple[str, ...]:
    if isinstance(value, str) or not isinstance(value, Sequence):
        raise TechnicalAgentError(f"{field_name} must be a sequence")
    return tuple(_required_string(field_name, item) for item in value)


def _hash_record(record: Mapping[str, Any]) -> str:
    payload = json.dumps(_plain_json_value(record), sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return f"sha256:{hashlib.sha256(payload.encode('utf-8')).hexdigest()}"


def _plain_json_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _plain_json_value(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_plain_json_value(item) for item in value]
    if isinstance(value, list):
        return [_plain_json_value(item) for item in value]
    return value


__all__ = [
    "TECHNICAL_AGENT_CONTRACT_VERSION",
    "TECHNICAL_AGENT_OUTPUT_SCHEMA_NAME",
    "TECHNICAL_AGENT_PROMPT_PAYLOAD_SCHEMA_NAME",
    "TECHNICAL_AGENT_SCHEMA_VERSION",
    "EvidenceScopedTechnicalAgent",
    "TechnicalAgentError",
    "TechnicalAgentPromptPayload",
    "TechnicalAgentPromptRequest",
    "TechnicalAgentResult",
    "TechnicalAgentStructuredOutput",
    "TechnicalSignal",
    "TechnicalTrendAlignment",
    "TechnicalVolumeStatus",
]
