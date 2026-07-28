from __future__ import annotations

from datetime import UTC, datetime, timedelta

from serenity_alpha_lab.evidence.citation_validator import CitationValidationIssueCode, CitationValidator
from serenity_alpha_lab.evidence.schema import (
    ClaimComputationPolicy,
    ClaimKind,
    ClaimVerificationStatus,
    EvidenceEvaluationScope,
    EvidenceKind,
    EvidenceRecord,
    EvidenceSource,
    EvidenceTrustLevel,
    ReportCitation,
    ResearchClaim,
    ResearchReport,
    ResearchReportLevel,
)


NOW = datetime(2026, 7, 28, 10, 0, tzinfo=UTC)
HASH_A = "sha256:" + "a" * 64
HASH_B = "sha256:" + "b" * 64
HASH_C = "sha256:" + "c" * 64
DATASET_VERSIONS = {"adjusted_daily_bars": "dsv_" + "1" * 32}


def test_citation_validator_accepts_verified_report_with_consistent_claims() -> None:
    report = _report(
        report_level=ResearchReportLevel.VERIFIED,
        claims=(_numeric_claim(), _temporal_claim()),
        citations=(_metric_citation(), _temporal_citation()),
    )

    result = CitationValidator().validate(report)

    assert result.report_level is ResearchReportLevel.VERIFIED
    assert result.issue_count == 0
    assert result.removed_claim_ids == ()
    assert [claim.claim_id for claim in result.validated_report.claims] == ["cl_metric", "cl_temporal"]
    assert all(claim.verification_status is ClaimVerificationStatus.VERIFIED for claim in result.validated_report.claims)


def test_citation_validator_downgrades_missing_temporal_or_mismatched_numeric_claims() -> None:
    report = _report(
        report_level=ResearchReportLevel.PARTIAL,
        claims=(
            _numeric_claim(value="0.990000"),
            _temporal_claim(citation_ids=(), verification_status=ClaimVerificationStatus.PARTIAL),
            _risk_claim(),
        ),
        citations=(_metric_citation(), _risk_citation()),
    )

    result = CitationValidator().validate(report)

    assert result.report_level is ResearchReportLevel.PARTIAL
    assert result.removed_claim_ids == ()
    assert {issue.code for issue in result.issues} == {
        CitationValidationIssueCode.VALUE_MISMATCH,
        CitationValidationIssueCode.MISSING_CITATION,
    }
    failed_by_id = {claim.claim_id: claim for claim in result.failed_claims}
    assert failed_by_id["cl_metric"].verification_status is ClaimVerificationStatus.VALUE_MISMATCH
    assert failed_by_id["cl_temporal"].verification_status is ClaimVerificationStatus.CITATION_MISSING
    assert all(
        claim.verification_status is not ClaimVerificationStatus.VERIFIED
        for claim in result.validated_report.claims
        if claim.claim_id in {"cl_metric", "cl_temporal"}
    )


def test_citation_validator_marks_claim_failed_when_citation_lineage_breaks() -> None:
    report = _report(
        report_level=ResearchReportLevel.VERIFIED,
        claims=(_numeric_claim(),),
        citations=(_metric_citation(artifact_hash=HASH_B),),
    )

    result = CitationValidator().validate(report)

    assert result.report_level is ResearchReportLevel.PARTIAL
    assert CitationValidationIssueCode.ARTIFACT_HASH_MISMATCH in {issue.code for issue in result.issues}
    assert result.failed_claims[0].claim_id == "cl_metric"
    assert result.validated_report.claims[0].verification_status is ClaimVerificationStatus.VALUE_MISMATCH


def test_citation_validator_marks_claim_failed_when_citation_disagrees_with_evidence_lineage() -> None:
    bad_versions = {"adjusted_daily_bars": "dsv_" + "9" * 32}
    report = _report(
        report_level=ResearchReportLevel.VERIFIED,
        claims=(_numeric_claim(dataset_versions=bad_versions),),
        citations=(_metric_citation(dataset_versions=bad_versions),),
    )

    result = CitationValidator().validate(report)

    assert result.report_level is ResearchReportLevel.PARTIAL
    assert CitationValidationIssueCode.DATASET_VERSION_MISMATCH in {issue.code for issue in result.issues}
    assert result.failed_claims[0].claim_id == "cl_metric"
    assert result.validated_report.claims[0].verification_status is ClaimVerificationStatus.VALUE_MISMATCH


def test_citation_validator_reports_missing_cited_evidence_without_revalidating_report_graph() -> None:
    missing_evidence_citation = _metric_citation().model_copy(update={"evidence_id": "ev_missing"})
    report = ResearchReport.model_construct(
        report_id="rpt_citation_validator",
        report_level=ResearchReportLevel.VERIFIED,
        decision_time=NOW,
        evidence=[_metric_evidence()],
        citations=[missing_evidence_citation],
        claims=[_numeric_claim()],
        dataset_versions=DATASET_VERSIONS,
        run_id="run-report",
        warnings=[],
    )

    result = CitationValidator().validate(report)

    assert result.report_level is ResearchReportLevel.PARTIAL
    assert CitationValidationIssueCode.UNKNOWN_EVIDENCE in {issue.code for issue in result.issues}
    assert result.failed_claims[0].claim_id == "cl_metric"
    assert result.validated_report.claims[0].verification_status is ClaimVerificationStatus.INSUFFICIENT_EVIDENCE


def test_citation_validator_reports_future_evidence_without_revalidating_report_graph() -> None:
    future_evidence = _metric_evidence().model_copy(update={"available_at": NOW + timedelta(minutes=1)})
    report = ResearchReport.model_construct(
        report_id="rpt_citation_validator",
        report_level=ResearchReportLevel.VERIFIED,
        decision_time=NOW,
        evidence=[future_evidence],
        citations=[_metric_citation()],
        claims=[_numeric_claim()],
        dataset_versions=DATASET_VERSIONS,
        run_id="run-report",
        warnings=[],
    )

    result = CitationValidator().validate(report)

    assert result.report_level is ResearchReportLevel.PARTIAL
    assert CitationValidationIssueCode.EVIDENCE_AFTER_DECISION in {issue.code for issue in result.issues}
    assert result.failed_claims[0].claim_id == "cl_metric"
    assert result.validated_report.claims[0].verification_status is ClaimVerificationStatus.INSUFFICIENT_EVIDENCE


def test_citation_validator_removes_claim_after_one_failed_repair_attempt() -> None:
    original = _report(
        report_level=ResearchReportLevel.VERIFIED,
        claims=(_numeric_claim(value="0.990000"), _risk_claim()),
        citations=(_metric_citation(), _risk_citation()),
    )
    repaired = _report(
        report_level=ResearchReportLevel.VERIFIED,
        claims=(_numeric_claim(value="0.880000"), _risk_claim()),
        citations=(_metric_citation(), _risk_citation()),
    )

    result = CitationValidator().validate_with_repair(original, repair_attempt=repaired)

    assert result.report_level is ResearchReportLevel.PARTIAL
    assert result.removed_claim_ids == ("cl_metric",)
    assert [claim.claim_id for claim in result.validated_report.claims] == ["cl_risk"]
    assert result.validated_report.claims[0].verification_status is ClaimVerificationStatus.VERIFIED
    assert all(claim.claim_id != "cl_metric" for claim in result.validated_report.claims)


def _report(
    *,
    report_level: ResearchReportLevel,
    claims: tuple[ResearchClaim, ...],
    citations: tuple[ReportCitation, ...],
) -> ResearchReport:
    return ResearchReport(
        report_id="rpt_citation_validator",
        report_level=report_level,
        decision_time=NOW,
        evidence=(_metric_evidence(), _temporal_evidence(), _risk_evidence()),
        citations=citations,
        claims=claims,
        dataset_versions=DATASET_VERSIONS,
        run_id="run-report",
    )


def _metric_evidence() -> EvidenceRecord:
    return EvidenceRecord(
        evidence_id="ev_metric",
        kind=EvidenceKind.BACKTEST_PERFORMANCE_METRICS,
        evaluation_scope=EvidenceEvaluationScope.FORMAL_PORTFOLIO_BACKTEST,
        title="Backtest metric evidence",
        summary="Formal backtest cumulative return metric.",
        source=EvidenceSource(
            source_id="metric_report",
            source_type="artifact",
            schema_name="quant.backtest.performance_metrics",
            schema_version="1.0.0",
        ),
        available_at=NOW,
        content_hash=HASH_A,
        trust=EvidenceTrustLevel.AUTHORITATIVE,
        dataset_versions=DATASET_VERSIONS,
        run_id="run-backtest",
        stage_id="stage-metrics",
        artifact_id="art_metrics",
        artifact_hash=HASH_A,
        formula_versions={"cumulative_return": "cumulative_return@1.0.0"},
        metadata={"llm_recompute_allowed": False},
    )


def _temporal_evidence() -> EvidenceRecord:
    return EvidenceRecord(
        evidence_id="ev_temporal",
        kind=EvidenceKind.UNSTRUCTURED_SOURCE,
        evaluation_scope=EvidenceEvaluationScope.MARKET_INTELLIGENCE,
        title="Official announcement",
        summary="Company announcement available before decision time.",
        source=EvidenceSource(
            source_id="official_announcement",
            source_type="official_disclosure",
            schema_name="research.source_trust",
            schema_version="1.0.0",
        ),
        available_at=NOW,
        content_hash=HASH_B,
        trust=EvidenceTrustLevel.HIGH,
        dataset_versions={"intel_corpus": "dsv_" + "2" * 32},
        run_id="run-intel",
        stage_id="stage-intel",
        artifact_id="art_announcement",
        artifact_hash=HASH_B,
        metadata={"llm_recompute_allowed": False},
    )


def _risk_evidence() -> EvidenceRecord:
    return EvidenceRecord(
        evidence_id="ev_risk",
        kind=EvidenceKind.RISK_POLICY_RESULT,
        evaluation_scope=EvidenceEvaluationScope.FORMAL_PORTFOLIO_BACKTEST,
        title="Risk policy result",
        summary="Risk policy blocked ranking for deterministic reasons.",
        source=EvidenceSource(
            source_id="risk_policy_result",
            source_type="artifact",
            schema_name="quant.backtest.risk_policy",
            schema_version="1.0.0",
        ),
        available_at=NOW,
        content_hash=HASH_C,
        trust=EvidenceTrustLevel.AUTHORITATIVE,
        dataset_versions=DATASET_VERSIONS,
        run_id="run-backtest",
        stage_id="stage-risk",
        artifact_id="art_risk",
        artifact_hash=HASH_C,
        formula_versions={"policy": "risk_policy.cn_a_share@1.0.0"},
        metadata={"llm_recompute_allowed": False, "risk_status": "block"},
    )


def _metric_citation(
    *,
    artifact_hash: str = HASH_A,
    dataset_versions: dict[str, str] | None = None,
) -> ReportCitation:
    return ReportCitation(
        citation_id="cit_metric",
        evidence_id="ev_metric",
        evidence_field_path="body.returns.cumulative_return",
        cited_value="0.120000",
        unit="ratio",
        formula_version="cumulative_return@1.0.0",
        dataset_versions=dataset_versions or DATASET_VERSIONS,
        run_id="run-backtest",
        stage_id="stage-metrics",
        artifact_hash=artifact_hash,
    )


def _temporal_citation() -> ReportCitation:
    return ReportCitation(
        citation_id="cit_temporal",
        evidence_id="ev_temporal",
        evidence_field_path="body.published_at",
        cited_value="2026-07-27T09:00:00+00:00",
        dataset_versions={"intel_corpus": "dsv_" + "2" * 32},
        run_id="run-intel",
        stage_id="stage-intel",
        artifact_hash=HASH_B,
    )


def _risk_citation() -> ReportCitation:
    return ReportCitation(
        citation_id="cit_risk",
        evidence_id="ev_risk",
        evidence_field_path="body.status",
        cited_value="block",
        formula_version="risk_policy.cn_a_share@1.0.0",
        dataset_versions=DATASET_VERSIONS,
        run_id="run-backtest",
        stage_id="stage-risk",
        artifact_hash=HASH_C,
    )


def _numeric_claim(
    *,
    value: str = "0.120000",
    dataset_versions: dict[str, str] | None = None,
) -> ResearchClaim:
    return ResearchClaim(
        claim_id="cl_metric",
        kind=ClaimKind.NUMERIC_METRIC,
        statement="The formal portfolio backtest cumulative return was 12.0%.",
        verification_status=ClaimVerificationStatus.VERIFIED,
        citation_ids=["cit_metric"],
        computation_policy=ClaimComputationPolicy.DETERMINISTIC_EVIDENCE,
        value=value,
        unit="ratio",
        formula_version="cumulative_return@1.0.0",
        dataset_versions=dataset_versions or DATASET_VERSIONS,
        run_id="run-backtest",
        stage_id="stage-metrics",
        artifact_hash=HASH_A,
    )


def _temporal_claim(
    *,
    citation_ids: tuple[str, ...] = ("cit_temporal",),
    verification_status: ClaimVerificationStatus = ClaimVerificationStatus.VERIFIED,
) -> ResearchClaim:
    return ResearchClaim(
        claim_id="cl_temporal",
        kind=ClaimKind.TEMPORAL_FACT,
        statement="The official announcement was available before the decision time.",
        verification_status=verification_status,
        citation_ids=list(citation_ids),
        computation_policy=ClaimComputationPolicy.CITATION_SUMMARY,
        value="2026-07-27T09:00:00+00:00",
        dataset_versions={"intel_corpus": "dsv_" + "2" * 32},
        run_id="run-intel",
        stage_id="stage-intel",
        artifact_hash=HASH_B,
    )


def _risk_claim() -> ResearchClaim:
    return ResearchClaim(
        claim_id="cl_risk",
        kind=ClaimKind.RISK_GATE,
        statement="Risk policy blocked ranking eligibility.",
        verification_status=ClaimVerificationStatus.VERIFIED,
        citation_ids=["cit_risk"],
        computation_policy=ClaimComputationPolicy.CITATION_SUMMARY,
        value="block",
        dataset_versions=DATASET_VERSIONS,
        run_id="run-backtest",
        stage_id="stage-risk",
        artifact_hash=HASH_C,
    )
