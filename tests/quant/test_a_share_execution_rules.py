from __future__ import annotations

import ast
import json
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from serenity_alpha_lab.domain.instruments import InstrumentId
from serenity_alpha_lab.quant.backtest.costs import CostModel
from serenity_alpha_lab.quant.backtest.execution import (
    A_SHARE_EXECUTION_MODEL_CONTRACT_VERSION,
    AShareExecutionError,
    AShareExecutionModel,
    AShareExecutionOutcome,
    AShareExecutionStatus,
    AShareMarketSnapshot,
    ASharePositionAvailability,
)
from serenity_alpha_lab.quant.backtest.orders import (
    Order,
    OrderIntent,
    OrderSide,
    OrderStatus,
    OrderType,
    TimeInForce,
)
from serenity_alpha_lab.quant.backtest.spec import BacktestCostSpec, BacktestExecutionSpec


SPEC_HASH = "sha256:" + "7" * 64
INSTRUMENT = InstrumentId.parse("600519.XSHG")
TRADE_DATE = date(2026, 7, 27)
SIGNAL_TIME = datetime(2026, 7, 24, 15, 0, tzinfo=UTC)
EXECUTION_TIME = datetime(2026, 7, 27, 9, 30, tzinfo=UTC)


def test_a_share_execution_fills_next_trade_day_order_and_returns_cost_audit() -> None:
    model = _execution_model()
    order = _created_order(side=OrderSide.BUY, quantity=Decimal("100"))

    result = model.execute(
        order=order,
        market_snapshot=_market_snapshot(open_price=Decimal("10"), volume=Decimal("2000")),
        occurred_at=EXECUTION_TIME,
        event_id_prefix="exec-fillable",
    )

    assert result.contract_version == A_SHARE_EXECUTION_MODEL_CONTRACT_VERSION
    assert result.status is AShareExecutionStatus.FILLED
    assert result.order.status is OrderStatus.FILLED
    assert result.fill_event is result.order.events[-1]
    assert result.fill_event.execution_id == "exec-fillable-fill"
    assert result.fill_event.fill_price == Decimal("10")
    assert result.cost_breakdown is not None
    assert result.cost_breakdown.total_cost == Decimal("5.72")
    assert result.execution_price == Decimal("10")
    assert result.executed_quantity == Decimal("100")

    audit_by_rule = _audit_by_rule(result)
    assert audit_by_rule["signal_available_before_execution"].outcome is AShareExecutionOutcome.PASS
    assert audit_by_rule["trade_unit_lot_size"].outcome is AShareExecutionOutcome.PASS
    assert audit_by_rule["market_tradable_status"].outcome is AShareExecutionOutcome.PASS
    assert audit_by_rule["limit_up_down_executable"].outcome is AShareExecutionOutcome.PASS
    assert audit_by_rule["cost_model_participation"].outcome is AShareExecutionOutcome.PASS

    record = result.to_record()
    assert record["schema_name"] == "quant.backtest.a_share_execution_model"
    assert record["status"] == "filled"
    assert record["cost_breakdown"]["total_cost"] == "5.72"
    assert record["order"]["status"] == "filled"
    serialized = json.dumps(record, sort_keys=True)
    assert "portfolioledger" not in serialized.lower()
    assert "backtestartifact" not in serialized.lower()


def test_t_plus_one_signal_timing_and_sellable_quantity_are_enforced() -> None:
    model = _execution_model()
    same_bar_order = _created_order(
        side=OrderSide.BUY,
        quantity=Decimal("100"),
        order_id="ord-same-day-close",
        signal_time=datetime(2026, 7, 27, 15, 0, tzinfo=UTC),
    )

    same_bar_result = model.execute(
        order=same_bar_order,
        market_snapshot=_market_snapshot(),
        occurred_at=EXECUTION_TIME,
        event_id_prefix="exec-same-bar",
    )

    assert same_bar_result.status is AShareExecutionStatus.REJECTED
    assert same_bar_result.order.status is OrderStatus.REJECTED
    assert same_bar_result.reason == "signal_not_available_for_execution"
    assert _audit_by_rule(same_bar_result)["signal_available_before_execution"].outcome is AShareExecutionOutcome.BLOCK

    sell_order = _created_order(
        side=OrderSide.SELL,
        quantity=Decimal("200"),
        order_id="ord-sell-t-plus-one",
    )
    sell_result = model.execute(
        order=sell_order,
        market_snapshot=_market_snapshot(),
        occurred_at=EXECUTION_TIME,
        event_id_prefix="exec-sell-t-plus-one",
        position_availability=ASharePositionAvailability(
            instrument_id=INSTRUMENT,
            trade_date=TRADE_DATE,
            total_quantity=Decimal("300"),
            sellable_quantity=Decimal("100"),
            locked_t_plus_one_quantity=Decimal("200"),
        ),
    )

    assert sell_result.status is AShareExecutionStatus.EXPIRED
    assert sell_result.order.status is OrderStatus.EXPIRED
    assert sell_result.reason == "t_plus_one_sell_restricted"
    assert _audit_by_rule(sell_result)["t_plus_one_sellable_quantity"].outcome is AShareExecutionOutcome.BLOCK


def test_trade_unit_and_suspension_create_auditable_rejections() -> None:
    model = _execution_model()

    odd_lot_result = model.execute(
        order=_created_order(side=OrderSide.BUY, quantity=Decimal("150"), order_id="ord-odd-lot"),
        market_snapshot=_market_snapshot(),
        occurred_at=EXECUTION_TIME,
        event_id_prefix="exec-odd-lot",
    )

    assert odd_lot_result.status is AShareExecutionStatus.REJECTED
    assert odd_lot_result.order.status is OrderStatus.REJECTED
    assert odd_lot_result.reason == "invalid_trade_unit"
    assert _audit_by_rule(odd_lot_result)["trade_unit_lot_size"].outcome is AShareExecutionOutcome.BLOCK

    suspended_result = model.execute(
        order=_created_order(side=OrderSide.BUY, quantity=Decimal("100"), order_id="ord-suspended"),
        market_snapshot=_market_snapshot(is_suspended=True),
        occurred_at=EXECUTION_TIME,
        event_id_prefix="exec-suspended",
    )

    assert suspended_result.status is AShareExecutionStatus.REJECTED
    assert suspended_result.order.status is OrderStatus.REJECTED
    assert suspended_result.reason == "security_suspended"
    assert _audit_by_rule(suspended_result)["market_tradable_status"].outcome is AShareExecutionOutcome.BLOCK


def test_limit_up_down_and_limit_price_unfillable_orders_use_policy() -> None:
    model = _execution_model()

    limit_up_buy = model.execute(
        order=_created_order(side=OrderSide.BUY, quantity=Decimal("100"), order_id="ord-buy-limit-up"),
        market_snapshot=_market_snapshot(open_price=Decimal("11.00"), limit_up_price=Decimal("11.00")),
        occurred_at=EXECUTION_TIME,
        event_id_prefix="exec-buy-limit-up",
    )
    assert limit_up_buy.status is AShareExecutionStatus.EXPIRED
    assert limit_up_buy.order.status is OrderStatus.EXPIRED
    assert limit_up_buy.reason == "limit_up_unfillable"

    limit_down_sell = model.execute(
        order=_created_order(side=OrderSide.SELL, quantity=Decimal("100"), order_id="ord-sell-limit-down"),
        market_snapshot=_market_snapshot(open_price=Decimal("9.00"), limit_down_price=Decimal("9.00")),
        occurred_at=EXECUTION_TIME,
        event_id_prefix="exec-sell-limit-down",
        position_availability=_sellable_position(Decimal("100")),
    )
    assert limit_down_sell.status is AShareExecutionStatus.EXPIRED
    assert limit_down_sell.order.status is OrderStatus.EXPIRED
    assert limit_down_sell.reason == "limit_down_unfillable"

    buy_limit_not_crossed = model.execute(
        order=_created_order(
            side=OrderSide.BUY,
            quantity=Decimal("100"),
            order_id="ord-buy-limit-not-crossed",
            order_type=OrderType.LIMIT,
            limit_price=Decimal("9.99"),
        ),
        market_snapshot=_market_snapshot(open_price=Decimal("10.00")),
        occurred_at=EXECUTION_TIME,
        event_id_prefix="exec-buy-limit-not-crossed",
    )
    assert buy_limit_not_crossed.status is AShareExecutionStatus.EXPIRED
    assert buy_limit_not_crossed.reason == "limit_price_not_crossed"
    assert _audit_by_rule(buy_limit_not_crossed)["order_limit_price_crosses_execution_price"].outcome is (
        AShareExecutionOutcome.BLOCK
    )


def test_keep_open_unfilled_policy_preserves_accepted_order_with_audit() -> None:
    model = _execution_model(
        BacktestExecutionSpec(
            signal_timing="after_close",
            execution_timing="next_open",
            signal_price_field="close",
            execution_price_field="open",
            rebalance_calendar="cn_a_share_trading_calendar",
            valuation_calendar="cn_a_share_trading_calendar",
            rebalance_frequency="daily",
            settlement_lag_days=1,
            lot_size=100,
            random_seed=20260725,
            unfilled_order_policy="keep_open_until_cancelled",
        )
    )

    result = model.execute(
        order=_created_order(side=OrderSide.BUY, quantity=Decimal("100"), order_id="ord-keep-open"),
        market_snapshot=_market_snapshot(open_price=Decimal("11.00"), limit_up_price=Decimal("11.00")),
        occurred_at=EXECUTION_TIME,
        event_id_prefix="exec-keep-open",
    )

    assert result.status is AShareExecutionStatus.KEPT_OPEN
    assert result.order.status is OrderStatus.ACCEPTED
    assert result.fill_event is None
    assert result.cost_breakdown is None
    assert result.reason == "limit_up_unfillable"
    assert result.to_record()["order"]["status"] == "accepted"


def test_a_share_execution_model_rejects_bad_bindings_and_stays_pure() -> None:
    model = _execution_model()

    with pytest.raises(AShareExecutionError, match="market_snapshot instrument_id must match order"):
        model.execute(
            order=_created_order(side=OrderSide.BUY, quantity=Decimal("100")),
            market_snapshot=_market_snapshot(instrument_id=InstrumentId.parse("000001.XSHE")),
            occurred_at=EXECUTION_TIME,
            event_id_prefix="exec-bad-instrument",
        )

    source = Path("src/serenity_alpha_lab/quant/backtest/execution.py").read_text()
    tree = ast.parse(source)
    imported_roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_roots.add(node.module.split(".")[0])

    assert not {"qlib", "pyqlib", "fastapi", "sqlalchemy"}.intersection(imported_roots)


def _execution_model(execution_spec: BacktestExecutionSpec | None = None) -> AShareExecutionModel:
    return AShareExecutionModel(
        spec_hash=SPEC_HASH,
        execution_spec=execution_spec or _execution_spec(),
        cost_model=CostModel(spec_hash=SPEC_HASH, cost_spec=_cost_spec()),
    )


def _execution_spec() -> BacktestExecutionSpec:
    return BacktestExecutionSpec(
        signal_timing="after_close",
        execution_timing="next_open",
        signal_price_field="close",
        execution_price_field="open",
        rebalance_calendar="cn_a_share_trading_calendar",
        valuation_calendar="cn_a_share_trading_calendar",
        rebalance_frequency="daily",
        settlement_lag_days=1,
        lot_size=100,
        random_seed=20260725,
    )


def _cost_spec() -> BacktestCostSpec:
    return BacktestCostSpec(
        commission_bps=Decimal("3.0"),
        min_commission=Decimal("5.00"),
        stamp_tax_bps=Decimal("10.0"),
        transfer_fee_bps=Decimal("0.2"),
        slippage_bps=Decimal("5.0"),
        impact_bps=Decimal("2.0"),
        max_participation_rate=Decimal("0.1000"),
    )


def _created_order(
    *,
    side: OrderSide,
    quantity: Decimal,
    order_id: str = "ord-execution-001",
    signal_time: datetime = SIGNAL_TIME,
    order_type: OrderType = OrderType.MARKET,
    limit_price: Decimal | None = None,
) -> Order:
    return Order.create(
        intent=OrderIntent(
            order_id=order_id,
            run_id="run-a-share-execution",
            stage_id="stage-a-share-execution",
            spec_id="formal_cn_quality_momentum_v1",
            spec_hash=SPEC_HASH,
            instrument_id=INSTRUMENT,
            side=side,
            order_type=order_type,
            target_quantity=quantity,
            trade_date=TRADE_DATE,
            signal_time=signal_time,
            created_at=datetime(2026, 7, 25, 9, 30, tzinfo=UTC),
            time_in_force=TimeInForce.DAY,
            limit_price=limit_price,
            source="screen_snapshot_rebalance",
        ),
        event_id=f"evt-created-{order_id}",
        occurred_at=datetime(2026, 7, 25, 9, 30, tzinfo=UTC),
    )


def _market_snapshot(
    *,
    instrument_id: InstrumentId = INSTRUMENT,
    open_price: Decimal = Decimal("10.00"),
    volume: Decimal = Decimal("2000"),
    is_trading: bool = True,
    is_suspended: bool = False,
    limit_up_price: Decimal = Decimal("11.00"),
    limit_down_price: Decimal = Decimal("9.00"),
) -> AShareMarketSnapshot:
    return AShareMarketSnapshot(
        instrument_id=instrument_id,
        trade_date=TRADE_DATE,
        open=open_price,
        high=max(open_price, Decimal("10.20")),
        low=min(open_price, Decimal("9.80")),
        close=open_price,
        volume=volume,
        is_trading=is_trading,
        is_suspended=is_suspended,
        limit_up_price=limit_up_price,
        limit_down_price=limit_down_price,
        source_dataset_version="dsv_" + "a" * 32,
    )


def _sellable_position(sellable_quantity: Decimal) -> ASharePositionAvailability:
    return ASharePositionAvailability(
        instrument_id=INSTRUMENT,
        trade_date=TRADE_DATE,
        total_quantity=sellable_quantity,
        sellable_quantity=sellable_quantity,
        locked_t_plus_one_quantity=Decimal("0"),
    )


def _audit_by_rule(result) -> dict[str, object]:
    return {record.rule_id: record for record in result.audit_records}
