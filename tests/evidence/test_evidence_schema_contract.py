from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

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
    quant_evidence_source_matrix,
)


NOW = datetime(2026, 7, 26, 15, 0, tzinfo=UTC)
HASH = "sha256:" + "a" * 64


def test_evidence_record_declares_required_schema_fields_and_json_schema() -> None:
    evidence = EvidenceRecord(
        evidence_id="ev_screen_snapshot_001",
        kind=EvidenceKind.SCREEN_SNAPSHOT,
        evaluation_scope=EvidenceEvaluationScope.SCREENING,
        title="Screen snapshot passed rows",
        summary="ScreenSnapshot includes ranked passed and failed rows.",
        source=EvidenceSource(
            source_id="ssn_11111111111111111111111111111111",
            source_type="artifact",
            schema_name="quant.screen_snapshot",
            schema_version="1.0.0",
        ),
        available_at=NOW,
        content_hash=HASH,
        trust=EvidenceTrustLevel.AUTHORITATIVE,
        dataset_versions={"universe": "dsv_" + "1" * 32},
        run_id="run-screen",
        stage_id="stage-screen",
        artifact_id="art_screen",
        artifact_hash=HASH,
    )

    record = evidence.to_record()
    assert record["schema_name"] == "research.evidence"
    assert record["schema_version"] == "1.0.0"
    assert record["source"]["source"] == "artifact"
    assert record["available_at"] == NOW.isoformat()
    assert record["content_hash"] == HASH
    assert record["trust"] == "authoritative"
    assert record["dataset_versions"] == {"universe": "dsv_" + "1" * 32}
    assert "properties" in EvidenceRecord.model_json_schema()


def test_evidence_rejects_latest_dataset_and_screen_as_formal_backtest() -> None:
    base = {
        "evidence_id": "ev_bad_scope",
        "kind": EvidenceKind.SCREEN_SNAPSHOT,
        "evaluation_scope": EvidenceEvaluationScope.FORMAL_PORTFOLIO_BACKTEST,
        "title": "Bad formal label",
        "summary": "Screen result is not a formal portfolio backtest.",
        "source": EvidenceSource(
            source_id="ssn_22222222222222222222222222222222",
            source_type="artifact",
            schema_name="quant.screen_snapshot",
            schema_version="1.0.0",
        ),
        "available_at": NOW,
        "content_hash": HASH,
        "trust": EvidenceTrustLevel.AUTHORITATIVE,
        "dataset_versions": {"universe": "dsv_" + "2" * 32},
    }

    with pytest.raises(ValidationError, match="formal portfolio backtest"):
        EvidenceRecord(**base)

    latest_payload = dict(base)
    latest_payload["evaluation_scope"] = EvidenceEvaluationScope.SCREENING
    latest_payload["dataset_versions"] = {"universe": "latest"}
    with pytest.raises(ValidationError, match="concrete Dataset Version"):
        EvidenceRecord(**latest_payload)


def test_numeric_claim_requires_citations_unit_formula_and_deterministic_policy() -> None:
    with pytest.raises(ValidationError, match="citation_ids"):
        ResearchClaim(
            claim_id="cl_no_citation",
            kind=ClaimKind.NUMERIC_METRIC,
            statement="The backtest cumulative return was 2.466%.",
            verification_status=ClaimVerificationStatus.VERIFIED,
            citation_ids=[],
            value="0.024660",
            unit="ratio",
            formula_version="cumulative_return@1.0.0",
            computation_policy=ClaimComputationPolicy.DETERMINISTIC_EVIDENCE,
        )

    with pytest.raises(ValidationError, match="LLM"):
        ResearchClaim(
            claim_id="cl_llm_numeric",
            kind=ClaimKind.NUMERIC_METRIC,
            statement="The backtest cumulative return was 2.466%.",
            verification_status=ClaimVerificationStatus.VERIFIED,
            citation_ids=["cit_metric"],
            value="0.024660",
            unit="ratio",
            formula_version="cumulative_return@1.0.0",
            computation_policy=ClaimComputationPolicy.LLM_NARRATIVE,
        )


def test_report_validates_citation_graph_and_decision_time() -> None:
    evidence = EvidenceRecord(
        evidence_id="ev_metric",
        kind=EvidenceKind.BACKTEST_PERFORMANCE_METRICS,
        evaluation_scope=EvidenceEvaluationScope.FORMAL_PORTFOLIO_BACKTEST,
        title="Backtest metric report",
        summary="Cumulative return is sourced from BacktestPerformanceMetricReport.",
        source=EvidenceSource(
            source_id="btm_metric_report",
            source_type="artifact",
            schema_name="quant.backtest.performance_metrics",
            schema_version="1.0.0",
        ),
        available_at=NOW,
        content_hash=HASH,
        trust=EvidenceTrustLevel.AUTHORITATIVE,
        dataset_versions={"bars": "dsv_" + "3" * 32},
        run_id="run-backtest",
        stage_id="stage-metrics",
        artifact_id="art_metrics",
        artifact_hash=HASH,
    )
    citation = ReportCitation(
        citation_id="cit_metric",
        evidence_id=evidence.evidence_id,
        evidence_field_path="metrics.cumulative_return",
        cited_value="0.024660",
        unit="ratio",
        formula_version="cumulative_return@1.0.0",
        artifact_hash=HASH,
    )
    claim = ResearchClaim(
        claim_id="cl_metric",
        kind=ClaimKind.NUMERIC_METRIC,
        statement="The formal portfolio backtest cumulative return was 2.466%.",
        verification_status=ClaimVerificationStatus.VERIFIED,
        citation_ids=[citation.citation_id],
        value="0.024660",
        unit="ratio",
        formula_version="cumulative_return@1.0.0",
        computation_policy=ClaimComputationPolicy.DETERMINISTIC_EVIDENCE,
    )

    report = ResearchReport(
        report_id="rpt_verified",
        report_level=ResearchReportLevel.VERIFIED,
        decision_time=NOW,
        evidence=[evidence],
        citations=[citation],
        claims=[claim],
        dataset_versions={"bars": "dsv_" + "3" * 32},
    )

    assert report.to_record()["report_level"] == "verified"
    assert report.to_record()["claims"][0]["citation_ids"] == ["cit_metric"]

    stale = evidence.model_copy(update={"available_at": datetime(2026, 7, 27, 9, 30, tzinfo=UTC)})
    with pytest.raises(ValidationError, match="available_at"):
        ResearchReport(
            report_id="rpt_stale",
            report_level=ResearchReportLevel.VERIFIED,
            decision_time=NOW,
            evidence=[stale],
            citations=[citation],
            claims=[claim],
            dataset_versions={"bars": "dsv_" + "3" * 32},
        )


def test_quant_evidence_source_matrix_freezes_p3_p4_mapping_and_excludes_legacy() -> None:
    matrix = quant_evidence_source_matrix()
    kinds = {row["kind"] for row in matrix}

    assert "screen_snapshot" in kinds
    assert "factor_evaluation" in kinds
    assert "backtest_run_summary" in kinds
    assert "backtest_artifact_bundle" in kinds
    assert "risk_policy_result" in kinds
    assert "backtest_bias_audit" in kinds
    assert "backtest_performance_metrics" in kinds
    assert "formal_backtest_api_record" in kinds
    assert "quant_lab_lineage" in kinds
    assert "legacy_signal_evaluation" not in kinds
    assert "qlib_internal_evidence" not in kinds
