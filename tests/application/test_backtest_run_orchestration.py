from __future__ import annotations

import ast
import json
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from serenity_alpha_lab.application.backtest_run import (
    BACKTEST_RUN_ORCHESTRATOR_CONTRACT_VERSION,
    BacktestRunCodeState,
    BacktestRunMode,
    BacktestRunOrchestrator,
    BacktestRunOrchestratorError,
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
from serenity_alpha_lab.quant.backtest.ledger import PortfolioLedger
from serenity_alpha_lab.quant.backtest.metrics import (
    BacktestMetricFrequency,
    BacktestMetricRegistry,
    BacktestPerformanceMetricReport,
)
from serenity_alpha_lab.quant.backtest.risk import (
    DeterministicRiskPolicy,
    RiskDecisionStatus,
    RiskPolicyResult,
    RiskRuleOutcome,
    RiskRuleStatus,
)
from serenity_alpha_lab.quant.backtest.spec import (
    BacktestCostSpec,
    BacktestDatasetSpec,
    BacktestExecutionSpec,
    BacktestRiskSpec,
    BacktestSpec,
    BacktestStrategySpec,
    BacktestUniverseSpec,
)
from serenity_alpha_lab.repositories.local_artifact_store import LocalArtifactStore


NOW = datetime(2026, 7, 26, 10, 30, tzinfo=UTC)
RUN_ID = "run-backtest-orchestration"
TRACE_ID = "trace-backtest-orchestration"
SPEC_HASH_CODE = "sha256:" + "8" * 64
PATCH_HASH = "sha256:" + "9" * 64
SCREEN_DEFINITION_VERSION = "sdv_" + "1" * 32
SCREEN_SNAPSHOT_ID = "ssn_" + "2" * 32
FACTOR_VERSION = "fdv_" + "3" * 32


def test_backtest_run_orchestrates_stage_chain_and_publishes_compact_summary(tmp_path: Path) -> None:
    store = LocalArtifactStore(tmp_path / "artifacts")
    spec = _formal_backtest_spec()
    orchestrator = BacktestRunOrchestrator(
        repository=InMemoryBacktestRunRepository(),
        artifact_store=store,
    )

    record = orchestrator.finalize(_request(store=store, spec=spec))

    assert record.contract_version == BACKTEST_RUN_ORCHESTRATOR_CONTRACT_VERSION
    assert record.status == "succeeded"
    assert record.requested_mode is BacktestRunMode.FORMAL
    assert record.effective_mode is BacktestRunMode.FORMAL
    assert record.eligible_for_ranking is True
    assert record.reused_from_run_id is None
    assert record.spec_hash == spec.spec_hash
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
    assert all(stage.status == "completed" for stage in record.stages)
    assert record.lifecycle["status"] == "completed"
    assert record.lifecycle["events"][-1]["kind"] == "run.completed"
    assert record.summary_artifact.schema_name == "quant.backtest_run"

    payload = json.loads(store.get_bytes(record.summary_artifact.artifact_id))
    assert payload["status"] == "succeeded"
    assert payload["effective_mode"] == "formal"
    assert payload["spec"]["spec_hash"] == spec.spec_hash
    assert payload["engine_evidence"]["engine_scope"] == "qlib_quant_engine_adapter"
    assert payload["outputs"]["artifact_bundle"]["bundle_id"] == record.artifact_bundle.bundle_id
    assert payload["runtime"] == {
        "resource_controls_started": False,
        "api_route_started": False,
        "quant_lab_started": False,
        "worker_loop_started": False,
        "real_provider_calls_started": False,
        "real_llm_calls_started": False,
    }
    assert "dataframe" not in json.dumps(payload, sort_keys=True).lower()
    assert "rows" not in json.dumps(payload, sort_keys=True).lower()


def test_backtest_run_idempotency_replay_and_successful_reuse(tmp_path: Path) -> None:
    store = LocalArtifactStore(tmp_path / "artifacts")
    spec = _formal_backtest_spec()
    repository = InMemoryBacktestRunRepository()
    orchestrator = BacktestRunOrchestrator(repository=repository, artifact_store=store)

    first = orchestrator.finalize(_request(store=store, spec=spec, idempotency_key="idem-first"))
    replay = orchestrator.finalize(_request(store=store, spec=spec, idempotency_key="idem-first"))
    reused = orchestrator.finalize(_request(store=store, spec=spec, idempotency_key="idem-second", run_id="run-reuse"))

    assert replay.run_id == first.run_id
    assert replay.summary_artifact.artifact_id == first.summary_artifact.artifact_id
    assert reused.run_id == first.run_id
    assert reused.reused_from_run_id == first.run_id
    assert reused.idempotency_key == "idem-second"

    changed_spec = _formal_backtest_spec(spec_id="formal_cn_quality_momentum_v2")
    with pytest.raises(BacktestRunOrchestratorError, match="Idempotency-Key"):
        orchestrator.finalize(_request(store=store, spec=changed_spec, idempotency_key="idem-first"))


def test_backtest_run_dirty_code_rejects_or_downgrades_formal_mode(tmp_path: Path) -> None:
    store = LocalArtifactStore(tmp_path / "artifacts")
    spec = _formal_backtest_spec()
    orchestrator = BacktestRunOrchestrator(
        repository=InMemoryBacktestRunRepository(),
        artifact_store=store,
    )

    with pytest.raises(BacktestRunOrchestratorError, match="dirty code"):
        orchestrator.finalize(
            _request(
                store=store,
                spec=spec,
                code_state=BacktestRunCodeState.DIRTY,
                patch_hash=None,
            )
        )

    record = orchestrator.finalize(
        _request(
            store=store,
            spec=spec,
            idempotency_key="dirty-with-patch",
            run_id="run-dirty-downgrade",
            code_state=BacktestRunCodeState.DIRTY,
            patch_hash=PATCH_HASH,
        )
    )

    assert record.requested_mode is BacktestRunMode.FORMAL
    assert record.effective_mode is BacktestRunMode.PREVIEW
    assert record.eligible_for_ranking is False
    assert record.code_state is BacktestRunCodeState.DIRTY
    assert record.patch_hash == PATCH_HASH
    assert "dirty_code_downgraded_to_preview" in record.warning_codes


def test_backtest_run_rejects_cross_layer_mismatches_and_stays_inside_boundary(tmp_path: Path) -> None:
    store = LocalArtifactStore(tmp_path / "artifacts")
    spec = _formal_backtest_spec()
    orchestrator = BacktestRunOrchestrator(
        repository=InMemoryBacktestRunRepository(),
        artifact_store=store,
    )
    bad_engine_evidence = dict(_engine_evidence(spec=spec, run_id=RUN_ID))
    bad_engine_evidence["spec_hash"] = "sha256:" + "7" * 64

    with pytest.raises(BacktestRunOrchestratorError, match="engine evidence spec_hash"):
        orchestrator.finalize(_request(store=store, spec=spec, engine_evidence=bad_engine_evidence))

    bad_bundle = _artifact_bundle(
        store=store,
        spec=spec,
        run_id=RUN_ID,
        spec_hash="sha256:" + "6" * 64,
    )
    with pytest.raises(BacktestRunOrchestratorError, match="artifact bundle spec_hash"):
        orchestrator.finalize(_request(store=store, spec=spec, artifact_bundle=bad_bundle))

    blocked_risk = _risk_result(spec=spec, run_id=RUN_ID, status=RiskDecisionStatus.BLOCK)
    with pytest.raises(BacktestRunOrchestratorError, match="risk policy block"):
        orchestrator.finalize(_request(store=store, spec=spec, risk_result=blocked_risk))

    source = Path("src/serenity_alpha_lab/application/backtest_run.py").read_text()
    tree = ast.parse(source)
    imported_roots: set[str] = set()
    imported_modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_roots.update(alias.name.split(".")[0] for alias in node.names)
            imported_modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_roots.add(node.module.split(".")[0])
            imported_modules.add(node.module)

    assert not {"qlib", "pyqlib", "fastapi", "sqlalchemy", "litellm"}.intersection(imported_roots)
    assert all(not module.startswith(("src.", "api.", "bot.", "data_provider")) for module in imported_modules)


def _request(
    *,
    store: LocalArtifactStore,
    spec: BacktestSpec,
    idempotency_key: str = "idem-backtest-run",
    run_id: str = RUN_ID,
    engine_evidence: dict[str, object] | None = None,
    ledger: PortfolioLedger | None = None,
    risk_result: RiskPolicyResult | None = None,
    audit_report: BacktestBiasAuditReport | None = None,
    metrics_report: BacktestPerformanceMetricReport | None = None,
    artifact_bundle: BacktestArtifactBundle | None = None,
    code_state: BacktestRunCodeState = BacktestRunCodeState.CLEAN,
    patch_hash: str | None = None,
) -> BacktestRunRequest:
    return BacktestRunRequest(
        run_id=run_id,
        trace_id=TRACE_ID,
        idempotency_key=idempotency_key,
        submitted_at=NOW,
        spec=spec,
        engine_evidence=engine_evidence or _engine_evidence(spec=spec, run_id=run_id),
        ledger=ledger or _ledger(spec=spec, run_id=run_id),
        risk_result=risk_result or _risk_result(spec=spec, run_id=run_id),
        audit_report=audit_report or _audit_report(spec=spec, run_id=run_id),
        metrics_report=metrics_report or _metrics_report(spec=spec, run_id=run_id),
        artifact_bundle=artifact_bundle or _artifact_bundle(store=store, spec=spec, run_id=run_id),
        requested_mode=BacktestRunMode.FORMAL,
        code_state=code_state,
        patch_hash=patch_hash,
        engine_version="cn_a_share_backtest_run_orchestrator@1.0.0",
    )


def _engine_evidence(*, spec: BacktestSpec, run_id: str) -> dict[str, object]:
    return {
        "schema_name": "integration.qlib.quant_engine_run_report",
        "schema_version": "1.0.0",
        "report_id": "qer_formal_cn_quality_momentum",
        "engine_scope": "qlib_quant_engine_adapter",
        "adapter_version": "integration.qlib.quant_engine_adapter@1.0.0",
        "spec_id": spec.spec_id,
        "spec_hash": spec.spec_hash,
        "operation_count": 3,
        "operations": ["train", "predict", "backtest"],
        "step_artifact_ids": ["art_engine_train", "art_engine_predict", "art_engine_backtest"],
        "trace": {
            "trace_id": TRACE_ID,
            "run_id": run_id,
            "stage_id": "stage-engine",
        },
        "runtime": {
            "formal_portfolio_backtest_started": False,
            "ledger_started": False,
            "risk_started": False,
            "worker_loop_started": False,
        },
    }


def _ledger(*, spec: BacktestSpec, run_id: str) -> PortfolioLedger:
    return PortfolioLedger.open(
        run_id=run_id,
        stage_id="stage-ledger",
        spec_id=spec.spec_id,
        spec_hash=spec.spec_hash,
        base_currency="CNY",
        initial_cash=spec.initial_capital,
        event_id=f"led-initial-{run_id}",
        occurred_at=NOW,
    )


def _risk_result(
    *,
    spec: BacktestSpec,
    run_id: str,
    status: RiskDecisionStatus = RiskDecisionStatus.PASS,
) -> RiskPolicyResult:
    rule_status = RiskRuleStatus.BLOCK if status is RiskDecisionStatus.BLOCK else RiskRuleStatus.PASS
    return RiskPolicyResult(
        result_id=f"risk_{run_id}",
        spec_id=spec.spec_id,
        spec_hash=spec.spec_hash,
        run_id=run_id,
        stage_id="stage-risk",
        policy=DeterministicRiskPolicy(
            policy_id="cn_a_share_deterministic_risk",
            policy_version="1.0.0",
        ),
        status=status,
        outcomes=(
            RiskRuleOutcome(
                rule_id="risk_profile_available",
                status=rule_status,
                message="risk fixture",
            ),
        ),
    )


def _audit_report(
    *,
    spec: BacktestSpec,
    run_id: str,
    status: BacktestBiasAuditStatus = BacktestBiasAuditStatus.PASS,
) -> BacktestBiasAuditReport:
    rule_status = BiasAuditRuleStatus.BLOCK if status is BacktestBiasAuditStatus.INVALID else BiasAuditRuleStatus.PASS
    return BacktestBiasAuditReport(
        report_id=f"audit_{run_id}",
        spec_id=spec.spec_id,
        spec_hash=spec.spec_hash,
        run_id=run_id,
        stage_id="stage-audit",
        policy=BacktestBiasAuditPolicy(
            policy_id="cn_a_share_bias_audit",
            policy_version="1.0.0",
        ),
        status=status,
        outcomes=(
            BiasAuditRuleOutcome(
                rule_id="lookahead_bias",
                status=rule_status,
                message="audit fixture",
            ),
        ),
        eligible_for_ranking=status is not BacktestBiasAuditStatus.INVALID,
        agent_strong_conclusion_allowed=status is not BacktestBiasAuditStatus.INVALID,
    )


def _metrics_report(*, spec: BacktestSpec, run_id: str) -> BacktestPerformanceMetricReport:
    return BacktestPerformanceMetricReport(
        report_id=f"metrics_{run_id}",
        spec_id=spec.spec_id,
        spec_hash=spec.spec_hash,
        run_id=run_id,
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


def _artifact_bundle(
    *,
    store: LocalArtifactStore,
    spec: BacktestSpec,
    run_id: str,
    spec_hash: str | None = None,
    state: BacktestArtifactState = BacktestArtifactState.FORMAL,
) -> BacktestArtifactBundle:
    return BacktestArtifactBundle(
        run_id=run_id,
        stage_id="stage-artifacts",
        spec_id=spec.spec_id,
        spec_hash=spec_hash or spec.spec_hash,
        dataset_versions=spec.dataset.dataset_versions,
        state=state,
        outputs=_required_outputs(store=store, run_id=run_id),
        created_at=NOW,
        trace_id=TRACE_ID,
    )


def _required_outputs(*, store: LocalArtifactStore, run_id: str) -> tuple[BacktestOutputArtifact, ...]:
    specs = (
        (BacktestArtifactKind.ORDERS, "quant.backtest.orders", 2),
        (BacktestArtifactKind.EXECUTIONS, "quant.backtest.executions", 2),
        (BacktestArtifactKind.POSITIONS, "quant.backtest.positions", 2),
        (BacktestArtifactKind.CASH, "quant.backtest.cash", 2),
        (BacktestArtifactKind.EQUITY_CURVE, "quant.backtest.equity_curve", 5),
        (BacktestArtifactKind.METRICS, "quant.backtest.metrics", 1),
        (BacktestArtifactKind.AUDIT, "quant.backtest.audit", 1),
    )
    outputs: list[BacktestOutputArtifact] = []
    for kind, schema_name, row_count in specs:
        manifest = _artifact_manifest(store=store, run_id=run_id, name=kind.value, schema_name=schema_name)
        outputs.append(
            BacktestOutputArtifact(
                kind=kind,
                schema_name=schema_name,
                schema_version="1.0.0",
                artifact_manifest=manifest,
                content_hash="sha256:" + manifest.sha256,
                row_count=row_count,
                partition_keys=("trade_date",) if kind in {BacktestArtifactKind.ORDERS, BacktestArtifactKind.EXECUTIONS} else (),
            )
        )
    return tuple(outputs)


def _artifact_manifest(
    *,
    store: LocalArtifactStore,
    run_id: str,
    name: str,
    schema_name: str,
) -> ArtifactManifest:
    return store.put_bytes(
        json.dumps({"name": name}, sort_keys=True).encode("utf-8"),
        schema_name=schema_name,
        schema_version="1.0.0",
        content_type="application/vnd.serenity.quant.backtest-table+json",
        produced_by_run_id=run_id,
        produced_by_stage_id="stage-artifacts",
        retention_tier=ArtifactRetentionTier.STANDARD,
        created_at=NOW,
    )


def _formal_backtest_spec(*, spec_id: str = "formal_cn_quality_momentum_v1") -> BacktestSpec:
    dataset_versions = {
        "adjusted_daily_bars": "dsv_" + "a" * 32,
        "raw_daily_bars": "dsv_" + "b" * 32,
        "trading_calendar": "dsv_" + "c" * 32,
        "corporate_actions": "dsv_" + "d" * 32,
        "instrument_master": "dsv_" + "e" * 32,
    }
    dataset_hashes = {name: f"sha256:{index:064x}" for index, name in enumerate(sorted(dataset_versions), start=1)}
    return BacktestSpec(
        spec_id=spec_id,
        created_at=NOW,
        created_by_run_id=RUN_ID,
        dataset=BacktestDatasetSpec(dataset_versions=dataset_versions, dataset_hashes=dataset_hashes),
        universe=BacktestUniverseSpec(
            universe_version_id="dsv_" + "f" * 32,
            universe_name="cn_a_share_l0",
            as_of=date(2026, 7, 25),
            membership_policy="pit_membership_as_of_decision_time",
        ),
        strategy=BacktestStrategySpec(
            strategy_id="quality_momentum_weekly",
            strategy_version="1.0.0",
            strategy_kind="screen_snapshot_rebalance",
            source_commit="abcdef1234567890",
            code_hash=SPEC_HASH_CODE,
            screen_definition_version_id=SCREEN_DEFINITION_VERSION,
            screen_snapshot_id=SCREEN_SNAPSHOT_ID,
            factor_version_ids=(FACTOR_VERSION,),
        ),
        start_date=date(2026, 1, 1),
        end_date=date(2026, 6, 30),
        benchmark="000300.XSHG",
        currency="CNY",
        initial_capital=Decimal("100000.00"),
        cash_rate_bps=Decimal("150.0"),
        execution=BacktestExecutionSpec(
            signal_timing="after_close",
            execution_timing="next_open",
            signal_price_field="close",
            execution_price_field="open",
            rebalance_calendar="cn_a_share_trading_calendar",
            valuation_calendar="cn_a_share_trading_calendar",
            rebalance_frequency="weekly",
            settlement_lag_days=1,
            lot_size=100,
            random_seed=20260725,
        ),
        costs=BacktestCostSpec(
            commission_bps=Decimal("3.0"),
            min_commission=Decimal("5.00"),
            stamp_tax_bps=Decimal("10.0"),
            transfer_fee_bps=Decimal("0.2"),
            slippage_bps=Decimal("5.0"),
            impact_bps=Decimal("2.0"),
            max_participation_rate=Decimal("0.1000"),
        ),
        risk=BacktestRiskSpec(
            risk_policy_version="risk_policy.cn_a_share@1.0.0",
            max_weight_per_instrument=Decimal("0.1000"),
            max_weight_per_industry=Decimal("0.3000"),
            max_turnover_per_rebalance=Decimal("0.4000"),
            cash_buffer_pct=Decimal("0.0200"),
            liquidity_floor_amount=Decimal("1000000.00"),
        ),
        artifact_output_level="full_audit",
    )
