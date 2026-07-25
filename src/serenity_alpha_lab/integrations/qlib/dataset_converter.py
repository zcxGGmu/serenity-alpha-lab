from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import StrEnum
from types import MappingProxyType
from typing import Any

from serenity_alpha_lab.datasets.catalog import DatasetVersionManifest
from serenity_alpha_lab.datasets.corporate_actions import (
    ADJUSTED_DAILY_BARS_SCHEMA_NAME,
    ADJUSTED_DAILY_BARS_SCHEMA_VERSION,
    AdjustmentMode,
    AdjustedDailyBar,
    AdjustedDailyBarsDataset,
)
from serenity_alpha_lab.datasets.instrument_master import (
    INSTRUMENT_MASTER_SCHEMA_NAME,
    INSTRUMENT_MASTER_SCHEMA_VERSION,
    InstrumentMasterDataset,
)
from serenity_alpha_lab.datasets.trading_calendar import (
    TRADING_CALENDAR_SCHEMA_NAME,
    TRADING_CALENDAR_SCHEMA_VERSION,
    TradingCalendarDataset,
)
from serenity_alpha_lab.domain.artifacts import ArtifactManifest, ArtifactRetentionTier, ArtifactStore
from serenity_alpha_lab.domain.instruments import Exchange, InstrumentId, Market


QLIB_DATASET_CONVERSION_SCHEMA_NAME = "integration.qlib.dataset_conversion"
QLIB_DATASET_CONVERSION_SCHEMA_VERSION = "1.0.0"
QLIB_DATASET_CONVERSION_CONTENT_TYPE = "application/vnd.serenity.integration.qlib.dataset-conversion+json"

QLIB_CALENDAR_SCHEMA_NAME = "integration.qlib.calendar"
QLIB_CALENDAR_SCHEMA_VERSION = "1.0.0"
QLIB_CALENDAR_CONTENT_TYPE = "text/plain; charset=utf-8"

QLIB_INSTRUMENT_SCHEMA_NAME = "integration.qlib.instrument"
QLIB_INSTRUMENT_SCHEMA_VERSION = "1.0.0"
QLIB_INSTRUMENT_CONTENT_TYPE = "text/plain; charset=utf-8"

QLIB_FEATURE_SCHEMA_NAME = "integration.qlib.feature"
QLIB_FEATURE_SCHEMA_VERSION = "1.0.0"
QLIB_FEATURE_CONTENT_TYPE = "application/vnd.serenity.integration.qlib.feature+json"

QLIB_FIELD_MAPPING_SCHEMA_NAME = "integration.qlib.field_mapping"
QLIB_FIELD_MAPPING_SCHEMA_VERSION = "1.0.0"
QLIB_FIELD_MAPPING_CONTENT_TYPE = "application/vnd.serenity.integration.qlib.field-mapping+json"

QLIB_DATASET_KEYS = ("trading_calendar", "instrument_master", "adjusted_daily_bars")

_EXPECTED_MANIFEST_SCHEMAS: Mapping[str, tuple[str, str]] = MappingProxyType(
    {
        "trading_calendar": (TRADING_CALENDAR_SCHEMA_NAME, TRADING_CALENDAR_SCHEMA_VERSION),
        "instrument_master": (INSTRUMENT_MASTER_SCHEMA_NAME, INSTRUMENT_MASTER_SCHEMA_VERSION),
        "adjusted_daily_bars": (ADJUSTED_DAILY_BARS_SCHEMA_NAME, ADJUSTED_DAILY_BARS_SCHEMA_VERSION),
    }
)

_FEATURE_FIELD_MAP: Mapping[str, str] = MappingProxyType(
    {
        "open": "$open",
        "high": "$high",
        "low": "$low",
        "close": "$close",
        "volume": "$volume",
        "amount": "$amount",
        "adjustment_factor": "$factor",
    }
)


class QlibDatasetConversionError(ValueError):
    """Raised when platform Dataset inputs cannot be converted to Qlib artifacts."""


class QlibFieldMappingDirection(StrEnum):
    PLATFORM_TO_QLIB = "platform_to_qlib"
    QLIB_TO_PLATFORM = "qlib_to_platform"


@dataclass(frozen=True, slots=True)
class QlibDatasetConversionSpec:
    market: Market | str
    start: date
    end: date
    dataset_manifests: Mapping[str, DatasetVersionManifest]
    created_at: datetime
    run_id: str
    stage_id: str
    provider_id: str | None = None
    adjustment: AdjustmentMode | str = AdjustmentMode.BACKWARD
    trace_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "market", _coerce_market(self.market))
        _require_date("start", self.start)
        _require_date("end", self.end)
        if self.end < self.start:
            raise QlibDatasetConversionError("end must be on or after start")
        _require_aware_datetime("created_at", self.created_at)
        object.__setattr__(self, "run_id", _required_string("run_id", self.run_id))
        object.__setattr__(self, "stage_id", _required_string("stage_id", self.stage_id))
        object.__setattr__(self, "provider_id", _optional_string(self.provider_id))
        object.__setattr__(self, "trace_id", _optional_string(self.trace_id))
        object.__setattr__(self, "adjustment", AdjustmentMode(self.adjustment))

        manifests: dict[str, DatasetVersionManifest] = {}
        for key in QLIB_DATASET_KEYS:
            try:
                manifest = self.dataset_manifests[key]
            except KeyError as exc:
                raise QlibDatasetConversionError(f"dataset manifest is required: {key}") from exc
            manifests[key] = _validate_dataset_manifest(key, manifest)
        object.__setattr__(self, "dataset_manifests", MappingProxyType(manifests))

    @property
    def source_dataset_versions(self) -> dict[str, str]:
        return {key: manifest.version_id for key, manifest in self.dataset_manifests.items()}

    @property
    def source_dataset_hashes(self) -> dict[str, list[str]]:
        return {key: list(manifest.file_hashes) for key, manifest in self.dataset_manifests.items()}


@dataclass(frozen=True, slots=True)
class QlibInstrumentRecord:
    qlib_symbol: str
    instrument_id: str
    market: str
    exchange: str
    name: str
    start_date: date
    end_date: date

    def __post_init__(self) -> None:
        object.__setattr__(self, "qlib_symbol", _required_string("qlib_symbol", self.qlib_symbol))
        object.__setattr__(self, "instrument_id", _required_string("instrument_id", self.instrument_id))
        object.__setattr__(self, "market", _required_string("market", self.market))
        object.__setattr__(self, "exchange", _required_string("exchange", self.exchange))
        object.__setattr__(self, "name", _required_string("name", self.name))
        _require_date("start_date", self.start_date)
        _require_date("end_date", self.end_date)
        if self.end_date < self.start_date:
            raise QlibDatasetConversionError("instrument end_date must be on or after start_date")

    def to_record(self) -> dict[str, object]:
        return {
            "qlib_symbol": self.qlib_symbol,
            "instrument_id": self.instrument_id,
            "market": self.market,
            "exchange": self.exchange,
            "name": self.name,
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
        }


@dataclass(frozen=True, slots=True)
class QlibFeatureRecord:
    qlib_symbol: str
    instrument_id: str
    trade_date: date
    values: Mapping[str, float]
    lineage: Mapping[str, Mapping[str, str]]

    def __post_init__(self) -> None:
        object.__setattr__(self, "qlib_symbol", _required_string("qlib_symbol", self.qlib_symbol))
        object.__setattr__(self, "instrument_id", _required_string("instrument_id", self.instrument_id))
        _require_date("trade_date", self.trade_date)

        values: dict[str, float] = {}
        for field_name, value in self.values.items():
            normalized_field = _required_string("qlib feature field", field_name)
            if normalized_field not in set(_FEATURE_FIELD_MAP.values()):
                raise QlibDatasetConversionError(f"Unsupported Qlib feature field: {normalized_field}")
            values[normalized_field] = _required_number(normalized_field, value)
        object.__setattr__(self, "values", MappingProxyType(dict(sorted(values.items()))))

        lineage: dict[str, Mapping[str, str]] = {}
        for qlib_field, details in self.lineage.items():
            normalized_field = _required_string("lineage qlib field", qlib_field)
            if normalized_field not in values:
                raise QlibDatasetConversionError("feature lineage must match feature values")
            lineage[normalized_field] = MappingProxyType(
                {
                    _required_string("lineage key", key): _required_string("lineage value", value)
                    for key, value in details.items()
                }
            )
        object.__setattr__(self, "lineage", MappingProxyType(lineage))

    def to_record(self) -> dict[str, object]:
        return {
            "qlib_symbol": self.qlib_symbol,
            "instrument_id": self.instrument_id,
            "trade_date": self.trade_date.isoformat(),
            "values": dict(self.values),
            "lineage": {key: dict(value) for key, value in self.lineage.items()},
        }


@dataclass(frozen=True, slots=True)
class QlibFieldMapping:
    direction: QlibFieldMappingDirection | str
    platform_dataset_key: str
    platform_schema_name: str
    platform_field: str
    qlib_artifact_kind: str
    qlib_field: str
    transform: str
    notes: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "direction", QlibFieldMappingDirection(self.direction))
        object.__setattr__(
            self,
            "platform_dataset_key",
            _required_string("platform_dataset_key", self.platform_dataset_key),
        )
        object.__setattr__(
            self,
            "platform_schema_name",
            _required_string("platform_schema_name", self.platform_schema_name),
        )
        object.__setattr__(self, "platform_field", _required_string("platform_field", self.platform_field))
        object.__setattr__(self, "qlib_artifact_kind", _required_string("qlib_artifact_kind", self.qlib_artifact_kind))
        object.__setattr__(self, "qlib_field", _required_string("qlib_field", self.qlib_field))
        object.__setattr__(self, "transform", _required_string("transform", self.transform))
        object.__setattr__(self, "notes", _required_string("notes", self.notes))

    def to_record(self) -> dict[str, str]:
        return {
            "direction": self.direction.value,
            "platform_dataset_key": self.platform_dataset_key,
            "platform_schema_name": self.platform_schema_name,
            "platform_field": self.platform_field,
            "qlib_artifact_kind": self.qlib_artifact_kind,
            "qlib_field": self.qlib_field,
            "transform": self.transform,
            "notes": self.notes,
        }


@dataclass(frozen=True, slots=True)
class QlibDatasetConversionArtifacts:
    calendar: ArtifactManifest
    instruments: ArtifactManifest
    features: ArtifactManifest
    field_mapping: ArtifactManifest
    summary: ArtifactManifest


@dataclass(frozen=True, slots=True)
class QlibConvertedDatasetBundle:
    market: Market
    start: date
    end: date
    created_at: datetime
    run_id: str
    stage_id: str
    source_dataset_versions: Mapping[str, str]
    source_dataset_hashes: Mapping[str, Sequence[str]]
    calendar: Sequence[str]
    instruments: Sequence[QlibInstrumentRecord]
    features: Sequence[QlibFeatureRecord]
    field_mappings: Sequence[QlibFieldMapping]
    trace_id: str | None = None
    warnings: Sequence[Mapping[str, str]] = ()
    conversion_id: str = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "market", _coerce_market(self.market))
        _require_date("start", self.start)
        _require_date("end", self.end)
        if self.end < self.start:
            raise QlibDatasetConversionError("end must be on or after start")
        _require_aware_datetime("created_at", self.created_at)
        object.__setattr__(self, "run_id", _required_string("run_id", self.run_id))
        object.__setattr__(self, "stage_id", _required_string("stage_id", self.stage_id))
        object.__setattr__(self, "trace_id", _optional_string(self.trace_id))

        source_versions = {
            _required_string("source dataset key", key): _required_string("source dataset version", value)
            for key, value in self.source_dataset_versions.items()
        }
        for key in QLIB_DATASET_KEYS:
            if key not in source_versions:
                raise QlibDatasetConversionError(f"source dataset version is required: {key}")
        object.__setattr__(self, "source_dataset_versions", MappingProxyType(dict(sorted(source_versions.items()))))

        source_hashes = {
            _required_string("source dataset key", key): tuple(
                _required_string("source dataset hash", value) for value in values
            )
            for key, values in self.source_dataset_hashes.items()
        }
        object.__setattr__(self, "source_dataset_hashes", MappingProxyType(dict(sorted(source_hashes.items()))))

        calendar = tuple(_required_string("calendar date", value) for value in self.calendar)
        if not calendar:
            raise QlibDatasetConversionError("calendar output cannot be empty")
        object.__setattr__(self, "calendar", calendar)

        instruments = tuple(self.instruments)
        if not instruments:
            raise QlibDatasetConversionError("instrument output cannot be empty")
        for instrument in instruments:
            if type(instrument) is not QlibInstrumentRecord:
                raise QlibDatasetConversionError("instruments must contain QlibInstrumentRecord values")
        object.__setattr__(self, "instruments", tuple(sorted(instruments, key=lambda item: item.qlib_symbol)))

        features = tuple(self.features)
        if not features:
            raise QlibDatasetConversionError("feature output cannot be empty")
        for feature in features:
            if type(feature) is not QlibFeatureRecord:
                raise QlibDatasetConversionError("features must contain QlibFeatureRecord values")
        object.__setattr__(
            self,
            "features",
            tuple(sorted(features, key=lambda item: (item.qlib_symbol, item.trade_date))),
        )

        field_mappings = tuple(self.field_mappings)
        if not field_mappings:
            raise QlibDatasetConversionError("field mappings are required")
        for mapping in field_mappings:
            if type(mapping) is not QlibFieldMapping:
                raise QlibDatasetConversionError("field_mappings must contain QlibFieldMapping values")
        object.__setattr__(
            self,
            "field_mappings",
            tuple(
                sorted(
                    field_mappings,
                    key=lambda item: (
                        item.direction.value,
                        item.platform_dataset_key,
                        item.platform_field,
                        item.qlib_field,
                    ),
                )
            ),
        )

        warnings = tuple(
            MappingProxyType(
                {
                    _required_string("warning key", key): _required_string("warning value", value)
                    for key, value in warning.items()
                }
            )
            for warning in self.warnings
        )
        object.__setattr__(self, "warnings", warnings)
        object.__setattr__(self, "conversion_id", _derive_conversion_id(self))

    def calendar_bytes(self) -> bytes:
        return ("".join(f"{line}\n" for line in self.calendar)).encode("utf-8")

    def instruments_bytes(self) -> bytes:
        lines = [
            f"{record.qlib_symbol}\t{record.start_date.isoformat()}\t{record.end_date.isoformat()}"
            for record in self.instruments
        ]
        return ("".join(f"{line}\n" for line in lines)).encode("utf-8")

    def features_bytes(self) -> bytes:
        return _canonical_json_bytes(
            {
                "schema_name": QLIB_FEATURE_SCHEMA_NAME,
                "schema_version": QLIB_FEATURE_SCHEMA_VERSION,
                "conversion_id": self.conversion_id,
                "market": self.market.value,
                "source_dataset_versions": dict(self.source_dataset_versions),
                "records": [record.to_record() for record in self.features],
            }
        )

    def field_mapping_bytes(self) -> bytes:
        return _canonical_json_bytes(
            {
                "schema_name": QLIB_FIELD_MAPPING_SCHEMA_NAME,
                "schema_version": QLIB_FIELD_MAPPING_SCHEMA_VERSION,
                "conversion_id": self.conversion_id,
                "source_dataset_versions": dict(self.source_dataset_versions),
                "records": [record.to_record() for record in self.field_mappings],
            }
        )

    def summary_bytes(self, *, artifacts: Mapping[str, ArtifactManifest] | None = None) -> bytes:
        return _canonical_json_bytes(self.to_summary_record(artifacts=artifacts))

    def to_summary_record(self, *, artifacts: Mapping[str, ArtifactManifest] | None = None) -> dict[str, object]:
        artifact_records: dict[str, object] = {}
        if artifacts:
            row_counts = {
                "calendar": len(self.calendar),
                "instruments": len(self.instruments),
                "features": len(self.features),
                "field_mapping": len(self.field_mappings),
            }
            for key, manifest in sorted(artifacts.items()):
                artifact_records[key] = {
                    "artifact_id": manifest.artifact_id,
                    "uri": str(manifest.uri),
                    "sha256": manifest.sha256,
                    "schema_name": manifest.schema_name,
                    "schema_version": manifest.schema_version,
                    "content_type": manifest.content_type,
                    "row_count": row_counts[key],
                }
        return {
            "schema_name": QLIB_DATASET_CONVERSION_SCHEMA_NAME,
            "schema_version": QLIB_DATASET_CONVERSION_SCHEMA_VERSION,
            "conversion_id": self.conversion_id,
            "market": self.market.value,
            "start": self.start.isoformat(),
            "end": self.end.isoformat(),
            "created_at": self.created_at.isoformat(),
            "trace_id": self.trace_id,
            "run_id": self.run_id,
            "stage_id": self.stage_id,
            "source_dataset_versions": dict(self.source_dataset_versions),
            "source_dataset_hashes": {key: list(value) for key, value in self.source_dataset_hashes.items()},
            "calendar_count": len(self.calendar),
            "instrument_count": len(self.instruments),
            "feature_count": len(self.features),
            "field_mapping_count": len(self.field_mappings),
            "warnings": [dict(warning) for warning in self.warnings],
            "artifacts": artifact_records,
            "runtime": {
                "qlib_runtime_started": False,
                "formal_backtest_started": False,
            },
        }

    def publish(
        self,
        artifact_store: ArtifactStore,
        *,
        retention_tier: ArtifactRetentionTier = ArtifactRetentionTier.STANDARD,
    ) -> QlibDatasetConversionArtifacts:
        calendar = artifact_store.put_bytes(
            self.calendar_bytes(),
            schema_name=QLIB_CALENDAR_SCHEMA_NAME,
            schema_version=QLIB_CALENDAR_SCHEMA_VERSION,
            content_type=QLIB_CALENDAR_CONTENT_TYPE,
            produced_by_run_id=self.run_id,
            produced_by_stage_id=self.stage_id,
            retention_tier=retention_tier,
            created_at=self.created_at,
        )
        instruments = artifact_store.put_bytes(
            self.instruments_bytes(),
            schema_name=QLIB_INSTRUMENT_SCHEMA_NAME,
            schema_version=QLIB_INSTRUMENT_SCHEMA_VERSION,
            content_type=QLIB_INSTRUMENT_CONTENT_TYPE,
            produced_by_run_id=self.run_id,
            produced_by_stage_id=self.stage_id,
            retention_tier=retention_tier,
            created_at=self.created_at,
        )
        features = artifact_store.put_bytes(
            self.features_bytes(),
            schema_name=QLIB_FEATURE_SCHEMA_NAME,
            schema_version=QLIB_FEATURE_SCHEMA_VERSION,
            content_type=QLIB_FEATURE_CONTENT_TYPE,
            produced_by_run_id=self.run_id,
            produced_by_stage_id=self.stage_id,
            retention_tier=retention_tier,
            created_at=self.created_at,
        )
        field_mapping = artifact_store.put_bytes(
            self.field_mapping_bytes(),
            schema_name=QLIB_FIELD_MAPPING_SCHEMA_NAME,
            schema_version=QLIB_FIELD_MAPPING_SCHEMA_VERSION,
            content_type=QLIB_FIELD_MAPPING_CONTENT_TYPE,
            produced_by_run_id=self.run_id,
            produced_by_stage_id=self.stage_id,
            retention_tier=retention_tier,
            created_at=self.created_at,
        )
        summary = artifact_store.put_bytes(
            self.summary_bytes(
                artifacts={
                    "calendar": calendar,
                    "instruments": instruments,
                    "features": features,
                    "field_mapping": field_mapping,
                }
            ),
            schema_name=QLIB_DATASET_CONVERSION_SCHEMA_NAME,
            schema_version=QLIB_DATASET_CONVERSION_SCHEMA_VERSION,
            content_type=QLIB_DATASET_CONVERSION_CONTENT_TYPE,
            produced_by_run_id=self.run_id,
            produced_by_stage_id=self.stage_id,
            retention_tier=retention_tier,
            created_at=self.created_at,
        )
        return QlibDatasetConversionArtifacts(
            calendar=calendar,
            instruments=instruments,
            features=features,
            field_mapping=field_mapping,
            summary=summary,
        )


def convert_datasets_to_qlib(
    spec: QlibDatasetConversionSpec,
    *,
    trading_calendar: TradingCalendarDataset,
    instrument_master: InstrumentMasterDataset,
    adjusted_daily_bars: AdjustedDailyBarsDataset,
) -> QlibConvertedDatasetBundle:
    if type(spec) is not QlibDatasetConversionSpec:
        raise QlibDatasetConversionError("spec must be a QlibDatasetConversionSpec")
    if type(trading_calendar) is not TradingCalendarDataset:
        raise QlibDatasetConversionError("trading_calendar must be a TradingCalendarDataset")
    if type(instrument_master) is not InstrumentMasterDataset:
        raise QlibDatasetConversionError("instrument_master must be an InstrumentMasterDataset")
    if type(adjusted_daily_bars) is not AdjustedDailyBarsDataset:
        raise QlibDatasetConversionError("adjusted_daily_bars must be an AdjustedDailyBarsDataset")

    calendar_days = trading_calendar.trading_days(spec.market, spec.start, spec.end)
    if not calendar_days:
        raise QlibDatasetConversionError("calendar conversion requires at least one trading day")
    calendar_set = set(calendar_days)
    filtered_bars = tuple(
        bar
        for bar in adjusted_daily_bars.records
        if bar.market is spec.market
        and spec.start <= bar.trade_date <= spec.end
        and bar.trade_date in calendar_set
        and bar.adjustment is spec.adjustment
        and (spec.provider_id is None or bar.provider_id == spec.provider_id)
    )
    if not filtered_bars:
        raise QlibDatasetConversionError("feature conversion requires adjusted daily bars")

    qlib_symbols = {_bar_key(bar.instrument_id): _qlib_symbol_for(bar.instrument_id) for bar in filtered_bars}
    instrument_records = _build_instruments(
        instrument_master,
        filtered_bars=filtered_bars,
        qlib_symbols=qlib_symbols,
    )
    feature_records = tuple(_feature_record_from_bar(bar, qlib_symbol=qlib_symbols[bar.instrument_id.canonical]) for bar in filtered_bars)
    warnings = _missing_feature_warnings(instrument_records, feature_records, calendar_days)
    field_mappings = _default_field_mappings()

    return QlibConvertedDatasetBundle(
        market=spec.market,
        start=spec.start,
        end=spec.end,
        created_at=spec.created_at,
        trace_id=spec.trace_id,
        run_id=spec.run_id,
        stage_id=spec.stage_id,
        source_dataset_versions=spec.source_dataset_versions,
        source_dataset_hashes=spec.source_dataset_hashes,
        calendar=tuple(day.isoformat() for day in calendar_days),
        instruments=instrument_records,
        features=feature_records,
        field_mappings=field_mappings,
        warnings=warnings,
    )


def _build_instruments(
    instrument_master: InstrumentMasterDataset,
    *,
    filtered_bars: Sequence[AdjustedDailyBar],
    qlib_symbols: Mapping[str, str],
) -> tuple[QlibInstrumentRecord, ...]:
    bars_by_instrument: dict[str, list[AdjustedDailyBar]] = {}
    for bar in filtered_bars:
        bars_by_instrument.setdefault(bar.instrument_id.canonical, []).append(bar)

    records: list[QlibInstrumentRecord] = []
    for canonical, bars in sorted(bars_by_instrument.items(), key=lambda item: qlib_symbols[item[0]]):
        instrument = InstrumentId.parse(canonical)
        dates = tuple(sorted(bar.trade_date for bar in bars))
        master_record = instrument_master.get(instrument, as_of=dates[-1])
        records.append(
            QlibInstrumentRecord(
                qlib_symbol=qlib_symbols[canonical],
                instrument_id=canonical,
                market=instrument.market.value,
                exchange=instrument.exchange.value,
                name=master_record.name,
                start_date=dates[0],
                end_date=dates[-1],
            )
        )
    return tuple(records)


def _feature_record_from_bar(bar: AdjustedDailyBar, *, qlib_symbol: str) -> QlibFeatureRecord:
    values: dict[str, float] = {}
    lineage: dict[str, Mapping[str, str]] = {}
    for platform_field, qlib_field in _FEATURE_FIELD_MAP.items():
        values[qlib_field] = float(getattr(bar, platform_field))
        lineage[qlib_field] = {
            "platform_dataset_key": "adjusted_daily_bars",
            "platform_schema_name": ADJUSTED_DAILY_BARS_SCHEMA_NAME,
            "platform_field": platform_field,
            "source": bar.field_lineage.get(platform_field, f"{ADJUSTED_DAILY_BARS_SCHEMA_NAME}.{platform_field}"),
        }
    return QlibFeatureRecord(
        qlib_symbol=qlib_symbol,
        instrument_id=bar.instrument_id.canonical,
        trade_date=bar.trade_date,
        values=values,
        lineage=lineage,
    )


def _missing_feature_warnings(
    instrument_records: Sequence[QlibInstrumentRecord],
    feature_records: Sequence[QlibFeatureRecord],
    calendar_days: Sequence[date],
) -> tuple[Mapping[str, str], ...]:
    feature_keys = {(record.qlib_symbol, record.trade_date) for record in feature_records}
    warnings: list[Mapping[str, str]] = []
    for instrument in instrument_records:
        for trade_date in calendar_days:
            if instrument.start_date <= trade_date <= instrument.end_date and (instrument.qlib_symbol, trade_date) not in feature_keys:
                warnings.append(
                    MappingProxyType(
                        {
                            "code": "missing_feature_bar",
                            "qlib_symbol": instrument.qlib_symbol,
                            "trade_date": trade_date.isoformat(),
                        }
                    )
                )
    return tuple(warnings)


def _default_field_mappings() -> tuple[QlibFieldMapping, ...]:
    mappings: list[QlibFieldMapping] = [
        QlibFieldMapping(
            direction=QlibFieldMappingDirection.PLATFORM_TO_QLIB,
            platform_dataset_key="instrument_master",
            platform_schema_name=INSTRUMENT_MASTER_SCHEMA_NAME,
            platform_field="instrument_id",
            qlib_artifact_kind="instrument",
            qlib_field="qlib_symbol",
            transform="CN exchange prefix mapping: XSHG->SH, XSHE->SZ, XBSE->BJ",
            notes="Qlib symbols are derived from platform canonical InstrumentId without changing platform identity.",
        ),
        QlibFieldMapping(
            direction=QlibFieldMappingDirection.QLIB_TO_PLATFORM,
            platform_dataset_key="instrument_master",
            platform_schema_name=INSTRUMENT_MASTER_SCHEMA_NAME,
            platform_field="instrument_id",
            qlib_artifact_kind="instrument",
            qlib_field="qlib_symbol",
            transform="Reverse lookup through conversion manifest",
            notes="The summary artifact retains qlib_symbol to platform instrument_id lineage.",
        ),
        QlibFieldMapping(
            direction=QlibFieldMappingDirection.PLATFORM_TO_QLIB,
            platform_dataset_key="trading_calendar",
            platform_schema_name=TRADING_CALENDAR_SCHEMA_NAME,
            platform_field="trade_date",
            qlib_artifact_kind="calendar",
            qlib_field="calendar",
            transform="ISO date line for trading sessions only",
            notes="Closed sessions are omitted; timezone and session metadata stay in source Dataset lineage.",
        ),
        QlibFieldMapping(
            direction=QlibFieldMappingDirection.QLIB_TO_PLATFORM,
            platform_dataset_key="trading_calendar",
            platform_schema_name=TRADING_CALENDAR_SCHEMA_NAME,
            platform_field="trade_date",
            qlib_artifact_kind="calendar",
            qlib_field="calendar",
            transform="ISO date line parsed as platform trade_date",
            notes="Qlib calendar dates resolve back to the source trading_calendar Dataset Version.",
        ),
    ]
    for platform_field, qlib_field in _FEATURE_FIELD_MAP.items():
        mappings.append(
            QlibFieldMapping(
                direction=QlibFieldMappingDirection.PLATFORM_TO_QLIB,
                platform_dataset_key="adjusted_daily_bars",
                platform_schema_name=ADJUSTED_DAILY_BARS_SCHEMA_NAME,
                platform_field=platform_field,
                qlib_artifact_kind="feature",
                qlib_field=qlib_field,
                transform="identity numeric mapping",
                notes="Adjusted bar values are not filled or rescaled during Qlib conversion.",
            )
        )
        mappings.append(
            QlibFieldMapping(
                direction=QlibFieldMappingDirection.QLIB_TO_PLATFORM,
                platform_dataset_key="adjusted_daily_bars",
                platform_schema_name=ADJUSTED_DAILY_BARS_SCHEMA_NAME,
                platform_field=platform_field,
                qlib_artifact_kind="feature",
                qlib_field=qlib_field,
                transform="reverse identity mapping",
                notes="Qlib feature values resolve back to adjusted_daily_bars fields and per-row lineage.",
            )
        )
    return tuple(mappings)


def _validate_dataset_manifest(key: str, manifest: DatasetVersionManifest) -> DatasetVersionManifest:
    if type(manifest) is not DatasetVersionManifest:
        raise QlibDatasetConversionError(f"{key} manifest must be a DatasetVersionManifest")
    expected_schema, expected_version = _EXPECTED_MANIFEST_SCHEMAS[key]
    if manifest.schema_name != expected_schema or manifest.schema_version != expected_version:
        raise QlibDatasetConversionError(f"{key} manifest must use {expected_schema}@{expected_version}")
    if manifest.metadata.get("quality_status") != "passed" or manifest.metadata.get("publication_status") != "published":
        raise QlibDatasetConversionError(f"{key} Dataset Version must be passed and published before Qlib conversion")
    return manifest


def _derive_conversion_id(bundle: QlibConvertedDatasetBundle) -> str:
    record = {
        "market": bundle.market.value,
        "start": bundle.start.isoformat(),
        "end": bundle.end.isoformat(),
        "source_dataset_versions": dict(bundle.source_dataset_versions),
        "calendar": list(bundle.calendar),
        "instruments": [record.to_record() for record in bundle.instruments],
        "features": [record.to_record() for record in bundle.features],
        "field_mappings": [record.to_record() for record in bundle.field_mappings],
        "warnings": [dict(warning) for warning in bundle.warnings],
    }
    return f"qdc_{hashlib.sha256(_canonical_json_bytes(record)).hexdigest()[:32]}"


def _qlib_symbol_for(instrument_id: InstrumentId) -> str:
    if instrument_id.exchange is Exchange.XSHG:
        return f"SH{instrument_id.symbol}"
    if instrument_id.exchange is Exchange.XSHE:
        return f"SZ{instrument_id.symbol}"
    if instrument_id.exchange is Exchange.XBSE:
        return f"BJ{instrument_id.symbol}"
    return instrument_id.canonical.replace(".", "_")


def _bar_key(instrument_id: InstrumentId) -> str:
    return instrument_id.canonical


def _canonical_json_bytes(record: Mapping[str, Any]) -> bytes:
    return json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _coerce_market(value: Market | str) -> Market:
    try:
        return Market(value)
    except ValueError as exc:
        raise QlibDatasetConversionError(f"Unsupported market: {value}") from exc


def _require_date(field_name: str, value: object) -> None:
    if type(value) is not date:
        raise QlibDatasetConversionError(f"{field_name} must be a date")


def _require_aware_datetime(field_name: str, value: object) -> None:
    if type(value) is not datetime or value.tzinfo is None or value.utcoffset() is None:
        raise QlibDatasetConversionError(f"{field_name} must be timezone-aware")


def _required_string(field_name: str, value: object | None) -> str:
    if type(value) is not str:
        raise QlibDatasetConversionError(f"{field_name} is required")
    normalized = value.strip()
    if not normalized:
        raise QlibDatasetConversionError(f"{field_name} is required")
    return normalized


def _optional_string(value: object | None) -> str | None:
    if value is None:
        return None
    if type(value) is not str:
        raise QlibDatasetConversionError("optional string value must be a string")
    normalized = value.strip()
    return normalized or None


def _required_number(field_name: str, value: object) -> float:
    if type(value) not in {int, float}:
        raise QlibDatasetConversionError(f"{field_name} must be numeric")
    converted = float(value)
    if converted != converted or converted in {float("inf"), float("-inf")}:
        raise QlibDatasetConversionError(f"{field_name} must be finite")
    return converted


__all__ = [
    "QLIB_CALENDAR_CONTENT_TYPE",
    "QLIB_CALENDAR_SCHEMA_NAME",
    "QLIB_CALENDAR_SCHEMA_VERSION",
    "QLIB_DATASET_CONVERSION_CONTENT_TYPE",
    "QLIB_DATASET_CONVERSION_SCHEMA_NAME",
    "QLIB_DATASET_CONVERSION_SCHEMA_VERSION",
    "QLIB_FEATURE_CONTENT_TYPE",
    "QLIB_FEATURE_SCHEMA_NAME",
    "QLIB_FEATURE_SCHEMA_VERSION",
    "QLIB_FIELD_MAPPING_CONTENT_TYPE",
    "QLIB_FIELD_MAPPING_SCHEMA_NAME",
    "QLIB_FIELD_MAPPING_SCHEMA_VERSION",
    "QLIB_INSTRUMENT_CONTENT_TYPE",
    "QLIB_INSTRUMENT_SCHEMA_NAME",
    "QLIB_INSTRUMENT_SCHEMA_VERSION",
    "QlibConvertedDatasetBundle",
    "QlibDatasetConversionArtifacts",
    "QlibDatasetConversionError",
    "QlibDatasetConversionSpec",
    "QlibFeatureRecord",
    "QlibFieldMapping",
    "QlibFieldMappingDirection",
    "QlibInstrumentRecord",
    "convert_datasets_to_qlib",
]
