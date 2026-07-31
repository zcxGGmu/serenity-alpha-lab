from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from types import MappingProxyType
from typing import Any

from serenity_alpha_lab.domain.instruments import InstrumentId


ORDER_STATE_MACHINE_CONTRACT_VERSION = "quant.order_state_machine@1.0.0"
ORDER_STATE_MACHINE_SCHEMA_NAME = "quant.backtest.orders"
ORDER_STATE_MACHINE_SCHEMA_VERSION = "1.0.0"

_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


class OrderStateMachineError(ValueError):
    """Raised when an order intent, event or transition violates the contract."""


class OrderSide(StrEnum):
    BUY = "buy"
    SELL = "sell"


class OrderType(StrEnum):
    MARKET = "market"
    LIMIT = "limit"


class TimeInForce(StrEnum):
    DAY = "day"
    GOOD_TIL_CANCELLED = "good_til_cancelled"
    IMMEDIATE_OR_CANCEL = "immediate_or_cancel"


class OrderStatus(StrEnum):
    CREATED = "created"
    ACCEPTED = "accepted"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    REJECTED = "rejected"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class OrderEventType(StrEnum):
    CREATED = "created"
    ACCEPTED = "accepted"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    REJECTED = "rejected"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


TERMINAL_ORDER_STATUSES = frozenset(
    {
        OrderStatus.FILLED,
        OrderStatus.REJECTED,
        OrderStatus.EXPIRED,
        OrderStatus.CANCELLED,
    }
)


@dataclass(frozen=True, slots=True)
class OrderIntent:
    order_id: str
    run_id: str
    stage_id: str
    spec_id: str
    spec_hash: str
    instrument_id: InstrumentId
    side: OrderSide | str
    order_type: OrderType | str
    target_quantity: Decimal | int | str
    trade_date: date
    signal_time: datetime
    created_at: datetime
    time_in_force: TimeInForce | str = TimeInForce.DAY
    limit_price: Decimal | int | str | None = None
    source: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "order_id", _required_string("order_id", self.order_id))
        object.__setattr__(self, "run_id", _required_string("run_id", self.run_id))
        object.__setattr__(self, "stage_id", _required_string("stage_id", self.stage_id))
        object.__setattr__(self, "spec_id", _required_string("spec_id", self.spec_id))
        object.__setattr__(self, "spec_hash", _validate_sha256("spec_hash", self.spec_hash))
        if type(self.instrument_id) is not InstrumentId:
            raise OrderStateMachineError("instrument_id must be an InstrumentId")
        object.__setattr__(self, "side", _enum_value(OrderSide, "side", self.side))
        object.__setattr__(self, "order_type", _enum_value(OrderType, "order_type", self.order_type))
        object.__setattr__(
            self,
            "target_quantity",
            _decimal_min("target_quantity", self.target_quantity, Decimal("0"), exclusive=True),
        )
        _require_date("trade_date", self.trade_date)
        _require_aware_datetime("signal_time", self.signal_time)
        _require_aware_datetime("created_at", self.created_at)
        object.__setattr__(self, "time_in_force", _enum_value(TimeInForce, "time_in_force", self.time_in_force))
        object.__setattr__(self, "limit_price", _optional_positive_decimal("limit_price", self.limit_price))
        object.__setattr__(self, "source", _optional_string(self.source))
        if self.order_type is OrderType.LIMIT and self.limit_price is None:
            raise OrderStateMachineError("limit_price is required for limit orders")

    def to_record(self) -> dict[str, object]:
        record: dict[str, object] = {
            "order_id": self.order_id,
            "run_id": self.run_id,
            "stage_id": self.stage_id,
            "spec_id": self.spec_id,
            "spec_hash": self.spec_hash,
            "instrument_id": self.instrument_id.canonical,
            "side": self.side.value,
            "order_type": self.order_type.value,
            "target_quantity": _decimal_to_string(self.target_quantity),
            "trade_date": self.trade_date.isoformat(),
            "signal_time": self.signal_time.isoformat(),
            "created_at": self.created_at.isoformat(),
            "time_in_force": self.time_in_force.value,
        }
        _set_if_present(record, "limit_price", _optional_decimal_to_string(self.limit_price))
        _set_if_present(record, "source", self.source)
        return record


@dataclass(frozen=True, slots=True)
class OrderEvent:
    event_id: str
    order_id: str
    sequence: int
    event_type: OrderEventType | str
    occurred_at: datetime
    status_after: OrderStatus | str
    fill_quantity: Decimal | int | str | None = None
    fill_price: Decimal | int | str | None = None
    execution_id: str | None = None
    reason: str | None = None
    message: str = ""
    metadata: Mapping[str, object] | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "event_id", _required_string("event_id", self.event_id))
        object.__setattr__(self, "order_id", _required_string("order_id", self.order_id))
        if type(self.sequence) is not int or self.sequence <= 0:
            raise OrderStateMachineError("sequence must be a positive integer")
        object.__setattr__(self, "event_type", _enum_value(OrderEventType, "event_type", self.event_type))
        _require_aware_datetime("occurred_at", self.occurred_at)
        object.__setattr__(self, "status_after", _enum_value(OrderStatus, "status_after", self.status_after))
        object.__setattr__(self, "fill_quantity", _optional_positive_decimal("fill_quantity", self.fill_quantity))
        object.__setattr__(self, "fill_price", _optional_positive_decimal("fill_price", self.fill_price))
        object.__setattr__(self, "execution_id", _optional_string(self.execution_id))
        object.__setattr__(self, "reason", _optional_string(self.reason))
        object.__setattr__(self, "message", _message_string(self.message))
        object.__setattr__(self, "metadata", _normalize_metadata(self.metadata))
        self._validate_payload()

    def to_record(self) -> dict[str, object]:
        record: dict[str, object] = {
            "event_id": self.event_id,
            "order_id": self.order_id,
            "sequence": self.sequence,
            "event_type": self.event_type.value,
            "occurred_at": self.occurred_at.isoformat(),
            "status_after": self.status_after.value,
        }
        _set_if_present(record, "fill_quantity", _optional_decimal_to_string(self.fill_quantity))
        _set_if_present(record, "fill_price", _optional_decimal_to_string(self.fill_price))
        _set_if_present(record, "execution_id", self.execution_id)
        _set_if_present(record, "reason", self.reason)
        if self.message:
            record["message"] = self.message
        if self.metadata:
            record["metadata"] = dict(self.metadata)
        return record

    def _validate_payload(self) -> None:
        if self.event_type in {OrderEventType.PARTIALLY_FILLED, OrderEventType.FILLED}:
            if self.fill_quantity is None:
                raise OrderStateMachineError("fill_quantity is required for fill events")
            if self.fill_price is None:
                raise OrderStateMachineError("fill_price is required for fill events")
            if self.execution_id is None:
                raise OrderStateMachineError("execution_id is required for fill events")
        elif self.fill_quantity is not None or self.fill_price is not None or self.execution_id is not None:
            raise OrderStateMachineError("fill fields are only valid for fill events")

        if self.event_type in {OrderEventType.REJECTED, OrderEventType.EXPIRED, OrderEventType.CANCELLED}:
            if self.reason is None:
                raise OrderStateMachineError("reason is required for terminal non-fill events")


@dataclass(frozen=True, slots=True)
class Order:
    intent: OrderIntent
    status: OrderStatus
    events: tuple[OrderEvent, ...]
    filled_quantity: Decimal = Decimal("0")
    reason: str | None = None
    contract_version: str = ORDER_STATE_MACHINE_CONTRACT_VERSION
    schema_name: str = ORDER_STATE_MACHINE_SCHEMA_NAME
    schema_version: str = ORDER_STATE_MACHINE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if type(self.intent) is not OrderIntent:
            raise OrderStateMachineError("intent must be an OrderIntent")
        object.__setattr__(self, "status", _enum_value(OrderStatus, "status", self.status))
        events = tuple(self.events)
        for event in events:
            if type(event) is not OrderEvent:
                raise OrderStateMachineError("events must contain OrderEvent values")
        object.__setattr__(self, "events", events)
        object.__setattr__(self, "filled_quantity", _decimal_min("filled_quantity", self.filled_quantity, Decimal("0")))
        if self.filled_quantity > self.intent.target_quantity:
            raise OrderStateMachineError("filled_quantity cannot exceed target_quantity")
        object.__setattr__(self, "reason", _optional_string(self.reason))
        object.__setattr__(self, "contract_version", _required_string("contract_version", self.contract_version))
        object.__setattr__(self, "schema_name", _required_string("schema_name", self.schema_name))
        object.__setattr__(self, "schema_version", _required_string("schema_version", self.schema_version))

    @classmethod
    def create(cls, *, intent: OrderIntent, event_id: str, occurred_at: datetime) -> Order:
        order = cls(intent=intent, status=OrderStatus.CREATED, events=())
        return order._apply_event(
            OrderEvent(
                event_id=event_id,
                order_id=intent.order_id,
                sequence=1,
                event_type=OrderEventType.CREATED,
                occurred_at=occurred_at,
                status_after=OrderStatus.CREATED,
            )
        )

    @classmethod
    def replay(cls, intent: OrderIntent, events: Sequence[OrderEvent]) -> Order:
        if isinstance(events, (str, bytes)):
            raise OrderStateMachineError("events must be a sequence of OrderEvent values")
        order = cls(intent=intent, status=OrderStatus.CREATED, events=())
        for event in events:
            order = order._apply_event(event)
        return order

    @property
    def order_id(self) -> str:
        return self.intent.order_id

    @property
    def remaining_quantity(self) -> Decimal:
        return self.intent.target_quantity - self.filled_quantity

    def accept(self, *, event_id: str, occurred_at: datetime, reason: str | None = None) -> Order:
        self._ensure_not_terminal()
        return self._apply_event(
            self._new_event(
                event_id=event_id,
                event_type=OrderEventType.ACCEPTED,
                occurred_at=occurred_at,
                status_after=OrderStatus.ACCEPTED,
                reason=reason,
            )
        )

    def reject(self, *, event_id: str, occurred_at: datetime, reason: str) -> Order:
        self._ensure_not_terminal()
        return self._apply_event(
            self._new_event(
                event_id=event_id,
                event_type=OrderEventType.REJECTED,
                occurred_at=occurred_at,
                status_after=OrderStatus.REJECTED,
                reason=reason,
            )
        )

    def record_fill(
        self,
        *,
        event_id: str,
        occurred_at: datetime,
        fill_quantity: Decimal | int | str,
        fill_price: Decimal | int | str,
        execution_id: str,
    ) -> Order:
        self._ensure_not_terminal()
        quantity = _decimal_min("fill_quantity", fill_quantity, Decimal("0"), exclusive=True)
        filled_quantity = self.filled_quantity + quantity
        if filled_quantity > self.intent.target_quantity:
            raise OrderStateMachineError("fill quantity exceeds remaining quantity")
        status_after = OrderStatus.FILLED if filled_quantity == self.intent.target_quantity else OrderStatus.PARTIALLY_FILLED
        event_type = (
            OrderEventType.FILLED
            if status_after is OrderStatus.FILLED
            else OrderEventType.PARTIALLY_FILLED
        )
        return self._apply_event(
            self._new_event(
                event_id=event_id,
                event_type=event_type,
                occurred_at=occurred_at,
                status_after=status_after,
                fill_quantity=quantity,
                fill_price=fill_price,
                execution_id=execution_id,
            )
        )

    def expire(self, *, event_id: str, occurred_at: datetime, reason: str) -> Order:
        self._ensure_not_terminal()
        return self._apply_event(
            self._new_event(
                event_id=event_id,
                event_type=OrderEventType.EXPIRED,
                occurred_at=occurred_at,
                status_after=OrderStatus.EXPIRED,
                reason=reason,
            )
        )

    def cancel(self, *, event_id: str, occurred_at: datetime, reason: str) -> Order:
        self._ensure_not_terminal()
        return self._apply_event(
            self._new_event(
                event_id=event_id,
                event_type=OrderEventType.CANCELLED,
                occurred_at=occurred_at,
                status_after=OrderStatus.CANCELLED,
                reason=reason,
            )
        )

    def to_record(self) -> dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "schema_name": self.schema_name,
            "schema_version": self.schema_version,
            "order_id": self.order_id,
            "status": self.status.value,
            "filled_quantity": _decimal_to_string(self.filled_quantity),
            "remaining_quantity": _decimal_to_string(self.remaining_quantity),
            "reason": self.reason,
            "intent": self.intent.to_record(),
            "last_event": self.events[-1].to_record() if self.events else None,
            "events": [event.to_record() for event in self.events],
        }

    def _new_event(
        self,
        *,
        event_id: str,
        event_type: OrderEventType,
        occurred_at: datetime,
        status_after: OrderStatus,
        fill_quantity: Decimal | int | str | None = None,
        fill_price: Decimal | int | str | None = None,
        execution_id: str | None = None,
        reason: str | None = None,
    ) -> OrderEvent:
        return OrderEvent(
            event_id=event_id,
            order_id=self.order_id,
            sequence=len(self.events) + 1,
            event_type=event_type,
            occurred_at=occurred_at,
            status_after=status_after,
            fill_quantity=fill_quantity,
            fill_price=fill_price,
            execution_id=execution_id,
            reason=reason,
        )

    def _apply_event(self, event: OrderEvent) -> Order:
        if type(event) is not OrderEvent:
            raise OrderStateMachineError("event must be an OrderEvent")
        if event.order_id != self.order_id:
            raise OrderStateMachineError("event order_id must match order intent")

        duplicate = self._find_event(event.event_id)
        if duplicate is not None:
            if duplicate.to_record() == event.to_record():
                return self
            raise OrderStateMachineError(f"conflicting duplicate event_id: {event.event_id}")

        if event.sequence != len(self.events) + 1:
            raise OrderStateMachineError("event sequence must be contiguous")

        filled_quantity = self.filled_quantity
        reason = self.reason
        self._validate_transition(event)
        if event.event_type in {OrderEventType.PARTIALLY_FILLED, OrderEventType.FILLED}:
            assert event.fill_quantity is not None
            filled_quantity += event.fill_quantity
        if event.status_after in {OrderStatus.REJECTED, OrderStatus.EXPIRED, OrderStatus.CANCELLED}:
            reason = event.reason

        return replace(
            self,
            status=event.status_after,
            events=(*self.events, event),
            filled_quantity=filled_quantity,
            reason=reason,
        )

    def _validate_transition(self, event: OrderEvent) -> None:
        if not self.events:
            if event.event_type is not OrderEventType.CREATED or event.status_after is not OrderStatus.CREATED:
                raise OrderStateMachineError("first order event must create the order")
            return

        self._ensure_not_terminal()
        if event.event_type is OrderEventType.CREATED:
            raise OrderStateMachineError("created event can only appear once")
        if event.event_type is OrderEventType.ACCEPTED:
            if self.status is not OrderStatus.CREATED:
                raise OrderStateMachineError("only created orders can be accepted")
            if event.status_after is not OrderStatus.ACCEPTED:
                raise OrderStateMachineError("accepted event must leave order accepted")
            return
        if event.event_type in {OrderEventType.PARTIALLY_FILLED, OrderEventType.FILLED}:
            if self.status not in {OrderStatus.ACCEPTED, OrderStatus.PARTIALLY_FILLED}:
                raise OrderStateMachineError("only accepted orders can record fills")
            assert event.fill_quantity is not None
            filled_quantity = self.filled_quantity + event.fill_quantity
            if filled_quantity > self.intent.target_quantity:
                raise OrderStateMachineError("fill quantity exceeds remaining quantity")
            expected_status = (
                OrderStatus.FILLED if filled_quantity == self.intent.target_quantity else OrderStatus.PARTIALLY_FILLED
            )
            expected_event_type = (
                OrderEventType.FILLED
                if expected_status is OrderStatus.FILLED
                else OrderEventType.PARTIALLY_FILLED
            )
            if event.status_after is not expected_status or event.event_type is not expected_event_type:
                raise OrderStateMachineError("fill event status does not match cumulative filled quantity")
            return
        if event.event_type is OrderEventType.REJECTED:
            if self.status not in {OrderStatus.CREATED, OrderStatus.ACCEPTED}:
                raise OrderStateMachineError("partially filled orders must expire or cancel remaining quantity")
            if event.status_after is not OrderStatus.REJECTED:
                raise OrderStateMachineError("rejected event must leave order rejected")
            return
        if event.event_type is OrderEventType.EXPIRED:
            if self.status not in {OrderStatus.CREATED, OrderStatus.ACCEPTED, OrderStatus.PARTIALLY_FILLED}:
                raise OrderStateMachineError("only active orders can expire")
            if event.status_after is not OrderStatus.EXPIRED:
                raise OrderStateMachineError("expired event must leave order expired")
            return
        if event.event_type is OrderEventType.CANCELLED:
            if self.status not in {OrderStatus.CREATED, OrderStatus.ACCEPTED, OrderStatus.PARTIALLY_FILLED}:
                raise OrderStateMachineError("only active orders can cancel")
            if event.status_after is not OrderStatus.CANCELLED:
                raise OrderStateMachineError("cancelled event must leave order cancelled")
            return
        raise OrderStateMachineError(f"unsupported order event type: {event.event_type}")

    def _ensure_not_terminal(self) -> None:
        if self.status in TERMINAL_ORDER_STATUSES:
            raise OrderStateMachineError(f"order is terminal: {self.status.value}")

    def _find_event(self, event_id: str) -> OrderEvent | None:
        return next((event for event in self.events if event.event_id == event_id), None)


def _enum_value(enum_type: type[StrEnum], field_name: str, value: object) -> Any:
    try:
        return enum_type(value)  # type: ignore[call-arg]
    except ValueError as exc:
        raise OrderStateMachineError(f"{field_name} must be one of {[item.value for item in enum_type]}") from exc


def _decimal_value(field_name: str, value: object) -> Decimal:
    if isinstance(value, bool):
        raise OrderStateMachineError(f"{field_name} must be a decimal value")
    try:
        decimal = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise OrderStateMachineError(f"{field_name} must be a decimal value") from exc
    if not decimal.is_finite():
        raise OrderStateMachineError(f"{field_name} must be finite")
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
            raise OrderStateMachineError(f"{field_name} must be greater than {minimum}")
    elif decimal < minimum:
        raise OrderStateMachineError(f"{field_name} cannot be less than {minimum}")
    return decimal


def _optional_positive_decimal(field_name: str, value: object) -> Decimal | None:
    if value is None:
        return None
    return _decimal_min(field_name, value, Decimal("0"), exclusive=True)


def _decimal_to_string(value: Decimal) -> str:
    return format(value, "f")


def _optional_decimal_to_string(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return _decimal_to_string(value)


def _validate_sha256(field_name: str, value: object) -> str:
    digest = _required_string(field_name, value)
    if not _SHA256_RE.fullmatch(digest):
        raise OrderStateMachineError(f"{field_name} must match sha256:<64 lowercase hex chars>")
    return digest


def _required_string(field_name: str, value: object) -> str:
    if type(value) is not str or not value.strip():
        raise OrderStateMachineError(f"{field_name} is required")
    return value


def _optional_string(value: object) -> str | None:
    if value is None:
        return None
    return _required_string("optional string", value)


def _message_string(value: object) -> str:
    if type(value) is not str:
        raise OrderStateMachineError("message must be a string")
    return value.strip()


def _set_if_present(record: dict[str, object], key: str, value: object | None) -> None:
    if value is not None:
        record[key] = value


def _require_date(field_name: str, value: object) -> None:
    if type(value) is not date:
        raise OrderStateMachineError(f"{field_name} must be a date")


def _require_aware_datetime(field_name: str, value: object) -> None:
    if type(value) is not datetime or value.tzinfo is None or value.utcoffset() is None:
        raise OrderStateMachineError(f"{field_name} must be a timezone-aware datetime")


def _normalize_metadata(metadata: Mapping[str, object] | None) -> Mapping[str, object]:
    if metadata is None:
        return MappingProxyType({})
    if not isinstance(metadata, Mapping):
        raise OrderStateMachineError("metadata must be a mapping")
    normalized = {_required_string("metadata key", key): value for key, value in sorted(metadata.items())}
    return MappingProxyType(normalized)
