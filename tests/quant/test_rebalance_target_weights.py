from __future__ import annotations

import ast
import json
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from serenity_alpha_lab.domain.instruments import InstrumentId
from serenity_alpha_lab.quant.backtest.ledger import PortfolioLedger
from serenity_alpha_lab.quant.backtest.orders import (
    Order,
    OrderIntent,
    OrderSide,
    OrderStatus,
    OrderType,
    TimeInForce,
)
from serenity_alpha_lab.quant.backtest.rebalance import (
    REBALANCE_POLICY_CONTRACT_VERSION,
    ModelSignal,
    RebalanceOrderGenerator,
    RebalancePolicy,
    RebalancePolicyError,
    WeightingPolicy,
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
from serenity_alpha_lab.quant.screening.pipeline import ScreenPipelineStage
from serenity_alpha_lab.quant.screening.snapshot import (
    ScreenExplanationStep,
    ScreenSnapshot,
    ScreenSnapshotResult,
    ScreenSnapshotStatus,
)


NOW = datetime(2026, 7, 25, 9, 30, tzinfo=UTC)
SIGNAL_TIME = datetime(2026, 7, 24, 15, 0, tzinfo=UTC)
TRADE_DATE = date(2026, 7, 27)
SPEC_HASH_64 = "f" * 64
SCREEN_SNAPSHOT_ID = "ssn_" + "2" * 32
SCREEN_DEFINITION_VERSION = "sdv_" + "1" * 32
FACTOR_QUALITY_VERSION = "fdv_" + "3" * 32
CODE_HASH = "sha256:" + "5" * 64
INSTRUMENT_KWEICHOW = InstrumentId.parse("600519.XSHG")
INSTRUMENT_PINGAN = InstrumentId.parse("000001.XSHE")
INSTRUMENT_CATL = InstrumentId.parse("300750.XSHE")


def test_screen_snapshot_rebalance_generates_lot_rounded_created_orders_with_cash_buffer() -> None:
    spec = _formal_backtest_spec()
    ledger = _ledger_with_positions(spec)
    generator = RebalanceOrderGenerator(spec=spec, policy=_policy(WeightingPolicy.EQUAL_WEIGHT))

    target_weights = generator.target_weights_from_screen_snapshot(_screen_snapshot())
    plan = generator.build_plan(
        ledger=ledger,
        target_weights=target_weights,
        prices={
            INSTRUMENT_KWEICHOW: Decimal("100"),
            INSTRUMENT_PINGAN: Decimal("10"),
            INSTRUMENT_CATL: Decimal("20"),
        },
        trade_date=TRADE_DATE,
        signal_time=SIGNAL_TIME,
        created_at=NOW,
        source_snapshot_id=SCREEN_SNAPSHOT_ID,
    )

    assert plan.contract_version == REBALANCE_POLICY_CONTRACT_VERSION
    assert [weight.instrument_id.canonical for weight in plan.target_weights] == [
        "600519.XSHG",
        "000001.XSHE",
        "300750.XSHE",
    ]
    assert [weight.target_weight for weight in plan.target_weights] == [
        Decimal("0.1000"),
        Decimal("0.1000"),
        Decimal("0.1000"),
    ]
    assert plan.target_weight_sum == Decimal("0.3000")
    assert plan.cash_buffer_amount == Decimal("2000.0000")
    assert plan.available_buy_cash == Decimal("77000.0000")
    assert plan.planned_sell_notional == Decimal("10000")
    assert plan.planned_buy_notional == Decimal("19000")
    assert plan.residual_cash == Decimal("58000.0000")

    assert [order.intent.side for order in plan.orders] == [OrderSide.SELL, OrderSide.BUY, OrderSide.BUY]
    assert [order.intent.instrument_id.canonical for order in plan.orders] == [
        "600519.XSHG",
        "000001.XSHE",
        "300750.XSHE",
    ]
    assert [order.intent.target_quantity for order in plan.orders] == [
        Decimal("100"),
        Decimal("900"),
        Decimal("500"),
    ]
    assert all(order.status is OrderStatus.CREATED for order in plan.orders)
    assert all(len(order.events) == 1 for order in plan.orders)
    assert all(order.intent.source == "screen_snapshot_rebalance" for order in plan.orders)
    assert plan.skipped_orders == ()

    record = plan.to_record()
    assert record["schema_name"] == "quant.backtest.rebalance_policy"
    assert record["orders"][0]["intent"]["source"] == "screen_snapshot_rebalance"
    assert all(order_record["status"] == "created" for order_record in record["orders"])
    assert "portfolioledger" not in json.dumps(record, sort_keys=True).lower()


def test_score_weighting_caps_weights_and_skips_min_notional_orders() -> None:
    spec = _formal_backtest_spec()
    ledger = _empty_ledger(spec)
    generator = RebalanceOrderGenerator(
        spec=spec,
        policy=_policy(WeightingPolicy.SCORE_PROPORTIONAL, min_order_notional=Decimal("2000")),
    )
    snapshot = _screen_snapshot(
        results=(
            _passed_result(INSTRUMENT_KWEICHOW, rank=1, final_score=100.0),
            _passed_result(INSTRUMENT_PINGAN, rank=2, final_score=2.0),
        )
    )

    target_weights = generator.target_weights_from_screen_snapshot(snapshot)
    plan = generator.build_plan(
        ledger=ledger,
        target_weights=target_weights,
        prices={INSTRUMENT_KWEICHOW: Decimal("100"), INSTRUMENT_PINGAN: Decimal("10")},
        trade_date=TRADE_DATE,
        signal_time=SIGNAL_TIME,
        created_at=NOW,
        source_snapshot_id=SCREEN_SNAPSHOT_ID,
    )

    assert [weight.target_weight for weight in target_weights] == [Decimal("0.1000"), Decimal("0.0192")]
    assert len(plan.orders) == 1
    assert plan.orders[0].intent.instrument_id == INSTRUMENT_KWEICHOW
    assert plan.orders[0].intent.target_quantity == Decimal("100")
    assert len(plan.skipped_orders) == 1
    assert plan.skipped_orders[0].instrument_id == INSTRUMENT_PINGAN
    assert plan.skipped_orders[0].reason == "min_order_notional"
    assert plan.skipped_orders[0].notional == Decimal("1000")


def test_model_signal_explicit_weights_create_deterministic_orders() -> None:
    spec = _formal_backtest_spec(strategy_kind="model_prediction_rebalance", screen_snapshot_id=None)
    ledger = _empty_ledger(spec)
    generator = RebalanceOrderGenerator(spec=spec, policy=_policy(WeightingPolicy.EXPLICIT_TARGET_WEIGHT))
    signals = (
        ModelSignal(
            signal_id="mdl-600519",
            instrument_id=INSTRUMENT_KWEICHOW,
            as_of=TRADE_DATE,
            model_version_id="model.cn.rebalance@1.0.0",
            target_weight=Decimal("0.0500"),
            rank=1,
        ),
        ModelSignal(
            signal_id="mdl-000001",
            instrument_id=INSTRUMENT_PINGAN,
            as_of=TRADE_DATE,
            model_version_id="model.cn.rebalance@1.0.0",
            target_weight=Decimal("0.0300"),
            rank=2,
        ),
    )

    target_weights = generator.target_weights_from_model_signals(signals)
    first = generator.build_plan(
        ledger=ledger,
        target_weights=target_weights,
        prices={INSTRUMENT_KWEICHOW: Decimal("50"), INSTRUMENT_PINGAN: Decimal("10")},
        trade_date=TRADE_DATE,
        signal_time=SIGNAL_TIME,
        created_at=NOW,
        source_model_version_id="model.cn.rebalance@1.0.0",
    )
    second = generator.build_plan(
        ledger=ledger,
        target_weights=target_weights,
        prices={INSTRUMENT_KWEICHOW: Decimal("50"), INSTRUMENT_PINGAN: Decimal("10")},
        trade_date=TRADE_DATE,
        signal_time=SIGNAL_TIME,
        created_at=NOW,
        source_model_version_id="model.cn.rebalance@1.0.0",
    )

    assert [weight.target_weight for weight in target_weights] == [Decimal("0.0500"), Decimal("0.0300")]
    assert first.to_record() == second.to_record()
    assert first.plan_id.startswith("rbp_")
    assert [order.intent.target_quantity for order in first.orders] == [Decimal("300"), Decimal("100")]
    assert all(order.order_id.startswith("ord_") for order in first.orders)
    assert all(order.events[0].event_id.startswith("evt_") for order in first.orders)
    json.dumps(first.to_record(), sort_keys=True)


def test_rebalance_rejects_bad_bindings_and_stays_pure() -> None:
    spec = _formal_backtest_spec()
    generator = RebalanceOrderGenerator(spec=spec, policy=_policy(WeightingPolicy.EQUAL_WEIGHT))

    with pytest.raises(RebalancePolicyError, match="screen_snapshot_id must match BacktestSpec"):
        generator.target_weights_from_screen_snapshot(_screen_snapshot(screen_snapshot_id="ssn_" + "9" * 32))

    with pytest.raises(RebalancePolicyError, match="target_weight cannot be less than"):
        ModelSignal(
            signal_id="bad-negative-weight",
            instrument_id=INSTRUMENT_KWEICHOW,
            as_of=TRADE_DATE,
            model_version_id="model.cn.rebalance@1.0.0",
            target_weight=Decimal("-0.01"),
        )

    with pytest.raises(RebalancePolicyError, match="latest is not allowed"):
        ModelSignal(
            signal_id="bad-latest-model",
            instrument_id=INSTRUMENT_KWEICHOW,
            as_of=TRADE_DATE,
            model_version_id="latest",
            target_weight=Decimal("0.01"),
        )

    target_weights = generator.target_weights_from_screen_snapshot(_screen_snapshot())
    with pytest.raises(RebalancePolicyError, match="missing rebalance price"):
        generator.build_plan(
            ledger=_ledger_with_positions(spec),
            target_weights=target_weights,
            prices={INSTRUMENT_KWEICHOW: Decimal("100")},
            trade_date=TRADE_DATE,
            signal_time=SIGNAL_TIME,
            created_at=NOW,
            source_snapshot_id=SCREEN_SNAPSHOT_ID,
        )

    source = Path("src/serenity_alpha_lab/quant/backtest/rebalance.py").read_text()
    tree = ast.parse(source)
    imported_roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_roots.add(node.module.split(".")[0])

    assert not {"qlib", "pyqlib", "fastapi", "sqlalchemy"}.intersection(imported_roots)


def _formal_backtest_spec(
    *,
    strategy_kind: str = "screen_snapshot_rebalance",
    screen_snapshot_id: str | None = SCREEN_SNAPSHOT_ID,
) -> BacktestSpec:
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
        created_by_run_id="run-rebalance",
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
            strategy_kind=strategy_kind,
            source_commit="abcdef1234567890",
            code_hash=CODE_HASH,
            screen_definition_version_id=SCREEN_DEFINITION_VERSION,
            screen_snapshot_id=screen_snapshot_id,
            factor_version_ids=(FACTOR_QUALITY_VERSION,),
            model_version_id="model.cn.rebalance@1.0.0" if strategy_kind == "model_prediction_rebalance" else None,
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


def _policy(
    weighting_policy: WeightingPolicy,
    *,
    min_order_notional: Decimal = Decimal("500"),
) -> RebalancePolicy:
    return RebalancePolicy(
        policy_id="cn_a_share_weekly_rebalance",
        policy_version="1.0.0",
        weighting_policy=weighting_policy,
        min_order_notional=min_order_notional,
        order_type=OrderType.MARKET,
        time_in_force=TimeInForce.DAY,
    )


def _empty_ledger(spec: BacktestSpec) -> PortfolioLedger:
    return PortfolioLedger.open(
        run_id="run-rebalance",
        stage_id="stage-rebalance",
        spec_id=spec.spec_id,
        spec_hash=spec.spec_hash,
        base_currency="CNY",
        initial_cash=Decimal("100000"),
        event_id="led-initial-cash",
        occurred_at=NOW,
    )


def _ledger_with_positions(spec: BacktestSpec) -> PortfolioLedger:
    ledger = _empty_ledger(spec)
    ledger = _record_filled_buy(ledger, spec, INSTRUMENT_KWEICHOW, order_id="ord-existing-kweichow", quantity=Decimal("200"), price=Decimal("100"))
    ledger = _record_filled_buy(ledger, spec, INSTRUMENT_PINGAN, order_id="ord-existing-pingan", quantity=Decimal("100"), price=Decimal("10"))
    ledger = ledger.settle_payable(
        event_id="led-settle-existing",
        occurred_at=NOW,
        settlement_date=date(2026, 7, 26),
        amount=Decimal("21000"),
        source_execution_id="exe-existing",
    )
    return ledger.mark_to_market(
        event_id="led-mtm-existing",
        occurred_at=NOW,
        valuation_date=date(2026, 7, 25),
        prices={INSTRUMENT_KWEICHOW: Decimal("100"), INSTRUMENT_PINGAN: Decimal("10")},
    )


def _record_filled_buy(
    ledger: PortfolioLedger,
    spec: BacktestSpec,
    instrument_id: InstrumentId,
    *,
    order_id: str,
    quantity: Decimal,
    price: Decimal,
) -> PortfolioLedger:
    order = Order.create(
        intent=OrderIntent(
            order_id=order_id,
            run_id=ledger.run_id,
            stage_id=ledger.stage_id,
            spec_id=spec.spec_id,
            spec_hash=spec.spec_hash,
            instrument_id=instrument_id,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            target_quantity=quantity,
            trade_date=TRADE_DATE,
            signal_time=SIGNAL_TIME,
            created_at=NOW,
            time_in_force=TimeInForce.DAY,
            source="fixture_existing_position",
        ),
        event_id=f"evt-created-{order_id}",
        occurred_at=NOW,
    ).accept(event_id=f"evt-accepted-{order_id}", occurred_at=NOW)
    order = order.record_fill(
        event_id=f"evt-fill-{order_id}",
        occurred_at=NOW,
        fill_quantity=quantity,
        fill_price=price,
        execution_id=f"exe-{order_id}",
    )
    return ledger.record_execution(
        order=order,
        fill_event=order.events[-1],
        event_id=f"led-{order_id}",
        occurred_at=NOW,
        trade_date=TRADE_DATE,
        settlement_date=date(2026, 7, 26),
    )


def _screen_snapshot(
    *,
    screen_snapshot_id: str = SCREEN_SNAPSHOT_ID,
    results: tuple[ScreenSnapshotResult, ...] | None = None,
) -> ScreenSnapshot:
    return ScreenSnapshot(
        pipeline_snapshot_id="sps_" + "8" * 32,
        definition_version_id=SCREEN_DEFINITION_VERSION,
        as_of=date(2026, 7, 25),
        dataset_versions={"universe": "dsv_" + "f" * 32},
        results=results
        or (
            _passed_result(INSTRUMENT_KWEICHOW, rank=1, final_score=90.0),
            _passed_result(INSTRUMENT_PINGAN, rank=2, final_score=80.0),
            _passed_result(INSTRUMENT_CATL, rank=3, final_score=70.0),
        ),
        created_at=NOW,
        trace_id="trace-rebalance",
        run_id="run-rebalance",
        stage_id="stage-screen",
        screen_snapshot_id=screen_snapshot_id,
    )


def _passed_result(instrument_id: InstrumentId, *, rank: int, final_score: float) -> ScreenSnapshotResult:
    return ScreenSnapshotResult(
        instrument_id=instrument_id.canonical,
        status=ScreenSnapshotStatus.PASSED,
        rank=rank,
        final_score=final_score,
        scores={"l4_final": final_score},
        factor_contributions={"quality": final_score},
        reason_codes=("l4_final_passed",),
        explanation_steps=(
            ScreenExplanationStep(
                stage=ScreenPipelineStage.L4_FINAL,
                rule_id="l4_final_passed",
                reason="instrument passed deterministic final screen gates",
                scores={"l4_final": final_score},
                factor_contributions={"quality": final_score},
            ),
        ),
    )
