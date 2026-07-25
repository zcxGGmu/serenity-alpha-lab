from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from types import MappingProxyType
from typing import Any

from serenity_alpha_lab.domain.instruments import InstrumentId
from serenity_alpha_lab.quant.backtest.spec import BacktestSpec


BACKTEST_BIAS_AUDIT_CONTRACT_VERSION = "quant.backtest_bias_audit@1.0.0"
BACKTEST_BIAS_AUDIT_SCHEMA_NAME = "quant.backtest.bias_audit"
BACKTEST_BIAS_AUDIT_SCHEMA_VERSION = "1.0.0"
BACKTEST_BIAS_AUDITOR_VERSION = "cn_a_share_backtest_bias_auditor@1.0.0"

_DATASET_VERSION_RE = re.compile(r"^dsv_[0-9a-f]{32,64}$")
_RATIO_QUANT = Decimal("0.0001")


class BacktestBiasAuditError(ValueError):
    """Raised when backtest bias audit inputs violate the contract."""


class BacktestBiasAuditStatus(StrEnum):
    PASS = "pass"
    WARN = "warn"
    INVALID = "invalid"


class BiasAuditRuleStatus(StrEnum):
    PASS = "pass"
    WARN = "warn"
    BLOCK = "block"
    NOT_EVALUABLE = "not_evaluable"


@dataclass(frozen=True, slots=True)
class BacktestBiasAuditObservation:
    instrument_id: InstrumentId | str
    trade_date: date
    decision_time: datetime
    data_available_at: datetime
    pit_available_at: datetime | None
    universe_as_of: date
    universe_source: str
    in_strategy_sample: bool
    in_return_sample: bool
    dataset_versions: Mapping[str, str]
    temporal_confidence: str = "known"
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "instrument_id", _instrument(self.instrument_id))
        _require_date("trade_date", self.trade_date)
        _require_aware_datetime("decision_time", self.decision_time)
        _require_aware_datetime("data_available_at", self.data_available_at)
        if self.pit_available_at is not None:
            _require_aware_datetime("pit_available_at", self.pit_available_at)
        _require_date("universe_as_of", self.universe_as_of)
        object.__setattr__(self, "universe_source", _required_string("universe_source", self.universe_source))
        if type(self.in_strategy_sample) is not bool:
            raise BacktestBiasAuditError("in_strategy_sample must be boolean")
        if type(self.in_return_sample) is not bool:
            raise BacktestBiasAuditError("in_return_sample must be boolean")
        object.__setattr__(self, "dataset_versions", _normalize_dataset_versions(self.dataset_versions))
        object.__setattr__(
            self,
            "temporal_confidence",
            _required_string("temporal_confidence", self.temporal_confidence).lower(),
        )
        object.__setattr__(self, "metadata", _normalize_metadata(self.metadata))

    @property
    def sample_key(self) -> tuple[str, str]:
        return (self.instrument_id.canonical, self.trade_date.isoformat())

    def to_record(self) -> dict[str, object]:
        record: dict[str, object] = {
            "instrument_id": self.instrument_id.canonical,
            "trade_date": self.trade_date.isoformat(),
            "decision_time": self.decision_time.isoformat(),
            "data_available_at": self.data_available_at.isoformat(),
            "pit_available_at": self.pit_available_at.isoformat() if self.pit_available_at else None,
            "universe_as_of": self.universe_as_of.isoformat(),
            "universe_source": self.universe_source,
            "in_strategy_sample": self.in_strategy_sample,
            "in_return_sample": self.in_return_sample,
            "dataset_versions": dict(self.dataset_versions),
            "temporal_confidence": self.temporal_confidence,
        }
        if self.metadata:
            record["metadata"] = _thaw_value(self.metadata)
        return record


@dataclass(frozen=True, slots=True)
class CostSensitivityScenario:
    scenario_id: str
    cost_multiplier: Decimal | int | str
    total_return: Decimal | int | str
    is_baseline: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "scenario_id", _required_string("scenario_id", self.scenario_id))
        object.__setattr__(
            self,
            "cost_multiplier",
            _decimal_min("cost_multiplier", self.cost_multiplier, Decimal("0"), exclusive=True),
        )
        object.__setattr__(self, "total_return", _decimal_value("total_return", self.total_return))
        if type(self.is_baseline) is not bool:
            raise BacktestBiasAuditError("is_baseline must be boolean")

    def to_record(self) -> dict[str, object]:
        return {
            "scenario_id": self.scenario_id,
            "cost_multiplier": _decimal_to_string(self.cost_multiplier),
            "total_return": _decimal_to_string(self.total_return),
            "is_baseline": self.is_baseline,
        }


@dataclass(frozen=True, slots=True)
class BacktestBiasAuditPolicy:
    policy_id: str
    policy_version: str
    minimum_sample_overlap_ratio: Decimal | int | str = Decimal("0.8000")
    cost_sensitivity_warning_threshold: Decimal | int | str = Decimal("0.0500")
    cost_sensitivity_block_threshold: Decimal | int | str = Decimal("0.1500")
    sample_overlap_block_threshold: Decimal | int | str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "policy_id", _required_string("policy_id", self.policy_id))
        object.__setattr__(self, "policy_version", _required_string("policy_version", self.policy_version))
        object.__setattr__(
            self,
            "minimum_sample_overlap_ratio",
            _decimal_ratio("minimum_sample_overlap_ratio", self.minimum_sample_overlap_ratio),
        )
        object.__setattr__(
            self,
            "cost_sensitivity_warning_threshold",
            _decimal_min("cost_sensitivity_warning_threshold", self.cost_sensitivity_warning_threshold, Decimal("0")),
        )
        object.__setattr__(
            self,
            "cost_sensitivity_block_threshold",
            _decimal_min("cost_sensitivity_block_threshold", self.cost_sensitivity_block_threshold, Decimal("0")),
        )
        object.__setattr__(
            self,
            "sample_overlap_block_threshold",
            _optional_decimal_ratio("sample_overlap_block_threshold", self.sample_overlap_block_threshold),
        )
        if self.cost_sensitivity_warning_threshold > self.cost_sensitivity_block_threshold:
            raise BacktestBiasAuditError("cost_sensitivity_warning_threshold cannot exceed block threshold")
        if (
            self.sample_overlap_block_threshold is not None
            and self.sample_overlap_block_threshold > self.minimum_sample_overlap_ratio
        ):
            raise BacktestBiasAuditError("sample_overlap_block_threshold cannot exceed minimum_sample_overlap_ratio")

    def to_record(self) -> dict[str, object]:
        record: dict[str, object] = {
            "policy_id": self.policy_id,
            "policy_version": self.policy_version,
            "minimum_sample_overlap_ratio": _decimal_to_string(self.minimum_sample_overlap_ratio),
            "cost_sensitivity_warning_threshold": _decimal_to_string(self.cost_sensitivity_warning_threshold),
            "cost_sensitivity_block_threshold": _decimal_to_string(self.cost_sensitivity_block_threshold),
        }
        if self.sample_overlap_block_threshold is not None:
            record["sample_overlap_block_threshold"] = _decimal_to_string(self.sample_overlap_block_threshold)
        return record


@dataclass(frozen=True, slots=True)
class BiasAuditRuleOutcome:
    rule_id: str
    status: BiasAuditRuleStatus | str
    message: str
    observed_value: Decimal | int | str | None = None
    limit_value: Decimal | int | str | None = None
    affected_count: int = 0
    instruments: Sequence[InstrumentId | str] = ()
    metadata: Mapping[str, object] | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "rule_id", _required_string("rule_id", self.rule_id))
        object.__setattr__(self, "status", _enum_value(BiasAuditRuleStatus, "status", self.status))
        object.__setattr__(self, "message", _required_string("message", self.message))
        object.__setattr__(self, "observed_value", _optional_decimal("observed_value", self.observed_value))
        object.__setattr__(self, "limit_value", _optional_decimal("limit_value", self.limit_value))
        if type(self.affected_count) is not int or self.affected_count < 0:
            raise BacktestBiasAuditError("affected_count must be a non-negative integer")
        instruments = tuple(sorted({_instrument(instrument).canonical for instrument in self.instruments}))
        object.__setattr__(self, "instruments", instruments)
        object.__setattr__(self, "metadata", _normalize_metadata(self.metadata))

    def to_record(self) -> dict[str, object]:
        record: dict[str, object] = {
            "rule_id": self.rule_id,
            "status": self.status.value,
            "message": self.message,
            "affected_count": self.affected_count,
        }
        _set_if_present(record, "observed_value", _optional_decimal_to_string(self.observed_value))
        _set_if_present(record, "limit_value", _optional_decimal_to_string(self.limit_value))
        if self.instruments:
            record["instruments"] = list(self.instruments)
        if self.metadata:
            record["metadata"] = _thaw_value(self.metadata)
        return record


@dataclass(frozen=True, slots=True)
class BacktestBiasAuditReport:
    report_id: str
    spec_id: str
    spec_hash: str
    run_id: str
    stage_id: str
    policy: BacktestBiasAuditPolicy
    status: BacktestBiasAuditStatus | str
    outcomes: Sequence[BiasAuditRuleOutcome]
    eligible_for_ranking: bool
    agent_strong_conclusion_allowed: bool
    contract_version: str = BACKTEST_BIAS_AUDIT_CONTRACT_VERSION
    schema_name: str = BACKTEST_BIAS_AUDIT_SCHEMA_NAME
    schema_version: str = BACKTEST_BIAS_AUDIT_SCHEMA_VERSION
    auditor_version: str = BACKTEST_BIAS_AUDITOR_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "report_id", _required_string("report_id", self.report_id))
        object.__setattr__(self, "spec_id", _required_string("spec_id", self.spec_id))
        object.__setattr__(self, "spec_hash", _required_string("spec_hash", self.spec_hash))
        object.__setattr__(self, "run_id", _required_string("run_id", self.run_id))
        object.__setattr__(self, "stage_id", _required_string("stage_id", self.stage_id))
        if type(self.policy) is not BacktestBiasAuditPolicy:
            raise BacktestBiasAuditError("policy must be a BacktestBiasAuditPolicy")
        object.__setattr__(self, "status", _enum_value(BacktestBiasAuditStatus, "status", self.status))
        outcomes = tuple(self.outcomes)
        for outcome in outcomes:
            if type(outcome) is not BiasAuditRuleOutcome:
                raise BacktestBiasAuditError("outcomes must contain BiasAuditRuleOutcome values")
        if len({outcome.rule_id for outcome in outcomes}) != len(outcomes):
            raise BacktestBiasAuditError("duplicate bias audit rule outcomes are not allowed")
        object.__setattr__(self, "outcomes", outcomes)
        if type(self.eligible_for_ranking) is not bool:
            raise BacktestBiasAuditError("eligible_for_ranking must be boolean")
        if type(self.agent_strong_conclusion_allowed) is not bool:
            raise BacktestBiasAuditError("agent_strong_conclusion_allowed must be boolean")
        if self.status is BacktestBiasAuditStatus.INVALID:
            if self.eligible_for_ranking or self.agent_strong_conclusion_allowed:
                raise BacktestBiasAuditError("invalid bias audit reports cannot be promoted or agent-endorsed")
        object.__setattr__(self, "contract_version", _required_string("contract_version", self.contract_version))
        object.__setattr__(self, "schema_name", _required_string("schema_name", self.schema_name))
        object.__setattr__(self, "schema_version", _required_string("schema_version", self.schema_version))
        object.__setattr__(self, "auditor_version", _required_string("auditor_version", self.auditor_version))

    @property
    def hard_failure_rule_ids(self) -> tuple[str, ...]:
        return tuple(sorted(outcome.rule_id for outcome in self.outcomes if outcome.status is BiasAuditRuleStatus.BLOCK))

    @property
    def warning_rule_ids(self) -> tuple[str, ...]:
        return tuple(sorted(outcome.rule_id for outcome in self.outcomes if outcome.status is BiasAuditRuleStatus.WARN))

    @property
    def not_evaluable_rule_ids(self) -> tuple[str, ...]:
        return tuple(
            sorted(outcome.rule_id for outcome in self.outcomes if outcome.status is BiasAuditRuleStatus.NOT_EVALUABLE)
        )

    def rule_by_id(self, rule_id: str) -> BiasAuditRuleOutcome:
        normalized = _required_string("rule_id", rule_id)
        for outcome in self.outcomes:
            if outcome.rule_id == normalized:
                return outcome
        raise BacktestBiasAuditError(f"bias audit rule outcome not found: {normalized}")

    def rule_status(self, rule_id: str) -> BiasAuditRuleStatus:
        return self.rule_by_id(rule_id).status

    def to_record(self) -> dict[str, object]:
        return {
            "contract_version": self.contract_version,
            "schema_name": self.schema_name,
            "schema_version": self.schema_version,
            "auditor_version": self.auditor_version,
            "report_id": self.report_id,
            "spec_id": self.spec_id,
            "spec_hash": self.spec_hash,
            "run_id": self.run_id,
            "stage_id": self.stage_id,
            "policy": self.policy.to_record(),
            "status": self.status.value,
            "eligible_for_ranking": self.eligible_for_ranking,
            "agent_strong_conclusion_allowed": self.agent_strong_conclusion_allowed,
            "hard_failure_rule_ids": list(self.hard_failure_rule_ids),
            "warning_rule_ids": list(self.warning_rule_ids),
            "not_evaluable_rule_ids": list(self.not_evaluable_rule_ids),
            "outcomes": [outcome.to_record() for outcome in self.outcomes],
        }


class BacktestBiasAuditor:
    def __init__(self, *, spec: BacktestSpec, policy: BacktestBiasAuditPolicy) -> None:
        if type(spec) is not BacktestSpec:
            raise BacktestBiasAuditError("spec must be a BacktestSpec")
        if type(policy) is not BacktestBiasAuditPolicy:
            raise BacktestBiasAuditError("policy must be a BacktestBiasAuditPolicy")
        self.spec = spec
        self.policy = policy

    def evaluate(
        self,
        *,
        run_id: str,
        stage_id: str,
        observations: Sequence[BacktestBiasAuditObservation],
        cost_scenarios: Sequence[CostSensitivityScenario],
    ) -> BacktestBiasAuditReport:
        run_id = _required_string("run_id", run_id)
        stage_id = _required_string("stage_id", stage_id)
        normalized_observations = _normalize_observations(observations)
        normalized_cost_scenarios = _normalize_cost_scenarios(cost_scenarios)
        self._validate_observation_dataset_versions(normalized_observations)

        outcomes = (
            self._lookahead_bias(normalized_observations),
            self._survivorship_bias(normalized_observations),
            self._pit_data_availability(normalized_observations),
            self._sample_overlap(normalized_observations),
            self._cost_sensitivity(normalized_cost_scenarios),
        )
        status = _overall_status(outcomes)
        promotable = status is not BacktestBiasAuditStatus.INVALID
        report_payload = {
            "spec_id": self.spec.spec_id,
            "spec_hash": self.spec.spec_hash,
            "run_id": run_id,
            "stage_id": stage_id,
            "policy": self.policy.to_record(),
            "status": status.value,
            "outcomes": [outcome.to_record() for outcome in outcomes],
        }
        return BacktestBiasAuditReport(
            report_id=_stable_id("audit", report_payload),
            spec_id=self.spec.spec_id,
            spec_hash=self.spec.spec_hash,
            run_id=run_id,
            stage_id=stage_id,
            policy=self.policy,
            status=status,
            outcomes=outcomes,
            eligible_for_ranking=promotable,
            agent_strong_conclusion_allowed=promotable,
        )

    def _validate_observation_dataset_versions(self, observations: Sequence[BacktestBiasAuditObservation]) -> None:
        expected = dict(self.spec.dataset.dataset_versions)
        for observation in observations:
            if dict(observation.dataset_versions) != expected:
                raise BacktestBiasAuditError("observation dataset version binding must match BacktestSpec")

    def _lookahead_bias(self, observations: Sequence[BacktestBiasAuditObservation]) -> BiasAuditRuleOutcome:
        offenders = tuple(observation for observation in observations if observation.data_available_at > observation.decision_time)
        if offenders:
            return BiasAuditRuleOutcome(
                rule_id="lookahead_bias",
                status=BiasAuditRuleStatus.BLOCK,
                message="records used data that was unavailable at decision_time",
                affected_count=len(offenders),
                instruments=tuple(observation.instrument_id for observation in offenders),
                metadata={"sample_keys": [list(observation.sample_key) for observation in offenders]},
            )
        return BiasAuditRuleOutcome(
            rule_id="lookahead_bias",
            status=BiasAuditRuleStatus.PASS,
            message="all data availability timestamps are at or before decision_time",
            affected_count=0,
        )

    def _survivorship_bias(self, observations: Sequence[BacktestBiasAuditObservation]) -> BiasAuditRuleOutcome:
        offenders = tuple(
            observation
            for observation in observations
            if observation.universe_source != "historical_as_of" or observation.universe_as_of > observation.trade_date
        )
        if offenders:
            return BiasAuditRuleOutcome(
                rule_id="survivorship_bias",
                status=BiasAuditRuleStatus.BLOCK,
                message="universe membership was not sourced from historical as-of records",
                affected_count=len(offenders),
                instruments=tuple(observation.instrument_id for observation in offenders),
                metadata={
                    "universe_sources": sorted({observation.universe_source for observation in offenders}),
                    "sample_keys": [list(observation.sample_key) for observation in offenders],
                },
            )
        return BiasAuditRuleOutcome(
            rule_id="survivorship_bias",
            status=BiasAuditRuleStatus.PASS,
            message="universe membership uses historical as-of records",
            affected_count=0,
        )

    def _pit_data_availability(self, observations: Sequence[BacktestBiasAuditObservation]) -> BiasAuditRuleOutcome:
        offenders = tuple(
            observation
            for observation in observations
            if observation.pit_available_at is None
            or observation.pit_available_at > observation.decision_time
            or observation.temporal_confidence != "known"
        )
        if offenders:
            return BiasAuditRuleOutcome(
                rule_id="pit_data_availability",
                status=BiasAuditRuleStatus.BLOCK,
                message="PIT records were unavailable, late or temporally uncertain at decision_time",
                affected_count=len(offenders),
                instruments=tuple(observation.instrument_id for observation in offenders),
                metadata={
                    "temporal_confidence": sorted({observation.temporal_confidence for observation in offenders}),
                    "sample_keys": [list(observation.sample_key) for observation in offenders],
                },
            )
        return BiasAuditRuleOutcome(
            rule_id="pit_data_availability",
            status=BiasAuditRuleStatus.PASS,
            message="PIT data was available and temporally known at decision_time",
            affected_count=0,
        )

    def _sample_overlap(self, observations: Sequence[BacktestBiasAuditObservation]) -> BiasAuditRuleOutcome:
        strategy_sample = {observation.sample_key for observation in observations if observation.in_strategy_sample}
        return_sample = {observation.sample_key for observation in observations if observation.in_return_sample}
        union_sample = strategy_sample | return_sample
        if not union_sample:
            return BiasAuditRuleOutcome(
                rule_id="sample_overlap",
                status=BiasAuditRuleStatus.NOT_EVALUABLE,
                message="sample overlap cannot be evaluated without strategy or return samples",
            )
        overlap_ratio = _quantize_ratio(Decimal(len(strategy_sample & return_sample)) / Decimal(len(union_sample)))
        metadata = {
            "strategy_sample_count": len(strategy_sample),
            "return_sample_count": len(return_sample),
            "overlap_count": len(strategy_sample & return_sample),
            "union_count": len(union_sample),
        }
        if (
            self.policy.sample_overlap_block_threshold is not None
            and overlap_ratio < self.policy.sample_overlap_block_threshold
        ):
            return BiasAuditRuleOutcome(
                rule_id="sample_overlap",
                status=BiasAuditRuleStatus.BLOCK,
                message="strategy and return sample overlap is below hard threshold",
                observed_value=overlap_ratio,
                limit_value=self.policy.sample_overlap_block_threshold,
                affected_count=len(union_sample),
                metadata=metadata,
            )
        if overlap_ratio < self.policy.minimum_sample_overlap_ratio:
            return BiasAuditRuleOutcome(
                rule_id="sample_overlap",
                status=BiasAuditRuleStatus.WARN,
                message="strategy and return sample overlap is below policy minimum",
                observed_value=overlap_ratio,
                limit_value=self.policy.minimum_sample_overlap_ratio,
                affected_count=len(union_sample),
                metadata=metadata,
            )
        return BiasAuditRuleOutcome(
            rule_id="sample_overlap",
            status=BiasAuditRuleStatus.PASS,
            message="strategy and return samples satisfy overlap policy",
            observed_value=overlap_ratio,
            limit_value=self.policy.minimum_sample_overlap_ratio,
            affected_count=len(union_sample),
            metadata=metadata,
        )

    def _cost_sensitivity(self, cost_scenarios: Sequence[CostSensitivityScenario]) -> BiasAuditRuleOutcome:
        baselines = tuple(scenario for scenario in cost_scenarios if scenario.is_baseline)
        if len(baselines) != 1:
            raise BacktestBiasAuditError("cost sensitivity audit requires a single baseline scenario")
        comparisons = tuple(scenario for scenario in cost_scenarios if not scenario.is_baseline)
        if not comparisons:
            return BiasAuditRuleOutcome(
                rule_id="cost_sensitivity",
                status=BiasAuditRuleStatus.NOT_EVALUABLE,
                message="cost sensitivity cannot be evaluated without non-baseline scenarios",
            )
        baseline = baselines[0]
        worst = min(comparisons, key=lambda scenario: (scenario.total_return, scenario.scenario_id))
        degradation = max(baseline.total_return - worst.total_return, Decimal("0"))
        degradation = _quantize_ratio(degradation)
        metadata = {
            "baseline_scenario_id": baseline.scenario_id,
            "worst_scenario_id": worst.scenario_id,
            "scenario_count": len(cost_scenarios),
        }
        if degradation > self.policy.cost_sensitivity_block_threshold:
            return BiasAuditRuleOutcome(
                rule_id="cost_sensitivity",
                status=BiasAuditRuleStatus.BLOCK,
                message="cost sensitivity degradation exceeds hard threshold",
                observed_value=degradation,
                limit_value=self.policy.cost_sensitivity_block_threshold,
                affected_count=len(comparisons),
                metadata=metadata,
            )
        if degradation > self.policy.cost_sensitivity_warning_threshold:
            return BiasAuditRuleOutcome(
                rule_id="cost_sensitivity",
                status=BiasAuditRuleStatus.WARN,
                message="cost sensitivity degradation exceeds warning threshold",
                observed_value=degradation,
                limit_value=self.policy.cost_sensitivity_warning_threshold,
                affected_count=len(comparisons),
                metadata=metadata,
            )
        return BiasAuditRuleOutcome(
            rule_id="cost_sensitivity",
            status=BiasAuditRuleStatus.PASS,
            message="cost sensitivity remains within policy thresholds",
            observed_value=degradation,
            limit_value=self.policy.cost_sensitivity_warning_threshold,
            affected_count=len(comparisons),
            metadata=metadata,
        )


def _overall_status(outcomes: Sequence[BiasAuditRuleOutcome]) -> BacktestBiasAuditStatus:
    if any(outcome.status in {BiasAuditRuleStatus.BLOCK, BiasAuditRuleStatus.NOT_EVALUABLE} for outcome in outcomes):
        return BacktestBiasAuditStatus.INVALID
    if any(outcome.status is BiasAuditRuleStatus.WARN for outcome in outcomes):
        return BacktestBiasAuditStatus.WARN
    return BacktestBiasAuditStatus.PASS


def _normalize_observations(observations: Sequence[BacktestBiasAuditObservation]) -> tuple[BacktestBiasAuditObservation, ...]:
    normalized = tuple(observations)
    if not normalized:
        raise BacktestBiasAuditError("observations are required")
    for observation in normalized:
        if type(observation) is not BacktestBiasAuditObservation:
            raise BacktestBiasAuditError("observations must contain BacktestBiasAuditObservation values")
    return tuple(sorted(normalized, key=lambda observation: observation.to_record()["instrument_id"] + observation.trade_date.isoformat()))


def _normalize_cost_scenarios(cost_scenarios: Sequence[CostSensitivityScenario]) -> tuple[CostSensitivityScenario, ...]:
    normalized = tuple(cost_scenarios)
    if not normalized:
        raise BacktestBiasAuditError("cost_scenarios are required")
    for scenario in normalized:
        if type(scenario) is not CostSensitivityScenario:
            raise BacktestBiasAuditError("cost_scenarios must contain CostSensitivityScenario values")
    scenario_ids = [scenario.scenario_id for scenario in normalized]
    if len(set(scenario_ids)) != len(scenario_ids):
        raise BacktestBiasAuditError("cost_scenarios cannot contain duplicate scenario_id values")
    return tuple(sorted(normalized, key=lambda scenario: scenario.scenario_id))


def _normalize_dataset_versions(dataset_versions: Mapping[str, str]) -> Mapping[str, str]:
    if not isinstance(dataset_versions, Mapping) or not dataset_versions:
        raise BacktestBiasAuditError("dataset_versions must be a non-empty mapping")
    normalized: dict[str, str] = {}
    for key, value in dataset_versions.items():
        dataset_key = _required_string("dataset version key", key)
        version = _required_string("dataset version", value)
        if version.lower() == "latest" or not _DATASET_VERSION_RE.fullmatch(version):
            raise BacktestBiasAuditError("dataset_versions must contain concrete dsv_* values")
        normalized[dataset_key] = version
    return MappingProxyType(dict(sorted(normalized.items())))


def _normalize_metadata(metadata: Mapping[str, object] | None) -> Mapping[str, object]:
    if metadata is None:
        return MappingProxyType({})
    if not isinstance(metadata, Mapping):
        raise BacktestBiasAuditError("metadata must be a mapping")
    return MappingProxyType({str(key): _freeze_value(value) for key, value in sorted(metadata.items(), key=lambda item: str(item[0]))})


def _freeze_value(value: object) -> object:
    if isinstance(value, Mapping):
        return MappingProxyType({str(key): _freeze_value(nested) for key, nested in sorted(value.items(), key=lambda item: str(item[0]))})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_value(item) for item in value)
    return value


def _thaw_value(value: object) -> object:
    if isinstance(value, Mapping):
        return {key: _thaw_value(nested) for key, nested in value.items()}
    if isinstance(value, tuple):
        return [_thaw_value(item) for item in value]
    return value


def _stable_id(prefix: str, payload: Mapping[str, object]) -> str:
    content = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return f"{prefix}_{hashlib.sha256(content).hexdigest()[:32]}"


def _instrument(instrument: InstrumentId | str) -> InstrumentId:
    if type(instrument) is InstrumentId:
        return instrument
    return InstrumentId.parse(_required_string("instrument_id", instrument))


def _enum_value(enum_type: type[StrEnum], field_name: str, value: object) -> Any:
    try:
        return enum_type(value)  # type: ignore[call-arg]
    except ValueError as exc:
        raise BacktestBiasAuditError(f"{field_name} must be one of {[item.value for item in enum_type]}") from exc


def _decimal_value(field_name: str, value: object) -> Decimal:
    if isinstance(value, bool):
        raise BacktestBiasAuditError(f"{field_name} must be a decimal value")
    try:
        decimal = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise BacktestBiasAuditError(f"{field_name} must be a decimal value") from exc
    if not decimal.is_finite():
        raise BacktestBiasAuditError(f"{field_name} must be finite")
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
            raise BacktestBiasAuditError(f"{field_name} must be greater than {minimum}")
    elif decimal < minimum:
        raise BacktestBiasAuditError(f"{field_name} cannot be less than {minimum}")
    return decimal


def _decimal_ratio(field_name: str, value: object) -> Decimal:
    decimal = _decimal_value(field_name, value)
    if decimal < 0 or decimal > 1:
        raise BacktestBiasAuditError(f"{field_name} must be between 0 and 1")
    return decimal


def _optional_decimal(field_name: str, value: object) -> Decimal | None:
    if value is None:
        return None
    return _decimal_value(field_name, value)


def _optional_decimal_ratio(field_name: str, value: object) -> Decimal | None:
    if value is None:
        return None
    return _decimal_ratio(field_name, value)


def _quantize_ratio(value: Decimal) -> Decimal:
    return value.quantize(_RATIO_QUANT)


def _decimal_to_string(value: Decimal) -> str:
    return format(value, "f")


def _optional_decimal_to_string(value: Decimal | None) -> str | None:
    return None if value is None else _decimal_to_string(value)


def _required_string(field_name: str, value: object) -> str:
    if type(value) is not str or not value.strip():
        raise BacktestBiasAuditError(f"{field_name} is required")
    return value


def _require_date(field_name: str, value: object) -> None:
    if type(value) is not date:
        raise BacktestBiasAuditError(f"{field_name} must be a date")


def _require_aware_datetime(field_name: str, value: object) -> None:
    if type(value) is not datetime or value.tzinfo is None or value.utcoffset() is None:
        raise BacktestBiasAuditError(f"{field_name} must be a timezone-aware datetime")


def _set_if_present(record: dict[str, object], key: str, value: object | None) -> None:
    if value is not None:
        record[key] = value

