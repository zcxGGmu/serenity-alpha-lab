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
from serenity_alpha_lab.datasets.raw_daily_bars import RawDailyBar, RawDailyBarsDataset
from serenity_alpha_lab.datasets.trading_calendar import TradingCalendarDataset
from serenity_alpha_lab.domain.artifacts import (
    ArtifactManifest,
    ArtifactRetentionTier,
    ArtifactStore,
    ArtifactUri,
)
from serenity_alpha_lab.domain.instruments import InstrumentId, Market


CORPORATE_ACTIONS_SCHEMA_NAME = "dataset.corporate_actions"
CORPORATE_ACTIONS_SCHEMA_VERSION = "1.0.0"
CORPORATE_ACTIONS_CONTENT_TYPE = "application/vnd.serenity.dataset.corporate-actions+json"
CORPORATE_ACTIONS_PARTITION_KEYS = ("market", "year")
CORPORATE_ACTIONS_FIELD_SCHEMA: Mapping[str, str] = MappingProxyType(
    {
        "instrument_id": "utf8",
        "market": "utf8",
        "exchange": "utf8",
        "ex_date": "date32[day]",
        "action_type": "utf8",
        "provider_id": "utf8",
        "provider_source": "utf8",
        "cash_dividend_per_share": "float64",
        "bonus_share_ratio": "float64",
        "split_ratio": "float64",
        "rights_issue_ratio": "float64",
        "rights_issue_price": "float64",
        "currency": "utf8",
        "provider_source_timestamp": "timestamp[us, tz=UTC]",
        "provider_raw_response_sha256": "utf8",
        "source_bronze_artifact_id": "utf8",
    }
)

ADJUSTED_DAILY_BARS_SCHEMA_NAME = "dataset.bars_1d_adjusted"
ADJUSTED_DAILY_BARS_SCHEMA_VERSION = "1.0.0"
ADJUSTED_DAILY_BARS_CONTENT_TYPE = "application/vnd.serenity.dataset.adjusted-daily-bars+json"
ADJUSTED_DAILY_BARS_PARTITION_KEYS = ("market", "year", "month")
ADJUSTED_DAILY_BARS_FIELD_SCHEMA: Mapping[str, str] = MappingProxyType(
    {
        "instrument_id": "utf8",
        "market": "utf8",
        "exchange": "utf8",
        "trade_date": "date32[day]",
        "provider_id": "utf8",
        "adjustment": "utf8",
        "adjustment_factor": "float64",
        "open": "float64",
        "high": "float64",
        "low": "float64",
        "close": "float64",
        "raw_open": "float64",
        "raw_high": "float64",
        "raw_low": "float64",
        "raw_close": "float64",
        "volume": "float64",
        "amount": "float64",
        "currency": "utf8",
        "provider_source": "utf8",
        "provider_source_timestamp": "timestamp[us, tz=UTC]",
        "provider_raw_response_sha256": "utf8",
        "source_raw_bronze_artifact_id": "utf8",
        "source_corporate_action_artifact_ids": "list<utf8>",
    }
)


class CorporateActionsDatasetError(ValueError):
    """Raised when corporate actions or adjustment factors violate the Dataset contract."""


class CorporateActionType(StrEnum):
    CASH_DIVIDEND = "cash_dividend"
    BONUS_SHARE = "bonus_share"
    RIGHTS_ISSUE = "rights_issue"
    SHARE_SPLIT = "share_split"


class AdjustmentMode(StrEnum):
    FORWARD = "forward"
    BACKWARD = "backward"


@dataclass(frozen=True, slots=True)
class CorporateAction:
    instrument_id: InstrumentId
    ex_date: date
    action_type: CorporateActionType | str
    provider_id: str
    provider_source: str
    provider_source_timestamp: datetime | None
    provider_raw_response_sha256: str
    field_lineage: Mapping[str, str]
    source_bronze_artifact_id: str
    cash_dividend_per_share: float = 0.0
    bonus_share_ratio: float = 0.0
    split_ratio: float = 1.0
    rights_issue_ratio: float = 0.0
    rights_issue_price: float | None = None
    currency: str | None = None

    def __post_init__(self) -> None:
        if type(self.instrument_id) is not InstrumentId:
            raise CorporateActionsDatasetError("instrument_id must be an InstrumentId")
        _require_date("ex_date", self.ex_date)
        object.__setattr__(self, "action_type", CorporateActionType(self.action_type))
        object.__setattr__(self, "provider_id", _required_string("provider_id", self.provider_id))
        object.__setattr__(self, "provider_source", _required_string("provider_source", self.provider_source))
        if self.provider_source_timestamp is not None:
            _require_aware_datetime("provider_source_timestamp", self.provider_source_timestamp)
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
        object.__setattr__(
            self,
            "cash_dividend_per_share",
            _non_negative_number("cash_dividend_per_share", self.cash_dividend_per_share),
        )
        object.__setattr__(
            self,
            "bonus_share_ratio",
            _non_negative_number("bonus_share_ratio", self.bonus_share_ratio),
        )
        object.__setattr__(self, "split_ratio", _positive_number("split_ratio", self.split_ratio))
        object.__setattr__(
            self,
            "rights_issue_ratio",
            _non_negative_number("rights_issue_ratio", self.rights_issue_ratio),
        )
        if self.rights_issue_price is not None:
            object.__setattr__(
                self,
                "rights_issue_price",
                _positive_number("rights_issue_price", self.rights_issue_price),
            )
        object.__setattr__(self, "field_lineage", _freeze_lineage(self.field_lineage))
        _validate_action_terms(self)

    @property
    def market(self) -> Market:
        return self.instrument_id.market

    @property
    def primary_key(self) -> tuple[str, date, str, str]:
        return (self.instrument_id.canonical, self.ex_date, self.action_type.value, self.provider_id)

    @property
    def partition_values(self) -> dict[str, str]:
        return {
            "market": self.market.value,
            "year": f"{self.ex_date.year:04d}",
        }

    def to_record(self) -> dict[str, object]:
        return {
            "instrument_id": self.instrument_id.canonical,
            "market": self.market.value,
            "exchange": self.instrument_id.exchange.value,
            "symbol": self.instrument_id.symbol,
            "ex_date": self.ex_date.isoformat(),
            "action_type": self.action_type.value,
            "provider_id": self.provider_id,
            "provider_source": self.provider_source,
            "cash_dividend_per_share": self.cash_dividend_per_share,
            "bonus_share_ratio": self.bonus_share_ratio,
            "split_ratio": self.split_ratio,
            "rights_issue_ratio": self.rights_issue_ratio,
            "rights_issue_price": self.rights_issue_price,
            "currency": self.currency,
            "provider_source_timestamp": (
                self.provider_source_timestamp.isoformat() if self.provider_source_timestamp else None
            ),
            "provider_raw_response_sha256": self.provider_raw_response_sha256,
            "field_lineage": dict(self.field_lineage),
            "source_bronze_artifact_id": self.source_bronze_artifact_id,
            "partition": self.partition_values,
        }


@dataclass(frozen=True, slots=True)
class CorporateActionsDataset:
    records: Sequence[CorporateAction]
    created_at: datetime
    trace_id: str | None = None
    run_id: str | None = None
    stage_id: str | None = None
    _action_by_key: Mapping[tuple[str, date, str, str], CorporateAction] = field(
        init=False,
        repr=False,
        compare=False,
    )
    _actions_by_instrument: Mapping[str, tuple[CorporateAction, ...]] = field(
        init=False,
        repr=False,
        compare=False,
    )
    _actions_by_market_date: Mapping[tuple[Market, date], tuple[CorporateAction, ...]] = field(
        init=False,
        repr=False,
        compare=False,
    )

    @classmethod
    def from_records(
        cls,
        records: Iterable[CorporateAction],
        *,
        instrument_master: InstrumentMasterDataset,
        trading_calendar: TradingCalendarDataset,
        created_at: datetime,
        trace_id: str | None = None,
        run_id: str | None = None,
        stage_id: str | None = None,
    ) -> CorporateActionsDataset:
        actions = tuple(records)
        for action in actions:
            if type(action) is not CorporateAction:
                raise CorporateActionsDatasetError("records must contain CorporateAction values")
            _validate_instrument_exists(instrument_master, action.instrument_id, action.ex_date)
            _validate_ex_date(trading_calendar, action.market, action.ex_date)
        return cls(
            records=actions,
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
            if type(record) is not CorporateAction:
                raise CorporateActionsDatasetError("records must contain CorporateAction values")

        action_by_key: dict[tuple[str, date, str, str], CorporateAction] = {}
        actions_by_instrument: dict[str, list[CorporateAction]] = defaultdict(list)
        actions_by_market_date: dict[tuple[Market, date], list[CorporateAction]] = defaultdict(list)
        for record in records:
            if record.primary_key in action_by_key:
                instrument, ex_date, action_type, provider = record.primary_key
                raise CorporateActionsDatasetError(
                    f"Duplicate corporate action key: {instrument} {ex_date.isoformat()} {action_type} {provider}"
                )
            action_by_key[record.primary_key] = record
            actions_by_instrument[record.instrument_id.canonical].append(record)
            actions_by_market_date[(record.market, record.ex_date)].append(record)

        sorted_records = tuple(
            sorted(
                records,
                key=lambda action: (
                    action.market.value,
                    action.instrument_id.canonical,
                    action.ex_date,
                    action.action_type.value,
                    action.provider_id,
                ),
            )
        )
        object.__setattr__(self, "records", sorted_records)
        object.__setattr__(self, "_action_by_key", MappingProxyType(dict(action_by_key)))
        object.__setattr__(
            self,
            "_actions_by_instrument",
            MappingProxyType(
                {
                    instrument_id: tuple(
                        sorted(
                            actions,
                            key=lambda action: (action.ex_date, action.action_type.value, action.provider_id),
                        )
                    )
                    for instrument_id, actions in actions_by_instrument.items()
                }
            ),
        )
        object.__setattr__(
            self,
            "_actions_by_market_date",
            MappingProxyType(
                {
                    key: tuple(
                        sorted(
                            actions,
                            key=lambda action: (action.instrument_id.canonical, action.action_type.value),
                        )
                    )
                    for key, actions in actions_by_market_date.items()
                }
            ),
        )

    @property
    def source_bronze_artifact_ids(self) -> tuple[str, ...]:
        return tuple(sorted({record.source_bronze_artifact_id for record in self.records}))

    @property
    def provider_ids(self) -> tuple[str, ...]:
        return tuple(sorted({record.provider_id for record in self.records}))

    def actions_for_instrument(
        self,
        instrument_id: InstrumentId | str,
        start: date,
        end: date,
        *,
        provider_id: str | None = None,
    ) -> tuple[CorporateAction, ...]:
        instrument = _coerce_instrument_id(instrument_id)
        _validate_date_range(start, end)
        provider_filter = _optional_string(provider_id)
        actions = self._actions_by_instrument.get(instrument.canonical, ())
        return tuple(
            action
            for action in actions
            if start <= action.ex_date <= end and (provider_filter is None or action.provider_id == provider_filter)
        )

    def actions_for_market(
        self,
        market: Market | str,
        ex_date: date,
        *,
        provider_id: str | None = None,
    ) -> tuple[CorporateAction, ...]:
        normalized_market = _coerce_market(market)
        _require_date("ex_date", ex_date)
        provider_filter = _optional_string(provider_id)
        actions = self._actions_by_market_date.get((normalized_market, ex_date), ())
        return tuple(action for action in actions if provider_filter is None or action.provider_id == provider_filter)

    def to_json_bytes(self) -> bytes:
        payload = {
            "schema_name": CORPORATE_ACTIONS_SCHEMA_NAME,
            "schema_version": CORPORATE_ACTIONS_SCHEMA_VERSION,
            "created_at": self.created_at.isoformat(),
            "trace_id": self.trace_id,
            "run_id": self.run_id,
            "stage_id": self.stage_id,
            "record_count": len(self.records),
            "partition_keys": list(CORPORATE_ACTIONS_PARTITION_KEYS),
            "field_schema": dict(CORPORATE_ACTIONS_FIELD_SCHEMA),
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
            schema_name=CORPORATE_ACTIONS_SCHEMA_NAME,
            schema_version=CORPORATE_ACTIONS_SCHEMA_VERSION,
            content_type=CORPORATE_ACTIONS_CONTENT_TYPE,
            produced_by_run_id=run_id,
            produced_by_stage_id=stage_id,
            retention_tier=retention_tier,
            created_at=self.created_at,
        )


@dataclass(frozen=True, slots=True)
class AdjustedDailyBar:
    instrument_id: InstrumentId
    trade_date: date
    provider_id: str
    adjustment: AdjustmentMode | str
    adjustment_factor: float
    open: float
    high: float
    low: float
    close: float
    raw_open: float
    raw_high: float
    raw_low: float
    raw_close: float
    volume: float
    amount: float
    provider_source: str
    provider_source_timestamp: datetime | None
    provider_raw_response_sha256: str
    field_lineage: Mapping[str, str]
    source_raw_bronze_artifact_id: str
    source_corporate_action_artifact_ids: Sequence[str]
    currency: str | None = None

    def __post_init__(self) -> None:
        if type(self.instrument_id) is not InstrumentId:
            raise CorporateActionsDatasetError("instrument_id must be an InstrumentId")
        _require_date("trade_date", self.trade_date)
        object.__setattr__(self, "provider_id", _required_string("provider_id", self.provider_id))
        object.__setattr__(self, "adjustment", AdjustmentMode(self.adjustment))
        object.__setattr__(self, "adjustment_factor", _positive_number("adjustment_factor", self.adjustment_factor))
        object.__setattr__(self, "provider_source", _required_string("provider_source", self.provider_source))
        if self.provider_source_timestamp is not None:
            _require_aware_datetime("provider_source_timestamp", self.provider_source_timestamp)
        object.__setattr__(
            self,
            "provider_raw_response_sha256",
            ArtifactUri.for_sha256(self.provider_raw_response_sha256).digest,
        )
        object.__setattr__(
            self,
            "source_raw_bronze_artifact_id",
            _required_string("source_raw_bronze_artifact_id", self.source_raw_bronze_artifact_id),
        )
        object.__setattr__(
            self,
            "source_corporate_action_artifact_ids",
            tuple(
                sorted(
                    _required_string("source_corporate_action_artifact_id", value)
                    for value in self.source_corporate_action_artifact_ids
                )
            ),
        )
        object.__setattr__(self, "currency", _optional_upper_string(self.currency))
        for field_name in (
            "open",
            "high",
            "low",
            "close",
            "raw_open",
            "raw_high",
            "raw_low",
            "raw_close",
            "volume",
            "amount",
        ):
            object.__setattr__(self, field_name, _required_number(field_name, getattr(self, field_name)))
        _validate_ohlc(self.open, self.high, self.low, self.close)
        _validate_ohlc(self.raw_open, self.raw_high, self.raw_low, self.raw_close)
        if self.volume < 0:
            raise CorporateActionsDatasetError("volume cannot be negative")
        if self.amount < 0:
            raise CorporateActionsDatasetError("amount cannot be negative")
        object.__setattr__(self, "field_lineage", _freeze_lineage(self.field_lineage))

    @property
    def market(self) -> Market:
        return self.instrument_id.market

    @property
    def primary_key(self) -> tuple[str, date, str, str]:
        return (self.instrument_id.canonical, self.trade_date, self.provider_id, self.adjustment.value)

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
            "adjustment": self.adjustment.value,
            "adjustment_factor": self.adjustment_factor,
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "raw_open": self.raw_open,
            "raw_high": self.raw_high,
            "raw_low": self.raw_low,
            "raw_close": self.raw_close,
            "volume": self.volume,
            "amount": self.amount,
            "currency": self.currency,
            "provider_source": self.provider_source,
            "provider_source_timestamp": (
                self.provider_source_timestamp.isoformat() if self.provider_source_timestamp else None
            ),
            "provider_raw_response_sha256": self.provider_raw_response_sha256,
            "field_lineage": dict(self.field_lineage),
            "source_raw_bronze_artifact_id": self.source_raw_bronze_artifact_id,
            "source_corporate_action_artifact_ids": list(self.source_corporate_action_artifact_ids),
            "partition": self.partition_values,
        }


@dataclass(frozen=True, slots=True)
class AdjustedDailyBarsDataset:
    records: Sequence[AdjustedDailyBar]
    created_at: datetime
    trace_id: str | None = None
    run_id: str | None = None
    stage_id: str | None = None
    _bar_by_key: Mapping[tuple[str, date, str, str], AdjustedDailyBar] = field(
        init=False,
        repr=False,
        compare=False,
    )
    _bars_by_instrument: Mapping[str, tuple[AdjustedDailyBar, ...]] = field(
        init=False,
        repr=False,
        compare=False,
    )

    @classmethod
    def from_records(
        cls,
        records: Iterable[AdjustedDailyBar],
        *,
        created_at: datetime,
        trace_id: str | None = None,
        run_id: str | None = None,
        stage_id: str | None = None,
    ) -> AdjustedDailyBarsDataset:
        return cls(
            records=tuple(records),
            created_at=created_at,
            trace_id=trace_id,
            run_id=run_id,
            stage_id=stage_id,
        )

    @classmethod
    def from_raw_bars(
        cls,
        raw_bars: RawDailyBarsDataset,
        *,
        corporate_actions: CorporateActionsDataset,
        created_at: datetime,
        adjustments: Sequence[AdjustmentMode | str] = (AdjustmentMode.FORWARD, AdjustmentMode.BACKWARD),
        trace_id: str | None = None,
        run_id: str | None = None,
        stage_id: str | None = None,
    ) -> AdjustedDailyBarsDataset:
        if type(raw_bars) is not RawDailyBarsDataset:
            raise CorporateActionsDatasetError("raw_bars must be a RawDailyBarsDataset")
        if type(corporate_actions) is not CorporateActionsDataset:
            raise CorporateActionsDatasetError("corporate_actions must be a CorporateActionsDataset")
        modes = _normalize_adjustments(adjustments)
        adjusted_records = _build_adjusted_records(raw_bars, corporate_actions, modes)
        return cls.from_records(
            adjusted_records,
            created_at=created_at,
            trace_id=trace_id if trace_id is not None else raw_bars.trace_id,
            run_id=run_id if run_id is not None else raw_bars.run_id,
            stage_id=stage_id if stage_id is not None else raw_bars.stage_id,
        )

    def __post_init__(self) -> None:
        _require_aware_datetime("created_at", self.created_at)
        object.__setattr__(self, "trace_id", _optional_string(self.trace_id))
        object.__setattr__(self, "run_id", _optional_string(self.run_id))
        object.__setattr__(self, "stage_id", _optional_string(self.stage_id))

        records = tuple(self.records)
        if not records:
            raise CorporateActionsDatasetError("adjusted daily bar records are required")
        for record in records:
            if type(record) is not AdjustedDailyBar:
                raise CorporateActionsDatasetError("records must contain AdjustedDailyBar values")

        bar_by_key: dict[tuple[str, date, str, str], AdjustedDailyBar] = {}
        bars_by_instrument: dict[str, list[AdjustedDailyBar]] = defaultdict(list)
        for record in records:
            if record.primary_key in bar_by_key:
                instrument, trade_date, provider, adjustment = record.primary_key
                raise CorporateActionsDatasetError(
                    f"Duplicate adjusted daily bar key: {instrument} {trade_date.isoformat()} {provider} {adjustment}"
                )
            bar_by_key[record.primary_key] = record
            bars_by_instrument[record.instrument_id.canonical].append(record)

        sorted_records = tuple(
            sorted(
                records,
                key=lambda item: (
                    item.market.value,
                    item.instrument_id.canonical,
                    item.trade_date,
                    item.adjustment.value,
                    item.provider_id,
                ),
            )
        )
        object.__setattr__(self, "records", sorted_records)
        object.__setattr__(self, "_bar_by_key", MappingProxyType(dict(bar_by_key)))
        object.__setattr__(
            self,
            "_bars_by_instrument",
            MappingProxyType(
                {
                    instrument_id: tuple(
                        sorted(bars, key=lambda item: (item.trade_date, item.adjustment.value, item.provider_id))
                    )
                    for instrument_id, bars in bars_by_instrument.items()
                }
            ),
        )

    @property
    def provider_ids(self) -> tuple[str, ...]:
        return tuple(sorted({record.provider_id for record in self.records}))

    @property
    def source_raw_bronze_artifact_ids(self) -> tuple[str, ...]:
        return tuple(sorted({record.source_raw_bronze_artifact_id for record in self.records}))

    @property
    def source_corporate_action_artifact_ids(self) -> tuple[str, ...]:
        source_ids: set[str] = set()
        for record in self.records:
            source_ids.update(record.source_corporate_action_artifact_ids)
        return tuple(sorted(source_ids))

    def get(
        self,
        instrument_id: InstrumentId | str,
        trade_date: date,
        *,
        provider_id: str,
        adjustment: AdjustmentMode | str,
    ) -> AdjustedDailyBar:
        instrument = _coerce_instrument_id(instrument_id)
        _require_date("trade_date", trade_date)
        normalized_provider = _required_string("provider_id", provider_id)
        normalized_adjustment = AdjustmentMode(adjustment)
        key = (instrument.canonical, trade_date, normalized_provider, normalized_adjustment.value)
        try:
            return self._bar_by_key[key]
        except KeyError as exc:
            raise CorporateActionsDatasetError(
                f"Adjusted daily bar not found: {instrument.canonical} {trade_date.isoformat()} "
                f"{normalized_provider} {normalized_adjustment.value}"
            ) from exc

    def bars_for_instrument(
        self,
        instrument_id: InstrumentId | str,
        start: date,
        end: date,
        *,
        provider_id: str | None = None,
        adjustment: AdjustmentMode | str | None = None,
    ) -> tuple[AdjustedDailyBar, ...]:
        instrument = _coerce_instrument_id(instrument_id)
        _validate_date_range(start, end)
        provider_filter = _optional_string(provider_id)
        adjustment_filter = AdjustmentMode(adjustment) if adjustment is not None else None
        bars = self._bars_by_instrument.get(instrument.canonical, ())
        return tuple(
            bar
            for bar in bars
            if start <= bar.trade_date <= end
            and (provider_filter is None or bar.provider_id == provider_filter)
            and (adjustment_filter is None or bar.adjustment is adjustment_filter)
        )

    def merge_incremental(
        self,
        incremental: AdjustedDailyBarsDataset,
        *,
        created_at: datetime | None = None,
        trace_id: str | None = None,
        run_id: str | None = None,
        stage_id: str | None = None,
    ) -> AdjustedDailyBarsDataset:
        if type(incremental) is not AdjustedDailyBarsDataset:
            raise CorporateActionsDatasetError("incremental must be an AdjustedDailyBarsDataset")
        merged = dict(self._bar_by_key)
        merged.update(incremental._bar_by_key)
        return AdjustedDailyBarsDataset.from_records(
            merged.values(),
            created_at=created_at if created_at is not None else incremental.created_at,
            trace_id=trace_id if trace_id is not None else incremental.trace_id,
            run_id=run_id if run_id is not None else incremental.run_id,
            stage_id=stage_id if stage_id is not None else incremental.stage_id,
        )

    def to_json_bytes(self) -> bytes:
        payload = {
            "schema_name": ADJUSTED_DAILY_BARS_SCHEMA_NAME,
            "schema_version": ADJUSTED_DAILY_BARS_SCHEMA_VERSION,
            "created_at": self.created_at.isoformat(),
            "trace_id": self.trace_id,
            "run_id": self.run_id,
            "stage_id": self.stage_id,
            "record_count": len(self.records),
            "partition_keys": list(ADJUSTED_DAILY_BARS_PARTITION_KEYS),
            "field_schema": dict(ADJUSTED_DAILY_BARS_FIELD_SCHEMA),
            "provider_ids": list(self.provider_ids),
            "source_raw_bronze_artifact_ids": list(self.source_raw_bronze_artifact_ids),
            "source_corporate_action_artifact_ids": list(self.source_corporate_action_artifact_ids),
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
            schema_name=ADJUSTED_DAILY_BARS_SCHEMA_NAME,
            schema_version=ADJUSTED_DAILY_BARS_SCHEMA_VERSION,
            content_type=ADJUSTED_DAILY_BARS_CONTENT_TYPE,
            produced_by_run_id=run_id,
            produced_by_stage_id=stage_id,
            retention_tier=retention_tier,
            created_at=self.created_at,
        )


def _build_adjusted_records(
    raw_bars: RawDailyBarsDataset,
    corporate_actions: CorporateActionsDataset,
    modes: Sequence[AdjustmentMode],
) -> tuple[AdjustedDailyBar, ...]:
    bars_by_identity: dict[tuple[str, str], list[RawDailyBar]] = defaultdict(list)
    for raw_bar in raw_bars.records:
        bars_by_identity[(raw_bar.instrument_id.canonical, raw_bar.provider_id)].append(raw_bar)

    adjusted_records: list[AdjustedDailyBar] = []
    for (instrument_id, provider_id), bars in bars_by_identity.items():
        ordered_bars = tuple(sorted(bars, key=lambda item: item.trade_date))
        instrument = ordered_bars[0].instrument_id
        start = ordered_bars[0].trade_date
        end = ordered_bars[-1].trade_date
        actions = corporate_actions.actions_for_instrument(instrument_id, start, end, provider_id=provider_id)
        coefficients = _event_coefficients(ordered_bars, actions)
        actions_by_date: dict[date, tuple[CorporateAction, ...]] = defaultdict(tuple)
        for ex_date in coefficients:
            actions_by_date[ex_date] = tuple(action for action in actions if action.ex_date == ex_date)
        for raw_bar in ordered_bars:
            for mode in modes:
                factor, applied_actions = _factor_for_bar(raw_bar.trade_date, mode, coefficients, actions_by_date)
                adjusted_records.append(_adjusted_bar_from_raw(raw_bar, mode, factor, applied_actions))
    return tuple(adjusted_records)


def _event_coefficients(
    ordered_bars: Sequence[RawDailyBar],
    actions: Sequence[CorporateAction],
) -> Mapping[date, float]:
    grouped: dict[date, list[CorporateAction]] = defaultdict(list)
    for action in actions:
        grouped[action.ex_date].append(action)

    coefficients: dict[date, float] = {}
    for ex_date, ex_date_actions in grouped.items():
        previous_bar = _previous_raw_bar(ordered_bars, ex_date)
        coefficients[ex_date] = _event_coefficient(ex_date_actions, previous_bar.close)
    return MappingProxyType(coefficients)


def _event_coefficient(actions: Sequence[CorporateAction], previous_close: float) -> float:
    if previous_close <= 0:
        raise CorporateActionsDatasetError("previous close must be positive")
    cash_dividend = sum(action.cash_dividend_per_share for action in actions)
    if cash_dividend >= previous_close:
        raise CorporateActionsDatasetError("cash dividend cannot exceed previous close")
    bonus_ratio = sum(action.bonus_share_ratio for action in actions)
    split_multiplier = math.prod(action.split_ratio for action in actions)
    rights_ratio = sum(action.rights_issue_ratio for action in actions)
    rights_value = sum(action.rights_issue_ratio * (action.rights_issue_price or 0.0) for action in actions)
    denominator = split_multiplier * (1.0 + bonus_ratio) + rights_ratio
    theoretical_ex_price = (previous_close - cash_dividend + rights_value) / denominator
    if theoretical_ex_price <= 0:
        raise CorporateActionsDatasetError("theoretical ex-rights price must be positive")
    coefficient = theoretical_ex_price / previous_close
    if not math.isfinite(coefficient) or coefficient <= 0:
        raise CorporateActionsDatasetError("adjustment factor must be positive and finite")
    return coefficient


def _previous_raw_bar(ordered_bars: Sequence[RawDailyBar], ex_date: date) -> RawDailyBar:
    previous = [bar for bar in ordered_bars if bar.trade_date < ex_date]
    if not previous:
        raise CorporateActionsDatasetError(f"previous raw close not found before ex_date: {ex_date.isoformat()}")
    return previous[-1]


def _factor_for_bar(
    trade_date: date,
    mode: AdjustmentMode,
    coefficients: Mapping[date, float],
    actions_by_date: Mapping[date, Sequence[CorporateAction]],
) -> tuple[float, tuple[CorporateAction, ...]]:
    if mode is AdjustmentMode.FORWARD:
        applicable_dates = tuple(sorted(ex_date for ex_date in coefficients if ex_date > trade_date))
        factor = math.prod(coefficients[ex_date] for ex_date in applicable_dates)
    else:
        applicable_dates = tuple(sorted(ex_date for ex_date in coefficients if ex_date <= trade_date))
        factor = math.prod(1.0 / coefficients[ex_date] for ex_date in applicable_dates)
    applied_actions: list[CorporateAction] = []
    for ex_date in applicable_dates:
        applied_actions.extend(actions_by_date.get(ex_date, ()))
    return factor, tuple(applied_actions)


def _adjusted_bar_from_raw(
    raw_bar: RawDailyBar,
    mode: AdjustmentMode,
    factor: float,
    applied_actions: Sequence[CorporateAction],
) -> AdjustedDailyBar:
    return AdjustedDailyBar(
        instrument_id=raw_bar.instrument_id,
        trade_date=raw_bar.trade_date,
        provider_id=raw_bar.provider_id,
        adjustment=mode,
        adjustment_factor=factor,
        open=raw_bar.open * factor,
        high=raw_bar.high * factor,
        low=raw_bar.low * factor,
        close=raw_bar.close * factor,
        raw_open=raw_bar.open,
        raw_high=raw_bar.high,
        raw_low=raw_bar.low,
        raw_close=raw_bar.close,
        volume=raw_bar.volume,
        amount=raw_bar.amount,
        currency=raw_bar.currency,
        provider_source=raw_bar.provider_source,
        provider_source_timestamp=raw_bar.provider_source_timestamp,
        provider_raw_response_sha256=raw_bar.provider_raw_response_sha256,
        field_lineage=raw_bar.field_lineage,
        source_raw_bronze_artifact_id=raw_bar.source_bronze_artifact_id,
        source_corporate_action_artifact_ids=tuple(
            sorted({action.source_bronze_artifact_id for action in applied_actions})
        ),
    )


def _normalize_adjustments(adjustments: Sequence[AdjustmentMode | str]) -> tuple[AdjustmentMode, ...]:
    modes = tuple(AdjustmentMode(adjustment) for adjustment in adjustments)
    if not modes:
        raise CorporateActionsDatasetError("adjustments are required")
    if len(set(modes)) != len(modes):
        raise CorporateActionsDatasetError("adjustments cannot contain duplicates")
    return modes


def _validate_action_terms(action: CorporateAction) -> None:
    if action.action_type is CorporateActionType.CASH_DIVIDEND:
        if action.cash_dividend_per_share <= 0:
            raise CorporateActionsDatasetError("cash_dividend_per_share must be positive for cash_dividend")
        _require_no_share_terms(action)
    elif action.action_type is CorporateActionType.BONUS_SHARE:
        if action.bonus_share_ratio <= 0:
            raise CorporateActionsDatasetError("bonus_share_ratio must be positive for bonus_share")
        _require_no_cash_or_rights_terms(action)
        if action.split_ratio != 1.0:
            raise CorporateActionsDatasetError("split_ratio is only valid for share_split")
    elif action.action_type is CorporateActionType.RIGHTS_ISSUE:
        if action.rights_issue_ratio <= 0:
            raise CorporateActionsDatasetError("rights_issue_ratio must be positive for rights_issue")
        if action.rights_issue_price is None:
            raise CorporateActionsDatasetError("rights_issue_price is required for rights_issue")
        if action.cash_dividend_per_share != 0 or action.bonus_share_ratio != 0 or action.split_ratio != 1.0:
            raise CorporateActionsDatasetError("rights_issue cannot include cash, bonus, or split terms")
    elif action.action_type is CorporateActionType.SHARE_SPLIT:
        if action.split_ratio == 1.0:
            raise CorporateActionsDatasetError("split_ratio must differ from 1.0 for share_split")
        _require_no_cash_or_rights_terms(action)
        if action.bonus_share_ratio != 0:
            raise CorporateActionsDatasetError("bonus_share_ratio is only valid for bonus_share")


def _require_no_share_terms(action: CorporateAction) -> None:
    if action.bonus_share_ratio != 0 or action.split_ratio != 1.0 or action.rights_issue_ratio != 0:
        raise CorporateActionsDatasetError("cash_dividend cannot include share or rights terms")
    if action.rights_issue_price is not None:
        raise CorporateActionsDatasetError("cash_dividend cannot include rights_issue_price")


def _require_no_cash_or_rights_terms(action: CorporateAction) -> None:
    if action.cash_dividend_per_share != 0 or action.rights_issue_ratio != 0:
        raise CorporateActionsDatasetError("share actions cannot include cash or rights terms")
    if action.rights_issue_price is not None:
        raise CorporateActionsDatasetError("share actions cannot include rights_issue_price")


def _validate_instrument_exists(
    instrument_master: InstrumentMasterDataset,
    instrument: InstrumentId,
    ex_date: date,
) -> None:
    try:
        instrument_master.get(instrument, as_of=ex_date)
    except Exception as exc:
        raise CorporateActionsDatasetError(
            f"instrument_id must exist in Instrument Master as of ex_date: {instrument.canonical} "
            f"{ex_date.isoformat()}"
        ) from exc


def _validate_ex_date(
    trading_calendar: TradingCalendarDataset,
    market: Market,
    ex_date: date,
) -> None:
    try:
        is_trading_day = trading_calendar.is_trading_day(market, ex_date)
    except Exception as exc:
        raise CorporateActionsDatasetError(
            f"ex_date must be present in Trading Calendar: {market.value} {ex_date.isoformat()}"
        ) from exc
    if not is_trading_day:
        raise CorporateActionsDatasetError(f"ex_date must be a trading day: {market.value} {ex_date.isoformat()}")


def _coerce_instrument_id(value: object) -> InstrumentId:
    if type(value) is InstrumentId:
        return value
    if type(value) is str:
        try:
            return InstrumentId.parse(value)
        except Exception as exc:
            raise CorporateActionsDatasetError(f"instrument_id is invalid: {value!r}") from exc
    raise CorporateActionsDatasetError("instrument_id is required")


def _coerce_market(value: Market | str) -> Market:
    try:
        return Market(value)
    except ValueError as exc:
        raise CorporateActionsDatasetError(f"Unsupported market: {value}") from exc


def _validate_ohlc(open_price: float, high: float, low: float, close: float) -> None:
    if min(open_price, high, low, close) < 0:
        raise CorporateActionsDatasetError("OHLC prices cannot be negative")
    if not (low <= open_price <= high and low <= close <= high):
        raise CorporateActionsDatasetError("OHLC relationship must satisfy low <= open/close <= high")


def _freeze_lineage(lineage: Mapping[str, str]) -> Mapping[str, str]:
    normalized: dict[str, str] = {}
    for key, value in lineage.items():
        normalized[_required_string("field lineage key", key)] = _required_string("field lineage value", value)
    return MappingProxyType(normalized)


def _validate_date_range(start: date, end: date) -> None:
    _require_date("start", start)
    _require_date("end", end)
    if end < start:
        raise CorporateActionsDatasetError("end must be on or after start")


def _require_date(field_name: str, value: object) -> None:
    if type(value) is not date:
        raise CorporateActionsDatasetError(f"{field_name} must be a date")


def _require_aware_datetime(field_name: str, value: object) -> None:
    if type(value) is not datetime or value.tzinfo is None or value.utcoffset() is None:
        raise CorporateActionsDatasetError(f"{field_name} must be timezone-aware")


def _required_number(field_name: str, value: object) -> float:
    if _is_missing(value):
        raise CorporateActionsDatasetError(f"{field_name} is required")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise CorporateActionsDatasetError(f"{field_name} must be numeric") from exc
    if not math.isfinite(number):
        raise CorporateActionsDatasetError(f"{field_name} must be finite")
    return number


def _non_negative_number(field_name: str, value: object) -> float:
    number = _required_number(field_name, value)
    if number < 0:
        raise CorporateActionsDatasetError(f"{field_name} cannot be negative")
    return number


def _positive_number(field_name: str, value: object) -> float:
    number = _required_number(field_name, value)
    if number <= 0:
        raise CorporateActionsDatasetError(f"{field_name} must be positive")
    return number


def _required_string(field_name: str, value: object | None) -> str:
    if type(value) is not str:
        raise CorporateActionsDatasetError(f"{field_name} is required")
    normalized = value.strip()
    if not normalized:
        raise CorporateActionsDatasetError(f"{field_name} is required")
    return normalized


def _optional_string(value: object | None) -> str | None:
    if value is None:
        return None
    if type(value) is not str:
        raise CorporateActionsDatasetError("optional string value must be a string")
    normalized = value.strip()
    return normalized or None


def _optional_upper_string(value: object | None) -> str | None:
    normalized = _optional_string(value)
    return normalized.upper() if normalized is not None else None


def _is_missing(value: object) -> bool:
    return value is None or value == ""


__all__ = [
    "ADJUSTED_DAILY_BARS_CONTENT_TYPE",
    "ADJUSTED_DAILY_BARS_FIELD_SCHEMA",
    "ADJUSTED_DAILY_BARS_PARTITION_KEYS",
    "ADJUSTED_DAILY_BARS_SCHEMA_NAME",
    "ADJUSTED_DAILY_BARS_SCHEMA_VERSION",
    "CORPORATE_ACTIONS_CONTENT_TYPE",
    "CORPORATE_ACTIONS_FIELD_SCHEMA",
    "CORPORATE_ACTIONS_PARTITION_KEYS",
    "CORPORATE_ACTIONS_SCHEMA_NAME",
    "CORPORATE_ACTIONS_SCHEMA_VERSION",
    "AdjustedDailyBar",
    "AdjustedDailyBarsDataset",
    "AdjustmentMode",
    "CorporateAction",
    "CorporateActionType",
    "CorporateActionsDataset",
    "CorporateActionsDatasetError",
]
