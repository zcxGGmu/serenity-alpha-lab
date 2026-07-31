from __future__ import annotations

from datetime import UTC, datetime

import pytest

from serenity_alpha_lab.application.input_fetch_security import (
    FileUploadCandidate,
    FileUploadPolicy,
    InputSecurityDecisionStatus,
    InputSecurityIssueCode,
    ReportRenderSecurityPolicy,
    UrlFetchCandidate,
    UrlFetchHop,
    UrlFetchPolicy,
    default_report_security_headers,
)
from serenity_alpha_lab.application.report_delivery import ReportDeliveryError, ResearchReportPagePresenter
from serenity_alpha_lab.evidence.report_renderer import (
    RenderedResearchReport,
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


NOW = datetime(2026, 7, 31, 9, 30, tzinfo=UTC)
HASH_A = "sha256:" + "a" * 64
DATASET_VERSIONS = {"adjusted_daily_bars": "dsv_" + "1" * 32}


def test_url_fetch_policy_blocks_ssrf_redirects_and_unsafe_response_metadata() -> None:
    policy = UrlFetchPolicy.default(
        allowed_hosts=("reports.example.com",),
        max_redirects=2,
        max_response_bytes=1_048_576,
    )

    allowed = policy.evaluate(
        UrlFetchCandidate(
            request=UrlFetchHop(
                url="https://reports.example.com/filing?id=1#frag",
                resolved_ip_addresses=("93.184.216.34",),
            ),
            response_content_type="text/html; charset=utf-8",
            response_size_bytes=2048,
        )
    )
    metadata_ip = policy.evaluate(
        UrlFetchCandidate(
            request=UrlFetchHop(
                url="https://reports.example.com/latest",
                resolved_ip_addresses=("169.254.169.254",),
            ),
            response_content_type="text/html",
            response_size_bytes=512,
        )
    )
    redirect_to_private = policy.evaluate(
        UrlFetchCandidate(
            request=UrlFetchHop(
                url="https://reports.example.com/start",
                resolved_ip_addresses=("93.184.216.34",),
            ),
            redirects=(
                UrlFetchHop(url="https://10.0.0.8/internal", resolved_ip_addresses=("10.0.0.8",)),
            ),
            response_content_type="text/html",
            response_size_bytes=512,
        )
    )
    too_many_redirects = policy.evaluate(
        UrlFetchCandidate(
            request=UrlFetchHop(
                url="https://reports.example.com/start",
                resolved_ip_addresses=("93.184.216.34",),
            ),
            redirects=(
                UrlFetchHop(url="https://reports.example.com/1", resolved_ip_addresses=("93.184.216.34",)),
                UrlFetchHop(url="https://reports.example.com/2", resolved_ip_addresses=("93.184.216.34",)),
                UrlFetchHop(url="https://reports.example.com/3", resolved_ip_addresses=("93.184.216.34",)),
            ),
            response_content_type="text/html",
            response_size_bytes=512,
        )
    )
    unsafe_scheme = policy.evaluate(
        UrlFetchCandidate(
            request=UrlFetchHop(url="file:///etc/passwd", resolved_ip_addresses=()),
            response_content_type="text/plain",
            response_size_bytes=10,
        )
    )
    over_limit = policy.evaluate(
        UrlFetchCandidate(
            request=UrlFetchHop(
                url="https://reports.example.com/large",
                resolved_ip_addresses=("93.184.216.34",),
            ),
            response_content_type="text/html",
            response_size_bytes=1_048_577,
        )
    )
    bad_content_type = policy.evaluate(
        UrlFetchCandidate(
            request=UrlFetchHop(
                url="https://reports.example.com/payload",
                resolved_ip_addresses=("93.184.216.34",),
            ),
            response_content_type="application/x-msdownload",
            response_size_bytes=512,
        )
    )

    assert allowed.status is InputSecurityDecisionStatus.ALLOWED
    assert allowed.canonical_url == "https://reports.example.com/filing?id=1"
    assert allowed.effective_url == "https://reports.example.com/filing?id=1"
    assert allowed.decision_hash.startswith("sha256:")
    assert allowed.issues == ()

    assert _issue_codes(metadata_ip) == {InputSecurityIssueCode.URL_PRIVATE_ADDRESS}
    assert _issue_codes(redirect_to_private) == {InputSecurityIssueCode.URL_PRIVATE_ADDRESS}
    assert _issue_codes(too_many_redirects) == {InputSecurityIssueCode.URL_REDIRECT_LIMIT_EXCEEDED}
    assert _issue_codes(unsafe_scheme) == {InputSecurityIssueCode.URL_SCHEME_FORBIDDEN}
    assert _issue_codes(over_limit) == {InputSecurityIssueCode.RESPONSE_TOO_LARGE}
    assert _issue_codes(bad_content_type) == {InputSecurityIssueCode.RESPONSE_CONTENT_TYPE_FORBIDDEN}
    assert metadata_ip.to_record()["status"] == "denied"


def test_file_upload_policy_limits_names_types_sizes_and_executable_signatures() -> None:
    policy = FileUploadPolicy.default(max_size_bytes=1024)

    allowed = policy.scan(
        FileUploadCandidate(
            filename="earnings-note.pdf",
            content_type="application/pdf",
            size_bytes=32,
            content_sample=b"%PDF-1.7\nsafe sample",
        )
    )
    path_traversal = policy.scan(
        FileUploadCandidate(
            filename="../evil.pdf",
            content_type="application/pdf",
            size_bytes=32,
            content_sample=b"%PDF-1.7\nsafe sample",
        )
    )
    html_payload = policy.scan(
        FileUploadCandidate(
            filename="report.html",
            content_type="text/html",
            size_bytes=128,
            content_sample=b"<script>alert(1)</script>",
        )
    )
    executable_signature = policy.scan(
        FileUploadCandidate(
            filename="report.pdf",
            content_type="application/pdf",
            size_bytes=128,
            content_sample=b"MZ\x90\x00payload",
        )
    )
    too_large = policy.scan(
        FileUploadCandidate(
            filename="dataset.csv",
            content_type="text/csv",
            size_bytes=1025,
            content_sample=b"date,value\n2026-07-31,1\n",
        )
    )

    assert allowed.status is InputSecurityDecisionStatus.ALLOWED
    assert allowed.sanitized_filename == "earnings-note.pdf"
    assert allowed.content_sha256.startswith("sha256:")
    assert allowed.issues == ()

    assert _issue_codes(path_traversal) == {InputSecurityIssueCode.FILENAME_UNSAFE}
    assert InputSecurityIssueCode.FILE_CONTENT_TYPE_FORBIDDEN in _issue_codes(html_payload)
    assert InputSecurityIssueCode.FILE_SIGNATURE_FORBIDDEN in _issue_codes(html_payload)
    assert _issue_codes(executable_signature) == {InputSecurityIssueCode.FILE_SIGNATURE_FORBIDDEN}
    assert _issue_codes(too_large) == {InputSecurityIssueCode.FILE_SIZE_EXCEEDED}


def test_report_render_security_policy_blocks_active_content_and_unsafe_links() -> None:
    rendered = _rendered_report(source_uri="https://reports.example.com/source/filing")
    policy = ReportRenderSecurityPolicy.default()

    allowed = policy.validate(rendered)
    unsafe = policy.validate(
        RenderedResearchReport(
            trusted_report=rendered.trusted_report,
            markdown=rendered.markdown,
            html='<article><script>alert(1)</script><a href="javascript:alert(1)" onclick="x()">x</a></article>',
        )
    )

    assert allowed.status is InputSecurityDecisionStatus.ALLOWED
    assert allowed.issues == ()
    assert unsafe.status is InputSecurityDecisionStatus.DENIED
    assert InputSecurityIssueCode.REPORT_ACTIVE_CONTENT in _issue_codes(unsafe)
    assert InputSecurityIssueCode.REPORT_UNSAFE_LINK in _issue_codes(unsafe)


def test_report_delivery_uses_security_headers_and_sanitizes_source_links() -> None:
    safe_page = ResearchReportPagePresenter().build(_rendered_report(source_uri="artifact://tenant/run/report@sha256"))
    unsafe_page = ResearchReportPagePresenter().build(_rendered_report(source_uri="javascript:alert(1)"))
    unsafe_html = RenderedResearchReport(
        trusted_report=_rendered_report(source_uri="https://reports.example.com/source/filing").trusted_report,
        markdown="# Unsafe\n",
        html='<article><img src="data:text/html;base64,PHNjcmlwdD4=" onerror="alert(1)"></article>',
    )

    headers = safe_page.headers
    record = safe_page.to_record()
    unsafe_record = unsafe_page.to_record()

    assert headers["Content-Security-Policy"] == default_report_security_headers()["Content-Security-Policy"]
    assert headers["X-Content-Type-Options"] == "nosniff"
    assert headers["Referrer-Policy"] == "no-referrer"
    assert headers["X-Frame-Options"] == "DENY"
    assert headers["Permissions-Policy"] == "camera=(), microphone=(), geolocation=()"
    assert record["evidence_lineage"][0]["source_link"] == "artifact://tenant/run/report@sha256"

    unsafe_evidence = unsafe_record["evidence_lineage"][0]
    assert "source_link" not in unsafe_evidence
    assert unsafe_evidence["source_link_security"]["status"] == "denied"
    assert unsafe_evidence["source_link_security"]["issues"][0]["code"] == "report_unsafe_link"

    with pytest.raises(ReportDeliveryError, match="unsafe report display html"):
        ResearchReportPagePresenter().build(unsafe_html)


def _rendered_report(*, source_uri: str) -> RenderedResearchReport:
    return TrustedResearchReportRenderer().render(_verified_report(source_uri=source_uri), context=_context())


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


def _verified_report(*, source_uri: str) -> ResearchReport:
    return ResearchReport(
        report_id="rpt_input_fetch_security",
        report_level=ResearchReportLevel.VERIFIED,
        decision_time=NOW,
        generated_at=NOW,
        evidence=[_metric_evidence(source_uri=source_uri)],
        citations=[_metric_citation()],
        claims=[_numeric_claim()],
        dataset_versions=DATASET_VERSIONS,
        run_id="run-report",
        trace_id="trace-report",
    )


def _metric_evidence(*, source_uri: str) -> EvidenceRecord:
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
            source_uri=source_uri,
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


def _issue_codes(decision: object) -> set[InputSecurityIssueCode]:
    return {issue.code for issue in decision.issues}  # type: ignore[attr-defined]
