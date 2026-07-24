from __future__ import annotations

import json
import math
import re
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import StrEnum
from types import MappingProxyType
from typing import Any

import numpy as np

from serenity_alpha_lab.datasets.catalog import DatasetCatalogError, DatasetVersionRef
from serenity_alpha_lab.domain.artifacts import ArtifactManifest, ArtifactRetentionTier, ArtifactStore
from serenity_alpha_lab.domain.instruments import InstrumentId
from serenity_alpha_lab.quant.factors.definitions import FactorDirection


FACTOR_EVALUATION_CONTRACT_VERSION = "1.0.0"
FACTOR_EVALUATION_SCHEMA_NAME = "quant.factor_evaluation"
FACTOR_EVALUATION_SCHEMA_VERSION = "1.0.0"
FACTOR_EVALUATION_ENGINE_VERSION = "factor_evaluation@1.0.0"
FACTOR_EVALUATION_METRIC_SET_VERSION = "factor_evaluation_metrics@1.0.0"

_FACTOR_VERSION_ID_RE = re.compile(r"^fdv_[0-9a-f]{32,64}$")


class FactorEvaluationError(ValueError):
    """Raised when Factor Evaluation inputs, parameters or guards are invalid."""


class FactorCorrelationMethod(StrEnum):
    PEARSON = "pearson"
    SPEARMAN = "spearman"


@dataclass(frozen=True, slots=True)
class FutureReturnWindow:
    horizon: int
    return_field: str
    version: str
    unit: str = "trading_day"
    annualization_periods: int = 252

    def __post_init__(self) -> None:
        if type(self.horizon) is not int or self.horizon <= 0:
            raise FactorEvaluationError("future-return horizon must be a positive integer")
        object.__setattr__(self, "return_field", _required_string("return_field", self.return_field))
        object.__setattr__(self, "version", _required_string("future return window version", self.version))
        object.__setattr__(self, "unit", _required_string("future return unit", self.unit))
        if type(self.annualization_periods) is not int or self.annualization_periods <= 0:
            raise FactorEvaluationError("annualization_periods must be a positive integer")

    def to_record(self) -> dict[str, object]:
        return {
            "horizon": self.horizon,
            "unit": self.unit,
            "return_field": self.return_field,
            "version": self.version,
            "annualization_periods": self.annualization_periods,
        }


@dataclass(frozen=True, slots=True)
class FactorEvaluationSpec:
    run_id: str
    stage_id: str
    factor_definition_id: str
    factor_version_id: str
    dataset_versions: Mapping[str, str]
    future_return_window: FutureReturnWindow
    factor_direction: FactorDirection | str
    quantile_count: int = 5
    minimum_ic_observations: int = 3
    correlation_method: FactorCorrelationMethod | str = FactorCorrelationMethod.SPEARMAN
    exposure_fields: Sequence[str] = ()
    formal: bool = True
    metric_set_version: str = FACTOR_EVALUATION_METRIC_SET_VERSION
    contract_version: str = FACTOR_EVALUATION_CONTRACT_VERSION
    schema_name: str = FACTOR_EVALUATION_SCHEMA_NAME
    schema_version: str = FACTOR_EVALUATION_SCHEMA_VERSION
    engine_version: str = FACTOR_EVALUATION_ENGINE_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "run_id", _required_string("run_id", self.run_id))
        object.__setattr__(self, "stage_id", _required_string("stage_id", self.stage_id))
        object.__setattr__(
            self,
            "factor_definition_id",
            _required_string("factor_definition_id", self.factor_definition_id),
        )
        object.__setattr__(self, "factor_version_id", _validate_factor_version_id(self.factor_version_id))
        if not self.dataset_versions:
            raise FactorEvaluationError("dataset_versions are required")
        versions: dict[str, str] = {}
        for name, version in self.dataset_versions.items():
            versions[_required_string("dataset name", name)] = _validate_dataset_version(version)
        object.__setattr__(self, "dataset_versions", MappingProxyType(versions))
        if type(self.future_return_window) is not FutureReturnWindow:
            raise FactorEvaluationError("future_return_window must be a FutureReturnWindow")
        object.__setattr__(self, "factor_direction", FactorDirection(self.factor_direction))
        if type(self.quantile_count) is not int or self.quantile_count < 2:
            raise FactorEvaluationError("quantile_count must be at least 2")
        if type(self.minimum_ic_observations) is not int or self.minimum_ic_observations < 2:
            raise FactorEvaluationError("minimum_ic_observations must be at least 2")
        object.__setattr__(self, "correlation_method", FactorCorrelationMethod(self.correlation_method))
        exposure_fields = tuple(_required_string("exposure field", field_name) for field_name in self.exposure_fields)
        if len(set(exposure_fields)) != len(exposure_fields):
            raise FactorEvaluationError("exposure_fields cannot contain duplicates")
        object.__setattr__(self, "exposure_fields", exposure_fields)
        if type(self.formal) is not bool:
            raise FactorEvaluationError("formal must be boolean")
        object.__setattr__(self, "metric_set_version", _required_string("metric_set_version", self.metric_set_version))
        object.__setattr__(self, "contract_version", _required_string("contract_version", self.contract_version))
        object.__setattr__(self, "schema_name", _required_string("schema_name", self.schema_name))
        object.__setattr__(self, "schema_version", _required_string("schema_version", self.schema_version))
        object.__setattr__(self, "engine_version", _required_string("engine_version", self.engine_version))

    def to_record(self) -> dict[str, object]:
        return {
            "contract_version": self.contract_version,
            "schema_name": self.schema_name,
            "schema_version": self.schema_version,
            "engine_version": self.engine_version,
            "metric_set_version": self.metric_set_version,
            "run_id": self.run_id,
            "stage_id": self.stage_id,
            "factor_definition_id": self.factor_definition_id,
            "factor_version_id": self.factor_version_id,
            "dataset_versions": dict(self.dataset_versions),
            "future_return_window": self.future_return_window.to_record(),
            "factor_direction": self.factor_direction.value,
            "quantile_count": self.quantile_count,
            "minimum_ic_observations": self.minimum_ic_observations,
            "correlation_method": self.correlation_method.value,
            "exposure_fields": list(self.exposure_fields),
            "formal": self.formal,
        }


@dataclass(frozen=True, slots=True)
class FactorEvaluationObservation:
    instrument_id: str | InstrumentId
    trade_date: date
    decision_time: datetime
    factor_available_at: datetime
    forward_return_available_at: datetime
    factor_value: float | None
    forward_return: float | None
    in_universe: bool = True
    exposures: Mapping[str, Any] = field(default_factory=dict)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        instrument = (
            self.instrument_id
            if isinstance(self.instrument_id, InstrumentId)
            else InstrumentId.parse(str(self.instrument_id))
        )
        object.__setattr__(self, "instrument_id", instrument.canonical)
        if type(self.trade_date) is datetime:
            object.__setattr__(self, "trade_date", self.trade_date.date())
        elif type(self.trade_date) is not date:
            raise FactorEvaluationError("trade_date must be a date")
        _require_aware_datetime("decision_time", self.decision_time)
        _require_aware_datetime("factor_available_at", self.factor_available_at)
        _require_aware_datetime("forward_return_available_at", self.forward_return_available_at)
        object.__setattr__(self, "factor_value", _optional_finite_float("factor_value", self.factor_value))
        object.__setattr__(self, "forward_return", _optional_finite_float("forward_return", self.forward_return))
        if type(self.in_universe) is not bool:
            raise FactorEvaluationError("in_universe must be boolean")
        object.__setattr__(self, "exposures", _freeze_mapping(self.exposures))
        object.__setattr__(self, "metadata", _freeze_mapping(self.metadata))

    def to_record(self) -> dict[str, object]:
        return {
            "instrument_id": self.instrument_id,
            "trade_date": self.trade_date.isoformat(),
            "decision_time": self.decision_time.isoformat(),
            "factor_available_at": self.factor_available_at.isoformat(),
            "forward_return_available_at": self.forward_return_available_at.isoformat(),
            "factor_value": self.factor_value,
            "forward_return": self.forward_return,
            "in_universe": self.in_universe,
            "exposures": _thaw_value(self.exposures),
            "metadata": _thaw_value(self.metadata),
        }


@dataclass(frozen=True, slots=True)
class FactorEvaluationWarning:
    code: str
    message: str
    affected_count: int = 0
    trade_date: date | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "code", _required_string("warning code", self.code))
        object.__setattr__(self, "message", _required_string("warning message", self.message))
        if type(self.affected_count) is not int or self.affected_count < 0:
            raise FactorEvaluationError("warning affected_count cannot be negative")
        if self.trade_date is not None and type(self.trade_date) is not date:
            raise FactorEvaluationError("warning trade_date must be a date")

    def to_record(self) -> dict[str, object]:
        record: dict[str, object] = {
            "code": self.code,
            "message": self.message,
            "affected_count": self.affected_count,
        }
        if self.trade_date is not None:
            record["trade_date"] = self.trade_date.isoformat()
        return record


@dataclass(frozen=True, slots=True)
class FactorCoverageSummary:
    total_universe_count: int
    factor_observation_count: int
    return_observation_count: int
    overlap_observation_count: int
    factor_only_count: int
    return_only_count: int

    @property
    def coverage_ratio(self) -> float:
        return _safe_ratio(self.factor_observation_count, self.total_universe_count)

    @property
    def sample_overlap_ratio(self) -> float:
        return _safe_ratio(self.overlap_observation_count, self.total_universe_count)

    def to_record(self) -> dict[str, object]:
        return {
            "total_universe_count": self.total_universe_count,
            "factor_observation_count": self.factor_observation_count,
            "return_observation_count": self.return_observation_count,
            "overlap_observation_count": self.overlap_observation_count,
            "factor_only_count": self.factor_only_count,
            "return_only_count": self.return_only_count,
            "coverage_ratio": self.coverage_ratio,
            "sample_overlap_ratio": self.sample_overlap_ratio,
        }


@dataclass(frozen=True, slots=True)
class FactorIcMetric:
    trade_date: date
    observation_count: int
    ic: float
    method: str

    def to_record(self) -> dict[str, object]:
        return {
            "trade_date": self.trade_date.isoformat(),
            "observation_count": self.observation_count,
            "ic": self.ic,
            "method": self.method,
        }


@dataclass(frozen=True, slots=True)
class FactorIcSummary:
    mean_ic: float | None
    ic_std: float | None
    icir: float | None
    annualization_periods: int
    date_count: int
    observation_count: int

    def to_record(self) -> dict[str, object]:
        return {
            "mean_ic": self.mean_ic,
            "ic_std": self.ic_std,
            "icir": self.icir,
            "annualization_periods": self.annualization_periods,
            "date_count": self.date_count,
            "observation_count": self.observation_count,
        }


@dataclass(frozen=True, slots=True)
class FactorGroupReturnBucket:
    group: int
    mean_forward_return: float
    observation_count: int

    def to_record(self) -> dict[str, object]:
        return {
            "group": self.group,
            "mean_forward_return": self.mean_forward_return,
            "observation_count": self.observation_count,
        }


@dataclass(frozen=True, slots=True)
class FactorGroupReturnSummary:
    groups: Sequence[FactorGroupReturnBucket]
    long_short_mean_return: float | None

    def __post_init__(self) -> None:
        object.__setattr__(self, "groups", tuple(self.groups))

    def to_record(self) -> dict[str, object]:
        return {
            "groups": [group.to_record() for group in self.groups],
            "long_short_mean_return": self.long_short_mean_return,
        }


@dataclass(frozen=True, slots=True)
class FactorMonotonicityMetric:
    score: float | None
    direction_adjusted_score: float | None
    method: str
    group_count: int

    def to_record(self) -> dict[str, object]:
        return {
            "score": self.score,
            "direction_adjusted_score": self.direction_adjusted_score,
            "method": self.method,
            "group_count": self.group_count,
        }


@dataclass(frozen=True, slots=True)
class FactorTurnoverMetric:
    from_trade_date: date
    to_trade_date: date
    previous_count: int
    current_count: int
    retained_count: int
    turnover: float | None

    def to_record(self) -> dict[str, object]:
        return {
            "from_trade_date": self.from_trade_date.isoformat(),
            "to_trade_date": self.to_trade_date.isoformat(),
            "previous_count": self.previous_count,
            "current_count": self.current_count,
            "retained_count": self.retained_count,
            "turnover": self.turnover,
        }


@dataclass(frozen=True, slots=True)
class FactorTurnoverSummary:
    mean_turnover: float | None
    period_count: int

    def to_record(self) -> dict[str, object]:
        return {
            "mean_turnover": self.mean_turnover,
            "period_count": self.period_count,
        }


@dataclass(frozen=True, slots=True)
class FactorExposureMetric:
    exposure_name: str
    observation_count: int
    mean_exposure: float
    factor_correlation: float | None

    def to_record(self) -> dict[str, object]:
        return {
            "exposure_name": self.exposure_name,
            "observation_count": self.observation_count,
            "mean_exposure": self.mean_exposure,
            "factor_correlation": self.factor_correlation,
        }


@dataclass(frozen=True, slots=True)
class FactorExposureSummary:
    exposures: Mapping[str, FactorExposureMetric]

    def __post_init__(self) -> None:
        object.__setattr__(self, "exposures", MappingProxyType(dict(self.exposures)))

    def to_record(self) -> dict[str, object]:
        return {
            "exposures": {name: metric.to_record() for name, metric in self.exposures.items()},
        }


@dataclass(frozen=True, slots=True)
class FactorEvaluationReport:
    spec: FactorEvaluationSpec
    coverage: FactorCoverageSummary
    ic_by_date: Sequence[FactorIcMetric]
    ic_summary: FactorIcSummary
    group_return_summary: FactorGroupReturnSummary
    monotonicity: FactorMonotonicityMetric
    turnover_by_period: Sequence[FactorTurnoverMetric]
    turnover_summary: FactorTurnoverSummary
    exposure_summary: FactorExposureSummary
    warnings: Sequence[FactorEvaluationWarning]

    def __post_init__(self) -> None:
        object.__setattr__(self, "ic_by_date", tuple(self.ic_by_date))
        object.__setattr__(self, "turnover_by_period", tuple(self.turnover_by_period))
        object.__setattr__(self, "warnings", tuple(self.warnings))

    @property
    def schema_name(self) -> str:
        return self.spec.schema_name

    @property
    def schema_version(self) -> str:
        return self.spec.schema_version

    def to_record(self) -> dict[str, object]:
        return {
            "spec": self.spec.to_record(),
            "coverage": self.coverage.to_record(),
            "ic_by_date": [metric.to_record() for metric in self.ic_by_date],
            "ic_summary": self.ic_summary.to_record(),
            "group_return_summary": self.group_return_summary.to_record(),
            "monotonicity": self.monotonicity.to_record(),
            "turnover_by_period": [metric.to_record() for metric in self.turnover_by_period],
            "turnover_summary": self.turnover_summary.to_record(),
            "exposure_summary": self.exposure_summary.to_record(),
            "warnings": [warning.to_record() for warning in self.warnings],
        }


@dataclass(frozen=True, slots=True)
class _PairedObservation:
    row: FactorEvaluationObservation
    group: int


def evaluate_factor(
    observations: Sequence[FactorEvaluationObservation],
    spec: FactorEvaluationSpec,
) -> FactorEvaluationReport:
    if type(spec) is not FactorEvaluationSpec:
        raise FactorEvaluationError("spec must be a FactorEvaluationSpec")
    rows = tuple(observations)
    if not rows:
        raise FactorEvaluationError("factor evaluation observations are required")
    for row in rows:
        if type(row) is not FactorEvaluationObservation:
            raise FactorEvaluationError("observations must contain FactorEvaluationObservation values")
        if spec.formal and row.factor_available_at > row.decision_time:
            raise FactorEvaluationError(
                "Factor Evaluation PIT check failed: factor_available_at is after decision_time"
            )

    universe_rows = tuple(row for row in rows if row.in_universe)
    if not universe_rows:
        raise FactorEvaluationError("at least one universe observation is required")

    warnings: list[FactorEvaluationWarning] = []
    coverage = _coverage_summary(universe_rows, warnings)
    grouped = _paired_by_date(universe_rows)
    if not grouped:
        raise FactorEvaluationError("Factor Evaluation sample overlap check failed: no factor/return pairs")

    paired_with_groups = _assign_groups(grouped, spec)
    ic_by_date = _ic_metrics(grouped, spec, warnings)
    ic_summary = _ic_summary(ic_by_date, spec, warnings)
    group_summary = _group_return_summary(paired_with_groups, spec, warnings)
    monotonicity = _monotonicity(group_summary, spec, warnings)
    turnover_by_period = _turnover_metrics(paired_with_groups, spec, warnings)
    turnover_summary = _turnover_summary(turnover_by_period)
    exposure_rows = tuple(item.row for values in paired_with_groups.values() for item in values)
    exposure_summary = _exposure_summary(exposure_rows, spec, warnings)

    return FactorEvaluationReport(
        spec=spec,
        coverage=coverage,
        ic_by_date=tuple(ic_by_date),
        ic_summary=ic_summary,
        group_return_summary=group_summary,
        monotonicity=monotonicity,
        turnover_by_period=tuple(turnover_by_period),
        turnover_summary=turnover_summary,
        exposure_summary=exposure_summary,
        warnings=tuple(warnings),
    )


def publish_factor_evaluation_report(
    report: FactorEvaluationReport,
    artifact_store: ArtifactStore,
    *,
    created_at: datetime,
    retention_tier: ArtifactRetentionTier = ArtifactRetentionTier.STANDARD,
) -> ArtifactManifest:
    if type(report) is not FactorEvaluationReport:
        raise FactorEvaluationError("report must be a FactorEvaluationReport")
    _require_aware_datetime("created_at", created_at)
    payload = (
        json.dumps(report.to_record(), ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8")
        + b"\n"
    )
    return artifact_store.put_bytes(
        payload,
        schema_name=report.schema_name,
        schema_version=report.schema_version,
        content_type="application/json",
        produced_by_run_id=report.spec.run_id,
        produced_by_stage_id=report.spec.stage_id,
        retention_tier=retention_tier,
        created_at=created_at,
    )


def _coverage_summary(
    rows: Sequence[FactorEvaluationObservation],
    warnings: list[FactorEvaluationWarning],
) -> FactorCoverageSummary:
    total = len(rows)
    factor_count = sum(row.factor_value is not None for row in rows)
    return_count = sum(row.forward_return is not None for row in rows)
    overlap_count = sum(row.factor_value is not None and row.forward_return is not None for row in rows)
    factor_only = sum(row.factor_value is not None and row.forward_return is None for row in rows)
    return_only = sum(row.factor_value is None and row.forward_return is not None for row in rows)
    if factor_only or return_only:
        warnings.append(
            FactorEvaluationWarning(
                code="sample_non_overlap",
                message=(
                    "Factor and forward-return samples did not fully overlap; "
                    "IC, group return and exposure metrics use the intersection."
                ),
                affected_count=factor_only + return_only,
            )
        )
    return FactorCoverageSummary(
        total_universe_count=total,
        factor_observation_count=factor_count,
        return_observation_count=return_count,
        overlap_observation_count=overlap_count,
        factor_only_count=factor_only,
        return_only_count=return_only,
    )


def _paired_by_date(
    rows: Sequence[FactorEvaluationObservation],
) -> dict[date, list[FactorEvaluationObservation]]:
    grouped: dict[date, list[FactorEvaluationObservation]] = defaultdict(list)
    for row in rows:
        if row.factor_value is not None and row.forward_return is not None:
            grouped[row.trade_date].append(row)
    return {
        trade_date: sorted(values, key=lambda row: row.instrument_id)
        for trade_date, values in sorted(grouped.items())
    }


def _assign_groups(
    grouped: Mapping[date, Sequence[FactorEvaluationObservation]],
    spec: FactorEvaluationSpec,
) -> dict[date, tuple[_PairedObservation, ...]]:
    assigned: dict[date, tuple[_PairedObservation, ...]] = {}
    for trade_date, rows in grouped.items():
        sorted_rows = sorted(rows, key=lambda row: (float(row.factor_value), row.instrument_id))
        n = len(sorted_rows)
        values: list[_PairedObservation] = []
        for index, row in enumerate(sorted_rows):
            group = max(1, min(spec.quantile_count, math.ceil(((index + 1) * spec.quantile_count) / n)))
            values.append(_PairedObservation(row=row, group=group))
        assigned[trade_date] = tuple(sorted(values, key=lambda item: item.row.instrument_id))
    return assigned


def _ic_metrics(
    grouped: Mapping[date, Sequence[FactorEvaluationObservation]],
    spec: FactorEvaluationSpec,
    warnings: list[FactorEvaluationWarning],
) -> list[FactorIcMetric]:
    metrics: list[FactorIcMetric] = []
    for trade_date, rows in grouped.items():
        if len(rows) < spec.minimum_ic_observations:
            warnings.append(
                FactorEvaluationWarning(
                    trade_date=trade_date,
                    code="ic_small_sample",
                    message="IC skipped because the date group is below minimum_ic_observations.",
                    affected_count=len(rows),
                )
            )
            continue
        factor_values = np.asarray([float(row.factor_value) for row in rows], dtype=float)
        returns = np.asarray([float(row.forward_return) for row in rows], dtype=float)
        ic = _correlation(factor_values, returns, spec.correlation_method)
        if ic is None:
            warnings.append(
                FactorEvaluationWarning(
                    trade_date=trade_date,
                    code="ic_zero_variance",
                    message="IC skipped because factor or forward-return values have zero variance.",
                    affected_count=len(rows),
                )
            )
            continue
        metrics.append(
            FactorIcMetric(
                trade_date=trade_date,
                observation_count=len(rows),
                ic=ic,
                method=spec.correlation_method.value,
            )
        )
    return metrics


def _ic_summary(
    metrics: Sequence[FactorIcMetric],
    spec: FactorEvaluationSpec,
    warnings: list[FactorEvaluationWarning],
) -> FactorIcSummary:
    if not metrics:
        warnings.append(
            FactorEvaluationWarning(
                code="ic_summary_empty",
                message="IC summary is empty because no date produced a valid IC.",
            )
        )
        return FactorIcSummary(
            mean_ic=None,
            ic_std=None,
            icir=None,
            annualization_periods=spec.future_return_window.annualization_periods,
            date_count=0,
            observation_count=0,
        )
    values = np.asarray([metric.ic for metric in metrics], dtype=float)
    mean_ic = float(np.mean(values))
    ic_std = float(np.std(values, ddof=1)) if len(values) > 1 else None
    if ic_std is None or ic_std == 0.0:
        warnings.append(
            FactorEvaluationWarning(
                code="icir_zero_variance",
                message="ICIR is undefined because IC standard deviation is zero or unavailable.",
                affected_count=len(metrics),
            )
        )
        icir = None
    else:
        icir = float(mean_ic / ic_std * math.sqrt(spec.future_return_window.annualization_periods))
    return FactorIcSummary(
        mean_ic=mean_ic,
        ic_std=ic_std,
        icir=icir,
        annualization_periods=spec.future_return_window.annualization_periods,
        date_count=len(metrics),
        observation_count=sum(metric.observation_count for metric in metrics),
    )


def _group_return_summary(
    assigned: Mapping[date, Sequence[_PairedObservation]],
    spec: FactorEvaluationSpec,
    warnings: list[FactorEvaluationWarning],
) -> FactorGroupReturnSummary:
    returns_by_group: dict[int, list[float]] = {group: [] for group in range(1, spec.quantile_count + 1)}
    for trade_date, observations in assigned.items():
        date_groups = {group: [] for group in range(1, spec.quantile_count + 1)}
        for item in observations:
            date_groups[item.group].append(float(item.row.forward_return))
        empty_groups = [group for group, values in date_groups.items() if not values]
        if empty_groups:
            warnings.append(
                FactorEvaluationWarning(
                    trade_date=trade_date,
                    code="group_return_empty_bin",
                    message="One or more quantile groups had no observations on this date.",
                    affected_count=len(empty_groups),
                )
            )
        for group, values in date_groups.items():
            returns_by_group[group].extend(values)

    buckets = tuple(
        FactorGroupReturnBucket(
            group=group,
            mean_forward_return=float(np.mean(values)) if values else 0.0,
            observation_count=len(values),
        )
        for group, values in returns_by_group.items()
    )
    bottom = buckets[0].mean_forward_return
    top = buckets[-1].mean_forward_return
    long_short = top - bottom
    if spec.factor_direction is FactorDirection.LOWER_IS_BETTER:
        long_short = bottom - top
    return FactorGroupReturnSummary(groups=buckets, long_short_mean_return=float(long_short))


def _monotonicity(
    group_summary: FactorGroupReturnSummary,
    spec: FactorEvaluationSpec,
    warnings: list[FactorEvaluationWarning],
) -> FactorMonotonicityMetric:
    groups = np.asarray([bucket.group for bucket in group_summary.groups], dtype=float)
    returns = np.asarray([bucket.mean_forward_return for bucket in group_summary.groups], dtype=float)
    score = _correlation(groups, returns, FactorCorrelationMethod.SPEARMAN)
    if score is None:
        warnings.append(
            FactorEvaluationWarning(
                code="monotonicity_rank_deficient",
                message="Monotonicity is undefined because group returns have zero variance.",
                affected_count=len(group_summary.groups),
            )
        )
        adjusted = None
    else:
        adjusted = score if spec.factor_direction is not FactorDirection.LOWER_IS_BETTER else -score
    return FactorMonotonicityMetric(
        score=score,
        direction_adjusted_score=adjusted,
        method="spearman_group_return",
        group_count=len(group_summary.groups),
    )


def _turnover_metrics(
    assigned: Mapping[date, Sequence[_PairedObservation]],
    spec: FactorEvaluationSpec,
    warnings: list[FactorEvaluationWarning],
) -> list[FactorTurnoverMetric]:
    selected_by_date: dict[date, set[str]] = {}
    selected_group = spec.quantile_count if spec.factor_direction is not FactorDirection.LOWER_IS_BETTER else 1
    for trade_date, observations in assigned.items():
        selected_by_date[trade_date] = {
            item.row.instrument_id for item in observations if item.group == selected_group
        }

    metrics: list[FactorTurnoverMetric] = []
    dates = sorted(selected_by_date)
    for previous_date, current_date in zip(dates, dates[1:]):
        previous = selected_by_date[previous_date]
        current = selected_by_date[current_date]
        if not previous:
            turnover = None
            warnings.append(
                FactorEvaluationWarning(
                    trade_date=current_date,
                    code="turnover_empty_previous_selection",
                    message="Turnover is undefined because the previous selected group was empty.",
                    affected_count=len(current),
                )
            )
        else:
            retained = len(previous & current)
            turnover = 1.0 - retained / len(previous)
        metrics.append(
            FactorTurnoverMetric(
                from_trade_date=previous_date,
                to_trade_date=current_date,
                previous_count=len(previous),
                current_count=len(current),
                retained_count=len(previous & current),
                turnover=turnover,
            )
        )
    return metrics


def _turnover_summary(metrics: Sequence[FactorTurnoverMetric]) -> FactorTurnoverSummary:
    values = [metric.turnover for metric in metrics if metric.turnover is not None]
    return FactorTurnoverSummary(
        mean_turnover=None if not values else float(np.mean(np.asarray(values, dtype=float))),
        period_count=len(metrics),
    )


def _exposure_summary(
    rows: Sequence[FactorEvaluationObservation],
    spec: FactorEvaluationSpec,
    warnings: list[FactorEvaluationWarning],
) -> FactorExposureSummary:
    exposure_metrics: dict[str, FactorExposureMetric] = {}
    for exposure_name in spec.exposure_fields:
        values: list[float] = []
        factors: list[float] = []
        missing = 0
        for row in rows:
            raw_exposure = row.exposures.get(exposure_name)
            if raw_exposure is None:
                missing += 1
                continue
            exposure_value = _optional_finite_float(f"exposure {exposure_name}", raw_exposure)
            if exposure_value is None:
                missing += 1
                continue
            values.append(exposure_value)
            factors.append(float(row.factor_value))
        if missing:
            warnings.append(
                FactorEvaluationWarning(
                    code="exposure_missing_values",
                    message=(
                        f"Exposure '{exposure_name}' had missing values "
                        "and was summarized on the available subset."
                    ),
                    affected_count=missing,
                )
            )
        if not values:
            warnings.append(
                FactorEvaluationWarning(
                    code="exposure_empty",
                    message=f"Exposure '{exposure_name}' had no numeric values.",
                    affected_count=len(rows),
                )
            )
            continue
        correlation = _correlation(
            np.asarray(factors, dtype=float),
            np.asarray(values, dtype=float),
            FactorCorrelationMethod.PEARSON,
        )
        exposure_metrics[exposure_name] = FactorExposureMetric(
            exposure_name=exposure_name,
            observation_count=len(values),
            mean_exposure=float(np.mean(np.asarray(values, dtype=float))),
            factor_correlation=correlation,
        )
    return FactorExposureSummary(exposures=exposure_metrics)


def _correlation(
    left: np.ndarray,
    right: np.ndarray,
    method: FactorCorrelationMethod,
) -> float | None:
    if len(left) != len(right):
        raise FactorEvaluationError("correlation inputs must have the same length")
    if len(left) < 2:
        return None
    x = _average_ranks(left) if method is FactorCorrelationMethod.SPEARMAN else left.astype(float)
    y = _average_ranks(right) if method is FactorCorrelationMethod.SPEARMAN else right.astype(float)
    if float(np.std(x)) == 0.0 or float(np.std(y)) == 0.0:
        return None
    return float(np.corrcoef(x, y)[0, 1])


def _average_ranks(values: np.ndarray) -> np.ndarray:
    order = np.argsort(values, kind="mergesort")
    ranks = np.empty(len(values), dtype=float)
    sorted_values = values[order]
    index = 0
    while index < len(values):
        end = index + 1
        while end < len(values) and sorted_values[end] == sorted_values[index]:
            end += 1
        average_rank = (index + 1 + end) / 2.0
        ranks[order[index:end]] = average_rank
        index = end
    return ranks


def _validate_factor_version_id(value: str) -> str:
    normalized = _required_string("factor_version_id", value)
    if not _FACTOR_VERSION_ID_RE.fullmatch(normalized):
        raise FactorEvaluationError("factor_version_id must be an fdv_* identifier")
    return normalized


def _validate_dataset_version(value: str) -> str:
    normalized = _required_string("dataset_version", value)
    if normalized.lower() == "latest":
        raise FactorEvaluationError("Factor Evaluation requires concrete Dataset Version references")
    try:
        DatasetVersionRef.version(normalized)
    except (DatasetCatalogError, ValueError) as exc:
        raise FactorEvaluationError("Factor Evaluation requires concrete Dataset Version references") from exc
    return normalized


def _required_string(field_name: str, value: str) -> str:
    if type(value) is not str:
        raise FactorEvaluationError(f"{field_name} is required")
    stripped = value.strip()
    if not stripped:
        raise FactorEvaluationError(f"{field_name} is required")
    return stripped


def _optional_finite_float(field_name: str, value: object) -> float | None:
    if value is None:
        return None
    if type(value) not in {int, float}:
        raise FactorEvaluationError(f"{field_name} must be numeric")
    numeric = float(value)
    if not math.isfinite(numeric):
        raise FactorEvaluationError(f"{field_name} must be finite")
    return numeric


def _require_aware_datetime(field_name: str, value: datetime) -> None:
    if type(value) is not datetime:
        raise FactorEvaluationError(f"{field_name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise FactorEvaluationError(f"{field_name} must be timezone-aware")


def _safe_ratio(numerator: int, denominator: int) -> float:
    return 0.0 if denominator == 0 else numerator / denominator


def _freeze_mapping(value: Mapping[str, Any]) -> Mapping[str, Any]:
    return MappingProxyType({str(key): _freeze_value(item) for key, item in value.items()})


def _freeze_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return _freeze_mapping(value)
    if isinstance(value, list | tuple):
        return tuple(_freeze_value(item) for item in value)
    return value


def _thaw_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw_value(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw_value(item) for item in value]
    return value
