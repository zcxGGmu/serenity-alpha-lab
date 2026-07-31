from __future__ import annotations

import ast
import json
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from serenity_alpha_lab.domain.instruments import InstrumentId
from serenity_alpha_lab.quant.backtest.ledger import PortfolioLedger
from serenity_alpha_lab.quant.backtest.rebalance import (
    RebalancePlan,
    RebalancePolicy,
    TargetWeight,
    WeightingPolicy,
)
from serenity_alpha_lab.quant.backtest.risk import (
    RISK_POLICY_CONTRACT_VERSION,
    DeterministicRiskPolicy,
    InstrumentRiskProfile,
    RiskDecisionStatus,
    RiskPolicyEvaluator,
    RiskPolicyError,
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


NOW = datetime(2026, 7, 26, 9, 30, tzinfo=UTC)
SIGNAL_TIME = datetime(2026, 7, 25, 15, 0, tzinfo=UTC)
TRADE_DATE = date(2026, 7, 27)
SCREEN_SNAPSHOT_ID = "ssn_" + "2" * 32
SCREEN_DEFINITION_VERSION = "sdv_" + "1" * 32
FACTOR_QUALITY_VERSION = "fdv_" + "3" * 32
CODE_HASH = "sha256:" + "5" * 64
INSTRUMENT_KWEICHOW = InstrumentId.parse("600519.XSHG")
INSTRUMENT_PINGAN = InstrumentId.parse("000001.XSHE")
INSTRUMENT_CATL = InstrumentId.parse("300750.XSHE")


def test_risk_policy_blocks_instrument_and_industry_breaches() -> None:
    spec = _formal_backtest_spec()
    ledger = _empty_ledger(spec)
    plan = _plan(
        spec=spec,
        ledger=ledger,
        weights={
            INSTRUMENT_KWEICHOW: Decimal("0.1200"),
            INSTRUMENT_PINGAN: Decimal("0.2500"),
            INSTRUMENT_CATL: Decimal("0.1200"),
        },
        planned_buy_notional=Decimal("39000"),
    )
    evaluator = RiskPolicyEvaluator(spec=spec, policy=_risk_policy())

    result = evaluator.evaluate(
        ledger=ledger,
        rebalance_plan=plan,
        profiles=_profiles(),
        high_water_mark_equity=Decimal("100000"),
    )

    assert result.contract_version == RISK_POLICY_CONTRACT_VERSION
    assert result.status is RiskDecisionStatus.BLOCK
    assert result.agent_override_allowed is False
    assert result.rule_status("max_weight_per_instrument") is RiskRuleStatus.BLOCK
    assert result.rule_status("max_weight_per_industry") is RiskRuleStatus.BLOCK
    assert result.blocking_rule_ids == ("max_weight_per_instrument", "max_weight_per_industry")
    assert result.rule_by_id("max_weight_per_instrument").instrument_id == INSTRUMENT_PINGAN
    assert result.rule_by_id("max_weight_per_industry").group_key == "consumer"
    record = result.to_record()
    assert record["status"] == "block"
    assert record["agent_override_allowed"] is False
    assert "formal_portfolio_backtest_started" not in json.dumps(record, sort_keys=True)


def test_risk_policy_warns_style_and_blocks_liquidity_turnover_drawdown() -> None:
    spec = _formal_backtest_spec()
    ledger = _empty_ledger(spec)
    plan = _plan(
        spec=spec,
        ledger=ledger,
        weights={
            INSTRUMENT_KWEICHOW: Decimal("0.0500"),
            INSTRUMENT_PINGAN: Decimal("0.0500"),
        },
        planned_buy_notional=Decimal("45000"),
        planned_sell_notional=Decimal("10000"),
    )
    evaluator = RiskPolicyEvaluator(spec=spec, policy=_risk_policy())

    result = evaluator.evaluate(
        ledger=ledger,
        rebalance_plan=plan,
        profiles={
            INSTRUMENT_KWEICHOW: InstrumentRiskProfile(
                instrument_id=INSTRUMENT_KWEICHOW,
                industry="consumer",
                average_daily_amount=Decimal("500000"),
                style_exposures={"momentum": Decimal("0.95")},
            ),
            INSTRUMENT_PINGAN: InstrumentRiskProfile(
                instrument_id=INSTRUMENT_PINGAN,
                industry="financials",
                average_daily_amount=Decimal("5000000"),
                style_exposures={"momentum": Decimal("0.80")},
            ),
        },
        high_water_mark_equity=Decimal("120000"),
    )

    assert result.status is RiskDecisionStatus.BLOCK
    assert result.rule_status("style_exposure:momentum") is RiskRuleStatus.WARN
    assert result.rule_status("liquidity_floor") is RiskRuleStatus.BLOCK
    assert result.rule_status("max_turnover_per_rebalance") is RiskRuleStatus.BLOCK
    assert result.rule_status("max_drawdown") is RiskRuleStatus.BLOCK
    assert result.rule_by_id("liquidity_floor").instrument_id == INSTRUMENT_KWEICHOW
    assert result.rule_by_id("max_turnover_per_rebalance").observed_value == Decimal("0.5500")
    assert result.rule_by_id("max_drawdown").observed_value == Decimal("0.1667")


def test_not_evaluable_defaults_to_block_and_result_is_deterministic() -> None:
    spec = _formal_backtest_spec()
    ledger = _empty_ledger(spec)
    plan = _plan(
        spec=spec,
        ledger=ledger,
        weights={INSTRUMENT_KWEICHOW: Decimal("0.0500")},
        planned_buy_notional=Decimal("5000"),
    )
    evaluator = RiskPolicyEvaluator(spec=spec, policy=_risk_policy())

    first = evaluator.evaluate(
        ledger=ledger,
        rebalance_plan=plan,
        profiles={},
        high_water_mark_equity=None,
    )
    second = evaluator.evaluate(
        ledger=ledger,
        rebalance_plan=plan,
        profiles={},
        high_water_mark_equity=None,
    )

    assert first.status is RiskDecisionStatus.BLOCK
    assert first.rule_status("risk_profile_available") is RiskRuleStatus.NOT_EVALUABLE
    assert first.rule_status("max_drawdown") is RiskRuleStatus.NOT_EVALUABLE
    assert set(first.not_evaluable_rule_ids) == {
        "liquidity_floor",
        "max_drawdown",
        "max_weight_per_industry",
        "risk_profile_available",
        "style_exposure:momentum",
    }
    assert first.to_record() == second.to_record()
    assert first.result_id.startswith("risk_")


def test_risk_policy_rejects_bad_bindings_and_stays_inside_pure_boundary() -> None:
    spec = _formal_backtest_spec()
    evaluator = RiskPolicyEvaluator(spec=spec, policy=_risk_policy())
    other_spec = _formal_backtest_spec(spec_id="other_spec")
    other_ledger = _empty_ledger(other_spec)
    other_plan = _plan(
        spec=other_spec,
        ledger=other_ledger,
        weights={INSTRUMENT_KWEICHOW: Decimal("0.0500")},
        planned_buy_notional=Decimal("5000"),
    )

    with pytest.raises(RiskPolicyError, match="ledger spec_id and spec_hash must match"):
        evaluator.evaluate(
            ledger=other_ledger,
            rebalance_plan=other_plan,
            profiles=_profiles(),
            high_water_mark_equity=Decimal("100000"),
        )

    with pytest.raises(RiskPolicyError, match="rebalance_plan spec_id and spec_hash must match"):
        evaluator.evaluate(
            ledger=_empty_ledger(spec),
            rebalance_plan=other_plan,
            profiles=_profiles(),
            high_water_mark_equity=Decimal("100000"),
        )

    source = Path("src/serenity_alpha_lab/quant/backtest/risk.py").read_text()
    tree = ast.parse(source)
    imported_roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_roots.add(node.module.split(".")[0])

    assert not {"qlib", "pyqlib", "fastapi", "sqlalchemy"}.intersection(imported_roots)


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
        created_by_run_id="run-risk-policy",
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


def _risk_policy() -> DeterministicRiskPolicy:
    return DeterministicRiskPolicy(
        policy_id="cn_a_share_deterministic_risk",
        policy_version="1.0.0",
        style_exposure_warning_limits={"momentum": Decimal("0.0800")},
        max_drawdown_pct=Decimal("0.1000"),
    )


def _empty_ledger(spec: BacktestSpec) -> PortfolioLedger:
    return PortfolioLedger.open(
        run_id="run-risk-policy",
        stage_id="stage-risk-policy",
        spec_id=spec.spec_id,
        spec_hash=spec.spec_hash,
        base_currency="CNY",
        initial_cash=Decimal("100000"),
        event_id=f"led-initial-cash-{spec.spec_id}",
        occurred_at=NOW,
    )


def _plan(
    *,
    spec: BacktestSpec,
    ledger: PortfolioLedger,
    weights: dict[InstrumentId, Decimal],
    planned_buy_notional: Decimal,
    planned_sell_notional: Decimal = Decimal("0"),
) -> RebalancePlan:
    return RebalancePlan(
        plan_id="rbp_risk_fixture",
        spec_id=spec.spec_id,
        spec_hash=spec.spec_hash,
        run_id=ledger.run_id,
        stage_id=ledger.stage_id,
        trade_date=TRADE_DATE,
        signal_time=SIGNAL_TIME,
        created_at=NOW,
        policy=RebalancePolicy(
            policy_id="cn_a_share_weekly_rebalance",
            policy_version="1.0.0",
            weighting_policy=WeightingPolicy.EXPLICIT_TARGET_WEIGHT,
            min_order_notional=Decimal("500"),
        ),
        target_weights=tuple(
            TargetWeight(
                instrument_id=instrument_id,
                target_weight=target_weight,
                source="risk_fixture",
                reason="risk_fixture",
            )
            for instrument_id, target_weight in sorted(weights.items(), key=lambda item: item[0].canonical)
        ),
        orders=(),
        skipped_orders=(),
        cash_buffer_amount=Decimal("2000"),
        available_buy_cash=Decimal("98000"),
        planned_buy_notional=planned_buy_notional,
        planned_sell_notional=planned_sell_notional,
        residual_cash=Decimal("53000"),
    )


def _profiles() -> dict[InstrumentId, InstrumentRiskProfile]:
    return {
        INSTRUMENT_KWEICHOW: InstrumentRiskProfile(
            instrument_id=INSTRUMENT_KWEICHOW,
            industry="consumer",
            average_daily_amount=Decimal("5000000"),
            style_exposures={"momentum": Decimal("0.50")},
        ),
        INSTRUMENT_PINGAN: InstrumentRiskProfile(
            instrument_id=INSTRUMENT_PINGAN,
            industry="consumer",
            average_daily_amount=Decimal("5000000"),
            style_exposures={"momentum": Decimal("0.20")},
        ),
        INSTRUMENT_CATL: InstrumentRiskProfile(
            instrument_id=INSTRUMENT_CATL,
            industry="industrials",
            average_daily_amount=Decimal("5000000"),
            style_exposures={"momentum": Decimal("-0.30")},
        ),
    }
