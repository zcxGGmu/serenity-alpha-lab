from __future__ import annotations

import json
import math
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date, datetime
from types import MappingProxyType

from serenity_alpha_lab.datasets.instrument_master import InstrumentMasterDataset
from serenity_alpha_lab.datasets.trading_calendar import TradingCalendarDataset
from serenity_alpha_lab.domain.artifacts import (
    ArtifactManifest,
    ArtifactRetentionTier,
    ArtifactStore,
    ArtifactUri,
)
from serenity_alpha_lab.domain.instruments import InstrumentId, Market
from serenity_alpha_lab.domain.providers import DataBatch, ProviderCapability


RAW_DAILY_BARS_SCHEMA_NAME = "dataset.bars_1d_raw"
RAW_DAILY_BARS_SCHEMA_VERSION = "1.0.0"
RAW_DAILY_BARS_CONTENT_TYPE = "application/vnd.serenity.dataset.raw-daily-bars+json"
RAW_DAILY_BARS_PARTITION_KEYS = ("market", "year", "month")
RAW_DAILY_BARS_FIELD_SCHEMA: Mapping[str, str] = MappingProxyType(
    {
        "instrument_id": "utf8",
        "market": "utf8",
        "exchange": "utf8",
        "trade_date": "date32[day]",
        "provider_id": "utf8",
        "provider_source": "utf8",
        "open": "float64",
        "high": "float64",
        "low": "float64",
        "close": "float64",
        "volume": "float64",
        "amount": "float64",
        "currency": "utf8",
        "adjustment": "utf8",
        "provider_source_timestamp": "timestamp[us, tz=UTC]",
        "provider_raw_response_sha256": "utf8",
        "source_bronze_artifact_id": "utf8",
    }
)


class RawDailyBarsDatasetError(ValueError):
    """Raised when raw daily bars violate the Dataset contract."""


@dataclass(frozen=True, slots=True)
class RawDailyBar:
    instrument_id: InstrumentId
    trade_date: date
    provider_id: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    amount: float
    provider_source: str
    provider_source_timestamp: datetime | None
    provider_raw_response_sha256: str
    field_lineage: Mapping[str, str]
    source_bronze_artifact_id: str
    currency: str | None = None
    adjustment: str = "unadjusted"

    def __post_init__(self) -> None:
        if type(self.instrument_id) is not InstrumentId:
            raise RawDailyBarsDatasetError("instrument_id must be an InstrumentId")
        _require_date("trade_date", self.trade_date)
        object.__setattr__(self, "provider_id", _required_string("provider_id", self.provider_id))
        object.__setattr__(self, "provider_source", _required_string("provider_source", self.provider_source))
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
        object.__setattr__(self, "currency", _optional_upper_string(self.currency))
        object.__setattr__(self, "adjustment", _required_string("adjustment", self.adjustment))
        if self.adjustment != "unadjusted":
            raise RawDailyBarsDatasetError("raw daily bars must use unadjusted prices")
        if self.provider_source_timestamp is not None:
            _require_aware_datetime("provider_source_timestamp", self.provider_source_timestamp)

        for field_name in ("open", "high", "low", "close", "volume", "amount"):
            object.__setattr__(self, field_name, _required_number(field_name, getattr(self, field_name)))
        _validate_ohlc(self.open, self.high, self.low, self.close)
        if self.volume < 0:
            raise RawDailyBarsDatasetError("volume cannot be negative")
        if self.amount < 0:
            raise RawDailyBarsDatasetError("amount cannot be negative")

        object.__setattr__(self, "field_lineage", _freeze_lineage(self.field_lineage))

    @property
    def market(self) -> Market:
        return self.instrument_id.market

    @property
    def primary_key(self) -> tuple[str, date, str]:
        return (self.instrument_id.canonical, self.trade_date, self.provider_id)

    @property
    def partition_values(self) -> dict[str, str]:
        return {
            "market": self.market.value,
            "year": f"{self.trade_date.year:04d}",
            "month": f"{self.trade_date.month:02d}",
        }

    def to_record(self) -> dict[str, object]:
        return {
            "instrument_id": self.instrument_id.canonical,
            "market": self.market.value,
            "exchange": self.instrument_id.exchange.value,
            "symbol": self.instrument_id.symbol,
            "trade_date": self.trade_date.isoformat(),
            "provider_id": self.provider_id,
            "provider_source": self.provider_source,
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
            "amount": self.amount,
            "currency": self.currency,
            "adjustment": self.adjustment,
            "provider_source_timestamp": (
                self.provider_source_timestamp.isoformat() if self.provider_source_timestamp else None
            ),
            "provider_raw_response_sha256": self.provider_raw_response_sha256,
            "field_lineage": dict(self.field_lineage),
            "source_bronze_artifact_id": self.source_bronze_artifact_id,
            "partition": self.partition_values,
        }


@dataclass(frozen=True, slots=True)
class RawDailyBarsDataset:
    records: Sequence[RawDailyBar]
    created_at: datetime
    trace_id: str | None = None
    run_id: str | None = None
    stage_id: str | None = None
    _bar_by_key: Mapping[tuple[str, date, str], RawDailyBar] = field(init=False, repr=False, compare=False)
    _bars_by_instrument: Mapping[str, tuple[RawDailyBar, ...]] = field(init=False, repr=False, compare=False)
    _bars_by_market_date: Mapping[tuple[Market, date], tuple[RawDailyBar, ...]] = field(
        init=False,
        repr=False,
        compare=False,
    )
    _bars_by_provider: Mapping[str, tuple[RawDailyBar, ...]] = field(init=False, repr=False, compare=False)

    @classmethod
    def from_records(
        cls,
        records: Iterable[RawDailyBar],
        *,
        created_at: datetime,
        trace_id: str | None = None,
        run_id: str | None = None,
        stage_id: str | None = None,
    ) -> RawDailyBarsDataset:
        return cls(
            records=tuple(records),
            created_at=created_at,
            trace_id=trace_id,
            run_id=run_id,
            stage_id=stage_id,
        )

    @classmethod
    def from_provider_batch(
        cls,
        batch: DataBatch[Mapping[str, object]],
        *,
        instrument_master: InstrumentMasterDataset,
        trading_calendar: TradingCalendarDataset,
        source_bronze_artifact_id: str,
        created_at: datetime,
        trace_id: str | None = None,
        run_id: str | None = None,
        stage_id: str | None = None,
    ) -> RawDailyBarsDataset:
        if type(batch) is not DataBatch:
            raise RawDailyBarsDatasetError("batch must be a Provider DataBatch")
        if batch.provenance.operation != ProviderCapability.DAILY_BARS.value:
            raise RawDailyBarsDatasetError("Provider DataBatch operation must be daily_bars")
        source_artifact_id = _required_string("source_bronze_artifact_id", source_bronze_artifact_id)
        bars = [
            _bar_from_provider_record(
                record,
                batch=batch,
                instrument_master=instrument_master,
                trading_calendar=trading_calendar,
                source_bronze_artifact_id=source_artifact_id,
            )
            for record in batch.records
        ]
        return cls.from_records(
            bars,
            created_at=created_at,
            trace_id=trace_id if trace_id is not None else batch.provenance.trace_id,
            run_id=run_id if run_id is not None else batch.provenance.run_id,
            stage_id=stage_id if stage_id is not None else batch.provenance.stage_id,
        )

    def __post_init__(self) -> None:
        _require_aware_datetime("created_at", self.created_at)
        object.__setattr__(self, "trace_id", _optional_string(self.trace_id))
        object.__setattr__(self, "run_id", _optional_string(self.run_id))
        object.__setattr__(self, "stage_id", _optional_string(self.stage_id))

        records = tuple(self.records)
        if not records:
            raise RawDailyBarsDatasetError("raw daily bar records are required")
        for record in records:
            if type(record) is not RawDailyBar:
                raise RawDailyBarsDatasetError("records must contain RawDailyBar values")

        bar_by_key: dict[tuple[str, date, str], RawDailyBar] = {}
        bars_by_instrument: dict[str, list[RawDailyBar]] = defaultdict(list)
        bars_by_market_date: dict[tuple[Market, date], list[RawDailyBar]] = defaultdict(list)
        bars_by_provider: dict[str, list[RawDailyBar]] = defaultdict(list)
        for record in records:
            if record.primary_key in bar_by_key:
                instrument, trade_date, provider = record.primary_key
                raise RawDailyBarsDatasetError(
                    f"Duplicate raw daily bar key: {instrument} {trade_date.isoformat()} {provider}"
                )
            bar_by_key[record.primary_key] = record
            bars_by_instrument[record.instrument_id.canonical].append(record)
            bars_by_market_date[(record.market, record.trade_date)].append(record)
            bars_by_provider[record.provider_id].append(record)

        sorted_records = tuple(
            sorted(
                records,
                key=lambda item: (item.market.value, item.instrument_id.canonical, item.trade_date, item.provider_id),
            )
        )
        object.__setattr__(self, "records", sorted_records)
        object.__setattr__(self, "_bar_by_key", MappingProxyType(dict(bar_by_key)))
        object.__setattr__(
            self,
            "_bars_by_instrument",
            MappingProxyType(
                {
                    instrument_id: tuple(sorted(bars, key=lambda item: (item.trade_date, item.provider_id)))
                    for instrument_id, bars in bars_by_instrument.items()
                }
            ),
        )
        object.__setattr__(
            self,
            "_bars_by_market_date",
            MappingProxyType(
                {
                    key: tuple(sorted(bars, key=lambda item: (item.instrument_id.canonical, item.provider_id)))
                    for key, bars in bars_by_market_date.items()
                }
            ),
        )
        object.__setattr__(
            self,
            "_bars_by_provider",
            MappingProxyType(
                {
                    provider_id: tuple(
                        sorted(bars, key=lambda item: (item.trade_date, item.instrument_id.canonical))
                    )
                    for provider_id, bars in bars_by_provider.items()
                }
            ),
        )

    @property
    def source_bronze_artifact_ids(self) -> tuple[str, ...]:
        return tuple(sorted({record.source_bronze_artifact_id for record in self.records}))

    @property
    def provider_ids(self) -> tuple[str, ...]:
        return tuple(sorted({record.provider_id for record in self.records}))

    def get(self, instrument_id: InstrumentId | str, trade_date: date, *, provider_id: str) -> RawDailyBar:
        instrument = _coerce_instrument_id(instrument_id)
        _require_date("trade_date", trade_date)
        normalized_provider = _required_string("provider_id", provider_id)
        key = (instrument.canonical, trade_date, normalized_provider)
        try:
            return self._bar_by_key[key]
        except KeyError as exc:
            raise RawDailyBarsDatasetError(
                f"Raw daily bar not found: {instrument.canonical} {trade_date.isoformat()} {normalized_provider}"
            ) from exc

    def bars_for_instrument(
        self,
        instrument_id: InstrumentId | str,
        start: date,
        end: date,
        *,
        provider_id: str | None = None,
    ) -> tuple[RawDailyBar, ...]:
        instrument = _coerce_instrument_id(instrument_id)
        _validate_date_range(start, end)
        provider_filter = _optional_string(provider_id)
        bars = self._bars_by_instrument.get(instrument.canonical, ())
        return tuple(
            bar
            for bar in bars
            if start <= bar.trade_date <= end and (provider_filter is None or bar.provider_id == provider_filter)
        )

    def bars_for_market(
        self,
        market: Market | str,
        trade_date: date,
        *,
        provider_id: str | None = None,
    ) -> tuple[RawDailyBar, ...]:
        normalized_market = _coerce_market(market)
        _require_date("trade_date", trade_date)
        provider_filter = _optional_string(provider_id)
        bars = self._bars_by_market_date.get((normalized_market, trade_date), ())
        return tuple(bar for bar in bars if provider_filter is None or bar.provider_id == provider_filter)

    def bars_for_provider(self, provider_id: str, start: date, end: date) -> tuple[RawDailyBar, ...]:
        normalized_provider = _required_string("provider_id", provider_id)
        _validate_date_range(start, end)
        return tuple(
            bar for bar in self._bars_by_provider.get(normalized_provider, ()) if start <= bar.trade_date <= end
        )

    def merge_incremental(
        self,
        incremental: RawDailyBarsDataset,
        *,
        created_at: datetime | None = None,
        trace_id: str | None = None,
        run_id: str | None = None,
        stage_id: str | None = None,
    ) -> RawDailyBarsDataset:
        if type(incremental) is not RawDailyBarsDataset:
            raise RawDailyBarsDatasetError("incremental must be a RawDailyBarsDataset")
        merged = dict(self._bar_by_key)
        merged.update(incremental._bar_by_key)
        return RawDailyBarsDataset.from_records(
            merged.values(),
            created_at=created_at if created_at is not None else incremental.created_at,
            trace_id=trace_id if trace_id is not None else incremental.trace_id,
            run_id=run_id if run_id is not None else incremental.run_id,
            stage_id=stage_id if stage_id is not None else incremental.stage_id,
        )

    def to_json_bytes(self) -> bytes:
        payload = {
            "schema_name": RAW_DAILY_BARS_SCHEMA_NAME,
            "schema_version": RAW_DAILY_BARS_SCHEMA_VERSION,
            "created_at": self.created_at.isoformat(),
            "trace_id": self.trace_id,
            "run_id": self.run_id,
            "stage_id": self.stage_id,
            "record_count": len(self.records),
            "partition_keys": list(RAW_DAILY_BARS_PARTITION_KEYS),
            "field_schema": dict(RAW_DAILY_BARS_FIELD_SCHEMA),
            "provider_ids": list(self.provider_ids),
            "source_bronze_artifact_ids": list(self.source_bronze_artifact_ids),
            "records": [record.to_record() for record in self.records],
        }
        return json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")

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
            schema_name=RAW_DAILY_BARS_SCHEMA_NAME,
            schema_version=RAW_DAILY_BARS_SCHEMA_VERSION,
            content_type=RAW_DAILY_BARS_CONTENT_TYPE,
            produced_by_run_id=run_id,
            produced_by_stage_id=stage_id,
            retention_tier=retention_tier,
            created_at=self.created_at,
        )


def _bar_from_provider_record(
    record: Mapping[str, object],
    *,
    batch: DataBatch[Mapping[str, object]],
    instrument_master: InstrumentMasterDataset,
    trading_calendar: TradingCalendarDataset,
    source_bronze_artifact_id: str,
) -> RawDailyBar:
    row = dict(record)
    instrument = _coerce_instrument_id(_record_value(row, "instrument_id"))
    trade_date = _coerce_trade_date(_record_value(row, "trade_date", fallback_field="date"))
    _validate_instrument_exists(instrument_master, instrument, trade_date)
    _validate_trade_date(trading_calendar, instrument.market, trade_date)
    return RawDailyBar(
        instrument_id=instrument,
        trade_date=trade_date,
        provider_id=batch.provenance.provider_id,
        provider_source=_optional_string(row.get("source")) or batch.provenance.provider_id,
        open=_required_number("open", row.get("open")),
        high=_required_number("high", row.get("high")),
        low=_required_number("low", row.get("low")),
        close=_required_number("close", row.get("close")),
        volume=_required_number("volume", row.get("volume")),
        amount=_required_number("amount", row.get("amount")),
        currency=_optional_upper_string(row.get("currency")),
        provider_source_timestamp=batch.provenance.source_timestamp,
        provider_raw_response_sha256=batch.provenance.raw_response_sha256,
        field_lineage=batch.provenance.field_lineage,
        source_bronze_artifact_id=source_bronze_artifact_id,
    )


def _validate_instrument_exists(
    instrument_master: InstrumentMasterDataset,
    instrument: InstrumentId,
    trade_date: date,
) -> None:
    try:
        instrument_master.get(instrument, as_of=trade_date)
    except Exception as exc:
        raise RawDailyBarsDatasetError(
            f"instrument_id must exist in Instrument Master as of trade_date: {instrument.canonical} "
            f"{trade_date.isoformat()}"
        ) from exc


def _validate_trade_date(
    trading_calendar: TradingCalendarDataset,
    market: Market,
    trade_date: date,
) -> None:
    try:
        is_trading_day = trading_calendar.is_trading_day(market, trade_date)
    except Exception as exc:
        raise RawDailyBarsDatasetError(
            f"trade_date must be present in Trading Calendar: {market.value} {trade_date.isoformat()}"
        ) from exc
    if not is_trading_day:
        raise RawDailyBarsDatasetError(
            f"trade_date must be a trading day: {market.value} {trade_date.isoformat()}"
        )


def _coerce_instrument_id(value: object) -> InstrumentId:
    if type(value) is InstrumentId:
        return value
    if type(value) is str:
        try:
            return InstrumentId.parse(value)
        except Exception as exc:
            raise RawDailyBarsDatasetError(f"instrument_id is invalid: {value!r}") from exc
    raise RawDailyBarsDatasetError("instrument_id is required")


def _coerce_market(value: Market | str) -> Market:
    try:
        return Market(value)
    except ValueError as exc:
        raise RawDailyBarsDatasetError(f"Unsupported market: {value}") from exc


def _coerce_trade_date(value: object) -> date:
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
                raise RawDailyBarsDatasetError(f"trade_date is invalid: {value!r}") from exc
    raise RawDailyBarsDatasetError("trade_date is required")


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
        raise RawDailyBarsDatasetError(f"{field_name} is required")
    return value


def _validate_ohlc(open_price: float, high: float, low: float, close: float) -> None:
    if min(open_price, high, low, close) < 0:
        raise RawDailyBarsDatasetError("OHLC prices cannot be negative")
    if not (low <= open_price <= high and low <= close <= high):
        raise RawDailyBarsDatasetError("OHLC relationship must satisfy low <= open/close <= high")


def _freeze_lineage(lineage: Mapping[str, str]) -> Mapping[str, str]:
    normalized: dict[str, str] = {}
    for key, value in lineage.items():
        normalized[_required_string("field lineage key", key)] = _required_string("field lineage value", value)
    return MappingProxyType(normalized)


def _validate_date_range(start: date, end: date) -> None:
    _require_date("start", start)
    _require_date("end", end)
    if end < start:
        raise RawDailyBarsDatasetError("end must be on or after start")


def _require_date(field_name: str, value: object) -> None:
    if type(value) is not date:
        raise RawDailyBarsDatasetError(f"{field_name} must be a date")


def _require_aware_datetime(field_name: str, value: object) -> None:
    if type(value) is not datetime or value.tzinfo is None or value.utcoffset() is None:
        raise RawDailyBarsDatasetError(f"{field_name} must be timezone-aware")


def _required_number(field_name: str, value: object) -> float:
    if _is_missing(value):
        raise RawDailyBarsDatasetError(f"{field_name} is required")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise RawDailyBarsDatasetError(f"{field_name} must be numeric") from exc
    if not math.isfinite(number):
        raise RawDailyBarsDatasetError(f"{field_name} must be finite")
    return number


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
        raise RawDailyBarsDatasetError(f"{field_name} is required")
    normalized = value.strip()
    if not normalized:
        raise RawDailyBarsDatasetError(f"{field_name} is required")
    return normalized


def _optional_string(value: object | None) -> str | None:
    if value is None:
        return None
    if type(value) is not str:
        raise RawDailyBarsDatasetError("optional string value must be a string")
    normalized = value.strip()
    return normalized or None


def _optional_upper_string(value: object | None) -> str | None:
    normalized = _optional_string(value)
    return normalized.upper() if normalized is not None else None


__all__ = [
    "RAW_DAILY_BARS_CONTENT_TYPE",
    "RAW_DAILY_BARS_FIELD_SCHEMA",
    "RAW_DAILY_BARS_PARTITION_KEYS",
    "RAW_DAILY_BARS_SCHEMA_NAME",
    "RAW_DAILY_BARS_SCHEMA_VERSION",
    "RawDailyBar",
    "RawDailyBarsDataset",
    "RawDailyBarsDatasetError",
]
