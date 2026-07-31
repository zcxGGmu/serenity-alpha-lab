from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from pathlib import Path
from types import MappingProxyType

from serenity_alpha_lab.datasets import RAW_DAILY_BARS_SCHEMA_NAME, RAW_DAILY_BARS_SCHEMA_VERSION
from serenity_alpha_lab.datasets.schema_registry import default_dataset_schema_registry
from serenity_alpha_lab.domain.instruments import Market
from serenity_alpha_lab.domain.providers import (
    DataBatch,
    ProviderCapability,
    ProviderError,
    ProviderErrorCategory,
    Provenance,
)


FIXTURE_REQUESTED_AT = datetime(2026, 7, 23, 1, 0, tzinfo=UTC)
FIXTURE_FETCHED_AT = datetime(2026, 7, 23, 1, 0, 2, tzinfo=UTC)
FIXTURE_FRESH_UNTIL = FIXTURE_FETCHED_AT + timedelta(days=1)
FIXTURE_SOURCE_TIMESTAMP = datetime(2026, 7, 22, tzinfo=UTC)

_FORBIDDEN_TEXT = (
    "api_key",
    "authorization",
    "bearer ",
    "cookie",
    "secret",
    "token=",
    "/users/",
    "c:\\",
)


class ProviderFixtureStatus(StrEnum):
    SUCCESS = "success"
    TIMEOUT = "timeout"
    EMPTY = "empty"
    SCHEMA_DRIFT = "schema_drift"


@dataclass(frozen=True, slots=True)
class ProviderFixtureSchema:
    schema_name: str
    schema_version: str
    capability: ProviderCapability
    required_fields: Sequence[str]
    optional_fields: Sequence[str] = ()
    dataset_schema_hash: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "schema_name", _required_string("schema_name", self.schema_name))
        object.__setattr__(self, "schema_version", _required_string("schema_version", self.schema_version))
        object.__setattr__(self, "capability", ProviderCapability(self.capability))
        required_fields = _unique_tuple(_required_string("required field", field) for field in self.required_fields)
        if not required_fields:
            raise ValueError("required_fields is required")
        object.__setattr__(self, "required_fields", required_fields)
        object.__setattr__(
            self,
            "optional_fields",
            _unique_tuple(_required_string("optional field", field) for field in self.optional_fields),
        )
        object.__setattr__(self, "dataset_schema_hash", _optional_string(self.dataset_schema_hash))

    @property
    def fields(self) -> tuple[str, ...]:
        return (*self.required_fields, *self.optional_fields)

    def validate_records(self, records: Sequence[Mapping[str, object]]) -> None:
        for index, record in enumerate(records):
            missing = [field for field in self.required_fields if field not in record]
            if missing:
                raise ValueError(
                    f"{self.schema_name} fixture record {index} missing required fields: {', '.join(missing)}"
                )

    def field_lineage(self, provider_id: str, records: Sequence[Mapping[str, object]]) -> Mapping[str, str]:
        fields: set[str] = set(self.required_fields)
        for record in records:
            fields.update(str(field) for field in record)
        source_id = f"fixture:{provider_id}"
        return {field: f"{source_id}.{field}" for field in sorted(fields)}

    def to_record(self) -> dict[str, object]:
        return {
            "schema_name": self.schema_name,
            "schema_version": self.schema_version,
            "capability": self.capability.value,
            "required_fields": list(self.required_fields),
            "optional_fields": list(self.optional_fields),
            "dataset_schema_hash": self.dataset_schema_hash,
        }


@dataclass(frozen=True, slots=True)
class ProviderContractFixtureCase:
    case_id: str
    provider_id: str
    provider_version: str
    market: Market
    capability: ProviderCapability
    request_parameters: Mapping[str, object]
    raw_response: object
    schema: ProviderFixtureSchema
    status: ProviderFixtureStatus = ProviderFixtureStatus.SUCCESS
    records: Sequence[Mapping[str, object]] = ()
    expected_error_category: ProviderErrorCategory | None = None
    failure_message: str | None = None
    requested_at: datetime = FIXTURE_REQUESTED_AT
    fetched_at: datetime = FIXTURE_FETCHED_AT
    source_timestamp: datetime | None = FIXTURE_SOURCE_TIMESTAMP
    fresh_until: datetime = FIXTURE_FRESH_UNTIL

    def __post_init__(self) -> None:
        object.__setattr__(self, "case_id", _required_string("case_id", self.case_id))
        object.__setattr__(self, "provider_id", _required_string("provider_id", self.provider_id).lower())
        object.__setattr__(self, "provider_version", _required_string("provider_version", self.provider_version))
        object.__setattr__(self, "market", Market(self.market))
        object.__setattr__(self, "capability", ProviderCapability(self.capability))
        object.__setattr__(self, "status", ProviderFixtureStatus(self.status))
        if type(self.schema) is not ProviderFixtureSchema:
            raise TypeError("schema must be ProviderFixtureSchema")
        if self.schema.capability is not self.capability:
            raise ValueError("case capability must match fixture schema capability")

        request_parameters = _freeze_json_mapping(self.request_parameters)
        raw_response = _freeze_json_value(self.raw_response)
        records = tuple(_freeze_json_mapping(record) for record in self.records)
        object.__setattr__(self, "request_parameters", request_parameters)
        object.__setattr__(self, "raw_response", raw_response)
        object.__setattr__(self, "records", records)

        expected_error_category = self.expected_error_category
        if expected_error_category is not None:
            expected_error_category = ProviderErrorCategory(expected_error_category)
        object.__setattr__(self, "expected_error_category", expected_error_category)
        object.__setattr__(self, "failure_message", _optional_string(self.failure_message))
        _require_aware_datetime("requested_at", self.requested_at)
        _require_aware_datetime("fetched_at", self.fetched_at)
        _require_aware_datetime("fresh_until", self.fresh_until)
        if self.source_timestamp is not None:
            _require_aware_datetime("source_timestamp", self.source_timestamp)

        _assert_sanitized(self.to_snapshot_record(include_hash=False))

        if self.status is ProviderFixtureStatus.SUCCESS:
            if expected_error_category is not None:
                raise ValueError("success fixtures cannot declare expected_error_category")
            if not records:
                raise ValueError("success fixtures require normalized records")
            self.schema.validate_records(records)
            return

        if expected_error_category is None:
            raise ValueError("error fixtures require expected_error_category")
        if records:
            raise ValueError("error fixtures must not include normalized success records")

    @property
    def raw_response_sha256(self) -> str:
        return _sha256_json(self.raw_response)

    def to_data_batch(
        self,
        *,
        trace_id: str | None = None,
        run_id: str | None = None,
        stage_id: str | None = None,
    ) -> DataBatch[Mapping[str, object]]:
        if self.status is not ProviderFixtureStatus.SUCCESS:
            raise self.to_provider_error()
        provenance = Provenance(
            provider_id=f"fixture:{self.provider_id}",
            provider_version=self.provider_version,
            operation=self.capability,
            request_parameters=self.request_parameters,
            requested_at=self.requested_at,
            fetched_at=self.fetched_at,
            raw_response_sha256=self.raw_response_sha256,
            field_lineage=self.schema.field_lineage(self.provider_id, self.records),
            source_timestamp=self.source_timestamp,
            trace_id=trace_id,
            run_id=run_id,
            stage_id=stage_id,
        )
        return DataBatch(
            records=self.records,
            schema_name=self.schema.schema_name,
            schema_version=self.schema.schema_version,
            provenance=provenance,
            fresh_until=self.fresh_until,
        )

    def to_provider_error(self) -> ProviderError:
        if self.status is ProviderFixtureStatus.SUCCESS:
            raise ValueError("success fixtures do not map to ProviderError")
        assert self.expected_error_category is not None
        return ProviderError(
            category=self.expected_error_category,
            provider_id=f"fixture:{self.provider_id}",
            operation=self.capability,
            message=self.failure_message or f"{self.provider_id} {self.status.value} fixture",
        )

    def to_snapshot_record(self, *, include_hash: bool = True) -> dict[str, object]:
        record: dict[str, object] = {
            "case_id": self.case_id,
            "provider_id": self.provider_id,
            "provider_version": self.provider_version,
            "market": self.market.value,
            "capability": self.capability.value,
            "status": self.status.value,
            "request_parameters": _json_ready(self.request_parameters),
            "raw_response": _json_ready(self.raw_response),
            "schema": self.schema.to_record(),
            "records": _json_ready(self.records),
            "expected_error_category": (
                None if self.expected_error_category is None else self.expected_error_category.value
            ),
            "failure_message": self.failure_message,
            "requested_at": self.requested_at.isoformat(),
            "fetched_at": self.fetched_at.isoformat(),
            "source_timestamp": None if self.source_timestamp is None else self.source_timestamp.isoformat(),
            "fresh_until": self.fresh_until.isoformat(),
        }
        if include_hash:
            record["raw_response_sha256"] = self.raw_response_sha256
        return record


@dataclass(frozen=True, slots=True)
class ProviderContractFixtureCatalog:
    cases: Sequence[ProviderContractFixtureCase]

    def __post_init__(self) -> None:
        cases = tuple(self.cases)
        if not cases:
            raise ValueError("fixture cases are required")
        for case in cases:
            if type(case) is not ProviderContractFixtureCase:
                raise TypeError("cases must contain ProviderContractFixtureCase values")
        case_ids = [case.case_id for case in cases]
        duplicates = {case_id for case_id in case_ids if case_ids.count(case_id) > 1}
        if duplicates:
            raise ValueError(f"Duplicate provider fixture case ids: {', '.join(sorted(duplicates))}")
        object.__setattr__(self, "cases", cases)

    @property
    def provider_ids(self) -> tuple[str, ...]:
        return tuple(sorted({case.provider_id for case in self.cases}))

    @property
    def dataset_schema_hash(self) -> str | None:
        hashes = tuple(
            dict.fromkeys(case.schema.dataset_schema_hash for case in self.cases if case.schema.dataset_schema_hash)
        )
        if len(hashes) > 1:
            raise ValueError("fixture catalog contains multiple dataset schema hashes")
        return hashes[0] if hashes else None

    def success_cases(self) -> tuple[ProviderContractFixtureCase, ...]:
        return tuple(case for case in self.cases if case.status is ProviderFixtureStatus.SUCCESS)

    def error_cases(self) -> tuple[ProviderContractFixtureCase, ...]:
        return tuple(case for case in self.cases if case.status is not ProviderFixtureStatus.SUCCESS)

    def get(self, case_id: str) -> ProviderContractFixtureCase:
        normalized = _required_string("case_id", case_id)
        for case in self.cases:
            if case.case_id == normalized:
                return case
        raise KeyError(f"Provider fixture case not found: {normalized}")


def default_provider_contract_fixture_catalog() -> ProviderContractFixtureCatalog:
    dataset_schema_hash = default_dataset_schema_registry().get(
        RAW_DAILY_BARS_SCHEMA_NAME,
        RAW_DAILY_BARS_SCHEMA_VERSION,
    ).schema_hash
    return ProviderContractFixtureCatalog(
        (
            _daily_bar_success_case(
                provider_id="akshare",
                provider_version="fixture-2026.07",
                market=Market.CN,
                provider_symbol="600519",
                endpoint="stock_zh_a_hist",
                raw_response={
                    "columns": ["date", "open", "high", "low", "close", "volume", "amount"],
                    "rows": [["2026-07-22", 1680.0, 1690.5, 1668.0, 1688.0, 1203000.0, 2030664000.0]],
                },
                dataset_schema_hash=dataset_schema_hash,
                record={
                    "instrument_id": "600519.XSHG",
                    "market": "cn",
                    "exchange": "XSHG",
                    "date": "2026-07-22",
                    "open": 1680.0,
                    "high": 1690.5,
                    "low": 1668.0,
                    "close": 1688.0,
                    "volume": 1203000.0,
                    "amount": 2030664000.0,
                    "currency": "CNY",
                    "adjustment": "unadjusted",
                    "provider_source": "akshare.stock_zh_a_hist",
                },
            ),
            _daily_bar_success_case(
                provider_id="efinance",
                provider_version="fixture-2026.07",
                market=Market.CN,
                provider_symbol="600519",
                endpoint="stock.get_quote_history",
                raw_response={
                    "name": "Fixture Moutai",
                    "rows": [
                        {
                            "date": "2026-07-22",
                            "open": 1681.0,
                            "high": 1691.0,
                            "low": 1670.0,
                            "close": 1686.5,
                            "volume": 1180000.0,
                        }
                    ],
                },
                dataset_schema_hash=dataset_schema_hash,
                record={
                    "instrument_id": "600519.XSHG",
                    "market": "cn",
                    "exchange": "XSHG",
                    "date": "2026-07-22",
                    "open": 1681.0,
                    "high": 1691.0,
                    "low": 1670.0,
                    "close": 1686.5,
                    "volume": 1180000.0,
                    "currency": "CNY",
                    "adjustment": "unadjusted",
                    "provider_source": "efinance.stock.get_quote_history",
                },
            ),
            _daily_bar_success_case(
                provider_id="tushare",
                provider_version="fixture-2026.07",
                market=Market.CN,
                provider_symbol="600519.SH",
                endpoint="daily",
                raw_response={
                    "fields": ["ts_code", "trade_date", "open", "high", "low", "close", "vol", "amount"],
                    "items": [["600519.SH", "20260722", 1682.0, 1692.0, 1672.0, 1687.0, 119.0, 200700.0]],
                },
                dataset_schema_hash=dataset_schema_hash,
                record={
                    "instrument_id": "600519.XSHG",
                    "market": "cn",
                    "exchange": "XSHG",
                    "date": "2026-07-22",
                    "open": 1682.0,
                    "high": 1692.0,
                    "low": 1672.0,
                    "close": 1687.0,
                    "volume": 1190000.0,
                    "amount": 2007000000.0,
                    "currency": "CNY",
                    "adjustment": "unadjusted",
                    "provider_source": "tushare.daily",
                },
            ),
            _daily_bar_success_case(
                provider_id="baostock",
                provider_version="fixture-2026.07",
                market=Market.CN,
                provider_symbol="sh.600519",
                endpoint="query_history_k_data_plus",
                raw_response={
                    "fields": "date,code,open,high,low,close,volume,amount",
                    "rows": [["2026-07-22", "sh.600519", "1680.5", "1690.0", "1669.5", "1685.0", "1170000", "1971450000"]],
                },
                dataset_schema_hash=dataset_schema_hash,
                record={
                    "instrument_id": "600519.XSHG",
                    "market": "cn",
                    "exchange": "XSHG",
                    "date": "2026-07-22",
                    "open": 1680.5,
                    "high": 1690.0,
                    "low": 1669.5,
                    "close": 1685.0,
                    "volume": 1170000.0,
                    "amount": 1971450000.0,
                    "currency": "CNY",
                    "adjustment": "unadjusted",
                    "provider_source": "baostock.query_history_k_data_plus",
                },
            ),
            _daily_bar_success_case(
                provider_id="yfinance",
                provider_version="fixture-2026.07",
                market=Market.US,
                provider_symbol="AAPL",
                endpoint="Ticker.history",
                raw_response={
                    "symbol": "AAPL",
                    "history": [{"Date": "2026-07-22", "Open": 213.0, "High": 216.4, "Low": 212.5, "Close": 215.2, "Volume": 78120000}],
                },
                dataset_schema_hash=dataset_schema_hash,
                record={
                    "instrument_id": "AAPL.XNAS",
                    "market": "us",
                    "exchange": "XNAS",
                    "date": "2026-07-22",
                    "open": 213.0,
                    "high": 216.4,
                    "low": 212.5,
                    "close": 215.2,
                    "volume": 78120000.0,
                    "currency": "USD",
                    "adjustment": "unadjusted",
                    "provider_source": "yfinance.Ticker.history",
                },
            ),
            _daily_bar_success_case(
                provider_id="yfinance",
                provider_version="fixture-2026.07",
                market=Market.HK,
                provider_symbol="0700.HK",
                endpoint="Ticker.history",
                raw_response={
                    "symbol": "0700.HK",
                    "history": [{"Date": "2026-07-22", "Open": 390.0, "High": 398.0, "Low": 388.0, "Close": 395.6, "Volume": 22400000}],
                },
                dataset_schema_hash=dataset_schema_hash,
                record={
                    "instrument_id": "0700.XHKG",
                    "market": "hk",
                    "exchange": "XHKG",
                    "date": "2026-07-22",
                    "open": 390.0,
                    "high": 398.0,
                    "low": 388.0,
                    "close": 395.6,
                    "volume": 22400000.0,
                    "currency": "HKD",
                    "adjustment": "unadjusted",
                    "provider_source": "yfinance.Ticker.history",
                },
            ),
            _daily_bar_error_case(
                case_id="akshare_daily_bars_timeout",
                provider_id="akshare",
                market=Market.CN,
                provider_symbol="600519",
                endpoint="stock_zh_a_hist",
                status=ProviderFixtureStatus.TIMEOUT,
                expected_error_category=ProviderErrorCategory.RETRYABLE,
                failure_message="akshare fixture request timed out after 10 seconds",
                raw_response={"error_type": "TimeoutError", "message": "request timed out after 10 seconds"},
                dataset_schema_hash=dataset_schema_hash,
            ),
            _daily_bar_error_case(
                case_id="baostock_daily_bars_empty",
                provider_id="baostock",
                market=Market.CN,
                provider_symbol="sh.600519",
                endpoint="query_history_k_data_plus",
                status=ProviderFixtureStatus.EMPTY,
                expected_error_category=ProviderErrorCategory.DATA_INVALID,
                failure_message="baostock fixture returned no daily bar rows",
                raw_response={"fields": "date,code,open,high,low,close,volume,amount", "rows": []},
                dataset_schema_hash=dataset_schema_hash,
            ),
            _daily_bar_error_case(
                case_id="tushare_daily_bars_schema_drift",
                provider_id="tushare",
                market=Market.CN,
                provider_symbol="600519.SH",
                endpoint="daily",
                status=ProviderFixtureStatus.SCHEMA_DRIFT,
                expected_error_category=ProviderErrorCategory.SCHEMA_DRIFT,
                failure_message="tushare fixture missing required close field",
                raw_response={
                    "fields": ["ts_code", "trade_date", "open", "high", "low", "vol"],
                    "items": [["600519.SH", "20260722", 1682.0, 1692.0, 1672.0, 119.0]],
                },
                dataset_schema_hash=dataset_schema_hash,
            ),
        )
    )


def write_provider_fixture_snapshots(
    catalog: ProviderContractFixtureCatalog,
    directory: str | Path,
) -> tuple[Path, ...]:
    if type(catalog) is not ProviderContractFixtureCatalog:
        raise TypeError("catalog must be ProviderContractFixtureCatalog")
    output_dir = Path(directory)
    output_dir.mkdir(parents=True, exist_ok=True)
    case_paths: list[Path] = []
    for case in catalog.cases:
        path = output_dir / f"{case.case_id}.json"
        path.write_text(_canonical_json(case.to_snapshot_record()) + "\n", encoding="utf-8")
        case_paths.append(path)

    index = {
        "providers": list(catalog.provider_ids),
        "case_count": len(catalog.cases),
        "dataset_schema_hash": catalog.dataset_schema_hash,
        "cases": [
            {
                "case_id": case.case_id,
                "provider_id": case.provider_id,
                "market": case.market.value,
                "status": case.status.value,
                "capability": case.capability.value,
            }
            for case in catalog.cases
        ],
    }
    index_path = output_dir / "index.json"
    index_path.write_text(_canonical_json(index) + "\n", encoding="utf-8")
    return (index_path, *case_paths)


def _daily_bar_schema(provider_id: str, dataset_schema_hash: str) -> ProviderFixtureSchema:
    return ProviderFixtureSchema(
        schema_name=f"market.daily_bars.{provider_id}.fixture",
        schema_version="1.0.0",
        capability=ProviderCapability.DAILY_BARS,
        required_fields=("instrument_id", "market", "exchange", "date", "open", "high", "low", "close", "volume"),
        optional_fields=("amount", "currency", "adjustment", "provider_source"),
        dataset_schema_hash=dataset_schema_hash,
    )


def _daily_bar_success_case(
    *,
    provider_id: str,
    provider_version: str,
    market: Market,
    provider_symbol: str,
    endpoint: str,
    raw_response: object,
    dataset_schema_hash: str,
    record: Mapping[str, object],
) -> ProviderContractFixtureCase:
    return ProviderContractFixtureCase(
        case_id=f"{provider_id}_daily_bars_{market.value}_success_{provider_symbol.replace('.', '_').lower()}",
        provider_id=provider_id,
        provider_version=provider_version,
        market=market,
        capability=ProviderCapability.DAILY_BARS,
        request_parameters={
            "endpoint": endpoint,
            "provider_symbol": provider_symbol,
            "start": "2026-07-22",
            "end": "2026-07-22",
            "adjustment": "unadjusted",
        },
        raw_response=raw_response,
        schema=_daily_bar_schema(provider_id, dataset_schema_hash),
        records=(record,),
    )


def _daily_bar_error_case(
    *,
    case_id: str,
    provider_id: str,
    market: Market,
    provider_symbol: str,
    endpoint: str,
    status: ProviderFixtureStatus,
    expected_error_category: ProviderErrorCategory,
    failure_message: str,
    raw_response: object,
    dataset_schema_hash: str,
) -> ProviderContractFixtureCase:
    return ProviderContractFixtureCase(
        case_id=case_id,
        provider_id=provider_id,
        provider_version="fixture-2026.07",
        market=market,
        capability=ProviderCapability.DAILY_BARS,
        request_parameters={
            "endpoint": endpoint,
            "provider_symbol": provider_symbol,
            "start": "2026-07-22",
            "end": "2026-07-22",
            "adjustment": "unadjusted",
        },
        raw_response=raw_response,
        schema=_daily_bar_schema(provider_id, dataset_schema_hash),
        status=status,
        expected_error_category=expected_error_category,
        failure_message=failure_message,
    )


def _required_string(field_name: str, value: object) -> str:
    if type(value) is not str:
        raise TypeError(f"{field_name} must be a string")
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} is required")
    return normalized


def _optional_string(value: object | None) -> str | None:
    if value is None:
        return None
    if type(value) is not str:
        raise TypeError("optional string value must be a string")
    normalized = value.strip()
    return normalized or None


def _require_aware_datetime(field_name: str, value: datetime) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")


def _unique_tuple(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(values))


def _freeze_json_mapping(value: Mapping[str, object]) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise TypeError("fixture JSON value must be a mapping")
    return MappingProxyType({_required_string("fixture key", key): _freeze_json_value(item) for key, item in value.items()})


def _freeze_json_value(value: object) -> object:
    if value is None or type(value) in {bool, int, float, str}:
        return value
    if isinstance(value, Mapping):
        return _freeze_json_mapping(value)
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_json_value(item) for item in value)
    raise TypeError(f"Unsupported fixture JSON value type: {type(value).__name__}")


def _json_ready(value: object) -> object:
    if isinstance(value, Mapping):
        return {str(key): _json_ready(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_json_ready(item) for item in value]
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def _canonical_json(value: object) -> str:
    return json.dumps(_json_ready(value), sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _sha256_json(value: object) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _assert_sanitized(value: object) -> None:
    text = _canonical_json(value).lower()
    for forbidden in _FORBIDDEN_TEXT:
        if forbidden in text:
            raise ValueError(f"provider fixture contains forbidden text: {forbidden}")


__all__ = [
    "ProviderContractFixtureCase",
    "ProviderContractFixtureCatalog",
    "ProviderFixtureSchema",
    "ProviderFixtureStatus",
    "default_provider_contract_fixture_catalog",
    "write_provider_fixture_snapshots",
]
