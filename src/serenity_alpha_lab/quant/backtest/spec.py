from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from types import MappingProxyType
from typing import Any

from serenity_alpha_lab.datasets.catalog import DatasetCatalogError, DatasetVersionRef


BACKTEST_SPEC_CONTRACT_VERSION = "quant.backtest_spec@1.0.0"
BACKTEST_SPEC_SCHEMA_NAME = "quant.backtest_spec"
BACKTEST_SPEC_SCHEMA_VERSION = "1.0.0"
BACKTEST_SPEC_ENGINE_VERSION = "portfolio_backtest_spec@1.0.0"

_REQUIRED_DATASET_KEYS = frozenset(
    {
        "adjusted_daily_bars",
        "raw_daily_bars",
        "trading_calendar",
        "corporate_actions",
        "instrument_master",
    }
)
_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_SCREEN_DEFINITION_VERSION_RE = re.compile(r"^sdv_[0-9a-f]{32,64}$")
_SCREEN_SNAPSHOT_ID_RE = re.compile(r"^ssn_[0-9a-f]{32,64}$")
_FACTOR_VERSION_RE = re.compile(r"^fdv_[0-9a-f]{32,64}$")
_FORMAL_STRATEGY_KINDS = frozenset(
    {
        "screen_snapshot_rebalance",
        "screen_definition_rebalance",
        "model_prediction_rebalance",
        "external_weight_schedule",
    }
)


class BacktestSpecError(ValueError):
    """Raised when a formal BacktestSpec input violates the contract."""


@dataclass(frozen=True, slots=True)
class BacktestDatasetSpec:
    dataset_versions: Mapping[str, str]
    dataset_hashes: Mapping[str, str]

    def __post_init__(self) -> None:
        versions = _normalize_dataset_versions(self.dataset_versions)
        missing = sorted(_REQUIRED_DATASET_KEYS.difference(versions))
        if missing:
            raise BacktestSpecError(f"dataset_versions missing required keys: {', '.join(missing)}")
        hashes = _normalize_sha256_mapping("dataset_hashes", self.dataset_hashes)
        if set(hashes) != set(versions):
            raise BacktestSpecError("dataset_hashes keys must match dataset_versions keys")
        object.__setattr__(self, "dataset_versions", MappingProxyType(versions))
        object.__setattr__(self, "dataset_hashes", MappingProxyType(hashes))

    def to_record(self) -> dict[str, object]:
        return {
            "dataset_versions": dict(self.dataset_versions),
            "dataset_hashes": dict(self.dataset_hashes),
        }


@dataclass(frozen=True, slots=True)
class BacktestUniverseSpec:
    universe_version_id: str
    universe_name: str
    as_of: date
    membership_policy: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "universe_version_id",
            _validate_dataset_version(self.universe_version_id, field_name="universe_version_id"),
        )
        object.__setattr__(self, "universe_name", _required_string("universe_name", self.universe_name))
        _require_date("as_of", self.as_of)
        object.__setattr__(
            self,
            "membership_policy",
            _required_string("membership_policy", self.membership_policy),
        )

    def to_record(self) -> dict[str, object]:
        return {
            "universe_version_id": self.universe_version_id,
            "universe_name": self.universe_name,
            "as_of": self.as_of.isoformat(),
            "membership_policy": self.membership_policy,
        }


@dataclass(frozen=True, slots=True)
class BacktestStrategySpec:
    strategy_id: str
    strategy_version: str
    strategy_kind: str
    source_commit: str
    code_hash: str
    screen_definition_version_id: str | None = None
    screen_snapshot_id: str | None = None
    factor_version_ids: Sequence[str] = field(default_factory=tuple)
    model_version_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "strategy_id", _required_string("strategy_id", self.strategy_id))
        object.__setattr__(self, "strategy_version", _required_string("strategy_version", self.strategy_version))
        strategy_kind = _required_string("strategy_kind", self.strategy_kind)
        if strategy_kind == "legacy_signal_evaluation":
            raise BacktestSpecError("legacy Signal Evaluation cannot be used as a formal portfolio backtest strategy")
        if strategy_kind not in _FORMAL_STRATEGY_KINDS:
            raise BacktestSpecError(f"strategy_kind must be one of {sorted(_FORMAL_STRATEGY_KINDS)}")
        object.__setattr__(self, "strategy_kind", strategy_kind)
        object.__setattr__(self, "source_commit", _required_string("source_commit", self.source_commit))
        object.__setattr__(self, "code_hash", _validate_sha256("code_hash", self.code_hash))
        object.__setattr__(
            self,
            "screen_definition_version_id",
            _validate_optional_screen_definition_version(self.screen_definition_version_id),
        )
        object.__setattr__(self, "screen_snapshot_id", _validate_optional_screen_snapshot_id(self.screen_snapshot_id))
        factor_version_ids = tuple(_validate_factor_version(value) for value in self.factor_version_ids)
        if len(set(factor_version_ids)) != len(factor_version_ids):
            raise BacktestSpecError("factor_version_ids cannot contain duplicates")
        object.__setattr__(self, "factor_version_ids", factor_version_ids)
        object.__setattr__(self, "model_version_id", _optional_string(self.model_version_id))
        if (
            self.screen_definition_version_id is None
            and self.screen_snapshot_id is None
            and not factor_version_ids
            and self.model_version_id is None
        ):
            raise BacktestSpecError("strategy must bind at least one screen, factor or model version")

    def to_record(self) -> dict[str, object]:
        record: dict[str, object] = {
            "strategy_id": self.strategy_id,
            "strategy_version": self.strategy_version,
            "strategy_kind": self.strategy_kind,
            "source_commit": self.source_commit,
            "code_hash": self.code_hash,
            "factor_version_ids": list(self.factor_version_ids),
        }
        _set_if_present(record, "screen_definition_version_id", self.screen_definition_version_id)
        _set_if_present(record, "screen_snapshot_id", self.screen_snapshot_id)
        _set_if_present(record, "model_version_id", self.model_version_id)
        return record


@dataclass(frozen=True, slots=True)
class BacktestExecutionSpec:
    signal_timing: str
    execution_timing: str
    signal_price_field: str
    execution_price_field: str
    rebalance_calendar: str
    valuation_calendar: str
    rebalance_frequency: str
    settlement_lag_days: int
    lot_size: int
    random_seed: int
    unfilled_order_policy: str = "expire_after_rebalance"
    suspended_security_policy: str = "reject_order"
    limit_up_down_policy: str = "reject_unfillable"

    def __post_init__(self) -> None:
        object.__setattr__(self, "signal_timing", _required_string("signal_timing", self.signal_timing))
        object.__setattr__(self, "execution_timing", _required_string("execution_timing", self.execution_timing))
        object.__setattr__(
            self,
            "signal_price_field",
            _required_string("signal_price_field", self.signal_price_field),
        )
        object.__setattr__(
            self,
            "execution_price_field",
            _required_string("execution_price_field", self.execution_price_field),
        )
        object.__setattr__(
            self,
            "rebalance_calendar",
            _required_string("rebalance_calendar", self.rebalance_calendar),
        )
        object.__setattr__(
            self,
            "valuation_calendar",
            _required_string("valuation_calendar", self.valuation_calendar),
        )
        object.__setattr__(
            self,
            "rebalance_frequency",
            _required_string("rebalance_frequency", self.rebalance_frequency),
        )
        object.__setattr__(
            self,
            "unfilled_order_policy",
            _required_string("unfilled_order_policy", self.unfilled_order_policy),
        )
        object.__setattr__(
            self,
            "suspended_security_policy",
            _required_string("suspended_security_policy", self.suspended_security_policy),
        )
        object.__setattr__(
            self,
            "limit_up_down_policy",
            _required_string("limit_up_down_policy", self.limit_up_down_policy),
        )
        if type(self.settlement_lag_days) is not int or self.settlement_lag_days < 0:
            raise BacktestSpecError("settlement_lag_days must be a non-negative integer")
        if type(self.lot_size) is not int or self.lot_size <= 0:
            raise BacktestSpecError("lot_size must be a positive integer")
        if type(self.random_seed) is not int or self.random_seed < 0:
            raise BacktestSpecError("random_seed must be a non-negative integer")
        if (
            self.signal_timing == "at_close"
            and self.execution_timing == "same_bar_close"
            and self.signal_price_field == "close"
            and self.execution_price_field == "close"
        ):
            raise BacktestSpecError("same bar close signal cannot execute at same bar close")

    def to_record(self) -> dict[str, object]:
        return {
            "signal_timing": self.signal_timing,
            "execution_timing": self.execution_timing,
            "signal_price_field": self.signal_price_field,
            "execution_price_field": self.execution_price_field,
            "rebalance_calendar": self.rebalance_calendar,
            "valuation_calendar": self.valuation_calendar,
            "rebalance_frequency": self.rebalance_frequency,
            "settlement_lag_days": self.settlement_lag_days,
            "lot_size": self.lot_size,
            "random_seed": self.random_seed,
            "unfilled_order_policy": self.unfilled_order_policy,
            "suspended_security_policy": self.suspended_security_policy,
            "limit_up_down_policy": self.limit_up_down_policy,
        }


@dataclass(frozen=True, slots=True)
class BacktestCostSpec:
    commission_bps: Decimal | int | str
    min_commission: Decimal | int | str
    stamp_tax_bps: Decimal | int | str
    transfer_fee_bps: Decimal | int | str
    slippage_bps: Decimal | int | str
    impact_bps: Decimal | int | str
    max_participation_rate: Decimal | int | str

    def __post_init__(self) -> None:
        object.__setattr__(self, "commission_bps", _decimal_min("commission_bps", self.commission_bps, Decimal("0")))
        object.__setattr__(self, "min_commission", _decimal_min("min_commission", self.min_commission, Decimal("0")))
        object.__setattr__(self, "stamp_tax_bps", _decimal_min("stamp_tax_bps", self.stamp_tax_bps, Decimal("0")))
        object.__setattr__(self, "transfer_fee_bps", _decimal_min("transfer_fee_bps", self.transfer_fee_bps, Decimal("0")))
        object.__setattr__(self, "slippage_bps", _decimal_min("slippage_bps", self.slippage_bps, Decimal("0")))
        object.__setattr__(self, "impact_bps", _decimal_min("impact_bps", self.impact_bps, Decimal("0")))
        object.__setattr__(
            self,
            "max_participation_rate",
            _decimal_ratio("max_participation_rate", self.max_participation_rate, allow_zero=False),
        )

    def to_record(self) -> dict[str, object]:
        return {
            "commission_bps": _decimal_to_string(self.commission_bps),
            "min_commission": _decimal_to_string(self.min_commission),
            "stamp_tax_bps": _decimal_to_string(self.stamp_tax_bps),
            "transfer_fee_bps": _decimal_to_string(self.transfer_fee_bps),
            "slippage_bps": _decimal_to_string(self.slippage_bps),
            "impact_bps": _decimal_to_string(self.impact_bps),
            "max_participation_rate": _decimal_to_string(self.max_participation_rate),
        }


@dataclass(frozen=True, slots=True)
class BacktestRiskSpec:
    risk_policy_version: str
    max_weight_per_instrument: Decimal | int | str
    max_weight_per_industry: Decimal | int | str
    max_turnover_per_rebalance: Decimal | int | str
    cash_buffer_pct: Decimal | int | str
    liquidity_floor_amount: Decimal | int | str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "risk_policy_version",
            _required_string("risk_policy_version", self.risk_policy_version),
        )
        object.__setattr__(
            self,
            "max_weight_per_instrument",
            _decimal_ratio("max_weight_per_instrument", self.max_weight_per_instrument),
        )
        object.__setattr__(
            self,
            "max_weight_per_industry",
            _decimal_ratio("max_weight_per_industry", self.max_weight_per_industry),
        )
        object.__setattr__(
            self,
            "max_turnover_per_rebalance",
            _decimal_ratio("max_turnover_per_rebalance", self.max_turnover_per_rebalance),
        )
        object.__setattr__(self, "cash_buffer_pct", _decimal_ratio("cash_buffer_pct", self.cash_buffer_pct))
        object.__setattr__(
            self,
            "liquidity_floor_amount",
            _decimal_min("liquidity_floor_amount", self.liquidity_floor_amount, Decimal("0")),
        )

    def to_record(self) -> dict[str, object]:
        return {
            "risk_policy_version": self.risk_policy_version,
            "max_weight_per_instrument": _decimal_to_string(self.max_weight_per_instrument),
            "max_weight_per_industry": _decimal_to_string(self.max_weight_per_industry),
            "max_turnover_per_rebalance": _decimal_to_string(self.max_turnover_per_rebalance),
            "cash_buffer_pct": _decimal_to_string(self.cash_buffer_pct),
            "liquidity_floor_amount": _decimal_to_string(self.liquidity_floor_amount),
        }


@dataclass(frozen=True, slots=True)
class BacktestSpec:
    spec_id: str
    created_at: datetime
    created_by_run_id: str
    dataset: BacktestDatasetSpec
    universe: BacktestUniverseSpec
    strategy: BacktestStrategySpec
    start_date: date
    end_date: date
    benchmark: str
    currency: str
    initial_capital: Decimal | int | str
    cash_rate_bps: Decimal | int | str
    execution: BacktestExecutionSpec
    costs: BacktestCostSpec
    risk: BacktestRiskSpec
    artifact_output_level: str
    spec_hash: str | None = None
    contract_version: str = BACKTEST_SPEC_CONTRACT_VERSION
    schema_name: str = BACKTEST_SPEC_SCHEMA_NAME
    schema_version: str = BACKTEST_SPEC_SCHEMA_VERSION
    engine_version: str = BACKTEST_SPEC_ENGINE_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "spec_id", _required_string("spec_id", self.spec_id))
        _require_aware_datetime("created_at", self.created_at)
        object.__setattr__(self, "created_by_run_id", _required_string("created_by_run_id", self.created_by_run_id))
        if type(self.dataset) is not BacktestDatasetSpec:
            raise BacktestSpecError("dataset must be a BacktestDatasetSpec")
        if type(self.universe) is not BacktestUniverseSpec:
            raise BacktestSpecError("universe must be a BacktestUniverseSpec")
        if type(self.strategy) is not BacktestStrategySpec:
            raise BacktestSpecError("strategy must be a BacktestStrategySpec")
        _require_date("start_date", self.start_date)
        _require_date("end_date", self.end_date)
        if self.start_date > self.end_date:
            raise BacktestSpecError("start_date cannot be after end_date")
        object.__setattr__(self, "benchmark", _required_string("benchmark", self.benchmark))
        object.__setattr__(self, "currency", _required_string("currency", self.currency))
        object.__setattr__(
            self,
            "initial_capital",
            _decimal_min("initial_capital", self.initial_capital, Decimal("0"), exclusive=True),
        )
        object.__setattr__(self, "cash_rate_bps", _decimal_value("cash_rate_bps", self.cash_rate_bps))
        if type(self.execution) is not BacktestExecutionSpec:
            raise BacktestSpecError("execution must be a BacktestExecutionSpec")
        if type(self.costs) is not BacktestCostSpec:
            raise BacktestSpecError("costs must be a BacktestCostSpec")
        if type(self.risk) is not BacktestRiskSpec:
            raise BacktestSpecError("risk must be a BacktestRiskSpec")
        object.__setattr__(
            self,
            "artifact_output_level",
            _required_string("artifact_output_level", self.artifact_output_level),
        )
        object.__setattr__(self, "contract_version", _required_string("contract_version", self.contract_version))
        object.__setattr__(self, "schema_name", _required_string("schema_name", self.schema_name))
        object.__setattr__(self, "schema_version", _required_string("schema_version", self.schema_version))
        object.__setattr__(self, "engine_version", _required_string("engine_version", self.engine_version))

        derived_hash = _derive_spec_hash(self._hash_payload())
        if self.spec_hash is not None and _validate_sha256("spec_hash", self.spec_hash) != derived_hash:
            raise BacktestSpecError("provided spec_hash does not match canonical BacktestSpec payload")
        object.__setattr__(self, "spec_hash", derived_hash)

    def canonical_json(self) -> str:
        return _canonical_json(self._hash_payload())

    def to_record(self) -> dict[str, object]:
        record = self._hash_payload()
        record.update(
            {
                "spec_hash": self.spec_hash,
                "created_at": self.created_at.isoformat(),
                "created_by_run_id": self.created_by_run_id,
            }
        )
        return record

    def _hash_payload(self) -> dict[str, object]:
        return {
            "contract_version": self.contract_version,
            "schema_name": self.schema_name,
            "schema_version": self.schema_version,
            "engine_version": self.engine_version,
            "spec_id": self.spec_id,
            "dataset": self.dataset.to_record(),
            "universe": self.universe.to_record(),
            "strategy": self.strategy.to_record(),
            "period": {
                "start_date": self.start_date.isoformat(),
                "end_date": self.end_date.isoformat(),
            },
            "portfolio": {
                "benchmark": self.benchmark,
                "currency": self.currency,
                "initial_capital": _decimal_to_string(self.initial_capital),
                "cash_rate_bps": _decimal_to_string(self.cash_rate_bps),
            },
            "execution": self.execution.to_record(),
            "costs": self.costs.to_record(),
            "risk": self.risk.to_record(),
            "artifact_output_level": self.artifact_output_level,
        }


def _normalize_dataset_versions(dataset_versions: Mapping[str, str]) -> dict[str, str]:
    if not isinstance(dataset_versions, Mapping):
        raise BacktestSpecError("dataset_versions must map names to concrete Dataset Version ids")
    if not dataset_versions:
        raise BacktestSpecError("dataset_versions are required")
    normalized = {
        _required_string("dataset name", name): _validate_dataset_version(version, field_name="dataset_version")
        for name, version in dataset_versions.items()
    }
    return dict(sorted(normalized.items()))


def _normalize_sha256_mapping(field_name: str, values: Mapping[str, str]) -> dict[str, str]:
    if not isinstance(values, Mapping):
        raise BacktestSpecError(f"{field_name} must be a mapping")
    if not values:
        raise BacktestSpecError(f"{field_name} is required")
    normalized = {
        _required_string(f"{field_name} key", key): _validate_sha256(field_name, value)
        for key, value in values.items()
    }
    return dict(sorted(normalized.items()))


def _validate_dataset_version(value: object, *, field_name: str) -> str:
    version = _required_string(field_name, value)
    if version.lower() == "latest":
        raise BacktestSpecError("BacktestSpec requires concrete Dataset Version ids; latest is not allowed")
    try:
        DatasetVersionRef.version(version)
    except (DatasetCatalogError, ValueError) as exc:
        raise BacktestSpecError(f"{field_name} must be a concrete Dataset Version id") from exc
    return version


def _validate_optional_screen_definition_version(value: object) -> str | None:
    value = _optional_string(value)
    if value is None:
        return None
    if not _SCREEN_DEFINITION_VERSION_RE.fullmatch(value):
        raise BacktestSpecError("screen_definition_version_id must be an sdv_* version id")
    return value


def _validate_optional_screen_snapshot_id(value: object) -> str | None:
    value = _optional_string(value)
    if value is None:
        return None
    if not _SCREEN_SNAPSHOT_ID_RE.fullmatch(value):
        raise BacktestSpecError("screen_snapshot_id must be an ssn_* snapshot id")
    return value


def _validate_factor_version(value: object) -> str:
    version = _required_string("factor_version_id", value)
    if not _FACTOR_VERSION_RE.fullmatch(version):
        raise BacktestSpecError("factor_version_ids must contain fdv_* version ids")
    return version


def _validate_sha256(field_name: str, value: object) -> str:
    digest = _required_string(field_name, value)
    if not _SHA256_RE.fullmatch(digest):
        raise BacktestSpecError(f"{field_name} must match sha256:<64 lowercase hex chars>")
    return digest


def _decimal_value(field_name: str, value: object) -> Decimal:
    if isinstance(value, bool):
        raise BacktestSpecError(f"{field_name} must be a decimal value")
    try:
        decimal = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise BacktestSpecError(f"{field_name} must be a decimal value") from exc
    if not decimal.is_finite():
        raise BacktestSpecError(f"{field_name} must be finite")
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
            raise BacktestSpecError(f"{field_name} must be greater than {minimum}")
    elif decimal < minimum:
        raise BacktestSpecError(f"{field_name} cannot be less than {minimum}")
    return decimal


def _decimal_ratio(field_name: str, value: object, *, allow_zero: bool = True) -> Decimal:
    decimal = _decimal_value(field_name, value)
    if allow_zero:
        if decimal < 0 or decimal > 1:
            raise BacktestSpecError(f"{field_name} must be between 0 and 1")
    elif decimal <= 0 or decimal > 1:
        raise BacktestSpecError(f"{field_name} must be greater than 0 and no more than 1")
    return decimal


def _decimal_to_string(value: Decimal) -> str:
    return format(value, "f")


def _required_string(field_name: str, value: object) -> str:
    if type(value) is not str or not value.strip():
        raise BacktestSpecError(f"{field_name} is required")
    return value


def _optional_string(value: object) -> str | None:
    if value is None:
        return None
    return _required_string("optional string", value)


def _require_date(field_name: str, value: object) -> None:
    if type(value) is not date:
        raise BacktestSpecError(f"{field_name} must be a date")


def _require_aware_datetime(field_name: str, value: object) -> None:
    if type(value) is not datetime or value.tzinfo is None or value.utcoffset() is None:
        raise BacktestSpecError(f"{field_name} must be a timezone-aware datetime")


def _set_if_present(record: dict[str, object], key: str, value: object | None) -> None:
    if value is not None:
        record[key] = value


def _derive_spec_hash(payload: Mapping[str, object]) -> str:
    return f"sha256:{hashlib.sha256(_canonical_json(payload).encode('utf-8')).hexdigest()}"


def _canonical_json(payload: Mapping[str, object]) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
