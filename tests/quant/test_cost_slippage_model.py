from __future__ import annotations

import ast
import json
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from serenity_alpha_lab.domain.instruments import InstrumentId
from serenity_alpha_lab.quant.backtest.costs import (
    BACKTEST_COST_MODEL_CONTRACT_VERSION,
    CostModel,
    CostModelError,
)
from serenity_alpha_lab.quant.backtest.ledger import PortfolioLedger
from serenity_alpha_lab.quant.backtest.orders import (
    Order,
    OrderIntent,
    OrderSide,
    OrderType,
    TimeInForce,
)
from serenity_alpha_lab.quant.backtest.spec import BacktestCostSpec


NOW = datetime(2026, 7, 25, 9, 30, tzinfo=UTC)
SPEC_HASH = "sha256:" + "6" * 64
INSTRUMENT = InstrumentId.parse("600519.XSHG")


def test_cost_model_calculates_buy_and_sell_fee_asymmetry_and_effective_prices() -> None:
    model = CostModel(spec_hash=SPEC_HASH, cost_spec=_cost_spec())
    buy_order = _filled_order(
        side=OrderSide.BUY,
        order_id="ord-buy-100",
        quantity=Decimal("100"),
        price=Decimal("10"),
    )
    sell_order = _filled_order(
        side=OrderSide.SELL,
        order_id="ord-sell-100",
        quantity=Decimal("100"),
        price=Decimal("10"),
    )

    buy_cost = model.calculate(order=buy_order, fill_event=buy_order.events[-1], market_volume=Decimal("2000"))
    sell_cost = model.calculate(order=sell_order, fill_event=sell_order.events[-1], market_volume=Decimal("2000"))

    assert buy_cost.contract_version == BACKTEST_COST_MODEL_CONTRACT_VERSION
    assert buy_cost.gross_amount == Decimal("1000")
    assert buy_cost.line_item_amount("commission") == Decimal("5.00")
    assert buy_cost.line_item_amount("stamp_tax") == Decimal("0")
    assert buy_cost.line_item_amount("transfer_fee") == Decimal("0.02")
    assert buy_cost.line_item_amount("slippage") == Decimal("0.5")
    assert buy_cost.line_item_amount("impact") == Decimal("0.2")
    assert buy_cost.total_cost == Decimal("5.72")
    assert buy_cost.effective_price == Decimal("10.007")
    assert buy_cost.participation_rate == Decimal("0.05")

    assert sell_cost.line_item_amount("commission") == Decimal("5.00")
    assert sell_cost.line_item_amount("stamp_tax") == Decimal("1.0")
    assert sell_cost.line_item_amount("transfer_fee") == Decimal("0.02")
    assert sell_cost.total_cost == Decimal("6.72")
    assert sell_cost.effective_price == Decimal("9.993")
    assert sell_cost.to_record()["line_items"]["stamp_tax"]["applies_to_side"] == "sell"


def test_cost_model_rejects_participation_breaches_and_emits_stable_records() -> None:
    model = CostModel(spec_hash=SPEC_HASH, cost_spec=_cost_spec())
    order = _filled_order(
        side=OrderSide.BUY,
        order_id="ord-participation",
        quantity=Decimal("100"),
        price=Decimal("10"),
    )

    with pytest.raises(CostModelError, match="participation rate exceeds maximum"):
        model.calculate(order=order, fill_event=order.events[-1], market_volume=Decimal("500"))

    cost = model.calculate(order=order, fill_event=order.events[-1], market_volume=Decimal("1000"))
    record = cost.to_record()

    assert record["schema_name"] == "quant.backtest.cost_model"
    assert record["schema_version"] == "1.0.0"
    assert record["model_version"] == "cn_a_share_cost_model@1.0.0"
    assert record["spec_hash"] == SPEC_HASH
    assert record["participation_rate"] == "0.1"
    assert record["max_participation_rate"] == "0.1000"
    assert record["total_cost"] == "5.72"
    assert list(record["line_items"]) == ["commission", "stamp_tax", "transfer_fee", "slippage", "impact"]
    json.dumps(record, sort_keys=True)


def test_cost_breakdown_feeds_ledger_without_mutating_accounting_layer() -> None:
    model = CostModel(spec_hash=SPEC_HASH, cost_spec=_cost_spec())
    order = _filled_order(
        side=OrderSide.BUY,
        order_id="ord-ledger-cost",
        quantity=Decimal("100"),
        price=Decimal("10"),
    )
    cost = model.calculate(order=order, fill_event=order.events[-1], market_volume=Decimal("2000"))
    ledger = PortfolioLedger.open(
        run_id="run-cost",
        stage_id="stage-cost",
        spec_id="formal_cn_quality_momentum_v1",
        spec_hash=SPEC_HASH,
        base_currency="CNY",
        initial_cash=Decimal("100000"),
        event_id="led-initial",
        occurred_at=NOW,
    )

    updated = ledger.record_execution(
        order=order,
        fill_event=order.events[-1],
        event_id="led-buy-with-cost",
        occurred_at=NOW,
        trade_date=date(2026, 7, 27),
        settlement_date=date(2026, 7, 28),
        transaction_cost=cost.total_cost,
    )

    assert ledger.events != updated.events
    assert updated.payables == Decimal("1005.72")
    assert updated.executions[-1].transaction_cost == Decimal("5.72")
    assert updated.position_lots[-1].cost_basis == Decimal("1005.72")


def test_cost_model_module_stays_inside_pure_contract_boundary() -> None:
    source = Path("src/serenity_alpha_lab/quant/backtest/costs.py").read_text()
    tree = ast.parse(source)
    imported_roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_roots.add(node.module.split(".")[0])

    assert not {"qlib", "pyqlib", "fastapi", "sqlalchemy"}.intersection(imported_roots)


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


def _filled_order(
    *,
    side: OrderSide,
    order_id: str,
    quantity: Decimal,
    price: Decimal,
) -> Order:
    return (
        Order.create(
            intent=OrderIntent(
                order_id=order_id,
                run_id="run-cost",
                stage_id="stage-cost",
                spec_id="formal_cn_quality_momentum_v1",
                spec_hash=SPEC_HASH,
                instrument_id=INSTRUMENT,
                side=side,
                order_type=OrderType.MARKET,
                target_quantity=quantity,
                trade_date=date(2026, 7, 27),
                signal_time=datetime(2026, 7, 25, 15, 0, tzinfo=UTC),
                created_at=NOW,
                time_in_force=TimeInForce.DAY,
                source="screen_snapshot_rebalance",
            ),
            event_id=f"evt-created-{order_id}",
            occurred_at=NOW,
        )
        .accept(event_id=f"evt-accepted-{order_id}", occurred_at=NOW)
        .record_fill(
            event_id=f"evt-fill-{order_id}",
            occurred_at=NOW,
            fill_quantity=quantity,
            fill_price=price,
            execution_id=f"exe-{order_id}",
        )
    )
