from __future__ import annotations

import ast
import json
from collections.abc import Mapping
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from serenity_alpha_lab.domain.artifacts import ArtifactRetentionTier
from serenity_alpha_lab.integrations.qlib.dataset_converter import (
    QLIB_CALENDAR_CONTENT_TYPE,
    QLIB_CALENDAR_SCHEMA_NAME,
    QLIB_CALENDAR_SCHEMA_VERSION,
    QLIB_DATASET_CONVERSION_CONTENT_TYPE,
    QLIB_DATASET_CONVERSION_SCHEMA_NAME,
    QLIB_DATASET_CONVERSION_SCHEMA_VERSION,
    QLIB_FEATURE_CONTENT_TYPE,
    QLIB_FEATURE_SCHEMA_NAME,
    QLIB_FEATURE_SCHEMA_VERSION,
    QLIB_FIELD_MAPPING_CONTENT_TYPE,
    QLIB_FIELD_MAPPING_SCHEMA_NAME,
    QLIB_FIELD_MAPPING_SCHEMA_VERSION,
    QLIB_INSTRUMENT_CONTENT_TYPE,
    QLIB_INSTRUMENT_SCHEMA_NAME,
    QLIB_INSTRUMENT_SCHEMA_VERSION,
    QlibDatasetConversionArtifacts,
)
from serenity_alpha_lab.integrations.qlib.quant_engine_adapter import (
    QLIB_QUANT_ENGINE_RUN_REPORT_SCHEMA_NAME,
    QLIB_QUANT_ENGINE_STEP_SCHEMA_NAME,
    QlibQuantEngineAdapter,
    QlibQuantEngineConfig,
    QlibQuantEngineError,
    QlibQuantEngineOperation,
    QlibQuantEngineRequest,
    QlibQuantEngineTemplate,
    QlibRecorderSnapshot,
)
from serenity_alpha_lab.integrations.qlib.runtime_policy import default_qlib_runtime_policy
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


NOW = datetime(2026, 7, 25, 13, 0, tzinfo=UTC)
DATASET_VERSIONS = {
    "adjusted_daily_bars": "dsv_" + "a" * 32,
    "raw_daily_bars": "dsv_" + "b" * 32,
    "trading_calendar": "dsv_" + "c" * 32,
    "corporate_actions": "dsv_" + "d" * 32,
    "instrument_master": "dsv_" + "e" * 32,
}
DATASET_HASHES = {name: f"sha256:{index:064x}" for index, name in enumerate(sorted(DATASET_VERSIONS), start=1)}
SCREEN_DEFINITION_VERSION = "sdv_" + "1" * 32
SCREEN_SNAPSHOT_ID = "ssn_" + "2" * 32
FACTOR_VERSION = "fdv_" + "3" * 32
CODE_HASH = "sha256:" + "4" * 64


class FakeQlibFacade:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def train(self, config: Mapping[str, Any]) -> Mapping[str, Any]:
        return self._record("train", config)

    def predict(self, config: Mapping[str, Any]) -> Mapping[str, Any]:
        return self._record("predict", config)

    def backtest(self, config: Mapping[str, Any]) -> Mapping[str, Any]:
        return self._record("backtest", config)

    def evaluate_factor(self, config: Mapping[str, Any]) -> Mapping[str, Any]:
        return self._record("evaluate_factor", config)

    def _record(self, operation: str, config: Mapping[str, Any]) -> Mapping[str, Any]:
        config_record = json.loads(json.dumps(config, sort_keys=True))
        self.calls.append((operation, config_record))
        return {
            "operation": operation,
            "status": "succeeded",
            "metrics": {"row_count": 2, "score": 0.75},
            "recorder": {
                "experiment_id": "exp_formal_cn_quality_momentum",
                "recorder_id": f"rec_{operation}_001",
                "uri": f"qlib://recorder/{operation}/001",
                "tags": {"qlib_step": operation},
            },
        }


def test_adapter_wraps_train_predict_backtest_evaluate_factor_and_recorder(tmp_path: Path) -> None:
    store = LocalArtifactStore(tmp_path / "artifacts")
    facade = FakeQlibFacade()
    adapter = QlibQuantEngineAdapter(
        artifact_store=store,
        facade=facade,
        policy=default_qlib_runtime_policy(),
    )
    request = make_request(store)

    results = (
        adapter.train(request),
        adapter.predict(request),
        adapter.backtest(request),
        adapter.evaluate_factor(request),
    )
    report = adapter.build_run_report(request=request, step_results=results)
    report_artifact = report.publish(store)

    assert [call[0] for call in facade.calls] == ["train", "predict", "backtest", "evaluate_factor"]
    assert all(call[1]["template_id"] == QlibQuantEngineTemplate.LIGHTGBM_DAILY_REBALANCE.value for call in facade.calls)
    assert all(call[1]["platform"]["run_id"] == request.run_id for call in facade.calls)
    assert all(call[1]["platform"]["spec_hash"] == request.backtest_spec.spec_hash for call in facade.calls)
    assert all(call[1]["dataset_conversion_artifacts"]["summary"]["artifact_id"] for call in facade.calls)

    for expected_operation, result in zip(QlibQuantEngineOperation, results, strict=True):
        assert result.operation is expected_operation
        assert result.artifact_manifest.schema_name == QLIB_QUANT_ENGINE_STEP_SCHEMA_NAME
        assert result.recorder_snapshot == QlibRecorderSnapshot(
            experiment_id="exp_formal_cn_quality_momentum",
            recorder_id=f"rec_{expected_operation.value}_001",
            uri=f"qlib://recorder/{expected_operation.value}/001",
            tags={
                "qlib_step": expected_operation.value,
                "platform_run_id": request.run_id,
                "platform_stage_id": request.stage_id,
                "platform_trace_id": request.trace_id,
                "backtest_spec_hash": request.backtest_spec.spec_hash,
            },
        )
        payload = json.loads(store.get_bytes(result.artifact_manifest.artifact_id))
        assert payload["operation"] == expected_operation.value
        assert payload["engine_scope"] == "qlib_quant_engine_adapter"
        assert payload["runtime"]["formal_portfolio_backtest_started"] is False
        assert payload["recorder"]["recorder_id"] == f"rec_{expected_operation.value}_001"
        assert "rows" not in json.dumps(payload, sort_keys=True).lower()

    report_payload = json.loads(store.get_bytes(report_artifact.artifact_id))
    assert report_payload["schema_name"] == QLIB_QUANT_ENGINE_RUN_REPORT_SCHEMA_NAME
    assert report_payload["operation_count"] == 4
    assert report_payload["operations"] == ["train", "predict", "backtest", "evaluate_factor"]
    assert report_payload["runtime"]["formal_portfolio_backtest_started"] is False
    assert report_payload["trace"] == {
        "trace_id": request.trace_id,
        "run_id": request.run_id,
        "stage_id": request.stage_id,
    }


def test_config_rejects_unknown_templates_and_arbitrary_module_path_payloads() -> None:
    with pytest.raises(QlibQuantEngineError, match="template"):
        QlibQuantEngineConfig(
            template_id="custom.module.Strategy",
            experiment_name="formal-cn",
            parameters={},
        )

    with pytest.raises(QlibQuantEngineError, match="arbitrary Python module path"):
        QlibQuantEngineConfig(
            template_id=QlibQuantEngineTemplate.LIGHTGBM_DAILY_REBALANCE,
            experiment_name="formal-cn",
            parameters={"model": {"module_path": "qlib.contrib.model.gbdt.LGBModel"}},
        )

    with pytest.raises(QlibQuantEngineError, match="arbitrary Python module path"):
        QlibQuantEngineConfig(
            template_id=QlibQuantEngineTemplate.LINEAR_FACTOR_EVALUATION,
            experiment_name="factor-eval",
            parameters={"handler": {"class": "qlib.contrib.data.handler.Alpha158"}},
        )


def test_request_requires_platform_context_spec_and_dataset_conversion_artifacts(tmp_path: Path) -> None:
    store = LocalArtifactStore(tmp_path / "artifacts")
    config = QlibQuantEngineConfig(
        template_id=QlibQuantEngineTemplate.LIGHTGBM_DAILY_REBALANCE,
        experiment_name="formal-cn",
        parameters={"learning_rate": "0.05"},
    )

    with pytest.raises(QlibQuantEngineError, match="trace_id"):
        QlibQuantEngineRequest(
            run_id="run-qlib-adapter",
            stage_id="stage-qlib-adapter",
            trace_id="",
            created_at=NOW,
            backtest_spec=formal_backtest_spec(),
            dataset_conversion_artifacts=make_conversion_artifacts(store),
            config=config,
        )

    with pytest.raises(QlibQuantEngineError, match="BacktestSpec"):
        QlibQuantEngineRequest(
            run_id="run-qlib-adapter",
            stage_id="stage-qlib-adapter",
            trace_id="trace-qlib-adapter",
            created_at=NOW,
            backtest_spec=object(),
            dataset_conversion_artifacts=make_conversion_artifacts(store),
            config=config,
        )

    with pytest.raises(QlibQuantEngineError, match="QlibDatasetConversionArtifacts"):
        QlibQuantEngineRequest(
            run_id="run-qlib-adapter",
            stage_id="stage-qlib-adapter",
            trace_id="trace-qlib-adapter",
            created_at=NOW,
            backtest_spec=formal_backtest_spec(),
            dataset_conversion_artifacts=object(),
            config=config,
        )


def test_quant_engine_adapter_module_does_not_import_qlib_runtime() -> None:
    module_path = (
        Path(__file__).resolve().parents[2]
        / "src"
        / "serenity_alpha_lab"
        / "integrations"
        / "qlib"
        / "quant_engine_adapter.py"
    )
    tree = ast.parse(module_path.read_text(encoding="utf-8"), filename=str(module_path))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)

    forbidden_roots = {"qlib", "pyqlib", "fastapi", "sqlalchemy"}
    assert {module.split(".", maxsplit=1)[0] for module in imports}.isdisjoint(forbidden_roots)


def make_request(store: LocalArtifactStore) -> QlibQuantEngineRequest:
    return QlibQuantEngineRequest(
        run_id="run-qlib-adapter",
        stage_id="stage-qlib-adapter",
        trace_id="trace-qlib-adapter",
        created_at=NOW,
        backtest_spec=formal_backtest_spec(),
        dataset_conversion_artifacts=make_conversion_artifacts(store),
        config=QlibQuantEngineConfig(
            template_id=QlibQuantEngineTemplate.LIGHTGBM_DAILY_REBALANCE,
            experiment_name="formal-cn-quality-momentum",
            parameters={
                "learning_rate": "0.05",
                "num_leaves": 8,
                "feature_schema": "integration.qlib.feature@1.0.0",
            },
            recorder_tags={"strategy": "quality_momentum_weekly"},
        ),
    )


def make_conversion_artifacts(store: LocalArtifactStore) -> QlibDatasetConversionArtifacts:
    return QlibDatasetConversionArtifacts(
        calendar=put_artifact(
            store,
            name="calendar",
            schema_name=QLIB_CALENDAR_SCHEMA_NAME,
            schema_version=QLIB_CALENDAR_SCHEMA_VERSION,
            content_type=QLIB_CALENDAR_CONTENT_TYPE,
        ),
        instruments=put_artifact(
            store,
            name="instruments",
            schema_name=QLIB_INSTRUMENT_SCHEMA_NAME,
            schema_version=QLIB_INSTRUMENT_SCHEMA_VERSION,
            content_type=QLIB_INSTRUMENT_CONTENT_TYPE,
        ),
        features=put_artifact(
            store,
            name="features",
            schema_name=QLIB_FEATURE_SCHEMA_NAME,
            schema_version=QLIB_FEATURE_SCHEMA_VERSION,
            content_type=QLIB_FEATURE_CONTENT_TYPE,
        ),
        field_mapping=put_artifact(
            store,
            name="field_mapping",
            schema_name=QLIB_FIELD_MAPPING_SCHEMA_NAME,
            schema_version=QLIB_FIELD_MAPPING_SCHEMA_VERSION,
            content_type=QLIB_FIELD_MAPPING_CONTENT_TYPE,
        ),
        summary=put_artifact(
            store,
            name="summary",
            schema_name=QLIB_DATASET_CONVERSION_SCHEMA_NAME,
            schema_version=QLIB_DATASET_CONVERSION_SCHEMA_VERSION,
            content_type=QLIB_DATASET_CONVERSION_CONTENT_TYPE,
        ),
    )


def put_artifact(
    store: LocalArtifactStore,
    *,
    name: str,
    schema_name: str,
    schema_version: str,
    content_type: str,
):
    return store.put_bytes(
        json.dumps({"name": name}, sort_keys=True).encode("utf-8"),
        schema_name=schema_name,
        schema_version=schema_version,
        content_type=content_type,
        produced_by_run_id="run-qlib-conversion",
        produced_by_stage_id="stage-qlib-conversion",
        retention_tier=ArtifactRetentionTier.STANDARD,
        created_at=NOW,
    )


def formal_backtest_spec() -> BacktestSpec:
    return BacktestSpec(
        spec_id="formal_cn_quality_momentum_v1",
        created_at=NOW,
        created_by_run_id="run-backtest-spec",
        dataset=BacktestDatasetSpec(dataset_versions=DATASET_VERSIONS, dataset_hashes=DATASET_HASHES),
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
            code_hash=CODE_HASH,
            screen_definition_version_id=SCREEN_DEFINITION_VERSION,
            screen_snapshot_id=SCREEN_SNAPSHOT_ID,
            factor_version_ids=(FACTOR_VERSION,),
        ),
        start_date=date(2026, 1, 1),
        end_date=date(2026, 6, 30),
        benchmark="000300.XSHG",
        currency="CNY",
        initial_capital=Decimal("10000000.00"),
        cash_rate_bps=Decimal("150.0"),
        execution=BacktestExecutionSpec(
            signal_timing="after_close",
            execution_timing="next_open",
            signal_price_field="close",
            execution_price_field="open",
            rebalance_calendar="cn_trading_days",
            valuation_calendar="cn_trading_days",
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
            max_weight_per_instrument=Decimal("0.10"),
            max_weight_per_industry=Decimal("0.30"),
            max_turnover_per_rebalance=Decimal("0.40"),
            cash_buffer_pct=Decimal("0.0200"),
            liquidity_floor_amount=Decimal("1000000.00"),
        ),
        artifact_output_level="full_audit",
    )
