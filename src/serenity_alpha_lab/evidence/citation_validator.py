from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from serenity_alpha_lab.evidence.schema import (
    ClaimComputationPolicy,
    ClaimKind,
    ClaimVerificationStatus,
    EvidenceRecord,
    ReportCitation,
    ResearchClaim,
    ResearchReport,
    ResearchReportLevel,
)


CITATION_VALIDATOR_CONTRACT_VERSION = "research.citation_validator@1.0.0"
CITATION_VALIDATION_RESULT_SCHEMA_NAME = "research.citation_validation_result"
CITATION_VALIDATION_RESULT_SCHEMA_VERSION = "1.0.0"

_MANDATORY_CITATION_KINDS = frozenset(
    {
        ClaimKind.NUMERIC_METRIC,
        ClaimKind.TEMPORAL_FACT,
        ClaimKind.RISK_GATE,
        ClaimKind.LINEAGE_FACT,
    }
)


class CitationValidatorError(ValueError):
    """Raised when Citation Validator input violates the offline contract."""


class CitationValidationSeverity(StrEnum):
    ERROR = "error"
    WARNING = "warning"


class CitationValidationIssueCode(StrEnum):
    MISSING_CITATION = "missing_citation"
    UNKNOWN_CITATION = "unknown_citation"
    UNKNOWN_EVIDENCE = "unknown_evidence"
    EVIDENCE_AFTER_DECISION = "evidence_after_decision"
    VALUE_MISMATCH = "value_mismatch"
    UNIT_MISMATCH = "unit_mismatch"
    FORMULA_VERSION_MISMATCH = "formula_version_mismatch"
    DATASET_VERSION_MISMATCH = "dataset_version_mismatch"
    RUN_ID_MISMATCH = "run_id_mismatch"
    STAGE_ID_MISMATCH = "stage_id_mismatch"
    ARTIFACT_HASH_MISMATCH = "artifact_hash_mismatch"
    INVALID_COMPUTATION_POLICY = "invalid_computation_policy"


@dataclass(frozen=True, slots=True)
class CitationValidationIssue:
    code: CitationValidationIssueCode
    message: str
    severity: CitationValidationSeverity = CitationValidationSeverity.ERROR
    claim_id: str | None = None
    citation_id: str | None = None
    evidence_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "code", CitationValidationIssueCode(self.code))
        object.__setattr__(self, "severity", CitationValidationSeverity(self.severity))
        object.__setattr__(self, "message", _required_string("message", self.message))
        object.__setattr__(self, "claim_id", _optional_string(self.claim_id))
        object.__setattr__(self, "citation_id", _optional_string(self.citation_id))
        object.__setattr__(self, "evidence_id", _optional_string(self.evidence_id))

    def to_record(self) -> dict[str, Any]:
        return {
            "code": self.code.value,
            "severity": self.severity.value,
            "message": self.message,
            "claim_id": self.claim_id,
            "citation_id": self.citation_id,
            "evidence_id": self.evidence_id,
        }


@dataclass(frozen=True, slots=True)
class CitationValidationResult:
    report_id: str
    report_level: ResearchReportLevel
    validated_report: ResearchReport
    issues: tuple[CitationValidationIssue, ...]
    failed_claims: tuple[ResearchClaim, ...]
    removed_claim_ids: tuple[str, ...] = ()
    repair_attempted: bool = False
    contract_version: str = CITATION_VALIDATOR_CONTRACT_VERSION
    schema_name: str = CITATION_VALIDATION_RESULT_SCHEMA_NAME
    schema_version: str = CITATION_VALIDATION_RESULT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "report_id", _required_string("report_id", self.report_id))
        object.__setattr__(self, "report_level", ResearchReportLevel(self.report_level))
        if type(self.validated_report) is not ResearchReport:
            raise CitationValidatorError("validated_report must be a ResearchReport")
        object.__setattr__(self, "issues", _issue_tuple(self.issues))
        object.__setattr__(self, "failed_claims", _claim_tuple(self.failed_claims))
        object.__setattr__(self, "removed_claim_ids", _string_tuple("removed_claim_ids", self.removed_claim_ids))
        if type(self.repair_attempted) is not bool:
            raise CitationValidatorError("repair_attempted must be a bool")

    @property
    def issue_count(self) -> int:
        return len(self.issues)

    def to_record(self) -> dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "schema_name": self.schema_name,
            "schema_version": self.schema_version,
            "report_id": self.report_id,
            "report_level": self.report_level.value,
            "issue_count": self.issue_count,
            "repair_attempted": self.repair_attempted,
            "removed_claim_ids": list(self.removed_claim_ids),
            "issues": [issue.to_record() for issue in self.issues],
            "failed_claims": [claim.to_record() for claim in self.failed_claims],
            "validated_report": self.validated_report.to_record(),
        }


class CitationValidator:
    """Offline validator for P5 report claim/citation/evidence consistency."""

    def validate(self, report: ResearchReport) -> CitationValidationResult:
        report = _report(report)
        issues = tuple(_scan_report(report))
        failed_claim_ids = _failed_claim_ids(issues)
        failed_claims = tuple(
            _downgrade_claim(claim, _issues_for_claim(issues, claim.claim_id))
            for claim in report.claims
            if claim.claim_id in failed_claim_ids
        )
        validated_claims = tuple(
            _downgrade_claim(claim, _issues_for_claim(issues, claim.claim_id))
            if claim.claim_id in failed_claim_ids
            else claim
            for claim in report.claims
        )
        report_level = _report_level(validated_claims, issues)
        validated_report = _copy_report(report, claims=validated_claims, report_level=report_level)
        return CitationValidationResult(
            report_id=report.report_id,
            report_level=report_level,
            validated_report=validated_report,
            issues=issues,
            failed_claims=failed_claims,
        )

    def validate_with_repair(
        self,
        report: ResearchReport,
        *,
        repair_attempt: ResearchReport | None = None,
    ) -> CitationValidationResult:
        initial = self.validate(report)
        if initial.issue_count == 0 or repair_attempt is None:
            return initial

        repair_attempt = _report(repair_attempt)
        issues = tuple(_scan_report(repair_attempt))
        if not issues:
            report_level = _report_level(tuple(repair_attempt.claims), issues)
            validated_report = _copy_report(repair_attempt, claims=tuple(repair_attempt.claims), report_level=report_level)
            return CitationValidationResult(
                report_id=repair_attempt.report_id,
                report_level=report_level,
                validated_report=validated_report,
                issues=issues,
                failed_claims=(),
                repair_attempted=True,
            )

        failed_claim_ids = _failed_claim_ids(issues)
        removed_claim_ids = tuple(claim.claim_id for claim in repair_attempt.claims if claim.claim_id in failed_claim_ids)
        surviving_claims = tuple(claim for claim in repair_attempt.claims if claim.claim_id not in failed_claim_ids)
        failed_claims = tuple(
            _downgrade_claim(claim, _issues_for_claim(issues, claim.claim_id))
            for claim in repair_attempt.claims
            if claim.claim_id in failed_claim_ids
        )
        report_level = _report_level(surviving_claims, issues)
        validated_report = _copy_report(repair_attempt, claims=surviving_claims, report_level=report_level)
        return CitationValidationResult(
            report_id=repair_attempt.report_id,
            report_level=report_level,
            validated_report=validated_report,
            issues=issues,
            failed_claims=failed_claims,
            removed_claim_ids=removed_claim_ids,
            repair_attempted=True,
        )


def _scan_report(report: ResearchReport) -> list[CitationValidationIssue]:
    evidence_by_id = {evidence.evidence_id: evidence for evidence in report.evidence}
    citation_by_id = {citation.citation_id: citation for citation in report.citations}
    issues: list[CitationValidationIssue] = []

    for citation in report.citations:
        evidence = evidence_by_id.get(citation.evidence_id)
        if evidence is None:
            issues.append(
                _issue(
                    CitationValidationIssueCode.UNKNOWN_EVIDENCE,
                    "citation references missing evidence",
                    citation_id=citation.citation_id,
                    evidence_id=citation.evidence_id,
                )
            )
            continue
        if evidence.available_at > report.decision_time:
            issues.append(
                _issue(
                    CitationValidationIssueCode.EVIDENCE_AFTER_DECISION,
                    "cited evidence is not available at report decision_time",
                    citation_id=citation.citation_id,
                    evidence_id=evidence.evidence_id,
                )
            )
        issues.extend(_citation_evidence_issues(citation, evidence))

    for claim in report.claims:
        if claim.kind in _MANDATORY_CITATION_KINDS and not claim.citation_ids:
            issues.append(
                _issue(
                    CitationValidationIssueCode.MISSING_CITATION,
                    f"{claim.kind.value} claims require citations",
                    claim_id=claim.claim_id,
                )
            )
            continue
        for citation_id in claim.citation_ids:
            citation = citation_by_id.get(citation_id)
            if citation is None:
                issues.append(
                    _issue(
                        CitationValidationIssueCode.UNKNOWN_CITATION,
                        "claim references missing citation",
                        claim_id=claim.claim_id,
                        citation_id=citation_id,
                    )
                )
                continue
            issues.extend(_claim_issues_from_citation_issues(claim, citation, issues))
            issues.extend(_claim_citation_issues(claim, citation))
    return issues


def _citation_evidence_issues(citation: ReportCitation, evidence: EvidenceRecord) -> list[CitationValidationIssue]:
    issues: list[CitationValidationIssue] = []
    if evidence.dataset_versions and dict(citation.dataset_versions) != dict(evidence.dataset_versions):
        issues.append(
            _issue(
                CitationValidationIssueCode.DATASET_VERSION_MISMATCH,
                "citation dataset_versions do not match evidence",
                citation_id=citation.citation_id,
                evidence_id=evidence.evidence_id,
            )
        )
    if evidence.run_id and citation.run_id != evidence.run_id:
        issues.append(
            _issue(
                CitationValidationIssueCode.RUN_ID_MISMATCH,
                "citation run_id does not match evidence",
                citation_id=citation.citation_id,
                evidence_id=evidence.evidence_id,
            )
        )
    if evidence.stage_id and citation.stage_id != evidence.stage_id:
        issues.append(
            _issue(
                CitationValidationIssueCode.STAGE_ID_MISMATCH,
                "citation stage_id does not match evidence",
                citation_id=citation.citation_id,
                evidence_id=evidence.evidence_id,
            )
        )
    if evidence.artifact_hash and citation.artifact_hash != evidence.artifact_hash:
        issues.append(
            _issue(
                CitationValidationIssueCode.ARTIFACT_HASH_MISMATCH,
                "citation artifact_hash does not match evidence",
                citation_id=citation.citation_id,
                evidence_id=evidence.evidence_id,
            )
        )
    if (
        citation.formula_version is not None
        and evidence.formula_versions
        and citation.formula_version not in set(evidence.formula_versions.values())
    ):
        issues.append(
            _issue(
                CitationValidationIssueCode.FORMULA_VERSION_MISMATCH,
                "citation formula_version does not match evidence",
                citation_id=citation.citation_id,
                evidence_id=evidence.evidence_id,
            )
        )
    return issues


def _claim_citation_issues(claim: ResearchClaim, citation: ReportCitation) -> list[CitationValidationIssue]:
    if claim.kind is ClaimKind.NUMERIC_METRIC:
        return _numeric_claim_citation_issues(claim, citation)

    issues: list[CitationValidationIssue] = []
    if claim.kind in {ClaimKind.RISK_GATE, ClaimKind.LINEAGE_FACT} and claim.computation_policy is ClaimComputationPolicy.LLM_NARRATIVE:
        issues.append(
            _issue(
                CitationValidationIssueCode.INVALID_COMPUTATION_POLICY,
                f"{claim.kind.value} claims cannot use llm_narrative",
                claim_id=claim.claim_id,
                citation_id=citation.citation_id,
                evidence_id=citation.evidence_id,
            )
        )
    if claim.value is not None and citation.cited_value is not None and claim.value != citation.cited_value:
        issues.append(
            _issue(
                CitationValidationIssueCode.VALUE_MISMATCH,
                "claim value does not match citation cited_value",
                claim_id=claim.claim_id,
                citation_id=citation.citation_id,
                evidence_id=citation.evidence_id,
            )
        )
    issues.extend(_shared_claim_lineage_issues(claim, citation))
    return issues


def _claim_issues_from_citation_issues(
    claim: ResearchClaim,
    citation: ReportCitation,
    issues: list[CitationValidationIssue],
) -> list[CitationValidationIssue]:
    return [
        _issue(
            issue.code,
            issue.message,
            claim_id=claim.claim_id,
            citation_id=citation.citation_id,
            evidence_id=citation.evidence_id,
        )
        for issue in issues
        if issue.claim_id is None and issue.citation_id == citation.citation_id
    ]


def _numeric_claim_citation_issues(claim: ResearchClaim, citation: ReportCitation) -> list[CitationValidationIssue]:
    issues: list[CitationValidationIssue] = []
    if claim.computation_policy is not ClaimComputationPolicy.DETERMINISTIC_EVIDENCE:
        issues.append(
            _issue(
                CitationValidationIssueCode.INVALID_COMPUTATION_POLICY,
                "numeric_metric claims must use deterministic_evidence",
                claim_id=claim.claim_id,
                citation_id=citation.citation_id,
                evidence_id=citation.evidence_id,
            )
        )
    if citation.unit is None:
        issues.append(
            _issue(
                CitationValidationIssueCode.UNIT_MISMATCH,
                "numeric citations require unit",
                claim_id=claim.claim_id,
                citation_id=citation.citation_id,
                evidence_id=citation.evidence_id,
            )
        )
    if citation.formula_version is None:
        issues.append(
            _issue(
                CitationValidationIssueCode.FORMULA_VERSION_MISMATCH,
                "numeric citations require formula_version",
                claim_id=claim.claim_id,
                citation_id=citation.citation_id,
                evidence_id=citation.evidence_id,
            )
        )
    if claim.value != citation.cited_value:
        issues.append(
            _issue(
                CitationValidationIssueCode.VALUE_MISMATCH,
                "numeric claim value does not match citation cited_value",
                claim_id=claim.claim_id,
                citation_id=citation.citation_id,
                evidence_id=citation.evidence_id,
            )
        )
    if claim.unit != citation.unit:
        issues.append(
            _issue(
                CitationValidationIssueCode.UNIT_MISMATCH,
                "numeric claim unit does not match citation unit",
                claim_id=claim.claim_id,
                citation_id=citation.citation_id,
                evidence_id=citation.evidence_id,
            )
        )
    if claim.formula_version != citation.formula_version:
        issues.append(
            _issue(
                CitationValidationIssueCode.FORMULA_VERSION_MISMATCH,
                "numeric claim formula_version does not match citation formula_version",
                claim_id=claim.claim_id,
                citation_id=citation.citation_id,
                evidence_id=citation.evidence_id,
            )
        )
    issues.extend(_shared_claim_lineage_issues(claim, citation))
    return issues


def _shared_claim_lineage_issues(claim: ResearchClaim, citation: ReportCitation) -> list[CitationValidationIssue]:
    issues: list[CitationValidationIssue] = []
    if dict(claim.dataset_versions) != dict(citation.dataset_versions):
        issues.append(
            _issue(
                CitationValidationIssueCode.DATASET_VERSION_MISMATCH,
                "claim dataset_versions do not match citation dataset_versions",
                claim_id=claim.claim_id,
                citation_id=citation.citation_id,
                evidence_id=citation.evidence_id,
            )
        )
    if citation.run_id is not None and claim.run_id != citation.run_id:
        issues.append(
            _issue(
                CitationValidationIssueCode.RUN_ID_MISMATCH,
                "claim run_id does not match citation run_id",
                claim_id=claim.claim_id,
                citation_id=citation.citation_id,
                evidence_id=citation.evidence_id,
            )
        )
    if citation.stage_id is not None and claim.stage_id != citation.stage_id:
        issues.append(
            _issue(
                CitationValidationIssueCode.STAGE_ID_MISMATCH,
                "claim stage_id does not match citation stage_id",
                claim_id=claim.claim_id,
                citation_id=citation.citation_id,
                evidence_id=citation.evidence_id,
            )
        )
    if citation.artifact_hash is not None and claim.artifact_hash != citation.artifact_hash:
        issues.append(
            _issue(
                CitationValidationIssueCode.ARTIFACT_HASH_MISMATCH,
                "claim artifact_hash does not match citation artifact_hash",
                claim_id=claim.claim_id,
                citation_id=citation.citation_id,
                evidence_id=citation.evidence_id,
            )
        )
    return issues


def _copy_report(
    report: ResearchReport,
    *,
    claims: tuple[ResearchClaim, ...],
    report_level: ResearchReportLevel,
) -> ResearchReport:
    return report.model_copy(
        update={
            "report_level": report_level,
            "claims": list(claims),
            "warnings": list(report.warnings),
        }
    )


def _downgrade_claim(claim: ResearchClaim, issues: tuple[CitationValidationIssue, ...]) -> ResearchClaim:
    if not issues:
        return claim
    status = _status_for_issues(issues)
    warning_codes = tuple(dict.fromkeys([*claim.warnings, *(issue.code.value for issue in issues)]))
    return claim.model_copy(
        update={
            "verification_status": status,
            "warnings": list(warning_codes),
        }
    )


def _report_level(claims: tuple[ResearchClaim, ...], issues: tuple[CitationValidationIssue, ...]) -> ResearchReportLevel:
    if not claims:
        return ResearchReportLevel.INSUFFICIENT_EVIDENCE
    if issues:
        return ResearchReportLevel.PARTIAL
    if all(claim.verification_status is ClaimVerificationStatus.VERIFIED for claim in claims):
        return ResearchReportLevel.VERIFIED
    return ResearchReportLevel.PARTIAL


def _status_for_issues(issues: tuple[CitationValidationIssue, ...]) -> ClaimVerificationStatus:
    codes = {issue.code for issue in issues}
    if CitationValidationIssueCode.MISSING_CITATION in codes or CitationValidationIssueCode.UNKNOWN_CITATION in codes:
        return ClaimVerificationStatus.CITATION_MISSING
    if CitationValidationIssueCode.UNKNOWN_EVIDENCE in codes or CitationValidationIssueCode.EVIDENCE_AFTER_DECISION in codes:
        return ClaimVerificationStatus.INSUFFICIENT_EVIDENCE
    if CitationValidationIssueCode.INVALID_COMPUTATION_POLICY in codes:
        return ClaimVerificationStatus.REJECTED
    if codes:
        return ClaimVerificationStatus.VALUE_MISMATCH
    return ClaimVerificationStatus.VERIFIED


def _failed_claim_ids(issues: tuple[CitationValidationIssue, ...]) -> frozenset[str]:
    return frozenset(issue.claim_id for issue in issues if issue.claim_id is not None)


def _issues_for_claim(
    issues: tuple[CitationValidationIssue, ...],
    claim_id: str,
) -> tuple[CitationValidationIssue, ...]:
    return tuple(issue for issue in issues if issue.claim_id == claim_id)


def _issue(
    code: CitationValidationIssueCode,
    message: str,
    *,
    claim_id: str | None = None,
    citation_id: str | None = None,
    evidence_id: str | None = None,
) -> CitationValidationIssue:
    return CitationValidationIssue(
        code=code,
        message=message,
        claim_id=claim_id,
        citation_id=citation_id,
        evidence_id=evidence_id,
    )


def _report(value: ResearchReport) -> ResearchReport:
    if type(value) is not ResearchReport:
        raise CitationValidatorError("report must be a ResearchReport")
    return value


def _issue_tuple(values: tuple[CitationValidationIssue, ...]) -> tuple[CitationValidationIssue, ...]:
    if isinstance(values, list):
        values = tuple(values)
    if type(values) is not tuple:
        raise CitationValidatorError("issues must be a tuple")
    for value in values:
        if type(value) is not CitationValidationIssue:
            raise CitationValidatorError("issues must contain CitationValidationIssue objects")
    return values


def _claim_tuple(values: tuple[ResearchClaim, ...]) -> tuple[ResearchClaim, ...]:
    if isinstance(values, list):
        values = tuple(values)
    if type(values) is not tuple:
        raise CitationValidatorError("failed_claims must be a tuple")
    for value in values:
        if type(value) is not ResearchClaim:
            raise CitationValidatorError("failed_claims must contain ResearchClaim objects")
    return values


def _string_tuple(field_name: str, values: tuple[str, ...]) -> tuple[str, ...]:
    if isinstance(values, list):
        values = tuple(values)
    if type(values) is not tuple:
        raise CitationValidatorError(f"{field_name} must be a tuple")
    return tuple(_required_string(field_name, value) for value in values)


def _required_string(field_name: str, value: str) -> str:
    if type(value) is not str or not value.strip():
        raise CitationValidatorError(f"{field_name} is required")
    return value


def _optional_string(value: str | None) -> str | None:
    if value is None:
        return None
    return _required_string("optional string", value)


__all__ = [
    "CITATION_VALIDATION_RESULT_SCHEMA_NAME",
    "CITATION_VALIDATION_RESULT_SCHEMA_VERSION",
    "CITATION_VALIDATOR_CONTRACT_VERSION",
    "CitationValidationIssue",
    "CitationValidationIssueCode",
    "CitationValidationResult",
    "CitationValidationSeverity",
    "CitationValidator",
    "CitationValidatorError",
]
