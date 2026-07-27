from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any

from serenity_alpha_lab.application.evidence_bundle_builder import EvidenceBundle, EvidenceBundleRole
from serenity_alpha_lab.evidence.prompt_registry import AgentPromptRole, PromptRunBinding
from serenity_alpha_lab.evidence.schema import (
    ClaimKind,
    EvidenceEvaluationScope,
    EvidenceKind,
    EvidenceRecord,
    ReportCitation,
    ResearchClaim,
)


INTEL_AGENT_CONTRACT_VERSION = "research.agent.intel@1.0.0"
INTEL_AGENT_PROMPT_PAYLOAD_SCHEMA_NAME = "research.agent.intel_prompt_payload"
INTEL_AGENT_OUTPUT_SCHEMA_NAME = "research.agent.intel_output_adapter"
INTEL_AGENT_SCHEMA_VERSION = "1.0.0"

_FORBIDDEN_ACTIONS = (
    "call_real_provider",
    "call_real_llm",
    "run_dsa_agent_tools",
    "call_live_intelligence_tools",
    "read_evidence_body",
    "write_evidence_store",
    "start_worker_loop",
    "initialize_qlib_runtime",
    "render_report",
    "place_or_simulate_trade",
)


class IntelAgentError(ValueError):
    """Raised when Intel Agent evidence or output violates the P5 contract."""


class IntelSentiment(StrEnum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    MIXED = "mixed"


class IntelEventImpact(StrEnum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    RISK = "risk"


class IntelEventStrength(StrEnum):
    STRONG = "strong"
    WATCHLIST = "watchlist"
    CONTEXT = "context"


class IntelFreshnessStatus(StrEnum):
    FRESH = "fresh"
    STALE = "stale"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class IntelAgentPromptRequest:
    run_id: str
    stage_id: str
    bundle: EvidenceBundle
    prompt_binding: PromptRunBinding

    def __post_init__(self) -> None:
        object.__setattr__(self, "run_id", _required_string("run_id", self.run_id))
        object.__setattr__(self, "stage_id", _required_string("stage_id", self.stage_id))
        if type(self.bundle) is not EvidenceBundle:
            raise IntelAgentError("bundle must be an EvidenceBundle")
        if type(self.prompt_binding) is not PromptRunBinding:
            raise IntelAgentError("prompt_binding must be a PromptRunBinding")
        if self.bundle.request.role is not EvidenceBundleRole.INTEL:
            raise IntelAgentError("Intel Agent requires an intel EvidenceBundle")
        if self.prompt_binding.request.role is not AgentPromptRole.INTEL:
            raise IntelAgentError("Intel Agent requires an intel prompt binding")
        if self.prompt_binding.request.run_id != self.run_id:
            raise IntelAgentError("prompt binding run_id must match the Intel Agent request")
        if self.prompt_binding.request.stage_id != self.stage_id:
            raise IntelAgentError("prompt binding stage_id must match the Intel Agent request")


@dataclass(frozen=True, slots=True)
class IntelAgentPromptPayload:
    bundle: EvidenceBundle
    prompt_binding: PromptRunBinding
    allowed_evidence_ids: tuple[str, ...]
    source_trust_records: tuple[Mapping[str, Any], ...]
    excluded_source_evidence: tuple[Mapping[str, Any], ...]
    forbidden_actions: tuple[str, ...] = _FORBIDDEN_ACTIONS
    contract_version: str = INTEL_AGENT_CONTRACT_VERSION
    schema_name: str = INTEL_AGENT_PROMPT_PAYLOAD_SCHEMA_NAME
    schema_version: str = INTEL_AGENT_SCHEMA_VERSION

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
            "source_trust_records": [_plain_json_value(record) for record in self.source_trust_records],
            "excluded_source_evidence": [_plain_json_value(record) for record in self.excluded_source_evidence],
            "forbidden_actions": list(self.forbidden_actions),
        }
        if include_hash:
            record["payload_hash"] = self.payload_hash
        return record


@dataclass(frozen=True, slots=True)
class IntelAgentStructuredEvent:
    event_id: str
    event_time: datetime
    published_at: datetime
    observed_at: datetime
    available_at: datetime
    summary: str
    impact: IntelEventImpact
    strength: IntelEventStrength
    freshness_status: IntelFreshnessStatus
    source_evidence_ids: Sequence[str]
    citation_ids: Sequence[str]

    def __post_init__(self) -> None:
        object.__setattr__(self, "event_id", _required_string("event_id", self.event_id))
        object.__setattr__(self, "event_time", _aware_datetime("event_time", self.event_time))
        object.__setattr__(self, "published_at", _aware_datetime("published_at", self.published_at))
        object.__setattr__(self, "observed_at", _aware_datetime("observed_at", self.observed_at))
        object.__setattr__(self, "available_at", _aware_datetime("available_at", self.available_at))
        object.__setattr__(self, "summary", _required_string("summary", self.summary))
        object.__setattr__(self, "impact", IntelEventImpact(self.impact))
        object.__setattr__(self, "strength", IntelEventStrength(self.strength))
        object.__setattr__(self, "freshness_status", IntelFreshnessStatus(self.freshness_status))
        object.__setattr__(self, "source_evidence_ids", _string_tuple("source_evidence_ids", self.source_evidence_ids))
        object.__setattr__(self, "citation_ids", _string_tuple("citation_ids", self.citation_ids))

    def to_record(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_time": self.event_time.isoformat(),
            "published_at": self.published_at.isoformat(),
            "observed_at": self.observed_at.isoformat(),
            "available_at": self.available_at.isoformat(),
            "summary": self.summary,
            "impact": self.impact.value,
            "strength": self.strength.value,
            "freshness_status": self.freshness_status.value,
            "source_evidence_ids": list(self.source_evidence_ids),
            "citation_ids": list(self.citation_ids),
        }


@dataclass(frozen=True, slots=True)
class IntelAgentStructuredOutput:
    summary: str
    sentiment: IntelSentiment
    sentiment_score: int
    events: Sequence[IntelAgentStructuredEvent]
    claims: Sequence[ResearchClaim]
    citations: Sequence[ReportCitation]
    warnings: Sequence[str] = ()
    limitations: Sequence[str] = ()
    contract_version: str = INTEL_AGENT_CONTRACT_VERSION
    schema_name: str = INTEL_AGENT_OUTPUT_SCHEMA_NAME
    schema_version: str = INTEL_AGENT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "summary", _required_string("summary", self.summary))
        object.__setattr__(self, "sentiment", IntelSentiment(self.sentiment))
        object.__setattr__(self, "sentiment_score", _int_range("sentiment_score", self.sentiment_score, minimum=0, maximum=100))
        events = tuple(self.events)
        claims = tuple(self.claims)
        citations = tuple(self.citations)
        for event in events:
            if type(event) is not IntelAgentStructuredEvent:
                raise IntelAgentError("events must contain IntelAgentStructuredEvent objects")
        for claim in claims:
            if type(claim) is not ResearchClaim:
                raise IntelAgentError("claims must contain ResearchClaim objects")
        for citation in citations:
            if type(citation) is not ReportCitation:
                raise IntelAgentError("citations must contain ReportCitation objects")
        object.__setattr__(self, "events", events)
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
            "summary": self.summary,
            "sentiment": self.sentiment.value,
            "sentiment_score": self.sentiment_score,
            "events": [event.to_record() for event in self.events],
            "claims": [claim.to_record() for claim in self.claims],
            "citations": [citation.to_record() for citation in self.citations],
            "warnings": list(self.warnings),
            "limitations": list(self.limitations),
        }


@dataclass(frozen=True, slots=True)
class IntelAgentResult:
    prompt_payload: IntelAgentPromptPayload
    output: IntelAgentStructuredOutput
    contract_version: str = INTEL_AGENT_CONTRACT_VERSION
    schema_name: str = "research.agent.intel_result"
    schema_version: str = INTEL_AGENT_SCHEMA_VERSION

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
                "source_quality": _source_quality(self.prompt_payload),
            }
        )
        return {
            "agent_name": "intel",
            "signal": self.output.sentiment.value,
            "sentiment_score": self.output.sentiment_score,
            "reasoning": self.output.summary,
            "news_summary": self.output.summary,
            "raw_data": raw_data,
        }

    def to_dsa_dashboard_fields(self) -> dict[str, Any]:
        source_quality = _source_quality(self.prompt_payload)
        return {
            "news_summary": self.output.summary,
            "news_analysis": self.output.summary,
            "intel_analysis": self.output.summary,
            "sentiment_score": self.output.sentiment_score,
            "sentiment_label": self.output.sentiment.value,
            "key_events": [event.to_record() for event in self.output.events],
            "source_quality": source_quality,
            "warnings": list(self.output.warnings),
            "limitations": list(self.output.limitations),
            "citations": [citation.to_record() for citation in self.output.citations],
        }


class EvidenceScopedIntelAgent:
    """Offline Intel Agent boundary over P5 EvidenceBundle and SourceTrust metadata."""

    def __init__(self, *, max_source_age_days: int = 14) -> None:
        self._max_source_age_days = _positive_int("max_source_age_days", max_source_age_days)

    def prepare_prompt_payload(self, request: IntelAgentPromptRequest) -> IntelAgentPromptPayload:
        if type(request) is not IntelAgentPromptRequest:
            raise IntelAgentError("request must be an IntelAgentPromptRequest")
        allowed_ids: list[str] = []
        source_records: list[Mapping[str, Any]] = []
        excluded: list[Mapping[str, Any]] = []
        seen_source_hashes: set[str] = set()

        for item in request.bundle.items:
            source_record = _source_record_from_evidence(
                item.evidence,
                decision_time=request.bundle.request.decision_time,
                max_source_age_days=self._max_source_age_days,
            )
            dedupe_key = str(source_record.get("cleaned_body_hash") or source_record.get("url_hash"))
            if source_record["malicious_instruction_detected"] is True:
                excluded.append(_excluded(item.evidence, "malicious_instruction"))
                continue
            if dedupe_key in seen_source_hashes:
                excluded.append(_excluded(item.evidence, "duplicate_source_hash"))
                continue
            seen_source_hashes.add(dedupe_key)
            allowed_ids.append(item.evidence.evidence_id)
            source_records.append(source_record)

        return IntelAgentPromptPayload(
            bundle=request.bundle,
            prompt_binding=request.prompt_binding,
            allowed_evidence_ids=tuple(allowed_ids),
            source_trust_records=tuple(source_records),
            excluded_source_evidence=tuple(excluded),
        )

    def finalize_output(
        self,
        prompt_payload: IntelAgentPromptPayload,
        output: IntelAgentStructuredOutput,
    ) -> IntelAgentResult:
        if type(prompt_payload) is not IntelAgentPromptPayload:
            raise IntelAgentError("prompt_payload must be an IntelAgentPromptPayload")
        if type(output) is not IntelAgentStructuredOutput:
            raise IntelAgentError("output must be an IntelAgentStructuredOutput")

        evidence_by_id = {item.evidence.evidence_id: item.evidence for item in prompt_payload.bundle.items}
        allowed_ids = set(prompt_payload.allowed_evidence_ids)
        source_by_evidence_id = {str(record["evidence_id"]): record for record in prompt_payload.source_trust_records}
        citations_by_id = {citation.citation_id: citation for citation in output.citations}
        if len(citations_by_id) != len(tuple(output.citations)):
            raise IntelAgentError("duplicate citation_id in Intel Agent output")

        for citation in output.citations:
            if citation.evidence_id not in allowed_ids:
                raise IntelAgentError(f"citation evidence_id is not included in the Intel prompt payload: {citation.evidence_id}")
            evidence = evidence_by_id[citation.evidence_id]
            if evidence.artifact_hash and citation.artifact_hash != evidence.artifact_hash:
                raise IntelAgentError(f"citation artifact_hash does not match evidence: {citation.citation_id}")
            if evidence.dataset_versions and dict(citation.dataset_versions) != dict(evidence.dataset_versions):
                raise IntelAgentError(f"citation dataset_versions do not match evidence: {citation.citation_id}")
            if evidence.run_id and citation.run_id != evidence.run_id:
                raise IntelAgentError(f"citation run_id does not match evidence: {citation.citation_id}")
            if evidence.stage_id and citation.stage_id != evidence.stage_id:
                raise IntelAgentError(f"citation stage_id does not match evidence: {citation.citation_id}")

        for claim in output.claims:
            for citation_id in claim.citation_ids:
                if citation_id not in citations_by_id:
                    raise IntelAgentError(f"claim references unknown citation_id: {citation_id}")
            if claim.kind is ClaimKind.NUMERIC_METRIC:
                raise IntelAgentError("Intel Agent cannot introduce numeric_metric claims")

        for event in output.events:
            for evidence_id in event.source_evidence_ids:
                if evidence_id not in allowed_ids:
                    raise IntelAgentError(f"event source evidence is not included in the Intel prompt payload: {evidence_id}")
            for citation_id in event.citation_ids:
                if citation_id not in citations_by_id:
                    raise IntelAgentError(f"event references unknown citation_id: {citation_id}")
            if event.strength is IntelEventStrength.STRONG:
                supporting = [source_by_evidence_id[evidence_id] for evidence_id in event.source_evidence_ids]
                if not supporting or not any(source.get("strong_claim_allowed") is True for source in supporting):
                    raise IntelAgentError("strong Intel events require trustworthy source evidence")
                if any(source.get("malicious_instruction_detected") is True for source in supporting):
                    raise IntelAgentError("strong Intel events require trustworthy source evidence")

        return IntelAgentResult(prompt_payload=prompt_payload, output=output)


def _source_record_from_evidence(evidence: EvidenceRecord, *, decision_time: datetime, max_source_age_days: int) -> dict[str, Any]:
    if type(evidence) is not EvidenceRecord:
        raise IntelAgentError("EvidenceBundle items must contain EvidenceRecord objects")
    if evidence.kind is not EvidenceKind.UNSTRUCTURED_SOURCE:
        raise IntelAgentError(f"Intel Agent evidence allowlist rejected evidence kind: {evidence.kind.value}")
    if evidence.evaluation_scope is not EvidenceEvaluationScope.MARKET_INTELLIGENCE:
        raise IntelAgentError(f"Intel Agent evidence scope rejected: {evidence.evaluation_scope.value}")
    if evidence.metadata.get("llm_recompute_allowed") is not False:
        raise IntelAgentError("Intel Agent evidence must disallow LLM recompute")
    source_trust = evidence.metadata.get("source_trust")
    if not isinstance(source_trust, Mapping):
        raise IntelAgentError("Intel Agent evidence requires metadata.source_trust")

    record = dict(source_trust)
    required = (
        "source_id",
        "source_type",
        "published_at",
        "observed_at",
        "available_at",
        "trust",
        "url_hash",
        "cleaned_body_hash",
        "strong_claim_allowed",
        "corroboration_required",
        "issues",
    )
    for key in required:
        if key not in record:
            raise IntelAgentError(f"metadata.source_trust missing required field: {key}")

    published_at = _parse_datetime("published_at", record["published_at"])
    observed_at = _parse_datetime("observed_at", record["observed_at"])
    available_at = _parse_datetime("available_at", record["available_at"])
    event_time = _parse_datetime("event_time", record.get("event_time", record["published_at"]))
    if available_at != evidence.available_at:
        raise IntelAgentError("source_trust available_at must match evidence available_at")
    freshness_status = _freshness_status(published_at, decision_time, max_source_age_days)
    issues = tuple(record.get("issues") or ())
    malicious = _has_issue_severity(issues, "malicious") or bool(record.get("malicious_instruction_detected"))
    strong_claim_allowed = bool(record.get("strong_claim_allowed")) and freshness_status is IntelFreshnessStatus.FRESH and not malicious
    corroboration_required = bool(record.get("corroboration_required")) or freshness_status is IntelFreshnessStatus.STALE or malicious

    record.update(
        {
            "evidence_id": evidence.evidence_id,
            "content_hash": evidence.content_hash,
            "artifact_hash": evidence.artifact_hash,
            "dataset_versions": dict(evidence.dataset_versions),
            "run_id": evidence.run_id,
            "stage_id": evidence.stage_id,
            "published_at": published_at.isoformat(),
            "observed_at": observed_at.isoformat(),
            "available_at": available_at.isoformat(),
            "event_time": event_time.isoformat(),
            "freshness_status": freshness_status.value,
            "malicious_instruction_detected": malicious,
            "strong_claim_allowed": strong_claim_allowed,
            "corroboration_required": corroboration_required,
        }
    )
    return record


def _freshness_status(published_at: datetime, decision_time: datetime, max_source_age_days: int) -> IntelFreshnessStatus:
    if published_at > decision_time:
        return IntelFreshnessStatus.UNKNOWN
    age_days = (decision_time - published_at).total_seconds() / 86_400
    return IntelFreshnessStatus.STALE if age_days > max_source_age_days else IntelFreshnessStatus.FRESH


def _excluded(evidence: EvidenceRecord, reason: str) -> dict[str, Any]:
    return {
        "evidence_id": evidence.evidence_id,
        "reason": reason,
        "content_hash": evidence.content_hash,
        "source_id": evidence.source.source_id,
    }


def _source_quality(prompt_payload: IntelAgentPromptPayload) -> dict[str, Any]:
    counts = {"authoritative": 0, "high": 0, "medium": 0, "low": 0, "untrusted": 0}
    stale_count = 0
    corroboration_required_count = 0
    for record in prompt_payload.source_trust_records:
        trust = str(record.get("trust"))
        if trust in counts:
            counts[trust] += 1
        if record.get("freshness_status") == IntelFreshnessStatus.STALE.value:
            stale_count += 1
        if record.get("corroboration_required") is True:
            corroboration_required_count += 1
    counts.update(
        {
            "included_count": len(prompt_payload.source_trust_records),
            "excluded_count": len(prompt_payload.excluded_source_evidence),
            "stale_count": stale_count,
            "corroboration_required_count": corroboration_required_count,
        }
    )
    return counts


def _has_issue_severity(issues: Sequence[Mapping[str, Any]], severity: str) -> bool:
    return any(isinstance(issue, Mapping) and issue.get("severity") == severity for issue in issues)


def _required_string(field_name: str, value: str) -> str:
    if type(value) is not str or not value.strip():
        raise IntelAgentError(f"{field_name} is required")
    return value


def _aware_datetime(field_name: str, value: datetime) -> datetime:
    if type(value) is not datetime or value.tzinfo is None or value.utcoffset() is None:
        raise IntelAgentError(f"{field_name} must be timezone-aware")
    return value


def _parse_datetime(field_name: str, value: Any) -> datetime:
    if type(value) is datetime:
        return _aware_datetime(field_name, value)
    if type(value) is not str or not value.strip():
        raise IntelAgentError(f"{field_name} must be a timezone-aware ISO datetime")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise IntelAgentError(f"{field_name} must be a timezone-aware ISO datetime") from exc
    return _aware_datetime(field_name, parsed)


def _positive_int(field_name: str, value: int) -> int:
    if type(value) is not int or isinstance(value, bool) or value <= 0:
        raise IntelAgentError(f"{field_name} must be a positive integer")
    return value


def _int_range(field_name: str, value: int, *, minimum: int, maximum: int) -> int:
    if type(value) is not int or isinstance(value, bool):
        raise IntelAgentError(f"{field_name} must be an integer")
    if value < minimum or value > maximum:
        raise IntelAgentError(f"{field_name} must be between {minimum} and {maximum}")
    return value


def _string_tuple(field_name: str, value: Sequence[str]) -> tuple[str, ...]:
    if isinstance(value, str) or not isinstance(value, Sequence):
        raise IntelAgentError(f"{field_name} must be a sequence")
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
    if isinstance(value, datetime):
        return value.isoformat()
    return value
