from __future__ import annotations

import ast
import json
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from serenity_alpha_lab.domain.instruments import InstrumentId
from serenity_alpha_lab.quant.backtest.ledger import (
    PORTFOLIO_LEDGER_CONTRACT_VERSION,
    LedgerEvent,
    LedgerEventType,
    PortfolioLedger,
    PortfolioLedgerError,
)
from serenity_alpha_lab.quant.backtest.orders import (
    Order,
    OrderEvent,
    OrderEventType,
    OrderIntent,
    OrderSide,
    OrderStatus,
    OrderType,
    TimeInForce,
)


NOW = datetime(2026, 7, 25, 9, 30, tzinfo=UTC)
SPEC_HASH = "sha256:" + "2" * 64
INSTRUMENT = InstrumentId.parse("600519.XSHG")


def test_portfolio_ledger_replays_cash_positions_receivables_payables_and_equity() -> None:
    ledger = PortfolioLedger.open(
        run_id="run-ledger",
        stage_id="stage-ledger",
        spec_id="formal_cn_quality_momentum_v1",
        spec_hash=SPEC_HASH,
        base_currency="CNY",
        initial_cash=Decimal("1000000"),
        event_id="led-initial-cash",
        occurred_at=NOW,
    )
    buy_order = _filled_order(side=OrderSide.BUY, order_id="ord-buy-100", quantity=Decimal("100"), price=Decimal("10"))
    buy_fill = buy_order.events[-1]

    ledger = ledger.record_execution(
        order=buy_order,
        fill_event=buy_fill,
        event_id="led-buy-100",
        occurred_at=NOW,
        trade_date=date(2026, 7, 27),
        settlement_date=date(2026, 7, 28),
        transaction_cost=Decimal("5"),
    )
    ledger = ledger.mark_to_market(
        event_id="led-mtm-buy",
        occurred_at=NOW + timedelta(minutes=1),
        valuation_date=date(2026, 7, 27),
        prices={INSTRUMENT: Decimal("11")},
    )

    assert ledger.cash_balance == Decimal("1000000")
    assert ledger.payables == Decimal("1005")
    assert ledger.receivables == Decimal("0")
    assert ledger.position_quantity(INSTRUMENT) == Decimal("100")
    assert ledger.position_market_value == Decimal("1100")
    assert ledger.equity == Decimal("1000095")
    assert ledger.reconciliation_record()["equity_formula"] == "cash + position_market_value + receivables - payables"

    ledger = ledger.settle_payable(
        event_id="led-settle-buy",
        occurred_at=NOW + timedelta(days=1),
        settlement_date=date(2026, 7, 28),
        amount=Decimal("1005"),
        source_execution_id="exe-ord-buy-100",
    )
    assert ledger.cash_balance == Decimal("998995")
    assert ledger.payables == Decimal("0")
    assert ledger.equity == Decimal("1000095")

    sell_order = _filled_order(
        side=OrderSide.SELL,
        order_id="ord-sell-40",
        quantity=Decimal("40"),
        price=Decimal("12"),
    )
    ledger = ledger.record_execution(
        order=sell_order,
        fill_event=sell_order.events[-1],
        event_id="led-sell-40",
        occurred_at=NOW + timedelta(days=2),
        trade_date=date(2026, 7, 29),
        settlement_date=date(2026, 7, 30),
        transaction_cost=Decimal("3"),
    )
    ledger = ledger.mark_to_market(
        event_id="led-mtm-sell",
        occurred_at=NOW + timedelta(days=2, minutes=1),
        valuation_date=date(2026, 7, 29),
        prices={INSTRUMENT: Decimal("12.5")},
    )

    assert ledger.position_quantity(INSTRUMENT) == Decimal("60")
    assert ledger.receivables == Decimal("477")
    assert ledger.position_market_value == Decimal("750.0")
    assert ledger.equity == Decimal("1000222.0")
    assert ledger.executions[-1].realized_pnl == Decimal("75.00")

    ledger = ledger.settle_receivable(
        event_id="led-settle-sell",
        occurred_at=NOW + timedelta(days=3),
        settlement_date=date(2026, 7, 30),
        amount=Decimal("477"),
        source_execution_id="exe-ord-sell-40",
    )
    record = ledger.to_record()

    assert record["contract_version"] == PORTFOLIO_LEDGER_CONTRACT_VERSION
    assert record["cash_balance"] == "999472"
    assert record["receivables"] == "0"
    assert record["payables"] == "0"
    assert record["equity"] == "1000222.0"
    assert record["positions"][INSTRUMENT.canonical]["quantity"] == "60"
    assert len(record["position_lots"]) == 1
    assert len(record["executions"]) == 2
    assert "risk" not in json.dumps(record, sort_keys=True).lower()
    assert "quant lab" not in json.dumps(record, sort_keys=True).lower()

    replayed = PortfolioLedger.replay(
        run_id=ledger.run_id,
        stage_id=ledger.stage_id,
        spec_id=ledger.spec_id,
        spec_hash=ledger.spec_hash,
        base_currency=ledger.base_currency,
        events=ledger.events,
    )
    assert replayed.to_record() == ledger.to_record()


def test_ledger_rejects_invariant_violations_and_event_conflicts() -> None:
    ledger = PortfolioLedger.open(
        run_id="run-ledger",
        stage_id="stage-ledger",
        spec_id="formal_cn_quality_momentum_v1",
        spec_hash=SPEC_HASH,
        base_currency="CNY",
        initial_cash=Decimal("100000"),
        event_id="led-initial-cash",
        occurred_at=NOW,
    )

    sell_order = _filled_order(side=OrderSide.SELL, order_id="ord-sell-too-much", quantity=Decimal("1"), price=Decimal("10"))
    with pytest.raises(PortfolioLedgerError, match="insufficient position"):
        ledger.record_execution(
            order=sell_order,
            fill_event=sell_order.events[-1],
            event_id="led-invalid-sell",
            occurred_at=NOW,
            trade_date=date(2026, 7, 27),
            settlement_date=date(2026, 7, 28),
        )

    buy_order = _filled_order(side=OrderSide.BUY, order_id="ord-buy-10", quantity=Decimal("10"), price=Decimal("10"))
    ledger = ledger.record_execution(
        order=buy_order,
        fill_event=buy_order.events[-1],
        event_id="led-buy-10",
        occurred_at=NOW,
        trade_date=date(2026, 7, 27),
        settlement_date=date(2026, 7, 28),
    )

    with pytest.raises(PortfolioLedgerError, match="exceeds payables"):
        ledger.settle_payable(
            event_id="led-over-settle",
            occurred_at=NOW,
            settlement_date=date(2026, 7, 28),
            amount=Decimal("101"),
            source_execution_id="exe-ord-buy-10",
        )
    with pytest.raises(PortfolioLedgerError, match="missing valuation price"):
        ledger.mark_to_market(
            event_id="led-missing-price",
            occurred_at=NOW,
            valuation_date=date(2026, 7, 27),
            prices={},
        )
    ledger = ledger.mark_to_market(
        event_id="led-mtm-buy",
        occurred_at=NOW + timedelta(minutes=1),
        valuation_date=date(2026, 7, 27),
        prices={INSTRUMENT: Decimal("10")},
    )

    duplicated = PortfolioLedger.replay(
        run_id=ledger.run_id,
        stage_id=ledger.stage_id,
        spec_id=ledger.spec_id,
        spec_hash=ledger.spec_hash,
        base_currency=ledger.base_currency,
        events=(*ledger.events, ledger.events[-1]),
    )
    assert duplicated.to_record() == ledger.to_record()

    conflicting = LedgerEvent(
        event_id=ledger.events[-1].event_id,
        sequence=ledger.events[-1].sequence,
        event_type=LedgerEventType.CASH_SETTLED,
        occurred_at=NOW,
        trade_date=date(2026, 7, 28),
        cash_delta=Decimal("-1"),
        payable_delta=Decimal("-1"),
        source_execution_id="exe-conflict",
    )
    with pytest.raises(PortfolioLedgerError, match="conflicting duplicate event_id"):
        PortfolioLedger.replay(
            run_id=ledger.run_id,
            stage_id=ledger.stage_id,
            spec_id=ledger.spec_id,
            spec_hash=ledger.spec_hash,
            base_currency=ledger.base_currency,
            events=(*ledger.events, conflicting),
        )


def test_ledger_validates_order_binding_and_stays_inside_pure_contract_boundary() -> None:
    ledger = PortfolioLedger.open(
        run_id="run-ledger",
        stage_id="stage-ledger",
        spec_id="formal_cn_quality_momentum_v1",
        spec_hash=SPEC_HASH,
        base_currency="CNY",
        initial_cash=Decimal("100000"),
        event_id="led-initial-cash",
        occurred_at=NOW,
    )
    order = _filled_order(side=OrderSide.BUY, order_id="ord-buy-100", quantity=Decimal("100"), price=Decimal("10"))
    mismatched_order = Order.create(
        intent=_order_intent(side=OrderSide.BUY, order_id="ord-mismatch", quantity=Decimal("100"), spec_hash="sha256:" + "3" * 64),
        event_id="evt-created-ord-mismatch",
        occurred_at=NOW,
    ).accept(event_id="evt-accepted-ord-mismatch", occurred_at=NOW)
    mismatched_filled_order = mismatched_order.record_fill(
        event_id="evt-fill-ord-mismatch",
        occurred_at=NOW,
        fill_quantity=Decimal("100"),
        fill_price=Decimal("10"),
        execution_id="exe-ord-mismatch",
    )

    with pytest.raises(PortfolioLedgerError, match="spec_hash must match ledger"):
        ledger.record_execution(
            order=mismatched_filled_order,
            fill_event=mismatched_filled_order.events[-1],
            event_id="led-mismatch",
            occurred_at=NOW,
            trade_date=date(2026, 7, 27),
            settlement_date=date(2026, 7, 28),
        )

    non_fill_event = OrderEvent(
        event_id="evt-not-fill",
        order_id=order.order_id,
        sequence=99,
        event_type=OrderEventType.ACCEPTED,
        occurred_at=NOW,
        status_after=OrderStatus.ACCEPTED,
    )
    with pytest.raises(PortfolioLedgerError, match="fill_event must be a fill event"):
        ledger.record_execution(
            order=order,
            fill_event=non_fill_event,
            event_id="led-not-fill",
            occurred_at=NOW,
            trade_date=date(2026, 7, 27),
            settlement_date=date(2026, 7, 28),
        )

    source = Path("src/serenity_alpha_lab/quant/backtest/ledger.py").read_text()
    tree = ast.parse(source)
    imported_roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_roots.add(node.module.split(".")[0])

    assert not {"qlib", "pyqlib", "fastapi", "sqlalchemy"}.intersection(imported_roots)


def _filled_order(*, side: OrderSide, order_id: str, quantity: Decimal, price: Decimal) -> Order:
    order = Order.create(
        intent=_order_intent(side=side, order_id=order_id, quantity=quantity),
        event_id=f"evt-created-{order_id}",
        occurred_at=NOW,
    ).accept(event_id=f"evt-accepted-{order_id}", occurred_at=NOW)
    return order.record_fill(
        event_id=f"evt-fill-{order_id}",
        occurred_at=NOW,
        fill_quantity=quantity,
        fill_price=price,
        execution_id=f"exe-{order_id}",
    )


def _order_intent(
    *,
    side: OrderSide,
    order_id: str,
    quantity: Decimal,
    spec_hash: str = SPEC_HASH,
) -> OrderIntent:
    return OrderIntent(
        order_id=order_id,
        run_id="run-ledger",
        stage_id="stage-ledger",
        spec_id="formal_cn_quality_momentum_v1",
        spec_hash=spec_hash,
        instrument_id=INSTRUMENT,
        side=side,
        order_type=OrderType.MARKET,
        target_quantity=quantity,
        trade_date=date(2026, 7, 27),
        signal_time=datetime(2026, 7, 25, 15, 0, tzinfo=UTC),
        created_at=NOW,
        time_in_force=TimeInForce.DAY,
        source="screen_snapshot_rebalance",
    )
