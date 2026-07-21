from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Any

import pandas as pd
import pytest

from serenity_alpha_lab.application.api_errors import ApiErrorCode, problem_from_exception
from serenity_alpha_lab.application.config_profiles import (
    ConfigProfileError,
    RuntimeProfile,
    RuntimeSettings,
)
from serenity_alpha_lab.application.tracing import TraceContext, use_trace_context
from serenity_alpha_lab.domain.instruments import InstrumentId, Market
from serenity_alpha_lab.domain.providers import (
    DataBatch,
    MarketDataProvider,
    ProviderCapability,
    ProviderError,
    ProviderErrorCategory,
)
from serenity_alpha_lab.integrations.dsa.provider_adapter import (
    DSA_DAILY_BAR_SCHEMA_NAME,
    DSA_DAILY_BAR_SCHEMA_VERSION,
    DsaProviderCompatibilityAdapter,
    DsaStockHistoryCompatibilityFacade,
)


NOW = datetime(2026, 7, 21, 10, 30, tzinfo=UTC)
START = date(2026, 7, 1)
END = date(2026, 7, 20)


class FakeDsaManager:
    def __init__(
        self,
        rows: list[dict[str, Any]] | None = None,
        *,
        source: str = "EfinanceFetcher",
        error: Exception | None = None,
    ) -> None:
        self.rows = rows if rows is not None else _daily_rows()
        self.source = source
        self.error = error
        self.daily_calls: list[dict[str, Any]] = []
        self.name_calls: list[str] = []

    def get_daily_data(self, stock_code: str, start_date=None, end_date=None, days: int = 30):
        self.daily_calls.append(
            {
                "stock_code": stock_code,
                "start_date": start_date,
                "end_date": end_date,
                "days": days,
            }
        )
        if self.error is not None:
            raise self.error
        return pd.DataFrame(self.rows), self.source

    def get_stock_name(self, stock_code: str):
        self.name_calls.append(stock_code)
        return "贵州茅台"


def _daily_rows() -> list[dict[str, Any]]:
    return [
        {
            "date": pd.Timestamp("2026-07-17"),
            "open": 10.0,
            "high": 11.0,
            "low": 9.5,
            "close": 10.5,
            "volume": 1000,
            "amount": 10000.0,
            "pct_chg": 1.5,
            "ma5": 10.1,
        },
        {
            "date": pd.Timestamp("2026-07-20"),
            "open": 10.5,
            "high": 12.0,
            "low": 10.0,
            "close": 11.5,
            "volume": 1200,
            "amount": 13800.0,
            "pct_chg": 2.0,
            "ma5": 10.4,
        },
    ]


def _adapter(manager: FakeDsaManager) -> DsaProviderCompatibilityAdapter:
    return DsaProviderCompatibilityAdapter(
        manager=manager,
        settings=RuntimeSettings(profile=RuntimeProfile.DESKTOP, allow_provider_calls=True),
        clock=lambda: NOW,
    )


def test_adapter_declares_daily_bar_capability_and_matches_provider_protocol() -> None:
    adapter = _adapter(FakeDsaManager())

    capabilities = adapter.capabilities()

    assert isinstance(adapter, MarketDataProvider)
    assert adapter.provider_id == "dsa_compatibility"
    assert capabilities.supports(ProviderCapability.DAILY_BARS, market=Market.CN)
    assert capabilities.supports(ProviderCapability.DAILY_BARS, market=Market.HK)
    assert capabilities.supports(ProviderCapability.DAILY_BARS, market=Market.US)
    assert capabilities.supports(ProviderCapability.DAILY_BARS, market=Market.JP)
    assert capabilities.supports(ProviderCapability.DAILY_BARS, market=Market.KR)
    assert capabilities.supports(ProviderCapability.DAILY_BARS, market=Market.TW)
    assert not capabilities.supports(ProviderCapability.FUNDAMENTALS)
    declaration = capabilities.get(ProviderCapability.DAILY_BARS)
    assert declaration is not None
    assert declaration.schema_name == DSA_DAILY_BAR_SCHEMA_NAME
    assert declaration.schema_version == DSA_DAILY_BAR_SCHEMA_VERSION


def test_daily_bars_map_dsa_dataframe_to_contract_batch_with_trace_and_lineage() -> None:
    manager = FakeDsaManager()
    adapter = _adapter(manager)
    instrument = InstrumentId.parse("600519.XSHG")

    with use_trace_context(TraceContext(trace_id="trace-001", run_id="run-001", stage_id="stage-provider")):
        batch = adapter.get_daily_bars([instrument], START, END)

    records = [dict(record) for record in batch.records]
    assert manager.daily_calls == [
        {
            "stock_code": "SH600519",
            "start_date": "2026-07-01",
            "end_date": "2026-07-20",
            "days": 30,
        }
    ]
    assert batch.schema_name == DSA_DAILY_BAR_SCHEMA_NAME
    assert batch.schema_version == DSA_DAILY_BAR_SCHEMA_VERSION
    assert batch.fresh_until == NOW + timedelta(days=1)
    assert batch.provenance.provider_id == "dsa:EfinanceFetcher"
    assert batch.provenance.operation == ProviderCapability.DAILY_BARS.value
    assert batch.provenance.requested_at == NOW
    assert batch.provenance.fetched_at == NOW
    assert batch.provenance.source_timestamp == datetime(2026, 7, 20, tzinfo=UTC)
    assert batch.provenance.trace_id == "trace-001"
    assert batch.provenance.run_id == "run-001"
    assert batch.provenance.stage_id == "stage-provider"
    assert len(batch.provenance.raw_response_sha256) == 64
    assert batch.provenance.request_parameters == {
        "instrument_ids": ("600519.XSHG",),
        "dsa_symbols": ("SH600519",),
        "start": "2026-07-01",
        "end": "2026-07-20",
        "days": 30,
    }
    assert batch.provenance.field_lineage["close"] == "dsa:EfinanceFetcher.close"
    assert records == [
        {
            "instrument_id": "600519.XSHG",
            "date": "2026-07-17",
            "open": 10.0,
            "high": 11.0,
            "low": 9.5,
            "close": 10.5,
            "volume": 1000.0,
            "amount": 10000.0,
            "pct_chg": 1.5,
            "ma5": 10.1,
            "source": "EfinanceFetcher",
        },
        {
            "instrument_id": "600519.XSHG",
            "date": "2026-07-20",
            "open": 10.5,
            "high": 12.0,
            "low": 10.0,
            "close": 11.5,
            "volume": 1200.0,
            "amount": 13800.0,
            "pct_chg": 2.0,
            "ma5": 10.4,
            "source": "EfinanceFetcher",
        },
    ]

    with pytest.raises(TypeError):
        batch.records[0]["close"] = 99.0  # type: ignore[index]


def test_adapter_rejects_schema_drift_and_empty_daily_results() -> None:
    missing_close = FakeDsaManager(rows=[{"date": "2026-07-20", "open": 1.0, "volume": 100}])
    empty = FakeDsaManager(rows=[])

    with pytest.raises(ProviderError) as schema_error:
        _adapter(missing_close).get_daily_bars([InstrumentId.parse("600519.XSHG")], START, END)
    assert schema_error.value.category is ProviderErrorCategory.SCHEMA_DRIFT
    assert schema_error.value.provider_id == "dsa_compatibility"

    with pytest.raises(ProviderError) as empty_error:
        _adapter(empty).get_daily_bars([InstrumentId.parse("600519.XSHG")], START, END)
    assert empty_error.value.category is ProviderErrorCategory.DATA_INVALID


def test_adapter_maps_manager_failures_to_provider_errors_and_problem_details_redacts() -> None:
    manager = FakeDsaManager(error=RuntimeError("429 rate limit token=super-secret"))
    adapter = _adapter(manager)

    with use_trace_context(TraceContext(trace_id="trace-provider")):
        with pytest.raises(ProviderError) as error:
            adapter.get_daily_bars([InstrumentId.parse("600519.XSHG")], START, END)
        problem = problem_from_exception(error.value)

    assert error.value.category is ProviderErrorCategory.RATE_LIMITED
    assert error.value.retry_after_seconds is None
    assert problem.code is ApiErrorCode.PROVIDER_ERROR
    assert problem.status == 502
    assert problem.trace_id == "trace-provider"
    assert "super-secret" not in problem.detail


def test_unsupported_provider_methods_fail_permanently() -> None:
    adapter = _adapter(FakeDsaManager())

    for call in (
        lambda: adapter.list_instruments(date(2026, 7, 21)),
        lambda: adapter.get_calendar(START, END),
        lambda: adapter.get_fundamentals([InstrumentId.parse("600519.XSHG")], NOW),
    ):
        with pytest.raises(ProviderError) as error:
            call()
        assert error.value.category is ProviderErrorCategory.PERMANENT
        assert error.value.is_retryable is False


def test_ci_profile_blocks_default_real_manager_but_allows_injected_offline_manager() -> None:
    settings = RuntimeSettings(profile=RuntimeProfile.CI)

    with pytest.raises(ConfigProfileError, match="CI profile forbids real provider calls"):
        DsaProviderCompatibilityAdapter.from_runtime_settings(settings=settings)

    adapter = DsaProviderCompatibilityAdapter(manager=FakeDsaManager(), settings=settings, clock=lambda: NOW)

    batch = adapter.get_daily_bars([InstrumentId.parse("600519.XSHG")], START, END)

    assert isinstance(batch, DataBatch)
    assert batch.records


def test_stock_history_facade_switches_between_legacy_and_provider_contract_paths() -> None:
    manager = FakeDsaManager()
    adapter = _adapter(manager)
    facade = DsaStockHistoryCompatibilityFacade(
        manager=manager,
        provider=adapter,
        clock=lambda: date(2026, 7, 21),
    )

    legacy = facade.get_history_data("600519", days=5, use_provider_contract=False)
    provider = facade.get_history_data("600519", days=5, use_provider_contract=True)

    assert legacy["stock_code"] == "600519"
    assert provider["stock_code"] == "600519"
    assert legacy["stock_name"] == "贵州茅台"
    assert provider["stock_name"] == "贵州茅台"
    assert legacy["period"] == provider["period"] == "daily"
    assert legacy["data"] == provider["data"]
    assert manager.daily_calls[0] == {
        "stock_code": "600519",
        "start_date": None,
        "end_date": None,
        "days": 5,
    }
    assert manager.daily_calls[1] == {
        "stock_code": "SH600519",
        "start_date": "2026-07-11",
        "end_date": "2026-07-21",
        "days": 30,
    }


def test_stock_history_facade_rejects_non_daily_period_before_calling_manager() -> None:
    manager = FakeDsaManager()
    facade = DsaStockHistoryCompatibilityFacade(manager=manager, provider=_adapter(manager))

    with pytest.raises(ValueError, match="仅支持 'daily'"):
        facade.get_history_data("600519", period="weekly", use_provider_contract=True)

    assert manager.daily_calls == []
