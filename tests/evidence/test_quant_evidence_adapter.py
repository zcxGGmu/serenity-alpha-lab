from __future__ import annotations

import hashlib
import json
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

import pytest

from serenity_alpha_lab.domain.artifacts import ArtifactManifest, ArtifactRetentionTier
from serenity_alpha_lab.evidence.quant_adapter import QuantEvidenceAdapter, QuantEvidenceAdapterError
from serenity_alpha_lab.evidence.schema import EvidenceEvaluationScope, EvidenceKind, EvidenceTrustLevel
from serenity_alpha_lab.quant.backtest.metrics import (
    BacktestMetricFrequency,
    BacktestMetricRegistry,
    BacktestPerformanceMetricReport,
)
from serenity_alpha_lab.quant.backtest.audit import (
    BacktestBiasAuditPolicy,
    BacktestBiasAuditReport,
    BacktestBiasAuditStatus,
    BiasAuditRuleOutcome,
    BiasAuditRuleStatus,
)
from serenity_alpha_lab.quant.backtest.risk import (
    DeterministicRiskPolicy,
    RiskDecisionStatus,
    RiskPolicyResult,
    RiskRuleOutcome,
    RiskRuleStatus,
)
from serenity_alpha_lab.quant.factors import FactorDirection
from serenity_alpha_lab.quant.factors.evaluation import (
    FactorCorrelationMethod,
    FactorCoverageSummary,
    FactorEvaluationReport,
    FactorEvaluationSpec,
    FactorExposureMetric,
    FactorExposureSummary,
    FactorGroupReturnBucket,
    FactorGroupReturnSummary,
    FactorIcMetric,
    FactorIcSummary,
    FactorMonotonicityMetric,
    FactorTurnoverSummary,
    FutureReturnWindow,
)
from serenity_alpha_lab.quant.screening.pipeline import ScreenPipelineStage
from serenity_alpha_lab.quant.screening.snapshot import (
    ScreenExplanationStep,
    ScreenSnapshot,
    ScreenSnapshotResult,
    ScreenSnapshotStatus,
)


NOW = datetime(2026, 7, 26, 18, 0, tzinfo=UTC)
DATASET_VERSIONS = {
    "adjusted_daily_bars": "dsv_" + "a" * 32,
    "instrument_master": "dsv_" + "b" * 32,
}
SPEC_HASH = "sha256:" + "8" * 64


def test_adapter_converts_screen_and_factor_outputs_without_formal_relabeling() -> None:
    adapter = QuantEvidenceAdapter.default()
    screen = _screen_snapshot()
    screen_manifest = _manifest_for(screen.to_record(), schema_name=screen.schema_name, run_id=screen.run_id or "run")

    screen_record = adapter.from_screen_snapshot(
        screen,
        available_at=NOW,
        artifact_manifest=screen_manifest,
    )

    assert screen_record.evidence.kind is EvidenceKind.SCREEN_SNAPSHOT
    assert screen_record.evidence.evaluation_scope is EvidenceEvaluationScope.SCREENING
    assert screen_record.evidence.trust is EvidenceTrustLevel.AUTHORITATIVE
    assert screen_record.evidence.content_hash == "sha256:" + screen_manifest.sha256
    assert screen_record.evidence.artifact_id == screen_manifest.artifact_id
    assert screen_record.evidence.dataset_versions == DATASET_VERSIONS
    assert screen_record.body["results_by_instrument"]["600519.XSHG"]["rank"] == 1
    assert screen_record.evidence.metadata["llm_recompute_allowed"] is False

    screen_score = _citation_by_path(screen_record.citations, "body.results_by_instrument.600519.XSHG.final_score")
    assert screen_score.cited_value == 91.0
    assert screen_score.unit == "score"
    assert screen_score.formula_version == f"screen_definition:{screen.definition_version_id}"
    assert screen_score.artifact_hash == "sha256:" + screen_manifest.sha256

    factor_report = _factor_report()
    factor_manifest = _manifest_for(
        factor_report.to_record(),
        schema_name=factor_report.schema_name,
        run_id=factor_report.spec.run_id,
        stage_id=factor_report.spec.stage_id,
    )

    factor_record = adapter.from_factor_evaluation_report(
        factor_report,
        available_at=NOW,
        artifact_manifest=factor_manifest,
    )

    assert factor_record.evidence.kind is EvidenceKind.FACTOR_EVALUATION
    assert factor_record.evidence.evaluation_scope is EvidenceEvaluationScope.FACTOR_EVALUATION
    assert factor_record.evidence.dataset_versions == factor_report.spec.dataset_versions
    assert factor_record.evidence.formula_versions["metric_set"] == "factor_evaluation_metrics@1.0.0"
    assert factor_record.evidence.formula_versions["future_return_window"] == "forward_return_5d_v1"
    mean_ic = _citation_by_path(factor_record.citations, "body.ic_summary.mean_ic")
    assert mean_ic.cited_value == 0.42
    assert mean_ic.unit == "correlation"
    assert mean_ic.formula_version == "factor_evaluation_metrics@1.0.0"


def test_adapter_converts_backtest_metrics_and_risk_with_artifact_and_formula_trace() -> None:
    adapter = QuantEvidenceAdapter.default()
    metrics = _metrics_report()
    metrics_manifest = _manifest_for(
        metrics.to_record(),
        schema_name=metrics.schema_name,
        run_id=metrics.run_id,
        stage_id=metrics.stage_id,
    )

    metrics_record = adapter.from_backtest_performance_metrics(
        metrics,
        dataset_versions=DATASET_VERSIONS,
        available_at=NOW,
        artifact_manifest=metrics_manifest,
    )

    assert metrics_record.evidence.kind is EvidenceKind.BACKTEST_PERFORMANCE_METRICS
    assert metrics_record.evidence.evaluation_scope is EvidenceEvaluationScope.FORMAL_PORTFOLIO_BACKTEST
    assert metrics_record.evidence.source.schema_name == "quant.backtest.performance_metrics"
    assert metrics_record.evidence.formula_versions["cumulative_return"] == "cumulative_return@1.0.0"
    assert metrics_record.evidence.metadata["numeric_citation_count"] >= 6
    cumulative_return = _citation_by_path(metrics_record.citations, "body.returns.cumulative_return")
    assert cumulative_return.cited_value == "0.120000"
    assert cumulative_return.unit == "ratio"
    assert cumulative_return.formula_version == "cumulative_return@1.0.0"
    assert cumulative_return.dataset_versions == DATASET_VERSIONS

    risk = _risk_result()
    risk_manifest = _manifest_for(
        risk.to_record(),
        schema_name=risk.schema_name,
        run_id=risk.run_id,
        stage_id=risk.stage_id,
    )

    risk_record = adapter.from_risk_policy_result(
        risk,
        dataset_versions=DATASET_VERSIONS,
        available_at=NOW,
        artifact_manifest=risk_manifest,
    )

    assert risk_record.evidence.kind is EvidenceKind.RISK_POLICY_RESULT
    assert risk_record.evidence.evaluation_scope is EvidenceEvaluationScope.FORMAL_PORTFOLIO_BACKTEST
    assert risk_record.evidence.formula_versions == {
        "policy": "risk_policy.cn_a_share@1.0.0",
        "evaluator": "cn_a_share_deterministic_risk_policy@1.0.0",
    }
    assert risk_record.body["agent_override_allowed"] is False
    assert _citation_by_path(risk_record.citations, "body.status").cited_value == "pass"

    audit = _audit_report()
    audit_manifest = _manifest_for(
        audit.to_record(),
        schema_name=audit.schema_name,
        run_id=audit.run_id,
        stage_id=audit.stage_id,
    )

    audit_record = adapter.from_backtest_bias_audit_report(
        audit,
        dataset_versions=DATASET_VERSIONS,
        available_at=NOW,
        artifact_manifest=audit_manifest,
    )

    assert audit_record.evidence.kind is EvidenceKind.BACKTEST_BIAS_AUDIT
    assert audit_record.evidence.evaluation_scope is EvidenceEvaluationScope.FORMAL_PORTFOLIO_BACKTEST
    assert audit_record.evidence.formula_versions == {
        "policy": "bias_audit.cn_a_share@1.0.0",
        "auditor": "cn_a_share_backtest_bias_auditor@1.0.0",
    }
    assert audit_record.body["agent_strong_conclusion_allowed"] is True
    assert _citation_by_path(audit_record.citations, "body.status").cited_value == "pass"


def test_adapter_requires_artifact_manifest_for_quant_evidence_traceability() -> None:
    with pytest.raises(QuantEvidenceAdapterError, match="artifact_manifest"):
        QuantEvidenceAdapter.default().from_backtest_performance_metrics(
            _metrics_report(),
            dataset_versions=DATASET_VERSIONS,
            available_at=NOW,
            artifact_manifest=None,
        )


def _screen_snapshot() -> ScreenSnapshot:
    return ScreenSnapshot(
        pipeline_snapshot_id="sps_" + "1" * 32,
        definition_version_id="sdv_" + "2" * 32,
        as_of=date(2026, 7, 25),
        dataset_versions=DATASET_VERSIONS,
        results=(
            ScreenSnapshotResult(
                instrument_id="600519.XSHG",
                status=ScreenSnapshotStatus.PASSED,
                rank=1,
                final_score=91.0,
                scores={"l4_final": 91.0},
                factor_contributions={"quality": 88.0},
                reason_codes=("passed",),
                summary="passed deterministic screen",
                explanation_steps=(
                    ScreenExplanationStep(
                        stage=ScreenPipelineStage.L4_FINAL,
                        rule_id="passed",
                        reason="passed deterministic screen",
                        scores={"l4_final": 91.0},
                    ),
                ),
            ),
            ScreenSnapshotResult(
                instrument_id="000001.XSHE",
                status=ScreenSnapshotStatus.FAILED,
                failed_stage=ScreenPipelineStage.L2_FACTOR,
                explanation_steps=(
                    ScreenExplanationStep(
                        stage=ScreenPipelineStage.L2_FACTOR,
                        rule_id="missing_factor",
                        reason="missing factor values",
                    ),
                ),
            ),
        ),
        created_at=NOW,
        trace_id="trace-screen",
        run_id="run-screen",
        stage_id="stage-screen",
    )


def _factor_report() -> FactorEvaluationReport:
    spec = FactorEvaluationSpec(
        run_id="run-factor",
        stage_id="stage-factor",
        factor_definition_id="quality",
        factor_version_id="fdv_" + "3" * 32,
        dataset_versions={
            "factor_values": "dsv_" + "4" * 32,
            "forward_returns": "dsv_" + "5" * 32,
            "instrument_master": "dsv_" + "6" * 32,
        },
        future_return_window=FutureReturnWindow(
            horizon=5,
            return_field="forward_return_5d",
            version="forward_return_5d_v1",
        ),
        factor_direction=FactorDirection.HIGHER_IS_BETTER,
        correlation_method=FactorCorrelationMethod.SPEARMAN,
    )
    return FactorEvaluationReport(
        spec=spec,
        coverage=FactorCoverageSummary(10, 10, 9, 9, 1, 0),
        ic_by_date=(FactorIcMetric(date(2026, 1, 2), 9, 0.40, "spearman"),),
        ic_summary=FactorIcSummary(0.42, 0.05, 8.4, 252, 1, 9),
        group_return_summary=FactorGroupReturnSummary(
            (FactorGroupReturnBucket(1, 0.01, 3), FactorGroupReturnBucket(2, 0.03, 3)),
            0.02,
        ),
        monotonicity=FactorMonotonicityMetric(0.9, 0.9, "spearman", 2),
        turnover_by_period=(),
        turnover_summary=FactorTurnoverSummary(0.2, 1),
        exposure_summary=FactorExposureSummary({"beta": FactorExposureMetric("beta", 9, 1.1, 0.2)}),
        warnings=(),
    )


def _metrics_report() -> BacktestPerformanceMetricReport:
    return BacktestPerformanceMetricReport(
        report_id="metrics-run",
        spec_id="formal_cn_quality_momentum_v1",
        spec_hash=SPEC_HASH,
        run_id="run-backtest",
        stage_id="stage-metrics",
        sample_start=date(2026, 1, 2),
        sample_end=date(2026, 1, 8),
        frequency=BacktestMetricFrequency.DAILY,
        annualization_days=252,
        risk_free_rate=Decimal("0.0300"),
        period_count=4,
        metric_registry=BacktestMetricRegistry.default(),
        returns={"cumulative_return": Decimal("0.120000")},
        risk={"sharpe_ratio": Decimal("1.250000")},
        drawdown={"max_drawdown": Decimal("0.050000")},
        trading={"turnover_rate": Decimal("0.250000")},
        costs={"cost_ratio": Decimal("0.004500")},
        benchmark={"information_ratio": Decimal("0.800000")},
        industry_exposure={"average_weights": {"consumer": Decimal("0.500000")}},
    )


def _risk_result() -> RiskPolicyResult:
    return RiskPolicyResult(
        result_id="risk-run",
        spec_id="formal_cn_quality_momentum_v1",
        spec_hash=SPEC_HASH,
        run_id="run-backtest",
        stage_id="stage-risk",
        policy=DeterministicRiskPolicy(
            policy_id="risk_policy.cn_a_share",
            policy_version="1.0.0",
        ),
        status=RiskDecisionStatus.PASS,
        outcomes=(
            RiskRuleOutcome(
                rule_id="max_drawdown",
                status=RiskRuleStatus.PASS,
                message="within limit",
                observed_value=Decimal("0.0500"),
                limit_value=Decimal("0.2000"),
            ),
        ),
    )


def _audit_report() -> BacktestBiasAuditReport:
    return BacktestBiasAuditReport(
        report_id="audit-run",
        spec_id="formal_cn_quality_momentum_v1",
        spec_hash=SPEC_HASH,
        run_id="run-backtest",
        stage_id="stage-audit",
        policy=BacktestBiasAuditPolicy(
            policy_id="bias_audit.cn_a_share",
            policy_version="1.0.0",
        ),
        status=BacktestBiasAuditStatus.PASS,
        outcomes=(
            BiasAuditRuleOutcome(
                rule_id="lookahead_bias",
                status=BiasAuditRuleStatus.PASS,
                message="no lookahead detected",
                observed_value=Decimal("1.0000"),
                limit_value=Decimal("0.8000"),
            ),
        ),
        eligible_for_ranking=True,
        agent_strong_conclusion_allowed=True,
    )


def _manifest_for(
    body: dict[str, Any],
    *,
    schema_name: str,
    run_id: str,
    stage_id: str | None = None,
) -> ArtifactManifest:
    payload = json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    digest = hashlib.sha256(payload).hexdigest()
    return ArtifactManifest.create(
        sha256=digest,
        size_bytes=len(payload),
        schema_name=schema_name,
        schema_version="1.0.0",
        content_type="application/vnd.serenity.quant.evidence-test+json",
        produced_by_run_id=run_id,
        produced_by_stage_id=stage_id,
        retention_tier=ArtifactRetentionTier.STANDARD,
        created_at=NOW,
    )


def _citation_by_path(citations, path: str):
    for citation in citations:
        if citation.evidence_field_path == path:
            return citation
    raise AssertionError(f"missing citation path: {path}")
