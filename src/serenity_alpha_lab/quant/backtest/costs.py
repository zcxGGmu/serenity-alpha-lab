from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from typing import Any

from serenity_alpha_lab.quant.backtest.orders import Order, OrderEvent, OrderEventType, OrderSide
from serenity_alpha_lab.quant.backtest.spec import BacktestCostSpec


BACKTEST_COST_MODEL_CONTRACT_VERSION = "quant.cost_model@1.0.0"
BACKTEST_COST_MODEL_SCHEMA_NAME = "quant.backtest.cost_model"
BACKTEST_COST_MODEL_SCHEMA_VERSION = "1.0.0"
BACKTEST_COST_MODEL_VERSION = "cn_a_share_cost_model@1.0.0"

_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_BPS_DENOMINATOR = Decimal("10000")


class CostModelError(ValueError):
    """Raised when a cost model input or calculation violates the contract."""


class CostLineItemName(StrEnum):
    COMMISSION = "commission"
    STAMP_TAX = "stamp_tax"
    TRANSFER_FEE = "transfer_fee"
    SLIPPAGE = "slippage"
    IMPACT = "impact"


@dataclass(frozen=True, slots=True)
class CostLineItem:
    name: CostLineItemName | str
    amount: Decimal | int | str
    rate_bps: Decimal | int | str
    basis_amount: Decimal | int | str
    applies_to_side: OrderSide | str | None = None
    description: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", _enum_value(CostLineItemName, "name", self.name))
        object.__setattr__(self, "amount", _decimal_min("amount", self.amount, Decimal("0")))
        object.__setattr__(self, "rate_bps", _decimal_min("rate_bps", self.rate_bps, Decimal("0")))
        object.__setattr__(self, "basis_amount", _decimal_min("basis_amount", self.basis_amount, Decimal("0")))
        object.__setattr__(self, "applies_to_side", _optional_enum_value(OrderSide, "applies_to_side", self.applies_to_side))
        if not isinstance(self.description, str):
            raise CostModelError("description must be a string")

    def to_record(self) -> dict[str, object]:
        record: dict[str, object] = {
            "name": self.name.value,
            "amount": _decimal_to_string(self.amount),
            "rate_bps": _decimal_to_string(self.rate_bps),
            "basis_amount": _decimal_to_string(self.basis_amount),
        }
        if self.applies_to_side is not None:
            record["applies_to_side"] = self.applies_to_side.value
        if self.description:
            record["description"] = self.description
        return record


@dataclass(frozen=True, slots=True)
class CostBreakdown:
    spec_hash: str
    order_id: str
    execution_id: str
    instrument_id: str
    side: OrderSide | str
    quantity: Decimal | int | str
    fill_price: Decimal | int | str
    effective_price: Decimal | int | str
    gross_amount: Decimal | int | str
    total_cost: Decimal | int | str
    participation_rate: Decimal | int | str
    max_participation_rate: Decimal | int | str
    line_items: tuple[CostLineItem, ...]
    filled_at: datetime
    pre_cost_cash_amount: Decimal | int | str
    post_cost_cash_amount: Decimal | int | str
    model_version: str = BACKTEST_COST_MODEL_VERSION
    contract_version: str = BACKTEST_COST_MODEL_CONTRACT_VERSION
    schema_name: str = BACKTEST_COST_MODEL_SCHEMA_NAME
    schema_version: str = BACKTEST_COST_MODEL_SCHEMA_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "spec_hash", _validate_sha256("spec_hash", self.spec_hash))
        object.__setattr__(self, "order_id", _required_string("order_id", self.order_id))
        object.__setattr__(self, "execution_id", _required_string("execution_id", self.execution_id))
        object.__setattr__(self, "instrument_id", _required_string("instrument_id", self.instrument_id))
        object.__setattr__(self, "side", _enum_value(OrderSide, "side", self.side))
        object.__setattr__(self, "quantity", _decimal_min("quantity", self.quantity, Decimal("0"), exclusive=True))
        object.__setattr__(self, "fill_price", _decimal_min("fill_price", self.fill_price, Decimal("0"), exclusive=True))
        object.__setattr__(self, "effective_price", _decimal_min("effective_price", self.effective_price, Decimal("0"), exclusive=True))
        object.__setattr__(self, "gross_amount", _decimal_min("gross_amount", self.gross_amount, Decimal("0")))
        object.__setattr__(self, "total_cost", _decimal_min("total_cost", self.total_cost, Decimal("0")))
        object.__setattr__(self, "participation_rate", _decimal_min("participation_rate", self.participation_rate, Decimal("0")))
        object.__setattr__(
            self,
            "max_participation_rate",
            _decimal_min("max_participation_rate", self.max_participation_rate, Decimal("0"), exclusive=True),
        )
        items = tuple(self.line_items)
        for item in items:
            if type(item) is not CostLineItem:
                raise CostModelError("line_items must contain CostLineItem values")
        object.__setattr__(self, "line_items", items)
        _require_aware_datetime("filled_at", self.filled_at)
        object.__setattr__(self, "pre_cost_cash_amount", _decimal_min("pre_cost_cash_amount", self.pre_cost_cash_amount, Decimal("0")))
        object.__setattr__(self, "post_cost_cash_amount", _decimal_min("post_cost_cash_amount", self.post_cost_cash_amount, Decimal("0")))
        object.__setattr__(self, "model_version", _required_string("model_version", self.model_version))
        object.__setattr__(self, "contract_version", _required_string("contract_version", self.contract_version))
        object.__setattr__(self, "schema_name", _required_string("schema_name", self.schema_name))
        object.__setattr__(self, "schema_version", _required_string("schema_version", self.schema_version))
        if sum((item.amount for item in items), Decimal("0")) != self.total_cost:
            raise CostModelError("total_cost must equal line item sum")

    def line_item_amount(self, name: CostLineItemName | str) -> Decimal:
        item_name = _enum_value(CostLineItemName, "name", name)
        for item in self.line_items:
            if item.name is item_name:
                return item.amount
        raise CostModelError(f"unknown cost line item: {item_name.value}")

    def to_record(self) -> dict[str, object]:
        return {
            "contract_version": self.contract_version,
            "schema_name": self.schema_name,
            "schema_version": self.schema_version,
            "model_version": self.model_version,
            "spec_hash": self.spec_hash,
            "order_id": self.order_id,
            "execution_id": self.execution_id,
            "instrument_id": self.instrument_id,
            "side": self.side.value,
            "quantity": _decimal_to_string(self.quantity),
            "fill_price": _decimal_to_string(self.fill_price),
            "effective_price": _decimal_to_string(self.effective_price),
            "gross_amount": _decimal_to_string(self.gross_amount),
            "total_cost": _decimal_to_string(self.total_cost),
            "pre_cost_cash_amount": _decimal_to_string(self.pre_cost_cash_amount),
            "post_cost_cash_amount": _decimal_to_string(self.post_cost_cash_amount),
            "participation_rate": _decimal_to_string(self.participation_rate),
            "max_participation_rate": _decimal_to_string(self.max_participation_rate),
            "filled_at": self.filled_at.isoformat(),
            "line_items": {item.name.value: item.to_record() for item in self.line_items},
        }


@dataclass(frozen=True, slots=True)
class CostModel:
    spec_hash: str
    cost_spec: BacktestCostSpec
    model_version: str = BACKTEST_COST_MODEL_VERSION
    contract_version: str = BACKTEST_COST_MODEL_CONTRACT_VERSION
    schema_name: str = BACKTEST_COST_MODEL_SCHEMA_NAME
    schema_version: str = BACKTEST_COST_MODEL_SCHEMA_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "spec_hash", _validate_sha256("spec_hash", self.spec_hash))
        if type(self.cost_spec) is not BacktestCostSpec:
            raise CostModelError("cost_spec must be a BacktestCostSpec")
        object.__setattr__(self, "model_version", _required_string("model_version", self.model_version))
        object.__setattr__(self, "contract_version", _required_string("contract_version", self.contract_version))
        object.__setattr__(self, "schema_name", _required_string("schema_name", self.schema_name))
        object.__setattr__(self, "schema_version", _required_string("schema_version", self.schema_version))

    def calculate(
        self,
        *,
        order: Order,
        fill_event: OrderEvent,
        market_volume: Decimal | int | str,
    ) -> CostBreakdown:
        if type(order) is not Order:
            raise CostModelError("order must be an Order")
        if type(fill_event) is not OrderEvent:
            raise CostModelError("fill_event must be an OrderEvent")
        if fill_event.event_type not in {OrderEventType.PARTIALLY_FILLED, OrderEventType.FILLED}:
            raise CostModelError("fill_event must be a fill event")
        if fill_event not in order.events:
            raise CostModelError("fill_event must be part of the order event history")
        if fill_event.order_id != order.order_id:
            raise CostModelError("fill_event order_id must match order")
        if order.intent.spec_hash != self.spec_hash:
            raise CostModelError("order spec_hash must match cost model")
        assert fill_event.fill_quantity is not None
        assert fill_event.fill_price is not None
        assert fill_event.execution_id is not None

        quantity = fill_event.fill_quantity
        price = fill_event.fill_price
        volume = _decimal_min("market_volume", market_volume, Decimal("0"), exclusive=True)
        participation_rate = quantity / volume
        if participation_rate > self.cost_spec.max_participation_rate:
            raise CostModelError("participation rate exceeds maximum")

        gross_amount = quantity * price
        commission = max(_bps_amount(gross_amount, self.cost_spec.commission_bps), self.cost_spec.min_commission)
        stamp_tax = (
            _bps_amount(gross_amount, self.cost_spec.stamp_tax_bps)
            if order.intent.side is OrderSide.SELL
            else Decimal("0")
        )
        transfer_fee = _bps_amount(gross_amount, self.cost_spec.transfer_fee_bps)
        slippage = _bps_amount(gross_amount, self.cost_spec.slippage_bps)
        impact = _bps_amount(gross_amount, self.cost_spec.impact_bps)
        total_cost = commission + stamp_tax + transfer_fee + slippage + impact
        price_adjustment = _bps_amount(price, self.cost_spec.slippage_bps + self.cost_spec.impact_bps)
        effective_price = (
            price + price_adjustment if order.intent.side is OrderSide.BUY else price - price_adjustment
        )
        post_cost_cash_amount = (
            gross_amount + total_cost if order.intent.side is OrderSide.BUY else gross_amount - total_cost
        )
        if post_cost_cash_amount < 0:
            raise CostModelError("total cost cannot exceed gross proceeds")

        return CostBreakdown(
            spec_hash=self.spec_hash,
            order_id=order.order_id,
            execution_id=fill_event.execution_id,
            instrument_id=order.intent.instrument_id.canonical,
            side=order.intent.side,
            quantity=quantity,
            fill_price=price,
            effective_price=effective_price,
            gross_amount=gross_amount,
            total_cost=total_cost,
            participation_rate=participation_rate,
            max_participation_rate=self.cost_spec.max_participation_rate,
            filled_at=fill_event.occurred_at,
            pre_cost_cash_amount=gross_amount,
            post_cost_cash_amount=post_cost_cash_amount,
            line_items=(
                CostLineItem(
                    name=CostLineItemName.COMMISSION,
                    amount=commission,
                    rate_bps=self.cost_spec.commission_bps,
                    basis_amount=gross_amount,
                    description="max(gross_amount * commission_bps / 10000, min_commission)",
                ),
                CostLineItem(
                    name=CostLineItemName.STAMP_TAX,
                    amount=stamp_tax,
                    rate_bps=self.cost_spec.stamp_tax_bps,
                    basis_amount=gross_amount,
                    applies_to_side=OrderSide.SELL,
                    description="applies to sell fills only",
                ),
                CostLineItem(
                    name=CostLineItemName.TRANSFER_FEE,
                    amount=transfer_fee,
                    rate_bps=self.cost_spec.transfer_fee_bps,
                    basis_amount=gross_amount,
                ),
                CostLineItem(
                    name=CostLineItemName.SLIPPAGE,
                    amount=slippage,
                    rate_bps=self.cost_spec.slippage_bps,
                    basis_amount=gross_amount,
                ),
                CostLineItem(
                    name=CostLineItemName.IMPACT,
                    amount=impact,
                    rate_bps=self.cost_spec.impact_bps,
                    basis_amount=gross_amount,
                ),
            ),
        )


def _bps_amount(basis: Decimal, rate_bps: Decimal) -> Decimal:
    return basis * rate_bps / _BPS_DENOMINATOR


def _enum_value(enum_type: type[StrEnum], field_name: str, value: object) -> Any:
    try:
        return enum_type(value)  # type: ignore[call-arg]
    except ValueError as exc:
        raise CostModelError(f"{field_name} must be one of {[item.value for item in enum_type]}") from exc


def _optional_enum_value(enum_type: type[StrEnum], field_name: str, value: object) -> Any | None:
    if value is None:
        return None
    return _enum_value(enum_type, field_name, value)


def _decimal_value(field_name: str, value: object) -> Decimal:
    if isinstance(value, bool):
        raise CostModelError(f"{field_name} must be a decimal value")
    try:
        decimal = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise CostModelError(f"{field_name} must be a decimal value") from exc
    if not decimal.is_finite():
        raise CostModelError(f"{field_name} must be finite")
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
            raise CostModelError(f"{field_name} must be greater than {minimum}")
    elif decimal < minimum:
        raise CostModelError(f"{field_name} cannot be less than {minimum}")
    return decimal


def _decimal_to_string(value: Decimal) -> str:
    return format(value, "f")


def _required_string(field_name: str, value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CostModelError(f"{field_name} is required")
    return value


def _validate_sha256(field_name: str, value: object) -> str:
    value = _required_string(field_name, value)
    if not _SHA256_RE.match(value):
        raise CostModelError(f"{field_name} must be sha256:<64 lowercase hex>")
    return value


def _require_aware_datetime(field_name: str, value: object) -> None:
    if type(value) is not datetime or value.tzinfo is None or value.utcoffset() is None:
        raise CostModelError(f"{field_name} must be timezone-aware")
