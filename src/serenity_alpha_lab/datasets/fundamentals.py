from __future__ import annotations

import json
import math
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import StrEnum
from types import MappingProxyType

from serenity_alpha_lab.datasets.instrument_master import InstrumentMasterDataset
from serenity_alpha_lab.domain.artifacts import (
    ArtifactManifest,
    ArtifactRetentionTier,
    ArtifactStore,
    ArtifactUri,
)
from serenity_alpha_lab.domain.instruments import InstrumentId, Market
from serenity_alpha_lab.domain.providers import DataBatch, ProviderCapability


FUNDAMENTALS_SCHEMA_NAME = "dataset.fundamentals"
FUNDAMENTALS_SCHEMA_VERSION = "1.0.0"
FUNDAMENTALS_CONTENT_TYPE = "application/vnd.serenity.dataset.fundamentals+json"
FUNDAMENTALS_PARTITION_KEYS = ("market", "period_year")
FUNDAMENTALS_FIELD_SCHEMA: Mapping[str, str] = MappingProxyType(
    {
        "instrument_id": "utf8",
        "market": "utf8",
        "exchange": "utf8",
        "period_end": "date32[day]",
        "period_type": "utf8",
        "item": "utf8",
        "value": "float64",
        "unit": "utf8",
        "currency": "utf8",
        "accounting_standard": "utf8",
        "fiscal_year": "int64",
        "fiscal_quarter": "int64",
        "provider_id": "utf8",
        "provider_source": "utf8",
        "announced_at": "timestamp[us, tz=UTC]",
        "available_at": "timestamp[us, tz=UTC]",
        "ingested_at": "timestamp[us, tz=UTC]",
        "revision": "int64",
        "temporal_confidence": "utf8",
        "provider_source_timestamp": "timestamp[us, tz=UTC]",
        "provider_raw_response_sha256": "utf8",
        "source_bronze_artifact_id": "utf8",
    }
)


class FundamentalsDatasetError(ValueError):
    """Raised when point-in-time fundamental records violate the Dataset contract."""


class FundamentalPeriodType(StrEnum):
    ANNUAL = "annual"
    QUARTERLY = "quarterly"
    TTM = "ttm"
    SNAPSHOT = "snapshot"


class FundamentalQueryPurpose(StrEnum):
    FORMAL_BACKTEST = "formal_backtest"
    RESEARCH_DISPLAY = "research_display"


class TemporalConfidence(StrEnum):
    EXACT = "exact"
    ESTIMATED = "estimated"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class FundamentalRecord:
    instrument_id: InstrumentId
    period_end: date
    period_type: FundamentalPeriodType | str
    item: str
    value: float
    revision: int
    provider_id: str
    announced_at: datetime | None
    available_at: datetime
    ingested_at: datetime
    provider_source: str
    provider_source_timestamp: datetime | None
    provider_raw_response_sha256: str
    field_lineage: Mapping[str, str]
    source_bronze_artifact_id: str
    unit: str | None = None
    currency: str | None = None
    accounting_standard: str | None = None
    fiscal_year: int | None = None
    fiscal_quarter: int | None = None
    temporal_confidence: TemporalConfidence | str = TemporalConfidence.EXACT

    def __post_init__(self) -> None:
        if type(self.instrument_id) is not InstrumentId:
            raise FundamentalsDatasetError("instrument_id must be an InstrumentId")
        _require_date("period_end", self.period_end)
        object.__setattr__(self, "period_type", FundamentalPeriodType(self.period_type))
        object.__setattr__(self, "item", _required_string("item", self.item).lower())
        object.__setattr__(self, "value", _required_number("value", self.value))
        object.__setattr__(self, "revision", _required_positive_int("revision", self.revision))
        object.__setattr__(self, "provider_id", _required_string("provider_id", self.provider_id))
        object.__setattr__(self, "provider_source", _required_string("provider_source", self.provider_source))
        object.__setattr__(self, "unit", _optional_string(self.unit))
        object.__setattr__(self, "currency", _optional_upper_string(self.currency))
        object.__setattr__(self, "accounting_standard", _optional_string(self.accounting_standard))
        object.__setattr__(self, "temporal_confidence", TemporalConfidence(self.temporal_confidence))
        object.__setattr__(
            self,
            "provider_raw_response_sha256",
            ArtifactUri.for_sha256(self.provider_raw_response_sha256).digest,
        )
        object.__setattr__(
            self,
            "source_bronze_artifact_id",
            _required_string("source_bronze_artifact_id", self.source_bronze_artifact_id),
        )

        if self.announced_at is not None:
            _require_aware_datetime("announced_at", self.announced_at)
        _require_aware_datetime("available_at", self.available_at)
        _require_aware_datetime("ingested_at", self.ingested_at)
        if self.provider_source_timestamp is not None:
            _require_aware_datetime("provider_source_timestamp", self.provider_source_timestamp)

        fiscal_year = self.period_end.year if self.fiscal_year is None else _required_int("fiscal_year", self.fiscal_year)
        object.__setattr__(self, "fiscal_year", fiscal_year)
        if self.fiscal_quarter is not None:
            quarter = _required_int("fiscal_quarter", self.fiscal_quarter)
            if quarter not in {1, 2, 3, 4}:
                raise FundamentalsDatasetError("fiscal_quarter must be between 1 and 4")
            object.__setattr__(self, "fiscal_quarter", quarter)

        object.__setattr__(self, "field_lineage", _freeze_lineage(self.field_lineage))
        _validate_pit_timing(self)

    @property
    def market(self) -> Market:
        return self.instrument_id.market

    @property
    def primary_key(self) -> tuple[str, date, str, int, str]:
        return (self.instrument_id.canonical, self.period_end, self.item, self.revision, self.provider_id)

    @property
    def partition_values(self) -> dict[str, str]:
        return {
            "market": self.market.value,
            "period_year": f"{self.period_end.year:04d}",
        }

    @property
    def is_formal_backtest_eligible(self) -> bool:
        return self.temporal_confidence is not TemporalConfidence.UNKNOWN and self.announced_at is not None

    def to_record(self) -> dict[str, object]:
        return {
            "instrument_id": self.instrument_id.canonical,
            "market": self.market.value,
            "exchange": self.instrument_id.exchange.value,
            "symbol": self.instrument_id.symbol,
            "period_end": self.period_end.isoformat(),
            "period_type": self.period_type.value,
            "item": self.item,
            "value": self.value,
            "unit": self.unit,
            "currency": self.currency,
            "accounting_standard": self.accounting_standard,
            "fiscal_year": self.fiscal_year,
            "fiscal_quarter": self.fiscal_quarter,
            "provider_id": self.provider_id,
            "provider_source": self.provider_source,
            "announced_at": self.announced_at.isoformat() if self.announced_at else None,
            "available_at": self.available_at.isoformat(),
            "ingested_at": self.ingested_at.isoformat(),
            "revision": self.revision,
            "temporal_confidence": self.temporal_confidence.value,
            "provider_source_timestamp": (
                self.provider_source_timestamp.isoformat() if self.provider_source_timestamp else None
            ),
            "provider_raw_response_sha256": self.provider_raw_response_sha256,
            "field_lineage": dict(self.field_lineage),
            "source_bronze_artifact_id": self.source_bronze_artifact_id,
            "partition": self.partition_values,
        }


@dataclass(frozen=True, slots=True)
class FundamentalsDataset:
    records: Sequence[FundamentalRecord]
    created_at: datetime
    trace_id: str | None = None
    run_id: str | None = None
    stage_id: str | None = None
    _record_by_key: Mapping[tuple[str, date, str, int, str], FundamentalRecord] = field(
        init=False,
        repr=False,
        compare=False,
    )
    _records_by_instrument: Mapping[str, tuple[FundamentalRecord, ...]] = field(
        init=False,
        repr=False,
        compare=False,
    )

    @classmethod
    def from_provider_batch(
        cls,
        batch: DataBatch[Mapping[str, object]],
        *,
        instrument_master: InstrumentMasterDataset,
        source_bronze_artifact_id: str,
        created_at: datetime,
        trace_id: str | None = None,
        run_id: str | None = None,
        stage_id: str | None = None,
    ) -> FundamentalsDataset:
        if type(batch) is not DataBatch:
            raise FundamentalsDatasetError("batch must be a Provider DataBatch")
        if batch.provenance.operation != ProviderCapability.FUNDAMENTALS.value:
            raise FundamentalsDatasetError("Provider DataBatch operation must be fundamentals")
        source_artifact_id = _required_string("source_bronze_artifact_id", source_bronze_artifact_id)
        records = [
            _record_from_provider_row(
                record,
                batch=batch,
                instrument_master=instrument_master,
                source_bronze_artifact_id=source_artifact_id,
            )
            for record in batch.records
        ]
        return cls.from_records(
            records,
            created_at=created_at,
            trace_id=trace_id if trace_id is not None else batch.provenance.trace_id,
            run_id=run_id if run_id is not None else batch.provenance.run_id,
            stage_id=stage_id if stage_id is not None else batch.provenance.stage_id,
        )

    @classmethod
    def from_records(
        cls,
        records: Iterable[FundamentalRecord],
        *,
        created_at: datetime,
        trace_id: str | None = None,
        run_id: str | None = None,
        stage_id: str | None = None,
    ) -> FundamentalsDataset:
        return cls(
            records=tuple(records),
            created_at=created_at,
            trace_id=trace_id,
            run_id=run_id,
            stage_id=stage_id,
        )

    def __post_init__(self) -> None:
        _require_aware_datetime("created_at", self.created_at)
        object.__setattr__(self, "trace_id", _optional_string(self.trace_id))
        object.__setattr__(self, "run_id", _optional_string(self.run_id))
        object.__setattr__(self, "stage_id", _optional_string(self.stage_id))

        records = tuple(self.records)
        for record in records:
            if type(record) is not FundamentalRecord:
                raise FundamentalsDatasetError("records must contain FundamentalRecord values")

        record_by_key: dict[tuple[str, date, str, int, str], FundamentalRecord] = {}
        records_by_instrument: dict[str, list[FundamentalRecord]] = defaultdict(list)
        for record in records:
            if record.primary_key in record_by_key:
                instrument, period_end, item, revision, provider = record.primary_key
                raise FundamentalsDatasetError(
                    f"Duplicate fundamental key: {instrument} {period_end.isoformat()} {item} {revision} {provider}"
                )
            record_by_key[record.primary_key] = record
            records_by_instrument[record.instrument_id.canonical].append(record)

        sorted_records = tuple(
            sorted(
                records,
                key=lambda record: (
                    record.market.value,
                    record.instrument_id.canonical,
                    record.period_end,
                    record.item,
                    record.revision,
                    record.provider_id,
                ),
            )
        )
        object.__setattr__(self, "records", sorted_records)
        object.__setattr__(self, "_record_by_key", MappingProxyType(dict(record_by_key)))
        object.__setattr__(
            self,
            "_records_by_instrument",
            MappingProxyType(
                {
                    instrument_id: tuple(
                        sorted(
                            items,
                            key=lambda record: (
                                record.period_end,
                                record.item,
                                record.available_at,
                                record.revision,
                                record.provider_id,
                            ),
                        )
                    )
                    for instrument_id, items in records_by_instrument.items()
                }
            ),
        )

    @property
    def provider_ids(self) -> tuple[str, ...]:
        return tuple(sorted({record.provider_id for record in self.records}))

    @property
    def source_bronze_artifact_ids(self) -> tuple[str, ...]:
        return tuple(sorted({record.source_bronze_artifact_id for record in self.records}))

    def get(
        self,
        instrument_id: InstrumentId | str,
        *,
        period_end: date,
        item: str,
        revision: int,
        provider_id: str,
    ) -> FundamentalRecord:
        instrument = _coerce_instrument_id(instrument_id)
        _require_date("period_end", period_end)
        normalized_item = _required_string("item", item).lower()
        normalized_revision = _required_positive_int("revision", revision)
        normalized_provider = _required_string("provider_id", provider_id)
        key = (instrument.canonical, period_end, normalized_item, normalized_revision, normalized_provider)
        try:
            return self._record_by_key[key]
        except KeyError as exc:
            raise FundamentalsDatasetError(
                f"Fundamental record not found: {instrument.canonical} {period_end.isoformat()} "
                f"{normalized_item} {normalized_revision} {normalized_provider}"
            ) from exc

    def latest_as_of(
        self,
        instrument_id: InstrumentId | str,
        *,
        item: str,
        decision_time: datetime,
        provider_id: str | None = None,
        period_type: FundamentalPeriodType | str | None = None,
        purpose: FundamentalQueryPurpose | str = FundamentalQueryPurpose.FORMAL_BACKTEST,
    ) -> FundamentalRecord:
        candidates = self._query_candidates(
            instrument_id,
            item=item,
            decision_time=decision_time,
            provider_id=provider_id,
            period_type=period_type,
        )
        if not candidates:
            raise FundamentalsDatasetError("Fundamental record not found for decision_time")
        selected = max(candidates, key=_latest_sort_key)
        _ensure_query_allowed(selected, FundamentalQueryPurpose(purpose))
        return selected

    def history_for_item(
        self,
        instrument_id: InstrumentId | str,
        *,
        item: str,
        start_period: date,
        end_period: date,
        decision_time: datetime,
        provider_id: str | None = None,
        period_type: FundamentalPeriodType | str | None = None,
        purpose: FundamentalQueryPurpose | str = FundamentalQueryPurpose.FORMAL_BACKTEST,
    ) -> tuple[FundamentalRecord, ...]:
        _validate_period_range(start_period, end_period)
        query_purpose = FundamentalQueryPurpose(purpose)
        records = tuple(
            record
            for record in self._query_candidates(
                instrument_id,
                item=item,
                decision_time=decision_time,
                provider_id=provider_id,
                period_type=period_type,
            )
            if start_period <= record.period_end <= end_period
        )
        for record in records:
            _ensure_query_allowed(record, query_purpose)
        return records

    def records_for_instrument(
        self,
        instrument_id: InstrumentId | str,
        *,
        decision_time: datetime,
        provider_id: str | None = None,
        purpose: FundamentalQueryPurpose | str = FundamentalQueryPurpose.RESEARCH_DISPLAY,
    ) -> tuple[FundamentalRecord, ...]:
        instrument = _coerce_instrument_id(instrument_id)
        _require_aware_datetime("decision_time", decision_time)
        provider_filter = _optional_string(provider_id)
        query_purpose = FundamentalQueryPurpose(purpose)
        records = tuple(
            record
            for record in self._records_by_instrument.get(instrument.canonical, ())
            if record.available_at <= decision_time and (provider_filter is None or record.provider_id == provider_filter)
        )
        for record in records:
            _ensure_query_allowed(record, query_purpose)
        return records

    def merge_incremental(
        self,
        incremental: FundamentalsDataset,
        *,
        created_at: datetime | None = None,
        trace_id: str | None = None,
        run_id: str | None = None,
        stage_id: str | None = None,
    ) -> FundamentalsDataset:
        if type(incremental) is not FundamentalsDataset:
            raise FundamentalsDatasetError("incremental must be a FundamentalsDataset")
        merged = dict(self._record_by_key)
        merged.update(incremental._record_by_key)
        return FundamentalsDataset.from_records(
            merged.values(),
            created_at=created_at if created_at is not None else incremental.created_at,
            trace_id=trace_id if trace_id is not None else incremental.trace_id,
            run_id=run_id if run_id is not None else incremental.run_id,
            stage_id=stage_id if stage_id is not None else incremental.stage_id,
        )

    def to_json_bytes(self) -> bytes:
        payload = {
            "schema_name": FUNDAMENTALS_SCHEMA_NAME,
            "schema_version": FUNDAMENTALS_SCHEMA_VERSION,
            "created_at": self.created_at.isoformat(),
            "trace_id": self.trace_id,
            "run_id": self.run_id,
            "stage_id": self.stage_id,
            "record_count": len(self.records),
            "partition_keys": list(FUNDAMENTALS_PARTITION_KEYS),
            "field_schema": dict(FUNDAMENTALS_FIELD_SCHEMA),
            "provider_ids": list(self.provider_ids),
            "source_bronze_artifact_ids": list(self.source_bronze_artifact_ids),
            "records": [record.to_record() for record in self.records],
        }
        return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")

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
            schema_name=FUNDAMENTALS_SCHEMA_NAME,
            schema_version=FUNDAMENTALS_SCHEMA_VERSION,
            content_type=FUNDAMENTALS_CONTENT_TYPE,
            produced_by_run_id=run_id,
            produced_by_stage_id=stage_id,
            retention_tier=retention_tier,
            created_at=self.created_at,
        )

    def _query_candidates(
        self,
        instrument_id: InstrumentId | str,
        *,
        item: str,
        decision_time: datetime,
        provider_id: str | None,
        period_type: FundamentalPeriodType | str | None,
    ) -> tuple[FundamentalRecord, ...]:
        instrument = _coerce_instrument_id(instrument_id)
        normalized_item = _required_string("item", item).lower()
        _require_aware_datetime("decision_time", decision_time)
        provider_filter = _optional_string(provider_id)
        period_filter = FundamentalPeriodType(period_type) if period_type is not None else None
        return tuple(
            record
            for record in self._records_by_instrument.get(instrument.canonical, ())
            if record.item == normalized_item
            and record.available_at <= decision_time
            and (provider_filter is None or record.provider_id == provider_filter)
            and (period_filter is None or record.period_type is period_filter)
        )


def _record_from_provider_row(
    record: Mapping[str, object],
    *,
    batch: DataBatch[Mapping[str, object]],
    instrument_master: InstrumentMasterDataset,
    source_bronze_artifact_id: str,
) -> FundamentalRecord:
    row = dict(record)
    instrument = _coerce_instrument_id(_record_value(row, "instrument_id"))
    period_end = _coerce_period_end(_record_value(row, "period_end", fallback_field="report_period"))
    _validate_instrument_exists(instrument_master, instrument, period_end)
    temporal_confidence = _coerce_temporal_confidence(row.get("temporal_confidence"), row.get("announced_at"))
    ingested_at_value = row.get("ingested_at")
    return FundamentalRecord(
        instrument_id=instrument,
        period_end=period_end,
        period_type=_record_value(row, "period_type"),
        item=_record_value(row, "item", fallback_field="metric"),
        value=_record_value(row, "value"),
        revision=_optional_int(row.get("revision"), default=1),
        provider_id=batch.provenance.provider_id,
        announced_at=_optional_datetime(row.get("announced_at")),
        available_at=_required_datetime("available_at", row.get("available_at")),
        ingested_at=(
            _required_datetime("ingested_at", ingested_at_value)
            if not _is_missing(ingested_at_value)
            else batch.provenance.fetched_at
        ),
        unit=_optional_string(row.get("unit")),
        currency=_optional_upper_string(row.get("currency")),
        accounting_standard=_optional_string(row.get("accounting_standard")),
        fiscal_year=_optional_int(row.get("fiscal_year"), default=None),
        fiscal_quarter=_optional_int(row.get("fiscal_quarter"), default=None),
        provider_source=_optional_string(row.get("source")) or batch.provenance.provider_id,
        provider_source_timestamp=batch.provenance.source_timestamp,
        provider_raw_response_sha256=batch.provenance.raw_response_sha256,
        field_lineage=batch.provenance.field_lineage,
        source_bronze_artifact_id=source_bronze_artifact_id,
        temporal_confidence=temporal_confidence,
    )


def _validate_instrument_exists(
    instrument_master: InstrumentMasterDataset,
    instrument: InstrumentId,
    period_end: date,
) -> None:
    try:
        instrument_master.get(instrument, as_of=period_end)
    except Exception as exc:
        raise FundamentalsDatasetError(
            f"instrument_id must exist in Instrument Master as of period_end: {instrument.canonical} "
            f"{period_end.isoformat()}"
        ) from exc


def _validate_pit_timing(record: FundamentalRecord) -> None:
    if record.temporal_confidence is TemporalConfidence.UNKNOWN:
        if record.announced_at is not None:
            raise FundamentalsDatasetError("announced_at must be omitted when temporal_confidence is unknown")
        if record.ingested_at < record.available_at:
            raise FundamentalsDatasetError("ingested_at cannot be before available_at")
        return

    if record.announced_at is None:
        raise FundamentalsDatasetError("announced_at is required unless temporal_confidence is unknown")
    if record.available_at < record.announced_at:
        raise FundamentalsDatasetError("available_at cannot be before announced_at")
    if record.ingested_at < record.available_at:
        raise FundamentalsDatasetError("ingested_at cannot be before available_at")


def _ensure_query_allowed(record: FundamentalRecord, purpose: FundamentalQueryPurpose) -> None:
    if purpose is FundamentalQueryPurpose.FORMAL_BACKTEST and not record.is_formal_backtest_eligible:
        raise FundamentalsDatasetError(
            f"record has unknown temporal confidence and cannot be used for formal backtest: "
            f"{record.instrument_id.canonical} {record.item} {record.period_end.isoformat()}"
        )


def _latest_sort_key(record: FundamentalRecord) -> tuple[date, datetime, int]:
    return (record.period_end, record.available_at, record.revision)


def _coerce_instrument_id(value: object) -> InstrumentId:
    if type(value) is InstrumentId:
        return value
    if type(value) is str:
        try:
            return InstrumentId.parse(value)
        except Exception as exc:
            raise FundamentalsDatasetError(f"instrument_id is invalid: {value!r}") from exc
    raise FundamentalsDatasetError("instrument_id is required")


def _coerce_period_end(value: object) -> date:
    if type(value) is date:
        return value
    if type(value) is datetime:
        return value.date()
    if type(value) is str:
        text = value.strip()
        try:
            return datetime.fromisoformat(text).date()
        except ValueError:
            try:
                return date.fromisoformat(text)
            except ValueError as exc:
                raise FundamentalsDatasetError(f"period_end is invalid: {value!r}") from exc
    raise FundamentalsDatasetError("period_end is required")


def _coerce_temporal_confidence(value: object, announced_at: object) -> TemporalConfidence:
    if _is_missing(value):
        return TemporalConfidence.EXACT if not _is_missing(announced_at) else TemporalConfidence.UNKNOWN
    return TemporalConfidence(_required_string("temporal_confidence", value))


def _required_datetime(field_name: str, value: object) -> datetime:
    if _is_missing(value):
        raise FundamentalsDatasetError(f"{field_name} is required")
    parsed = _parse_datetime(field_name, value)
    _require_aware_datetime(field_name, parsed)
    return parsed


def _optional_datetime(value: object) -> datetime | None:
    if _is_missing(value):
        return None
    parsed = _parse_datetime("announced_at", value)
    _require_aware_datetime("announced_at", parsed)
    return parsed


def _parse_datetime(field_name: str, value: object) -> datetime:
    if type(value) is datetime:
        return value
    if type(value) is str:
        text = value.strip()
        if text.endswith("Z"):
            text = f"{text[:-1]}+00:00"
        try:
            return datetime.fromisoformat(text)
        except ValueError as exc:
            raise FundamentalsDatasetError(f"{field_name} is invalid: {value!r}") from exc
    raise FundamentalsDatasetError(f"{field_name} must be a datetime")


def _record_value(
    record: Mapping[str, object],
    field_name: str,
    *,
    fallback_field: str | None = None,
) -> object:
    value = record.get(field_name)
    if _is_missing(value) and fallback_field is not None:
        value = record.get(fallback_field)
    if _is_missing(value):
        raise FundamentalsDatasetError(f"{field_name} is required")
    return value


def _validate_period_range(start: date, end: date) -> None:
    _require_date("start_period", start)
    _require_date("end_period", end)
    if end < start:
        raise FundamentalsDatasetError("end_period must be on or after start_period")


def _require_date(field_name: str, value: object) -> None:
    if type(value) is not date:
        raise FundamentalsDatasetError(f"{field_name} must be a date")


def _require_aware_datetime(field_name: str, value: object) -> None:
    if type(value) is not datetime or value.tzinfo is None or value.utcoffset() is None:
        raise FundamentalsDatasetError(f"{field_name} must be timezone-aware")


def _required_number(field_name: str, value: object) -> float:
    if _is_missing(value):
        raise FundamentalsDatasetError(f"{field_name} is required")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise FundamentalsDatasetError(f"{field_name} must be numeric") from exc
    if not math.isfinite(number):
        raise FundamentalsDatasetError(f"{field_name} must be finite")
    return number


def _required_int(field_name: str, value: object) -> int:
    if type(value) is bool or not isinstance(value, int):
        raise FundamentalsDatasetError(f"{field_name} must be an integer")
    return int(value)


def _required_positive_int(field_name: str, value: object) -> int:
    integer = _required_int(field_name, value)
    if integer <= 0:
        raise FundamentalsDatasetError(f"{field_name} must be positive")
    return integer


def _optional_int(value: object, *, default: int | None) -> int | None:
    if _is_missing(value):
        return default
    return _required_int("integer value", value)


def _freeze_lineage(lineage: Mapping[str, str]) -> Mapping[str, str]:
    normalized: dict[str, str] = {}
    for key, value in lineage.items():
        normalized[_required_string("field lineage key", key)] = _required_string("field lineage value", value)
    return MappingProxyType(normalized)


def _is_missing(value: object) -> bool:
    if value is None:
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    if isinstance(value, str) and value.strip().lower() in {"", "nan", "none", "null", "na", "n/a"}:
        return True
    return False


def _required_string(field_name: str, value: object | None) -> str:
    if type(value) is not str:
        raise FundamentalsDatasetError(f"{field_name} is required")
    normalized = value.strip()
    if not normalized:
        raise FundamentalsDatasetError(f"{field_name} is required")
    return normalized


def _optional_string(value: object | None) -> str | None:
    if value is None:
        return None
    if type(value) is not str:
        raise FundamentalsDatasetError("optional string value must be a string")
    normalized = value.strip()
    return normalized or None


def _optional_upper_string(value: object | None) -> str | None:
    normalized = _optional_string(value)
    return normalized.upper() if normalized is not None else None


__all__ = [
    "FUNDAMENTALS_CONTENT_TYPE",
    "FUNDAMENTALS_FIELD_SCHEMA",
    "FUNDAMENTALS_PARTITION_KEYS",
    "FUNDAMENTALS_SCHEMA_NAME",
    "FUNDAMENTALS_SCHEMA_VERSION",
    "FundamentalPeriodType",
    "FundamentalQueryPurpose",
    "FundamentalRecord",
    "FundamentalsDataset",
    "FundamentalsDatasetError",
    "TemporalConfidence",
]
