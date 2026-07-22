from __future__ import annotations

import json
import math
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import StrEnum
from types import MappingProxyType
from typing import Protocol

from serenity_alpha_lab.datasets.schema_registry import DatasetSchemaDeclaration, DatasetSchemaField
from serenity_alpha_lab.domain.artifacts import ArtifactManifest, ArtifactRetentionTier, ArtifactStore


class DataQualityRuleError(ValueError):
    """Raised when a data quality rule or report contract is invalid."""


class DataQualitySeverity(StrEnum):
    WARNING = "warning"
    QUARANTINE = "quarantine"
    BLOCKING = "blocking"


class DataQualityStatus(StrEnum):
    PASSED = "passed"
    WARNING = "warning"
    QUARANTINE = "quarantine"
    BLOCKING = "blocking"


@dataclass(frozen=True, slots=True)
class QualityDatasetSnapshot:
    dataset_name: str
    schema_declaration: DatasetSchemaDeclaration
    records: Sequence[Mapping[str, object]]
    dataset_version_id: str | None = None

    @classmethod
    def from_records(
        cls,
        *,
        dataset_name: str,
        schema_declaration: DatasetSchemaDeclaration,
        records: Iterable[Mapping[str, object]],
        dataset_version_id: str | None = None,
    ) -> QualityDatasetSnapshot:
        return cls(
            dataset_name=dataset_name,
            schema_declaration=schema_declaration,
            records=tuple(records),
            dataset_version_id=dataset_version_id,
        )

    @classmethod
    def from_dataset(
        cls,
        dataset: object,
        *,
        schema_declaration: DatasetSchemaDeclaration,
        dataset_name: str | None = None,
        dataset_version_id: str | None = None,
    ) -> QualityDatasetSnapshot:
        dataset_records = getattr(dataset, "records", None)
        if dataset_records is None:
            raise DataQualityRuleError("dataset must expose records")
        records: list[Mapping[str, object]] = []
        for record in dataset_records:
            to_record = getattr(record, "to_record", None)
            if not callable(to_record):
                raise DataQualityRuleError("dataset records must expose to_record()")
            records.append(to_record())
        return cls.from_records(
            dataset_name=dataset_name or schema_declaration.schema_name,
            schema_declaration=schema_declaration,
            records=records,
            dataset_version_id=dataset_version_id,
        )

    def __post_init__(self) -> None:
        object.__setattr__(self, "dataset_name", _required_string("dataset_name", self.dataset_name))
        if type(self.schema_declaration) is not DatasetSchemaDeclaration:
            raise DataQualityRuleError("schema_declaration must be a DatasetSchemaDeclaration")
        if self.dataset_name != self.schema_declaration.schema_name:
            raise DataQualityRuleError("dataset_name must match schema declaration name")
        object.__setattr__(self, "dataset_version_id", _optional_string(self.dataset_version_id))
        records: list[Mapping[str, object]] = []
        for record in self.records:
            if not isinstance(record, Mapping):
                raise DataQualityRuleError("records must contain mappings")
            records.append(MappingProxyType(dict(record)))
        object.__setattr__(self, "records", tuple(records))

    @property
    def primary_key_fields(self) -> tuple[str, ...]:
        return tuple(self.schema_declaration.primary_key)

    @property
    def partition_keys(self) -> tuple[str, ...]:
        return tuple(self.schema_declaration.partition_keys)

    def primary_key_for(self, record: Mapping[str, object]) -> Mapping[str, str]:
        return MappingProxyType(
            {
                field_name: _stringify(record.get(field_name))
                for field_name in self.primary_key_fields
            }
        )

    def partition_for(self, record: Mapping[str, object]) -> Mapping[str, str]:
        partition = record.get("partition")
        if isinstance(partition, Mapping):
            return MappingProxyType(
                {
                    str(key): _stringify(value)
                    for key, value in sorted(partition.items(), key=lambda item: str(item[0]))
                    if value is not None
                }
            )
        return MappingProxyType(
            {
                field_name: _stringify(record.get(field_name))
                for field_name in self.partition_keys
                if record.get(field_name) is not None
            }
        )


@dataclass(frozen=True, slots=True)
class DataQualityIssue:
    rule_id: str
    rule_version: str
    severity: DataQualitySeverity | str
    dataset_name: str
    message: str
    dataset_version_id: str | None = None
    partition_values: Mapping[str, str] = field(default_factory=dict)
    field_name: str | None = None
    primary_key: Mapping[str, str] = field(default_factory=dict)
    observed_value: object | None = None
    expected_value: object | None = None
    sample: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "rule_id", _required_string("rule_id", self.rule_id))
        object.__setattr__(self, "rule_version", _required_string("rule_version", self.rule_version))
        object.__setattr__(self, "severity", DataQualitySeverity(self.severity))
        object.__setattr__(self, "dataset_name", _required_string("dataset_name", self.dataset_name))
        object.__setattr__(self, "message", _required_string("message", self.message))
        object.__setattr__(self, "dataset_version_id", _optional_string(self.dataset_version_id))
        object.__setattr__(self, "field_name", _optional_string(self.field_name))
        object.__setattr__(self, "partition_values", _freeze_string_mapping(self.partition_values))
        object.__setattr__(self, "primary_key", _freeze_string_mapping(self.primary_key))
        object.__setattr__(self, "sample", MappingProxyType(dict(self.sample)))

    def to_record(self) -> dict[str, object]:
        return {
            "rule_id": self.rule_id,
            "rule_version": self.rule_version,
            "severity": self.severity.value,
            "dataset_name": self.dataset_name,
            "dataset_version_id": self.dataset_version_id,
            "partition_values": dict(self.partition_values),
            "field_name": self.field_name,
            "primary_key": dict(self.primary_key),
            "observed_value": _json_safe(self.observed_value),
            "expected_value": _json_safe(self.expected_value),
            "message": self.message,
            "sample": _json_safe_mapping(self.sample),
        }


@dataclass(frozen=True, slots=True)
class DataQualityReport:
    REPORT_SCHEMA_NAME = "dataset.data_quality_report"
    REPORT_SCHEMA_VERSION = "1.0.0"
    REPORT_CONTENT_TYPE = "application/vnd.serenity.dataset.quality-report+json"

    dataset_name: str
    schema_name: str
    schema_version: str
    schema_hash: str
    rule_set_version: str
    generated_at: datetime
    records_evaluated: int
    issues: Sequence[DataQualityIssue]
    dataset_version_id: str | None = None
    trace_id: str | None = None
    run_id: str | None = None
    stage_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "dataset_name", _required_string("dataset_name", self.dataset_name))
        object.__setattr__(self, "schema_name", _required_string("schema_name", self.schema_name))
        object.__setattr__(self, "schema_version", _required_string("schema_version", self.schema_version))
        object.__setattr__(self, "schema_hash", _required_string("schema_hash", self.schema_hash))
        object.__setattr__(self, "rule_set_version", _required_string("rule_set_version", self.rule_set_version))
        _require_aware_datetime("generated_at", self.generated_at)
        if type(self.records_evaluated) is not int or self.records_evaluated < 0:
            raise DataQualityRuleError("records_evaluated cannot be negative")
        object.__setattr__(self, "dataset_version_id", _optional_string(self.dataset_version_id))
        object.__setattr__(self, "trace_id", _optional_string(self.trace_id))
        object.__setattr__(self, "run_id", _optional_string(self.run_id))
        object.__setattr__(self, "stage_id", _optional_string(self.stage_id))
        issues = tuple(self.issues)
        for issue in issues:
            if type(issue) is not DataQualityIssue:
                raise DataQualityRuleError("issues must contain DataQualityIssue values")
        object.__setattr__(self, "issues", tuple(sorted(issues, key=_issue_sort_key)))

    @property
    def status(self) -> DataQualityStatus:
        severities = {issue.severity for issue in self.issues}
        if DataQualitySeverity.BLOCKING in severities:
            return DataQualityStatus.BLOCKING
        if DataQualitySeverity.QUARANTINE in severities:
            return DataQualityStatus.QUARANTINE
        if DataQualitySeverity.WARNING in severities:
            return DataQualityStatus.WARNING
        return DataQualityStatus.PASSED

    @property
    def issue_counts(self) -> dict[str, int]:
        return {
            severity.value: sum(1 for issue in self.issues if issue.severity is severity)
            for severity in (
                DataQualitySeverity.WARNING,
                DataQualitySeverity.QUARANTINE,
                DataQualitySeverity.BLOCKING,
            )
        }

    def to_record(self) -> dict[str, object]:
        return {
            "schema_name": self.REPORT_SCHEMA_NAME,
            "schema_version": self.REPORT_SCHEMA_VERSION,
            "dataset_name": self.dataset_name,
            "dataset_version_id": self.dataset_version_id,
            "evaluated_schema_name": self.schema_name,
            "evaluated_schema_version": self.schema_version,
            "evaluated_schema_hash": self.schema_hash,
            "rule_set_version": self.rule_set_version,
            "quality_status": self.status.value,
            "generated_at": self.generated_at.isoformat(),
            "trace_id": self.trace_id,
            "run_id": self.run_id,
            "stage_id": self.stage_id,
            "records_evaluated": self.records_evaluated,
            "issue_counts": self.issue_counts,
            "issues": [issue.to_record() for issue in self.issues],
        }

    def to_json_bytes(self) -> bytes:
        return json.dumps(self.to_record(), ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")

    def publish(
        self,
        artifact_store: ArtifactStore,
        *,
        produced_by_run_id: str | None = None,
        produced_by_stage_id: str | None = None,
        retention_tier: ArtifactRetentionTier = ArtifactRetentionTier.STANDARD,
    ) -> ArtifactManifest:
        run_id = _required_string("produced_by_run_id", produced_by_run_id or self.run_id)
        stage_id = produced_by_stage_id if produced_by_stage_id is not None else self.stage_id
        return artifact_store.put_bytes(
            self.to_json_bytes(),
            schema_name=self.REPORT_SCHEMA_NAME,
            schema_version=self.REPORT_SCHEMA_VERSION,
            content_type=self.REPORT_CONTENT_TYPE,
            produced_by_run_id=run_id,
            produced_by_stage_id=stage_id,
            retention_tier=retention_tier,
            created_at=self.generated_at,
        )

    def manifest_metadata(self, *, report_artifact: ArtifactManifest | None = None) -> dict[str, str]:
        metadata = {
            "quality_status": self.status.value,
            "quality_rule_set_version": self.rule_set_version,
            "quality_issue_count_warning": str(self.issue_counts[DataQualitySeverity.WARNING.value]),
            "quality_issue_count_quarantine": str(self.issue_counts[DataQualitySeverity.QUARANTINE.value]),
            "quality_issue_count_blocking": str(self.issue_counts[DataQualitySeverity.BLOCKING.value]),
            "quality_issue_count_total": str(len(self.issues)),
        }
        if report_artifact is not None:
            metadata["quality_report_artifact_id"] = report_artifact.artifact_id
            metadata["quality_report_sha256"] = report_artifact.sha256
        return metadata


class DataQualityRule(Protocol):
    rule_id: str
    rule_version: str
    severity: DataQualitySeverity

    def evaluate(self, snapshot: QualityDatasetSnapshot) -> tuple[DataQualityIssue, ...]:
        """Return deterministic quality issues for a Dataset snapshot."""


@dataclass(frozen=True, slots=True)
class DataQualityEngine:
    rule_set_version: str
    rules: Sequence[DataQualityRule]

    def __post_init__(self) -> None:
        object.__setattr__(self, "rule_set_version", _required_string("rule_set_version", self.rule_set_version))
        rules = tuple(self.rules)
        if not rules:
            raise DataQualityRuleError("rules are required")
        for rule in rules:
            _required_string("rule_id", rule.rule_id)
            _required_string("rule_version", rule.rule_version)
            DataQualitySeverity(rule.severity)
        object.__setattr__(self, "rules", rules)

    def evaluate(
        self,
        snapshot: QualityDatasetSnapshot,
        *,
        generated_at: datetime,
        trace_id: str | None = None,
        run_id: str | None = None,
        stage_id: str | None = None,
    ) -> DataQualityReport:
        if type(snapshot) is not QualityDatasetSnapshot:
            raise DataQualityRuleError("snapshot must be a QualityDatasetSnapshot")
        issues: list[DataQualityIssue] = []
        for rule in self.rules:
            issues.extend(rule.evaluate(snapshot))
        return DataQualityReport(
            dataset_name=snapshot.dataset_name,
            dataset_version_id=snapshot.dataset_version_id,
            schema_name=snapshot.schema_declaration.schema_name,
            schema_version=snapshot.schema_declaration.schema_version,
            schema_hash=snapshot.schema_declaration.schema_hash,
            rule_set_version=self.rule_set_version,
            generated_at=generated_at,
            trace_id=trace_id,
            run_id=run_id,
            stage_id=stage_id,
            records_evaluated=len(snapshot.records),
            issues=tuple(issues),
        )


@dataclass(frozen=True, slots=True)
class UniquePrimaryKeyRule:
    rule_id: str = "primary_key.unique"
    rule_version: str = "1.0.0"
    severity: DataQualitySeverity = DataQualitySeverity.BLOCKING

    def evaluate(self, snapshot: QualityDatasetSnapshot) -> tuple[DataQualityIssue, ...]:
        seen: dict[tuple[str, ...], Mapping[str, object]] = {}
        issues: list[DataQualityIssue] = []
        for record in snapshot.records:
            key = tuple(snapshot.primary_key_for(record).values())
            if key in seen:
                issues.append(
                    _issue(
                        self,
                        snapshot,
                        record,
                        message="Duplicate primary key in dataset snapshot.",
                        primary_key=snapshot.primary_key_for(record),
                        observed_value="duplicate",
                        expected_value="unique",
                    )
                )
                continue
            seen[key] = record
        return tuple(issues)


@dataclass(frozen=True, slots=True)
class SchemaFieldRule:
    rule_id: str = "schema.required_fields_and_types"
    rule_version: str = "1.0.0"
    severity: DataQualitySeverity = DataQualitySeverity.BLOCKING

    def evaluate(self, snapshot: QualityDatasetSnapshot) -> tuple[DataQualityIssue, ...]:
        issues: list[DataQualityIssue] = []
        declared_fields = {schema_field.name: schema_field for schema_field in snapshot.schema_declaration.fields}
        for record in snapshot.records:
            for field_name, schema_field in declared_fields.items():
                if field_name not in record:
                    issues.append(
                        _issue(
                            self,
                            snapshot,
                            record,
                            field_name=field_name,
                            message=f"Required schema field is missing: {field_name}",
                            observed_value="missing",
                            expected_value=schema_field.logical_type,
                        )
                    )
                    continue
                value = record.get(field_name)
                if _is_missing(value):
                    if not schema_field.nullable:
                        issues.append(
                            _issue(
                                self,
                                snapshot,
                                record,
                                field_name=field_name,
                                message=f"Required schema field is null: {field_name}",
                                observed_value=None,
                                expected_value=schema_field.logical_type,
                            )
                        )
                    continue
                if not _matches_logical_type(value, schema_field):
                    issues.append(
                        _issue(
                            self,
                            snapshot,
                            record,
                            field_name=field_name,
                            message=f"Schema field type mismatch: {field_name}",
                            observed_value=value,
                            expected_value=schema_field.logical_type,
                        )
                    )
        return tuple(issues)


@dataclass(frozen=True, slots=True)
class OhlcRelationshipRule:
    rule_id: str = "bars.ohlc_relationship"
    rule_version: str = "1.0.0"
    severity: DataQualitySeverity = DataQualitySeverity.BLOCKING
    open_field: str = "open"
    high_field: str = "high"
    low_field: str = "low"
    close_field: str = "close"

    def evaluate(self, snapshot: QualityDatasetSnapshot) -> tuple[DataQualityIssue, ...]:
        issues: list[DataQualityIssue] = []
        for record in snapshot.records:
            open_price = _optional_float(record.get(self.open_field))
            high = _optional_float(record.get(self.high_field))
            low = _optional_float(record.get(self.low_field))
            close = _optional_float(record.get(self.close_field))
            if None in (open_price, high, low, close):
                continue
            if not (low <= open_price <= high and low <= close <= high):
                issues.append(
                    _issue(
                        self,
                        snapshot,
                        record,
                        field_name=self.close_field,
                        message="OHLC relationship must satisfy low <= open/close <= high.",
                        observed_value={
                            "open": open_price,
                            "high": high,
                            "low": low,
                            "close": close,
                        },
                        expected_value="low <= open/close <= high",
                    )
                )
        return tuple(issues)


@dataclass(frozen=True, slots=True)
class NonNegativeFieldRule:
    fields: Sequence[str]
    rule_id: str = "fields.non_negative"
    rule_version: str = "1.0.0"
    severity: DataQualitySeverity = DataQualitySeverity.BLOCKING

    def __post_init__(self) -> None:
        object.__setattr__(self, "fields", tuple(_required_string("field", field_name) for field_name in self.fields))

    def evaluate(self, snapshot: QualityDatasetSnapshot) -> tuple[DataQualityIssue, ...]:
        issues: list[DataQualityIssue] = []
        for record in snapshot.records:
            for field_name in self.fields:
                value = _optional_float(record.get(field_name))
                if value is None:
                    continue
                if value < 0:
                    issues.append(
                        _issue(
                            self,
                            snapshot,
                            record,
                            field_name=field_name,
                            message=f"{field_name} cannot be negative.",
                            observed_value=value,
                            expected_value=">= 0",
                        )
                    )
        return tuple(issues)


@dataclass(frozen=True, slots=True)
class NullRatioDriftRule:
    baseline_null_ratios: Mapping[str, float]
    max_delta: float
    rule_id: str = "fields.null_ratio_drift"
    rule_version: str = "1.0.0"
    severity: DataQualitySeverity = DataQualitySeverity.QUARANTINE

    def __post_init__(self) -> None:
        object.__setattr__(self, "severity", DataQualitySeverity(self.severity))
        object.__setattr__(self, "max_delta", _non_negative_float("max_delta", self.max_delta))
        baselines: dict[str, float] = {}
        for field_name, ratio in self.baseline_null_ratios.items():
            normalized = _non_negative_float(f"baseline_null_ratios[{field_name}]", ratio)
            if normalized > 1:
                raise DataQualityRuleError("baseline null ratio cannot exceed 1")
            baselines[_required_string("field", field_name)] = normalized
        object.__setattr__(self, "baseline_null_ratios", MappingProxyType(baselines))

    def evaluate(self, snapshot: QualityDatasetSnapshot) -> tuple[DataQualityIssue, ...]:
        if not snapshot.records:
            return ()
        issues: list[DataQualityIssue] = []
        for field_name, baseline_ratio in self.baseline_null_ratios.items():
            null_count = sum(1 for record in snapshot.records if _is_missing(record.get(field_name)))
            observed_ratio = null_count / len(snapshot.records)
            if observed_ratio > baseline_ratio + self.max_delta:
                sample = next(record for record in snapshot.records if _is_missing(record.get(field_name)))
                issues.append(
                    _issue(
                        self,
                        snapshot,
                        sample,
                        field_name=field_name,
                        observed_value=round(observed_ratio, 6),
                        expected_value=f"<= {baseline_ratio + self.max_delta:.6f}",
                        message=f"Null ratio drift exceeded threshold for {field_name}.",
                    )
                )
        return tuple(issues)


@dataclass(frozen=True, slots=True)
class TradingContinuityRule:
    expected_trade_dates_by_market: Mapping[str, Sequence[date]]
    rule_id: str = "bars.trading_continuity"
    rule_version: str = "1.0.0"
    severity: DataQualitySeverity = DataQualitySeverity.QUARANTINE
    instrument_field: str = "instrument_id"
    market_field: str = "market"
    date_field: str = "trade_date"
    provider_field: str = "provider_id"

    def __post_init__(self) -> None:
        object.__setattr__(self, "severity", DataQualitySeverity(self.severity))
        normalized: dict[str, tuple[date, ...]] = {}
        for market, dates in self.expected_trade_dates_by_market.items():
            market_id = _required_string("market", market)
            normalized[market_id] = tuple(sorted(_coerce_date(value) for value in dates))
        object.__setattr__(self, "expected_trade_dates_by_market", MappingProxyType(normalized))

    def evaluate(self, snapshot: QualityDatasetSnapshot) -> tuple[DataQualityIssue, ...]:
        groups: dict[tuple[str, str, str], dict[date, Mapping[str, object]]] = defaultdict(dict)
        for record in snapshot.records:
            instrument = _stringify(record.get(self.instrument_field))
            market = _stringify(record.get(self.market_field))
            provider = _stringify(record.get(self.provider_field))
            trade_date = _optional_date(record.get(self.date_field))
            if not instrument or not market or not provider or trade_date is None:
                continue
            groups[(instrument, market, provider)][trade_date] = record

        issues: list[DataQualityIssue] = []
        for (instrument, market, provider), records_by_date in sorted(groups.items()):
            expected_dates = self.expected_trade_dates_by_market.get(market, ())
            if not expected_dates or not records_by_date:
                continue
            observed_dates = set(records_by_date)
            min_seen = min(observed_dates)
            max_seen = max(observed_dates)
            for expected_date in expected_dates:
                if expected_date < min_seen or expected_date > max_seen or expected_date in observed_dates:
                    continue
                sample = records_by_date[max(date_value for date_value in observed_dates if date_value < expected_date)]
                issues.append(
                    _issue(
                        self,
                        snapshot,
                        sample,
                        field_name=self.date_field,
                        primary_key={
                            self.instrument_field: instrument,
                            self.date_field: expected_date.isoformat(),
                            self.provider_field: provider,
                        },
                        observed_value=f"missing:{expected_date.isoformat()}",
                        expected_value="one row for every expected trading day between observed endpoints",
                        message="Trading calendar continuity gap detected for instrument/provider.",
                    )
                )
        return tuple(issues)


@dataclass(frozen=True, slots=True)
class ReturnOutlierRule:
    max_abs_return: float
    rule_id: str = "bars.return_outlier"
    rule_version: str = "1.0.0"
    severity: DataQualitySeverity = DataQualitySeverity.WARNING
    instrument_field: str = "instrument_id"
    date_field: str = "trade_date"
    provider_field: str = "provider_id"
    close_field: str = "close"

    def __post_init__(self) -> None:
        object.__setattr__(self, "severity", DataQualitySeverity(self.severity))
        object.__setattr__(self, "max_abs_return", _non_negative_float("max_abs_return", self.max_abs_return))

    def evaluate(self, snapshot: QualityDatasetSnapshot) -> tuple[DataQualityIssue, ...]:
        issues: list[DataQualityIssue] = []
        for _, rows in _time_series_groups(
            snapshot.records,
            instrument_field=self.instrument_field,
            provider_field=self.provider_field,
            date_field=self.date_field,
        ).items():
            previous_close: float | None = None
            for record in rows:
                close = _optional_float(record.get(self.close_field))
                if close is None:
                    previous_close = None
                    continue
                if previous_close not in (None, 0.0):
                    observed_return = close / previous_close - 1.0
                    if abs(observed_return) > self.max_abs_return:
                        issues.append(
                            _issue(
                                self,
                                snapshot,
                                record,
                                field_name=self.close_field,
                                observed_value=round(observed_return, 6),
                                expected_value=f"abs(return) <= {self.max_abs_return:.6f}",
                                message="Daily return outlier exceeded threshold.",
                            )
                        )
                previous_close = close
        return tuple(issues)


@dataclass(frozen=True, slots=True)
class VolumeSpikeRule:
    max_multiple: float
    rule_id: str = "bars.volume_spike"
    rule_version: str = "1.0.0"
    severity: DataQualitySeverity = DataQualitySeverity.WARNING
    instrument_field: str = "instrument_id"
    date_field: str = "trade_date"
    provider_field: str = "provider_id"
    volume_field: str = "volume"

    def __post_init__(self) -> None:
        object.__setattr__(self, "severity", DataQualitySeverity(self.severity))
        multiple = _positive_float("max_multiple", self.max_multiple)
        if multiple <= 1:
            raise DataQualityRuleError("max_multiple must be greater than 1")
        object.__setattr__(self, "max_multiple", multiple)

    def evaluate(self, snapshot: QualityDatasetSnapshot) -> tuple[DataQualityIssue, ...]:
        issues: list[DataQualityIssue] = []
        for _, rows in _time_series_groups(
            snapshot.records,
            instrument_field=self.instrument_field,
            provider_field=self.provider_field,
            date_field=self.date_field,
        ).items():
            previous_volume: float | None = None
            for record in rows:
                volume = _optional_float(record.get(self.volume_field))
                if volume is None:
                    previous_volume = None
                    continue
                if previous_volume not in (None, 0.0) and volume > 0:
                    observed_multiple = max(volume / previous_volume, previous_volume / volume)
                    if observed_multiple > self.max_multiple:
                        issues.append(
                            _issue(
                                self,
                                snapshot,
                                record,
                                field_name=self.volume_field,
                                observed_value=round(observed_multiple, 6),
                                expected_value=f"<= {self.max_multiple:.6f}x",
                                message="Volume spike exceeded threshold.",
                            )
                        )
                previous_volume = volume
        return tuple(issues)


@dataclass(frozen=True, slots=True)
class AdjustmentFactorJumpRule:
    max_abs_pct_change: float
    rule_id: str = "adjusted_bars.factor_jump"
    rule_version: str = "1.0.0"
    severity: DataQualitySeverity = DataQualitySeverity.QUARANTINE
    instrument_field: str = "instrument_id"
    date_field: str = "trade_date"
    provider_field: str = "provider_id"
    adjustment_field: str = "adjustment"
    factor_field: str = "adjustment_factor"

    def __post_init__(self) -> None:
        object.__setattr__(self, "severity", DataQualitySeverity(self.severity))
        object.__setattr__(
            self,
            "max_abs_pct_change",
            _non_negative_float("max_abs_pct_change", self.max_abs_pct_change),
        )

    def evaluate(self, snapshot: QualityDatasetSnapshot) -> tuple[DataQualityIssue, ...]:
        groups: dict[tuple[str, str, str], list[Mapping[str, object]]] = defaultdict(list)
        for record in snapshot.records:
            trade_date = _optional_date(record.get(self.date_field))
            if trade_date is None:
                continue
            key = (
                _stringify(record.get(self.instrument_field)),
                _stringify(record.get(self.provider_field)),
                _stringify(record.get(self.adjustment_field)),
            )
            groups[key].append(record)

        issues: list[DataQualityIssue] = []
        for rows in groups.values():
            previous_factor: float | None = None
            for record in sorted(rows, key=lambda item: _optional_date(item.get(self.date_field)) or date.min):
                factor = _optional_float(record.get(self.factor_field))
                if factor is None or factor <= 0:
                    previous_factor = None
                    continue
                if previous_factor not in (None, 0.0):
                    change = factor / previous_factor - 1.0
                    if abs(change) > self.max_abs_pct_change:
                        issues.append(
                            _issue(
                                self,
                                snapshot,
                                record,
                                field_name=self.factor_field,
                                observed_value=round(change, 6),
                                expected_value=f"abs(change) <= {self.max_abs_pct_change:.6f}",
                                message="Adjustment factor jump exceeded threshold.",
                            )
                        )
                previous_factor = factor
        return tuple(issues)


def _issue(
    rule: DataQualityRule,
    snapshot: QualityDatasetSnapshot,
    record: Mapping[str, object],
    *,
    message: str,
    field_name: str | None = None,
    primary_key: Mapping[str, str] | None = None,
    observed_value: object | None = None,
    expected_value: object | None = None,
) -> DataQualityIssue:
    return DataQualityIssue(
        rule_id=rule.rule_id,
        rule_version=rule.rule_version,
        severity=rule.severity,
        dataset_name=snapshot.dataset_name,
        dataset_version_id=snapshot.dataset_version_id,
        partition_values=snapshot.partition_for(record),
        field_name=field_name,
        primary_key=primary_key if primary_key is not None else snapshot.primary_key_for(record),
        observed_value=observed_value,
        expected_value=expected_value,
        message=message,
        sample=record,
    )


def _time_series_groups(
    records: Sequence[Mapping[str, object]],
    *,
    instrument_field: str,
    provider_field: str,
    date_field: str,
) -> dict[tuple[str, str], list[Mapping[str, object]]]:
    groups: dict[tuple[str, str], list[Mapping[str, object]]] = defaultdict(list)
    for record in records:
        trade_date = _optional_date(record.get(date_field))
        if trade_date is None:
            continue
        key = (_stringify(record.get(instrument_field)), _stringify(record.get(provider_field)))
        groups[key].append(record)
    return {
        key: sorted(rows, key=lambda item: _optional_date(item.get(date_field)) or date.min)
        for key, rows in groups.items()
    }


def _issue_sort_key(issue: DataQualityIssue) -> tuple[int, str, str, str, str]:
    severity_rank = {
        DataQualitySeverity.BLOCKING: 0,
        DataQualitySeverity.QUARANTINE: 1,
        DataQualitySeverity.WARNING: 2,
    }
    return (
        severity_rank[issue.severity],
        issue.rule_id,
        json.dumps(dict(issue.primary_key), ensure_ascii=False, sort_keys=True),
        issue.field_name or "",
        issue.message,
    )


def _matches_logical_type(value: object, schema_field: DatasetSchemaField) -> bool:
    logical_type = schema_field.logical_type
    if logical_type == "utf8":
        return type(value) is str
    if logical_type == "float64":
        return _optional_float(value) is not None
    if logical_type == "int64":
        return type(value) is int and not isinstance(value, bool)
    if logical_type == "bool":
        return type(value) is bool
    if logical_type == "date32[day]":
        return _optional_date(value) is not None
    if logical_type == "timestamp[us, tz=UTC]":
        return _optional_datetime(value) is not None
    if logical_type == "list<utf8>":
        return isinstance(value, Sequence) and not isinstance(value, (str, bytes)) and all(
            type(item) is str for item in value
        )
    if logical_type.startswith("list<struct<"):
        return isinstance(value, Sequence) and not isinstance(value, (str, bytes))
    return True


def _optional_float(value: object) -> float | None:
    if _is_missing(value) or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    return number


def _non_negative_float(field_name: str, value: object) -> float:
    number = _optional_float(value)
    if number is None or number < 0:
        raise DataQualityRuleError(f"{field_name} must be a non-negative number")
    return number


def _positive_float(field_name: str, value: object) -> float:
    number = _optional_float(value)
    if number is None or number <= 0:
        raise DataQualityRuleError(f"{field_name} must be a positive number")
    return number


def _optional_date(value: object) -> date | None:
    if type(value) is date:
        return value
    if type(value) is str:
        try:
            return date.fromisoformat(value.strip())
        except ValueError:
            return None
    return None


def _coerce_date(value: object) -> date:
    parsed = _optional_date(value)
    if parsed is None:
        raise DataQualityRuleError(f"date is invalid: {value!r}")
    return parsed


def _optional_datetime(value: object) -> datetime | None:
    if type(value) is datetime and value.tzinfo is not None and value.utcoffset() is not None:
        return value
    if type(value) is str:
        try:
            parsed = datetime.fromisoformat(value.strip())
        except ValueError:
            return None
        return parsed if parsed.tzinfo is not None and parsed.utcoffset() is not None else None
    return None


def _is_missing(value: object) -> bool:
    return value is None or value == ""


def _json_safe(value: object) -> object:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Mapping):
        return _json_safe_mapping(value)
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_json_safe(item) for item in value]
    if isinstance(value, float) and not math.isfinite(value):
        return str(value)
    return value


def _json_safe_mapping(value: Mapping[str, object]) -> dict[str, object]:
    return {str(key): _json_safe(item) for key, item in sorted(value.items(), key=lambda entry: str(entry[0]))}


def _freeze_string_mapping(value: Mapping[str, str]) -> Mapping[str, str]:
    return MappingProxyType(
        {
            _required_string("mapping key", key): _stringify(item)
            for key, item in sorted(value.items(), key=lambda entry: str(entry[0]))
        }
    )


def _required_string(field_name: str, value: object | None) -> str:
    if type(value) is not str:
        raise DataQualityRuleError(f"{field_name} is required")
    normalized = value.strip()
    if not normalized:
        raise DataQualityRuleError(f"{field_name} is required")
    return normalized


def _optional_string(value: object | None) -> str | None:
    if value is None:
        return None
    if type(value) is not str:
        raise DataQualityRuleError("optional string value must be a string")
    normalized = value.strip()
    return normalized or None


def _stringify(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return str(value)


def _require_aware_datetime(field_name: str, value: object) -> None:
    if type(value) is not datetime or value.tzinfo is None or value.utcoffset() is None:
        raise DataQualityRuleError(f"{field_name} must be timezone-aware")


__all__ = [
    "AdjustmentFactorJumpRule",
    "DataQualityEngine",
    "DataQualityIssue",
    "DataQualityReport",
    "DataQualityRule",
    "DataQualityRuleError",
    "DataQualitySeverity",
    "DataQualityStatus",
    "NonNegativeFieldRule",
    "NullRatioDriftRule",
    "OhlcRelationshipRule",
    "QualityDatasetSnapshot",
    "ReturnOutlierRule",
    "SchemaFieldRule",
    "TradingContinuityRule",
    "UniquePrimaryKeyRule",
    "VolumeSpikeRule",
]
