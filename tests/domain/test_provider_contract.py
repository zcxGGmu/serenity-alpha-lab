from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import UTC, date, datetime, timedelta
from typing import Mapping, Sequence

import pytest

from serenity_alpha_lab.domain.artifacts import InvalidArtifactUri
from serenity_alpha_lab.domain.instruments import InstrumentId, Market
from serenity_alpha_lab.domain.providers import (
    Capability,
    DataBatch,
    MarketDataProvider,
    Provenance,
    ProviderCapabilities,
    ProviderCapability,
    ProviderError,
    ProviderErrorCategory,
    ProviderWarning,
)


REQUESTED_AT = datetime(2026, 7, 20, 9, 59, tzinfo=UTC)
FETCHED_AT = datetime(2026, 7, 20, 10, 0, tzinfo=UTC)
SOURCE_TIMESTAMP = datetime(2026, 7, 18, 8, 0, tzinfo=UTC)
FRESH_UNTIL = datetime(2026, 7, 20, 10, 15, tzinfo=UTC)
RAW_SHA256 = "AB" * 32


def make_provenance(**overrides: object) -> Provenance:
    values: dict[str, object] = {
        "provider_id": "fixture",
        "provider_version": "1.0.0",
        "operation": ProviderCapability.DAILY_BARS,
        "request_parameters": {"instruments": ["600519.XSHG"]},
        "requested_at": REQUESTED_AT,
        "fetched_at": FETCHED_AT,
        "raw_response_sha256": RAW_SHA256,
        "field_lineage": {"close": "fixture.close"},
        "source_timestamp": SOURCE_TIMESTAMP,
        "trace_id": "trace-001",
        "run_id": "run-001",
        "stage_id": "stage-provider",
    }
    values.update(overrides)
    return Provenance(**values)  # type: ignore[arg-type]


def make_batch(*, records: Sequence[Mapping[str, object]] = ()) -> DataBatch[Mapping[str, object]]:
    return DataBatch(
        records=records,
        schema_name="market.daily_bars",
        schema_version="1.0.0",
        provenance=make_provenance(),
        fresh_until=FRESH_UNTIL,
    )


def test_provider_capability_values_are_stable() -> None:
    assert {capability.value for capability in ProviderCapability} == {
        "instruments",
        "trading_calendar",
        "daily_bars",
        "fundamentals",
    }


def test_capability_collection_normalizes_inputs_and_supports_market_lookup() -> None:
    markets = ["cn", Market.HK]
    fields = ["instrument_id", "close"]
    daily_bars = Capability(
        capability="daily_bars",
        markets=markets,
        frequency="1d",
        fields=fields,
        schema_name="market.daily_bars",
        schema_version="1.0.0",
    )
    instruments = Capability(
        capability=ProviderCapability.INSTRUMENTS,
        markets=(),
        schema_name="market.instruments",
        schema_version="1.0.0",
    )
    declarations = [daily_bars, instruments]
    capabilities = ProviderCapabilities(declarations)

    markets.append(Market.US)
    fields.append("volume")
    declarations.clear()

    assert daily_bars.capability is ProviderCapability.DAILY_BARS
    assert daily_bars.markets == (Market.CN, Market.HK)
    assert daily_bars.fields == ("instrument_id", "close")
    assert capabilities.supports(ProviderCapability.DAILY_BARS)
    assert capabilities.supports("daily_bars", market="cn")
    assert not capabilities.supports(ProviderCapability.DAILY_BARS, market=Market.US)
    assert capabilities.supports(ProviderCapability.INSTRUMENTS, market=Market.US)
    assert not capabilities.supports(ProviderCapability.FUNDAMENTALS)
    assert capabilities.get(ProviderCapability.DAILY_BARS) is daily_bars


def test_capability_collection_rejects_invalid_or_ambiguous_declarations() -> None:
    declaration = Capability(
        capability=ProviderCapability.DAILY_BARS,
        markets=(Market.CN,),
        schema_name="market.daily_bars",
        schema_version="1.0.0",
    )

    with pytest.raises(ValueError, match="Duplicate provider capability"):
        ProviderCapabilities([declaration, declaration])

    class MutableCapabilityDeclaration:
        capability = ProviderCapability.FUNDAMENTALS
        markets = []

    with pytest.raises(TypeError, match="ProviderCapabilities requires Capability declarations"):
        ProviderCapabilities([MutableCapabilityDeclaration()])  # type: ignore[list-item]

    for schema_name, schema_version in (("", "1.0.0"), ("daily_bars", " ")):
        with pytest.raises(ValueError, match="is required"):
            Capability(
                capability=ProviderCapability.DAILY_BARS,
                schema_name=schema_name,
                schema_version=schema_version,
            )


def test_data_batch_preserves_provenance_freshness_and_warnings() -> None:
    requested_instruments = ["600519.XSHG"]
    request_parameters: dict[str, object] = {
        "instruments": requested_instruments,
        "filters": {"adjustment": "forward"},
    }
    field_lineage = {"close": "fixture.close"}
    provenance = make_provenance(
        request_parameters=request_parameters,
        field_lineage=field_lineage,
    )
    warning_fields = ["turnover"]
    warning = ProviderWarning(
        code="partial_fields",
        message="turnover is absent",
        fields=warning_fields,
    )
    record: dict[str, object] = {"instrument_id": "600519.XSHG", "close": "1688.00"}
    records: list[Mapping[str, object]] = [record]
    warnings = [warning]
    batch = DataBatch(
        records=records,
        schema_name="market.daily_bars",
        schema_version="1.0.0",
        provenance=provenance,
        fresh_until=FRESH_UNTIL,
        warnings=warnings,
    )

    request_parameters["token"] = "must-not-leak-into-copy"
    requested_instruments.append("000001.XSHE")
    nested_filters = request_parameters["filters"]
    assert isinstance(nested_filters, dict)
    nested_filters["adjustment"] = "backward"
    field_lineage["close"] = "mutated.close"
    warning_fields.append("amount")
    records.append({"instrument_id": "000001.XSHE"})
    record["close"] = "mutated"
    warnings.clear()

    assert provenance.provider_id == "fixture"
    assert provenance.provider_version == "1.0.0"
    assert provenance.operation == ProviderCapability.DAILY_BARS.value
    assert provenance.request_parameters == {
        "instruments": ("600519.XSHG",),
        "filters": {"adjustment": "forward"},
    }
    assert provenance.requested_at == REQUESTED_AT
    assert provenance.fetched_at == FETCHED_AT
    assert provenance.raw_response_sha256 == RAW_SHA256.lower()
    assert provenance.field_lineage == {"close": "fixture.close"}
    assert provenance.source_timestamp == SOURCE_TIMESTAMP
    assert provenance.trace_id == "trace-001"
    assert provenance.run_id == "run-001"
    assert provenance.stage_id == "stage-provider"
    assert warning.fields == ("turnover",)
    assert batch.records == ({"instrument_id": "600519.XSHG", "close": "1688.00"},)
    assert batch.warnings == (warning,)
    assert batch.is_stale(at=FRESH_UNTIL) is False
    assert batch.is_stale(at=FRESH_UNTIL + timedelta(microseconds=1)) is True
    assert make_batch().records == ()
    assert make_batch().warnings == ()

    with pytest.raises(TypeError):
        provenance.request_parameters["new"] = "value"  # type: ignore[index]
    with pytest.raises(TypeError):
        provenance.field_lineage["close"] = "other.close"  # type: ignore[index]
    with pytest.raises(TypeError):
        provenance.request_parameters["filters"]["adjustment"] = "none"  # type: ignore[index]
    with pytest.raises(TypeError):
        batch.records[0]["close"] = "other"  # type: ignore[index]
    with pytest.raises(FrozenInstanceError):
        batch.schema_name = "other"  # type: ignore[misc]


def test_data_batch_requires_contract_value_objects() -> None:
    class MutableProvenance:
        provider_id = "fixture"

    class MutableWarning:
        code = "partial"
        fields: list[str] = []

    with pytest.raises(TypeError, match="DataBatch provenance must be Provenance"):
        DataBatch(
            records=(),
            schema_name="market.daily_bars",
            schema_version="1.0.0",
            provenance=MutableProvenance(),  # type: ignore[arg-type]
            fresh_until=FRESH_UNTIL,
        )

    with pytest.raises(TypeError, match="DataBatch warnings must be ProviderWarning"):
        DataBatch(
            records=(),
            schema_name="market.daily_bars",
            schema_version="1.0.0",
            provenance=make_provenance(),
            fresh_until=FRESH_UNTIL,
            warnings=[MutableWarning()],  # type: ignore[list-item]
        )


def test_batch_and_provenance_freeze_bytearrays_and_reject_custom_values() -> None:
    request_payload = bytearray(b"request")
    record_payload = bytearray(b"record")
    instrument = InstrumentId.parse("600519.XSHG")
    provenance = make_provenance(
        request_parameters={
            "payloads": [request_payload],
            "as_of": date(2026, 7, 20),
            "requested_at": REQUESTED_AT,
        }
    )
    batch = make_batch(
        records=(
            {
                "instrument_id": instrument,
                "payloads": [record_payload],
                "observed_at": FETCHED_AT,
            },
        )
    )

    request_payload[:] = b"changed"
    record_payload[:] = b"changed"

    frozen_request_payload = provenance.request_parameters["payloads"][0]  # type: ignore[index]
    frozen_record_payload = batch.records[0]["payloads"][0]  # type: ignore[index]
    assert frozen_request_payload == b"request"
    assert frozen_record_payload == b"record"
    assert isinstance(frozen_request_payload, bytes)
    assert isinstance(frozen_record_payload, bytes)
    assert provenance.request_parameters["as_of"] == date(2026, 7, 20)
    assert provenance.request_parameters["requested_at"] == REQUESTED_AT
    assert batch.records[0]["instrument_id"] == instrument
    assert batch.records[0]["observed_at"] == FETCHED_AT

    with pytest.raises(TypeError):
        frozen_request_payload[0] = 0  # type: ignore[index]
    with pytest.raises(TypeError):
        frozen_record_payload[0] = 0  # type: ignore[index]

    class MutableProviderValue:
        pass

    with pytest.raises(TypeError, match="Unsupported provider value type: MutableProviderValue"):
        make_provenance(request_parameters={"unsupported": MutableProviderValue()})


def test_provenance_rejects_mutable_scalar_subclasses() -> None:
    class MutableString(str):
        def __new__(cls, value: str) -> MutableString:
            instance = super().__new__(cls, value)
            instance.notes = []
            return instance

    mutable_value = MutableString("fixture")

    with pytest.raises(TypeError, match="Unsupported provider value type: MutableString"):
        make_provenance(request_parameters={"provider": mutable_value})


def test_provenance_rejects_mutable_mapping_keys() -> None:
    class MutableString(str):
        def __new__(cls, value: str) -> MutableString:
            instance = super().__new__(cls, value)
            instance.notes = []
            return instance

    mutable_key = MutableString("provider")

    with pytest.raises(TypeError, match="Unsupported provider value type: MutableString"):
        make_provenance(request_parameters={mutable_key: "fixture"})  # type: ignore[dict-item]


def test_provenance_requires_string_request_and_lineage_schema() -> None:
    with pytest.raises(TypeError, match="request parameter key must be a string"):
        make_provenance(request_parameters={1: "fixture"})  # type: ignore[dict-item]

    with pytest.raises(TypeError, match="field lineage value must be a string"):
        make_provenance(field_lineage={"close": 123})  # type: ignore[dict-item]


def test_contract_value_objects_require_identity_fields() -> None:
    with pytest.raises(ValueError, match="code is required"):
        ProviderWarning(code=" ", message="warning")

    with pytest.raises(ValueError, match="message is required"):
        ProviderWarning(code="warning", message="")

    for field_name in ("provider_id", "operation"):
        with pytest.raises(ValueError, match=f"{field_name} is required"):
            make_provenance(**{field_name: ""})

    for schema_name, schema_version in (("", "1.0.0"), ("daily_bars", "")):
        with pytest.raises(ValueError, match="is required"):
            DataBatch(
                records=(),
                schema_name=schema_name,
                schema_version=schema_version,
                provenance=make_provenance(),
                fresh_until=FRESH_UNTIL,
            )


def test_provenance_validates_digest_and_aware_timestamps() -> None:
    with pytest.raises(InvalidArtifactUri):
        make_provenance(raw_response_sha256="not-a-sha256")

    for field_name in ("requested_at", "fetched_at", "source_timestamp"):
        with pytest.raises(ValueError, match=f"{field_name} must be timezone-aware"):
            make_provenance(**{field_name: datetime(2026, 7, 20, 10, 0)})


def test_data_batch_requires_aware_freshness_times() -> None:
    with pytest.raises(ValueError, match="fresh_until must be timezone-aware"):
        DataBatch(
            records=(),
            schema_name="market.daily_bars",
            schema_version="1.0.0",
            provenance=make_provenance(),
            fresh_until=datetime(2026, 7, 20, 10, 15),
        )

    batch = make_batch()
    with pytest.raises(ValueError, match="at must be timezone-aware"):
        batch.is_stale(at=datetime(2026, 7, 20, 10, 15))


@pytest.mark.parametrize(
    ("category", "is_retryable"),
    [
        (ProviderErrorCategory.RETRYABLE, True),
        (ProviderErrorCategory.RATE_LIMITED, True),
        (ProviderErrorCategory.AUTH, False),
        (ProviderErrorCategory.SCHEMA_DRIFT, False),
        (ProviderErrorCategory.DATA_INVALID, False),
        (ProviderErrorCategory.PERMANENT, False),
    ],
)
def test_provider_error_categories_expose_retry_policy(
    category: ProviderErrorCategory,
    is_retryable: bool,
) -> None:
    retry_after_seconds = 30.0 if category is ProviderErrorCategory.RATE_LIMITED else None
    error = ProviderError(
        category=category,
        provider_id="fixture",
        operation=ProviderCapability.DAILY_BARS,
        message="provider call failed",
        retry_after_seconds=retry_after_seconds,
    )

    assert error.category is category
    assert error.provider_id == "fixture"
    assert error.operation == ProviderCapability.DAILY_BARS.value
    assert str(error) == "provider call failed"
    assert error.retry_after_seconds == retry_after_seconds
    assert error.is_retryable is is_retryable


def test_provider_error_validates_required_fields_and_retry_after() -> None:
    common = {
        "category": ProviderErrorCategory.RATE_LIMITED,
        "provider_id": "fixture",
        "operation": "daily_bars",
        "message": "rate limited",
    }

    for field_name in ("provider_id", "operation", "message"):
        with pytest.raises(ValueError, match=f"{field_name} is required"):
            ProviderError(**{**common, field_name: ""})  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="cannot be negative"):
        ProviderError(**common, retry_after_seconds=-1)

    with pytest.raises(ValueError, match="only valid for rate_limited"):
        ProviderError(
            category=ProviderErrorCategory.RETRYABLE,
            provider_id="fixture",
            operation="daily_bars",
            message="temporarily unavailable",
            retry_after_seconds=5,
        )


@pytest.mark.parametrize(
    "retry_after_seconds",
    [float("nan"), float("inf"), float("-inf")],
)
def test_provider_error_rejects_non_finite_retry_after_seconds(retry_after_seconds: float) -> None:
    with pytest.raises(ValueError, match="retry_after_seconds must be finite"):
        ProviderError(
            category=ProviderErrorCategory.RATE_LIMITED,
            provider_id="fixture",
            operation="daily_bars",
            message="rate limited",
            retry_after_seconds=retry_after_seconds,
        )


class FakeMarketDataProvider:
    provider_id = "fixture"

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            [
                Capability(
                    capability=capability,
                    markets=(Market.CN,),
                    schema_name=f"market.{capability.value}",
                    schema_version="1.0.0",
                )
                for capability in ProviderCapability
            ]
        )

    def list_instruments(self, as_of: date) -> DataBatch[Mapping[str, object]]:
        return make_batch(records=({"as_of": as_of.isoformat()},))

    def get_calendar(self, start: date, end: date) -> DataBatch[Mapping[str, object]]:
        return make_batch(records=({"start": start.isoformat(), "end": end.isoformat()},))

    def get_daily_bars(
        self,
        instruments: Sequence[InstrumentId],
        start: date,
        end: date,
    ) -> DataBatch[Mapping[str, object]]:
        return make_batch(records=({"instrument_count": len(instruments)},))

    def get_fundamentals(
        self,
        instruments: Sequence[InstrumentId],
        as_of: datetime,
    ) -> DataBatch[Mapping[str, object]]:
        return make_batch(records=({"instrument_count": len(instruments), "as_of": as_of.isoformat()},))


def test_market_data_provider_protocol_is_synchronous_and_runtime_checkable() -> None:
    provider = FakeMarketDataProvider()

    assert isinstance(provider, MarketDataProvider)
    assert provider.capabilities().supports(ProviderCapability.TRADING_CALENDAR, Market.CN)
    assert provider.list_instruments(date(2026, 7, 20)).records
    assert provider.get_calendar(date(2026, 7, 1), date(2026, 7, 20)).records
    assert provider.get_daily_bars((), date(2026, 7, 1), date(2026, 7, 20)).records
    assert provider.get_fundamentals((), FETCHED_AT).records
