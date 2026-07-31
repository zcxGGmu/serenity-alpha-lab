from __future__ import annotations

import ast
import json
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from serenity_alpha_lab.application.backtest_api import (
    BACKTEST_API_CONTRACT_VERSION,
    BACKTEST_API_RUN_SCHEMA_NAME,
    FORMAL_BACKTEST_API_ROUTES,
    FORMAL_BACKTEST_TASK_TYPE,
    BacktestArtifactAccessSubject,
    FormalBacktestApiService,
    InMemoryBacktestApiRepository,
)
from serenity_alpha_lab.application.backtest_resource_control import (
    BacktestRunChildProcessSnapshot,
    BacktestRunChildProcessStatus,
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
from serenity_alpha_lab.application.task_backend import InMemoryTaskBackend
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


NOW = datetime(2026, 7, 26, 14, 30, tzinfo=UTC)
RUN_ID = "run-formal-backtest-api"
TRACE_ID = "trace-formal-backtest-api"
SPEC_HASH_CODE = "sha256:" + "8" * 64
SCREEN_DEFINITION_VERSION = "sdv_" + "1" * 32
SCREEN_SNAPSHOT_ID = "ssn_" + "2" * 32
FACTOR_VERSION = "fdv_" + "3" * 32


class DeterministicClock:
    def __init__(self) -> None:
        self._now = NOW

    def __call__(self) -> datetime:
        value = self._now
        self._now += timedelta(seconds=1)
        return value


def test_formal_backtest_api_declares_expected_routes_and_no_legacy_signal_namespace() -> None:
    paths = {(route.method, route.path, route.response_status) for route in FORMAL_BACKTEST_API_ROUTES}

    assert ("POST", "/api/v1/quant/backtest-runs", 202) in paths
    assert ("GET", "/api/v1/quant/backtest-runs/{run_id}", 200) in paths
    assert ("GET", "/api/v1/quant/backtest-runs/{run_id}/metrics", 200) in paths
    assert ("GET", "/api/v1/quant/backtest-runs/{run_id}/orders", 200) in paths
    assert ("GET", "/api/v1/quant/backtest-runs/{run_id}/positions", 200) in paths
    assert ("GET", "/api/v1/quant/backtest-runs/{run_id}/audit", 200) in paths
    assert ("GET", "/api/v1/quant/backtest-runs/{run_id}/artifacts/{artifact_kind}", 200) in paths
    assert ("POST", "/api/v1/quant/backtest-runs/{run_id}/cancel", 202) in paths
    assert all("/api/v1/backtest" not in route.path for route in FORMAL_BACKTEST_API_ROUTES)
    assert all("signal" not in route.operation_id.lower() for route in FORMAL_BACKTEST_API_ROUTES)
    assert FORMAL_BACKTEST_TASK_TYPE == "quant.backtest.run"
    assert json.dumps([route.to_record() for route in FORMAL_BACKTEST_API_ROUTES], sort_keys=True)


def test_backtest_run_creation_requires_idempotency_key_and_replays_accepted_response(tmp_path: Path) -> None:
    service, store = _service(tmp_path)
    request = _request(store=store)

    response = service.create_backtest_run(request, idempotency_key=request.idempotency_key)
    replay = service.create_backtest_run(request, idempotency_key=request.idempotency_key)

    assert response.status_code == 202
    assert replay.body == response.body
    assert response.headers["Location"] == f"/api/v1/quant/backtest-runs/{RUN_ID}"
    assert response.headers["Idempotency-Key"] == "idem-formal-backtest-api"
    assert response.body["contract_version"] == BACKTEST_API_CONTRACT_VERSION
    assert response.body["schema"] == {"name": BACKTEST_API_RUN_SCHEMA_NAME, "version": "1.0.0"}
    assert response.body["run_id"] == RUN_ID
    assert response.body["run_type"] == "formal_portfolio_backtest"
    assert response.body["evaluation_type"] == "portfolio_backtest"
    assert response.body["task_type"] == FORMAL_BACKTEST_TASK_TYPE
    assert response.body["task_status"] == "queued"
    assert response.body["execution_status"] == "running"
    assert response.body["spec"]["spec_hash"] == request.spec.spec_hash
    assert "orders" not in response.body
    assert "positions" not in response.body

    with pytest.raises(ValueError, match="Idempotency-Key"):
        service.create_backtest_run(request, idempotency_key="")

    changed = _request(store=store, run_id=RUN_ID, spec=_formal_backtest_spec(spec_id="formal_cn_quality_momentum_v2"))
    with pytest.raises(ValueError, match="Idempotency-Key"):
        service.create_backtest_run(changed, idempotency_key=request.idempotency_key)


def test_status_metrics_audit_and_runtime_flags_after_successful_child_observation(tmp_path: Path) -> None:
    service, store = _service(tmp_path)
    request = _request(store=store)
    service.create_backtest_run(request, idempotency_key=request.idempotency_key)

    service.observe_backtest_run(
        RUN_ID,
        BacktestRunChildProcessSnapshot(
            process_id="pid-formal-api",
            status=BacktestRunChildProcessStatus.SUCCEEDED,
            observed_at=NOW + timedelta(seconds=10),
            stage_id="stage-summary",
            progress_pct=100,
            memory_peak_mb=256,
            output_size_bytes=4096,
            result_request=request,
        ),
    )
    status = service.get_backtest_run(RUN_ID)
    metrics = service.get_backtest_metrics(RUN_ID)
    audit = service.get_backtest_audit(RUN_ID)

    assert status.status_code == 200
    assert status.body["task_status"] == "succeeded"
    assert status.body["execution_status"] == "succeeded"
    assert status.body["final_status"] == "succeeded"
    assert status.body["effective_mode"] == "formal"
    assert status.body["eligible_for_ranking"] is True
    assert status.body["artifact_bundle"]["state"] == "formal"
    assert status.body["metrics_artifact"]["kind"] == "metrics"
    assert status.body["audit_artifact"]["kind"] == "audit"
    assert status.body["runtime"] == {
        "formal_backtest_api_started": True,
        "resource_controls_started": True,
        "quant_lab_started": False,
        "evidence_agent_started": False,
        "worker_loop_started": False,
        "real_provider_calls_started": False,
        "real_llm_calls_started": False,
        "qlib_runtime_started": False,
        "legacy_signal_evaluation_started": False,
    }
    assert status.body["evaluation_type"] == "portfolio_backtest"
    assert status.body["runtime"]["legacy_signal_evaluation_started"] is False

    assert metrics.body["payload"]["metrics"]["cumulative_return"] == "0.024660"
    assert metrics.body["payload"]["metrics"]["sharpe_ratio"] == "1.250000"
    assert metrics.body["artifact"]["kind"] == "metrics"
    assert audit.body["payload"]["status"] == "pass"
    assert audit.body["payload"]["outcomes"][0]["rule_id"] == "lookahead_bias"


def test_orders_and_positions_are_cursor_paginated_from_artifacts(tmp_path: Path) -> None:
    service, store = _service(tmp_path)
    request = _request(store=store)
    service.create_backtest_run(request, idempotency_key=request.idempotency_key)
    service.observe_backtest_run(
        RUN_ID,
        BacktestRunChildProcessSnapshot(
            process_id="pid-formal-api",
            status=BacktestRunChildProcessStatus.SUCCEEDED,
            observed_at=NOW + timedelta(seconds=10),
            stage_id="stage-summary",
            progress_pct=100,
            result_request=request,
        ),
    )

    first_orders = service.list_backtest_orders(RUN_ID, page_size=2)
    second_orders = service.list_backtest_orders(
        RUN_ID,
        page_size=2,
        cursor=first_orders.body["pagination"]["next_cursor"],
    )
    positions = service.list_backtest_positions(RUN_ID, page_size=1)

    assert first_orders.body["pagination"] == {
        "page_size": 2,
        "cursor": None,
        "next_cursor": "2",
        "total_count": 3,
    }
    assert [row["order_id"] for row in first_orders.body["rows"]] == [
        "ord-formal-buy-600519",
        "ord-formal-sell-600519",
    ]
    assert [row["order_id"] for row in second_orders.body["rows"]] == ["ord-formal-reject-000001"]
    assert second_orders.body["pagination"]["next_cursor"] is None
    assert positions.body["rows"][0]["instrument_id"] == "600519.XSHG"
    assert positions.body["pagination"]["next_cursor"] == "1"


def test_artifact_download_requires_explicit_subject_permission(tmp_path: Path) -> None:
    service, store = _service(tmp_path)
    request = _request(store=store)
    service.create_backtest_run(request, idempotency_key=request.idempotency_key)
    service.observe_backtest_run(
        RUN_ID,
        BacktestRunChildProcessSnapshot(
            process_id="pid-formal-api",
            status=BacktestRunChildProcessStatus.SUCCEEDED,
            observed_at=NOW + timedelta(seconds=10),
            stage_id="stage-summary",
            progress_pct=100,
            result_request=request,
        ),
    )
    metrics_artifact_id = request.artifact_bundle.outputs[BacktestArtifactKind.METRICS].artifact_id

    with pytest.raises(ValueError, match="not authorized"):
        service.download_backtest_artifact(
            RUN_ID,
            BacktestArtifactKind.METRICS,
            subject=BacktestArtifactAccessSubject(subject_id="analyst"),
        )

    response = service.download_backtest_artifact(
        RUN_ID,
        BacktestArtifactKind.METRICS,
        subject=BacktestArtifactAccessSubject(
            subject_id="analyst",
            allowed_run_ids=(RUN_ID,),
            allowed_artifact_ids=(metrics_artifact_id,),
        ),
    )

    assert response.status_code == 200
    assert response.body["artifact"]["artifact_id"] == metrics_artifact_id
    assert response.body["payload"]["metrics"]["cumulative_return"] == "0.024660"


def test_cancel_request_is_exposed_without_worker_loop_or_legacy_route_side_effects(tmp_path: Path) -> None:
    service, store = _service(tmp_path)
    request = _request(store=store)
    service.create_backtest_run(request, idempotency_key=request.idempotency_key)

    response = service.cancel_backtest_run(RUN_ID, reason="user_requested_cancel")
    status = service.get_backtest_run(RUN_ID)

    assert response.status_code == 202
    assert response.body["task_status"] == "cancelled"
    assert response.body["execution_status"] == "running"
    assert response.body["termination_reason"] == "user_requested_cancel"
    assert status.body["task_status"] == "cancelled"
    assert status.body["runtime"]["worker_loop_started"] is False
    assert status.body["runtime"]["legacy_signal_evaluation_started"] is False


def test_backtest_api_import_boundary_stays_outside_framework_worker_provider_and_legacy_dsa() -> None:
    source = Path("src/serenity_alpha_lab/application/backtest_api.py").read_text()
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


def _service(tmp_path: Path) -> tuple[FormalBacktestApiService, LocalArtifactStore]:
    store = LocalArtifactStore(tmp_path / "artifacts")
    clock = DeterministicClock()
    supervisor = BacktestRunResourceSupervisor(
        execution_repository=InMemoryBacktestRunExecutionRepository(),
        artifact_store=store,
        finalizer=BacktestRunOrchestrator(
            repository=InMemoryBacktestRunRepository(),
            artifact_store=store,
        ),
        clock=clock,
    )
    return (
        FormalBacktestApiService(
            repository=InMemoryBacktestApiRepository(),
            task_backend=InMemoryTaskBackend(clock=clock),
            resource_supervisor=supervisor,
            artifact_store=store,
            clock=clock,
            trace_id=TRACE_ID,
        ),
        store,
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
        idempotency_key="idem-formal-backtest-api",
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
        returns={"cumulative_return": Decimal("0.024660")},
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
        (BacktestArtifactKind.ORDERS, "quant.backtest.orders", _orders_rows()),
        (BacktestArtifactKind.EXECUTIONS, "quant.backtest.executions", _executions_rows()),
        (BacktestArtifactKind.POSITIONS, "quant.backtest.positions", _positions_rows()),
        (BacktestArtifactKind.CASH, "quant.backtest.cash", _cash_rows()),
        (BacktestArtifactKind.EQUITY_CURVE, "quant.backtest.equity_curve", _equity_rows()),
        (BacktestArtifactKind.METRICS, "quant.backtest.metrics", {"metrics": {"cumulative_return": "0.024660", "sharpe_ratio": "1.250000"}}),
        (BacktestArtifactKind.AUDIT, "quant.backtest.audit", {"status": "pass", "outcomes": [{"rule_id": "lookahead_bias", "status": "pass"}]}),
    )
    outputs: list[BacktestOutputArtifact] = []
    for kind, schema_name, payload in specs:
        rows = payload if isinstance(payload, list) else [payload]
        manifest = _artifact_manifest(store=store, run_id=run_id, schema_name=schema_name, payload=payload)
        outputs.append(
            BacktestOutputArtifact(
                kind=kind,
                schema_name=schema_name,
                schema_version="1.0.0",
                artifact_manifest=manifest,
                content_hash="sha256:" + manifest.sha256,
                row_count=len(rows),
                partition_keys=("trade_date",) if kind in {BacktestArtifactKind.ORDERS, BacktestArtifactKind.EXECUTIONS} else (),
            )
        )
    return tuple(outputs)


def _artifact_manifest(
    *,
    store: LocalArtifactStore,
    run_id: str,
    schema_name: str,
    payload: object,
) -> ArtifactManifest:
    content = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return store.put_bytes(
        content,
        schema_name=schema_name,
        schema_version="1.0.0",
        content_type="application/vnd.serenity.quant.backtest-table+json",
        produced_by_run_id=run_id,
        produced_by_stage_id="stage-artifacts",
        retention_tier=ArtifactRetentionTier.STANDARD,
        created_at=NOW,
    )


def _orders_rows() -> list[dict[str, object]]:
    return [
        {"order_id": "ord-formal-buy-600519", "instrument_id": "600519.XSHG", "status": "filled", "trade_date": "2026-01-05"},
        {"order_id": "ord-formal-sell-600519", "instrument_id": "600519.XSHG", "status": "filled", "trade_date": "2026-01-20"},
        {"order_id": "ord-formal-reject-000001", "instrument_id": "000001.XSHE", "status": "rejected", "trade_date": "2026-01-05"},
    ]


def _executions_rows() -> list[dict[str, object]]:
    return [
        {"execution_id": "exe-formal-buy-600519", "order_id": "ord-formal-buy-600519", "trade_date": "2026-01-05"},
        {"execution_id": "exe-formal-sell-600519", "order_id": "ord-formal-sell-600519", "trade_date": "2026-01-20"},
    ]


def _positions_rows() -> list[dict[str, object]]:
    return [
        {"valuation_date": "2026-01-05", "instrument_id": "600519.XSHG", "quantity": "100"},
        {"valuation_date": "2026-01-20", "instrument_id": "600519.XSHG", "quantity": "0"},
    ]


def _cash_rows() -> list[dict[str, object]]:
    return [
        {"valuation_date": "2026-01-05", "cash": "9000.000"},
        {"valuation_date": "2026-01-20", "cash": "10246.600"},
    ]


def _equity_rows() -> list[dict[str, object]]:
    return [
        {"valuation_date": "2026-01-02", "equity": "10000.000"},
        {"valuation_date": "2026-01-05", "equity": "10010.000"},
        {"valuation_date": "2026-01-20", "equity": "10246.600"},
    ]


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
