from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import StrEnum
from types import MappingProxyType
from typing import Any

import numpy as np

from serenity_alpha_lab.datasets.catalog import DatasetCatalogError, DatasetVersionRef
from serenity_alpha_lab.domain.instruments import InstrumentId


FACTOR_POST_PROCESSING_CONTRACT_VERSION = "1.0.0"
FACTOR_POST_PROCESSING_SCHEMA_NAME = "quant.factor_cross_section_post_processing"
FACTOR_POST_PROCESSING_SCHEMA_VERSION = "1.0.0"
FACTOR_POST_PROCESSING_ENGINE_VERSION = "factor_cross_section_post_processing@1.0.0"
MISSING_INDUSTRY_BUCKET = "__missing_industry__"


class FactorPostProcessingError(ValueError):
    """Raised when cross-sectional post-processing input or parameters are invalid."""


class CrossSectionMissingStrategy(StrEnum):
    DROP = "drop"
    FILL_MEDIAN = "fill_median"
    FILL_CONSTANT = "fill_constant"
    ZERO = "zero"


class WinsorizationMethod(StrEnum):
    MAD = "mad"
    QUANTILE = "quantile"


class StandardizationMethod(StrEnum):
    ZSCORE = "zscore"


class NeutralizationExposure(StrEnum):
    INDUSTRY = "industry"
    LOG_MARKET_CAP = "log_market_cap"


@dataclass(frozen=True, slots=True)
class CrossSectionMissingPolicy:
    strategy: CrossSectionMissingStrategy | str
    fill_value: float | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "strategy", CrossSectionMissingStrategy(self.strategy))
        if self.strategy is CrossSectionMissingStrategy.FILL_CONSTANT:
            if self.fill_value is None:
                raise FactorPostProcessingError("fill_value is required for fill_constant missing policy")
            object.__setattr__(self, "fill_value", _finite_float("fill_value", self.fill_value))
        elif self.fill_value is not None:
            raise FactorPostProcessingError("fill_value is only valid for fill_constant missing policy")

    def to_record(self) -> dict[str, object]:
        record: dict[str, object] = {"strategy": self.strategy.value}
        if self.fill_value is not None:
            record["fill_value"] = self.fill_value
        return record


@dataclass(frozen=True, slots=True)
class WinsorizationSpec:
    method: WinsorizationMethod | str
    n_mad: float | None = None
    lower_quantile: float | None = None
    upper_quantile: float | None = None

    def __post_init__(self) -> None:
        method = WinsorizationMethod(self.method)
        object.__setattr__(self, "method", method)
        if method is WinsorizationMethod.MAD:
            n_mad = 3.0 if self.n_mad is None else _finite_float("n_mad", self.n_mad, minimum=0.0)
            if n_mad <= 0:
                raise FactorPostProcessingError("n_mad must be positive")
            object.__setattr__(self, "n_mad", n_mad)
            if self.lower_quantile is not None or self.upper_quantile is not None:
                raise FactorPostProcessingError("quantile parameters are only valid for quantile winsorization")
        else:
            if self.lower_quantile is None or self.upper_quantile is None:
                raise FactorPostProcessingError("lower_quantile and upper_quantile are required")
            lower = _finite_float("lower_quantile", self.lower_quantile, minimum=0.0, maximum=1.0)
            upper = _finite_float("upper_quantile", self.upper_quantile, minimum=0.0, maximum=1.0)
            if lower >= upper:
                raise FactorPostProcessingError("lower_quantile must be less than upper_quantile")
            object.__setattr__(self, "lower_quantile", lower)
            object.__setattr__(self, "upper_quantile", upper)
            if self.n_mad is not None:
                raise FactorPostProcessingError("n_mad is only valid for mad winsorization")

    def to_record(self) -> dict[str, object]:
        if self.method is WinsorizationMethod.MAD:
            return {"method": self.method.value, "n_mad": self.n_mad}
        return {
            "method": self.method.value,
            "lower_quantile": self.lower_quantile,
            "upper_quantile": self.upper_quantile,
        }


@dataclass(frozen=True, slots=True)
class StandardizationSpec:
    method: StandardizationMethod | str

    def __post_init__(self) -> None:
        object.__setattr__(self, "method", StandardizationMethod(self.method))

    def to_record(self) -> dict[str, str]:
        return {"method": self.method.value}


@dataclass(frozen=True, slots=True)
class NeutralizationSpec:
    exposures: Sequence[NeutralizationExposure | str]
    missing_industry_bucket: str = MISSING_INDUSTRY_BUCKET
    missing_market_cap_strategy: CrossSectionMissingStrategy | str = CrossSectionMissingStrategy.DROP

    def __post_init__(self) -> None:
        exposures = tuple(NeutralizationExposure(exposure) for exposure in self.exposures)
        if not exposures:
            raise FactorPostProcessingError("neutralization exposures are required")
        if len(set(exposures)) != len(exposures):
            raise FactorPostProcessingError("neutralization exposures cannot contain duplicates")
        object.__setattr__(self, "exposures", exposures)
        object.__setattr__(
            self,
            "missing_industry_bucket",
            _required_string("missing_industry_bucket", self.missing_industry_bucket),
        )
        strategy = CrossSectionMissingStrategy(self.missing_market_cap_strategy)
        if strategy is CrossSectionMissingStrategy.FILL_CONSTANT:
            raise FactorPostProcessingError("missing market_cap fill_constant is not supported")
        object.__setattr__(self, "missing_market_cap_strategy", strategy)

    def to_record(self) -> dict[str, object]:
        return {
            "exposures": [exposure.value for exposure in self.exposures],
            "missing_industry_bucket": self.missing_industry_bucket,
            "missing_market_cap_strategy": self.missing_market_cap_strategy.value,
        }


@dataclass(frozen=True, slots=True)
class CrossSectionPostProcessingSpec:
    dataset_versions: Mapping[str, str]
    missing_policy: CrossSectionMissingPolicy = field(
        default_factory=lambda: CrossSectionMissingPolicy(strategy=CrossSectionMissingStrategy.DROP)
    )
    winsorization: WinsorizationSpec | None = None
    neutralization: NeutralizationSpec | None = None
    standardization: StandardizationSpec | None = None
    contract_version: str = FACTOR_POST_PROCESSING_CONTRACT_VERSION
    schema_name: str = FACTOR_POST_PROCESSING_SCHEMA_NAME
    schema_version: str = FACTOR_POST_PROCESSING_SCHEMA_VERSION
    engine_version: str = FACTOR_POST_PROCESSING_ENGINE_VERSION

    def __post_init__(self) -> None:
        if not self.dataset_versions:
            raise FactorPostProcessingError("dataset_versions are required")
        versions: dict[str, str] = {}
        for name, version in self.dataset_versions.items():
            versions[_required_string("dataset name", name)] = _validate_dataset_version(version)
        object.__setattr__(self, "dataset_versions", MappingProxyType(versions))
        if type(self.missing_policy) is not CrossSectionMissingPolicy:
            raise FactorPostProcessingError("missing_policy must be a CrossSectionMissingPolicy")
        if self.winsorization is not None and type(self.winsorization) is not WinsorizationSpec:
            raise FactorPostProcessingError("winsorization must be a WinsorizationSpec")
        if self.neutralization is not None and type(self.neutralization) is not NeutralizationSpec:
            raise FactorPostProcessingError("neutralization must be a NeutralizationSpec")
        if self.standardization is not None and type(self.standardization) is not StandardizationSpec:
            raise FactorPostProcessingError("standardization must be a StandardizationSpec")
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
            "dataset_versions": dict(self.dataset_versions),
            "missing_policy": self.missing_policy.to_record(),
            "winsorization": None if self.winsorization is None else self.winsorization.to_record(),
            "neutralization": None if self.neutralization is None else self.neutralization.to_record(),
            "standardization": None if self.standardization is None else self.standardization.to_record(),
        }


@dataclass(frozen=True, slots=True)
class CrossSectionFactorValue:
    instrument_id: str | InstrumentId
    trade_date: date
    raw_value: float | None
    industry: str | None = None
    market_cap: float | None = None
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
            raise FactorPostProcessingError("trade_date must be a date")
        object.__setattr__(self, "raw_value", _optional_finite_float("raw_value", self.raw_value))
        object.__setattr__(self, "industry", _optional_string(self.industry))
        if self.market_cap is not None:
            market_cap = _finite_float("market_cap", self.market_cap, minimum=0.0)
            if market_cap <= 0:
                raise FactorPostProcessingError("market_cap must be positive")
            object.__setattr__(self, "market_cap", market_cap)
        object.__setattr__(self, "metadata", _freeze_mapping(self.metadata))

    def to_record(self) -> dict[str, object]:
        return {
            "instrument_id": self.instrument_id,
            "trade_date": self.trade_date.isoformat(),
            "raw_value": self.raw_value,
            "industry": self.industry,
            "market_cap": self.market_cap,
            "metadata": _thaw_value(self.metadata),
        }


@dataclass(frozen=True, slots=True)
class FactorPostProcessingWarning:
    trade_date: date
    code: str
    message: str
    affected_count: int = 0

    def __post_init__(self) -> None:
        if type(self.trade_date) is not date:
            raise FactorPostProcessingError("warning trade_date must be a date")
        object.__setattr__(self, "code", _required_string("warning code", self.code))
        object.__setattr__(self, "message", _required_string("warning message", self.message))
        if type(self.affected_count) is not int or self.affected_count < 0:
            raise FactorPostProcessingError("affected_count cannot be negative")

    def to_record(self) -> dict[str, object]:
        return {
            "trade_date": self.trade_date.isoformat(),
            "code": self.code,
            "message": self.message,
            "affected_count": self.affected_count,
        }


@dataclass(frozen=True, slots=True)
class ProcessedCrossSectionFactorValue:
    instrument_id: str
    trade_date: date
    raw_value: float | None
    filled_value: float | None
    processed_value: float
    step_values: Mapping[str, float | None]
    exposures: Mapping[str, Any]
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "instrument_id", InstrumentId.parse(str(self.instrument_id)).canonical)
        if type(self.trade_date) is not date:
            raise FactorPostProcessingError("trade_date must be a date")
        object.__setattr__(self, "filled_value", _optional_finite_float("filled_value", self.filled_value))
        object.__setattr__(self, "processed_value", _finite_float("processed_value", self.processed_value))
        object.__setattr__(self, "step_values", _freeze_mapping(self.step_values))
        object.__setattr__(self, "exposures", _freeze_mapping(self.exposures))
        object.__setattr__(self, "metadata", _freeze_mapping(self.metadata))

    def to_record(self) -> dict[str, object]:
        return {
            "instrument_id": self.instrument_id,
            "trade_date": self.trade_date.isoformat(),
            "raw_value": self.raw_value,
            "filled_value": self.filled_value,
            "processed_value": self.processed_value,
            "step_values": _thaw_value(self.step_values),
            "exposures": _thaw_value(self.exposures),
            "metadata": _thaw_value(self.metadata),
        }


@dataclass(frozen=True, slots=True)
class CrossSectionPostProcessingResult:
    spec: CrossSectionPostProcessingSpec
    processed_values: Sequence[ProcessedCrossSectionFactorValue]
    dropped_values: Sequence[CrossSectionFactorValue]
    warnings: Sequence[FactorPostProcessingWarning]

    def __post_init__(self) -> None:
        object.__setattr__(self, "processed_values", tuple(self.processed_values))
        object.__setattr__(self, "dropped_values", tuple(self.dropped_values))
        object.__setattr__(self, "warnings", tuple(self.warnings))

    @property
    def dataset_versions(self) -> Mapping[str, str]:
        return self.spec.dataset_versions

    def to_record(self) -> dict[str, object]:
        return {
            "spec": self.spec.to_record(),
            "processed_count": len(self.processed_values),
            "dropped_count": len(self.dropped_values),
            "processed_values": [value.to_record() for value in self.processed_values],
            "dropped_values": [value.to_record() for value in self.dropped_values],
            "warnings": [warning.to_record() for warning in self.warnings],
        }


@dataclass(slots=True)
class _WorkingValue:
    source: CrossSectionFactorValue
    filled_value: float
    current_value: float
    step_values: dict[str, float | None]
    exposures: dict[str, Any]


def process_cross_sectional_factor_values(
    rows: Sequence[CrossSectionFactorValue],
    spec: CrossSectionPostProcessingSpec,
) -> CrossSectionPostProcessingResult:
    if type(spec) is not CrossSectionPostProcessingSpec:
        raise FactorPostProcessingError("spec must be a CrossSectionPostProcessingSpec")
    grouped: dict[date, list[CrossSectionFactorValue]] = defaultdict(list)
    for row in rows:
        if type(row) is not CrossSectionFactorValue:
            raise FactorPostProcessingError("rows must contain CrossSectionFactorValue values")
        grouped[row.trade_date].append(row)

    processed: list[ProcessedCrossSectionFactorValue] = []
    dropped: list[CrossSectionFactorValue] = []
    warnings: list[FactorPostProcessingWarning] = []
    for trade_date in sorted(grouped):
        group = sorted(grouped[trade_date], key=lambda item: item.instrument_id)
        working, group_dropped = _apply_missing_policy(group, spec.missing_policy, warnings)
        dropped.extend(group_dropped)
        if not working:
            warnings.append(
                FactorPostProcessingWarning(
                    trade_date=trade_date,
                    code="all_values_missing",
                    message="No finite factor values remained after missing-value handling.",
                    affected_count=len(group),
                )
            )
            continue
        if spec.winsorization is not None:
            _apply_winsorization(working, spec.winsorization, warnings)
        if spec.neutralization is not None:
            neutralization_dropped = _apply_neutralization(working, spec.neutralization, warnings)
            dropped.extend(neutralization_dropped)
            if not working:
                continue
        if spec.standardization is not None:
            _apply_standardization(working, spec.standardization, warnings)

        processed.extend(
            ProcessedCrossSectionFactorValue(
                instrument_id=value.source.instrument_id,
                trade_date=value.source.trade_date,
                raw_value=value.source.raw_value,
                filled_value=value.filled_value,
                processed_value=value.current_value,
                step_values=value.step_values,
                exposures=value.exposures,
                metadata=value.source.metadata,
            )
            for value in working
        )

    return CrossSectionPostProcessingResult(
        spec=spec,
        processed_values=tuple(processed),
        dropped_values=tuple(dropped),
        warnings=tuple(warnings),
    )


def _apply_missing_policy(
    group: Sequence[CrossSectionFactorValue],
    policy: CrossSectionMissingPolicy,
    warnings: list[FactorPostProcessingWarning],
) -> tuple[list[_WorkingValue], list[CrossSectionFactorValue]]:
    trade_date = group[0].trade_date
    finite_values = [row.raw_value for row in group if row.raw_value is not None]
    missing_rows = [row for row in group if row.raw_value is None]
    dropped: list[CrossSectionFactorValue] = []
    if missing_rows:
        warnings.append(
            FactorPostProcessingWarning(
                trade_date=trade_date,
                code=(
                    "missing_values_dropped"
                    if policy.strategy is CrossSectionMissingStrategy.DROP
                    else "missing_values_filled"
                ),
                message="Missing factor values were handled according to the cross-sectional missing policy.",
                affected_count=len(missing_rows),
            )
        )
    if policy.strategy is CrossSectionMissingStrategy.DROP:
        dropped.extend(missing_rows)
        fill_value = None
    elif policy.strategy is CrossSectionMissingStrategy.FILL_MEDIAN:
        if not finite_values:
            return [], list(group)
        fill_value = float(np.median(np.asarray(finite_values, dtype=float)))
    elif policy.strategy is CrossSectionMissingStrategy.ZERO:
        fill_value = 0.0
    else:
        fill_value = policy.fill_value

    working: list[_WorkingValue] = []
    for row in group:
        if row.raw_value is None:
            if policy.strategy is CrossSectionMissingStrategy.DROP:
                continue
            value = float(fill_value)
        else:
            value = row.raw_value
        working.append(
            _WorkingValue(
                source=row,
                filled_value=value,
                current_value=value,
                step_values={"filled": value},
                exposures={},
            )
        )
    return working, dropped


def _apply_winsorization(
    values: Sequence[_WorkingValue],
    spec: WinsorizationSpec,
    warnings: list[FactorPostProcessingWarning],
) -> None:
    trade_date = values[0].source.trade_date
    raw = np.asarray([value.current_value for value in values], dtype=float)
    if len(raw) <= 1:
        warnings.append(
            FactorPostProcessingWarning(
                trade_date=trade_date,
                code="winsorize_small_sample",
                message="Winsorization skipped because the date group has fewer than two observations.",
                affected_count=len(raw),
            )
        )
        clipped = raw
    elif spec.method is WinsorizationMethod.MAD:
        median = float(np.median(raw))
        mad = float(np.median(np.abs(raw - median)))
        if mad == 0.0:
            warnings.append(
                FactorPostProcessingWarning(
                    trade_date=trade_date,
                    code="winsorize_zero_mad",
                    message="MAD winsorization skipped because median absolute deviation is zero.",
                    affected_count=len(raw),
                )
            )
            clipped = raw
        else:
            lower = median - float(spec.n_mad) * mad
            upper = median + float(spec.n_mad) * mad
            clipped = np.clip(raw, lower, upper)
    else:
        lower = float(np.quantile(raw, float(spec.lower_quantile)))
        upper = float(np.quantile(raw, float(spec.upper_quantile)))
        clipped = np.clip(raw, lower, upper)

    for working, clipped_value in zip(values, clipped):
        working.current_value = float(clipped_value)
        working.step_values["winsorized"] = float(clipped_value)


def _apply_neutralization(
    values: list[_WorkingValue],
    spec: NeutralizationSpec,
    warnings: list[FactorPostProcessingWarning],
) -> list[CrossSectionFactorValue]:
    trade_date = values[0].source.trade_date
    dropped: list[CrossSectionFactorValue] = []
    if NeutralizationExposure.INDUSTRY in spec.exposures:
        missing_count = 0
        for value in values:
            industry = value.source.industry
            if industry is None:
                missing_count += 1
                industry = spec.missing_industry_bucket
            value.exposures["industry"] = industry
        if missing_count:
            warnings.append(
                FactorPostProcessingWarning(
                    trade_date=trade_date,
                    code="missing_industry_bucketed",
                    message="Missing industry exposure values were assigned to the configured bucket.",
                    affected_count=missing_count,
                )
            )
    if NeutralizationExposure.LOG_MARKET_CAP in spec.exposures:
        _apply_market_cap_exposure(values, spec, warnings, dropped)
    if len(values) <= 1:
        warnings.append(
            FactorPostProcessingWarning(
                trade_date=trade_date,
                code="neutralize_small_sample",
                message=(
                    "Neutralization returned zero residuals because the date group "
                    "has fewer than two observations."
                ),
                affected_count=len(values),
            )
        )
        for value in values:
            value.current_value = 0.0
            value.step_values["neutralized"] = 0.0
        return dropped

    y = np.asarray([value.current_value for value in values], dtype=float)
    columns = [np.ones(len(values), dtype=float)]
    if NeutralizationExposure.INDUSTRY in spec.exposures:
        industries = sorted({str(value.exposures["industry"]) for value in values})
        for industry in industries[1:]:
            columns.append(np.asarray([1.0 if value.exposures["industry"] == industry else 0.0 for value in values]))
    if NeutralizationExposure.LOG_MARKET_CAP in spec.exposures:
        columns.append(np.asarray([float(value.exposures["log_market_cap"]) for value in values], dtype=float))
    x = np.column_stack(columns)
    beta, _, rank, _ = np.linalg.lstsq(x, y, rcond=None)
    residuals = y - x @ beta
    if rank < x.shape[1]:
        warnings.append(
            FactorPostProcessingWarning(
                trade_date=trade_date,
                code="neutralize_rank_deficient",
                message="Neutralization design matrix was rank deficient; least-squares residuals were still returned.",
                affected_count=len(values),
            )
        )
    for value, residual in zip(values, residuals):
        value.current_value = float(residual)
        value.step_values["neutralized"] = float(residual)
    return dropped


def _apply_market_cap_exposure(
    values: list[_WorkingValue],
    spec: NeutralizationSpec,
    warnings: list[FactorPostProcessingWarning],
    dropped: list[CrossSectionFactorValue],
) -> None:
    trade_date = values[0].source.trade_date
    valid_caps = [value.source.market_cap for value in values if value.source.market_cap is not None]
    missing = [value for value in values if value.source.market_cap is None]
    if missing and spec.missing_market_cap_strategy is CrossSectionMissingStrategy.DROP:
        dropped.extend(value.source for value in missing)
        values[:] = [value for value in values if value.source.market_cap is not None]
        warnings.append(
            FactorPostProcessingWarning(
                trade_date=trade_date,
                code="missing_market_cap_dropped",
                message="Rows with missing market capitalization were dropped before neutralization.",
                affected_count=len(missing),
            )
        )
    elif missing:
        if not valid_caps:
            dropped.extend(value.source for value in missing)
            values.clear()
            warnings.append(
                FactorPostProcessingWarning(
                    trade_date=trade_date,
                    code="missing_market_cap_all_dropped",
                    message="All rows had missing market capitalization before neutralization.",
                    affected_count=len(missing),
                )
            )
            return
        if spec.missing_market_cap_strategy is CrossSectionMissingStrategy.FILL_MEDIAN:
            fill_cap = float(np.median(np.asarray(valid_caps, dtype=float)))
        elif spec.missing_market_cap_strategy is CrossSectionMissingStrategy.ZERO:
            fill_cap = 1.0
        else:
            raise FactorPostProcessingError("unsupported missing market_cap strategy")
        warnings.append(
            FactorPostProcessingWarning(
                trade_date=trade_date,
                code="missing_market_cap_filled",
                message="Missing market capitalization values were filled before log-market-cap neutralization.",
                affected_count=len(missing),
            )
        )
        for value in missing:
            value.exposures["market_cap"] = fill_cap
            value.exposures["log_market_cap"] = float(math.log(fill_cap))
    for value in values:
        if "log_market_cap" not in value.exposures:
            market_cap = float(value.source.market_cap)
            value.exposures["market_cap"] = market_cap
            value.exposures["log_market_cap"] = float(math.log(market_cap))


def _apply_standardization(
    values: Sequence[_WorkingValue],
    spec: StandardizationSpec,
    warnings: list[FactorPostProcessingWarning],
) -> None:
    trade_date = values[0].source.trade_date
    if spec.method is not StandardizationMethod.ZSCORE:
        raise FactorPostProcessingError(f"unsupported standardization method: {spec.method.value}")
    raw = np.asarray([value.current_value for value in values], dtype=float)
    if len(raw) <= 1:
        warnings.append(
            FactorPostProcessingWarning(
                trade_date=trade_date,
                code="standardize_small_sample",
                message="Z-score standardization returned zero because the date group has fewer than two observations.",
                affected_count=len(raw),
            )
        )
        standardized = np.zeros_like(raw)
    else:
        mean = float(np.mean(raw))
        std = float(np.std(raw))
        if std == 0.0:
            warnings.append(
                FactorPostProcessingWarning(
                    trade_date=trade_date,
                    code="standardize_zero_variance",
                    message="Z-score standardization returned zero because the date group variance is zero.",
                    affected_count=len(raw),
                )
            )
            standardized = np.zeros_like(raw)
        else:
            standardized = (raw - mean) / std
    for working, standardized_value in zip(values, standardized):
        working.current_value = float(standardized_value)
        working.step_values["standardized"] = float(standardized_value)


def _validate_dataset_version(version: str) -> str:
    normalized = _required_string("dataset_version", version)
    if normalized.lower() == "latest":
        raise FactorPostProcessingError("post-processing inputs must reference a concrete Dataset Version")
    try:
        DatasetVersionRef.version(normalized)
    except (DatasetCatalogError, ValueError) as exc:
        raise FactorPostProcessingError("post-processing inputs must reference a concrete Dataset Version") from exc
    return normalized


def _required_string(field_name: str, value: object) -> str:
    if type(value) is not str:
        raise FactorPostProcessingError(f"{field_name} is required")
    stripped = value.strip()
    if not stripped:
        raise FactorPostProcessingError(f"{field_name} is required")
    return stripped


def _optional_string(value: str | None) -> str | None:
    if value is None:
        return None
    return _required_string("optional string", value)


def _finite_float(
    field_name: str,
    value: object,
    *,
    minimum: float | None = None,
    maximum: float | None = None,
) -> float:
    if type(value) not in {int, float}:
        raise FactorPostProcessingError(f"{field_name} must be numeric")
    normalized = float(value)
    if not math.isfinite(normalized):
        raise FactorPostProcessingError(f"{field_name} must be finite")
    if minimum is not None and normalized < minimum:
        raise FactorPostProcessingError(f"{field_name} must be >= {minimum}")
    if maximum is not None and normalized > maximum:
        raise FactorPostProcessingError(f"{field_name} must be <= {maximum}")
    return normalized


def _optional_finite_float(field_name: str, value: object | None) -> float | None:
    if value is None:
        return None
    return _finite_float(field_name, value)


def _freeze_mapping(values: Mapping[str, Any]) -> Mapping[str, Any]:
    return MappingProxyType({str(key): _freeze_value(value) for key, value in values.items()})


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


__all__ = [
    "FACTOR_POST_PROCESSING_CONTRACT_VERSION",
    "FACTOR_POST_PROCESSING_ENGINE_VERSION",
    "FACTOR_POST_PROCESSING_SCHEMA_NAME",
    "FACTOR_POST_PROCESSING_SCHEMA_VERSION",
    "MISSING_INDUSTRY_BUCKET",
    "CrossSectionFactorValue",
    "CrossSectionMissingPolicy",
    "CrossSectionMissingStrategy",
    "CrossSectionPostProcessingResult",
    "CrossSectionPostProcessingSpec",
    "FactorPostProcessingError",
    "FactorPostProcessingWarning",
    "NeutralizationExposure",
    "NeutralizationSpec",
    "ProcessedCrossSectionFactorValue",
    "StandardizationMethod",
    "StandardizationSpec",
    "WinsorizationMethod",
    "WinsorizationSpec",
    "process_cross_sectional_factor_values",
]
