from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from serenity_alpha_lab.application.evidence_bundle_builder import EvidenceBundle, EvidenceBundleRole
from serenity_alpha_lab.application.intel_agent import IntelAgentResult
from serenity_alpha_lab.application.risk_portfolio_agent import (
    RiskPortfolioAgentResult,
    RiskPortfolioGateStatus,
)
from serenity_alpha_lab.application.technical_agent import TechnicalAgentResult
from serenity_alpha_lab.evidence.prompt_registry import AgentPromptRole, PromptRunBinding
from serenity_alpha_lab.evidence.schema import (
    ClaimComputationPolicy,
    ClaimKind,
    EvidenceRecord,
    ReportCitation,
    ResearchClaim,
)


DECISION_AGENT_CONTRACT_VERSION = "research.agent.decision@1.0.0"
DECISION_AGENT_PROMPT_PAYLOAD_SCHEMA_NAME = "research.agent.decision_prompt_payload"
DECISION_AGENT_OUTPUT_SCHEMA_NAME = "research.agent.decision_output_adapter"
DECISION_AGENT_SCHEMA_VERSION = "1.0.0"

_ROLE_NAMES = ("technical", "intel", "risk_portfolio")
_FORBIDDEN_ACTIONS = (
    "call_real_provider",
    "call_real_llm",
    "run_dsa_agent_tools",
    "fetch_realtime_quote",
    "fetch_news_or_search",
    "read_evidence_body",
    "write_evidence_store",
    "recompute_technical_indicators",
    "recompute_source_trust",
    "recompute_backtest_metrics",
    "override_risk_policy",
    "execute_backtest_task",
    "initialize_qlib_runtime",
    "start_worker_loop",
    "render_report",
    "place_or_simulate_trade",
)
_UPGRADE_RECOMMENDATIONS = frozenset({"strong_buy", "buy", "hold", "watchlist"})
_BLOCK_PRESERVING_RECOMMENDATIONS = frozenset({"blocked", "avoid"})
_NOT_EVALUABLE_RECOMMENDATIONS = frozenset({"insufficient_evidence", "blocked", "avoid"})


class DecisionAgentError(ValueError):
    """Raised when Decision Agent synthesis violates the P5 evidence contract."""


class DecisionRecommendation(StrEnum):
    STRONG_BUY = "strong_buy"
    BUY = "buy"
    HOLD = "hold"
    WATCHLIST = "watchlist"
    REDUCE = "reduce"
    AVOID = "avoid"
    BLOCKED = "blocked"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class DecisionConfidenceLevel(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INSUFFICIENT = "insufficient"


class DecisionCaseSide(StrEnum):
    BULL = "bull"
    BEAR = "bear"


@dataclass(frozen=True, slots=True)
class DecisionAgentPromptRequest:
    run_id: str
    stage_id: str
    bundle: EvidenceBundle
    prompt_binding: PromptRunBinding
    technical_result: TechnicalAgentResult
    intel_result: IntelAgentResult
    risk_portfolio_result: RiskPortfolioAgentResult

    def __post_init__(self) -> None:
        object.__setattr__(self, "run_id", _required_string("run_id", self.run_id))
        object.__setattr__(self, "stage_id", _required_string("stage_id", self.stage_id))
        if type(self.bundle) is not EvidenceBundle:
            raise DecisionAgentError("bundle must be an EvidenceBundle")
        if type(self.prompt_binding) is not PromptRunBinding:
            raise DecisionAgentError("prompt_binding must be a PromptRunBinding")
        if type(self.technical_result) is not TechnicalAgentResult:
            raise DecisionAgentError("technical_result must be a TechnicalAgentResult")
        if type(self.intel_result) is not IntelAgentResult:
            raise DecisionAgentError("intel_result must be an IntelAgentResult")
        if type(self.risk_portfolio_result) is not RiskPortfolioAgentResult:
            raise DecisionAgentError("risk_portfolio_result must be a RiskPortfolioAgentResult")
        if self.bundle.request.role is not EvidenceBundleRole.DECISION:
            raise DecisionAgentError("Decision Agent requires a decision EvidenceBundle")
        if self.prompt_binding.request.role is not AgentPromptRole.DECISION:
            raise DecisionAgentError("Decision Agent requires a decision prompt binding")
        if self.prompt_binding.request.run_id != self.run_id:
            raise DecisionAgentError("prompt binding run_id must match the Decision Agent request")
        if self.prompt_binding.request.stage_id != self.stage_id:
            raise DecisionAgentError("prompt binding stage_id must match the Decision Agent request")


@dataclass(frozen=True, slots=True)
class DecisionAgentPromptPayload:
    bundle: EvidenceBundle
    prompt_binding: PromptRunBinding
    technical_result: TechnicalAgentResult
    intel_result: IntelAgentResult
    risk_portfolio_result: RiskPortfolioAgentResult
    allowed_evidence_ids: tuple[str, ...]
    allowed_evidence_hashes: tuple[str, ...]
    role_result_hashes: Mapping[str, str]
    role_citation_evidence_ids: Mapping[str, tuple[str, ...]]
    risk_gate_summary: Mapping[str, Any]
    forbidden_actions: tuple[str, ...] = _FORBIDDEN_ACTIONS
    contract_version: str = DECISION_AGENT_CONTRACT_VERSION
    schema_name: str = DECISION_AGENT_PROMPT_PAYLOAD_SCHEMA_NAME
    schema_version: str = DECISION_AGENT_SCHEMA_VERSION

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
            "role_result_hashes": dict(self.role_result_hashes),
            "role_citation_evidence_ids": {
                role: list(evidence_ids) for role, evidence_ids in self.role_citation_evidence_ids.items()
            },
            "risk_gate_summary": _plain_json_value(self.risk_gate_summary),
            "prior_role_results": {
                "technical": self.technical_result.to_record(),
                "intel": self.intel_result.to_record(),
                "risk_portfolio": self.risk_portfolio_result.to_record(),
            },
            "forbidden_actions": list(self.forbidden_actions),
        }
        if include_hash:
            record["payload_hash"] = self.payload_hash
        return record


@dataclass(frozen=True, slots=True)
class DecisionCase:
    case_id: str
    side: DecisionCaseSide
    thesis: str
    factors: Sequence[str]
    citation_ids: Sequence[str]
    source_roles: Sequence[str]

    def __post_init__(self) -> None:
        object.__setattr__(self, "case_id", _required_string("case_id", self.case_id))
        object.__setattr__(self, "side", DecisionCaseSide(self.side))
        object.__setattr__(self, "thesis", _required_string("thesis", self.thesis))
        object.__setattr__(self, "factors", _string_tuple("factors", self.factors))
        object.__setattr__(self, "citation_ids", _string_tuple("citation_ids", self.citation_ids))
        object.__setattr__(self, "source_roles", _role_tuple(self.source_roles))
        if not self.factors:
            raise DecisionAgentError("Decision cases require at least one factor")
        if not self.citation_ids:
            raise DecisionAgentError("Decision cases require citations")
        if not self.source_roles:
            raise DecisionAgentError("Decision cases require source_roles")

    def to_record(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "side": self.side.value,
            "thesis": self.thesis,
            "factors": list(self.factors),
            "citation_ids": list(self.citation_ids),
            "source_roles": list(self.source_roles),
        }


@dataclass(frozen=True, slots=True)
class DecisionDisagreementSummary:
    summary: str
    unresolved_conflicts: Sequence[str]
    citation_ids: Sequence[str]

    def __post_init__(self) -> None:
        object.__setattr__(self, "summary", _required_string("summary", self.summary))
        object.__setattr__(self, "unresolved_conflicts", _string_tuple("unresolved_conflicts", self.unresolved_conflicts))
        object.__setattr__(self, "citation_ids", _string_tuple("citation_ids", self.citation_ids))

    def to_record(self) -> dict[str, Any]:
        return {
            "summary": self.summary,
            "unresolved_conflicts": list(self.unresolved_conflicts),
            "citation_ids": list(self.citation_ids),
        }


@dataclass(frozen=True, slots=True)
class DecisionInvalidationCondition:
    condition_id: str
    description: str
    citation_ids: Sequence[str]

    def __post_init__(self) -> None:
        object.__setattr__(self, "condition_id", _required_string("condition_id", self.condition_id))
        object.__setattr__(self, "description", _required_string("description", self.description))
        object.__setattr__(self, "citation_ids", _string_tuple("citation_ids", self.citation_ids))
        if not self.citation_ids:
            raise DecisionAgentError("Decision invalidation conditions require citations")

    def to_record(self) -> dict[str, Any]:
        return {
            "condition_id": self.condition_id,
            "description": self.description,
            "citation_ids": list(self.citation_ids),
        }


@dataclass(frozen=True, slots=True)
class DecisionStructuredOutput:
    recommendation: DecisionRecommendation
    confidence_level: DecisionConfidenceLevel
    confidence: float
    summary: str
    bull_case: DecisionCase
    bear_case: DecisionCase
    disagreement: DecisionDisagreementSummary
    invalidation_conditions: Sequence[DecisionInvalidationCondition]
    claims: Sequence[ResearchClaim]
    citations: Sequence[ReportCitation]
    ranking_eligible: bool
    warnings: Sequence[str] = ()
    limitations: Sequence[str] = ()
    contract_version: str = DECISION_AGENT_CONTRACT_VERSION
    schema_name: str = DECISION_AGENT_OUTPUT_SCHEMA_NAME
    schema_version: str = DECISION_AGENT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "recommendation", DecisionRecommendation(self.recommendation))
        object.__setattr__(self, "confidence_level", DecisionConfidenceLevel(self.confidence_level))
        object.__setattr__(self, "confidence", _ratio("confidence", self.confidence))
        object.__setattr__(self, "summary", _required_string("summary", self.summary))
        if type(self.bull_case) is not DecisionCase:
            raise DecisionAgentError("bull_case must be a DecisionCase")
        if type(self.bear_case) is not DecisionCase:
            raise DecisionAgentError("bear_case must be a DecisionCase")
        if self.bull_case.side is not DecisionCaseSide.BULL:
            raise DecisionAgentError("bull_case must use side=bull")
        if self.bear_case.side is not DecisionCaseSide.BEAR:
            raise DecisionAgentError("bear_case must use side=bear")
        if type(self.disagreement) is not DecisionDisagreementSummary:
            raise DecisionAgentError("disagreement must be a DecisionDisagreementSummary")
        invalidation_conditions = tuple(self.invalidation_conditions)
        for condition in invalidation_conditions:
            if type(condition) is not DecisionInvalidationCondition:
                raise DecisionAgentError("invalidation_conditions must contain DecisionInvalidationCondition objects")
        claims = tuple(self.claims)
        citations = tuple(self.citations)
        for claim in claims:
            if type(claim) is not ResearchClaim:
                raise DecisionAgentError("claims must contain ResearchClaim objects")
        for citation in citations:
            if type(citation) is not ReportCitation:
                raise DecisionAgentError("citations must contain ReportCitation objects")
        if type(self.ranking_eligible) is not bool:
            raise DecisionAgentError("ranking_eligible must be a bool")
        object.__setattr__(self, "invalidation_conditions", invalidation_conditions)
        object.__setattr__(self, "claims", claims)
        object.__setattr__(self, "citations", citations)
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
            "recommendation": self.recommendation.value,
            "confidence_level": self.confidence_level.value,
            "confidence": self.confidence,
            "summary": self.summary,
            "bull_case": self.bull_case.to_record(),
            "bear_case": self.bear_case.to_record(),
            "disagreement": self.disagreement.to_record(),
            "invalidation_conditions": [condition.to_record() for condition in self.invalidation_conditions],
            "claims": [claim.to_record() for claim in self.claims],
            "citations": [citation.to_record() for citation in self.citations],
            "ranking_eligible": self.ranking_eligible,
            "warnings": list(self.warnings),
            "limitations": list(self.limitations),
        }


@dataclass(frozen=True, slots=True)
class DecisionAgentResult:
    prompt_payload: DecisionAgentPromptPayload
    output: DecisionStructuredOutput
    contract_version: str = DECISION_AGENT_CONTRACT_VERSION
    schema_name: str = "research.agent.decision_result"
    schema_version: str = DECISION_AGENT_SCHEMA_VERSION

    def to_record(self) -> dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "schema_name": self.schema_name,
            "schema_version": self.schema_version,
            "prompt_payload_hash": self.prompt_payload.payload_hash,
            "bundle_id": self.prompt_payload.bundle.bundle_id,
            "prompt_binding_hash": self.prompt_payload.prompt_binding.binding_hash,
            "role_result_hashes": dict(self.prompt_payload.role_result_hashes),
            "risk_gate_summary": _plain_json_value(self.prompt_payload.risk_gate_summary),
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
                "role_result_hashes": dict(self.prompt_payload.role_result_hashes),
                "risk_gate_summary": _plain_json_value(self.prompt_payload.risk_gate_summary),
            }
        )
        return {
            "agent_name": "decision",
            "signal": _signal_for(self.output.recommendation),
            "recommendation": self.output.recommendation.value,
            "confidence": self.output.confidence,
            "confidence_level": self.output.confidence_level.value,
            "reasoning": self.output.summary,
            "raw_data": raw_data,
        }

    def to_dsa_dashboard_fields(self) -> dict[str, Any]:
        return {
            "final_decision": self.output.recommendation.value,
            "decision_summary": self.output.summary,
            "confidence_level": self.output.confidence_level.value,
            "confidence_score": self.output.confidence,
            "ranking_eligible": self.output.ranking_eligible,
            "bull_case": self.output.bull_case.to_record(),
            "bear_case": self.output.bear_case.to_record(),
            "disagreement_summary": self.output.disagreement.to_record(),
            "invalidation_conditions": [condition.to_record() for condition in self.output.invalidation_conditions],
            "risk_gate": _plain_json_value(self.prompt_payload.risk_gate_summary),
            "warnings": list(self.output.warnings),
            "limitations": list(self.output.limitations),
            "citations": [citation.to_record() for citation in self.output.citations],
        }


class EvidenceScopedDecisionAgent:
    """Offline Decision Agent boundary over prior role outputs and P5 EvidenceBundle."""

    def prepare_prompt_payload(self, request: DecisionAgentPromptRequest) -> DecisionAgentPromptPayload:
        if type(request) is not DecisionAgentPromptRequest:
            raise DecisionAgentError("request must be a DecisionAgentPromptRequest")
        prior_role_results = {
            "technical": request.technical_result,
            "intel": request.intel_result,
            "risk_portfolio": request.risk_portfolio_result,
        }
        role_result_hashes = {
            role: _hash_record(result.to_record()) for role, result in prior_role_results.items()
        }
        role_citation_evidence_ids = {
            role: _unique_evidence_ids(result.output.citations) for role, result in prior_role_results.items()
        }
        prior_evidence_ids = set().union(*(set(ids) for ids in role_citation_evidence_ids.values()))
        allowed_items = []
        for item in request.bundle.items:
            if type(item.evidence) is not EvidenceRecord:
                raise DecisionAgentError("EvidenceBundle items must contain EvidenceRecord objects")
            if item.evidence.metadata.get("llm_recompute_allowed") is not False:
                raise DecisionAgentError("Decision Agent evidence must disallow LLM recompute")
            if item.evidence.evidence_id in prior_evidence_ids:
                allowed_items.append(item)

        return DecisionAgentPromptPayload(
            bundle=request.bundle,
            prompt_binding=request.prompt_binding,
            technical_result=request.technical_result,
            intel_result=request.intel_result,
            risk_portfolio_result=request.risk_portfolio_result,
            allowed_evidence_ids=tuple(item.evidence.evidence_id for item in allowed_items),
            allowed_evidence_hashes=tuple(item.evidence.content_hash for item in allowed_items),
            role_result_hashes=role_result_hashes,
            role_citation_evidence_ids=role_citation_evidence_ids,
            risk_gate_summary=request.risk_portfolio_result.prompt_payload.hard_gate_summary,
        )

    def finalize_output(
        self,
        prompt_payload: DecisionAgentPromptPayload,
        output: DecisionStructuredOutput,
    ) -> DecisionAgentResult:
        if type(prompt_payload) is not DecisionAgentPromptPayload:
            raise DecisionAgentError("prompt_payload must be a DecisionAgentPromptPayload")
        if type(output) is not DecisionStructuredOutput:
            raise DecisionAgentError("output must be a DecisionStructuredOutput")

        evidence_by_id = {item.evidence.evidence_id: item.evidence for item in prompt_payload.bundle.items}
        allowed_ids = set(prompt_payload.allowed_evidence_ids)
        prior_roles_by_evidence_id = _prior_roles_by_evidence_id(prompt_payload.role_citation_evidence_ids)
        citations_by_id = {citation.citation_id: citation for citation in output.citations}
        if len(citations_by_id) != len(tuple(output.citations)):
            raise DecisionAgentError("duplicate citation_id in Decision Agent output")

        for citation in output.citations:
            evidence = evidence_by_id.get(citation.evidence_id)
            if evidence is None:
                raise DecisionAgentError(f"citation evidence_id is not included in the decision EvidenceBundle: {citation.evidence_id}")
            if citation.evidence_id not in allowed_ids:
                raise DecisionAgentError(f"citation evidence_id was not cited by prior role outputs: {citation.evidence_id}")
            _validate_citation_matches_evidence(citation, evidence)

        _validate_case(output.bull_case, citations_by_id, prior_roles_by_evidence_id)
        _validate_case(output.bear_case, citations_by_id, prior_roles_by_evidence_id)
        _validate_bull_bear_distinct(output.bull_case, output.bear_case)
        _validate_referenced_citations("disagreement", output.disagreement.citation_ids, citations_by_id)
        for condition in output.invalidation_conditions:
            _validate_referenced_citations("invalidation_condition", condition.citation_ids, citations_by_id)

        for claim in output.claims:
            _validate_claim(claim, citations_by_id, prompt_payload.risk_gate_summary)

        _validate_risk_gate_preserved(prompt_payload.risk_gate_summary, output)
        return DecisionAgentResult(prompt_payload=prompt_payload, output=output)


def _validate_citation_matches_evidence(citation: ReportCitation, evidence: EvidenceRecord) -> None:
    if evidence.artifact_hash and citation.artifact_hash != evidence.artifact_hash:
        raise DecisionAgentError(f"citation artifact_hash does not match evidence: {citation.citation_id}")
    if evidence.dataset_versions and dict(citation.dataset_versions) != dict(evidence.dataset_versions):
        raise DecisionAgentError(f"citation dataset_versions do not match evidence: {citation.citation_id}")
    if evidence.run_id and citation.run_id != evidence.run_id:
        raise DecisionAgentError(f"citation run_id does not match evidence: {citation.citation_id}")
    if evidence.stage_id and citation.stage_id != evidence.stage_id:
        raise DecisionAgentError(f"citation stage_id does not match evidence: {citation.citation_id}")
    if (
        citation.formula_version is not None
        and evidence.formula_versions
        and citation.formula_version not in set(evidence.formula_versions.values())
    ):
        raise DecisionAgentError(f"citation formula_version does not match evidence: {citation.citation_id}")


def _validate_case(
    case: DecisionCase,
    citations_by_id: Mapping[str, ReportCitation],
    prior_roles_by_evidence_id: Mapping[str, set[str]],
) -> None:
    _validate_referenced_citations(case.case_id, case.citation_ids, citations_by_id)
    source_roles = set(case.source_roles)
    for citation_id in case.citation_ids:
        citation = citations_by_id[citation_id]
        prior_roles = prior_roles_by_evidence_id.get(citation.evidence_id, set())
        if prior_roles.isdisjoint(source_roles):
            raise DecisionAgentError(f"Decision case citation is not supported by its source_roles: {case.case_id}")


def _validate_bull_bear_distinct(bull_case: DecisionCase, bear_case: DecisionCase) -> None:
    if bull_case.thesis.strip().casefold() == bear_case.thesis.strip().casefold():
        raise DecisionAgentError("Bull and bear cases must be distinct")
    if set(bull_case.citation_ids) == set(bear_case.citation_ids):
        raise DecisionAgentError("Bull and bear cases must be distinct")
    if {factor.casefold() for factor in bull_case.factors} == {factor.casefold() for factor in bear_case.factors}:
        raise DecisionAgentError("Bull and bear cases must be distinct")


def _validate_referenced_citations(
    owner: str,
    citation_ids: Sequence[str],
    citations_by_id: Mapping[str, ReportCitation],
) -> None:
    for citation_id in citation_ids:
        if citation_id not in citations_by_id:
            raise DecisionAgentError(f"{owner} references unknown citation_id: {citation_id}")


def _validate_claim(
    claim: ResearchClaim,
    citations_by_id: Mapping[str, ReportCitation],
    risk_gate_summary: Mapping[str, Any],
) -> None:
    for citation_id in claim.citation_ids:
        if citation_id not in citations_by_id:
            raise DecisionAgentError(f"claim references unknown citation_id: {citation_id}")
    if claim.kind is ClaimKind.NUMERIC_METRIC:
        if claim.computation_policy is not ClaimComputationPolicy.DETERMINISTIC_EVIDENCE:
            raise DecisionAgentError("Decision numeric claims must use deterministic_evidence")
        for citation_id in claim.citation_ids:
            citation = citations_by_id[citation_id]
            if citation.unit is None or citation.formula_version is None:
                raise DecisionAgentError("Decision numeric claim citations require unit and formula_version")
            _validate_numeric_claim_citation(claim, citation)
    if claim.kind is ClaimKind.RISK_GATE:
        if not claim.citation_ids:
            raise DecisionAgentError("Decision risk gate claims require citations")
        if claim.computation_policy is ClaimComputationPolicy.LLM_NARRATIVE:
            raise DecisionAgentError("Decision risk gate claims cannot use llm_narrative")
        risk_status = str(risk_gate_summary.get("status", ""))
        if claim.value is not None and risk_status in {"block", "not_evaluable"} and str(claim.value) != risk_status:
            raise DecisionAgentError("Decision risk gate claim value must match preserved risk gate")


def _validate_numeric_claim_citation(claim: ResearchClaim, citation: ReportCitation) -> None:
    if claim.value != citation.cited_value:
        raise DecisionAgentError(f"numeric claim cited_value mismatch: {claim.claim_id}")
    if claim.unit != citation.unit:
        raise DecisionAgentError(f"numeric claim unit mismatch: {claim.claim_id}")
    if claim.formula_version != citation.formula_version:
        raise DecisionAgentError(f"numeric claim formula_version mismatch: {claim.claim_id}")
    if dict(claim.dataset_versions) != dict(citation.dataset_versions):
        raise DecisionAgentError(f"numeric claim dataset_versions mismatch: {claim.claim_id}")
    if citation.run_id is not None and claim.run_id != citation.run_id:
        raise DecisionAgentError(f"numeric claim run_id mismatch: {claim.claim_id}")
    if citation.stage_id is not None and claim.stage_id != citation.stage_id:
        raise DecisionAgentError(f"numeric claim stage_id mismatch: {claim.claim_id}")
    if citation.artifact_hash is not None and claim.artifact_hash != citation.artifact_hash:
        raise DecisionAgentError(f"numeric claim artifact_hash mismatch: {claim.claim_id}")


def _validate_risk_gate_preserved(risk_gate_summary: Mapping[str, Any], output: DecisionStructuredOutput) -> None:
    risk_status = _risk_gate_status(risk_gate_summary.get("status", "pass"))
    if risk_status is RiskPortfolioGateStatus.BLOCK and output.recommendation.value not in _BLOCK_PRESERVING_RECOMMENDATIONS:
        raise DecisionAgentError("Decision output cannot upgrade hard gate status")
    if (
        risk_status is RiskPortfolioGateStatus.NOT_EVALUABLE
        and output.recommendation.value not in _NOT_EVALUABLE_RECOMMENDATIONS
    ):
        raise DecisionAgentError("Decision output cannot upgrade hard gate status")
    if output.recommendation.value in _UPGRADE_RECOMMENDATIONS and risk_status in {
        RiskPortfolioGateStatus.BLOCK,
        RiskPortfolioGateStatus.NOT_EVALUABLE,
    }:
        raise DecisionAgentError("Decision output cannot upgrade hard gate status")
    if risk_gate_summary.get("eligible_for_ranking") is False and output.ranking_eligible:
        raise DecisionAgentError("Decision output cannot mark ranking eligible when risk evidence forbids ranking")
    if risk_gate_summary.get("agent_strong_conclusion_allowed") is False:
        if output.recommendation in {DecisionRecommendation.STRONG_BUY, DecisionRecommendation.BUY}:
            raise DecisionAgentError("Decision output cannot make strong conclusion when risk evidence forbids it")
        if output.confidence_level is DecisionConfidenceLevel.HIGH:
            raise DecisionAgentError("Decision output cannot make strong conclusion when risk evidence forbids it")


def _risk_gate_status(value: Any) -> RiskPortfolioGateStatus:
    text = str(value)
    if text == "not-evaluable":
        text = "not_evaluable"
    try:
        return RiskPortfolioGateStatus(text)
    except ValueError as exc:
        raise DecisionAgentError(f"unknown risk gate status: {value}") from exc


def _prior_roles_by_evidence_id(role_citation_evidence_ids: Mapping[str, Sequence[str]]) -> dict[str, set[str]]:
    roles_by_evidence_id: dict[str, set[str]] = {}
    for role, evidence_ids in role_citation_evidence_ids.items():
        for evidence_id in evidence_ids:
            roles_by_evidence_id.setdefault(evidence_id, set()).add(role)
    return roles_by_evidence_id


def _unique_evidence_ids(citations: Sequence[ReportCitation]) -> tuple[str, ...]:
    seen: set[str] = set()
    ordered: list[str] = []
    for citation in citations:
        if citation.evidence_id not in seen:
            seen.add(citation.evidence_id)
            ordered.append(citation.evidence_id)
    return tuple(ordered)


def _role_tuple(values: Sequence[str]) -> tuple[str, ...]:
    roles = _string_tuple("source_roles", values)
    unknown = sorted(set(roles) - set(_ROLE_NAMES))
    if unknown:
        raise DecisionAgentError(f"unknown source_roles: {', '.join(unknown)}")
    return roles


def _required_string(field_name: str, value: Any) -> str:
    if type(value) is not str or not value.strip():
        raise DecisionAgentError(f"{field_name} is required")
    return value


def _ratio(field_name: str, value: float) -> float:
    if type(value) not in {int, float} or isinstance(value, bool):
        raise DecisionAgentError(f"{field_name} must be numeric")
    normalized = float(value)
    if normalized < 0.0 or normalized > 1.0:
        raise DecisionAgentError(f"{field_name} must be between 0 and 1")
    return normalized


def _string_tuple(field_name: str, value: Sequence[str]) -> tuple[str, ...]:
    if isinstance(value, str) or not isinstance(value, Sequence):
        raise DecisionAgentError(f"{field_name} must be a sequence")
    return tuple(_required_string(field_name, item) for item in value)


def _hash_record(record: Mapping[str, Any]) -> str:
    payload = json.dumps(_plain_json_value(record), sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return f"sha256:{hashlib.sha256(payload.encode('utf-8')).hexdigest()}"


def _plain_json_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _plain_json_value(item) for key, item in sorted(value.items(), key=lambda item: str(item[0]))}
    if isinstance(value, tuple | list):
        return [_plain_json_value(item) for item in value]
    if isinstance(value, StrEnum):
        return value.value
    return value


def _signal_for(recommendation: DecisionRecommendation) -> str:
    if recommendation in {DecisionRecommendation.STRONG_BUY, DecisionRecommendation.BUY}:
        return "positive"
    if recommendation in {DecisionRecommendation.HOLD, DecisionRecommendation.WATCHLIST}:
        return "neutral"
    if recommendation is DecisionRecommendation.INSUFFICIENT_EVIDENCE:
        return "insufficient_evidence"
    return "negative"


__all__ = [
    "DECISION_AGENT_CONTRACT_VERSION",
    "DECISION_AGENT_OUTPUT_SCHEMA_NAME",
    "DECISION_AGENT_PROMPT_PAYLOAD_SCHEMA_NAME",
    "DECISION_AGENT_SCHEMA_VERSION",
    "DecisionAgentError",
    "DecisionAgentPromptPayload",
    "DecisionAgentPromptRequest",
    "DecisionAgentResult",
    "DecisionCase",
    "DecisionCaseSide",
    "DecisionConfidenceLevel",
    "DecisionDisagreementSummary",
    "DecisionInvalidationCondition",
    "DecisionRecommendation",
    "DecisionStructuredOutput",
    "EvidenceScopedDecisionAgent",
]
