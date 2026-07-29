from __future__ import annotations

from datetime import UTC, datetime

from serenity_alpha_lab.application.report_delivery import (
    REPORT_DELIVERY_UI_CONTRACT_VERSION,
    REPORT_DELIVERY_UI_ROUTES,
    REPORT_PAGE_SCHEMA_NAME,
    ResearchReportNotificationStatus,
    ResearchReportPagePresenter,
)
from serenity_alpha_lab.evidence.report_renderer import ResearchReportRenderContext, TrustedResearchReportRenderer
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


NOW = datetime(2026, 7, 29, 15, 30, tzinfo=UTC)
HASH_A = "sha256:" + "a" * 64
HASH_B = "sha256:" + "b" * 64
DATASET_VERSIONS = {"adjusted_daily_bars": "dsv_" + "1" * 32}


def test_report_delivery_ui_expands_claims_to_citations_evidence_sources_and_artifacts() -> None:
    rendered = TrustedResearchReportRenderer().render(_verified_report(), context=_context())
    notification = ResearchReportNotificationStatus(
        message_id="msg-report-email",
        channel="email",
        dedupe_key="report:rpt_delivery:email",
        status="sent",
        attempt=1,
        last_error=None,
        sent_at=NOW,
    )

    page = ResearchReportPagePresenter().build(rendered, notification_records=[notification])
    record = page.to_record()
    claim = record["claims"][0]
    citation = claim["citations"][0]

    assert record["contract_version"] == REPORT_DELIVERY_UI_CONTRACT_VERSION
    assert record["schema"] == {"name": REPORT_PAGE_SCHEMA_NAME, "version": "1.0.0"}
    assert record["authority"] == "canonical_json"
    assert record["authoritative_json_hash"] == rendered.trusted_report.authoritative_json_hash
    assert record["rendering_hash"] == rendered.rendering_hash
    assert record["markdown_source"] == "derived_from_authoritative_json"
    assert record["html_source"] == "derived_from_authoritative_json"
    assert record["report"]["report_id"] == "rpt_delivery"
    assert record["report"]["report_level"] == "verified"
    assert record["display_context"]["model"]["provider"] == "openai"
    assert record["display_context"]["cost"]["total_cost_usd"] == "0.123456"
    assert record["dataset_versions"] == DATASET_VERSIONS
    assert record["notification_statuses"] == [
        {
            "message_id": "msg-report-email",
            "channel": "email",
            "dedupe_key": "report:rpt_delivery:email",
            "status": "sent",
            "attempt": 1,
            "sent_at": NOW.isoformat(),
        }
    ]

    assert claim["claim_id"] == "cl_metric"
    assert claim["citation_ids"] == ["cit_metric"]
    assert citation["citation_id"] == "cit_metric"
    assert citation["evidence_field_path"] == "body.returns.cumulative_return"
    assert citation["evidence"]["evidence_id"] == "ev_metric"
    assert citation["evidence"]["title"] == "Backtest metric evidence"
    assert citation["evidence"]["source"]["source_uri"] == "artifact://tenant/run/metrics@sha256"
    assert citation["evidence"]["source_link"] == "artifact://tenant/run/metrics@sha256"
    assert citation["evidence"]["artifact"] == {
        "artifact_id": "art_metrics",
        "artifact_hash": HASH_A,
    }
    assert citation["artifact_hash"] == HASH_A
    assert citation["dataset_versions"] == DATASET_VERSIONS
    assert record["citation_graph_hash"].startswith("sha256:")


def test_report_delivery_ui_declares_research_report_routes_without_notification_side_effects() -> None:
    paths = {(route.method, route.path, route.response_status) for route in REPORT_DELIVERY_UI_ROUTES}

    assert ("GET", "/api/v1/research/reports/{report_id}", 200) in paths
    assert ("GET", "/api/v1/research/reports/{report_id}/notifications", 200) in paths
    assert all("/api/v1/backtest" not in route.path for route in REPORT_DELIVERY_UI_ROUTES)
    assert all("send" not in route.operation_id.lower() for route in REPORT_DELIVERY_UI_ROUTES)


def _context() -> ResearchReportRenderContext:
    return ResearchReportRenderContext(
        title="Trusted Alpha Delivery Report",
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
        report_id="rpt_delivery",
        report_level=ResearchReportLevel.VERIFIED,
        decision_time=NOW,
        generated_at=NOW,
        evidence=[_metric_evidence(), _risk_evidence()],
        citations=[_metric_citation(), _risk_citation()],
        claims=[_numeric_claim(), _risk_claim()],
        dataset_versions=DATASET_VERSIONS,
        run_id="run-report",
        trace_id="trace-report",
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
            source_uri="artifact://tenant/run/metrics@sha256",
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
