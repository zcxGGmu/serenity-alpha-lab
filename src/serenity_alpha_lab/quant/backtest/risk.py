from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from types import MappingProxyType
from typing import Any

from serenity_alpha_lab.domain.instruments import InstrumentId
from serenity_alpha_lab.quant.backtest.ledger import PortfolioLedger
from serenity_alpha_lab.quant.backtest.rebalance import RebalancePlan
from serenity_alpha_lab.quant.backtest.spec import BacktestSpec


RISK_POLICY_CONTRACT_VERSION = "quant.risk_policy@1.0.0"
RISK_POLICY_SCHEMA_NAME = "quant.backtest.risk_policy"
RISK_POLICY_SCHEMA_VERSION = "1.0.0"
RISK_POLICY_EVALUATOR_VERSION = "cn_a_share_deterministic_risk_policy@1.0.0"

_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_RATIO_QUANT = Decimal("0.0001")


class RiskPolicyError(ValueError):
    """Raised when deterministic risk policy inputs violate the contract."""


class RiskDecisionStatus(StrEnum):
    PASS = "pass"
    WARN = "warn"
    BLOCK = "block"


class RiskRuleStatus(StrEnum):
    PASS = "pass"
    WARN = "warn"
    BLOCK = "block"
    NOT_EVALUABLE = "not_evaluable"


@dataclass(frozen=True, slots=True)
class DeterministicRiskPolicy:
    policy_id: str
    policy_version: str
    style_exposure_warning_limits: Mapping[str, Decimal | int | str] = field(default_factory=dict)
    style_exposure_block_limits: Mapping[str, Decimal | int | str] = field(default_factory=dict)
    max_drawdown_pct: Decimal | int | str = Decimal("0.20")
    warn_drawdown_pct: Decimal | int | str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "policy_id", _required_string("policy_id", self.policy_id))
        object.__setattr__(self, "policy_version", _required_string("policy_version", self.policy_version))
        object.__setattr__(
            self,
            "style_exposure_warning_limits",
            _normalize_decimal_mapping("style_exposure_warning_limits", self.style_exposure_warning_limits),
        )
        object.__setattr__(
            self,
            "style_exposure_block_limits",
            _normalize_decimal_mapping("style_exposure_block_limits", self.style_exposure_block_limits),
        )
        object.__setattr__(self, "max_drawdown_pct", _decimal_ratio("max_drawdown_pct", self.max_drawdown_pct))
        object.__setattr__(
            self,
            "warn_drawdown_pct",
            _optional_decimal_ratio("warn_drawdown_pct", self.warn_drawdown_pct),
        )
        if self.warn_drawdown_pct is not None and self.warn_drawdown_pct > self.max_drawdown_pct:
            raise RiskPolicyError("warn_drawdown_pct cannot exceed max_drawdown_pct")

    def to_record(self) -> dict[str, object]:
        record: dict[str, object] = {
            "policy_id": self.policy_id,
            "policy_version": self.policy_version,
            "style_exposure_warning_limits": _decimal_mapping_to_record(self.style_exposure_warning_limits),
            "style_exposure_block_limits": _decimal_mapping_to_record(self.style_exposure_block_limits),
            "max_drawdown_pct": _decimal_to_string(self.max_drawdown_pct),
        }
        _set_if_present(record, "warn_drawdown_pct", _optional_decimal_to_string(self.warn_drawdown_pct))
        return record


@dataclass(frozen=True, slots=True)
class InstrumentRiskProfile:
    instrument_id: InstrumentId
    industry: str
    average_daily_amount: Decimal | int | str
    style_exposures: Mapping[str, Decimal | int | str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if type(self.instrument_id) is not InstrumentId:
            raise RiskPolicyError("instrument_id must be an InstrumentId")
        object.__setattr__(self, "industry", _required_string("industry", self.industry))
        object.__setattr__(
            self,
            "average_daily_amount",
            _decimal_min("average_daily_amount", self.average_daily_amount, Decimal("0")),
        )
        object.__setattr__(
            self,
            "style_exposures",
            _normalize_decimal_mapping("style_exposures", self.style_exposures, allow_negative=True),
        )

    def to_record(self) -> dict[str, object]:
        return {
            "instrument_id": self.instrument_id.canonical,
            "industry": self.industry,
            "average_daily_amount": _decimal_to_string(self.average_daily_amount),
            "style_exposures": _decimal_mapping_to_record(self.style_exposures),
        }


@dataclass(frozen=True, slots=True)
class RiskRuleOutcome:
    rule_id: str
    status: RiskRuleStatus | str
    message: str
    observed_value: Decimal | int | str | None = None
    limit_value: Decimal | int | str | None = None
    instrument_id: InstrumentId | None = None
    group_key: str | None = None
    metadata: Mapping[str, object] | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "rule_id", _required_string("rule_id", self.rule_id))
        object.__setattr__(self, "status", _enum_value(RiskRuleStatus, "status", self.status))
        object.__setattr__(self, "message", _required_string("message", self.message))
        object.__setattr__(self, "observed_value", _optional_decimal("observed_value", self.observed_value))
        object.__setattr__(self, "limit_value", _optional_decimal("limit_value", self.limit_value))
        if self.instrument_id is not None and type(self.instrument_id) is not InstrumentId:
            raise RiskPolicyError("instrument_id must be an InstrumentId")
        object.__setattr__(self, "group_key", _optional_string(self.group_key))
        object.__setattr__(self, "metadata", _normalize_metadata(self.metadata))

    def to_record(self) -> dict[str, object]:
        record: dict[str, object] = {
            "rule_id": self.rule_id,
            "status": self.status.value,
            "message": self.message,
        }
        _set_if_present(record, "observed_value", _optional_decimal_to_string(self.observed_value))
        _set_if_present(record, "limit_value", _optional_decimal_to_string(self.limit_value))
        _set_if_present(record, "instrument_id", self.instrument_id.canonical if self.instrument_id else None)
        _set_if_present(record, "group_key", self.group_key)
        if self.metadata:
            record["metadata"] = dict(self.metadata)
        return record


@dataclass(frozen=True, slots=True)
class RiskPolicyResult:
    result_id: str
    spec_id: str
    spec_hash: str
    run_id: str
    stage_id: str
    policy: DeterministicRiskPolicy
    status: RiskDecisionStatus | str
    outcomes: Sequence[RiskRuleOutcome]
    agent_override_allowed: bool = False
    contract_version: str = RISK_POLICY_CONTRACT_VERSION
    schema_name: str = RISK_POLICY_SCHEMA_NAME
    schema_version: str = RISK_POLICY_SCHEMA_VERSION
    evaluator_version: str = RISK_POLICY_EVALUATOR_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "result_id", _required_string("result_id", self.result_id))
        object.__setattr__(self, "spec_id", _required_string("spec_id", self.spec_id))
        object.__setattr__(self, "spec_hash", _validate_sha256("spec_hash", self.spec_hash))
        object.__setattr__(self, "run_id", _required_string("run_id", self.run_id))
        object.__setattr__(self, "stage_id", _required_string("stage_id", self.stage_id))
        if type(self.policy) is not DeterministicRiskPolicy:
            raise RiskPolicyError("policy must be a DeterministicRiskPolicy")
        object.__setattr__(self, "status", _enum_value(RiskDecisionStatus, "status", self.status))
        outcomes = tuple(self.outcomes)
        for outcome in outcomes:
            if type(outcome) is not RiskRuleOutcome:
                raise RiskPolicyError("outcomes must contain RiskRuleOutcome values")
        if len({outcome.rule_id for outcome in outcomes}) != len(outcomes):
            raise RiskPolicyError("duplicate risk rule outcomes are not allowed")
        object.__setattr__(self, "outcomes", outcomes)
        if self.agent_override_allowed is not False:
            raise RiskPolicyError("RiskPolicy block/warn results cannot be marked agent-overridable")
        object.__setattr__(self, "contract_version", _required_string("contract_version", self.contract_version))
        object.__setattr__(self, "schema_name", _required_string("schema_name", self.schema_name))
        object.__setattr__(self, "schema_version", _required_string("schema_version", self.schema_version))
        object.__setattr__(self, "evaluator_version", _required_string("evaluator_version", self.evaluator_version))

    @property
    def blocking_rule_ids(self) -> tuple[str, ...]:
        return tuple(outcome.rule_id for outcome in self.outcomes if outcome.status is RiskRuleStatus.BLOCK)

    @property
    def warning_rule_ids(self) -> tuple[str, ...]:
        return tuple(outcome.rule_id for outcome in self.outcomes if outcome.status is RiskRuleStatus.WARN)

    @property
    def not_evaluable_rule_ids(self) -> tuple[str, ...]:
        return tuple(sorted(outcome.rule_id for outcome in self.outcomes if outcome.status is RiskRuleStatus.NOT_EVALUABLE))

    def rule_by_id(self, rule_id: str) -> RiskRuleOutcome:
        normalized = _required_string("rule_id", rule_id)
        for outcome in self.outcomes:
            if outcome.rule_id == normalized:
                return outcome
        raise RiskPolicyError(f"risk rule outcome not found: {normalized}")

    def rule_status(self, rule_id: str) -> RiskRuleStatus:
        return self.rule_by_id(rule_id).status

    def to_record(self) -> dict[str, object]:
        return {
            "contract_version": self.contract_version,
            "schema_name": self.schema_name,
            "schema_version": self.schema_version,
            "evaluator_version": self.evaluator_version,
            "result_id": self.result_id,
            "spec_id": self.spec_id,
            "spec_hash": self.spec_hash,
            "run_id": self.run_id,
            "stage_id": self.stage_id,
            "policy": self.policy.to_record(),
            "status": self.status.value,
            "agent_override_allowed": self.agent_override_allowed,
            "blocking_rule_ids": list(self.blocking_rule_ids),
            "warning_rule_ids": list(self.warning_rule_ids),
            "not_evaluable_rule_ids": list(self.not_evaluable_rule_ids),
            "outcomes": [outcome.to_record() for outcome in self.outcomes],
        }


class RiskPolicyEvaluator:
    def __init__(self, *, spec: BacktestSpec, policy: DeterministicRiskPolicy) -> None:
        if type(spec) is not BacktestSpec:
            raise RiskPolicyError("spec must be a BacktestSpec")
        if type(policy) is not DeterministicRiskPolicy:
            raise RiskPolicyError("policy must be a DeterministicRiskPolicy")
        self.spec = spec
        self.policy = policy

    def evaluate(
        self,
        *,
        ledger: PortfolioLedger,
        rebalance_plan: RebalancePlan | None,
        profiles: Mapping[InstrumentId | str, InstrumentRiskProfile],
        high_water_mark_equity: Decimal | int | str | None,
    ) -> RiskPolicyResult:
        if type(ledger) is not PortfolioLedger:
            raise RiskPolicyError("ledger must be a PortfolioLedger")
        if ledger.spec_id != self.spec.spec_id or ledger.spec_hash != self.spec.spec_hash:
            raise RiskPolicyError("ledger spec_id and spec_hash must match BacktestSpec")
        if rebalance_plan is not None:
            if type(rebalance_plan) is not RebalancePlan:
                raise RiskPolicyError("rebalance_plan must be a RebalancePlan")
            if rebalance_plan.spec_id != self.spec.spec_id or rebalance_plan.spec_hash != self.spec.spec_hash:
                raise RiskPolicyError("rebalance_plan spec_id and spec_hash must match BacktestSpec")
            if rebalance_plan.run_id != ledger.run_id or rebalance_plan.stage_id != ledger.stage_id:
                raise RiskPolicyError("rebalance_plan run_id and stage_id must match ledger")

        normalized_profiles = _normalize_profiles(profiles)
        target_weights = self._target_weights(ledger=ledger, rebalance_plan=rebalance_plan)
        outcomes: list[RiskRuleOutcome] = []
        outcomes.append(self._risk_profile_available(target_weights, normalized_profiles))
        outcomes.append(self._max_weight_per_instrument(target_weights))
        outcomes.append(self._max_weight_per_industry(target_weights, normalized_profiles))
        outcomes.extend(self._style_exposure_outcomes(target_weights, normalized_profiles))
        outcomes.append(self._liquidity_floor(target_weights, normalized_profiles))
        outcomes.append(self._max_turnover(ledger=ledger, rebalance_plan=rebalance_plan))
        outcomes.append(self._max_drawdown(ledger=ledger, high_water_mark_equity=high_water_mark_equity))

        status = _overall_status(outcomes)
        result_payload = {
            "spec_id": self.spec.spec_id,
            "spec_hash": self.spec.spec_hash,
            "run_id": ledger.run_id,
            "stage_id": ledger.stage_id,
            "policy": self.policy.to_record(),
            "status": status.value,
            "outcomes": [outcome.to_record() for outcome in outcomes],
        }
        return RiskPolicyResult(
            result_id=_stable_id("risk", result_payload),
            spec_id=self.spec.spec_id,
            spec_hash=self.spec.spec_hash,
            run_id=ledger.run_id,
            stage_id=ledger.stage_id,
            policy=self.policy,
            status=status,
            outcomes=tuple(outcomes),
            agent_override_allowed=False,
        )

    def _target_weights(self, *, ledger: PortfolioLedger, rebalance_plan: RebalancePlan | None) -> Mapping[str, Decimal]:
        if rebalance_plan is not None:
            return MappingProxyType(
                dict(
                    sorted(
                        (
                            (target.instrument_id.canonical, _decimal_ratio("target_weight", target.target_weight))
                            for target in rebalance_plan.target_weights
                        ),
                        key=lambda item: item[0],
                    )
                )
            )
        equity = ledger.equity
        if equity <= 0:
            raise RiskPolicyError("ledger equity must be positive for risk evaluation")
        weights: dict[str, Decimal] = {}
        for lot in ledger.position_lots:
            price = ledger.valuation_prices.get(lot.instrument_id.canonical)
            if price is None:
                raise RiskPolicyError(f"missing valuation price for open position: {lot.instrument_id.canonical}")
            weights[lot.instrument_id.canonical] = weights.get(lot.instrument_id.canonical, Decimal("0")) + (lot.quantity * price / equity)
        return MappingProxyType(dict(sorted((instrument, _quantize_ratio(weight)) for instrument, weight in weights.items())))

    def _risk_profile_available(
        self,
        target_weights: Mapping[str, Decimal],
        profiles: Mapping[str, InstrumentRiskProfile],
    ) -> RiskRuleOutcome:
        missing = sorted(instrument for instrument in target_weights if instrument not in profiles)
        if missing:
            return RiskRuleOutcome(
                rule_id="risk_profile_available",
                status=RiskRuleStatus.NOT_EVALUABLE,
                message="risk profile missing for target instruments",
                metadata={"missing_instruments": missing},
            )
        return RiskRuleOutcome(
            rule_id="risk_profile_available",
            status=RiskRuleStatus.PASS,
            message="risk profiles available for all target instruments",
        )

    def _max_weight_per_instrument(self, target_weights: Mapping[str, Decimal]) -> RiskRuleOutcome:
        limit = self.spec.risk.max_weight_per_instrument
        breach = max(target_weights.items(), key=lambda item: (item[1], item[0])) if target_weights else None
        if breach is not None and breach[1] > limit:
            return RiskRuleOutcome(
                rule_id="max_weight_per_instrument",
                status=RiskRuleStatus.BLOCK,
                message="instrument target weight exceeds BacktestRiskSpec max_weight_per_instrument",
                observed_value=_quantize_ratio(breach[1]),
                limit_value=limit,
                instrument_id=InstrumentId.parse(breach[0]),
            )
        observed = max(target_weights.values(), default=Decimal("0"))
        return RiskRuleOutcome(
            rule_id="max_weight_per_instrument",
            status=RiskRuleStatus.PASS,
            message="instrument target weights are within limit",
            observed_value=_quantize_ratio(observed),
            limit_value=limit,
        )

    def _max_weight_per_industry(
        self,
        target_weights: Mapping[str, Decimal],
        profiles: Mapping[str, InstrumentRiskProfile],
    ) -> RiskRuleOutcome:
        if any(instrument not in profiles for instrument in target_weights):
            return RiskRuleOutcome(
                rule_id="max_weight_per_industry",
                status=RiskRuleStatus.NOT_EVALUABLE,
                message="industry exposure cannot be evaluated without all risk profiles",
            )
        exposures: dict[str, Decimal] = {}
        for instrument, weight in target_weights.items():
            profile = profiles[instrument]
            exposures[profile.industry] = exposures.get(profile.industry, Decimal("0")) + weight
        breach = max(exposures.items(), key=lambda item: (item[1], item[0])) if exposures else None
        limit = self.spec.risk.max_weight_per_industry
        if breach is not None and breach[1] > limit:
            return RiskRuleOutcome(
                rule_id="max_weight_per_industry",
                status=RiskRuleStatus.BLOCK,
                message="industry target weight exceeds BacktestRiskSpec max_weight_per_industry",
                observed_value=_quantize_ratio(breach[1]),
                limit_value=limit,
                group_key=breach[0],
            )
        return RiskRuleOutcome(
            rule_id="max_weight_per_industry",
            status=RiskRuleStatus.PASS,
            message="industry target weights are within limit",
            observed_value=_quantize_ratio(breach[1] if breach else Decimal("0")),
            limit_value=limit,
        )

    def _style_exposure_outcomes(
        self,
        target_weights: Mapping[str, Decimal],
        profiles: Mapping[str, InstrumentRiskProfile],
    ) -> tuple[RiskRuleOutcome, ...]:
        style_names = sorted(
            set(self.policy.style_exposure_warning_limits)
            | set(self.policy.style_exposure_block_limits)
            | {style for profile in profiles.values() for style in profile.style_exposures}
        )
        outcomes: list[RiskRuleOutcome] = []
        for style_name in style_names:
            rule_id = f"style_exposure:{style_name}"
            if any(instrument not in profiles for instrument in target_weights):
                outcomes.append(
                    RiskRuleOutcome(
                        rule_id=rule_id,
                        status=RiskRuleStatus.NOT_EVALUABLE,
                        message="style exposure cannot be evaluated without all risk profiles",
                    )
                )
                continue
            exposure = sum(
                (
                    target_weights[instrument] * profiles[instrument].style_exposures.get(style_name, Decimal("0"))
                    for instrument in target_weights
                ),
                Decimal("0"),
            )
            absolute_exposure = abs(exposure)
            block_limit = self.policy.style_exposure_block_limits.get(style_name)
            warn_limit = self.policy.style_exposure_warning_limits.get(style_name)
            if block_limit is not None and absolute_exposure > block_limit:
                outcomes.append(
                    RiskRuleOutcome(
                        rule_id=rule_id,
                        status=RiskRuleStatus.BLOCK,
                        message="style exposure exceeds block limit",
                        observed_value=_quantize_ratio(absolute_exposure),
                        limit_value=block_limit,
                        group_key=style_name,
                    )
                )
            elif warn_limit is not None and absolute_exposure > warn_limit:
                outcomes.append(
                    RiskRuleOutcome(
                        rule_id=rule_id,
                        status=RiskRuleStatus.WARN,
                        message="style exposure exceeds warning limit",
                        observed_value=_quantize_ratio(absolute_exposure),
                        limit_value=warn_limit,
                        group_key=style_name,
                    )
                )
            elif warn_limit is not None or block_limit is not None:
                outcomes.append(
                    RiskRuleOutcome(
                        rule_id=rule_id,
                        status=RiskRuleStatus.PASS,
                        message="style exposure is within configured limits",
                        observed_value=_quantize_ratio(absolute_exposure),
                        limit_value=block_limit if block_limit is not None else warn_limit,
                        group_key=style_name,
                    )
                )
        return tuple(outcomes)

    def _liquidity_floor(
        self,
        target_weights: Mapping[str, Decimal],
        profiles: Mapping[str, InstrumentRiskProfile],
    ) -> RiskRuleOutcome:
        if any(instrument not in profiles for instrument in target_weights):
            return RiskRuleOutcome(
                rule_id="liquidity_floor",
                status=RiskRuleStatus.NOT_EVALUABLE,
                message="liquidity cannot be evaluated without all risk profiles",
            )
        limit = self.spec.risk.liquidity_floor_amount
        breach = min(
            ((instrument, profiles[instrument].average_daily_amount) for instrument in target_weights),
            key=lambda item: (item[1], item[0]),
            default=None,
        )
        if breach is not None and breach[1] < limit:
            return RiskRuleOutcome(
                rule_id="liquidity_floor",
                status=RiskRuleStatus.BLOCK,
                message="instrument average daily amount is below BacktestRiskSpec liquidity floor",
                observed_value=breach[1],
                limit_value=limit,
                instrument_id=InstrumentId.parse(breach[0]),
            )
        return RiskRuleOutcome(
            rule_id="liquidity_floor",
            status=RiskRuleStatus.PASS,
            message="all target instruments satisfy liquidity floor",
            observed_value=breach[1] if breach else None,
            limit_value=limit,
        )

    def _max_turnover(
        self,
        *,
        ledger: PortfolioLedger,
        rebalance_plan: RebalancePlan | None,
    ) -> RiskRuleOutcome:
        if rebalance_plan is None:
            return RiskRuleOutcome(
                rule_id="max_turnover_per_rebalance",
                status=RiskRuleStatus.NOT_EVALUABLE,
                message="turnover cannot be evaluated without a rebalance plan",
            )
        equity = ledger.equity
        if equity <= 0:
            return RiskRuleOutcome(
                rule_id="max_turnover_per_rebalance",
                status=RiskRuleStatus.NOT_EVALUABLE,
                message="turnover cannot be evaluated with non-positive ledger equity",
            )
        turnover = _quantize_ratio((rebalance_plan.planned_buy_notional + rebalance_plan.planned_sell_notional) / equity)
        limit = self.spec.risk.max_turnover_per_rebalance
        if turnover > limit:
            return RiskRuleOutcome(
                rule_id="max_turnover_per_rebalance",
                status=RiskRuleStatus.BLOCK,
                message="planned turnover exceeds BacktestRiskSpec max_turnover_per_rebalance",
                observed_value=turnover,
                limit_value=limit,
            )
        return RiskRuleOutcome(
            rule_id="max_turnover_per_rebalance",
            status=RiskRuleStatus.PASS,
            message="planned turnover is within limit",
            observed_value=turnover,
            limit_value=limit,
        )

    def _max_drawdown(
        self,
        *,
        ledger: PortfolioLedger,
        high_water_mark_equity: Decimal | int | str | None,
    ) -> RiskRuleOutcome:
        if high_water_mark_equity is None:
            return RiskRuleOutcome(
                rule_id="max_drawdown",
                status=RiskRuleStatus.NOT_EVALUABLE,
                message="drawdown cannot be evaluated without high_water_mark_equity",
            )
        high_water_mark = _decimal_min("high_water_mark_equity", high_water_mark_equity, Decimal("0"), exclusive=True)
        equity = ledger.equity
        drawdown = Decimal("0") if equity >= high_water_mark else _quantize_ratio((high_water_mark - equity) / high_water_mark)
        if drawdown > self.policy.max_drawdown_pct:
            return RiskRuleOutcome(
                rule_id="max_drawdown",
                status=RiskRuleStatus.BLOCK,
                message="portfolio drawdown exceeds deterministic risk policy max_drawdown_pct",
                observed_value=drawdown,
                limit_value=self.policy.max_drawdown_pct,
            )
        if self.policy.warn_drawdown_pct is not None and drawdown > self.policy.warn_drawdown_pct:
            return RiskRuleOutcome(
                rule_id="max_drawdown",
                status=RiskRuleStatus.WARN,
                message="portfolio drawdown exceeds deterministic risk policy warning threshold",
                observed_value=drawdown,
                limit_value=self.policy.warn_drawdown_pct,
            )
        return RiskRuleOutcome(
            rule_id="max_drawdown",
            status=RiskRuleStatus.PASS,
            message="portfolio drawdown is within limit",
            observed_value=drawdown,
            limit_value=self.policy.max_drawdown_pct,
        )


def _overall_status(outcomes: Sequence[RiskRuleOutcome]) -> RiskDecisionStatus:
    if any(outcome.status in {RiskRuleStatus.BLOCK, RiskRuleStatus.NOT_EVALUABLE} for outcome in outcomes):
        return RiskDecisionStatus.BLOCK
    if any(outcome.status is RiskRuleStatus.WARN for outcome in outcomes):
        return RiskDecisionStatus.WARN
    return RiskDecisionStatus.PASS


def _normalize_profiles(
    profiles: Mapping[InstrumentId | str, InstrumentRiskProfile],
) -> Mapping[str, InstrumentRiskProfile]:
    if not isinstance(profiles, Mapping):
        raise RiskPolicyError("profiles must be a mapping")
    normalized: dict[str, InstrumentRiskProfile] = {}
    for key, profile in profiles.items():
        if type(profile) is not InstrumentRiskProfile:
            raise RiskPolicyError("profiles must contain InstrumentRiskProfile values")
        profile_key = _instrument_key(key)
        if profile_key != profile.instrument_id.canonical:
            raise RiskPolicyError("profile mapping key must match profile instrument_id")
        normalized[profile_key] = profile
    return MappingProxyType(dict(sorted(normalized.items())))


def _instrument_key(instrument: InstrumentId | str) -> str:
    if type(instrument) is InstrumentId:
        return instrument.canonical
    return InstrumentId.parse(_required_string("instrument_id", instrument)).canonical


def _stable_id(prefix: str, payload: Mapping[str, object]) -> str:
    content = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return f"{prefix}_{hashlib.sha256(content).hexdigest()[:32]}"


def _enum_value(enum_type: type[StrEnum], field_name: str, value: object) -> Any:
    try:
        return enum_type(value)  # type: ignore[call-arg]
    except ValueError as exc:
        raise RiskPolicyError(f"{field_name} must be one of {[item.value for item in enum_type]}") from exc


def _decimal_value(field_name: str, value: object) -> Decimal:
    if isinstance(value, bool):
        raise RiskPolicyError(f"{field_name} must be a decimal value")
    try:
        decimal = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise RiskPolicyError(f"{field_name} must be a decimal value") from exc
    if not decimal.is_finite():
        raise RiskPolicyError(f"{field_name} must be finite")
    return decimal


def _decimal_min(field_name: str, value: object, minimum: Decimal, *, exclusive: bool = False) -> Decimal:
    decimal = _decimal_value(field_name, value)
    if exclusive:
        if decimal <= minimum:
            raise RiskPolicyError(f"{field_name} must be greater than {minimum}")
    elif decimal < minimum:
        raise RiskPolicyError(f"{field_name} cannot be less than {minimum}")
    return decimal


def _decimal_ratio(field_name: str, value: object) -> Decimal:
    decimal = _decimal_min(field_name, value, Decimal("0"))
    if decimal > 1:
        raise RiskPolicyError(f"{field_name} cannot exceed 1")
    return decimal


def _optional_decimal(field_name: str, value: object | None) -> Decimal | None:
    if value is None:
        return None
    return _decimal_value(field_name, value)


def _optional_decimal_ratio(field_name: str, value: object | None) -> Decimal | None:
    if value is None:
        return None
    return _decimal_ratio(field_name, value)


def _normalize_decimal_mapping(
    field_name: str,
    values: Mapping[str, Decimal | int | str],
    *,
    allow_negative: bool = False,
) -> Mapping[str, Decimal]:
    if not isinstance(values, Mapping):
        raise RiskPolicyError(f"{field_name} must be a mapping")
    normalized: dict[str, Decimal] = {}
    for key, value in values.items():
        normalized_key = _required_string(f"{field_name} key", key)
        normalized_value = _decimal_value(f"{field_name}.{normalized_key}", value)
        if not allow_negative and normalized_value < 0:
            raise RiskPolicyError(f"{field_name}.{normalized_key} cannot be less than 0")
        normalized[normalized_key] = normalized_value
    return MappingProxyType(dict(sorted(normalized.items())))


def _normalize_metadata(metadata: Mapping[str, object] | None) -> Mapping[str, object]:
    if metadata is None:
        return MappingProxyType({})
    if not isinstance(metadata, Mapping):
        raise RiskPolicyError("metadata must be a mapping")
    return MappingProxyType({str(key): value for key, value in sorted(metadata.items(), key=lambda item: str(item[0]))})


def _required_string(field_name: str, value: object) -> str:
    if type(value) is not str or not value.strip():
        raise RiskPolicyError(f"{field_name} is required")
    return value.strip()


def _optional_string(value: object | None) -> str | None:
    if value is None:
        return None
    return _required_string("value", value)


def _validate_sha256(field_name: str, value: str) -> str:
    value = _required_string(field_name, value)
    if not _SHA256_RE.match(value):
        raise RiskPolicyError(f"{field_name} must be sha256:<64 lowercase hex>")
    return value


def _quantize_ratio(value: Decimal) -> Decimal:
    return value.quantize(_RATIO_QUANT)


def _decimal_to_string(value: Decimal) -> str:
    return format(value, "f")


def _optional_decimal_to_string(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return _decimal_to_string(value)


def _decimal_mapping_to_record(values: Mapping[str, Decimal]) -> dict[str, str]:
    return {key: _decimal_to_string(values[key]) for key in sorted(values)}


def _set_if_present(record: dict[str, object], key: str, value: object | None) -> None:
    if value is not None:
        record[key] = value
