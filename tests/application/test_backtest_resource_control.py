from __future__ import annotations

import ast
import json
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from serenity_alpha_lab.application.backtest_resource_control import (
    BACKTEST_RUN_CHECKPOINT_SCHEMA_NAME,
    BACKTEST_RUN_RESOURCE_CONTROL_CONTRACT_VERSION,
    BacktestRunChildProcessSnapshot,
    BacktestRunChildProcessStatus,
    BacktestRunExecutionStatus,
    BacktestRunResourcePolicy,
    BacktestRunResourceSupervisor,
    InMemoryBacktestRunExecutionRepository,
)
from serenity_alpha_lab.application.backtest_run import (
    BacktestRunCodeState,
    BacktestRunMode,
    BacktestRunOrchestrator,
    BacktestRunRequest,
    InMemoryBacktestRunRepository,
)
from serenity_alpha_lab.domain.artifacts import ArtifactManifest, ArtifactRetentionTier
from serenity_alpha_lab.integrations.qlib.runtime_policy import default_qlib_runtime_policy
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


NOW = datetime(2026, 7, 26, 12, 0, tzinfo=UTC)
RUN_ID = "run-backtest-resource-control"
TRACE_ID = "trace-backtest-resource-control"
SPEC_HASH_CODE = "sha256:" + "8" * 64
SCREEN_DEFINITION_VERSION = "sdv_" + "1" * 32
SCREEN_SNAPSHOT_ID = "ssn_" + "2" * 32
FACTOR_VERSION = "fdv_" + "3" * 32


def test_supervisor_records_resource_policy_and_successfully_finalizes_child_result(tmp_path: Path) -> None:
    store = LocalArtifactStore(tmp_path / "artifacts")
    request = _request(store=store)
    supervisor = _supervisor(store=store)
    policy = BacktestRunResourcePolicy.from_qlib_runtime_policy(default_qlib_runtime_policy())

    started = supervisor.start(request=request, resource_policy=policy)
    record = supervisor.observe(
        RUN_ID,
        BacktestRunChildProcessSnapshot(
            process_id="pid-1001",
            status=BacktestRunChildProcessStatus.SUCCEEDED,
            observed_at=NOW + timedelta(seconds=10),
            stage_id="stage-summary",
            progress_pct=100,
            memory_peak_mb=512,
            output_size_bytes=2048,
            result_request=request,
        ),
    )

    assert started.status is BacktestRunExecutionStatus.RUNNING
    assert record.contract_version == BACKTEST_RUN_RESOURCE_CONTROL_CONTRACT_VERSION
    assert record.status is BacktestRunExecutionStatus.SUCCEEDED
    assert record.final_record is not None
    assert record.final_record.status == "succeeded"
    assert record.resource_policy.queue_name == "worker-quant"
    assert record.resource_policy.max_cpu_cores == 2
    assert record.resource_policy.max_memory_mb == 4096
    assert record.resource_policy.wall_clock_timeout_seconds == 3600
    assert record.to_record()["runtime"] == {
        "resource_controls_started": True,
        "api_route_started": False,
        "quant_lab_started": False,
        "evidence_agent_started": False,
        "worker_loop_started": False,
        "real_provider_calls_started": False,
        "real_llm_calls_started": False,
        "qlib_runtime_started": False,
    }


def test_supervisor_timeout_publishes_partial_checkpoint_and_never_succeeds(tmp_path: Path) -> None:
    store = LocalArtifactStore(tmp_path / "artifacts")
    supervisor = _supervisor(store=store)
    request = _request(store=store)
    policy = BacktestRunResourcePolicy(
        max_cpu_cores=2,
        max_memory_mb=1024,
        wall_clock_timeout_seconds=30,
        heartbeat_interval_seconds=10,
        checkpoint_interval_seconds=10,
        max_output_bytes=4096,
    )
    supervisor.start(request=request, resource_policy=policy)

    record = supervisor.observe(
        RUN_ID,
        BacktestRunChildProcessSnapshot(
            process_id="pid-timeout",
            status=BacktestRunChildProcessStatus.RUNNING,
            observed_at=NOW + timedelta(seconds=31),
            stage_id="stage-engine",
            progress_pct=42,
            memory_peak_mb=900,
            output_size_bytes=1024,
            partial_output_artifact_ids=("art_partial_equity",),
        ),
    )

    assert record.status is BacktestRunExecutionStatus.TIMED_OUT
    assert record.final_record is None
    assert record.termination_requested is True
    assert record.termination_reason == "timeout"
    assert record.checkpoints[-1].reason == "timeout"
    assert record.checkpoints[-1].artifact_state is BacktestArtifactState.PARTIAL
    assert record.checkpoints[-1].partial_output_artifact_ids == ("art_partial_equity",)
    checkpoint_payload = json.loads(store.get_bytes(record.checkpoints[-1].artifact_manifest.artifact_id))
    assert checkpoint_payload["schema_name"] == BACKTEST_RUN_CHECKPOINT_SCHEMA_NAME
    assert checkpoint_payload["status"] == "timed_out"
    assert checkpoint_payload["artifact_state"] == "partial"
    assert checkpoint_payload["resume"]["next_allowed_stage_id"] == "stage-engine"


def test_supervisor_cancel_request_publishes_partial_checkpoint_and_terminates_child(tmp_path: Path) -> None:
    store = LocalArtifactStore(tmp_path / "artifacts")
    supervisor = _supervisor(store=store)
    request = _request(store=store)
    supervisor.start(request=request)
    supervisor.request_cancel(RUN_ID, reason="user_requested_cancel", requested_at=NOW + timedelta(seconds=5))

    record = supervisor.observe(
        RUN_ID,
        BacktestRunChildProcessSnapshot(
            process_id="pid-cancel",
            status=BacktestRunChildProcessStatus.RUNNING,
            observed_at=NOW + timedelta(seconds=6),
            stage_id="stage-ledger",
            progress_pct=55,
            memory_peak_mb=700,
            output_size_bytes=1280,
            partial_output_artifact_ids=("art_partial_orders", "art_partial_positions"),
        ),
    )

    assert record.status is BacktestRunExecutionStatus.CANCELLED
    assert record.final_record is None
    assert record.termination_requested is True
    assert record.termination_reason == "user_requested_cancel"
    assert record.cancel_requested_at == NOW + timedelta(seconds=5)
    checkpoint_payload = json.loads(store.get_bytes(record.checkpoints[-1].artifact_manifest.artifact_id))
    assert checkpoint_payload["reason"] == "user_requested_cancel"
    assert checkpoint_payload["status"] == "cancelled"
    assert checkpoint_payload["partial_output_artifact_ids"] == ["art_partial_orders", "art_partial_positions"]


def test_supervisor_oom_classification_publishes_partial_checkpoint_and_never_succeeds(tmp_path: Path) -> None:
    store = LocalArtifactStore(tmp_path / "artifacts")
    supervisor = _supervisor(store=store)
    request = _request(store=store)
    supervisor.start(request=request)

    record = supervisor.observe(
        RUN_ID,
        BacktestRunChildProcessSnapshot(
            process_id="pid-oom",
            status=BacktestRunChildProcessStatus.OOM_KILLED,
            observed_at=NOW + timedelta(seconds=20),
            stage_id="stage-engine",
            progress_pct=27,
            exit_code=-9,
            memory_peak_mb=8192,
            output_size_bytes=1024,
            partial_output_artifact_ids=("art_partial_engine",),
        ),
    )

    assert record.status is BacktestRunExecutionStatus.OOM_KILLED
    assert record.final_record is None
    assert record.termination_requested is False
    assert record.failure_reason == "oom_killed"
    checkpoint_payload = json.loads(store.get_bytes(record.checkpoints[-1].artifact_manifest.artifact_id))
    assert checkpoint_payload["status"] == "oom_killed"
    assert checkpoint_payload["resource_usage"]["memory_peak_mb"] == 8192
    assert checkpoint_payload["artifact_state"] == "partial"


def test_resource_control_contract_stays_outside_api_worker_provider_and_qlib_runtime_boundaries() -> None:
    source = Path("src/serenity_alpha_lab/application/backtest_resource_control.py").read_text()
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

    assert not {"qlib", "pyqlib", "fastapi", "celery", "redis", "sqlalchemy", "litellm"}.intersection(imported_roots)
    assert all(
        not module.startswith(("api.", "bot.", "data_provider", "src.services.llm", "src.services.stock"))
        for module in imported_modules
    )


def _supervisor(*, store: LocalArtifactStore) -> BacktestRunResourceSupervisor:
    return BacktestRunResourceSupervisor(
        execution_repository=InMemoryBacktestRunExecutionRepository(),
        artifact_store=store,
        finalizer=BacktestRunOrchestrator(
            repository=InMemoryBacktestRunRepository(),
            artifact_store=store,
        ),
        clock=lambda: NOW,
    )


def _request(
    *,
    store: LocalArtifactStore,
    spec: BacktestSpec | None = None,
    run_id: str = RUN_ID,
) -> BacktestRunRequest:
    resolved_spec = spec or _formal_backtest_spec()
    return BacktestRunRequest(
        run_id=run_id,
        trace_id=TRACE_ID,
        idempotency_key=f"idem-{run_id}",
        submitted_at=NOW,
        spec=resolved_spec,
        engine_evidence=_engine_evidence(spec=resolved_spec, run_id=run_id),
        ledger=_ledger(spec=resolved_spec, run_id=run_id),
        risk_result=_risk_result(spec=resolved_spec, run_id=run_id),
        audit_report=_audit_report(spec=resolved_spec, run_id=run_id),
        metrics_report=_metrics_report(spec=resolved_spec, run_id=run_id),
        artifact_bundle=_artifact_bundle(store=store, spec=resolved_spec, run_id=run_id),
        requested_mode=BacktestRunMode.FORMAL,
        code_state=BacktestRunCodeState.CLEAN,
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


def _risk_result(*, spec: BacktestSpec, run_id: str) -> RiskPolicyResult:
    return RiskPolicyResult(
        result_id=f"risk_{run_id}",
        spec_id=spec.spec_id,
        spec_hash=spec.spec_hash,
        run_id=run_id,
        stage_id="stage-risk",
        policy=DeterministicRiskPolicy(policy_id="cn_a_share_deterministic_risk", policy_version="1.0.0"),
        status=RiskDecisionStatus.PASS,
        outcomes=(
            RiskRuleOutcome(
                rule_id="risk_profile_available",
                status=RiskRuleStatus.PASS,
                message="risk fixture",
            ),
        ),
    )


def _audit_report(*, spec: BacktestSpec, run_id: str) -> BacktestBiasAuditReport:
    return BacktestBiasAuditReport(
        report_id=f"audit_{run_id}",
        spec_id=spec.spec_id,
        spec_hash=spec.spec_hash,
        run_id=run_id,
        stage_id="stage-audit",
        policy=BacktestBiasAuditPolicy(policy_id="cn_a_share_bias_audit", policy_version="1.0.0"),
        status=BacktestBiasAuditStatus.PASS,
        outcomes=(
            BiasAuditRuleOutcome(
                rule_id="lookahead_bias",
                status=BiasAuditRuleStatus.PASS,
                message="audit fixture",
            ),
        ),
        eligible_for_ranking=True,
        agent_strong_conclusion_allowed=True,
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
) -> BacktestArtifactBundle:
    return BacktestArtifactBundle(
        run_id=run_id,
        stage_id="stage-artifacts",
        spec_id=spec.spec_id,
        spec_hash=spec.spec_hash,
        dataset_versions=spec.dataset.dataset_versions,
        state=BacktestArtifactState.FORMAL,
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
        partition_keys = ("trade_date",) if kind in {BacktestArtifactKind.ORDERS, BacktestArtifactKind.EXECUTIONS} else ()
        outputs.append(
            BacktestOutputArtifact(
                kind=kind,
                schema_name=schema_name,
                schema_version="1.0.0",
                artifact_manifest=manifest,
                content_hash="sha256:" + manifest.sha256,
                row_count=row_count,
                partition_keys=partition_keys,
            )
        )
    return tuple(outputs)


def _artifact_manifest(*, store: LocalArtifactStore, run_id: str, name: str, schema_name: str) -> ArtifactManifest:
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
