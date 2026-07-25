from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation, ROUND_DOWN
from enum import StrEnum
from types import MappingProxyType
from typing import Any

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
from serenity_alpha_lab.quant.backtest.spec import BacktestSpec
from serenity_alpha_lab.quant.screening.snapshot import (
    ScreenSnapshot,
    ScreenSnapshotStatus,
)


REBALANCE_POLICY_CONTRACT_VERSION = "quant.rebalance_policy@1.0.0"
REBALANCE_POLICY_SCHEMA_NAME = "quant.backtest.rebalance_policy"
REBALANCE_POLICY_SCHEMA_VERSION = "1.0.0"
REBALANCE_ORDER_GENERATOR_VERSION = "cn_a_share_rebalance_order_generator@1.0.0"

_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_WEIGHT_QUANT = Decimal("0.0001")


class RebalancePolicyError(ValueError):
    """Raised when target-weight or rebalance order generation violates the contract."""


class WeightingPolicy(StrEnum):
    EQUAL_WEIGHT = "equal_weight"
    SCORE_PROPORTIONAL = "score_proportional"
    EXPLICIT_TARGET_WEIGHT = "explicit_target_weight"


@dataclass(frozen=True, slots=True)
class RebalancePolicy:
    policy_id: str
    policy_version: str
    weighting_policy: WeightingPolicy | str
    min_order_notional: Decimal | int | str
    max_positions: int | None = None
    order_type: OrderType | str = OrderType.MARKET
    time_in_force: TimeInForce | str = TimeInForce.DAY

    def __post_init__(self) -> None:
        object.__setattr__(self, "policy_id", _required_string("policy_id", self.policy_id))
        object.__setattr__(self, "policy_version", _required_string("policy_version", self.policy_version))
        object.__setattr__(
            self,
            "weighting_policy",
            _enum_value(WeightingPolicy, "weighting_policy", self.weighting_policy),
        )
        object.__setattr__(
            self,
            "min_order_notional",
            _decimal_min("min_order_notional", self.min_order_notional, Decimal("0")),
        )
        if self.max_positions is not None and (type(self.max_positions) is not int or self.max_positions <= 0):
            raise RebalancePolicyError("max_positions must be a positive integer")
        object.__setattr__(self, "order_type", _enum_value(OrderType, "order_type", self.order_type))
        object.__setattr__(self, "time_in_force", _enum_value(TimeInForce, "time_in_force", self.time_in_force))

    def to_record(self) -> dict[str, object]:
        record: dict[str, object] = {
            "policy_id": self.policy_id,
            "policy_version": self.policy_version,
            "weighting_policy": self.weighting_policy.value,
            "min_order_notional": _decimal_to_string(self.min_order_notional),
            "order_type": self.order_type.value,
            "time_in_force": self.time_in_force.value,
        }
        _set_if_present(record, "max_positions", self.max_positions)
        return record


@dataclass(frozen=True, slots=True)
class ModelSignal:
    signal_id: str
    instrument_id: InstrumentId
    as_of: date
    model_version_id: str
    score: Decimal | int | str | None = None
    target_weight: Decimal | int | str | None = None
    rank: int | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "signal_id", _required_string("signal_id", self.signal_id))
        if type(self.instrument_id) is not InstrumentId:
            raise RebalancePolicyError("instrument_id must be an InstrumentId")
        _require_date("as_of", self.as_of)
        object.__setattr__(self, "model_version_id", _model_version_id(self.model_version_id))
        object.__setattr__(self, "score", _optional_decimal_min("score", self.score, Decimal("0")))
        object.__setattr__(
            self,
            "target_weight",
            _optional_decimal_ratio("target_weight", self.target_weight),
        )
        if self.rank is not None and (type(self.rank) is not int or self.rank <= 0):
            raise RebalancePolicyError("rank must be a positive integer")

    def to_record(self) -> dict[str, object]:
        record: dict[str, object] = {
            "signal_id": self.signal_id,
            "instrument_id": self.instrument_id.canonical,
            "as_of": self.as_of.isoformat(),
            "model_version_id": self.model_version_id,
        }
        _set_if_present(record, "score", _optional_decimal_to_string(self.score))
        _set_if_present(record, "target_weight", _optional_decimal_to_string(self.target_weight))
        _set_if_present(record, "rank", self.rank)
        return record


@dataclass(frozen=True, slots=True)
class TargetWeight:
    instrument_id: InstrumentId
    target_weight: Decimal | int | str
    source: str
    source_rank: int | None = None
    score: Decimal | int | str | None = None
    reason: str = ""

    def __post_init__(self) -> None:
        if type(self.instrument_id) is not InstrumentId:
            raise RebalancePolicyError("instrument_id must be an InstrumentId")
        object.__setattr__(self, "target_weight", _decimal_ratio("target_weight", self.target_weight))
        object.__setattr__(self, "source", _required_string("source", self.source))
        if self.source_rank is not None and (type(self.source_rank) is not int or self.source_rank <= 0):
            raise RebalancePolicyError("source_rank must be a positive integer")
        object.__setattr__(self, "score", _optional_decimal_min("score", self.score, Decimal("0")))
        object.__setattr__(self, "reason", _optional_text(self.reason))

    def to_record(self) -> dict[str, object]:
        record: dict[str, object] = {
            "instrument_id": self.instrument_id.canonical,
            "target_weight": _decimal_to_string(self.target_weight),
            "source": self.source,
            "reason": self.reason,
        }
        _set_if_present(record, "source_rank", self.source_rank)
        _set_if_present(record, "score", _optional_decimal_to_string(self.score))
        return record


@dataclass(frozen=True, slots=True)
class SkippedRebalanceOrder:
    instrument_id: InstrumentId
    side: OrderSide | str
    target_notional: Decimal | int | str
    current_notional: Decimal | int | str
    delta_notional: Decimal | int | str
    quantity: Decimal | int | str
    notional: Decimal | int | str
    reason: str
    message: str = ""

    def __post_init__(self) -> None:
        if type(self.instrument_id) is not InstrumentId:
            raise RebalancePolicyError("instrument_id must be an InstrumentId")
        object.__setattr__(self, "side", _enum_value(OrderSide, "side", self.side))
        for field_name in ("target_notional", "current_notional", "delta_notional"):
            object.__setattr__(self, field_name, _decimal_value(field_name, getattr(self, field_name)))
        object.__setattr__(self, "quantity", _decimal_min("quantity", self.quantity, Decimal("0")))
        object.__setattr__(self, "notional", _decimal_min("notional", self.notional, Decimal("0")))
        object.__setattr__(self, "reason", _required_string("reason", self.reason))
        object.__setattr__(self, "message", _optional_text(self.message))

    def to_record(self) -> dict[str, object]:
        return {
            "instrument_id": self.instrument_id.canonical,
            "side": self.side.value,
            "target_notional": _decimal_to_string(self.target_notional),
            "current_notional": _decimal_to_string(self.current_notional),
            "delta_notional": _decimal_to_string(self.delta_notional),
            "quantity": _decimal_to_string(self.quantity),
            "notional": _decimal_to_string(self.notional),
            "reason": self.reason,
            "message": self.message,
        }


@dataclass(frozen=True, slots=True)
class RebalancePlan:
    plan_id: str
    spec_id: str
    spec_hash: str
    run_id: str
    stage_id: str
    trade_date: date
    signal_time: datetime
    created_at: datetime
    policy: RebalancePolicy
    target_weights: Sequence[TargetWeight]
    orders: Sequence[Order]
    skipped_orders: Sequence[SkippedRebalanceOrder]
    cash_buffer_amount: Decimal | int | str
    available_buy_cash: Decimal | int | str
    planned_buy_notional: Decimal | int | str
    planned_sell_notional: Decimal | int | str
    residual_cash: Decimal | int | str
    source_snapshot_id: str | None = None
    source_model_version_id: str | None = None
    contract_version: str = REBALANCE_POLICY_CONTRACT_VERSION
    schema_name: str = REBALANCE_POLICY_SCHEMA_NAME
    schema_version: str = REBALANCE_POLICY_SCHEMA_VERSION
    generator_version: str = REBALANCE_ORDER_GENERATOR_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "plan_id", _required_string("plan_id", self.plan_id))
        object.__setattr__(self, "spec_id", _required_string("spec_id", self.spec_id))
        object.__setattr__(self, "spec_hash", _validate_sha256("spec_hash", self.spec_hash))
        object.__setattr__(self, "run_id", _required_string("run_id", self.run_id))
        object.__setattr__(self, "stage_id", _required_string("stage_id", self.stage_id))
        _require_date("trade_date", self.trade_date)
        _require_aware_datetime("signal_time", self.signal_time)
        _require_aware_datetime("created_at", self.created_at)
        if type(self.policy) is not RebalancePolicy:
            raise RebalancePolicyError("policy must be a RebalancePolicy")
        target_weights = tuple(self.target_weights)
        for target in target_weights:
            if type(target) is not TargetWeight:
                raise RebalancePolicyError("target_weights must contain TargetWeight values")
        if len({target.instrument_id.canonical for target in target_weights}) != len(target_weights):
            raise RebalancePolicyError("duplicate target_weights are not allowed")
        object.__setattr__(self, "target_weights", target_weights)
        orders = tuple(self.orders)
        for order in orders:
            if type(order) is not Order:
                raise RebalancePolicyError("orders must contain Order values")
            if order.status is not OrderStatus.CREATED:
                raise RebalancePolicyError("rebalance generator may only emit created orders")
        object.__setattr__(self, "orders", orders)
        skipped = tuple(self.skipped_orders)
        for item in skipped:
            if type(item) is not SkippedRebalanceOrder:
                raise RebalancePolicyError("skipped_orders must contain SkippedRebalanceOrder values")
        object.__setattr__(self, "skipped_orders", skipped)
        for field_name in (
            "cash_buffer_amount",
            "available_buy_cash",
            "planned_buy_notional",
            "planned_sell_notional",
            "residual_cash",
        ):
            object.__setattr__(self, field_name, _decimal_min(field_name, getattr(self, field_name), Decimal("0")))
        object.__setattr__(self, "source_snapshot_id", _optional_string(self.source_snapshot_id))
        object.__setattr__(self, "source_model_version_id", _optional_string(self.source_model_version_id))
        object.__setattr__(self, "contract_version", _required_string("contract_version", self.contract_version))
        object.__setattr__(self, "schema_name", _required_string("schema_name", self.schema_name))
        object.__setattr__(self, "schema_version", _required_string("schema_version", self.schema_version))
        object.__setattr__(self, "generator_version", _required_string("generator_version", self.generator_version))

    @property
    def target_weight_sum(self) -> Decimal:
        return sum((target.target_weight for target in self.target_weights), Decimal("0"))

    def to_record(self) -> dict[str, Any]:
        record: dict[str, Any] = {
            "contract_version": self.contract_version,
            "schema_name": self.schema_name,
            "schema_version": self.schema_version,
            "generator_version": self.generator_version,
            "plan_id": self.plan_id,
            "spec_id": self.spec_id,
            "spec_hash": self.spec_hash,
            "run_id": self.run_id,
            "stage_id": self.stage_id,
            "trade_date": self.trade_date.isoformat(),
            "signal_time": self.signal_time.isoformat(),
            "created_at": self.created_at.isoformat(),
            "policy": self.policy.to_record(),
            "target_weight_sum": _decimal_to_string(self.target_weight_sum),
            "cash_buffer_amount": _decimal_to_string(self.cash_buffer_amount),
            "available_buy_cash": _decimal_to_string(self.available_buy_cash),
            "planned_buy_notional": _decimal_to_string(self.planned_buy_notional),
            "planned_sell_notional": _decimal_to_string(self.planned_sell_notional),
            "residual_cash": _decimal_to_string(self.residual_cash),
            "target_weights": [target.to_record() for target in self.target_weights],
            "orders": [order.to_record() for order in self.orders],
            "skipped_orders": [item.to_record() for item in self.skipped_orders],
        }
        _set_if_present(record, "source_snapshot_id", self.source_snapshot_id)
        _set_if_present(record, "source_model_version_id", self.source_model_version_id)
        return record


@dataclass(frozen=True, slots=True)
class _OrderCandidate:
    instrument_id: InstrumentId
    side: OrderSide
    target_notional: Decimal
    current_notional: Decimal
    delta_notional: Decimal
    quantity: Decimal
    price: Decimal

    @property
    def notional(self) -> Decimal:
        return self.quantity * self.price


class RebalanceOrderGenerator:
    def __init__(self, *, spec: BacktestSpec, policy: RebalancePolicy) -> None:
        if type(spec) is not BacktestSpec:
            raise RebalancePolicyError("spec must be a BacktestSpec")
        if type(policy) is not RebalancePolicy:
            raise RebalancePolicyError("policy must be a RebalancePolicy")
        self.spec = spec
        self.policy = policy

    @property
    def investable_weight(self) -> Decimal:
        return _quantize_weight(Decimal("1") - self.spec.risk.cash_buffer_pct)

    @property
    def max_weight_per_instrument(self) -> Decimal:
        return _quantize_weight(self.spec.risk.max_weight_per_instrument)

    def target_weights_from_screen_snapshot(self, snapshot: ScreenSnapshot) -> tuple[TargetWeight, ...]:
        if type(snapshot) is not ScreenSnapshot:
            raise RebalancePolicyError("snapshot must be a ScreenSnapshot")
        if self.spec.strategy.screen_snapshot_id is None:
            raise RebalancePolicyError("BacktestSpec strategy must bind screen_snapshot_id")
        if snapshot.screen_snapshot_id != self.spec.strategy.screen_snapshot_id:
            raise RebalancePolicyError("screen_snapshot_id must match BacktestSpec strategy")
        passed = tuple(
            sorted(
                (result for result in snapshot.results if result.status is ScreenSnapshotStatus.PASSED),
                key=lambda result: result.rank or 0,
            )
        )
        if not passed:
            raise RebalancePolicyError("screen snapshot must contain passed results")
        if self.policy.max_positions is not None:
            passed = passed[: self.policy.max_positions]

        if self.policy.weighting_policy is WeightingPolicy.EQUAL_WEIGHT:
            raw_weights = [self.investable_weight / Decimal(len(passed)) for _ in passed]
        elif self.policy.weighting_policy is WeightingPolicy.SCORE_PROPORTIONAL:
            scores = [_decimal_min("final_score", result.final_score, Decimal("0"), exclusive=True) for result in passed]
            raw_weights = self._score_weights(scores)
        else:
            raise RebalancePolicyError("screen snapshot weighting requires equal_weight or score_proportional")

        return tuple(
            TargetWeight(
                instrument_id=InstrumentId.parse(result.instrument_id),
                target_weight=self._cap_weight(weight),
                source="screen_snapshot_rebalance",
                source_rank=result.rank,
                score=Decimal(str(result.final_score)) if result.final_score is not None else None,
                reason="screen_snapshot_passed",
            )
            for result, weight in zip(passed, raw_weights, strict=True)
        )

    def target_weights_from_model_signals(self, signals: Sequence[ModelSignal]) -> tuple[TargetWeight, ...]:
        if isinstance(signals, (str, bytes)):
            raise RebalancePolicyError("signals must be a sequence of ModelSignal values")
        signal_values = tuple(signals)
        if not signal_values:
            raise RebalancePolicyError("model signals are required")
        for signal in signal_values:
            if type(signal) is not ModelSignal:
                raise RebalancePolicyError("signals must contain ModelSignal values")
        if len({signal.instrument_id.canonical for signal in signal_values}) != len(signal_values):
            raise RebalancePolicyError("duplicate model signal instruments are not allowed")
        signal_values = tuple(sorted(signal_values, key=lambda item: (item.rank or 10**9, item.instrument_id.canonical)))
        if self.policy.max_positions is not None:
            signal_values = signal_values[: self.policy.max_positions]

        if self.policy.weighting_policy is WeightingPolicy.EXPLICIT_TARGET_WEIGHT:
            raw_weights = []
            for signal in signal_values:
                if signal.target_weight is None:
                    raise RebalancePolicyError("explicit target weights require target_weight")
                raw_weights.append(signal.target_weight)
            if sum(raw_weights, Decimal("0")) > self.investable_weight:
                raise RebalancePolicyError("explicit target weights cannot exceed investable weight after cash buffer")
        elif self.policy.weighting_policy is WeightingPolicy.EQUAL_WEIGHT:
            raw_weights = [self.investable_weight / Decimal(len(signal_values)) for _ in signal_values]
        elif self.policy.weighting_policy is WeightingPolicy.SCORE_PROPORTIONAL:
            scores = []
            for signal in signal_values:
                if signal.score is None:
                    raise RebalancePolicyError("score weighting requires score")
                scores.append(_decimal_min("score", signal.score, Decimal("0"), exclusive=True))
            raw_weights = self._score_weights(scores)
        else:
            raise RebalancePolicyError(f"unsupported weighting policy: {self.policy.weighting_policy}")

        return tuple(
            TargetWeight(
                instrument_id=signal.instrument_id,
                target_weight=self._cap_weight(weight),
                source="model_signal_rebalance",
                source_rank=signal.rank,
                score=signal.score,
                reason=signal.signal_id,
            )
            for signal, weight in zip(signal_values, raw_weights, strict=True)
        )

    def build_plan(
        self,
        *,
        ledger: PortfolioLedger,
        target_weights: Sequence[TargetWeight],
        prices: Mapping[InstrumentId | str, Decimal | int | str],
        trade_date: date,
        signal_time: datetime,
        created_at: datetime,
        source_snapshot_id: str | None = None,
        source_model_version_id: str | None = None,
    ) -> RebalancePlan:
        if type(ledger) is not PortfolioLedger:
            raise RebalancePolicyError("ledger must be a PortfolioLedger")
        if ledger.spec_id != self.spec.spec_id or ledger.spec_hash != self.spec.spec_hash:
            raise RebalancePolicyError("ledger spec_id and spec_hash must match BacktestSpec")
        _require_date("trade_date", trade_date)
        _require_aware_datetime("signal_time", signal_time)
        _require_aware_datetime("created_at", created_at)
        target_values = self._normalize_target_weights(target_weights)
        price_map = _normalize_prices(prices)
        current_instruments = _current_position_instruments(ledger)
        required_prices = set(current_instruments).union(target_values)
        missing_prices = sorted(instrument for instrument in required_prices if instrument not in price_map)
        if missing_prices:
            raise RebalancePolicyError(f"missing rebalance price for: {', '.join(missing_prices)}")

        equity = ledger.equity
        cash_buffer_amount = _money(equity * self.spec.risk.cash_buffer_pct)
        available_buy_cash = max(ledger.cash_balance - ledger.payables - cash_buffer_amount, Decimal("0"))
        candidates: list[_OrderCandidate] = []
        skipped: list[SkippedRebalanceOrder] = []
        for instrument in sorted(required_prices):
            instrument_id = InstrumentId.parse(instrument)
            price = price_map[instrument]
            current_quantity = ledger.position_quantity(instrument)
            current_notional = current_quantity * price
            target_notional = _money(equity * target_values[instrument].target_weight) if instrument in target_values else Decimal("0")
            delta_notional = target_notional - current_notional
            if delta_notional == 0:
                continue
            side = OrderSide.BUY if delta_notional > 0 else OrderSide.SELL
            quantity = _floor_to_lot(abs(delta_notional) / price, self.spec.execution.lot_size)
            notional = quantity * price
            if quantity <= 0:
                skipped.append(
                    _skipped(
                        instrument_id=instrument_id,
                        side=side,
                        target_notional=target_notional,
                        current_notional=current_notional,
                        delta_notional=delta_notional,
                        quantity=quantity,
                        notional=notional,
                        reason="below_trade_lot",
                    )
                )
                continue
            if side is OrderSide.SELL and quantity > current_quantity:
                quantity = _floor_to_lot(current_quantity, self.spec.execution.lot_size)
                notional = quantity * price
            if notional < self.policy.min_order_notional:
                skipped.append(
                    _skipped(
                        instrument_id=instrument_id,
                        side=side,
                        target_notional=target_notional,
                        current_notional=current_notional,
                        delta_notional=delta_notional,
                        quantity=quantity,
                        notional=notional,
                        reason="min_order_notional",
                    )
                )
                continue
            candidates.append(
                _OrderCandidate(
                    instrument_id=instrument_id,
                    side=side,
                    target_notional=target_notional,
                    current_notional=current_notional,
                    delta_notional=delta_notional,
                    quantity=quantity,
                    price=price,
                )
            )

        sell_candidates = sorted((candidate for candidate in candidates if candidate.side is OrderSide.SELL), key=_candidate_sort_key)
        buy_candidates = sorted((candidate for candidate in candidates if candidate.side is OrderSide.BUY), key=_candidate_sort_key)
        remaining_buy_cash = available_buy_cash
        approved: list[_OrderCandidate] = []
        approved.extend(sell_candidates)
        for candidate in buy_candidates:
            quantity = candidate.quantity
            notional = candidate.notional
            if notional > remaining_buy_cash:
                quantity = _floor_to_lot(remaining_buy_cash / candidate.price, self.spec.execution.lot_size)
                notional = quantity * candidate.price
            if quantity <= 0 or notional < self.policy.min_order_notional:
                skipped.append(
                    _skipped(
                        instrument_id=candidate.instrument_id,
                        side=candidate.side,
                        target_notional=candidate.target_notional,
                        current_notional=candidate.current_notional,
                        delta_notional=candidate.delta_notional,
                        quantity=quantity,
                        notional=notional,
                        reason="insufficient_buy_cash",
                    )
                )
                continue
            approved_candidate = _OrderCandidate(
                instrument_id=candidate.instrument_id,
                side=candidate.side,
                target_notional=candidate.target_notional,
                current_notional=candidate.current_notional,
                delta_notional=candidate.delta_notional,
                quantity=quantity,
                price=candidate.price,
            )
            approved.append(approved_candidate)
            remaining_buy_cash -= approved_candidate.notional

        plan_payload = {
            "spec_id": self.spec.spec_id,
            "spec_hash": self.spec.spec_hash,
            "run_id": ledger.run_id,
            "stage_id": ledger.stage_id,
            "trade_date": trade_date.isoformat(),
            "signal_time": signal_time.isoformat(),
            "created_at": created_at.isoformat(),
            "policy": self.policy.to_record(),
            "source_snapshot_id": source_snapshot_id,
            "source_model_version_id": source_model_version_id,
            "target_weights": [target.to_record() for target in target_values.values()],
            "prices": {instrument: _decimal_to_string(price_map[instrument]) for instrument in sorted(price_map)},
            "orders": [_candidate_record(candidate) for candidate in approved],
            "skipped": [item.to_record() for item in sorted(skipped, key=lambda item: (item.side.value, item.instrument_id.canonical, item.reason))],
        }
        plan_id = _stable_id("rbp", plan_payload)
        orders = tuple(
            self._created_order(
                candidate=candidate,
                sequence=index,
                plan_id=plan_id,
                ledger=ledger,
                trade_date=trade_date,
                signal_time=signal_time,
                created_at=created_at,
            )
            for index, candidate in enumerate(approved, start=1)
        )
        planned_buy_notional = sum((candidate.notional for candidate in approved if candidate.side is OrderSide.BUY), Decimal("0"))
        planned_sell_notional = sum((candidate.notional for candidate in approved if candidate.side is OrderSide.SELL), Decimal("0"))
        return RebalancePlan(
            plan_id=plan_id,
            spec_id=self.spec.spec_id,
            spec_hash=self.spec.spec_hash,
            run_id=ledger.run_id,
            stage_id=ledger.stage_id,
            trade_date=trade_date,
            signal_time=signal_time,
            created_at=created_at,
            policy=self.policy,
            target_weights=tuple(target_values.values()),
            orders=orders,
            skipped_orders=tuple(sorted(skipped, key=lambda item: (item.side.value, item.instrument_id.canonical, item.reason))),
            cash_buffer_amount=cash_buffer_amount,
            available_buy_cash=available_buy_cash,
            planned_buy_notional=planned_buy_notional,
            planned_sell_notional=planned_sell_notional,
            residual_cash=remaining_buy_cash,
            source_snapshot_id=source_snapshot_id,
            source_model_version_id=source_model_version_id,
        )

    def _score_weights(self, scores: Sequence[Decimal]) -> list[Decimal]:
        total = sum(scores, Decimal("0"))
        if total <= 0:
            raise RebalancePolicyError("score weighting requires a positive score sum")
        return [self.investable_weight * score / total for score in scores]

    def _cap_weight(self, weight: Decimal) -> Decimal:
        return _quantize_weight(min(weight, self.max_weight_per_instrument))

    def _normalize_target_weights(self, target_weights: Sequence[TargetWeight]) -> Mapping[str, TargetWeight]:
        if isinstance(target_weights, (str, bytes)):
            raise RebalancePolicyError("target_weights must be a sequence of TargetWeight values")
        targets = tuple(target_weights)
        if not targets:
            raise RebalancePolicyError("target_weights are required")
        normalized: dict[str, TargetWeight] = {}
        for target in targets:
            if type(target) is not TargetWeight:
                raise RebalancePolicyError("target_weights must contain TargetWeight values")
            key = target.instrument_id.canonical
            if key in normalized:
                raise RebalancePolicyError(f"duplicate target weight: {key}")
            normalized[key] = target
        total_weight = sum((target.target_weight for target in normalized.values()), Decimal("0"))
        if total_weight > self.investable_weight:
            raise RebalancePolicyError("target weights cannot exceed investable weight after cash buffer")
        return MappingProxyType(normalized)

    def _created_order(
        self,
        *,
        candidate: _OrderCandidate,
        sequence: int,
        plan_id: str,
        ledger: PortfolioLedger,
        trade_date: date,
        signal_time: datetime,
        created_at: datetime,
    ) -> Order:
        short_id = plan_id.removeprefix("rbp_")[:16]
        order_id = f"ord_{short_id}_{sequence:04d}"
        event_id = f"evt_{short_id}_{sequence:04d}_created"
        return Order.create(
            intent=OrderIntent(
                order_id=order_id,
                run_id=ledger.run_id,
                stage_id=ledger.stage_id,
                spec_id=self.spec.spec_id,
                spec_hash=self.spec.spec_hash,
                instrument_id=candidate.instrument_id,
                side=candidate.side,
                order_type=self.policy.order_type,
                target_quantity=candidate.quantity,
                trade_date=trade_date,
                signal_time=signal_time,
                created_at=created_at,
                time_in_force=self.policy.time_in_force,
                source=self.spec.strategy.strategy_kind,
            ),
            event_id=event_id,
            occurred_at=created_at,
        )


def _current_position_instruments(ledger: PortfolioLedger) -> set[str]:
    return {lot.instrument_id.canonical for lot in ledger.position_lots}


def _candidate_sort_key(candidate: _OrderCandidate) -> tuple[str, str]:
    side_rank = "0" if candidate.side is OrderSide.SELL else "1"
    return (side_rank, candidate.instrument_id.canonical)


def _candidate_record(candidate: _OrderCandidate) -> dict[str, object]:
    return {
        "instrument_id": candidate.instrument_id.canonical,
        "side": candidate.side.value,
        "target_notional": _decimal_to_string(candidate.target_notional),
        "current_notional": _decimal_to_string(candidate.current_notional),
        "delta_notional": _decimal_to_string(candidate.delta_notional),
        "quantity": _decimal_to_string(candidate.quantity),
        "price": _decimal_to_string(candidate.price),
        "notional": _decimal_to_string(candidate.notional),
    }


def _skipped(
    *,
    instrument_id: InstrumentId,
    side: OrderSide,
    target_notional: Decimal,
    current_notional: Decimal,
    delta_notional: Decimal,
    quantity: Decimal,
    notional: Decimal,
    reason: str,
) -> SkippedRebalanceOrder:
    return SkippedRebalanceOrder(
        instrument_id=instrument_id,
        side=side,
        target_notional=target_notional,
        current_notional=current_notional,
        delta_notional=delta_notional,
        quantity=quantity,
        notional=notional,
        reason=reason,
        message=reason.replace("_", " "),
    )


def _floor_to_lot(quantity: Decimal, lot_size: int) -> Decimal:
    if lot_size <= 0:
        raise RebalancePolicyError("lot_size must be positive")
    lots = (quantity / Decimal(lot_size)).to_integral_value(rounding=ROUND_DOWN)
    return lots * Decimal(lot_size)


def _money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.0001"))


def _quantize_weight(value: Decimal) -> Decimal:
    return value.quantize(_WEIGHT_QUANT)


def _stable_id(prefix: str, payload: Mapping[str, object]) -> str:
    content = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return f"{prefix}_{hashlib.sha256(content).hexdigest()[:32]}"


def _normalize_prices(prices: Mapping[InstrumentId | str, Decimal | int | str]) -> Mapping[str, Decimal]:
    if not isinstance(prices, Mapping):
        raise RebalancePolicyError("prices must be a mapping")
    normalized = {
        _instrument_key(instrument): _decimal_min("rebalance price", price, Decimal("0"), exclusive=True)
        for instrument, price in prices.items()
    }
    return MappingProxyType(dict(sorted(normalized.items())))


def _instrument_key(instrument: InstrumentId | str) -> str:
    if type(instrument) is InstrumentId:
        return instrument.canonical
    return InstrumentId.parse(_required_string("instrument_id", instrument)).canonical


def _enum_value(enum_type: type[StrEnum], field_name: str, value: object) -> Any:
    try:
        return enum_type(value)  # type: ignore[call-arg]
    except ValueError as exc:
        raise RebalancePolicyError(f"{field_name} must be one of {[item.value for item in enum_type]}") from exc


def _decimal_value(field_name: str, value: object) -> Decimal:
    if isinstance(value, bool):
        raise RebalancePolicyError(f"{field_name} must be a decimal value")
    try:
        decimal = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise RebalancePolicyError(f"{field_name} must be a decimal value") from exc
    if not decimal.is_finite():
        raise RebalancePolicyError(f"{field_name} must be finite")
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
            raise RebalancePolicyError(f"{field_name} must be greater than {minimum}")
    elif decimal < minimum:
        raise RebalancePolicyError(f"{field_name} cannot be less than {minimum}")
    return decimal


def _decimal_ratio(field_name: str, value: object) -> Decimal:
    decimal = _decimal_min(field_name, value, Decimal("0"))
    if decimal > 1:
        raise RebalancePolicyError(f"{field_name} cannot exceed 1")
    return _quantize_weight(decimal)


def _optional_decimal_ratio(field_name: str, value: object) -> Decimal | None:
    if value is None:
        return None
    return _decimal_ratio(field_name, value)


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


def _validate_sha256(field_name: str, value: object) -> str:
    digest = _required_string(field_name, value)
    if not _SHA256_RE.fullmatch(digest):
        raise RebalancePolicyError(f"{field_name} must match sha256:<64 lowercase hex chars>")
    return digest


def _required_string(field_name: str, value: object) -> str:
    if type(value) is not str or not value.strip():
        raise RebalancePolicyError(f"{field_name} is required")
    return value.strip()


def _optional_string(value: object) -> str | None:
    if value is None:
        return None
    return _required_string("optional string", value)


def _model_version_id(value: object) -> str:
    version = _required_string("model_version_id", value)
    if version.lower() == "latest":
        raise RebalancePolicyError("model_version_id must be concrete; latest is not allowed")
    return version


def _optional_text(value: object) -> str:
    if type(value) is not str:
        raise RebalancePolicyError("text field must be a string")
    return value.strip()


def _require_date(field_name: str, value: object) -> None:
    if type(value) is not date:
        raise RebalancePolicyError(f"{field_name} must be a date")


def _require_aware_datetime(field_name: str, value: object) -> None:
    if type(value) is not datetime or value.tzinfo is None or value.utcoffset() is None:
        raise RebalancePolicyError(f"{field_name} must be a timezone-aware datetime")


def _set_if_present(record: dict[str, object], key: str, value: object | None) -> None:
    if value is not None:
        record[key] = value
