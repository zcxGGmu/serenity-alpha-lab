from __future__ import annotations

import json
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from serenity_alpha_lab.quant.backtest.spec import (
    BACKTEST_SPEC_CONTRACT_VERSION,
    BACKTEST_SPEC_SCHEMA_NAME,
    BacktestCostSpec,
    BacktestDatasetSpec,
    BacktestExecutionSpec,
    BacktestRiskSpec,
    BacktestSpec,
    BacktestSpecError,
    BacktestStrategySpec,
    BacktestUniverseSpec,
)


DATASET_VERSIONS = {
    "adjusted_daily_bars": "dsv_" + "a" * 32,
    "raw_daily_bars": "dsv_" + "b" * 32,
    "trading_calendar": "dsv_" + "c" * 32,
    "corporate_actions": "dsv_" + "d" * 32,
    "instrument_master": "dsv_" + "e" * 32,
}
DATASET_HASHES = {
    name: f"sha256:{index:064x}"
    for index, name in enumerate(sorted(DATASET_VERSIONS), start=1)
}
UNIVERSE_VERSION = "dsv_" + "f" * 32
SCREEN_DEFINITION_VERSION = "sdv_" + "1" * 32
SCREEN_SNAPSHOT_ID = "ssn_" + "2" * 32
FACTOR_QUALITY_VERSION = "fdv_" + "3" * 32
FACTOR_MOMENTUM_VERSION = "fdv_" + "4" * 32
CODE_HASH = "sha256:" + "5" * 64


def test_backtest_spec_binds_formal_inputs_and_stable_hash() -> None:
    spec = _formal_backtest_spec()

    assert spec.contract_version == BACKTEST_SPEC_CONTRACT_VERSION
    assert spec.schema_name == BACKTEST_SPEC_SCHEMA_NAME
    assert spec.spec_hash.startswith("sha256:")
    assert spec.dataset.dataset_versions == DATASET_VERSIONS
    assert spec.dataset.dataset_hashes == DATASET_HASHES
    assert spec.universe.universe_version_id == UNIVERSE_VERSION
    assert spec.strategy.screen_definition_version_id == SCREEN_DEFINITION_VERSION
    assert spec.strategy.factor_version_ids == (FACTOR_QUALITY_VERSION, FACTOR_MOMENTUM_VERSION)
    assert spec.execution.signal_timing == "after_close"
    assert spec.execution.execution_timing == "next_open"
    assert spec.execution.signal_price_field == "close"
    assert spec.execution.execution_price_field == "open"
    assert spec.execution.random_seed == 20260725
    assert spec.costs.commission_bps == Decimal("3.0")
    assert spec.risk.max_weight_per_instrument == Decimal("0.10")

    record = spec.to_record()
    assert record["spec_hash"] == spec.spec_hash
    assert record["strategy"]["code_hash"] == CODE_HASH
    assert record["portfolio"]["initial_capital"] == "10000000.00"
    assert record["costs"]["max_participation_rate"] == "0.1000"
    assert record["risk"]["cash_buffer_pct"] == "0.0200"
    json.dumps(record, sort_keys=True)


def test_canonical_hash_is_independent_of_mapping_order_and_changes_on_semantics() -> None:
    first = _formal_backtest_spec()
    reordered = _formal_backtest_spec(
        dataset=BacktestDatasetSpec(
            dataset_versions=dict(reversed(list(DATASET_VERSIONS.items()))),
            dataset_hashes=dict(reversed(list(DATASET_HASHES.items()))),
        )
    )
    changed_cost = _formal_backtest_spec(
        costs=BacktestCostSpec(
            commission_bps=Decimal("4.0"),
            min_commission=Decimal("5.00"),
            stamp_tax_bps=Decimal("10.0"),
            transfer_fee_bps=Decimal("0.2"),
            slippage_bps=Decimal("5.0"),
            impact_bps=Decimal("2.0"),
            max_participation_rate=Decimal("0.1000"),
        )
    )

    assert reordered.canonical_json() == first.canonical_json()
    assert reordered.spec_hash == first.spec_hash
    assert changed_cost.spec_hash != first.spec_hash


def test_backtest_spec_rejects_latest_legacy_signal_and_same_bar_execution() -> None:
    with pytest.raises(BacktestSpecError, match="concrete Dataset Version"):
        _formal_backtest_spec(
            dataset=BacktestDatasetSpec(
                dataset_versions={**DATASET_VERSIONS, "raw_daily_bars": "latest"},
                dataset_hashes=DATASET_HASHES,
            )
        )

    with pytest.raises(BacktestSpecError, match="legacy Signal Evaluation"):
        _formal_backtest_spec(
            strategy=BacktestStrategySpec(
                strategy_id="legacy_signal_eval",
                strategy_version="1.0.0",
                strategy_kind="legacy_signal_evaluation",
                source_commit="abcdef1234567890",
                code_hash=CODE_HASH,
                screen_definition_version_id=SCREEN_DEFINITION_VERSION,
                screen_snapshot_id=SCREEN_SNAPSHOT_ID,
                factor_version_ids=(FACTOR_QUALITY_VERSION,),
            )
        )

    with pytest.raises(BacktestSpecError, match="same bar close signal"):
        _formal_backtest_spec(
            execution=BacktestExecutionSpec(
                signal_timing="at_close",
                execution_timing="same_bar_close",
                signal_price_field="close",
                execution_price_field="close",
                rebalance_calendar="cn_trading_days",
                valuation_calendar="cn_trading_days",
                rebalance_frequency="weekly",
                settlement_lag_days=1,
                lot_size=100,
                random_seed=20260725,
            )
        )


def _formal_backtest_spec(**overrides) -> BacktestSpec:
    values = {
        "spec_id": "formal_cn_quality_momentum_v1",
        "created_at": datetime(2026, 7, 25, 9, 30, tzinfo=UTC),
        "created_by_run_id": "run-backtest-spec",
        "dataset": BacktestDatasetSpec(dataset_versions=DATASET_VERSIONS, dataset_hashes=DATASET_HASHES),
        "universe": BacktestUniverseSpec(
            universe_version_id=UNIVERSE_VERSION,
            universe_name="cn_a_share_l0",
            as_of=date(2026, 7, 25),
            membership_policy="pit_membership_as_of_decision_time",
        ),
        "strategy": BacktestStrategySpec(
            strategy_id="quality_momentum_weekly",
            strategy_version="1.0.0",
            strategy_kind="screen_snapshot_rebalance",
            source_commit="abcdef1234567890",
            code_hash=CODE_HASH,
            screen_definition_version_id=SCREEN_DEFINITION_VERSION,
            screen_snapshot_id=SCREEN_SNAPSHOT_ID,
            factor_version_ids=(FACTOR_QUALITY_VERSION, FACTOR_MOMENTUM_VERSION),
        ),
        "start_date": date(2026, 1, 1),
        "end_date": date(2026, 6, 30),
        "benchmark": "000300.XSHG",
        "currency": "CNY",
        "initial_capital": Decimal("10000000.00"),
        "cash_rate_bps": Decimal("150.0"),
        "execution": BacktestExecutionSpec(
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
        "costs": BacktestCostSpec(
            commission_bps=Decimal("3.0"),
            min_commission=Decimal("5.00"),
            stamp_tax_bps=Decimal("10.0"),
            transfer_fee_bps=Decimal("0.2"),
            slippage_bps=Decimal("5.0"),
            impact_bps=Decimal("2.0"),
            max_participation_rate=Decimal("0.1000"),
        ),
        "risk": BacktestRiskSpec(
            risk_policy_version="risk_policy.cn_a_share@1.0.0",
            max_weight_per_instrument=Decimal("0.10"),
            max_weight_per_industry=Decimal("0.30"),
            max_turnover_per_rebalance=Decimal("0.40"),
            cash_buffer_pct=Decimal("0.0200"),
            liquidity_floor_amount=Decimal("1000000.00"),
        ),
        "artifact_output_level": "full_audit",
    }
    values.update(overrides)
    return BacktestSpec(**values)
