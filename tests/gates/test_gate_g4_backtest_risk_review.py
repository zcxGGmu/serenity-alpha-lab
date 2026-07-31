from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from serenity_alpha_lab.application.backtest_api import FORMAL_BACKTEST_API_ROUTES, FORMAL_BACKTEST_TASK_TYPE
from serenity_alpha_lab.application.backtest_run import (
    BACKTEST_RUN_TYPE,
    BacktestRunCodeState,
    BacktestRunMode,
    BacktestRunOrchestrator,
    BacktestRunRequest,
    InMemoryBacktestRunRepository,
)
from serenity_alpha_lab.domain.artifacts import ArtifactManifest, ArtifactRetentionTier
from serenity_alpha_lab.quant.backtest.artifacts import (
    BacktestArtifactBundle,
    BacktestArtifactKind,
    BacktestArtifactState,
    BacktestOutputArtifact,
)
from serenity_alpha_lab.quant.backtest.audit import (
    BacktestBiasAuditPolicy,
    BacktestBiasAuditReport,
    BacktestBiasAuditStatus,
    BiasAuditRuleOutcome,
    BiasAuditRuleStatus,
)
from serenity_alpha_lab.quant.backtest.golden import BacktestGoldenRunner, default_backtest_golden_fixture
from serenity_alpha_lab.quant.backtest.risk import (
    DeterministicRiskPolicy,
    RiskDecisionStatus,
    RiskPolicyResult,
    RiskRuleOutcome,
    RiskRuleStatus,
)
from serenity_alpha_lab.repositories.local_artifact_store import LocalArtifactStore


NOW = datetime(2026, 7, 26, 18, 0, tzinfo=UTC)
TRACE_ID = "trace-gate-g4-backtest-risk"
EXPECTED_GOLDEN_HASH = "sha256:76e9c93b060bdec6cc05497a477efa2de870168f20d18f349e2a78393d4e78d1"


def test_gate_g4_review_document_approves_p4_evidence_without_expanding_scope() -> None:
    review_path = Path("docs/gate-g4-backtest-risk-review.md")
    text = review_path.read_text(encoding="utf-8")

    required_phrases = [
        "GO with accepted risks",
        "APPROVED FOR P5",
        "SAL-P4-001",
        "SAL-P4-021",
        "SignalEvaluationEngine",
        "Factor Evaluation",
        "formal portfolio backtest",
        "BacktestSpec",
        "BacktestArtifact",
        "Qlib Adapter",
        "Order State Machine",
        "Portfolio Ledger",
        "CostModel",
        "A-share execution",
        "Corporate Action Ledger",
        "RiskPolicy",
        "Backtest Bias Audit",
        "Backtest Performance Metrics",
        "BacktestRun",
        "Resource Control",
        "Backtest Golden",
        "Formal Backtest API",
        "Quant Lab",
        "Dataset Version",
        "Run/Stage/Event",
        "Artifact",
        "不启动 Evidence Agent",
        "不调用真实 Provider/LLM",
        "不启动 Worker loop",
        "不启动 Qlib runtime",
        "legacy /api/v1/backtest/*",
    ]

    missing = [phrase for phrase in required_phrases if phrase not in text]
    assert missing == []
    assert "Signal Evaluation、Factor Evaluation 和 Portfolio Backtest" in text
    assert "Qlib internal evidence、Dataset conversion artifacts、Screen results、AlphaSift T+N evaluation" in text


def test_gate_g4_executable_contract_links_golden_run_risk_api_and_runtime_boundaries(
    tmp_path: Path,
) -> None:
    store = LocalArtifactStore(tmp_path / "artifacts")
    golden = BacktestGoldenRunner(default_backtest_golden_fixture()).run()
    spec = golden.fixture.spec
    run_id = golden.ledger.run_id

    artifact_bundle = _artifact_bundle(store=store, golden=golden, trace_id=TRACE_ID)
    request = BacktestRunRequest(
        run_id=run_id,
        trace_id=TRACE_ID,
        idempotency_key="gate-g4:formal-backtest-golden",
        submitted_at=NOW,
        spec=spec,
        engine_evidence=_engine_evidence(spec_id=spec.spec_id, spec_hash=spec.spec_hash, run_id=run_id),
        ledger=golden.ledger,
        risk_result=_risk_result(spec_id=spec.spec_id, spec_hash=spec.spec_hash, run_id=run_id),
        audit_report=_audit_report(spec_id=spec.spec_id, spec_hash=spec.spec_hash, run_id=run_id),
        metrics_report=golden.metrics_report,
        artifact_bundle=artifact_bundle,
        requested_mode=BacktestRunMode.FORMAL,
        code_state=BacktestRunCodeState.CLEAN,
        metadata={"gate": "G4", "golden_result_hash": golden.result_hash},
    )
    record = BacktestRunOrchestrator(
        repository=InMemoryBacktestRunRepository(),
        artifact_store=store,
    ).finalize(request)
    summary = json.loads(store.get_bytes(record.summary_artifact.artifact_id))
    route_paths = {(route.method, route.path) for route in FORMAL_BACKTEST_API_ROUTES}

    assert golden.result_hash == EXPECTED_GOLDEN_HASH
    assert golden.fixture_summary["production_backtest_promoted"] is False
    assert set(golden.covered_rules) == {
        "fees",
        "t_plus_one",
        "suspension",
        "limit_up_down",
        "cash_dividend",
        "rebalance",
        "chunked_vs_full_read",
    }
    assert golden.metrics_report.returns["cumulative_return"] == Decimal("0.024660")
    assert golden.ledger.reconciliation_record()["equity_formula"] == (
        "cash + position_market_value + receivables - payables"
    )

    assert record.status == "succeeded"
    assert record.effective_mode is BacktestRunMode.FORMAL
    assert record.eligible_for_ranking is True
    assert record.schema_name == "quant.backtest_run"
    assert [stage.name for stage in record.stages] == [
        "spec",
        "engine",
        "ledger",
        "risk",
        "audit",
        "metrics",
        "artifacts",
        "summary",
    ]
    assert artifact_bundle.state is BacktestArtifactState.FORMAL
    assert set(artifact_bundle.outputs) == set(BacktestArtifactKind)

    assert summary["lifecycle"]["run_type"] == BACKTEST_RUN_TYPE
    assert summary["layer_outputs"]["risk"]["status"] == "pass"
    assert summary["layer_outputs"]["audit"]["eligible_for_ranking"] is True
    assert summary["layer_outputs"]["metrics"]["metric_set_version"] == golden.metrics_report.metric_set_version
    assert summary["runtime"] == {
        "resource_controls_started": False,
        "api_route_started": False,
        "quant_lab_started": False,
        "worker_loop_started": False,
        "real_provider_calls_started": False,
        "real_llm_calls_started": False,
    }

    assert FORMAL_BACKTEST_TASK_TYPE == "quant.backtest.run"
    assert ("POST", "/api/v1/quant/backtest-runs") in route_paths
    assert ("GET", "/api/v1/quant/backtest-runs/{run_id}/metrics") in route_paths
    assert all("/api/v1/backtest" not in route.path for route in FORMAL_BACKTEST_API_ROUTES)
    assert all("signal" not in route.operation_id.lower() for route in FORMAL_BACKTEST_API_ROUTES)
    assert "legacy_signal_evaluation" not in json.dumps(record.to_record(), sort_keys=True)
    assert "latest" not in json.dumps(spec.to_record(), sort_keys=True)


def _engine_evidence(*, spec_id: str, spec_hash: str, run_id: str) -> dict[str, object]:
    return {
        "schema_name": "integration.qlib.quant_engine_run_report",
        "schema_version": "1.0.0",
        "report_id": "qer_gate_g4_formal_backtest",
        "engine_scope": "qlib_quant_engine_adapter",
        "adapter_version": "integration.qlib.quant_engine_adapter@1.0.0",
        "spec_id": spec_id,
        "spec_hash": spec_hash,
        "operation_count": 3,
        "operations": ["train", "predict", "backtest"],
        "step_artifact_ids": ["art_gate_g4_train", "art_gate_g4_predict", "art_gate_g4_backtest"],
        "trace": {
            "trace_id": TRACE_ID,
            "run_id": run_id,
            "stage_id": "stage-gate-g4-engine",
        },
        "runtime": {
            "formal_portfolio_backtest_started": False,
            "ledger_started": False,
            "risk_started": False,
            "worker_loop_started": False,
        },
    }


def _risk_result(*, spec_id: str, spec_hash: str, run_id: str) -> RiskPolicyResult:
    return RiskPolicyResult(
        result_id="risk_gate_g4_pass",
        spec_id=spec_id,
        spec_hash=spec_hash,
        run_id=run_id,
        stage_id="stage-gate-g4-risk",
        policy=DeterministicRiskPolicy(
            policy_id="cn_a_share_deterministic_risk",
            policy_version="1.0.0",
        ),
        status=RiskDecisionStatus.PASS,
        outcomes=(
            RiskRuleOutcome(
                rule_id="risk_profile_available",
                status=RiskRuleStatus.PASS,
                message="Gate G4 fixture has explicit risk evidence.",
            ),
        ),
    )


def _audit_report(*, spec_id: str, spec_hash: str, run_id: str) -> BacktestBiasAuditReport:
    return BacktestBiasAuditReport(
        report_id="audit_gate_g4_pass",
        spec_id=spec_id,
        spec_hash=spec_hash,
        run_id=run_id,
        stage_id="stage-gate-g4-audit",
        policy=BacktestBiasAuditPolicy(
            policy_id="cn_a_share_bias_audit",
            policy_version="1.0.0",
        ),
        status=BacktestBiasAuditStatus.PASS,
        outcomes=(
            BiasAuditRuleOutcome(
                rule_id="lookahead_bias",
                status=BiasAuditRuleStatus.PASS,
                message="Gate G4 fixture keeps decision-time data availability explicit.",
            ),
        ),
        eligible_for_ranking=True,
        agent_strong_conclusion_allowed=True,
    )


def _artifact_bundle(
    *,
    store: LocalArtifactStore,
    golden,
    trace_id: str,
) -> BacktestArtifactBundle:
    spec = golden.fixture.spec
    return BacktestArtifactBundle(
        run_id=golden.ledger.run_id,
        stage_id="stage-gate-g4-artifacts",
        spec_id=spec.spec_id,
        spec_hash=spec.spec_hash,
        dataset_versions=spec.dataset.dataset_versions,
        state=BacktestArtifactState.FORMAL,
        outputs=_required_outputs(store=store, golden=golden),
        created_at=NOW,
        trace_id=trace_id,
    )


def _required_outputs(*, store: LocalArtifactStore, golden) -> tuple[BacktestOutputArtifact, ...]:
    output_specs = (
        (BacktestArtifactKind.ORDERS, "quant.backtest.orders", golden.order_records),
        (
            BacktestArtifactKind.EXECUTIONS,
            "quant.backtest.executions",
            [result.to_record() for result in golden.execution_results],
        ),
        (
            BacktestArtifactKind.POSITIONS,
            "quant.backtest.positions",
            list(golden.ledger.to_record()["position_lots"]),
        ),
        (BacktestArtifactKind.CASH, "quant.backtest.cash", [golden.ledger.reconciliation_record()]),
        (
            BacktestArtifactKind.EQUITY_CURVE,
            "quant.backtest.equity_curve",
            [point.to_record() for point in golden.equity_curve],
        ),
        (BacktestArtifactKind.METRICS, "quant.backtest.metrics", [golden.metrics_report.to_record()]),
        (
            BacktestArtifactKind.AUDIT,
            "quant.backtest.audit",
            [{"status": "pass", "rule_ids": ["lookahead_bias", "survivorship_bias", "pit_data_availability"]}],
        ),
    )
    return tuple(
        _output_artifact(store=store, kind=kind, schema_name=schema_name, rows=rows)
        for kind, schema_name, rows in output_specs
    )


def _output_artifact(
    *,
    store: LocalArtifactStore,
    kind: BacktestArtifactKind,
    schema_name: str,
    rows: list[object] | tuple[object, ...],
) -> BacktestOutputArtifact:
    manifest = _artifact_manifest(store=store, schema_name=schema_name, payload=list(rows))
    return BacktestOutputArtifact(
        kind=kind,
        schema_name=schema_name,
        schema_version="1.0.0",
        artifact_manifest=manifest,
        content_hash="sha256:" + manifest.sha256,
        row_count=len(rows),
        partition_keys=("trade_date",) if kind in {BacktestArtifactKind.ORDERS, BacktestArtifactKind.EXECUTIONS} else (),
    )


def _artifact_manifest(*, store: LocalArtifactStore, schema_name: str, payload: object) -> ArtifactManifest:
    return store.put_bytes(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8"),
        schema_name=schema_name,
        schema_version="1.0.0",
        content_type="application/vnd.serenity.quant.backtest-table+json",
        produced_by_run_id="run-backtest-golden-fixture",
        produced_by_stage_id="stage-gate-g4-artifacts",
        retention_tier=ArtifactRetentionTier.STANDARD,
        created_at=NOW,
    )
