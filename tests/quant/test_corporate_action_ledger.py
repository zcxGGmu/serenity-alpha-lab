from __future__ import annotations

import ast
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from serenity_alpha_lab.datasets.corporate_actions import CorporateAction, CorporateActionType
from serenity_alpha_lab.domain.instruments import InstrumentId
from serenity_alpha_lab.quant.backtest.corporate_actions import CorporateActionLedgerProcessor
from serenity_alpha_lab.quant.backtest.ledger import (
    CorporateActionLedgerType,
    PortfolioLedger,
)
from serenity_alpha_lab.quant.backtest.orders import (
    Order,
    OrderIntent,
    OrderSide,
    OrderType,
    TimeInForce,
)

NOW = datetime(2026, 7, 25, 9, 30, tzinfo=UTC)
SPEC_HASH = "sha256:" + "4" * 64
INSTRUMENT = InstrumentId.parse("600519.XSHG")


def test_corporate_actions_post_cash_dividend_bonus_rights_and_delisting_to_ledger() -> None:
    ledger = _ledger_with_settled_position(quantity=Decimal("100"), price=Decimal("10"))
    processor = CorporateActionLedgerProcessor()

    ledger = processor.apply(
        ledger,
        _dataset_action(CorporateActionType.CASH_DIVIDEND, cash_dividend_per_share=1.0),
        event_id="ca-cash-dividend",
        occurred_at=NOW + timedelta(days=1),
        settlement_date=date(2026, 7, 29),
    )
    ledger = ledger.mark_to_market(
        event_id="mtm-after-dividend",
        occurred_at=NOW + timedelta(days=1, minutes=1),
        valuation_date=date(2026, 7, 28),
        prices={INSTRUMENT: Decimal("9")},
    )

    assert ledger.receivables == Decimal("100.0")
    assert ledger.position_quantity(INSTRUMENT) == Decimal("100")
    assert ledger.equity == Decimal("100000.0")
    assert ledger.corporate_actions[-1].corporate_action_type is CorporateActionLedgerType.CASH_DIVIDEND

    ledger = ledger.settle_receivable(
        event_id="settle-cash-dividend",
        occurred_at=NOW + timedelta(days=2),
        settlement_date=date(2026, 7, 29),
        amount=Decimal("100.0"),
        source_execution_id=ledger.corporate_actions[-1].corporate_action_id,
    )
    ledger = processor.apply(
        ledger,
        _dataset_action(CorporateActionType.BONUS_SHARE, bonus_share_ratio=0.1),
        event_id="ca-bonus-share",
        occurred_at=NOW + timedelta(days=3),
    )

    assert ledger.position_quantity(INSTRUMENT) == Decimal("110.0")
    assert sum(lot.cost_basis for lot in ledger.position_lots) == Decimal("1000")
    assert ledger.corporate_actions[-1].share_delta == Decimal("10.0")

    ledger = processor.apply(
        ledger,
        _dataset_action(CorporateActionType.RIGHTS_ISSUE, rights_issue_ratio=0.2, rights_issue_price=8.0),
        event_id="ca-rights-issue",
        occurred_at=NOW + timedelta(days=4),
        settlement_date=date(2026, 8, 3),
    )

    assert ledger.position_quantity(INSTRUMENT) == Decimal("132.00")
    assert ledger.payables == Decimal("176.00")
    assert ledger.corporate_actions[-1].payable_amount == Decimal("176.00")
    assert sum(lot.cost_basis for lot in ledger.position_lots) == Decimal("1176.00")

    ledger = ledger.settle_payable(
        event_id="settle-rights-issue",
        occurred_at=NOW + timedelta(days=7),
        settlement_date=date(2026, 8, 3),
        amount=Decimal("176.00"),
        source_execution_id=ledger.corporate_actions[-1].corporate_action_id,
    )
    ledger = processor.apply_delisting_liquidation(
        ledger,
        instrument_id=INSTRUMENT,
        liquidation_date=date(2026, 8, 10),
        settlement_date=date(2026, 8, 11),
        liquidation_price=Decimal("9"),
        corporate_action_id="delist:600519.XSHG:2026-08-10",
        event_id="ca-delisting-liquidation",
        occurred_at=NOW + timedelta(days=10),
    )

    assert ledger.position_quantity(INSTRUMENT) == Decimal("0")
    assert ledger.receivables == Decimal("1188.00")
    assert ledger.corporate_actions[-1].corporate_action_type is CorporateActionLedgerType.DELISTING_LIQUIDATION
    assert ledger.corporate_actions[-1].realized_pnl == Decimal("12.00")
    assert ledger.equity == Decimal("100112.000")

    replayed = PortfolioLedger.replay(
        run_id=ledger.run_id,
        stage_id=ledger.stage_id,
        spec_id=ledger.spec_id,
        spec_hash=ledger.spec_hash,
        base_currency=ledger.base_currency,
        events=ledger.events,
    )
    assert replayed.to_record() == ledger.to_record()


def test_corporate_action_processor_rejects_double_counting_adjusted_price_inputs() -> None:
    ledger = _ledger_with_settled_position(quantity=Decimal("100"), price=Decimal("10"))
    processor = CorporateActionLedgerProcessor()

    action = _dataset_action(CorporateActionType.CASH_DIVIDEND, cash_dividend_per_share=0.5)
    ledger = processor.apply(
        ledger,
        action,
        event_id="ca-raw-price-guard",
        occurred_at=NOW + timedelta(days=1),
        settlement_date=date(2026, 7, 29),
    )
    record = ledger.to_record()

    assert record["corporate_actions"][0]["source_schema"] == "dataset.corporate_actions@1.0.0"
    assert "adjusted" not in str(record["corporate_actions"][0]).lower()
    assert "adjustment_factor" not in str(record["corporate_actions"][0]).lower()

    source = Path("src/serenity_alpha_lab/quant/backtest/corporate_actions.py").read_text()
    tree = ast.parse(source)
    imported_modules = {
        node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module is not None
    }

    assert "serenity_alpha_lab.datasets.corporate_actions" in imported_modules
    assert "qlib" not in "\n".join(sorted(imported_modules))
    assert "fastapi" not in "\n".join(sorted(imported_modules))
    assert "sqlalchemy" not in "\n".join(sorted(imported_modules))


def test_share_split_scales_lots_without_changing_total_cost_basis() -> None:
    ledger = _ledger_with_settled_position(quantity=Decimal("50"), price=Decimal("20"))
    processor = CorporateActionLedgerProcessor()

    ledger = processor.apply(
        ledger,
        _dataset_action(CorporateActionType.SHARE_SPLIT, split_ratio=2.0),
        event_id="ca-share-split",
        occurred_at=NOW + timedelta(days=1),
    )

    assert ledger.position_quantity(INSTRUMENT) == Decimal("100.0")
    assert sum(lot.cost_basis for lot in ledger.position_lots) == Decimal("1000")
    assert ledger.corporate_actions[-1].corporate_action_type is CorporateActionLedgerType.SHARE_SPLIT
    assert ledger.corporate_actions[-1].share_delta == Decimal("50.0")


def _ledger_with_settled_position(*, quantity: Decimal, price: Decimal) -> PortfolioLedger:
    ledger = PortfolioLedger.open(
        run_id="run-corporate-actions",
        stage_id="stage-corporate-actions",
        spec_id="formal_cn_quality_momentum_v1",
        spec_hash=SPEC_HASH,
        base_currency="CNY",
        initial_cash=Decimal("100000"),
        event_id="initial-cash",
        occurred_at=NOW,
    )
    order = Order.create(
        intent=OrderIntent(
            order_id="ord-initial-buy",
            run_id=ledger.run_id,
            stage_id=ledger.stage_id,
            spec_id=ledger.spec_id,
            spec_hash=ledger.spec_hash,
            instrument_id=INSTRUMENT,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            target_quantity=quantity,
            trade_date=date(2026, 7, 27),
            signal_time=datetime(2026, 7, 24, 15, 0, tzinfo=UTC),
            created_at=NOW,
            time_in_force=TimeInForce.DAY,
            source="test_position_fixture",
        ),
        event_id="ord-created",
        occurred_at=NOW,
    ).accept(event_id="ord-accepted", occurred_at=NOW)
    order = order.record_fill(
        event_id="ord-filled",
        occurred_at=NOW,
        fill_quantity=quantity,
        fill_price=price,
        execution_id="exe-initial-buy",
    )
    ledger = ledger.record_execution(
        order=order,
        fill_event=order.events[-1],
        event_id="ledger-buy",
        occurred_at=NOW,
        trade_date=date(2026, 7, 27),
        settlement_date=date(2026, 7, 28),
    )
    ledger = ledger.settle_payable(
        event_id="settle-buy",
        occurred_at=NOW + timedelta(days=1),
        settlement_date=date(2026, 7, 28),
        amount=quantity * price,
        source_execution_id="exe-initial-buy",
    )
    return ledger.mark_to_market(
        event_id="mtm-initial",
        occurred_at=NOW + timedelta(days=1, minutes=1),
        valuation_date=date(2026, 7, 27),
        prices={INSTRUMENT: price},
    )


def _dataset_action(
    action_type: CorporateActionType,
    *,
    cash_dividend_per_share: float = 0.0,
    bonus_share_ratio: float = 0.0,
    split_ratio: float = 1.0,
    rights_issue_ratio: float = 0.0,
    rights_issue_price: float | None = None,
) -> CorporateAction:
    return CorporateAction(
        instrument_id=INSTRUMENT,
        ex_date=date(2026, 7, 28),
        action_type=action_type,
        provider_id="fixture_provider",
        provider_source="fixture_corporate_actions",
        provider_source_timestamp=NOW,
        provider_raw_response_sha256="a" * 64,
        field_lineage={"fixture": "tests"},
        source_bronze_artifact_id="bronze://fixture/corporate-actions",
        cash_dividend_per_share=cash_dividend_per_share,
        bonus_share_ratio=bonus_share_ratio,
        split_ratio=split_ratio,
        rights_issue_ratio=rights_issue_ratio,
        rights_issue_price=rights_issue_price,
        currency="CNY",
    )
