from __future__ import annotations

import ast
import json
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from serenity_alpha_lab.domain.instruments import InstrumentId
from serenity_alpha_lab.quant.backtest.audit import (
    BACKTEST_BIAS_AUDIT_CONTRACT_VERSION,
    BacktestBiasAuditError,
    BacktestBiasAuditObservation,
    BacktestBiasAuditPolicy,
    BacktestBiasAuditStatus,
    BacktestBiasAuditor,
    BiasAuditRuleStatus,
    CostSensitivityScenario,
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


NOW = datetime(2026, 7, 26, 9, 30, tzinfo=UTC)
DECISION_TIME = datetime(2026, 1, 5, 15, 30, tzinfo=UTC)
AVAILABLE_BEFORE_DECISION = datetime(2026, 1, 5, 9, 30, tzinfo=UTC)
AVAILABLE_AFTER_DECISION = datetime(2026, 1, 6, 9, 30, tzinfo=UTC)
TRADE_DATE = date(2026, 1, 5)
SCREEN_SNAPSHOT_ID = "ssn_" + "2" * 32
SCREEN_DEFINITION_VERSION = "sdv_" + "1" * 32
FACTOR_QUALITY_VERSION = "fdv_" + "3" * 32
CODE_HASH = "sha256:" + "5" * 64
INSTRUMENT_KWEICHOW = InstrumentId.parse("600519.XSHG")
INSTRUMENT_PINGAN = InstrumentId.parse("000001.XSHE")
INSTRUMENT_CATL = InstrumentId.parse("300750.XSHE")
INSTRUMENT_MIDEA = InstrumentId.parse("000333.XSHE")


def test_bias_audit_blocks_known_lookahead_survivor_and_pit_leaks() -> None:
    spec = _formal_backtest_spec()
    auditor = BacktestBiasAuditor(spec=spec, policy=_audit_policy())

    report = auditor.evaluate(
        run_id="run-bias-audit",
        stage_id="stage-bias-audit",
        observations=(
            _observation(spec, INSTRUMENT_KWEICHOW),
            _observation(spec, INSTRUMENT_PINGAN, data_available_at=AVAILABLE_AFTER_DECISION),
            _observation(
                spec,
                INSTRUMENT_CATL,
                universe_as_of=date(2026, 7, 26),
                universe_source="current_constituents",
            ),
            _observation(
                spec,
                INSTRUMENT_KWEICHOW,
                pit_available_at=AVAILABLE_AFTER_DECISION,
                temporal_confidence="unknown",
            ),
        ),
        cost_scenarios=_stable_cost_scenarios(),
    )

    assert report.contract_version == BACKTEST_BIAS_AUDIT_CONTRACT_VERSION
    assert report.status is BacktestBiasAuditStatus.INVALID
    assert report.eligible_for_ranking is False
    assert report.agent_strong_conclusion_allowed is False
    assert report.rule_status("lookahead_bias") is BiasAuditRuleStatus.BLOCK
    assert report.rule_status("survivorship_bias") is BiasAuditRuleStatus.BLOCK
    assert report.rule_status("pit_data_availability") is BiasAuditRuleStatus.BLOCK
    assert set(report.hard_failure_rule_ids) == {
        "lookahead_bias",
        "pit_data_availability",
        "survivorship_bias",
    }
    record = report.to_record()
    assert record["status"] == "invalid"
    assert record["eligible_for_ranking"] is False
    assert record["agent_strong_conclusion_allowed"] is False
    assert "formal_portfolio_backtest_started" not in json.dumps(record, sort_keys=True)


def test_bias_audit_warns_on_sample_overlap_and_cost_sensitivity() -> None:
    spec = _formal_backtest_spec()
    auditor = BacktestBiasAuditor(spec=spec, policy=_audit_policy())
    observations = (
        _observation(spec, INSTRUMENT_KWEICHOW, in_strategy_sample=True, in_return_sample=False),
        _observation(spec, INSTRUMENT_PINGAN, in_strategy_sample=True, in_return_sample=False),
        _observation(spec, INSTRUMENT_CATL, in_strategy_sample=False, in_return_sample=True),
        _observation(spec, INSTRUMENT_MIDEA, in_strategy_sample=True, in_return_sample=True),
    )
    scenarios = (
        CostSensitivityScenario(
            scenario_id="baseline_cost",
            cost_multiplier=Decimal("1.0"),
            total_return=Decimal("0.1200"),
            is_baseline=True,
        ),
        CostSensitivityScenario(
            scenario_id="double_cost",
            cost_multiplier=Decimal("2.0"),
            total_return=Decimal("0.0600"),
        ),
    )

    first = auditor.evaluate(
        run_id="run-bias-audit",
        stage_id="stage-bias-audit",
        observations=observations,
        cost_scenarios=scenarios,
    )
    second = auditor.evaluate(
        run_id="run-bias-audit",
        stage_id="stage-bias-audit",
        observations=observations,
        cost_scenarios=scenarios,
    )

    assert first.status is BacktestBiasAuditStatus.WARN
    assert first.eligible_for_ranking is True
    assert first.agent_strong_conclusion_allowed is True
    assert first.rule_status("sample_overlap") is BiasAuditRuleStatus.WARN
    assert first.rule_status("cost_sensitivity") is BiasAuditRuleStatus.WARN
    assert first.rule_by_id("sample_overlap").observed_value == Decimal("0.2500")
    assert first.rule_by_id("cost_sensitivity").observed_value == Decimal("0.0600")
    assert first.warning_rule_ids == ("cost_sensitivity", "sample_overlap")
    assert first.to_record() == second.to_record()
    assert first.report_id.startswith("audit_")


def test_bias_audit_rejects_bad_bindings_and_stays_inside_pure_boundary() -> None:
    spec = _formal_backtest_spec()
    auditor = BacktestBiasAuditor(spec=spec, policy=_audit_policy())
    bad_dataset_observation = _observation(
        spec,
        INSTRUMENT_KWEICHOW,
        dataset_versions={**spec.dataset.dataset_versions, "raw_daily_bars": "dsv_" + "9" * 32},
    )

    with pytest.raises(BacktestBiasAuditError, match="dataset version"):
        auditor.evaluate(
            run_id="run-bias-audit",
            stage_id="stage-bias-audit",
            observations=(bad_dataset_observation,),
            cost_scenarios=_stable_cost_scenarios(),
        )

    with pytest.raises(BacktestBiasAuditError, match="single baseline"):
        auditor.evaluate(
            run_id="run-bias-audit",
            stage_id="stage-bias-audit",
            observations=(_observation(spec, INSTRUMENT_KWEICHOW),),
            cost_scenarios=(
                CostSensitivityScenario(
                    scenario_id="one",
                    cost_multiplier=Decimal("1.0"),
                    total_return=Decimal("0.10"),
                    is_baseline=True,
                ),
                CostSensitivityScenario(
                    scenario_id="two",
                    cost_multiplier=Decimal("1.1"),
                    total_return=Decimal("0.09"),
                    is_baseline=True,
                ),
            ),
        )

    source = Path("src/serenity_alpha_lab/quant/backtest/audit.py").read_text()
    tree = ast.parse(source)
    imported_roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_roots.add(node.module.split(".")[0])

    assert not {"qlib", "pyqlib", "fastapi", "sqlalchemy"}.intersection(imported_roots)


def _formal_backtest_spec() -> BacktestSpec:
    dataset_versions = {
        "adjusted_daily_bars": "dsv_" + "a" * 32,
        "raw_daily_bars": "dsv_" + "b" * 32,
        "trading_calendar": "dsv_" + "c" * 32,
        "corporate_actions": "dsv_" + "d" * 32,
        "instrument_master": "dsv_" + "e" * 32,
    }
    dataset_hashes = {name: f"sha256:{index:064x}" for index, name in enumerate(sorted(dataset_versions), start=1)}
    return BacktestSpec(
        spec_id="formal_cn_quality_momentum_v1",
        created_at=NOW,
        created_by_run_id="run-bias-audit",
        dataset=BacktestDatasetSpec(dataset_versions=dataset_versions, dataset_hashes=dataset_hashes),
        universe=BacktestUniverseSpec(
            universe_version_id="dsv_" + "f" * 32,
            universe_name="cn_a_share_l0",
            as_of=date(2026, 1, 5),
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
            factor_version_ids=(FACTOR_QUALITY_VERSION,),
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


def _audit_policy() -> BacktestBiasAuditPolicy:
    return BacktestBiasAuditPolicy(
        policy_id="cn_a_share_bias_audit",
        policy_version="1.0.0",
        minimum_sample_overlap_ratio=Decimal("0.8000"),
        cost_sensitivity_warning_threshold=Decimal("0.0500"),
        cost_sensitivity_block_threshold=Decimal("0.1500"),
    )


def _observation(
    spec: BacktestSpec,
    instrument_id: InstrumentId,
    *,
    data_available_at: datetime = AVAILABLE_BEFORE_DECISION,
    pit_available_at: datetime | None = AVAILABLE_BEFORE_DECISION,
    universe_as_of: date = TRADE_DATE,
    universe_source: str = "historical_as_of",
    in_strategy_sample: bool = True,
    in_return_sample: bool = True,
    dataset_versions: dict[str, str] | None = None,
    temporal_confidence: str = "known",
) -> BacktestBiasAuditObservation:
    return BacktestBiasAuditObservation(
        instrument_id=instrument_id,
        trade_date=TRADE_DATE,
        decision_time=DECISION_TIME,
        data_available_at=data_available_at,
        pit_available_at=pit_available_at,
        universe_as_of=universe_as_of,
        universe_source=universe_source,
        in_strategy_sample=in_strategy_sample,
        in_return_sample=in_return_sample,
        dataset_versions=dataset_versions or dict(spec.dataset.dataset_versions),
        temporal_confidence=temporal_confidence,
    )


def _stable_cost_scenarios() -> tuple[CostSensitivityScenario, ...]:
    return (
        CostSensitivityScenario(
            scenario_id="baseline_cost",
            cost_multiplier=Decimal("1.0"),
            total_return=Decimal("0.1000"),
            is_baseline=True,
        ),
        CostSensitivityScenario(
            scenario_id="double_cost",
            cost_multiplier=Decimal("2.0"),
            total_return=Decimal("0.0850"),
        ),
    )
