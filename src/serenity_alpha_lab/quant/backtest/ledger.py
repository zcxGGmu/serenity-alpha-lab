from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from types import MappingProxyType
from typing import Any

from serenity_alpha_lab.domain.instruments import InstrumentId
from serenity_alpha_lab.quant.backtest.orders import (
    Order,
    OrderEvent,
    OrderEventType,
    OrderSide,
)


PORTFOLIO_LEDGER_CONTRACT_VERSION = "quant.portfolio_ledger@1.0.0"
PORTFOLIO_LEDGER_SCHEMA_NAME = "quant.backtest.portfolio_ledger"
PORTFOLIO_LEDGER_SCHEMA_VERSION = "1.0.0"

_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


class PortfolioLedgerError(ValueError):
    """Raised when a portfolio ledger event or replay violates accounting rules."""


class LedgerEventType(StrEnum):
    INITIAL_CASH = "initial_cash"
    EXECUTION = "execution"
    CASH_SETTLED = "cash_settled"
    VALUATION = "valuation"


@dataclass(frozen=True, slots=True)
class PositionLot:
    lot_id: str
    instrument_id: InstrumentId
    opened_trade_date: date
    source_execution_id: str
    quantity: Decimal | int | str
    cost_basis: Decimal | int | str

    def __post_init__(self) -> None:
        object.__setattr__(self, "lot_id", _required_string("lot_id", self.lot_id))
        if type(self.instrument_id) is not InstrumentId:
            raise PortfolioLedgerError("instrument_id must be an InstrumentId")
        _require_date("opened_trade_date", self.opened_trade_date)
        object.__setattr__(
            self,
            "source_execution_id",
            _required_string("source_execution_id", self.source_execution_id),
        )
        object.__setattr__(
            self,
            "quantity",
            _decimal_min("quantity", self.quantity, Decimal("0"), exclusive=True),
        )
        object.__setattr__(self, "cost_basis", _decimal_min("cost_basis", self.cost_basis, Decimal("0")))

    @property
    def average_cost(self) -> Decimal:
        return self.cost_basis / self.quantity

    def reduce(self, quantity: Decimal) -> tuple[PositionLot | None, Decimal]:
        quantity = _decimal_min("quantity", quantity, Decimal("0"), exclusive=True)
        if quantity > self.quantity:
            raise PortfolioLedgerError("lot reduction exceeds lot quantity")
        removed_cost = self.average_cost * quantity
        remaining_quantity = self.quantity - quantity
        if remaining_quantity == 0:
            return None, removed_cost
        return (
            replace(
                self,
                quantity=remaining_quantity,
                cost_basis=self.cost_basis - removed_cost,
            ),
            removed_cost,
        )

    def to_record(self) -> dict[str, object]:
        return {
            "lot_id": self.lot_id,
            "instrument_id": self.instrument_id.canonical,
            "opened_trade_date": self.opened_trade_date.isoformat(),
            "source_execution_id": self.source_execution_id,
            "quantity": _decimal_to_string(self.quantity),
            "cost_basis": _decimal_to_string(self.cost_basis),
            "average_cost": _decimal_to_string(self.average_cost),
        }


@dataclass(frozen=True, slots=True)
class ExecutionRecord:
    order_id: str
    execution_id: str
    instrument_id: InstrumentId
    side: OrderSide | str
    quantity: Decimal | int | str
    price: Decimal | int | str
    gross_amount: Decimal | int | str
    transaction_cost: Decimal | int | str
    trade_date: date
    settlement_date: date
    payable_amount: Decimal | int | str = Decimal("0")
    receivable_amount: Decimal | int | str = Decimal("0")
    realized_pnl: Decimal | int | str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "order_id", _required_string("order_id", self.order_id))
        object.__setattr__(self, "execution_id", _required_string("execution_id", self.execution_id))
        if type(self.instrument_id) is not InstrumentId:
            raise PortfolioLedgerError("instrument_id must be an InstrumentId")
        object.__setattr__(self, "side", _enum_value(OrderSide, "side", self.side))
        object.__setattr__(
            self,
            "quantity",
            _decimal_min("quantity", self.quantity, Decimal("0"), exclusive=True),
        )
        object.__setattr__(self, "price", _decimal_min("price", self.price, Decimal("0"), exclusive=True))
        object.__setattr__(self, "gross_amount", _decimal_min("gross_amount", self.gross_amount, Decimal("0")))
        object.__setattr__(
            self,
            "transaction_cost",
            _decimal_min("transaction_cost", self.transaction_cost, Decimal("0")),
        )
        _require_date("trade_date", self.trade_date)
        _require_date("settlement_date", self.settlement_date)
        object.__setattr__(
            self,
            "payable_amount",
            _decimal_min("payable_amount", self.payable_amount, Decimal("0")),
        )
        object.__setattr__(
            self,
            "receivable_amount",
            _decimal_min("receivable_amount", self.receivable_amount, Decimal("0")),
        )
        object.__setattr__(self, "realized_pnl", _optional_decimal("realized_pnl", self.realized_pnl))

    def to_record(self) -> dict[str, object]:
        record = {
            "order_id": self.order_id,
            "execution_id": self.execution_id,
            "instrument_id": self.instrument_id.canonical,
            "side": self.side.value,
            "quantity": _decimal_to_string(self.quantity),
            "price": _decimal_to_string(self.price),
            "gross_amount": _decimal_to_string(self.gross_amount),
            "transaction_cost": _decimal_to_string(self.transaction_cost),
            "trade_date": self.trade_date.isoformat(),
            "settlement_date": self.settlement_date.isoformat(),
            "payable_amount": _decimal_to_string(self.payable_amount),
            "receivable_amount": _decimal_to_string(self.receivable_amount),
        }
        _set_if_present(record, "realized_pnl", _optional_decimal_to_string(self.realized_pnl))
        return record


@dataclass(frozen=True, slots=True)
class LedgerEvent:
    event_id: str
    sequence: int
    event_type: LedgerEventType | str
    occurred_at: datetime
    trade_date: date
    settlement_date: date | None = None
    instrument_id: InstrumentId | None = None
    order_id: str | None = None
    execution_id: str | None = None
    side: OrderSide | str | None = None
    quantity: Decimal | int | str | None = None
    price: Decimal | int | str | None = None
    gross_amount: Decimal | int | str | None = None
    transaction_cost: Decimal | int | str = Decimal("0")
    cash_delta: Decimal | int | str = Decimal("0")
    receivable_delta: Decimal | int | str = Decimal("0")
    payable_delta: Decimal | int | str = Decimal("0")
    lot_id: str | None = None
    realized_pnl: Decimal | int | str | None = None
    source_execution_id: str | None = None
    valuation_date: date | None = None
    valuation_prices: Mapping[InstrumentId | str, Decimal | int | str] | None = None
    message: str = ""
    metadata: Mapping[str, object] | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "event_id", _required_string("event_id", self.event_id))
        if type(self.sequence) is not int or self.sequence <= 0:
            raise PortfolioLedgerError("sequence must be a positive integer")
        object.__setattr__(self, "event_type", _enum_value(LedgerEventType, "event_type", self.event_type))
        _require_aware_datetime("occurred_at", self.occurred_at)
        _require_date("trade_date", self.trade_date)
        if self.settlement_date is not None:
            _require_date("settlement_date", self.settlement_date)
        if self.instrument_id is not None and type(self.instrument_id) is not InstrumentId:
            raise PortfolioLedgerError("instrument_id must be an InstrumentId")
        object.__setattr__(self, "order_id", _optional_string(self.order_id))
        object.__setattr__(self, "execution_id", _optional_string(self.execution_id))
        object.__setattr__(self, "side", _optional_enum_value(OrderSide, "side", self.side))
        object.__setattr__(self, "quantity", _optional_positive_decimal("quantity", self.quantity))
        object.__setattr__(self, "price", _optional_positive_decimal("price", self.price))
        object.__setattr__(self, "gross_amount", _optional_decimal_min("gross_amount", self.gross_amount, Decimal("0")))
        object.__setattr__(
            self,
            "transaction_cost",
            _decimal_min("transaction_cost", self.transaction_cost, Decimal("0")),
        )
        object.__setattr__(self, "cash_delta", _decimal_value("cash_delta", self.cash_delta))
        object.__setattr__(self, "receivable_delta", _decimal_value("receivable_delta", self.receivable_delta))
        object.__setattr__(self, "payable_delta", _decimal_value("payable_delta", self.payable_delta))
        object.__setattr__(self, "lot_id", _optional_string(self.lot_id))
        object.__setattr__(self, "realized_pnl", _optional_decimal("realized_pnl", self.realized_pnl))
        object.__setattr__(self, "source_execution_id", _optional_string(self.source_execution_id))
        if self.valuation_date is not None:
            _require_date("valuation_date", self.valuation_date)
        object.__setattr__(self, "valuation_prices", _normalize_valuation_prices(self.valuation_prices))
        object.__setattr__(self, "message", _message_string(self.message))
        object.__setattr__(self, "metadata", _normalize_metadata(self.metadata))
        self._validate_payload()

    def to_record(self) -> dict[str, object]:
        record: dict[str, object] = {
            "event_id": self.event_id,
            "sequence": self.sequence,
            "event_type": self.event_type.value,
            "occurred_at": self.occurred_at.isoformat(),
            "trade_date": self.trade_date.isoformat(),
            "cash_delta": _decimal_to_string(self.cash_delta),
            "receivable_delta": _decimal_to_string(self.receivable_delta),
            "payable_delta": _decimal_to_string(self.payable_delta),
            "transaction_cost": _decimal_to_string(self.transaction_cost),
        }
        _set_if_present(record, "settlement_date", self.settlement_date.isoformat() if self.settlement_date else None)
        _set_if_present(record, "instrument_id", self.instrument_id.canonical if self.instrument_id else None)
        _set_if_present(record, "order_id", self.order_id)
        _set_if_present(record, "execution_id", self.execution_id)
        _set_if_present(record, "side", self.side.value if self.side else None)
        _set_if_present(record, "quantity", _optional_decimal_to_string(self.quantity))
        _set_if_present(record, "price", _optional_decimal_to_string(self.price))
        _set_if_present(record, "gross_amount", _optional_decimal_to_string(self.gross_amount))
        _set_if_present(record, "lot_id", self.lot_id)
        _set_if_present(record, "realized_pnl", _optional_decimal_to_string(self.realized_pnl))
        _set_if_present(record, "source_execution_id", self.source_execution_id)
        _set_if_present(record, "valuation_date", self.valuation_date.isoformat() if self.valuation_date else None)
        if self.valuation_prices:
            record["valuation_prices"] = {
                instrument: _decimal_to_string(price) for instrument, price in self.valuation_prices.items()
            }
        if self.message:
            record["message"] = self.message
        if self.metadata:
            record["metadata"] = dict(self.metadata)
        return record

    def _validate_payload(self) -> None:
        if self.event_type is LedgerEventType.INITIAL_CASH:
            if self.cash_delta <= 0:
                raise PortfolioLedgerError("initial cash event requires positive cash_delta")
            if self.receivable_delta != 0 or self.payable_delta != 0:
                raise PortfolioLedgerError("initial cash cannot change receivables or payables")
            return

        if self.event_type is LedgerEventType.EXECUTION:
            required = {
                "instrument_id": self.instrument_id,
                "order_id": self.order_id,
                "execution_id": self.execution_id,
                "side": self.side,
                "quantity": self.quantity,
                "price": self.price,
                "gross_amount": self.gross_amount,
                "settlement_date": self.settlement_date,
            }
            missing = sorted(name for name, value in required.items() if value is None)
            if missing:
                raise PortfolioLedgerError(f"execution event missing fields: {', '.join(missing)}")
            if self.side is OrderSide.BUY and self.payable_delta <= 0:
                raise PortfolioLedgerError("buy execution requires positive payable_delta")
            if self.side is OrderSide.SELL and self.receivable_delta <= 0:
                raise PortfolioLedgerError("sell execution requires positive receivable_delta")
            return

        if self.event_type is LedgerEventType.CASH_SETTLED:
            if self.source_execution_id is None:
                raise PortfolioLedgerError("cash settlement requires source_execution_id")
            if self.cash_delta == 0:
                raise PortfolioLedgerError("cash settlement requires cash_delta")
            if (self.receivable_delta == 0) == (self.payable_delta == 0):
                raise PortfolioLedgerError("cash settlement must settle either receivable or payable")
            return

        if self.event_type is LedgerEventType.VALUATION:
            if self.valuation_date is None:
                raise PortfolioLedgerError("valuation event requires valuation_date")
            if not self.valuation_prices:
                raise PortfolioLedgerError("valuation event requires valuation_prices")
            return


@dataclass(frozen=True, slots=True)
class PortfolioLedger:
    run_id: str
    stage_id: str
    spec_id: str
    spec_hash: str
    base_currency: str
    events: tuple[LedgerEvent, ...]
    cash_balance: Decimal = Decimal("0")
    receivables: Decimal = Decimal("0")
    payables: Decimal = Decimal("0")
    position_lots: tuple[PositionLot, ...] = ()
    executions: tuple[ExecutionRecord, ...] = ()
    valuation_prices: Mapping[str, Decimal] = field(default_factory=lambda: MappingProxyType({}))
    valuation_date: date | None = None
    contract_version: str = PORTFOLIO_LEDGER_CONTRACT_VERSION
    schema_name: str = PORTFOLIO_LEDGER_SCHEMA_NAME
    schema_version: str = PORTFOLIO_LEDGER_SCHEMA_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "run_id", _required_string("run_id", self.run_id))
        object.__setattr__(self, "stage_id", _required_string("stage_id", self.stage_id))
        object.__setattr__(self, "spec_id", _required_string("spec_id", self.spec_id))
        object.__setattr__(self, "spec_hash", _validate_sha256("spec_hash", self.spec_hash))
        object.__setattr__(self, "base_currency", _required_string("base_currency", self.base_currency))
        events = tuple(self.events)
        for event in events:
            if type(event) is not LedgerEvent:
                raise PortfolioLedgerError("events must contain LedgerEvent values")
        object.__setattr__(self, "events", events)
        object.__setattr__(self, "cash_balance", _decimal_value("cash_balance", self.cash_balance))
        object.__setattr__(self, "receivables", _decimal_min("receivables", self.receivables, Decimal("0")))
        object.__setattr__(self, "payables", _decimal_min("payables", self.payables, Decimal("0")))
        lots = tuple(self.position_lots)
        for lot in lots:
            if type(lot) is not PositionLot:
                raise PortfolioLedgerError("position_lots must contain PositionLot values")
        object.__setattr__(self, "position_lots", lots)
        executions = tuple(self.executions)
        for execution in executions:
            if type(execution) is not ExecutionRecord:
                raise PortfolioLedgerError("executions must contain ExecutionRecord values")
        object.__setattr__(self, "executions", executions)
        object.__setattr__(self, "valuation_prices", _normalize_price_mapping(self.valuation_prices))
        if self.valuation_date is not None:
            _require_date("valuation_date", self.valuation_date)
        object.__setattr__(self, "contract_version", _required_string("contract_version", self.contract_version))
        object.__setattr__(self, "schema_name", _required_string("schema_name", self.schema_name))
        object.__setattr__(self, "schema_version", _required_string("schema_version", self.schema_version))

    @classmethod
    def open(
        cls,
        *,
        run_id: str,
        stage_id: str,
        spec_id: str,
        spec_hash: str,
        base_currency: str,
        initial_cash: Decimal | int | str,
        event_id: str,
        occurred_at: datetime,
    ) -> PortfolioLedger:
        ledger = cls(
            run_id=run_id,
            stage_id=stage_id,
            spec_id=spec_id,
            spec_hash=spec_hash,
            base_currency=base_currency,
            events=(),
        )
        return ledger._apply_event(
            LedgerEvent(
                event_id=event_id,
                sequence=1,
                event_type=LedgerEventType.INITIAL_CASH,
                occurred_at=occurred_at,
                trade_date=occurred_at.date(),
                cash_delta=_decimal_min("initial_cash", initial_cash, Decimal("0"), exclusive=True),
            )
        )

    @classmethod
    def replay(
        cls,
        *,
        run_id: str,
        stage_id: str,
        spec_id: str,
        spec_hash: str,
        base_currency: str,
        events: Sequence[LedgerEvent],
    ) -> PortfolioLedger:
        if isinstance(events, (str, bytes)):
            raise PortfolioLedgerError("events must be a sequence of LedgerEvent values")
        ledger = cls(
            run_id=run_id,
            stage_id=stage_id,
            spec_id=spec_id,
            spec_hash=spec_hash,
            base_currency=base_currency,
            events=(),
        )
        for event in events:
            ledger = ledger._apply_event(event)
        return ledger

    @property
    def position_market_value(self) -> Decimal:
        total = Decimal("0")
        for instrument, quantity in self._position_quantities().items():
            price = self.valuation_prices.get(instrument)
            if price is None:
                raise PortfolioLedgerError(f"missing valuation price for open position: {instrument}")
            total += quantity * price
        return total

    @property
    def equity(self) -> Decimal:
        return self.cash_balance + self.position_market_value + self.receivables - self.payables

    def position_quantity(self, instrument_id: InstrumentId | str) -> Decimal:
        key = _instrument_key(instrument_id)
        return self._position_quantities().get(key, Decimal("0"))

    def record_execution(
        self,
        *,
        order: Order,
        fill_event: OrderEvent,
        event_id: str,
        occurred_at: datetime,
        trade_date: date,
        settlement_date: date,
        transaction_cost: Decimal | int | str = Decimal("0"),
    ) -> PortfolioLedger:
        if type(order) is not Order:
            raise PortfolioLedgerError("order must be an Order")
        if type(fill_event) is not OrderEvent:
            raise PortfolioLedgerError("fill_event must be an OrderEvent")
        if fill_event.event_type not in {OrderEventType.PARTIALLY_FILLED, OrderEventType.FILLED}:
            raise PortfolioLedgerError("fill_event must be a fill event")
        if fill_event.order_id != order.order_id:
            raise PortfolioLedgerError("fill_event order_id must match order")
        if fill_event not in order.events:
            raise PortfolioLedgerError("fill_event must be part of the order event history")
        if order.intent.spec_hash != self.spec_hash:
            raise PortfolioLedgerError("order spec_hash must match ledger")
        if order.intent.run_id != self.run_id or order.intent.stage_id != self.stage_id:
            raise PortfolioLedgerError("order run_id and stage_id must match ledger")
        assert fill_event.fill_quantity is not None
        assert fill_event.fill_price is not None
        assert fill_event.execution_id is not None

        quantity = fill_event.fill_quantity
        price = fill_event.fill_price
        cost = _decimal_min("transaction_cost", transaction_cost, Decimal("0"))
        gross_amount = quantity * price
        lot_id: str | None = None
        realized_pnl: Decimal | None = None
        payable_delta = Decimal("0")
        receivable_delta = Decimal("0")
        if order.intent.side is OrderSide.BUY:
            payable_delta = gross_amount + cost
            lot_id = f"lot:{fill_event.execution_id}"
        elif order.intent.side is OrderSide.SELL:
            _reduced_lots, cost_removed = self._reduce_lots(
                order.intent.instrument_id,
                quantity,
                dry_run=True,
            )
            receivable_delta = gross_amount - cost
            if receivable_delta < 0:
                raise PortfolioLedgerError("sell transaction cost cannot exceed gross proceeds")
            realized_pnl = gross_amount - cost - cost_removed
        else:
            raise PortfolioLedgerError(f"unsupported order side: {order.intent.side}")

        return self._apply_event(
            LedgerEvent(
                event_id=event_id,
                sequence=len(self.events) + 1,
                event_type=LedgerEventType.EXECUTION,
                occurred_at=occurred_at,
                trade_date=trade_date,
                settlement_date=settlement_date,
                instrument_id=order.intent.instrument_id,
                order_id=order.order_id,
                execution_id=fill_event.execution_id,
                side=order.intent.side,
                quantity=quantity,
                price=price,
                gross_amount=gross_amount,
                transaction_cost=cost,
                receivable_delta=receivable_delta,
                payable_delta=payable_delta,
                lot_id=lot_id,
                realized_pnl=realized_pnl,
            )
        )

    def settle_payable(
        self,
        *,
        event_id: str,
        occurred_at: datetime,
        settlement_date: date,
        amount: Decimal | int | str,
        source_execution_id: str,
    ) -> PortfolioLedger:
        amount = _decimal_min("amount", amount, Decimal("0"), exclusive=True)
        if amount > self.payables:
            raise PortfolioLedgerError("settlement amount exceeds payables")
        return self._apply_event(
            LedgerEvent(
                event_id=event_id,
                sequence=len(self.events) + 1,
                event_type=LedgerEventType.CASH_SETTLED,
                occurred_at=occurred_at,
                trade_date=settlement_date,
                settlement_date=settlement_date,
                cash_delta=-amount,
                payable_delta=-amount,
                source_execution_id=source_execution_id,
            )
        )

    def settle_receivable(
        self,
        *,
        event_id: str,
        occurred_at: datetime,
        settlement_date: date,
        amount: Decimal | int | str,
        source_execution_id: str,
    ) -> PortfolioLedger:
        amount = _decimal_min("amount", amount, Decimal("0"), exclusive=True)
        if amount > self.receivables:
            raise PortfolioLedgerError("settlement amount exceeds receivables")
        return self._apply_event(
            LedgerEvent(
                event_id=event_id,
                sequence=len(self.events) + 1,
                event_type=LedgerEventType.CASH_SETTLED,
                occurred_at=occurred_at,
                trade_date=settlement_date,
                settlement_date=settlement_date,
                cash_delta=amount,
                receivable_delta=-amount,
                source_execution_id=source_execution_id,
            )
        )

    def mark_to_market(
        self,
        *,
        event_id: str,
        occurred_at: datetime,
        valuation_date: date,
        prices: Mapping[InstrumentId | str, Decimal | int | str],
    ) -> PortfolioLedger:
        normalized_prices = _normalize_valuation_prices(prices)
        missing = sorted(set(self._position_quantities()).difference(normalized_prices))
        if missing:
            raise PortfolioLedgerError(f"missing valuation price for open position: {', '.join(missing)}")
        return self._apply_event(
            LedgerEvent(
                event_id=event_id,
                sequence=len(self.events) + 1,
                event_type=LedgerEventType.VALUATION,
                occurred_at=occurred_at,
                trade_date=valuation_date,
                valuation_date=valuation_date,
                valuation_prices=normalized_prices,
            )
        )

    def reconciliation_record(self) -> dict[str, object]:
        return {
            "equity_formula": "cash + position_market_value + receivables - payables",
            "cash": _decimal_to_string(self.cash_balance),
            "position_market_value": _decimal_to_string(self.position_market_value),
            "receivables": _decimal_to_string(self.receivables),
            "payables": _decimal_to_string(self.payables),
            "equity": _decimal_to_string(self.equity),
        }

    def to_record(self) -> dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "schema_name": self.schema_name,
            "schema_version": self.schema_version,
            "run_id": self.run_id,
            "stage_id": self.stage_id,
            "spec_id": self.spec_id,
            "spec_hash": self.spec_hash,
            "base_currency": self.base_currency,
            "cash_balance": _decimal_to_string(self.cash_balance),
            "receivables": _decimal_to_string(self.receivables),
            "payables": _decimal_to_string(self.payables),
            "position_market_value": _decimal_to_string(self.position_market_value),
            "equity": _decimal_to_string(self.equity),
            "valuation_date": self.valuation_date.isoformat() if self.valuation_date else None,
            "valuation_prices": {
                instrument: _decimal_to_string(price) for instrument, price in self.valuation_prices.items()
            },
            "positions": self._positions_record(),
            "position_lots": [lot.to_record() for lot in self.position_lots],
            "executions": [execution.to_record() for execution in self.executions],
            "reconciliation": self.reconciliation_record(),
            "last_event": self.events[-1].to_record() if self.events else None,
            "events": [event.to_record() for event in self.events],
        }

    def _apply_event(self, event: LedgerEvent) -> PortfolioLedger:
        if type(event) is not LedgerEvent:
            raise PortfolioLedgerError("event must be a LedgerEvent")
        duplicate = self._find_event(event.event_id)
        if duplicate is not None:
            if duplicate.to_record() == event.to_record():
                return self
            raise PortfolioLedgerError(f"conflicting duplicate event_id: {event.event_id}")
        if event.sequence != len(self.events) + 1:
            raise PortfolioLedgerError("event sequence must be contiguous")
        if not self.events and event.event_type is not LedgerEventType.INITIAL_CASH:
            raise PortfolioLedgerError("first ledger event must initialize cash")
        if self.events and event.event_type is LedgerEventType.INITIAL_CASH:
            raise PortfolioLedgerError("initial cash event can only appear once")

        cash_balance = self.cash_balance + event.cash_delta
        receivables = self.receivables + event.receivable_delta
        payables = self.payables + event.payable_delta
        lots = self.position_lots
        executions = self.executions
        valuation_prices = self.valuation_prices
        valuation_date = self.valuation_date

        if receivables < 0:
            raise PortfolioLedgerError("ledger receivables cannot be negative")
        if payables < 0:
            raise PortfolioLedgerError("ledger payables cannot be negative")

        if event.event_type is LedgerEventType.EXECUTION:
            lots, execution = self._apply_execution_event(event)
            executions = (*executions, execution)
        elif event.event_type is LedgerEventType.VALUATION:
            assert event.valuation_prices is not None
            valuation_prices = event.valuation_prices
            valuation_date = event.valuation_date

        return replace(
            self,
            events=(*self.events, event),
            cash_balance=cash_balance,
            receivables=receivables,
            payables=payables,
            position_lots=lots,
            executions=executions,
            valuation_prices=valuation_prices,
            valuation_date=valuation_date,
        )

    def _apply_execution_event(self, event: LedgerEvent) -> tuple[tuple[PositionLot, ...], ExecutionRecord]:
        assert event.instrument_id is not None
        assert event.side is not None
        assert event.quantity is not None
        assert event.price is not None
        assert event.gross_amount is not None
        assert event.order_id is not None
        assert event.execution_id is not None
        assert event.settlement_date is not None

        if event.side is OrderSide.BUY:
            assert event.lot_id is not None
            lot = PositionLot(
                lot_id=event.lot_id,
                instrument_id=event.instrument_id,
                opened_trade_date=event.trade_date,
                source_execution_id=event.execution_id,
                quantity=event.quantity,
                cost_basis=event.gross_amount + event.transaction_cost,
            )
            lots = (*self.position_lots, lot)
            payable_amount = event.payable_delta
            receivable_amount = Decimal("0")
            realized_pnl = None
        else:
            lots, cost_removed = self._reduce_lots(event.instrument_id, event.quantity)
            payable_amount = Decimal("0")
            receivable_amount = event.receivable_delta
            realized_pnl = event.realized_pnl
            expected_pnl = event.gross_amount - event.transaction_cost - cost_removed
            if realized_pnl != expected_pnl:
                raise PortfolioLedgerError("sell execution realized_pnl does not match FIFO lots")

        execution = ExecutionRecord(
            order_id=event.order_id,
            execution_id=event.execution_id,
            instrument_id=event.instrument_id,
            side=event.side,
            quantity=event.quantity,
            price=event.price,
            gross_amount=event.gross_amount,
            transaction_cost=event.transaction_cost,
            trade_date=event.trade_date,
            settlement_date=event.settlement_date,
            payable_amount=payable_amount,
            receivable_amount=receivable_amount,
            realized_pnl=realized_pnl,
        )
        return lots, execution

    def _reduce_lots(
        self,
        instrument_id: InstrumentId,
        quantity: Decimal,
        *,
        dry_run: bool = False,
    ) -> tuple[tuple[PositionLot, ...], Decimal]:
        quantity = _decimal_min("quantity", quantity, Decimal("0"), exclusive=True)
        remaining = quantity
        new_lots: list[PositionLot] = []
        removed_cost = Decimal("0")
        for lot in self.position_lots:
            if lot.instrument_id != instrument_id or remaining == 0:
                new_lots.append(lot)
                continue
            reduction = min(lot.quantity, remaining)
            updated_lot, lot_removed_cost = lot.reduce(reduction)
            removed_cost += lot_removed_cost
            remaining -= reduction
            if updated_lot is not None:
                new_lots.append(updated_lot)
        if remaining != 0:
            raise PortfolioLedgerError("insufficient position for sell execution")
        if dry_run:
            return self.position_lots, removed_cost
        return tuple(new_lots), removed_cost

    def _positions_record(self) -> dict[str, dict[str, object]]:
        positions: dict[str, dict[str, object]] = {}
        quantities = self._position_quantities()
        costs = self._position_costs()
        for instrument in sorted(quantities):
            quantity = quantities[instrument]
            price = self.valuation_prices.get(instrument)
            if price is None:
                raise PortfolioLedgerError(f"missing valuation price for open position: {instrument}")
            market_value = quantity * price
            positions[instrument] = {
                "instrument_id": instrument,
                "quantity": _decimal_to_string(quantity),
                "cost_basis": _decimal_to_string(costs[instrument]),
                "valuation_price": _decimal_to_string(price),
                "market_value": _decimal_to_string(market_value),
            }
        return positions

    def _position_quantities(self) -> dict[str, Decimal]:
        quantities: dict[str, Decimal] = {}
        for lot in self.position_lots:
            key = lot.instrument_id.canonical
            quantities[key] = quantities.get(key, Decimal("0")) + lot.quantity
        return quantities

    def _position_costs(self) -> dict[str, Decimal]:
        costs: dict[str, Decimal] = {}
        for lot in self.position_lots:
            key = lot.instrument_id.canonical
            costs[key] = costs.get(key, Decimal("0")) + lot.cost_basis
        return costs

    def _find_event(self, event_id: str) -> LedgerEvent | None:
        return next((event for event in self.events if event.event_id == event_id), None)


def _enum_value(enum_type: type[StrEnum], field_name: str, value: object) -> Any:
    try:
        return enum_type(value)  # type: ignore[call-arg]
    except ValueError as exc:
        raise PortfolioLedgerError(f"{field_name} must be one of {[item.value for item in enum_type]}") from exc


def _optional_enum_value(enum_type: type[StrEnum], field_name: str, value: object) -> Any | None:
    if value is None:
        return None
    return _enum_value(enum_type, field_name, value)


def _decimal_value(field_name: str, value: object) -> Decimal:
    if isinstance(value, bool):
        raise PortfolioLedgerError(f"{field_name} must be a decimal value")
    try:
        decimal = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise PortfolioLedgerError(f"{field_name} must be a decimal value") from exc
    if not decimal.is_finite():
        raise PortfolioLedgerError(f"{field_name} must be finite")
    return decimal


def _decimal_min(
    field_name: str,
    value: object,
    minimum: Decimal,
    *,
    exclusive: bool = False,
) -> Decimal:
    decimal = _decimal_value(field_name, value)
    if exclusive:
        if decimal <= minimum:
            raise PortfolioLedgerError(f"{field_name} must be greater than {minimum}")
    elif decimal < minimum:
        raise PortfolioLedgerError(f"{field_name} cannot be less than {minimum}")
    return decimal


def _optional_decimal(field_name: str, value: object) -> Decimal | None:
    if value is None:
        return None
    return _decimal_value(field_name, value)


def _optional_positive_decimal(field_name: str, value: object) -> Decimal | None:
    if value is None:
        return None
    return _decimal_min(field_name, value, Decimal("0"), exclusive=True)


def _optional_decimal_min(field_name: str, value: object, minimum: Decimal) -> Decimal | None:
    if value is None:
        return None
    return _decimal_min(field_name, value, minimum)


def _decimal_to_string(value: Decimal) -> str:
    return format(value, "f")


def _optional_decimal_to_string(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return _decimal_to_string(value)


def _required_string(field_name: str, value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PortfolioLedgerError(f"{field_name} is required")
    return value


def _optional_string(value: object) -> str | None:
    if value is None:
        return None
    return _required_string("optional string", value)


def _message_string(value: object) -> str:
    if not isinstance(value, str):
        raise PortfolioLedgerError("message must be a string")
    return value


def _validate_sha256(field_name: str, value: object) -> str:
    value = _required_string(field_name, value)
    if not _SHA256_RE.match(value):
        raise PortfolioLedgerError(f"{field_name} must be sha256:<64 lowercase hex>")
    return value


def _require_date(field_name: str, value: object) -> None:
    if type(value) is not date:
        raise PortfolioLedgerError(f"{field_name} must be a date")


def _require_aware_datetime(field_name: str, value: object) -> None:
    if type(value) is not datetime or value.tzinfo is None or value.utcoffset() is None:
        raise PortfolioLedgerError(f"{field_name} must be timezone-aware")


def _instrument_key(instrument_id: InstrumentId | str) -> str:
    if type(instrument_id) is InstrumentId:
        return instrument_id.canonical
    return _required_string("instrument_id", instrument_id)


def _normalize_price_mapping(prices: Mapping[str, Decimal] | MappingProxyType[str, Decimal]) -> Mapping[str, Decimal]:
    if not isinstance(prices, Mapping):
        raise PortfolioLedgerError("valuation_prices must be a mapping")
    return MappingProxyType(
        {
            _required_string("instrument_id", instrument): _decimal_min("valuation_price", price, Decimal("0"), exclusive=True)
            for instrument, price in sorted(prices.items())
        }
    )


def _normalize_valuation_prices(
    prices: Mapping[InstrumentId | str, Decimal | int | str] | None,
) -> Mapping[str, Decimal]:
    if prices is None:
        return MappingProxyType({})
    if not isinstance(prices, Mapping):
        raise PortfolioLedgerError("valuation_prices must be a mapping")
    normalized = {
        _instrument_key(instrument): _decimal_min("valuation_price", price, Decimal("0"), exclusive=True)
        for instrument, price in prices.items()
    }
    return MappingProxyType(dict(sorted(normalized.items())))


def _normalize_metadata(metadata: Mapping[str, object] | None) -> Mapping[str, object]:
    if metadata is None:
        return MappingProxyType({})
    if not isinstance(metadata, Mapping):
        raise PortfolioLedgerError("metadata must be a mapping")
    normalized = {_required_string("metadata key", key): value for key, value in metadata.items()}
    return MappingProxyType(dict(sorted(normalized.items())))


def _set_if_present(record: dict[str, object], key: str, value: object | None) -> None:
    if value is not None:
        record[key] = value
