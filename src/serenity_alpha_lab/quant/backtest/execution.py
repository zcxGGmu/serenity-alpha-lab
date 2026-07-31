from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from types import MappingProxyType
from typing import Any

from serenity_alpha_lab.domain.instruments import InstrumentId
from serenity_alpha_lab.quant.backtest.costs import CostBreakdown, CostModel, CostModelError
from serenity_alpha_lab.quant.backtest.orders import (
    Order,
    OrderEvent,
    OrderSide,
    OrderStatus,
    OrderType,
)
from serenity_alpha_lab.quant.backtest.spec import BacktestExecutionSpec


A_SHARE_EXECUTION_MODEL_CONTRACT_VERSION = "quant.a_share_execution_model@1.0.0"
A_SHARE_EXECUTION_MODEL_SCHEMA_NAME = "quant.backtest.a_share_execution_model"
A_SHARE_EXECUTION_MODEL_SCHEMA_VERSION = "1.0.0"
A_SHARE_EXECUTION_MODEL_VERSION = "cn_a_share_execution_model@1.0.0"

_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_DATASET_VERSION_RE = re.compile(r"^dsv_[0-9a-f]{32,64}$")


class AShareExecutionError(ValueError):
    """Raised when A-share execution inputs or rules violate the contract."""


class AShareExecutionOutcome(StrEnum):
    PASS = "pass"
    BLOCK = "block"
    WARN = "warn"


class AShareExecutionStatus(StrEnum):
    FILLED = "filled"
    REJECTED = "rejected"
    EXPIRED = "expired"
    KEPT_OPEN = "kept_open"


@dataclass(frozen=True, slots=True)
class AShareExecutionAuditRecord:
    rule_id: str
    outcome: AShareExecutionOutcome | str
    reason: str
    message: str
    order_id: str
    instrument_id: str
    trade_date: date
    occurred_at: datetime
    metadata: Mapping[str, object] | None = None
    contract_version: str = A_SHARE_EXECUTION_MODEL_CONTRACT_VERSION
    schema_name: str = A_SHARE_EXECUTION_MODEL_SCHEMA_NAME
    schema_version: str = A_SHARE_EXECUTION_MODEL_SCHEMA_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "rule_id", _required_string("rule_id", self.rule_id))
        object.__setattr__(self, "outcome", _enum_value(AShareExecutionOutcome, "outcome", self.outcome))
        object.__setattr__(self, "reason", _required_string("reason", self.reason))
        object.__setattr__(self, "message", _message_string(self.message))
        object.__setattr__(self, "order_id", _required_string("order_id", self.order_id))
        object.__setattr__(self, "instrument_id", _required_string("instrument_id", self.instrument_id))
        _require_date("trade_date", self.trade_date)
        _require_aware_datetime("occurred_at", self.occurred_at)
        object.__setattr__(self, "metadata", _normalize_metadata(self.metadata))
        object.__setattr__(self, "contract_version", _required_string("contract_version", self.contract_version))
        object.__setattr__(self, "schema_name", _required_string("schema_name", self.schema_name))
        object.__setattr__(self, "schema_version", _required_string("schema_version", self.schema_version))

    def to_record(self) -> dict[str, object]:
        record: dict[str, object] = {
            "contract_version": self.contract_version,
            "schema_name": self.schema_name,
            "schema_version": self.schema_version,
            "rule_id": self.rule_id,
            "outcome": self.outcome.value,
            "reason": self.reason,
            "message": self.message,
            "order_id": self.order_id,
            "instrument_id": self.instrument_id,
            "trade_date": self.trade_date.isoformat(),
            "occurred_at": self.occurred_at.isoformat(),
        }
        if self.metadata:
            record["metadata"] = dict(self.metadata)
        return record


@dataclass(frozen=True, slots=True)
class AShareMarketSnapshot:
    instrument_id: InstrumentId
    trade_date: date
    open: Decimal | int | str
    high: Decimal | int | str
    low: Decimal | int | str
    close: Decimal | int | str
    volume: Decimal | int | str
    is_trading: bool
    is_suspended: bool
    limit_up_price: Decimal | int | str
    limit_down_price: Decimal | int | str
    source_dataset_version: str
    metadata: Mapping[str, object] | None = None

    def __post_init__(self) -> None:
        if type(self.instrument_id) is not InstrumentId:
            raise AShareExecutionError("instrument_id must be an InstrumentId")
        _require_date("trade_date", self.trade_date)
        object.__setattr__(self, "open", _decimal_min("open", self.open, Decimal("0"), exclusive=True))
        object.__setattr__(self, "high", _decimal_min("high", self.high, Decimal("0"), exclusive=True))
        object.__setattr__(self, "low", _decimal_min("low", self.low, Decimal("0"), exclusive=True))
        object.__setattr__(self, "close", _decimal_min("close", self.close, Decimal("0"), exclusive=True))
        object.__setattr__(self, "volume", _decimal_min("volume", self.volume, Decimal("0"), exclusive=True))
        if type(self.is_trading) is not bool:
            raise AShareExecutionError("is_trading must be a bool")
        if type(self.is_suspended) is not bool:
            raise AShareExecutionError("is_suspended must be a bool")
        object.__setattr__(
            self,
            "limit_up_price",
            _decimal_min("limit_up_price", self.limit_up_price, Decimal("0"), exclusive=True),
        )
        object.__setattr__(
            self,
            "limit_down_price",
            _decimal_min("limit_down_price", self.limit_down_price, Decimal("0"), exclusive=True),
        )
        if self.limit_down_price > self.limit_up_price:
            raise AShareExecutionError("limit_down_price cannot exceed limit_up_price")
        object.__setattr__(
            self,
            "source_dataset_version",
            _validate_dataset_version("source_dataset_version", self.source_dataset_version),
        )
        object.__setattr__(self, "metadata", _normalize_metadata(self.metadata))

    def price_for(self, field_name: str) -> Decimal:
        field = _required_string("price field", field_name)
        if field not in {"open", "high", "low", "close"}:
            raise AShareExecutionError("execution_price_field must be one of open, high, low or close")
        return getattr(self, field)

    def to_record(self) -> dict[str, object]:
        record: dict[str, object] = {
            "instrument_id": self.instrument_id.canonical,
            "trade_date": self.trade_date.isoformat(),
            "open": _decimal_to_string(self.open),
            "high": _decimal_to_string(self.high),
            "low": _decimal_to_string(self.low),
            "close": _decimal_to_string(self.close),
            "volume": _decimal_to_string(self.volume),
            "is_trading": self.is_trading,
            "is_suspended": self.is_suspended,
            "limit_up_price": _decimal_to_string(self.limit_up_price),
            "limit_down_price": _decimal_to_string(self.limit_down_price),
            "source_dataset_version": self.source_dataset_version,
        }
        if self.metadata:
            record["metadata"] = dict(self.metadata)
        return record


@dataclass(frozen=True, slots=True)
class ASharePositionAvailability:
    instrument_id: InstrumentId
    trade_date: date
    total_quantity: Decimal | int | str
    sellable_quantity: Decimal | int | str
    locked_t_plus_one_quantity: Decimal | int | str = Decimal("0")
    source: str = "portfolio_ledger"

    def __post_init__(self) -> None:
        if type(self.instrument_id) is not InstrumentId:
            raise AShareExecutionError("instrument_id must be an InstrumentId")
        _require_date("trade_date", self.trade_date)
        object.__setattr__(self, "total_quantity", _decimal_min("total_quantity", self.total_quantity, Decimal("0")))
        object.__setattr__(
            self,
            "sellable_quantity",
            _decimal_min("sellable_quantity", self.sellable_quantity, Decimal("0")),
        )
        object.__setattr__(
            self,
            "locked_t_plus_one_quantity",
            _decimal_min("locked_t_plus_one_quantity", self.locked_t_plus_one_quantity, Decimal("0")),
        )
        object.__setattr__(self, "source", _required_string("source", self.source))
        if self.sellable_quantity > self.total_quantity:
            raise AShareExecutionError("sellable_quantity cannot exceed total_quantity")
        if self.sellable_quantity + self.locked_t_plus_one_quantity > self.total_quantity:
            raise AShareExecutionError("sellable plus locked quantity cannot exceed total_quantity")

    def to_record(self) -> dict[str, object]:
        return {
            "instrument_id": self.instrument_id.canonical,
            "trade_date": self.trade_date.isoformat(),
            "total_quantity": _decimal_to_string(self.total_quantity),
            "sellable_quantity": _decimal_to_string(self.sellable_quantity),
            "locked_t_plus_one_quantity": _decimal_to_string(self.locked_t_plus_one_quantity),
            "source": self.source,
        }


@dataclass(frozen=True, slots=True)
class AShareExecutionResult:
    spec_hash: str
    status: AShareExecutionStatus | str
    order: Order
    audit_records: tuple[AShareExecutionAuditRecord, ...]
    fill_event: OrderEvent | None = None
    cost_breakdown: CostBreakdown | None = None
    execution_price: Decimal | int | str | None = None
    executed_quantity: Decimal | int | str | None = None
    reason: str | None = None
    model_version: str = A_SHARE_EXECUTION_MODEL_VERSION
    contract_version: str = A_SHARE_EXECUTION_MODEL_CONTRACT_VERSION
    schema_name: str = A_SHARE_EXECUTION_MODEL_SCHEMA_NAME
    schema_version: str = A_SHARE_EXECUTION_MODEL_SCHEMA_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "spec_hash", _validate_sha256("spec_hash", self.spec_hash))
        object.__setattr__(self, "status", _enum_value(AShareExecutionStatus, "status", self.status))
        if type(self.order) is not Order:
            raise AShareExecutionError("order must be an Order")
        audit_records = tuple(self.audit_records)
        for record in audit_records:
            if type(record) is not AShareExecutionAuditRecord:
                raise AShareExecutionError("audit_records must contain AShareExecutionAuditRecord values")
        object.__setattr__(self, "audit_records", audit_records)
        if self.fill_event is not None and type(self.fill_event) is not OrderEvent:
            raise AShareExecutionError("fill_event must be an OrderEvent")
        if self.cost_breakdown is not None and type(self.cost_breakdown) is not CostBreakdown:
            raise AShareExecutionError("cost_breakdown must be a CostBreakdown")
        object.__setattr__(self, "execution_price", _optional_positive_decimal("execution_price", self.execution_price))
        object.__setattr__(
            self,
            "executed_quantity",
            _optional_positive_decimal("executed_quantity", self.executed_quantity),
        )
        object.__setattr__(self, "reason", _optional_string(self.reason))
        object.__setattr__(self, "model_version", _required_string("model_version", self.model_version))
        object.__setattr__(self, "contract_version", _required_string("contract_version", self.contract_version))
        object.__setattr__(self, "schema_name", _required_string("schema_name", self.schema_name))
        object.__setattr__(self, "schema_version", _required_string("schema_version", self.schema_version))

    def to_record(self) -> dict[str, object]:
        record: dict[str, object] = {
            "contract_version": self.contract_version,
            "schema_name": self.schema_name,
            "schema_version": self.schema_version,
            "model_version": self.model_version,
            "spec_hash": self.spec_hash,
            "status": self.status.value,
            "order": self.order.to_record(),
            "audit_records": [audit.to_record() for audit in self.audit_records],
        }
        if self.fill_event is not None:
            record["fill_event"] = self.fill_event.to_record()
        if self.cost_breakdown is not None:
            record["cost_breakdown"] = self.cost_breakdown.to_record()
        if self.execution_price is not None:
            record["execution_price"] = _decimal_to_string(self.execution_price)
        if self.executed_quantity is not None:
            record["executed_quantity"] = _decimal_to_string(self.executed_quantity)
        if self.reason is not None:
            record["reason"] = self.reason
        return record


@dataclass(frozen=True, slots=True)
class AShareExecutionModel:
    spec_hash: str
    execution_spec: BacktestExecutionSpec
    cost_model: CostModel
    model_version: str = A_SHARE_EXECUTION_MODEL_VERSION
    contract_version: str = A_SHARE_EXECUTION_MODEL_CONTRACT_VERSION
    schema_name: str = A_SHARE_EXECUTION_MODEL_SCHEMA_NAME
    schema_version: str = A_SHARE_EXECUTION_MODEL_SCHEMA_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "spec_hash", _validate_sha256("spec_hash", self.spec_hash))
        if type(self.execution_spec) is not BacktestExecutionSpec:
            raise AShareExecutionError("execution_spec must be a BacktestExecutionSpec")
        if type(self.cost_model) is not CostModel:
            raise AShareExecutionError("cost_model must be a CostModel")
        if self.cost_model.spec_hash != self.spec_hash:
            raise AShareExecutionError("cost_model spec_hash must match execution model")
        object.__setattr__(self, "model_version", _required_string("model_version", self.model_version))
        object.__setattr__(self, "contract_version", _required_string("contract_version", self.contract_version))
        object.__setattr__(self, "schema_name", _required_string("schema_name", self.schema_name))
        object.__setattr__(self, "schema_version", _required_string("schema_version", self.schema_version))

    def execute(
        self,
        *,
        order: Order,
        market_snapshot: AShareMarketSnapshot,
        occurred_at: datetime,
        event_id_prefix: str,
        position_availability: ASharePositionAvailability | None = None,
    ) -> AShareExecutionResult:
        self._validate_request(
            order=order,
            market_snapshot=market_snapshot,
            occurred_at=occurred_at,
            event_id_prefix=event_id_prefix,
            position_availability=position_availability,
        )
        event_prefix = _required_string("event_id_prefix", event_id_prefix)
        audit_records: list[AShareExecutionAuditRecord] = []
        quantity = order.remaining_quantity

        if order.intent.signal_time.date() >= order.intent.trade_date:
            audit_records.append(
                self._audit(
                    order=order,
                    market_snapshot=market_snapshot,
                    occurred_at=occurred_at,
                    rule_id="signal_available_before_execution",
                    outcome=AShareExecutionOutcome.BLOCK,
                    reason="signal_not_available_for_execution",
                    message="Close or after-close signals must execute on a later trade date.",
                )
            )
            return self._reject_order(
                order=order,
                reason="signal_not_available_for_execution",
                occurred_at=occurred_at,
                event_id_prefix=event_prefix,
                audit_records=tuple(audit_records),
            )
        audit_records.append(
            self._audit(
                order=order,
                market_snapshot=market_snapshot,
                occurred_at=occurred_at,
                rule_id="signal_available_before_execution",
                outcome=AShareExecutionOutcome.PASS,
                reason="execution_date_after_signal_date",
                message="Signal time precedes the execution trade date.",
            )
        )

        if quantity % Decimal(self.execution_spec.lot_size) != 0:
            audit_records.append(
                self._audit(
                    order=order,
                    market_snapshot=market_snapshot,
                    occurred_at=occurred_at,
                    rule_id="trade_unit_lot_size",
                    outcome=AShareExecutionOutcome.BLOCK,
                    reason="invalid_trade_unit",
                    message="Order quantity must be a multiple of the configured A-share lot size.",
                    metadata={
                        "remaining_quantity": _decimal_to_string(quantity),
                        "lot_size": self.execution_spec.lot_size,
                    },
                )
            )
            return self._reject_order(
                order=order,
                reason="invalid_trade_unit",
                occurred_at=occurred_at,
                event_id_prefix=event_prefix,
                audit_records=tuple(audit_records),
            )
        audit_records.append(
            self._audit(
                order=order,
                market_snapshot=market_snapshot,
                occurred_at=occurred_at,
                rule_id="trade_unit_lot_size",
                outcome=AShareExecutionOutcome.PASS,
                reason="quantity_matches_lot_size",
                message="Order quantity matches the configured A-share lot size.",
                metadata={"lot_size": self.execution_spec.lot_size},
            )
        )

        if market_snapshot.is_suspended or not market_snapshot.is_trading:
            reason = "security_suspended" if market_snapshot.is_suspended else "not_trading"
            audit_records.append(
                self._audit(
                    order=order,
                    market_snapshot=market_snapshot,
                    occurred_at=occurred_at,
                    rule_id="market_tradable_status",
                    outcome=AShareExecutionOutcome.BLOCK,
                    reason=reason,
                    message="Security is not tradable for this execution date.",
                    metadata={
                        "is_trading": market_snapshot.is_trading,
                        "is_suspended": market_snapshot.is_suspended,
                    },
                )
            )
            return self._apply_unfilled_policy(
                order=order,
                reason=reason,
                policy=self.execution_spec.suspended_security_policy,
                occurred_at=occurred_at,
                event_id_prefix=event_prefix,
                audit_records=tuple(audit_records),
            )
        audit_records.append(
            self._audit(
                order=order,
                market_snapshot=market_snapshot,
                occurred_at=occurred_at,
                rule_id="market_tradable_status",
                outcome=AShareExecutionOutcome.PASS,
                reason="security_tradable",
                message="Security is trading and not suspended.",
            )
        )

        if order.intent.side is OrderSide.SELL:
            if position_availability is None:
                raise AShareExecutionError("position_availability is required for sell orders")
            if position_availability.sellable_quantity < quantity:
                audit_records.append(
                    self._audit(
                        order=order,
                        market_snapshot=market_snapshot,
                        occurred_at=occurred_at,
                        rule_id="t_plus_one_sellable_quantity",
                        outcome=AShareExecutionOutcome.BLOCK,
                        reason="t_plus_one_sell_restricted",
                        message="Sell quantity exceeds T+1 sellable quantity.",
                        metadata=position_availability.to_record(),
                    )
                )
                return self._apply_unfilled_policy(
                    order=order,
                    reason="t_plus_one_sell_restricted",
                    policy=self.execution_spec.unfilled_order_policy,
                    occurred_at=occurred_at,
                    event_id_prefix=event_prefix,
                    audit_records=tuple(audit_records),
                )
            audit_records.append(
                self._audit(
                    order=order,
                    market_snapshot=market_snapshot,
                    occurred_at=occurred_at,
                    rule_id="t_plus_one_sellable_quantity",
                    outcome=AShareExecutionOutcome.PASS,
                    reason="sellable_quantity_available",
                    message="Sell quantity is within T+1 sellable quantity.",
                    metadata=position_availability.to_record(),
                )
            )

        execution_price = market_snapshot.price_for(self.execution_spec.execution_price_field)
        limit_reason = self._limit_up_down_block_reason(order=order, market_snapshot=market_snapshot, price=execution_price)
        if limit_reason is not None:
            audit_records.append(
                self._audit(
                    order=order,
                    market_snapshot=market_snapshot,
                    occurred_at=occurred_at,
                    rule_id="limit_up_down_executable",
                    outcome=AShareExecutionOutcome.BLOCK,
                    reason=limit_reason,
                    message="Execution price is at an A-share daily price limit for this side.",
                    metadata={
                        "execution_price": _decimal_to_string(execution_price),
                        "limit_up_price": _decimal_to_string(market_snapshot.limit_up_price),
                        "limit_down_price": _decimal_to_string(market_snapshot.limit_down_price),
                    },
                )
            )
            return self._apply_unfilled_policy(
                order=order,
                reason=limit_reason,
                policy=self.execution_spec.unfilled_order_policy,
                occurred_at=occurred_at,
                event_id_prefix=event_prefix,
                audit_records=tuple(audit_records),
            )
        audit_records.append(
            self._audit(
                order=order,
                market_snapshot=market_snapshot,
                occurred_at=occurred_at,
                rule_id="limit_up_down_executable",
                outcome=AShareExecutionOutcome.PASS,
                reason="not_at_unfillable_price_limit",
                message="Execution price is not at the unfillable A-share price limit for this side.",
            )
        )

        price_cross_reason = self._limit_price_block_reason(order=order, price=execution_price)
        if price_cross_reason is not None:
            audit_records.append(
                self._audit(
                    order=order,
                    market_snapshot=market_snapshot,
                    occurred_at=occurred_at,
                    rule_id="order_limit_price_crosses_execution_price",
                    outcome=AShareExecutionOutcome.BLOCK,
                    reason=price_cross_reason,
                    message="Limit order price does not cross the execution price.",
                    metadata={
                        "execution_price": _decimal_to_string(execution_price),
                        "limit_price": _decimal_to_string(order.intent.limit_price)
                        if order.intent.limit_price is not None
                        else None,
                    },
                )
            )
            return self._apply_unfilled_policy(
                order=order,
                reason=price_cross_reason,
                policy=self.execution_spec.unfilled_order_policy,
                occurred_at=occurred_at,
                event_id_prefix=event_prefix,
                audit_records=tuple(audit_records),
            )
        audit_records.append(
            self._audit(
                order=order,
                market_snapshot=market_snapshot,
                occurred_at=occurred_at,
                rule_id="order_limit_price_crosses_execution_price",
                outcome=AShareExecutionOutcome.PASS,
                reason="market_or_crossed_limit_order",
                message="Order type and limit price allow execution at the selected price.",
            )
        )

        participation_rate = quantity / market_snapshot.volume
        if participation_rate > self.cost_model.cost_spec.max_participation_rate:
            audit_records.append(
                self._audit(
                    order=order,
                    market_snapshot=market_snapshot,
                    occurred_at=occurred_at,
                    rule_id="cost_model_participation",
                    outcome=AShareExecutionOutcome.BLOCK,
                    reason="participation_rate_exceeded",
                    message="Order quantity exceeds the configured maximum participation rate.",
                    metadata={
                        "participation_rate": _decimal_to_string(participation_rate),
                        "max_participation_rate": _decimal_to_string(
                            self.cost_model.cost_spec.max_participation_rate
                        ),
                    },
                )
            )
            return self._apply_unfilled_policy(
                order=order,
                reason="participation_rate_exceeded",
                policy=self.execution_spec.unfilled_order_policy,
                occurred_at=occurred_at,
                event_id_prefix=event_prefix,
                audit_records=tuple(audit_records),
            )
        audit_records.append(
            self._audit(
                order=order,
                market_snapshot=market_snapshot,
                occurred_at=occurred_at,
                rule_id="cost_model_participation",
                outcome=AShareExecutionOutcome.PASS,
                reason="within_participation_limit",
                message="Order quantity is within the configured participation-rate limit.",
                metadata={
                    "participation_rate": _decimal_to_string(participation_rate),
                    "max_participation_rate": _decimal_to_string(self.cost_model.cost_spec.max_participation_rate),
                },
            )
        )

        working_order = self._ensure_accepted(
            order=order,
            occurred_at=occurred_at,
            event_id_prefix=event_prefix,
        )
        filled_order = working_order.record_fill(
            event_id=f"{event_prefix}-fill-event",
            occurred_at=occurred_at,
            fill_quantity=working_order.remaining_quantity,
            fill_price=execution_price,
            execution_id=f"{event_prefix}-fill",
        )
        fill_event = filled_order.events[-1]
        try:
            cost_breakdown = self.cost_model.calculate(
                order=filled_order,
                fill_event=fill_event,
                market_volume=market_snapshot.volume,
            )
        except CostModelError as exc:
            raise AShareExecutionError(str(exc)) from exc

        return AShareExecutionResult(
            spec_hash=self.spec_hash,
            status=AShareExecutionStatus.FILLED,
            order=filled_order,
            audit_records=tuple(audit_records),
            fill_event=fill_event,
            cost_breakdown=cost_breakdown,
            execution_price=execution_price,
            executed_quantity=fill_event.fill_quantity,
        )

    def _validate_request(
        self,
        *,
        order: Order,
        market_snapshot: AShareMarketSnapshot,
        occurred_at: datetime,
        event_id_prefix: str,
        position_availability: ASharePositionAvailability | None,
    ) -> None:
        if type(order) is not Order:
            raise AShareExecutionError("order must be an Order")
        if order.intent.spec_hash != self.spec_hash:
            raise AShareExecutionError("order spec_hash must match execution model")
        if order.status not in {OrderStatus.CREATED, OrderStatus.ACCEPTED, OrderStatus.PARTIALLY_FILLED}:
            raise AShareExecutionError(f"order is not executable: {order.status.value}")
        if type(market_snapshot) is not AShareMarketSnapshot:
            raise AShareExecutionError("market_snapshot must be an AShareMarketSnapshot")
        if market_snapshot.instrument_id != order.intent.instrument_id:
            raise AShareExecutionError("market_snapshot instrument_id must match order")
        if market_snapshot.trade_date != order.intent.trade_date:
            raise AShareExecutionError("market_snapshot trade_date must match order")
        _require_aware_datetime("occurred_at", occurred_at)
        _required_string("event_id_prefix", event_id_prefix)
        if position_availability is not None:
            if type(position_availability) is not ASharePositionAvailability:
                raise AShareExecutionError("position_availability must be an ASharePositionAvailability")
            if position_availability.instrument_id != order.intent.instrument_id:
                raise AShareExecutionError("position_availability instrument_id must match order")
            if position_availability.trade_date != order.intent.trade_date:
                raise AShareExecutionError("position_availability trade_date must match order")

    def _limit_up_down_block_reason(
        self,
        *,
        order: Order,
        market_snapshot: AShareMarketSnapshot,
        price: Decimal,
    ) -> str | None:
        if order.intent.side is OrderSide.BUY and price >= market_snapshot.limit_up_price:
            return "limit_up_unfillable"
        if order.intent.side is OrderSide.SELL and price <= market_snapshot.limit_down_price:
            return "limit_down_unfillable"
        return None

    def _limit_price_block_reason(self, *, order: Order, price: Decimal) -> str | None:
        if order.intent.order_type is not OrderType.LIMIT:
            return None
        assert order.intent.limit_price is not None
        if order.intent.side is OrderSide.BUY and order.intent.limit_price < price:
            return "limit_price_not_crossed"
        if order.intent.side is OrderSide.SELL and order.intent.limit_price > price:
            return "limit_price_not_crossed"
        return None

    def _apply_unfilled_policy(
        self,
        *,
        order: Order,
        reason: str,
        policy: str,
        occurred_at: datetime,
        event_id_prefix: str,
        audit_records: tuple[AShareExecutionAuditRecord, ...],
    ) -> AShareExecutionResult:
        policy_name = _required_string("policy", policy)
        if policy_name == "reject_order":
            return self._reject_order(
                order=order,
                reason=reason,
                occurred_at=occurred_at,
                event_id_prefix=event_id_prefix,
                audit_records=audit_records,
            )
        if policy_name in {"expire_after_rebalance", "expire_order"}:
            working_order = self._ensure_accepted(
                order=order,
                occurred_at=occurred_at,
                event_id_prefix=event_id_prefix,
            )
            expired = working_order.expire(
                event_id=f"{event_id_prefix}-expire",
                occurred_at=occurred_at,
                reason=reason,
            )
            return AShareExecutionResult(
                spec_hash=self.spec_hash,
                status=AShareExecutionStatus.EXPIRED,
                order=expired,
                audit_records=audit_records,
                reason=reason,
            )
        if policy_name == "keep_open_until_cancelled":
            accepted = self._ensure_accepted(
                order=order,
                occurred_at=occurred_at,
                event_id_prefix=event_id_prefix,
            )
            return AShareExecutionResult(
                spec_hash=self.spec_hash,
                status=AShareExecutionStatus.KEPT_OPEN,
                order=accepted,
                audit_records=audit_records,
                reason=reason,
            )
        raise AShareExecutionError(f"unsupported unfilled order policy: {policy_name}")

    def _reject_order(
        self,
        *,
        order: Order,
        reason: str,
        occurred_at: datetime,
        event_id_prefix: str,
        audit_records: tuple[AShareExecutionAuditRecord, ...],
    ) -> AShareExecutionResult:
        if order.status is OrderStatus.PARTIALLY_FILLED:
            expired = order.expire(
                event_id=f"{event_id_prefix}-expire",
                occurred_at=occurred_at,
                reason=reason,
            )
            return AShareExecutionResult(
                spec_hash=self.spec_hash,
                status=AShareExecutionStatus.EXPIRED,
                order=expired,
                audit_records=audit_records,
                reason=reason,
            )
        rejected = order.reject(
            event_id=f"{event_id_prefix}-reject",
            occurred_at=occurred_at,
            reason=reason,
        )
        return AShareExecutionResult(
            spec_hash=self.spec_hash,
            status=AShareExecutionStatus.REJECTED,
            order=rejected,
            audit_records=audit_records,
            reason=reason,
        )

    def _ensure_accepted(self, *, order: Order, occurred_at: datetime, event_id_prefix: str) -> Order:
        if order.status is OrderStatus.CREATED:
            return order.accept(
                event_id=f"{event_id_prefix}-accepted",
                occurred_at=occurred_at,
                reason="a_share_execution_rules_passed",
            )
        if order.status in {OrderStatus.ACCEPTED, OrderStatus.PARTIALLY_FILLED}:
            return order
        raise AShareExecutionError(f"order is not active: {order.status.value}")

    def _audit(
        self,
        *,
        order: Order,
        market_snapshot: AShareMarketSnapshot,
        occurred_at: datetime,
        rule_id: str,
        outcome: AShareExecutionOutcome,
        reason: str,
        message: str,
        metadata: Mapping[str, object] | None = None,
    ) -> AShareExecutionAuditRecord:
        return AShareExecutionAuditRecord(
            rule_id=rule_id,
            outcome=outcome,
            reason=reason,
            message=message,
            order_id=order.order_id,
            instrument_id=order.intent.instrument_id.canonical,
            trade_date=market_snapshot.trade_date,
            occurred_at=occurred_at,
            metadata=metadata,
        )


def _enum_value(enum_type: type[StrEnum], field_name: str, value: object) -> Any:
    try:
        return enum_type(value)  # type: ignore[call-arg]
    except ValueError as exc:
        raise AShareExecutionError(f"{field_name} must be one of {[item.value for item in enum_type]}") from exc


def _decimal_value(field_name: str, value: object) -> Decimal:
    if isinstance(value, bool):
        raise AShareExecutionError(f"{field_name} must be a decimal value")
    try:
        decimal = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise AShareExecutionError(f"{field_name} must be a decimal value") from exc
    if not decimal.is_finite():
        raise AShareExecutionError(f"{field_name} must be finite")
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
            raise AShareExecutionError(f"{field_name} must be greater than {minimum}")
    elif decimal < minimum:
        raise AShareExecutionError(f"{field_name} cannot be less than {minimum}")
    return decimal


def _optional_positive_decimal(field_name: str, value: object) -> Decimal | None:
    if value is None:
        return None
    return _decimal_min(field_name, value, Decimal("0"), exclusive=True)


def _decimal_to_string(value: Decimal) -> str:
    return format(value, "f")


def _validate_sha256(field_name: str, value: object) -> str:
    digest = _required_string(field_name, value)
    if not _SHA256_RE.fullmatch(digest):
        raise AShareExecutionError(f"{field_name} must be sha256:<64 lowercase hex>")
    return digest


def _validate_dataset_version(field_name: str, value: object) -> str:
    version = _required_string(field_name, value)
    if not _DATASET_VERSION_RE.fullmatch(version):
        raise AShareExecutionError(f"{field_name} must be a concrete dsv_* Dataset Version")
    return version


def _required_string(field_name: str, value: object) -> str:
    if type(value) is not str or not value.strip():
        raise AShareExecutionError(f"{field_name} is required")
    return value


def _optional_string(value: object) -> str | None:
    if value is None:
        return None
    return _required_string("optional string", value)


def _message_string(value: object) -> str:
    if type(value) is not str or not value.strip():
        raise AShareExecutionError("message is required")
    return value.strip()


def _require_date(field_name: str, value: object) -> None:
    if type(value) is not date:
        raise AShareExecutionError(f"{field_name} must be a date")


def _require_aware_datetime(field_name: str, value: object) -> None:
    if type(value) is not datetime or value.tzinfo is None or value.utcoffset() is None:
        raise AShareExecutionError(f"{field_name} must be timezone-aware")


def _normalize_metadata(metadata: Mapping[str, object] | None) -> MappingProxyType[str, object]:
    if metadata is None:
        return MappingProxyType({})
    if not isinstance(metadata, Mapping):
        raise AShareExecutionError("metadata must be a mapping")
    normalized: dict[str, object] = {}
    for key, value in metadata.items():
        normalized[_required_string("metadata key", key)] = value
    return MappingProxyType(normalized)
