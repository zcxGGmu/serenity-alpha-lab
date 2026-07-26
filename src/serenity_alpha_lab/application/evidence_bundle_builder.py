from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any

from serenity_alpha_lab.evidence.schema import (
    EvidenceEvaluationScope,
    EvidenceKind,
    EvidenceRecord,
    EvidenceTrustLevel,
)
from serenity_alpha_lab.repositories.evidence_store import LocalEvidenceStore, PersistedEvidence


EVIDENCE_BUNDLE_CONTRACT_VERSION = "research.evidence_bundle@1.0.0"
EVIDENCE_BUNDLE_SCHEMA_NAME = "research.evidence_bundle"
EVIDENCE_BUNDLE_SCHEMA_VERSION = "1.0.0"

EVIDENCE_BUNDLE_SCHEMA_INSTRUCTIONS = (
    "EvidenceBundle instructions: use only included evidence_records; preserve evidence_id, "
    "content_hash, artifact_hash, dataset_versions, run_id and stage_id in every citation; "
    "numeric claims must cite deterministic evidence and formula versions; never recompute "
    "returns, risk, drawdown, costs, orders, ledger state or gate outcomes; if bundle status "
    "is trimmed, empty or budget_exhausted, report the limitation instead of inventing facts."
)


class EvidenceBundleError(ValueError):
    """Raised when an EvidenceBundle request cannot be built safely."""


class EvidenceBundleRole(StrEnum):
    TECHNICAL = "technical"
    INTEL = "intel"
    RISK_PORTFOLIO = "risk_portfolio"
    DECISION = "decision"


class EvidenceBundleStatus(StrEnum):
    COMPLETE = "complete"
    TRIMMED = "trimmed"
    EMPTY = "empty"
    BUDGET_EXHAUSTED = "budget_exhausted"


@dataclass(frozen=True, slots=True)
class EvidenceBundleBudget:
    max_prompt_tokens: int
    reserved_schema_tokens: int = 0
    max_evidence_items: int = 20

    def __post_init__(self) -> None:
        _positive_int("max_prompt_tokens", self.max_prompt_tokens)
        if type(self.reserved_schema_tokens) is not int or self.reserved_schema_tokens < 0:
            raise EvidenceBundleError("reserved_schema_tokens must be a non-negative integer")
        _positive_int("max_evidence_items", self.max_evidence_items)

    def to_record(self) -> dict[str, int]:
        return {
            "max_prompt_tokens": self.max_prompt_tokens,
            "reserved_schema_tokens": self.reserved_schema_tokens,
            "max_evidence_items": self.max_evidence_items,
        }


@dataclass(frozen=True, slots=True)
class EvidenceBundleRequest:
    tenant_id: str
    decision_time: datetime
    role: EvidenceBundleRole
    budget: EvidenceBundleBudget
    team_id: str | None = None
    owner_user_id: str | None = None
    instrument_id: str | None = None
    kinds: tuple[EvidenceKind, ...] = ()
    evaluation_scopes: tuple[EvidenceEvaluationScope, ...] = ()

    def __post_init__(self) -> None:
        _required_string("tenant_id", self.tenant_id)
        _optional_string("team_id", self.team_id)
        _optional_string("owner_user_id", self.owner_user_id)
        _optional_string("instrument_id", self.instrument_id)
        _aware_datetime("decision_time", self.decision_time)
        object.__setattr__(self, "role", EvidenceBundleRole(self.role))
        if type(self.budget) is not EvidenceBundleBudget:
            raise EvidenceBundleError("budget must be an EvidenceBundleBudget")
        object.__setattr__(self, "kinds", _normalize_kinds(self.kinds))
        object.__setattr__(self, "evaluation_scopes", _normalize_scopes(self.evaluation_scopes))

    def to_record(self) -> dict[str, Any]:
        return {
            "tenant_id": self.tenant_id,
            "team_id": self.team_id,
            "owner_user_id": self.owner_user_id,
            "instrument_id": self.instrument_id,
            "decision_time": self.decision_time.isoformat(),
            "role": self.role.value,
            "budget": self.budget.to_record(),
            "kinds": [kind.value for kind in self.kinds],
            "evaluation_scopes": [scope.value for scope in self.evaluation_scopes],
        }


@dataclass(frozen=True, slots=True)
class EvidenceBundleItem:
    evidence: EvidenceRecord
    priority_score: int
    priority_reasons: tuple[str, ...]
    estimated_tokens: int

    def to_record(self) -> dict[str, Any]:
        return {
            "evidence": self.evidence.to_record(),
            "priority_score": self.priority_score,
            "priority_reasons": list(self.priority_reasons),
            "estimated_tokens": self.estimated_tokens,
        }


@dataclass(frozen=True, slots=True)
class EvidenceBundleExcludedItem:
    evidence_id: str
    reason: str
    priority_score: int = 0
    estimated_tokens: int = 0

    def to_record(self) -> dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "reason": self.reason,
            "priority_score": self.priority_score,
            "estimated_tokens": self.estimated_tokens,
        }


@dataclass(frozen=True, slots=True)
class EvidenceBundle:
    bundle_id: str
    request: EvidenceBundleRequest
    schema_instructions: str
    status: EvidenceBundleStatus
    items: tuple[EvidenceBundleItem, ...]
    excluded_items: tuple[EvidenceBundleExcludedItem, ...]
    estimated_tokens: int
    schema_instruction_tokens: int
    contract_version: str = EVIDENCE_BUNDLE_CONTRACT_VERSION
    schema_name: str = EVIDENCE_BUNDLE_SCHEMA_NAME
    schema_version: str = EVIDENCE_BUNDLE_SCHEMA_VERSION

    def to_record(self) -> dict[str, Any]:
        return {
            "bundle_id": self.bundle_id,
            "contract_version": self.contract_version,
            "schema_name": self.schema_name,
            "schema_version": self.schema_version,
            "status": self.status.value,
            "request": self.request.to_record(),
            "schema_instruction_tokens": self.schema_instruction_tokens,
            "estimated_tokens": self.estimated_tokens,
            "items": [item.to_record() for item in self.items],
            "excluded_items": [item.to_record() for item in self.excluded_items],
        }

    def to_prompt_payload(self) -> dict[str, Any]:
        return {
            "bundle_id": self.bundle_id,
            "schema_name": self.schema_name,
            "schema_version": self.schema_version,
            "status": self.status.value,
            "role": self.request.role.value,
            "instrument_id": self.request.instrument_id,
            "decision_time": self.request.decision_time.isoformat(),
            "schema_instructions": self.schema_instructions,
            "estimated_tokens": self.estimated_tokens,
            "evidence_records": [item.evidence.to_record() for item in self.items],
            "excluded_evidence": [item.to_record() for item in self.excluded_items],
        }


class EvidenceBundleBuilder:
    """Build deterministic evidence context bundles from local Evidence Store metadata."""

    def __init__(self, evidence_store: LocalEvidenceStore) -> None:
        if not hasattr(evidence_store, "find_evidence"):
            raise EvidenceBundleError("evidence_store must provide find_evidence")
        self._evidence_store = evidence_store

    def build(self, request: EvidenceBundleRequest) -> EvidenceBundle:
        if type(request) is not EvidenceBundleRequest:
            raise EvidenceBundleError("request must be an EvidenceBundleRequest")

        schema_tokens = max(
            estimate_text_tokens(EVIDENCE_BUNDLE_SCHEMA_INSTRUCTIONS),
            request.budget.reserved_schema_tokens,
        )
        if schema_tokens > request.budget.max_prompt_tokens:
            raise EvidenceBundleError("token budget cannot fit required schema instructions")

        persisted_records = self._evidence_store.find_evidence(
            tenant_id=request.tenant_id,
            team_id=request.team_id,
            owner_user_id=request.owner_user_id,
        )
        candidates: list[_Candidate] = []
        excluded: list[EvidenceBundleExcludedItem] = []
        requested_kinds = set(request.kinds)
        requested_scopes = set(request.evaluation_scopes)

        for persisted in persisted_records:
            evidence = persisted.evidence
            item = _candidate_from(persisted, request=request)
            if requested_kinds and evidence.kind not in requested_kinds:
                excluded.append(item.exclude("kind_filtered"))
                continue
            if requested_scopes and evidence.evaluation_scope not in requested_scopes:
                excluded.append(item.exclude("evaluation_scope_filtered"))
                continue
            if evidence.available_at > request.decision_time:
                excluded.append(item.exclude("future_available_at"))
                continue
            if (
                request.instrument_id is not None
                and evidence.instrument_id is not None
                and evidence.instrument_id != request.instrument_id
            ):
                excluded.append(item.exclude("instrument_mismatch"))
                continue
            candidates.append(item)

        ranked = sorted(candidates, key=_candidate_sort_key)
        ranked, duplicate_exclusions = _dedupe_candidates(ranked)
        excluded.extend(duplicate_exclusions)

        items: list[EvidenceBundleItem] = []
        token_count = schema_tokens
        budget_trimmed = False
        for candidate in ranked:
            if len(items) >= request.budget.max_evidence_items:
                excluded.append(candidate.exclude("budget_trimmed"))
                budget_trimmed = True
                continue
            if token_count + candidate.estimated_tokens > request.budget.max_prompt_tokens:
                excluded.append(candidate.exclude("budget_trimmed"))
                budget_trimmed = True
                continue
            items.append(candidate.to_item())
            token_count += candidate.estimated_tokens

        if budget_trimmed and not items:
            status = EvidenceBundleStatus.BUDGET_EXHAUSTED
        elif budget_trimmed:
            status = EvidenceBundleStatus.TRIMMED
        elif not items:
            status = EvidenceBundleStatus.EMPTY
        else:
            status = EvidenceBundleStatus.COMPLETE

        bundle = EvidenceBundle(
            bundle_id=_bundle_id(request, items, excluded, token_count, schema_tokens, status),
            request=request,
            schema_instructions=EVIDENCE_BUNDLE_SCHEMA_INSTRUCTIONS,
            status=status,
            items=tuple(items),
            excluded_items=tuple(sorted(excluded, key=lambda item: (item.reason, item.evidence_id))),
            estimated_tokens=token_count,
            schema_instruction_tokens=schema_tokens,
        )
        return bundle


@dataclass(frozen=True, slots=True)
class _Candidate:
    persisted: PersistedEvidence
    priority_score: int
    priority_reasons: tuple[str, ...]
    estimated_tokens: int

    @property
    def evidence(self) -> EvidenceRecord:
        return self.persisted.evidence

    def to_item(self) -> EvidenceBundleItem:
        return EvidenceBundleItem(
            evidence=self.evidence,
            priority_score=self.priority_score,
            priority_reasons=self.priority_reasons,
            estimated_tokens=self.estimated_tokens,
        )

    def exclude(self, reason: str) -> EvidenceBundleExcludedItem:
        return EvidenceBundleExcludedItem(
            evidence_id=self.evidence.evidence_id,
            reason=reason,
            priority_score=self.priority_score,
            estimated_tokens=self.estimated_tokens,
        )


def estimate_text_tokens(value: str) -> int:
    if type(value) is not str:
        raise EvidenceBundleError("text must be a string")
    return max(1, math.ceil(len(value.encode("utf-8")) / 4))


def _candidate_from(persisted: PersistedEvidence, *, request: EvidenceBundleRequest) -> _Candidate:
    evidence = persisted.evidence
    priority_score, reasons = _priority(evidence, request=request)
    payload = json.dumps(evidence.to_record(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return _Candidate(
        persisted=persisted,
        priority_score=priority_score,
        priority_reasons=reasons,
        estimated_tokens=estimate_text_tokens(payload),
    )


def _priority(evidence: EvidenceRecord, *, request: EvidenceBundleRequest) -> tuple[int, tuple[str, ...]]:
    reasons: list[str] = []
    role_weight = _ROLE_KIND_WEIGHTS[request.role].get(evidence.kind, 100)
    trust_weight = _TRUST_WEIGHTS[evidence.trust]
    scope_weight = 80 if evidence.evaluation_scope is EvidenceEvaluationScope.FORMAL_PORTFOLIO_BACKTEST else 0
    if request.instrument_id is not None and evidence.instrument_id == request.instrument_id:
        instrument_weight = 50
        reasons.append("instrument_match")
    elif evidence.instrument_id is None:
        instrument_weight = 10
        reasons.append("global_evidence")
    else:
        instrument_weight = 0
    recency_weight = _recency_weight(evidence.available_at, request.decision_time)

    reasons.append(f"role:{request.role.value}:{evidence.kind.value}")
    reasons.append(f"trust:{evidence.trust.value}")
    reasons.append(f"scope:{evidence.evaluation_scope.value}")
    score = role_weight + trust_weight + scope_weight + instrument_weight + recency_weight
    return score, tuple(reasons)


def _recency_weight(available_at: datetime, decision_time: datetime) -> int:
    if available_at > decision_time:
        return 0
    age_seconds = max(0, int((decision_time - available_at).total_seconds()))
    age_days = age_seconds // 86_400
    return max(0, 30 - min(age_days, 30))


def _candidate_sort_key(candidate: _Candidate) -> tuple[int, str]:
    return (-candidate.priority_score, candidate.evidence.evidence_id)


def _dedupe_candidates(candidates: list[_Candidate]) -> tuple[list[_Candidate], list[EvidenceBundleExcludedItem]]:
    seen_hashes: set[str] = set()
    kept: list[_Candidate] = []
    excluded: list[EvidenceBundleExcludedItem] = []
    for candidate in candidates:
        content_hash = candidate.evidence.content_hash
        if content_hash in seen_hashes:
            excluded.append(candidate.exclude("duplicate_content_hash"))
            continue
        seen_hashes.add(content_hash)
        kept.append(candidate)
    return kept, excluded


_ROLE_KIND_WEIGHTS: dict[EvidenceBundleRole, dict[EvidenceKind, int]] = {
    EvidenceBundleRole.TECHNICAL: {
        EvidenceKind.BACKTEST_PERFORMANCE_METRICS: 1_000,
        EvidenceKind.FACTOR_EVALUATION: 950,
        EvidenceKind.SCREEN_SNAPSHOT: 900,
        EvidenceKind.RISK_POLICY_RESULT: 850,
        EvidenceKind.BACKTEST_BIAS_AUDIT: 800,
        EvidenceKind.BACKTEST_RUN_SUMMARY: 760,
        EvidenceKind.BACKTEST_ARTIFACT_BUNDLE: 740,
        EvidenceKind.FORMAL_BACKTEST_API_RECORD: 720,
    },
    EvidenceBundleRole.INTEL: {
        EvidenceKind.QUANT_LAB_LINEAGE: 800,
        EvidenceKind.FORMAL_BACKTEST_API_RECORD: 760,
        EvidenceKind.SCREEN_SNAPSHOT: 700,
        EvidenceKind.SCREEN_PIPELINE_SNAPSHOT: 680,
    },
    EvidenceBundleRole.RISK_PORTFOLIO: {
        EvidenceKind.RISK_POLICY_RESULT: 1_000,
        EvidenceKind.BACKTEST_BIAS_AUDIT: 960,
        EvidenceKind.BACKTEST_PERFORMANCE_METRICS: 900,
        EvidenceKind.BACKTEST_RUN_SUMMARY: 860,
        EvidenceKind.BACKTEST_ARTIFACT_BUNDLE: 830,
        EvidenceKind.FORMAL_BACKTEST_API_RECORD: 780,
    },
    EvidenceBundleRole.DECISION: {
        EvidenceKind.RISK_POLICY_RESULT: 1_000,
        EvidenceKind.BACKTEST_PERFORMANCE_METRICS: 980,
        EvidenceKind.BACKTEST_BIAS_AUDIT: 960,
        EvidenceKind.BACKTEST_RUN_SUMMARY: 930,
        EvidenceKind.FORMAL_BACKTEST_API_RECORD: 900,
        EvidenceKind.SCREEN_SNAPSHOT: 860,
        EvidenceKind.FACTOR_EVALUATION: 840,
    },
}

_TRUST_WEIGHTS: dict[EvidenceTrustLevel, int] = {
    EvidenceTrustLevel.AUTHORITATIVE: 500,
    EvidenceTrustLevel.HIGH: 400,
    EvidenceTrustLevel.MEDIUM: 250,
    EvidenceTrustLevel.LOW: 100,
    EvidenceTrustLevel.UNTRUSTED: 0,
}


def _bundle_id(
    request: EvidenceBundleRequest,
    items: list[EvidenceBundleItem],
    excluded: list[EvidenceBundleExcludedItem],
    estimated_tokens: int,
    schema_tokens: int,
    status: EvidenceBundleStatus,
) -> str:
    payload = {
        "request": request.to_record(),
        "item_ids": [item.evidence.evidence_id for item in items],
        "item_hashes": [item.evidence.content_hash for item in items],
        "excluded": [item.to_record() for item in sorted(excluded, key=lambda value: (value.reason, value.evidence_id))],
        "estimated_tokens": estimated_tokens,
        "schema_instruction_tokens": schema_tokens,
        "status": status.value,
    }
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    return f"evb_{digest[:32]}"


def _normalize_kinds(values: tuple[EvidenceKind, ...]) -> tuple[EvidenceKind, ...]:
    if values is None:
        return ()
    if isinstance(values, str):
        raise EvidenceBundleError("kinds must be an iterable of EvidenceKind values")
    return tuple(sorted((EvidenceKind(value) for value in values), key=lambda item: item.value))


def _normalize_scopes(values: tuple[EvidenceEvaluationScope, ...]) -> tuple[EvidenceEvaluationScope, ...]:
    if values is None:
        return ()
    if isinstance(values, str):
        raise EvidenceBundleError("evaluation_scopes must be an iterable of EvidenceEvaluationScope values")
    return tuple(sorted((EvidenceEvaluationScope(value) for value in values), key=lambda item: item.value))


def _positive_int(field_name: str, value: int) -> None:
    if type(value) is not int or value <= 0:
        raise EvidenceBundleError(f"{field_name} must be a positive integer")


def _required_string(field_name: str, value: str) -> str:
    if type(value) is not str or not value.strip():
        raise EvidenceBundleError(f"{field_name} is required")
    return value


def _optional_string(field_name: str, value: str | None) -> str | None:
    if value is None:
        return None
    return _required_string(field_name, value)


def _aware_datetime(field_name: str, value: datetime) -> datetime:
    if type(value) is not datetime or value.tzinfo is None or value.utcoffset() is None:
        raise EvidenceBundleError(f"{field_name} must be timezone-aware")
    return value
