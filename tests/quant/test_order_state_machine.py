from __future__ import annotations

import ast
import json
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from serenity_alpha_lab.domain.instruments import InstrumentId
from serenity_alpha_lab.quant.backtest.orders import (
    ORDER_STATE_MACHINE_CONTRACT_VERSION,
    Order,
    OrderEvent,
    OrderEventType,
    OrderIntent,
    OrderSide,
    OrderStateMachineError,
    OrderStatus,
    OrderType,
    TimeInForce,
)


NOW = datetime(2026, 7, 25, 9, 30, tzinfo=UTC)
SPEC_HASH = "sha256:" + "1" * 64
INSTRUMENT = InstrumentId.parse("600519.XSHG")


def test_order_accepts_partial_fills_and_reaches_filled_terminal_state() -> None:
    order = Order.create(
        intent=_order_intent(target_quantity=Decimal("300")),
        event_id="evt-created",
        occurred_at=NOW,
    )

    accepted = order.accept(event_id="evt-accepted", occurred_at=NOW, reason="passes pre-trade checks")
    partial = accepted.record_fill(
        event_id="evt-fill-100",
        occurred_at=NOW,
        fill_quantity=Decimal("100"),
        fill_price=Decimal("1688.50"),
        execution_id="exe-001",
    )
    filled = partial.record_fill(
        event_id="evt-fill-200",
        occurred_at=NOW,
        fill_quantity=Decimal("200"),
        fill_price=Decimal("1689.00"),
        execution_id="exe-002",
    )

    assert order.status is OrderStatus.CREATED
    assert accepted.status is OrderStatus.ACCEPTED
    assert partial.status is OrderStatus.PARTIALLY_FILLED
    assert partial.filled_quantity == Decimal("100")
    assert partial.remaining_quantity == Decimal("200")
    assert filled.status is OrderStatus.FILLED
    assert filled.filled_quantity == Decimal("300")
    assert filled.remaining_quantity == Decimal("0")
    assert [event.sequence for event in filled.events] == [1, 2, 3, 4]
    assert [event.event_type for event in filled.events] == [
        OrderEventType.CREATED,
        OrderEventType.ACCEPTED,
        OrderEventType.PARTIALLY_FILLED,
        OrderEventType.FILLED,
    ]

    record = filled.to_record()
    assert record["contract_version"] == ORDER_STATE_MACHINE_CONTRACT_VERSION
    assert record["order_id"] == "ord-cn-001"
    assert record["status"] == "filled"
    assert record["filled_quantity"] == "300"
    assert record["remaining_quantity"] == "0"
    assert record["last_event"]["event_type"] == "filled"
    assert record["intent"]["instrument_id"] == "600519.XSHG"
    assert "ledger" not in json.dumps(record, sort_keys=True).lower()
    assert "cash" not in json.dumps(record, sort_keys=True).lower()
    assert "position" not in json.dumps(record, sort_keys=True).lower()


def test_order_rejects_invalid_transitions_and_terminal_mutation() -> None:
    order = Order.create(intent=_order_intent(), event_id="evt-created", occurred_at=NOW)

    with pytest.raises(OrderStateMachineError, match="accepted orders can record fills"):
        order.record_fill(
            event_id="evt-fill-too-early",
            occurred_at=NOW,
            fill_quantity=Decimal("100"),
            fill_price=Decimal("1688.50"),
            execution_id="exe-early",
        )

    accepted = order.accept(event_id="evt-accepted", occurred_at=NOW)

    with pytest.raises(OrderStateMachineError, match="exceeds remaining quantity"):
        accepted.record_fill(
            event_id="evt-overfill",
            occurred_at=NOW,
            fill_quantity=Decimal("200"),
            fill_price=Decimal("1688.50"),
            execution_id="exe-overfill",
        )

    filled = accepted.record_fill(
        event_id="evt-fill",
        occurred_at=NOW,
        fill_quantity=Decimal("100"),
        fill_price=Decimal("1688.50"),
        execution_id="exe-fill",
    )

    with pytest.raises(OrderStateMachineError, match="terminal"):
        filled.cancel(event_id="evt-cancel-filled", occurred_at=NOW, reason="late cancel")

    with pytest.raises(OrderStateMachineError, match="terminal"):
        filled.accept(event_id="evt-reaccept-filled", occurred_at=NOW)


def test_rejection_expiration_and_cancellation_store_reasons_and_stop_transitions() -> None:
    rejected = Order.create(intent=_order_intent(order_id="ord-reject"), event_id="evt-created", occurred_at=NOW).reject(
        event_id="evt-reject",
        occurred_at=NOW,
        reason="limit_up_unfillable",
    )
    expired = (
        Order.create(intent=_order_intent(order_id="ord-expire"), event_id="evt-created", occurred_at=NOW)
        .accept(event_id="evt-accepted", occurred_at=NOW)
        .expire(event_id="evt-expire", occurred_at=NOW, reason="expire_after_rebalance")
    )
    cancelled = (
        Order.create(intent=_order_intent(order_id="ord-cancel"), event_id="evt-created", occurred_at=NOW)
        .accept(event_id="evt-accepted", occurred_at=NOW)
        .cancel(event_id="evt-cancel", occurred_at=NOW, reason="user_requested_cancel")
    )

    assert rejected.status is OrderStatus.REJECTED
    assert rejected.reason == "limit_up_unfillable"
    assert expired.status is OrderStatus.EXPIRED
    assert expired.reason == "expire_after_rebalance"
    assert cancelled.status is OrderStatus.CANCELLED
    assert cancelled.reason == "user_requested_cancel"

    partially_expired = (
        Order.create(
            intent=_order_intent(order_id="ord-partial-expire"),
            event_id="evt-created",
            occurred_at=NOW,
        )
        .accept(event_id="evt-accepted", occurred_at=NOW)
        .record_fill(
            event_id="evt-fill-40",
            occurred_at=NOW,
            fill_quantity=Decimal("40"),
            fill_price=Decimal("1688.50"),
            execution_id="exe-partial",
        )
        .expire(event_id="evt-expire-partial", occurred_at=NOW, reason="expire_after_rebalance")
    )
    assert partially_expired.status is OrderStatus.EXPIRED
    assert partially_expired.filled_quantity == Decimal("40")
    assert partially_expired.remaining_quantity == Decimal("60")
    assert partially_expired.reason == "expire_after_rebalance"

    for terminal_order in (rejected, expired, cancelled):
        with pytest.raises(OrderStateMachineError, match="terminal"):
            terminal_order.accept(event_id=f"{terminal_order.order_id}-late-accept", occurred_at=NOW)


def test_replay_is_deterministic_and_duplicate_events_are_idempotent() -> None:
    order = (
        Order.create(intent=_order_intent(), event_id="evt-created", occurred_at=NOW)
        .accept(event_id="evt-accepted", occurred_at=NOW)
        .record_fill(
            event_id="evt-fill",
            occurred_at=NOW,
            fill_quantity=Decimal("100"),
            fill_price=Decimal("1688.50"),
            execution_id="exe-fill",
        )
    )
    events_with_duplicate = (*order.events, order.events[-1])

    replayed = Order.replay(order.intent, events_with_duplicate)
    replayed_again = Order.replay(order.intent, events_with_duplicate)

    assert replayed.to_record() == order.to_record()
    assert replayed_again.to_record() == replayed.to_record()

    conflicting_duplicate = OrderEvent(
        event_id="evt-fill",
        order_id=order.order_id,
        sequence=3,
        event_type=OrderEventType.PARTIALLY_FILLED,
        occurred_at=NOW,
        status_after=OrderStatus.PARTIALLY_FILLED,
        fill_quantity=Decimal("50"),
        fill_price=Decimal("1688.50"),
        execution_id="exe-conflict",
    )
    with pytest.raises(OrderStateMachineError, match="conflicting duplicate event_id"):
        Order.replay(order.intent, (*order.events, conflicting_duplicate))


def test_order_state_machine_module_stays_inside_pure_contract_boundary() -> None:
    source = Path("src/serenity_alpha_lab/quant/backtest/orders.py").read_text()
    tree = ast.parse(source)
    imported_roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_roots.add(node.module.split(".")[0])

    assert not {"qlib", "pyqlib", "fastapi", "sqlalchemy"}.intersection(imported_roots)


def _order_intent(
    *,
    order_id: str = "ord-cn-001",
    target_quantity: Decimal = Decimal("100"),
) -> OrderIntent:
    return OrderIntent(
        order_id=order_id,
        run_id="run-order-state",
        stage_id="stage-orders",
        spec_id="formal_cn_quality_momentum_v1",
        spec_hash=SPEC_HASH,
        instrument_id=INSTRUMENT,
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        target_quantity=target_quantity,
        trade_date=date(2026, 7, 27),
        signal_time=datetime(2026, 7, 25, 15, 0, tzinfo=UTC),
        created_at=NOW,
        time_in_force=TimeInForce.DAY,
        source="screen_snapshot_rebalance",
    )
