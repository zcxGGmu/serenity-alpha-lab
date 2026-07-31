from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from serenity_alpha_lab.evidence.report_renderer import (
    REPORT_RENDERER_CONTRACT_VERSION,
    REPORT_RENDERING_SCHEMA_NAME,
    REPORT_RENDERING_SCHEMA_VERSION,
    TRUSTED_RESEARCH_REPORT_SCHEMA_NAME,
    TRUSTED_RESEARCH_REPORT_SCHEMA_VERSION,
    ReportRendererError,
    ResearchReportRenderContext,
    TrustedResearchReportRenderer,
)
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


NOW = datetime(2026, 7, 29, 10, 30, tzinfo=UTC)
HASH_A = "sha256:" + "a" * 64
HASH_B = "sha256:" + "b" * 64
DATASET_VERSIONS = {"adjusted_daily_bars": "dsv_" + "1" * 32}


def test_renderer_produces_authoritative_json_and_derived_markdown_html() -> None:
    report = _verified_report()
    context = _context()

    rendered = TrustedResearchReportRenderer().render(report, context=context)

    assert rendered.contract_version == REPORT_RENDERER_CONTRACT_VERSION
    assert rendered.schema_name == REPORT_RENDERING_SCHEMA_NAME
    assert rendered.schema_version == REPORT_RENDERING_SCHEMA_VERSION
    assert rendered.trusted_report.schema_name == TRUSTED_RESEARCH_REPORT_SCHEMA_NAME
    assert rendered.trusted_report.schema_version == TRUSTED_RESEARCH_REPORT_SCHEMA_VERSION
    assert rendered.trusted_report.authoritative_json["authority"] == "canonical_json"
    assert rendered.trusted_report.authoritative_json_hash.startswith("sha256:")
    assert rendered.trusted_report.authoritative_json["report"]["report_level"] == "verified"
    assert rendered.trusted_report.authoritative_json["validation"]["issue_count"] == 0
    assert rendered.markdown_source == "derived_from_authoritative_json"
    assert rendered.html_source == "derived_from_authoritative_json"

    markdown = rendered.markdown
    assert "# Trusted Alpha Report" in markdown
    assert "Report Level: verified" in markdown
    assert "As Of: 2026-07-29T10:30:00+00:00" in markdown
    assert "adjusted_daily_bars: dsv_11111111111111111111111111111111" in markdown
    assert "Model: openai / gpt-4.1-mini / 2026-07-01" in markdown
    assert "Cost: USD 0.123456" in markdown
    assert "Risk: Risk gate remains block until deterministic policy rerun." in markdown
    assert "Disclaimer: Research only; not investment advice." in markdown
    assert "[cl_metric] The formal portfolio backtest cumulative return was 12.0%." in markdown
    assert "citations: cit_metric" in markdown
    assert "[cit_metric] evidence=ev_metric path=body.returns.cumulative_return" in markdown

    html = rendered.html
    assert "<article" in html
    assert "data-authoritative-json-hash=" in html
    assert "Trusted Alpha Report" in html
    assert "Research only; not investment advice." in html
    assert "<script" not in html.lower()


def test_renderer_downgrades_invalid_report_and_displays_validation_issues() -> None:
    future_evidence = _metric_evidence().model_copy(update={"available_at": NOW + timedelta(minutes=1)})
    invalid_report = ResearchReport.model_construct(
        report_id="rpt_trusted_renderer",
        report_level=ResearchReportLevel.VERIFIED,
        decision_time=NOW,
        generated_at=NOW,
        evidence=[future_evidence],
        citations=[_metric_citation()],
        claims=[_numeric_claim()],
        dataset_versions=DATASET_VERSIONS,
        run_id="run-report",
        warnings=[],
    )

    rendered = TrustedResearchReportRenderer().render(invalid_report, context=_context())

    assert rendered.trusted_report.report_level is ResearchReportLevel.PARTIAL
    assert rendered.trusted_report.authoritative_json["report"]["report_level"] == "partial"
    assert rendered.trusted_report.authoritative_json["validation"]["issue_count"] >= 1
    assert "Validation Issues" in rendered.markdown
    assert "evidence_after_decision" in rendered.markdown
    assert "Report Level: partial" in rendered.markdown


def test_renderer_renders_insufficient_evidence_without_promoting_to_verified() -> None:
    report = ResearchReport(
        report_id="rpt_insufficient",
        report_level=ResearchReportLevel.INSUFFICIENT_EVIDENCE,
        decision_time=NOW,
        generated_at=NOW,
        evidence=[_metric_evidence()],
        citations=[],
        claims=[],
        dataset_versions=DATASET_VERSIONS,
        run_id="run-report",
        warnings=["No valid claims survived citation validation."],
    )

    rendered = TrustedResearchReportRenderer().render(report, context=_context())

    assert rendered.trusted_report.report_level is ResearchReportLevel.INSUFFICIENT_EVIDENCE
    assert "Report Level: insufficient_evidence" in rendered.markdown
    assert "No verified claims available." in rendered.markdown
    assert "No valid claims survived citation validation." in rendered.markdown


def test_renderer_rejects_markdown_input_and_missing_required_display_context() -> None:
    renderer = TrustedResearchReportRenderer()

    with pytest.raises(ReportRendererError, match="ResearchReport"):
        renderer.render("# fake markdown", context=_context())  # type: ignore[arg-type]

    with pytest.raises(ReportRendererError, match="disclaimer"):
        ResearchReportRenderContext(
            title="Trusted Alpha Report",
            model_provider="openai",
            model_name="gpt-4.1-mini",
            model_version="2026-07-01",
            prompt_versions={"decision": "decision@1.0.0"},
            total_cost_usd="0.123456",
            risk_summary="Risk gate remains block until deterministic policy rerun.",
            disclaimer=" ",
        )


def _context() -> ResearchReportRenderContext:
    return ResearchReportRenderContext(
        title="Trusted Alpha Report",
        model_provider="openai",
        model_name="gpt-4.1-mini",
        model_version="2026-07-01",
        prompt_versions={"decision": "decision@1.0.0"},
        total_cost_usd="0.123456",
        risk_summary="Risk gate remains block until deterministic policy rerun.",
        disclaimer="Research only; not investment advice.",
    )


def _verified_report() -> ResearchReport:
    return ResearchReport(
        report_id="rpt_trusted_renderer",
        report_level=ResearchReportLevel.VERIFIED,
        decision_time=NOW,
        generated_at=NOW,
        evidence=[_metric_evidence(), _risk_evidence()],
        citations=[_metric_citation(), _risk_citation()],
        claims=[_numeric_claim(), _risk_claim()],
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


def _risk_evidence() -> EvidenceRecord:
    return EvidenceRecord(
        evidence_id="ev_risk",
        kind=EvidenceKind.RISK_POLICY_RESULT,
        evaluation_scope=EvidenceEvaluationScope.FORMAL_PORTFOLIO_BACKTEST,
        title="Risk policy result",
        summary="Risk policy blocks promotion until rerun.",
        source=EvidenceSource(
            source_id="risk_policy_result",
            source_type="artifact",
            schema_name="quant.backtest.risk_policy",
            schema_version="1.0.0",
        ),
        available_at=NOW,
        content_hash=HASH_B,
        trust=EvidenceTrustLevel.AUTHORITATIVE,
        dataset_versions=DATASET_VERSIONS,
        run_id="run-backtest",
        stage_id="stage-risk",
        artifact_id="art_risk",
        artifact_hash=HASH_B,
        formula_versions={"policy": "risk_policy.cn_a_share@1.0.0"},
        metadata={"llm_recompute_allowed": False, "risk_status": "block"},
    )


def _metric_citation() -> ReportCitation:
    return ReportCitation(
        citation_id="cit_metric",
        evidence_id="ev_metric",
        evidence_field_path="body.returns.cumulative_return",
        cited_value="0.120000",
        unit="ratio",
        formula_version="cumulative_return@1.0.0",
        dataset_versions=DATASET_VERSIONS,
        run_id="run-backtest",
        stage_id="stage-metrics",
        artifact_hash=HASH_A,
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
        artifact_hash=HASH_B,
    )


def _numeric_claim() -> ResearchClaim:
    return ResearchClaim(
        claim_id="cl_metric",
        kind=ClaimKind.NUMERIC_METRIC,
        statement="The formal portfolio backtest cumulative return was 12.0%.",
        verification_status=ClaimVerificationStatus.VERIFIED,
        citation_ids=["cit_metric"],
        computation_policy=ClaimComputationPolicy.DETERMINISTIC_EVIDENCE,
        value="0.120000",
        unit="ratio",
        formula_version="cumulative_return@1.0.0",
        dataset_versions=DATASET_VERSIONS,
        run_id="run-backtest",
        stage_id="stage-metrics",
        artifact_hash=HASH_A,
    )


def _risk_claim() -> ResearchClaim:
    return ResearchClaim(
        claim_id="cl_risk",
        kind=ClaimKind.RISK_GATE,
        statement="Risk policy status remains block.",
        verification_status=ClaimVerificationStatus.VERIFIED,
        citation_ids=["cit_risk"],
        computation_policy=ClaimComputationPolicy.DETERMINISTIC_EVIDENCE,
        value="block",
        formula_version="risk_policy.cn_a_share@1.0.0",
        dataset_versions=DATASET_VERSIONS,
        run_id="run-backtest",
        stage_id="stage-risk",
        artifact_hash=HASH_B,
    )
