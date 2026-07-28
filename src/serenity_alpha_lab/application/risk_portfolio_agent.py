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


RISK_PORTFOLIO_AGENT_CONTRACT_VERSION = "research.agent.risk_portfolio@1.0.0"
RISK_PORTFOLIO_AGENT_PROMPT_PAYLOAD_SCHEMA_NAME = "research.agent.risk_portfolio_prompt_payload"
RISK_PORTFOLIO_AGENT_OUTPUT_SCHEMA_NAME = "research.agent.risk_portfolio_output_adapter"
RISK_PORTFOLIO_AGENT_SCHEMA_VERSION = "1.0.0"

_ALLOWED_RISK_PORTFOLIO_SCOPE_BY_KIND = {
    EvidenceKind.RISK_POLICY_RESULT: frozenset({EvidenceEvaluationScope.FORMAL_PORTFOLIO_BACKTEST}),
    EvidenceKind.BACKTEST_BIAS_AUDIT: frozenset({EvidenceEvaluationScope.FORMAL_PORTFOLIO_BACKTEST}),
    EvidenceKind.BACKTEST_PERFORMANCE_METRICS: frozenset({EvidenceEvaluationScope.FORMAL_PORTFOLIO_BACKTEST}),
    EvidenceKind.BACKTEST_RUN_SUMMARY: frozenset({EvidenceEvaluationScope.FORMAL_PORTFOLIO_BACKTEST}),
    EvidenceKind.BACKTEST_ARTIFACT_BUNDLE: frozenset({EvidenceEvaluationScope.FORMAL_PORTFOLIO_BACKTEST}),
    EvidenceKind.FORMAL_BACKTEST_API_RECORD: frozenset(
        {EvidenceEvaluationScope.FORMAL_PORTFOLIO_BACKTEST, EvidenceEvaluationScope.API_LINEAGE}
    ),
}
_FORBIDDEN_ACTIONS = (
    "call_real_provider",
    "call_real_llm",
    "run_dsa_agent_tools",
    "read_evidence_body",
    "write_evidence_store",
    "run_backtest",
    "simulate_orders",
    "recompute_risk_policy",
    "recompute_backtest_metrics",
    "recompute_costs_or_slippage",
    "override_risk_policy",
    "override_bias_audit",
    "promote_formal_backtest",
    "start_worker_loop",
    "initialize_qlib_runtime",
    "render_report",
    "place_or_simulate_trade",
)
_SEVERITY = {"pass": 0, "warn": 1, "not_evaluable": 2, "block": 3}


class RiskPortfolioAgentError(ValueError):
    """Raised when Risk/Portfolio Agent evidence or output violates the P5 contract."""


class RiskPortfolioGateStatus(StrEnum):
    PASS = "pass"
    WARN = "warn"
    BLOCK = "block"
    NOT_EVALUABLE = "not_evaluable"


class RiskPortfolioAction(StrEnum):
    ELIGIBLE = "eligible"
    WATCHLIST = "watchlist"
    REDUCE = "reduce"
    AVOID = "avoid"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


@dataclass(frozen=True, slots=True)
class RiskPortfolioAgentPromptRequest:
    run_id: str
    stage_id: str
    bundle: EvidenceBundle
    prompt_binding: PromptRunBinding

    def __post_init__(self) -> None:
        object.__setattr__(self, "run_id", _required_string("run_id", self.run_id))
        object.__setattr__(self, "stage_id", _required_string("stage_id", self.stage_id))
        if type(self.bundle) is not EvidenceBundle:
            raise RiskPortfolioAgentError("bundle must be an EvidenceBundle")
        if type(self.prompt_binding) is not PromptRunBinding:
            raise RiskPortfolioAgentError("prompt_binding must be a PromptRunBinding")
        if self.bundle.request.role is not EvidenceBundleRole.RISK_PORTFOLIO:
            raise RiskPortfolioAgentError("Risk/Portfolio Agent requires a risk_portfolio EvidenceBundle")
        if self.prompt_binding.request.role is not AgentPromptRole.RISK_PORTFOLIO:
            raise RiskPortfolioAgentError("Risk/Portfolio Agent requires a risk_portfolio prompt binding")
        if self.prompt_binding.request.run_id != self.run_id:
            raise RiskPortfolioAgentError("prompt binding run_id must match the Risk/Portfolio Agent request")
        if self.prompt_binding.request.stage_id != self.stage_id:
            raise RiskPortfolioAgentError("prompt binding stage_id must match the Risk/Portfolio Agent request")


@dataclass(frozen=True, slots=True)
class RiskPortfolioAgentPromptPayload:
    bundle: EvidenceBundle
    prompt_binding: PromptRunBinding
    allowed_evidence_ids: tuple[str, ...]
    allowed_evidence_hashes: tuple[str, ...]
    hard_gate_summary: Mapping[str, Any]
    forbidden_actions: tuple[str, ...] = _FORBIDDEN_ACTIONS
    contract_version: str = RISK_PORTFOLIO_AGENT_CONTRACT_VERSION
    schema_name: str = RISK_PORTFOLIO_AGENT_PROMPT_PAYLOAD_SCHEMA_NAME
    schema_version: str = RISK_PORTFOLIO_AGENT_SCHEMA_VERSION

    @property
    def hard_gate_status(self) -> RiskPortfolioGateStatus:
        return RiskPortfolioGateStatus(str(self.hard_gate_summary["status"]))

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
            "hard_gate_summary": _plain_json_value(self.hard_gate_summary),
            "forbidden_actions": list(self.forbidden_actions),
        }
        if include_hash:
            record["payload_hash"] = self.payload_hash
        return record


@dataclass(frozen=True, slots=True)
class RiskPortfolioStructuredOutput:
    gate_status: RiskPortfolioGateStatus
    portfolio_action: RiskPortfolioAction
    confidence: float
    summary: str
    claims: Sequence[ResearchClaim]
    citations: Sequence[ReportCitation]
    risk_factors: Sequence[str]
    portfolio_constraints: Sequence[str]
    warnings: Sequence[str] = ()
    limitations: Sequence[str] = ()
    contract_version: str = RISK_PORTFOLIO_AGENT_CONTRACT_VERSION
    schema_name: str = RISK_PORTFOLIO_AGENT_OUTPUT_SCHEMA_NAME
    schema_version: str = RISK_PORTFOLIO_AGENT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "gate_status", RiskPortfolioGateStatus(self.gate_status))
        object.__setattr__(self, "portfolio_action", RiskPortfolioAction(self.portfolio_action))
        object.__setattr__(self, "confidence", _ratio("confidence", self.confidence))
        object.__setattr__(self, "summary", _required_string("summary", self.summary))
        claims = tuple(self.claims)
        citations = tuple(self.citations)
        for claim in claims:
            if type(claim) is not ResearchClaim:
                raise RiskPortfolioAgentError("claims must contain ResearchClaim objects")
        for citation in citations:
            if type(citation) is not ReportCitation:
                raise RiskPortfolioAgentError("citations must contain ReportCitation objects")
        object.__setattr__(self, "claims", claims)
        object.__setattr__(self, "citations", citations)
        object.__setattr__(self, "risk_factors", _string_tuple("risk_factors", self.risk_factors))
        object.__setattr__(
            self,
            "portfolio_constraints",
            _string_tuple("portfolio_constraints", self.portfolio_constraints),
        )
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
            "gate_status": self.gate_status.value,
            "portfolio_action": self.portfolio_action.value,
            "confidence": self.confidence,
            "summary": self.summary,
            "claims": [claim.to_record() for claim in self.claims],
            "citations": [citation.to_record() for citation in self.citations],
            "risk_factors": list(self.risk_factors),
            "portfolio_constraints": list(self.portfolio_constraints),
            "warnings": list(self.warnings),
            "limitations": list(self.limitations),
        }


@dataclass(frozen=True, slots=True)
class RiskPortfolioAgentResult:
    prompt_payload: RiskPortfolioAgentPromptPayload
    output: RiskPortfolioStructuredOutput
    contract_version: str = RISK_PORTFOLIO_AGENT_CONTRACT_VERSION
    schema_name: str = "research.agent.risk_portfolio_result"
    schema_version: str = RISK_PORTFOLIO_AGENT_SCHEMA_VERSION

    def to_record(self) -> dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "schema_name": self.schema_name,
            "schema_version": self.schema_version,
            "prompt_payload_hash": self.prompt_payload.payload_hash,
            "bundle_id": self.prompt_payload.bundle.bundle_id,
            "prompt_binding_hash": self.prompt_payload.prompt_binding.binding_hash,
            "hard_gate_summary": _plain_json_value(self.prompt_payload.hard_gate_summary),
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
                "hard_gate_summary": _plain_json_value(self.prompt_payload.hard_gate_summary),
            }
        )
        return {
            "agent_name": "risk_portfolio",
            "signal": _signal_for(self.output.gate_status, self.output.portfolio_action),
            "risk_status": self.output.gate_status.value,
            "portfolio_action": self.output.portfolio_action.value,
            "confidence": self.output.confidence,
            "reasoning": self.output.summary,
            "raw_data": raw_data,
        }

    def to_dsa_dashboard_fields(self) -> dict[str, Any]:
        hard_gates = _plain_json_value(self.prompt_payload.hard_gate_summary)
        return {
            "risk_analysis": self.output.summary,
            "portfolio_analysis": self.output.summary,
            "risk_status": self.output.gate_status.value,
            "portfolio_action": self.output.portfolio_action.value,
            "hard_gates": hard_gates,
            "risk_factors": list(self.output.risk_factors),
            "portfolio_constraints": list(self.output.portfolio_constraints),
            "warnings": list(self.output.warnings),
            "limitations": list(self.output.limitations),
            "citations": [citation.to_record() for citation in self.output.citations],
        }


class EvidenceScopedRiskPortfolioAgent:
    """Offline Risk/Portfolio Agent boundary over P5 formal evidence."""

    def prepare_prompt_payload(self, request: RiskPortfolioAgentPromptRequest) -> RiskPortfolioAgentPromptPayload:
        if type(request) is not RiskPortfolioAgentPromptRequest:
            raise RiskPortfolioAgentError("request must be a RiskPortfolioAgentPromptRequest")
        hard_gate = _HardGateAccumulator()
        for item in request.bundle.items:
            _validate_allowed_evidence(item.evidence)
            hard_gate.add(item.evidence)
        return RiskPortfolioAgentPromptPayload(
            bundle=request.bundle,
            prompt_binding=request.prompt_binding,
            allowed_evidence_ids=tuple(item.evidence.evidence_id for item in request.bundle.items),
            allowed_evidence_hashes=tuple(item.evidence.content_hash for item in request.bundle.items),
            hard_gate_summary=hard_gate.to_record(),
        )

    def finalize_output(
        self,
        prompt_payload: RiskPortfolioAgentPromptPayload,
        output: RiskPortfolioStructuredOutput,
    ) -> RiskPortfolioAgentResult:
        if type(prompt_payload) is not RiskPortfolioAgentPromptPayload:
            raise RiskPortfolioAgentError("prompt_payload must be a RiskPortfolioAgentPromptPayload")
        if type(output) is not RiskPortfolioStructuredOutput:
            raise RiskPortfolioAgentError("output must be a RiskPortfolioStructuredOutput")
        _validate_gate_preserved(prompt_payload.hard_gate_status, output.gate_status)
        evidence_by_id = {item.evidence.evidence_id: item.evidence for item in prompt_payload.bundle.items}
        citations_by_id = {citation.citation_id: citation for citation in output.citations}
        if len(citations_by_id) != len(tuple(output.citations)):
            raise RiskPortfolioAgentError("duplicate citation_id in Risk/Portfolio Agent output")

        for citation in output.citations:
            evidence = evidence_by_id.get(citation.evidence_id)
            if evidence is None:
                raise RiskPortfolioAgentError(
                    f"citation evidence_id is not included in the EvidenceBundle: {citation.evidence_id}"
                )
            if evidence.artifact_hash and citation.artifact_hash != evidence.artifact_hash:
                raise RiskPortfolioAgentError(f"citation artifact_hash does not match evidence: {citation.citation_id}")
            if evidence.dataset_versions and dict(citation.dataset_versions) != dict(evidence.dataset_versions):
                raise RiskPortfolioAgentError(
                    f"citation dataset_versions do not match evidence: {citation.citation_id}"
                )
            if evidence.run_id and citation.run_id != evidence.run_id:
                raise RiskPortfolioAgentError(f"citation run_id does not match evidence: {citation.citation_id}")
            if evidence.stage_id and citation.stage_id != evidence.stage_id:
                raise RiskPortfolioAgentError(f"citation stage_id does not match evidence: {citation.citation_id}")
            if (
                citation.formula_version is not None
                and evidence.formula_versions
                and citation.formula_version not in set(evidence.formula_versions.values())
            ):
                raise RiskPortfolioAgentError(
                    f"citation formula_version does not match evidence: {citation.citation_id}"
                )

        for claim in output.claims:
            for citation_id in claim.citation_ids:
                if citation_id not in citations_by_id:
                    raise RiskPortfolioAgentError(f"claim references unknown citation_id: {citation_id}")
            if claim.kind is ClaimKind.NUMERIC_METRIC:
                if claim.computation_policy is not ClaimComputationPolicy.DETERMINISTIC_EVIDENCE:
                    raise RiskPortfolioAgentError("Risk/Portfolio numeric claims must use deterministic_evidence")
                for citation_id in claim.citation_ids:
                    citation = citations_by_id[citation_id]
                    if citation.unit is None or citation.formula_version is None:
                        raise RiskPortfolioAgentError("Risk/Portfolio numeric claim citations require unit and formula_version")
                    _validate_numeric_claim_citation(claim, citation)
            if claim.kind is ClaimKind.RISK_GATE:
                _validate_risk_gate_claim(claim, citations_by_id, output.gate_status)

        return RiskPortfolioAgentResult(prompt_payload=prompt_payload, output=output)


class _HardGateAccumulator:
    def __init__(self) -> None:
        self.status = RiskPortfolioGateStatus.PASS
        self.blocking_evidence_ids: list[str] = []
        self.warning_evidence_ids: list[str] = []
        self.not_evaluable_rule_ids: list[str] = []
        self.risk_statuses: dict[str, str] = {}
        self.audit_statuses: dict[str, str] = {}
        self.eligible_for_ranking: bool | None = None
        self.agent_strong_conclusion_allowed: bool | None = None

    def add(self, evidence: EvidenceRecord) -> None:
        metadata = evidence.metadata
        risk_status = _optional_status(metadata.get("risk_status"))
        if risk_status is not None:
            self.risk_statuses[evidence.evidence_id] = risk_status.value
            self._raise_status(risk_status, evidence.evidence_id)
        audit_status = _audit_status(metadata.get("audit_status"))
        if audit_status is not None:
            self.audit_statuses[evidence.evidence_id] = audit_status
            if audit_status == "invalid":
                self._raise_status(RiskPortfolioGateStatus.BLOCK, evidence.evidence_id)
            elif audit_status == "warn":
                self._raise_status(RiskPortfolioGateStatus.WARN, evidence.evidence_id)
        if metadata.get("eligible_for_ranking") is False:
            self.eligible_for_ranking = False
            self._raise_status(RiskPortfolioGateStatus.BLOCK, evidence.evidence_id)
        elif metadata.get("eligible_for_ranking") is True and self.eligible_for_ranking is None:
            self.eligible_for_ranking = True
        if metadata.get("agent_strong_conclusion_allowed") is False:
            self.agent_strong_conclusion_allowed = False
        elif metadata.get("agent_strong_conclusion_allowed") is True and self.agent_strong_conclusion_allowed is None:
            self.agent_strong_conclusion_allowed = True

        for rule_id in _string_items(metadata.get("not_evaluable_rule_ids")):
            self.not_evaluable_rule_ids.append(rule_id)
            self._raise_status(RiskPortfolioGateStatus.NOT_EVALUABLE, evidence.evidence_id)

    def to_record(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "blocking_evidence_ids": sorted(set(self.blocking_evidence_ids)),
            "warning_evidence_ids": sorted(set(self.warning_evidence_ids)),
            "not_evaluable_rule_ids": sorted(set(self.not_evaluable_rule_ids)),
            "risk_statuses": dict(sorted(self.risk_statuses.items())),
            "audit_statuses": dict(sorted(self.audit_statuses.items())),
            "eligible_for_ranking": self.eligible_for_ranking,
            "agent_strong_conclusion_allowed": self.agent_strong_conclusion_allowed,
        }

    def _raise_status(self, status: RiskPortfolioGateStatus, evidence_id: str) -> None:
        if _SEVERITY[status.value] > _SEVERITY[self.status.value]:
            self.status = status
        if status is RiskPortfolioGateStatus.BLOCK:
            self.blocking_evidence_ids.append(evidence_id)
        elif status in {RiskPortfolioGateStatus.WARN, RiskPortfolioGateStatus.NOT_EVALUABLE}:
            self.warning_evidence_ids.append(evidence_id)


def _validate_allowed_evidence(evidence: EvidenceRecord) -> None:
    if type(evidence) is not EvidenceRecord:
        raise RiskPortfolioAgentError("EvidenceBundle items must contain EvidenceRecord objects")
    allowed_scopes = _ALLOWED_RISK_PORTFOLIO_SCOPE_BY_KIND.get(evidence.kind)
    if allowed_scopes is None:
        raise RiskPortfolioAgentError(
            f"Risk/Portfolio Agent evidence allowlist rejected evidence kind: {evidence.kind.value}"
        )
    if evidence.evaluation_scope not in allowed_scopes:
        raise RiskPortfolioAgentError(
            f"Risk/Portfolio Agent evidence scope rejected for {evidence.kind.value}: {evidence.evaluation_scope.value}"
        )
    if evidence.metadata.get("llm_recompute_allowed") is not False:
        raise RiskPortfolioAgentError("Risk/Portfolio Agent evidence must disallow LLM recompute")


def _validate_gate_preserved(prompt_status: RiskPortfolioGateStatus, output_status: RiskPortfolioGateStatus) -> None:
    if prompt_status in {RiskPortfolioGateStatus.BLOCK, RiskPortfolioGateStatus.NOT_EVALUABLE}:
        if output_status is not prompt_status:
            raise RiskPortfolioAgentError("Risk/Portfolio Agent output cannot upgrade hard gate status")
    elif _SEVERITY[output_status.value] < _SEVERITY[prompt_status.value]:
        raise RiskPortfolioAgentError("Risk/Portfolio Agent output cannot upgrade hard gate status")


def _validate_numeric_claim_citation(claim: ResearchClaim, citation: ReportCitation) -> None:
    if claim.value != citation.cited_value:
        raise RiskPortfolioAgentError(f"numeric claim cited_value mismatch: {claim.claim_id}")
    if claim.unit != citation.unit:
        raise RiskPortfolioAgentError(f"numeric claim unit mismatch: {claim.claim_id}")
    if claim.formula_version != citation.formula_version:
        raise RiskPortfolioAgentError(f"numeric claim formula_version mismatch: {claim.claim_id}")
    if dict(claim.dataset_versions) != dict(citation.dataset_versions):
        raise RiskPortfolioAgentError(f"numeric claim dataset_versions mismatch: {claim.claim_id}")
    if citation.run_id is not None and claim.run_id != citation.run_id:
        raise RiskPortfolioAgentError(f"numeric claim run_id mismatch: {claim.claim_id}")
    if citation.stage_id is not None and claim.stage_id != citation.stage_id:
        raise RiskPortfolioAgentError(f"numeric claim stage_id mismatch: {claim.claim_id}")
    if citation.artifact_hash is not None and claim.artifact_hash != citation.artifact_hash:
        raise RiskPortfolioAgentError(f"numeric claim artifact_hash mismatch: {claim.claim_id}")


def _validate_risk_gate_claim(
    claim: ResearchClaim,
    citations_by_id: Mapping[str, ReportCitation],
    output_gate_status: RiskPortfolioGateStatus,
) -> None:
    if not claim.citation_ids:
        raise RiskPortfolioAgentError("Risk gate claims require citations")
    if claim.computation_policy is ClaimComputationPolicy.LLM_NARRATIVE:
        raise RiskPortfolioAgentError("Risk gate claims cannot use llm_narrative")
    if claim.value is not None and str(claim.value) != output_gate_status.value:
        raise RiskPortfolioAgentError("Risk gate claim value must match output gate_status")
    for citation_id in claim.citation_ids:
        citation = citations_by_id[citation_id]
        if citation.cited_value is not None and claim.value is not None and citation.cited_value != claim.value:
            raise RiskPortfolioAgentError(f"risk gate claim cited_value mismatch: {claim.claim_id}")


def _signal_for(gate_status: RiskPortfolioGateStatus, action: RiskPortfolioAction) -> str:
    if gate_status is RiskPortfolioGateStatus.BLOCK:
        return "negative"
    if gate_status is RiskPortfolioGateStatus.NOT_EVALUABLE:
        return "insufficient_evidence"
    if action in {RiskPortfolioAction.REDUCE, RiskPortfolioAction.AVOID}:
        return "negative"
    if action is RiskPortfolioAction.WATCHLIST:
        return "neutral"
    return "positive"


def _optional_status(value: Any) -> RiskPortfolioGateStatus | None:
    if value is None:
        return None
    text = str(value)
    if text == "not-evaluable":
        text = "not_evaluable"
    try:
        return RiskPortfolioGateStatus(text)
    except ValueError as exc:
        raise RiskPortfolioAgentError(f"unknown risk status: {value}") from exc


def _audit_status(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).lower().strip()
    if text not in {"pass", "warn", "invalid"}:
        raise RiskPortfolioAgentError(f"unknown audit status: {value}")
    return text


def _string_items(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (_required_string("not_evaluable_rule_id", value),)
    if isinstance(value, Sequence):
        return tuple(_required_string("not_evaluable_rule_id", item) for item in value)
    raise RiskPortfolioAgentError("not_evaluable_rule_ids must be a sequence")


def _required_string(field_name: str, value: Any) -> str:
    if type(value) is not str or not value.strip():
        raise RiskPortfolioAgentError(f"{field_name} is required")
    return value


def _ratio(field_name: str, value: float) -> float:
    if type(value) not in {int, float} or isinstance(value, bool):
        raise RiskPortfolioAgentError(f"{field_name} must be numeric")
    normalized = float(value)
    if normalized < 0.0 or normalized > 1.0:
        raise RiskPortfolioAgentError(f"{field_name} must be between 0 and 1")
    return normalized


def _string_tuple(field_name: str, value: Sequence[str]) -> tuple[str, ...]:
    if isinstance(value, str) or not isinstance(value, Sequence):
        raise RiskPortfolioAgentError(f"{field_name} must be a sequence")
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


__all__ = [
    "RISK_PORTFOLIO_AGENT_CONTRACT_VERSION",
    "RISK_PORTFOLIO_AGENT_OUTPUT_SCHEMA_NAME",
    "RISK_PORTFOLIO_AGENT_PROMPT_PAYLOAD_SCHEMA_NAME",
    "RISK_PORTFOLIO_AGENT_SCHEMA_VERSION",
    "EvidenceScopedRiskPortfolioAgent",
    "RiskPortfolioAction",
    "RiskPortfolioAgentError",
    "RiskPortfolioAgentPromptPayload",
    "RiskPortfolioAgentPromptRequest",
    "RiskPortfolioAgentResult",
    "RiskPortfolioGateStatus",
    "RiskPortfolioStructuredOutput",
]
