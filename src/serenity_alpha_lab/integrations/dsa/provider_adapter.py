from __future__ import annotations

import hashlib
import importlib
import json
import math
import sys
from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

from serenity_alpha_lab.application.config_profiles import (
    ConfigProfileError,
    RuntimeProfile,
    RuntimeSettings,
    load_runtime_settings,
    profile_policy,
)
from serenity_alpha_lab.application.tracing import current_trace_context
from serenity_alpha_lab.domain.instruments import InstrumentId, Market
from serenity_alpha_lab.domain.providers import (
    Capability,
    DataBatch,
    ProviderCapabilities,
    ProviderCapability,
    ProviderError,
    ProviderErrorCategory,
    ProviderWarning,
    Provenance,
)
from serenity_alpha_lab.integrations.dsa.entrypoints import resolve_dsa_root


DSA_PROVIDER_ID = "dsa_compatibility"
DSA_DAILY_BAR_SCHEMA_NAME = "market.daily_bars.dsa_compatibility"
DSA_DAILY_BAR_SCHEMA_VERSION = "1.0.0"

_SUPPORTED_DAILY_BAR_MARKETS = (Market.CN, Market.HK, Market.US, Market.JP, Market.KR, Market.TW)
_REQUIRED_DAILY_BAR_FIELDS = ("date", "open", "high", "low", "close", "volume")
_OPTIONAL_DAILY_BAR_FIELDS = ("amount", "pct_chg")
_PASSTHROUGH_DAILY_BAR_FIELDS = ("ma5", "ma10", "ma20", "volume_ratio")


ManagerFactory = Callable[[], Any]
Clock = Callable[[], datetime]
DateClock = Callable[[], date]


class DsaProviderCompatibilityAdapter:
    """MarketDataProvider facade over DSA's synchronous DataFetcherManager.

    The adapter is intentionally injection-first: tests and CI pass a DSA-like
    manager, while production callers opt into the lazy isolated-worktree
    factory through :meth:`from_runtime_settings`.
    """

    provider_id = DSA_PROVIDER_ID

    def __init__(
        self,
        *,
        manager: Any | None = None,
        manager_factory: ManagerFactory | None = None,
        settings: RuntimeSettings | None = None,
        clock: Clock | None = None,
        freshness_ttl: timedelta = timedelta(days=1),
    ) -> None:
        self._manager = manager
        self._manager_factory = manager_factory or create_default_dsa_data_fetcher_manager
        self._settings = settings or RuntimeSettings()
        self._clock = clock or (lambda: datetime.now(UTC))
        self._freshness_ttl = freshness_ttl

    @classmethod
    def from_runtime_settings(
        cls,
        *,
        settings: RuntimeSettings | None = None,
        dsa_root: str | Path | None = None,
        clock: Clock | None = None,
    ) -> DsaProviderCompatibilityAdapter:
        resolved_settings = settings or load_runtime_settings()
        _assert_real_provider_calls_allowed(resolved_settings)
        return cls(
            manager_factory=lambda: create_default_dsa_data_fetcher_manager(dsa_root),
            settings=resolved_settings,
            clock=clock,
        )

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            (
                Capability(
                    capability=ProviderCapability.DAILY_BARS,
                    schema_name=DSA_DAILY_BAR_SCHEMA_NAME,
                    schema_version=DSA_DAILY_BAR_SCHEMA_VERSION,
                    markets=_SUPPORTED_DAILY_BAR_MARKETS,
                    frequency="1d",
                    fields=(
                        "instrument_id",
                        *_REQUIRED_DAILY_BAR_FIELDS,
                        *_OPTIONAL_DAILY_BAR_FIELDS,
                        *_PASSTHROUGH_DAILY_BAR_FIELDS,
                        "source",
                    ),
                ),
            )
        )

    def list_instruments(self, as_of: date) -> DataBatch[Mapping[str, object]]:
        raise _unsupported(ProviderCapability.INSTRUMENTS)

    def get_calendar(self, start: date, end: date) -> DataBatch[Mapping[str, object]]:
        raise _unsupported(ProviderCapability.TRADING_CALENDAR)

    def get_daily_bars(
        self,
        instruments: Sequence[InstrumentId],
        start: date,
        end: date,
    ) -> DataBatch[Mapping[str, object]]:
        requested_at = self._now()
        if end < start:
            raise ProviderError(
                category=ProviderErrorCategory.DATA_INVALID,
                provider_id=self.provider_id,
                operation=ProviderCapability.DAILY_BARS,
                message="daily bars end date cannot be before start date",
            )

        normalized_instruments = tuple(instruments)
        records: list[dict[str, object]] = []
        sources: list[str] = []
        warnings: list[ProviderWarning] = []
        manager = self._manager_instance()

        for instrument in normalized_instruments:
            if type(instrument) is not InstrumentId:
                raise TypeError("get_daily_bars requires InstrumentId values")
            dsa_symbol = instrument.to_dsa_symbol()
            frame, source = self._call_manager_daily_data(
                manager,
                dsa_symbol=dsa_symbol,
                start=start,
                end=end,
            )
            rows, row_warnings = _normalize_daily_bar_rows(
                frame,
                instrument=instrument,
                source=source,
                provider_id=self.provider_id,
            )
            records.extend(rows)
            warnings.extend(row_warnings)
            sources.append(source)

        if normalized_instruments and not records:
            raise ProviderError(
                category=ProviderErrorCategory.DATA_INVALID,
                provider_id=self.provider_id,
                operation=ProviderCapability.DAILY_BARS,
                message="DSA daily bars returned no records",
            )

        fetched_at = self._now()
        source_id = _source_provider_id(sources)
        provenance = Provenance(
            provider_id=source_id,
            provider_version=None,
            operation=ProviderCapability.DAILY_BARS,
            request_parameters={
                "instrument_ids": [instrument.canonical for instrument in normalized_instruments],
                "dsa_symbols": [instrument.to_dsa_symbol() for instrument in normalized_instruments],
                "start": start.isoformat(),
                "end": end.isoformat(),
                "days": 30,
            },
            requested_at=requested_at,
            fetched_at=fetched_at,
            raw_response_sha256=_sha256_records(records),
            field_lineage=_field_lineage(records, source_id=source_id),
            source_timestamp=_source_timestamp(records),
            trace_id=_active_trace_field("trace_id"),
            run_id=_active_trace_field("run_id"),
            stage_id=_active_trace_field("stage_id"),
        )
        return DataBatch(
            records=records,
            schema_name=DSA_DAILY_BAR_SCHEMA_NAME,
            schema_version=DSA_DAILY_BAR_SCHEMA_VERSION,
            provenance=provenance,
            fresh_until=fetched_at + self._freshness_ttl,
            warnings=tuple(_dedupe_warnings(warnings)),
        )

    def get_fundamentals(
        self,
        instruments: Sequence[InstrumentId],
        as_of: datetime,
    ) -> DataBatch[Mapping[str, object]]:
        raise _unsupported(ProviderCapability.FUNDAMENTALS)

    def _manager_instance(self) -> Any:
        if self._manager is not None:
            return self._manager
        _assert_real_provider_calls_allowed(self._settings)
        self._manager = self._manager_factory()
        return self._manager

    def _call_manager_daily_data(
        self,
        manager: Any,
        *,
        dsa_symbol: str,
        start: date,
        end: date,
    ) -> tuple[Any, str]:
        try:
            result = manager.get_daily_data(
                dsa_symbol,
                start_date=start.isoformat(),
                end_date=end.isoformat(),
                days=30,
            )
        except Exception as exc:
            raise _provider_error_from_exception(exc, provider_id=self.provider_id) from exc

        if isinstance(result, tuple) and len(result) >= 2:
            frame, source = result[0], str(result[1] or "unknown")
        else:
            frame = result
            source = type(manager).__name__
        return frame, source.strip() or "unknown"

    def _now(self) -> datetime:
        current = self._clock()
        if current.tzinfo is None or current.utcoffset() is None:
            return current.replace(tzinfo=UTC)
        return current.astimezone(UTC)


class DsaStockHistoryCompatibilityFacade:
    """Feature-flag facade for legacy stock-history callers."""

    def __init__(
        self,
        *,
        manager: Any,
        provider: DsaProviderCompatibilityAdapter,
        clock: DateClock | None = None,
    ) -> None:
        self._manager = manager
        self._provider = provider
        self._clock = clock or date.today

    def get_history_data(
        self,
        stock_code: str,
        *,
        period: str = "daily",
        days: int = 30,
        use_provider_contract: bool = False,
    ) -> dict[str, object]:
        if period != "daily":
            raise ValueError("暂不支持非 daily 周期，目前仅支持 'daily'。")
        if use_provider_contract:
            return self._get_history_data_via_provider(stock_code, period=period, days=days)
        frame, _source = self._manager.get_daily_data(stock_code, days=days)
        return self._history_payload(stock_code, period, _legacy_rows_from_frame(frame))

    def _get_history_data_via_provider(self, stock_code: str, *, period: str, days: int) -> dict[str, object]:
        end = self._clock()
        start = end - timedelta(days=days * 2)
        instrument = _instrument_from_legacy_stock_code(stock_code)
        batch = self._provider.get_daily_bars([instrument], start, end)
        return self._history_payload(stock_code, period, _legacy_rows_from_batch(batch))

    def _history_payload(self, stock_code: str, period: str, rows: list[dict[str, object]]) -> dict[str, object]:
        return {
            "stock_code": stock_code,
            "stock_name": self._stock_name(stock_code),
            "period": period,
            "data": rows,
        }

    def _stock_name(self, stock_code: str) -> str | None:
        getter = getattr(self._manager, "get_stock_name", None)
        if not callable(getter):
            return None
        return getter(stock_code)


def create_default_dsa_data_fetcher_manager(root: str | Path | None = None) -> Any:
    dsa_root = resolve_dsa_root(root)
    root_text = str(dsa_root)
    if root_text not in sys.path:
        sys.path.insert(0, root_text)
    module = importlib.import_module("data_provider.base")
    return module.DataFetcherManager()


def _assert_real_provider_calls_allowed(settings: RuntimeSettings) -> None:
    policy = profile_policy(settings)
    if settings.profile is RuntimeProfile.CI:
        raise ConfigProfileError("CI profile forbids real provider calls")
    if not policy.provider_calls_allowed:
        raise ConfigProfileError(f"{settings.profile.value} profile forbids real provider calls")


def _unsupported(capability: ProviderCapability) -> ProviderError:
    return ProviderError(
        category=ProviderErrorCategory.PERMANENT,
        provider_id=DSA_PROVIDER_ID,
        operation=capability,
        message=f"DSA compatibility adapter does not support {capability.value}",
    )


def _normalize_daily_bar_rows(
    frame: Any,
    *,
    instrument: InstrumentId,
    source: str,
    provider_id: str,
) -> tuple[list[dict[str, object]], list[ProviderWarning]]:
    rows = _frame_records(frame)
    if not rows:
        raise ProviderError(
            category=ProviderErrorCategory.DATA_INVALID,
            provider_id=provider_id,
            operation=ProviderCapability.DAILY_BARS,
            message="DSA daily bars returned an empty DataFrame",
        )

    columns = {str(column) for column in _frame_columns(frame, rows)}
    missing_required = [field for field in _REQUIRED_DAILY_BAR_FIELDS if field not in columns]
    if missing_required:
        raise ProviderError(
            category=ProviderErrorCategory.SCHEMA_DRIFT,
            provider_id=provider_id,
            operation=ProviderCapability.DAILY_BARS,
            message=f"DSA daily bars missing required columns: {', '.join(missing_required)}",
        )

    warnings = [
        ProviderWarning(
            code="partial_fields",
            message="DSA daily bars missing optional fields",
            fields=tuple(field for field in _OPTIONAL_DAILY_BAR_FIELDS if field not in columns),
        )
    ] if any(field not in columns for field in _OPTIONAL_DAILY_BAR_FIELDS) else []

    normalized: list[dict[str, object]] = []
    for row in rows:
        normalized_row: dict[str, object] = {
            "instrument_id": instrument.canonical,
            "date": _coerce_date_text(row.get("date")),
            "open": _required_number(row.get("open"), "open"),
            "high": _required_number(row.get("high"), "high"),
            "low": _required_number(row.get("low"), "low"),
            "close": _required_number(row.get("close"), "close"),
            "volume": _required_number(row.get("volume"), "volume"),
            "source": source,
        }
        for field in _OPTIONAL_DAILY_BAR_FIELDS:
            if field in row:
                normalized_row[field] = _optional_number(row.get(field))
        for field in _PASSTHROUGH_DAILY_BAR_FIELDS:
            if field in row:
                normalized_row[field] = _optional_number(row.get(field))
        normalized.append(normalized_row)
    return normalized, warnings


def _frame_records(frame: Any) -> list[dict[str, Any]]:
    if frame is None:
        return []
    if bool(getattr(frame, "empty", False)):
        return []
    if hasattr(frame, "to_dict"):
        records = frame.to_dict(orient="records")
    else:
        records = list(frame)
    return [dict(record) for record in records]


def _frame_columns(frame: Any, rows: Sequence[Mapping[str, Any]]) -> tuple[str, ...]:
    columns = getattr(frame, "columns", None)
    if columns is not None:
        return tuple(str(column) for column in columns)
    keys: set[str] = set()
    for row in rows:
        keys.update(str(key) for key in row)
    return tuple(sorted(keys))


def _coerce_date_text(value: Any) -> str:
    if _is_missing(value):
        raise _data_invalid("daily bar date is required")
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if hasattr(value, "to_pydatetime"):
        return value.to_pydatetime().date().isoformat()
    text = str(value).strip()
    try:
        return datetime.fromisoformat(text).date().isoformat()
    except ValueError:
        try:
            return date.fromisoformat(text).isoformat()
        except ValueError as exc:
            raise _data_invalid(f"daily bar date is invalid: {text!r}") from exc


def _required_number(value: Any, field: str) -> float:
    number = _optional_number(value)
    if number is None:
        raise _data_invalid(f"daily bar {field} is required")
    return number


def _optional_number(value: Any) -> float | None:
    if _is_missing(value):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise _data_invalid(f"daily bar numeric value is invalid: {value!r}") from exc
    if not math.isfinite(number):
        return None
    return number


def _is_missing(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    try:
        if bool(value != value):
            return True
    except Exception:
        pass
    if isinstance(value, str) and value.strip().lower() in {"", "nan", "none", "null", "na", "n/a"}:
        return True
    return False


def _data_invalid(message: str) -> ProviderError:
    return ProviderError(
        category=ProviderErrorCategory.DATA_INVALID,
        provider_id=DSA_PROVIDER_ID,
        operation=ProviderCapability.DAILY_BARS,
        message=message,
    )


def _provider_error_from_exception(exc: Exception, *, provider_id: str) -> ProviderError:
    return ProviderError(
        category=_classify_exception(exc),
        provider_id=provider_id,
        operation=ProviderCapability.DAILY_BARS,
        message=str(exc) or type(exc).__name__,
    )


def _classify_exception(exc: Exception) -> ProviderErrorCategory:
    text = f"{type(exc).__name__} {exc}".lower()
    if any(token in text for token in ("429", "rate limit", "rate_limited", "too many", "限流")):
        return ProviderErrorCategory.RATE_LIMITED
    if any(token in text for token in ("auth", "unauthor", "forbidden", "permission", "api key", "apikey", "凭证")):
        return ProviderErrorCategory.AUTH
    if any(token in text for token in ("schema", "column", "keyerror", "columns", "字段")):
        return ProviderErrorCategory.SCHEMA_DRIFT
    if any(token in text for token in ("empty", "no data", "not found", "未获取到", "暂无可用")):
        return ProviderErrorCategory.DATA_INVALID
    return ProviderErrorCategory.RETRYABLE


def _source_provider_id(sources: Sequence[str]) -> str:
    unique_sources = tuple(dict.fromkeys(source.strip() or "unknown" for source in sources))
    if len(unique_sources) == 1:
        return f"dsa:{unique_sources[0]}"
    if not unique_sources:
        return "dsa:unknown"
    return "dsa:mixed"


def _sha256_records(records: Sequence[Mapping[str, object]]) -> str:
    payload = json.dumps(records, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _field_lineage(records: Sequence[Mapping[str, object]], *, source_id: str) -> Mapping[str, str]:
    fields: set[str] = set()
    for record in records:
        fields.update(str(field) for field in record)
    return {field: f"{source_id}.{field}" for field in sorted(fields)}


def _source_timestamp(records: Sequence[Mapping[str, object]]) -> datetime | None:
    dates: list[date] = []
    for record in records:
        value = record.get("date")
        if isinstance(value, str):
            try:
                dates.append(date.fromisoformat(value))
            except ValueError:
                continue
    if not dates:
        return None
    return datetime.combine(max(dates), datetime.min.time(), tzinfo=UTC)


def _active_trace_field(field_name: str) -> str | None:
    context = current_trace_context()
    return None if context is None else getattr(context, field_name)


def _dedupe_warnings(warnings: Sequence[ProviderWarning]) -> tuple[ProviderWarning, ...]:
    deduped: dict[tuple[str, tuple[str, ...]], ProviderWarning] = {}
    for warning in warnings:
        deduped.setdefault((warning.code, tuple(warning.fields)), warning)
    return tuple(deduped.values())


def _instrument_from_legacy_stock_code(stock_code: str) -> InstrumentId:
    text = str(stock_code or "").strip()
    market = Market.CN if text.isdigit() and len(text) == 6 else None
    return InstrumentId.from_legacy(text, market=market)


def _legacy_rows_from_frame(frame: Any) -> list[dict[str, object]]:
    rows = _frame_records(frame)
    return [_legacy_history_row(row) for row in rows]


def _legacy_rows_from_batch(batch: DataBatch[Mapping[str, object]]) -> list[dict[str, object]]:
    return [_legacy_history_row(dict(record)) for record in batch.records]


def _legacy_history_row(row: Mapping[str, Any]) -> dict[str, object]:
    return {
        "date": _coerce_date_text(row.get("date")),
        "open": _required_number(row.get("open"), "open"),
        "high": _required_number(row.get("high"), "high"),
        "low": _required_number(row.get("low"), "low"),
        "close": _required_number(row.get("close"), "close"),
        "volume": _optional_number(row.get("volume")),
        "amount": _optional_number(row.get("amount")),
        "change_percent": _optional_number(row.get("pct_chg")),
    }


__all__ = [
    "DSA_DAILY_BAR_SCHEMA_NAME",
    "DSA_DAILY_BAR_SCHEMA_VERSION",
    "DSA_PROVIDER_ID",
    "DsaProviderCompatibilityAdapter",
    "DsaStockHistoryCompatibilityFacade",
    "create_default_dsa_data_fetcher_manager",
]
