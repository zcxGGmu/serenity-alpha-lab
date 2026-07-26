from __future__ import annotations

import re
from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


EVIDENCE_CONTRACT_VERSION = "research.evidence@1.0.0"
EVIDENCE_SCHEMA_NAME = "research.evidence"
EVIDENCE_SCHEMA_VERSION = "1.0.0"

REPORT_CITATION_SCHEMA_NAME = "research.report_citation"
REPORT_CITATION_SCHEMA_VERSION = "1.0.0"

RESEARCH_CLAIM_CONTRACT_VERSION = "research.claim@1.0.0"
RESEARCH_CLAIM_SCHEMA_NAME = "research.claim"
RESEARCH_CLAIM_SCHEMA_VERSION = "1.0.0"

RESEARCH_REPORT_CONTRACT_VERSION = "research.report@1.0.0"
RESEARCH_REPORT_SCHEMA_NAME = "research.report"
RESEARCH_REPORT_SCHEMA_VERSION = "1.0.0"

_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_DATASET_VERSION_RE = re.compile(r"^dsv_[0-9a-f]{32,64}$")


class EvidenceSchemaError(ValueError):
    """Raised when the P5 evidence schema contract is violated."""


class EvidenceKind(StrEnum):
    HISTORICAL_UNIVERSE = "historical_universe"
    FACTOR_CACHE_MANIFEST = "factor_cache_manifest"
    FACTOR_EVALUATION = "factor_evaluation"
    SCREEN_PIPELINE_SNAPSHOT = "screen_pipeline_snapshot"
    SCREEN_SNAPSHOT = "screen_snapshot"
    QUANT_SCREENING_API_RECORD = "quant_screening_api_record"
    BACKTEST_RUN_SUMMARY = "backtest_run_summary"
    BACKTEST_ARTIFACT_BUNDLE = "backtest_artifact_bundle"
    RISK_POLICY_RESULT = "risk_policy_result"
    BACKTEST_BIAS_AUDIT = "backtest_bias_audit"
    BACKTEST_PERFORMANCE_METRICS = "backtest_performance_metrics"
    FORMAL_BACKTEST_API_RECORD = "formal_backtest_api_record"
    QUANT_LAB_LINEAGE = "quant_lab_lineage"


class EvidenceEvaluationScope(StrEnum):
    DATASET_LINEAGE = "dataset_lineage"
    SCREENING = "screening"
    FACTOR_EVALUATION = "factor_evaluation"
    FORMAL_PORTFOLIO_BACKTEST = "formal_portfolio_backtest"
    API_LINEAGE = "api_lineage"
    UI_LINEAGE = "ui_lineage"


class EvidenceTrustLevel(StrEnum):
    AUTHORITATIVE = "authoritative"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNTRUSTED = "untrusted"


class ClaimKind(StrEnum):
    NUMERIC_METRIC = "numeric_metric"
    TEMPORAL_FACT = "temporal_fact"
    RISK_GATE = "risk_gate"
    LINEAGE_FACT = "lineage_fact"
    QUALITATIVE_ASSESSMENT = "qualitative_assessment"


class ClaimVerificationStatus(StrEnum):
    VERIFIED = "verified"
    PARTIAL = "partial"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    CITATION_MISSING = "citation_missing"
    VALUE_MISMATCH = "value_mismatch"
    REJECTED = "rejected"
    BLOCKED = "blocked"


class ClaimComputationPolicy(StrEnum):
    DETERMINISTIC_EVIDENCE = "deterministic_evidence"
    CITATION_SUMMARY = "citation_summary"
    LLM_NARRATIVE = "llm_narrative"


class ResearchReportLevel(StrEnum):
    VERIFIED = "verified"
    PARTIAL = "partial"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    BLOCKED = "blocked"


class SchemaModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    def to_record(self) -> dict[str, Any]:
        return _json_ready(self.model_dump(mode="python", exclude_none=True))


class EvidenceSource(SchemaModel):
    source_id: str
    source_type: str = Field(description="Source class such as artifact, api_record, ui_lineage or dataset_manifest.")
    schema_name: str
    schema_version: str
    contract_version: str | None = None
    source_uri: str | None = None
    producer: str | None = None

    @field_validator("source_id", "source_type", "schema_name", "schema_version")
    @classmethod
    def _required_source_string(cls, value: str) -> str:
        return _required_string("source field", value)

    @field_validator("contract_version", "source_uri", "producer")
    @classmethod
    def _optional_source_string(cls, value: str | None) -> str | None:
        return _optional_string(value)

    def to_record(self) -> dict[str, Any]:
        record = super().to_record()
        record["source"] = record.pop("source_type")
        return record


class EvidenceRecord(SchemaModel):
    evidence_id: str
    kind: EvidenceKind
    evaluation_scope: EvidenceEvaluationScope
    title: str
    summary: str
    source: EvidenceSource
    available_at: datetime
    content_hash: str
    trust: EvidenceTrustLevel
    dataset_versions: dict[str, str]
    instrument_id: str | None = None
    as_of: str | None = None
    run_id: str | None = None
    stage_id: str | None = None
    trace_id: str | None = None
    artifact_id: str | None = None
    artifact_hash: str | None = None
    formula_versions: dict[str, str] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    contract_version: str = EVIDENCE_CONTRACT_VERSION
    schema_name: str = EVIDENCE_SCHEMA_NAME
    schema_version: str = EVIDENCE_SCHEMA_VERSION

    @field_validator("evidence_id", "title", "summary", "contract_version", "schema_name", "schema_version")
    @classmethod
    def _required_evidence_string(cls, value: str) -> str:
        return _required_string("evidence field", value)

    @field_validator("instrument_id", "as_of", "run_id", "stage_id", "trace_id", "artifact_id")
    @classmethod
    def _optional_evidence_string(cls, value: str | None) -> str | None:
        return _optional_string(value)

    @field_validator("available_at")
    @classmethod
    def _available_at_is_aware(cls, value: datetime) -> datetime:
        return _aware_datetime("available_at", value)

    @field_validator("content_hash")
    @classmethod
    def _content_hash_is_sha256(cls, value: str) -> str:
        return _sha256("content_hash", value)

    @field_validator("artifact_hash")
    @classmethod
    def _artifact_hash_is_sha256(cls, value: str | None) -> str | None:
        return _optional_sha256("artifact_hash", value)

    @field_validator("dataset_versions")
    @classmethod
    def _dataset_versions_are_concrete(cls, value: dict[str, str]) -> dict[str, str]:
        return _dataset_versions(value)

    @field_validator("formula_versions")
    @classmethod
    def _formula_versions_are_strings(cls, value: dict[str, str]) -> dict[str, str]:
        return _string_mapping("formula_versions", value)

    @model_validator(mode="after")
    def _validate_scope_and_artifact(self) -> EvidenceRecord:
        if self.evaluation_scope is EvidenceEvaluationScope.FORMAL_PORTFOLIO_BACKTEST:
            if self.kind not in _FORMAL_PORTFOLIO_BACKTEST_KINDS:
                raise ValueError(
                    f"{self.kind.value} cannot be labeled as formal portfolio backtest evidence"
                )
        if self.artifact_id is not None and self.artifact_hash is None:
            raise ValueError("artifact_hash is required when artifact_id is present")
        return self

    def to_record(self) -> dict[str, Any]:
        record = super().to_record()
        record["source"] = self.source.to_record()
        return record


class ReportCitation(SchemaModel):
    citation_id: str
    evidence_id: str
    evidence_field_path: str
    cited_value: Any | None = None
    unit: str | None = None
    formula_version: str | None = None
    dataset_versions: dict[str, str] = Field(default_factory=dict)
    run_id: str | None = None
    stage_id: str | None = None
    artifact_hash: str | None = None
    schema_name: str = REPORT_CITATION_SCHEMA_NAME
    schema_version: str = REPORT_CITATION_SCHEMA_VERSION

    @field_validator("citation_id", "evidence_id", "evidence_field_path", "schema_name", "schema_version")
    @classmethod
    def _required_citation_string(cls, value: str) -> str:
        return _required_string("citation field", value)

    @field_validator("unit", "formula_version", "run_id", "stage_id")
    @classmethod
    def _optional_citation_string(cls, value: str | None) -> str | None:
        return _optional_string(value)

    @field_validator("dataset_versions")
    @classmethod
    def _citation_dataset_versions_are_concrete(cls, value: dict[str, str]) -> dict[str, str]:
        if not value:
            return {}
        return _dataset_versions(value)

    @field_validator("artifact_hash")
    @classmethod
    def _citation_artifact_hash_is_sha256(cls, value: str | None) -> str | None:
        return _optional_sha256("artifact_hash", value)


class ResearchClaim(SchemaModel):
    claim_id: str
    kind: ClaimKind
    statement: str
    verification_status: ClaimVerificationStatus
    citation_ids: list[str]
    computation_policy: ClaimComputationPolicy = ClaimComputationPolicy.CITATION_SUMMARY
    value: Any | None = None
    unit: str | None = None
    formula_version: str | None = None
    dataset_versions: dict[str, str] = Field(default_factory=dict)
    run_id: str | None = None
    stage_id: str | None = None
    artifact_hash: str | None = None
    warnings: list[str] = Field(default_factory=list)
    contract_version: str = RESEARCH_CLAIM_CONTRACT_VERSION
    schema_name: str = RESEARCH_CLAIM_SCHEMA_NAME
    schema_version: str = RESEARCH_CLAIM_SCHEMA_VERSION

    @field_validator("claim_id", "statement", "contract_version", "schema_name", "schema_version")
    @classmethod
    def _required_claim_string(cls, value: str) -> str:
        return _required_string("claim field", value)

    @field_validator("unit", "formula_version", "run_id", "stage_id")
    @classmethod
    def _optional_claim_string(cls, value: str | None) -> str | None:
        return _optional_string(value)

    @field_validator("citation_ids", "warnings")
    @classmethod
    def _claim_string_list(cls, value: list[str]) -> list[str]:
        return _string_list("claim string list", value)

    @field_validator("dataset_versions")
    @classmethod
    def _claim_dataset_versions_are_concrete(cls, value: dict[str, str]) -> dict[str, str]:
        if not value:
            return {}
        return _dataset_versions(value)

    @field_validator("artifact_hash")
    @classmethod
    def _claim_artifact_hash_is_sha256(cls, value: str | None) -> str | None:
        return _optional_sha256("artifact_hash", value)

    @model_validator(mode="after")
    def _validate_claim_rules(self) -> ResearchClaim:
        if self.verification_status is ClaimVerificationStatus.VERIFIED and not self.citation_ids:
            raise ValueError("verified claims require citation_ids")
        if self.kind is ClaimKind.NUMERIC_METRIC:
            if not self.citation_ids:
                raise ValueError("numeric_metric claims require citation_ids")
            if self.unit is None:
                raise ValueError("numeric_metric claims require unit")
            if self.formula_version is None:
                raise ValueError("numeric_metric claims require formula_version")
            if self.computation_policy is ClaimComputationPolicy.LLM_NARRATIVE:
                raise ValueError("LLM cannot compute numeric_metric claims")
        return self


class ResearchReport(SchemaModel):
    report_id: str
    report_level: ResearchReportLevel
    decision_time: datetime
    evidence: list[EvidenceRecord]
    citations: list[ReportCitation]
    claims: list[ResearchClaim]
    dataset_versions: dict[str, str]
    trace_id: str | None = None
    run_id: str | None = None
    generated_at: datetime | None = None
    warnings: list[str] = Field(default_factory=list)
    contract_version: str = RESEARCH_REPORT_CONTRACT_VERSION
    schema_name: str = RESEARCH_REPORT_SCHEMA_NAME
    schema_version: str = RESEARCH_REPORT_SCHEMA_VERSION

    @field_validator("report_id", "contract_version", "schema_name", "schema_version")
    @classmethod
    def _required_report_string(cls, value: str) -> str:
        return _required_string("report field", value)

    @field_validator("trace_id", "run_id")
    @classmethod
    def _optional_report_string(cls, value: str | None) -> str | None:
        return _optional_string(value)

    @field_validator("decision_time")
    @classmethod
    def _decision_time_is_aware(cls, value: datetime) -> datetime:
        return _aware_datetime("decision_time", value)

    @field_validator("generated_at")
    @classmethod
    def _generated_at_is_aware(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        return _aware_datetime("generated_at", value)

    @field_validator("dataset_versions")
    @classmethod
    def _report_dataset_versions_are_concrete(cls, value: dict[str, str]) -> dict[str, str]:
        return _dataset_versions(value)

    @field_validator("warnings")
    @classmethod
    def _report_warning_list(cls, value: list[str]) -> list[str]:
        return _string_list("warning", value)

    @model_validator(mode="after")
    def _validate_report_graph(self) -> ResearchReport:
        evidence_by_id = _unique_by("evidence", self.evidence, lambda item: item.evidence_id)
        citation_by_id = _unique_by("citation", self.citations, lambda item: item.citation_id)
        _unique_by("claim", self.claims, lambda item: item.claim_id)

        for evidence in self.evidence:
            if evidence.available_at > self.decision_time:
                raise ValueError("evidence available_at cannot be later than report decision_time")

        for citation in self.citations:
            if citation.evidence_id not in evidence_by_id:
                raise ValueError(f"citation references unknown evidence_id: {citation.evidence_id}")

        for claim in self.claims:
            for citation_id in claim.citation_ids:
                if citation_id not in citation_by_id:
                    raise ValueError(f"claim references unknown citation_id: {citation_id}")

        if self.report_level is ResearchReportLevel.VERIFIED:
            if not self.claims:
                raise ValueError("verified reports require at least one claim")
            non_verified = [
                claim.claim_id
                for claim in self.claims
                if claim.verification_status is not ClaimVerificationStatus.VERIFIED
            ]
            if non_verified:
                raise ValueError(f"verified reports cannot include non-verified claims: {', '.join(non_verified)}")
        return self


def evidence_json_schemas() -> dict[str, dict[str, Any]]:
    return {
        EVIDENCE_SCHEMA_NAME: EvidenceRecord.model_json_schema(),
        REPORT_CITATION_SCHEMA_NAME: ReportCitation.model_json_schema(),
        RESEARCH_CLAIM_SCHEMA_NAME: ResearchClaim.model_json_schema(),
        RESEARCH_REPORT_SCHEMA_NAME: ResearchReport.model_json_schema(),
    }


def quant_evidence_source_matrix() -> list[dict[str, Any]]:
    rows = [
        (
            EvidenceKind.HISTORICAL_UNIVERSE,
            EvidenceEvaluationScope.DATASET_LINEAGE,
            "quant.historical_universe_snapshot",
            "SAL-P3-011",
            False,
        ),
        (
            EvidenceKind.FACTOR_CACHE_MANIFEST,
            EvidenceEvaluationScope.DATASET_LINEAGE,
            "quant.factor_cache_manifest",
            "SAL-P3-010",
            False,
        ),
        (
            EvidenceKind.FACTOR_EVALUATION,
            EvidenceEvaluationScope.FACTOR_EVALUATION,
            "quant.factor_evaluation",
            "SAL-P3-009",
            False,
        ),
        (
            EvidenceKind.SCREEN_PIPELINE_SNAPSHOT,
            EvidenceEvaluationScope.SCREENING,
            "quant.screen_pipeline_snapshot",
            "SAL-P3-012",
            False,
        ),
        (
            EvidenceKind.SCREEN_SNAPSHOT,
            EvidenceEvaluationScope.SCREENING,
            "quant.screen_snapshot",
            "SAL-P3-013",
            False,
        ),
        (
            EvidenceKind.QUANT_SCREENING_API_RECORD,
            EvidenceEvaluationScope.API_LINEAGE,
            "application.quant_screening_api",
            "SAL-P3-014",
            False,
        ),
        (
            EvidenceKind.BACKTEST_RUN_SUMMARY,
            EvidenceEvaluationScope.FORMAL_PORTFOLIO_BACKTEST,
            "quant.backtest_run",
            "SAL-P4-017",
            True,
        ),
        (
            EvidenceKind.BACKTEST_ARTIFACT_BUNDLE,
            EvidenceEvaluationScope.FORMAL_PORTFOLIO_BACKTEST,
            "quant.backtest_artifact_bundle",
            "SAL-P4-004",
            True,
        ),
        (
            EvidenceKind.RISK_POLICY_RESULT,
            EvidenceEvaluationScope.FORMAL_PORTFOLIO_BACKTEST,
            "quant.backtest.risk_policy",
            "SAL-P4-014",
            True,
        ),
        (
            EvidenceKind.BACKTEST_BIAS_AUDIT,
            EvidenceEvaluationScope.FORMAL_PORTFOLIO_BACKTEST,
            "quant.backtest.bias_audit",
            "SAL-P4-015",
            True,
        ),
        (
            EvidenceKind.BACKTEST_PERFORMANCE_METRICS,
            EvidenceEvaluationScope.FORMAL_PORTFOLIO_BACKTEST,
            "quant.backtest.performance_metrics",
            "SAL-P4-016",
            True,
        ),
        (
            EvidenceKind.FORMAL_BACKTEST_API_RECORD,
            EvidenceEvaluationScope.FORMAL_PORTFOLIO_BACKTEST,
            "application.formal_backtest_api",
            "SAL-P4-020",
            True,
        ),
        (
            EvidenceKind.QUANT_LAB_LINEAGE,
            EvidenceEvaluationScope.UI_LINEAGE,
            "dsa.quant_lab",
            "SAL-P4-021",
            False,
        ),
    ]
    return [
        {
            "kind": kind.value,
            "evaluation_scope": scope.value,
            "source_schema": source_schema,
            "approved_from": approved_from,
            "formal_portfolio_backtest_output": formal_output,
        }
        for kind, scope, source_schema, approved_from, formal_output in rows
    ]


_FORMAL_PORTFOLIO_BACKTEST_KINDS = frozenset(
    {
        EvidenceKind.BACKTEST_RUN_SUMMARY,
        EvidenceKind.BACKTEST_ARTIFACT_BUNDLE,
        EvidenceKind.RISK_POLICY_RESULT,
        EvidenceKind.BACKTEST_BIAS_AUDIT,
        EvidenceKind.BACKTEST_PERFORMANCE_METRICS,
        EvidenceKind.FORMAL_BACKTEST_API_RECORD,
    }
)


def _required_string(field_name: str, value: str) -> str:
    if type(value) is not str or not value.strip():
        raise ValueError(f"{field_name} is required")
    return value


def _optional_string(value: str | None) -> str | None:
    if value is None:
        return None
    return _required_string("optional string", value)


def _aware_datetime(field_name: str, value: datetime) -> datetime:
    if type(value) is not datetime or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")
    return value


def _sha256(field_name: str, value: str) -> str:
    value = _required_string(field_name, value)
    if not _SHA256_RE.fullmatch(value):
        raise ValueError(f"{field_name} must match sha256:<64 lowercase hex chars>")
    return value


def _optional_sha256(field_name: str, value: str | None) -> str | None:
    if value is None:
        return None
    return _sha256(field_name, value)


def _dataset_versions(value: dict[str, str]) -> dict[str, str]:
    if type(value) is not dict or not value:
        raise ValueError("dataset_versions must contain concrete Dataset Version ids")
    normalized: dict[str, str] = {}
    for name, version in value.items():
        normalized[_required_string("dataset name", name)] = _dataset_version(version)
    return dict(sorted(normalized.items()))


def _dataset_version(value: str) -> str:
    value = _required_string("dataset_version", value)
    if value.lower() == "latest" or not _DATASET_VERSION_RE.fullmatch(value):
        raise ValueError("dataset_versions must contain concrete Dataset Version ids")
    return value


def _string_mapping(field_name: str, value: dict[str, str]) -> dict[str, str]:
    if type(value) is not dict:
        raise ValueError(f"{field_name} must be a mapping")
    return {
        _required_string(f"{field_name} key", key): _required_string(f"{field_name} value", item)
        for key, item in sorted(value.items())
    }


def _string_list(field_name: str, value: list[str]) -> list[str]:
    if type(value) is not list:
        raise ValueError(f"{field_name} must be a list")
    normalized = [_required_string(field_name, item) for item in value]
    if len(normalized) != len(set(normalized)):
        raise ValueError(f"{field_name} cannot contain duplicates")
    return normalized


def _unique_by(label: str, values: list[Any], get_key: Any) -> dict[str, Any]:
    by_key: dict[str, Any] = {}
    for value in values:
        key = get_key(value)
        if key in by_key:
            raise ValueError(f"duplicate {label} id: {key}")
        by_key[key] = value
    return by_key


def _json_ready(value: Any) -> Any:
    if isinstance(value, StrEnum):
        return value.value
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): _json_ready(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_ready(item) for item in value]
    return value
