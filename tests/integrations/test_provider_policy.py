from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from serenity_alpha_lab.datasets.quality import DataQualityStatus
from serenity_alpha_lab.domain.instruments import Market
from serenity_alpha_lab.domain.providers import DataBatch, ProviderCapability, ProviderError
from serenity_alpha_lab.integrations.data.provider_contract_fixtures import (
    ProviderContractFixtureCase,
    default_provider_contract_fixture_catalog,
)
from serenity_alpha_lab.integrations.data.provider_policy import (
    ProviderPolicy,
    ProviderPolicyEngine,
    ProviderPolicyError,
    ProviderPolicyStatus,
    ProviderSelectionRequest,
)


NOW = datetime(2026, 7, 23, 1, 30, tzinfo=UTC)


def test_policy_selects_first_fresh_complete_provider_and_records_trace() -> None:
    catalog = default_provider_contract_fixture_catalog()
    policy = _cn_daily_policy()
    request = _daily_request(required_fields=("open", "high", "low", "close", "volume"))
    akshare = _case(catalog.success_cases(), "akshare").to_data_batch(
        trace_id="trace-policy-001",
        run_id="run-policy-001",
        stage_id="stage-provider-policy",
    )
    tushare = _case(catalog.success_cases(), "tushare").to_data_batch()

    result = ProviderPolicyEngine(policy).select(
        request,
        provider_results={"akshare": akshare, "tushare": tushare},
    )

    assert result.status is ProviderPolicyStatus.SELECTED
    assert result.selected_batch is akshare
    assert result.selected_provider_id == "akshare"
    assert result.trace.attempted_order == ("akshare", "efinance", "tushare", "baostock")
    assert [attempt.provider_id for attempt in result.trace.attempts] == ["akshare"]
    assert result.trace.attempts[0].status == "selected"
    assert result.trace.attempts[0].raw_response_sha256 == akshare.provenance.raw_response_sha256
    assert result.trace.trace_id == "trace-policy-001"
    assert result.trace.run_id == "run-policy-001"
    assert result.trace.stage_id == "stage-provider-policy"
    assert result.trace.to_record()["selected_provider_id"] == "akshare"


def test_policy_falls_back_from_stale_or_missing_field_successes() -> None:
    catalog = default_provider_contract_fixture_catalog()
    policy = _cn_daily_policy()
    request = _daily_request(required_fields=("open", "high", "low", "close", "volume", "amount"))
    stale_akshare = _stale(_case(catalog.success_cases(), "akshare").to_data_batch())
    missing_amount_efinance = _case(catalog.success_cases(), "efinance").to_data_batch()
    tushare = _case(catalog.success_cases(), "tushare").to_data_batch()

    result = ProviderPolicyEngine(policy).select(
        request,
        provider_results={
            "akshare": stale_akshare,
            "efinance": missing_amount_efinance,
            "tushare": tushare,
        },
    )

    assert result.status is ProviderPolicyStatus.SELECTED
    assert result.selected_provider_id == "tushare"
    assert result.selected_batch is tushare
    assert [(attempt.provider_id, attempt.status, attempt.reason) for attempt in result.trace.attempts] == [
        ("akshare", "rejected", "stale"),
        ("efinance", "rejected", "missing_fields"),
        ("tushare", "selected", None),
    ]
    assert result.trace.attempts[1].missing_fields == ("amount",)
    assert result.trace.to_record()["attempts"][0]["reason"] == "stale"


def test_policy_records_provider_errors_and_exhaustion_without_real_calls() -> None:
    catalog = default_provider_contract_fixture_catalog()
    policy = _cn_daily_policy()
    request = _daily_request()
    timeout = catalog.get("akshare_daily_bars_timeout").to_provider_error()
    empty = catalog.get("baostock_daily_bars_empty").to_provider_error()
    drift = catalog.get("tushare_daily_bars_schema_drift").to_provider_error()

    result = ProviderPolicyEngine(policy).select(
        request,
        provider_results={"akshare": timeout, "tushare": drift, "baostock": empty},
    )

    assert result.status is ProviderPolicyStatus.EXHAUSTED
    assert result.selected_batch is None
    assert result.selected_provider_id is None
    assert [attempt.provider_id for attempt in result.trace.attempts] == ["akshare", "tushare", "baostock"]
    assert [attempt.reason for attempt in result.trace.attempts] == [
        "provider_retryable",
        "provider_schema_drift",
        "provider_data_invalid",
    ]
    assert all(isinstance(error, ProviderError) for error in (timeout, empty, drift))
    assert result.trace.to_record()["status"] == "exhausted"


def test_policy_rejects_quarantined_quality_status_and_selects_next_source() -> None:
    catalog = default_provider_contract_fixture_catalog()
    policy = _cn_daily_policy()
    request = _daily_request(quality_status_by_provider={"akshare": DataQualityStatus.BLOCKING})
    akshare = _case(catalog.success_cases(), "akshare").to_data_batch()
    efinance = _case(catalog.success_cases(), "efinance").to_data_batch()

    result = ProviderPolicyEngine(policy).select(
        request,
        provider_results={"akshare": akshare, "efinance": efinance},
    )

    assert result.status is ProviderPolicyStatus.SELECTED
    assert result.selected_provider_id == "efinance"
    assert [(attempt.provider_id, attempt.status, attempt.reason) for attempt in result.trace.attempts] == [
        ("akshare", "rejected", "quality_blocking"),
        ("efinance", "selected", None),
    ]
    assert result.trace.attempts[0].quality_status is DataQualityStatus.BLOCKING


def test_policy_quarantines_cross_provider_close_conflict_without_averaging() -> None:
    catalog = default_provider_contract_fixture_catalog()
    policy = _cn_daily_policy(cross_check_provider_id="tushare", max_close_diff_bps=5.0)
    request = _daily_request(required_fields=("open", "high", "low", "close", "volume"))
    akshare = _case(catalog.success_cases(), "akshare").to_data_batch()
    tushare_conflict = _with_close(_case(catalog.success_cases(), "tushare").to_data_batch(), close=1700.0)

    result = ProviderPolicyEngine(policy).select(
        request,
        provider_results={"akshare": akshare, "tushare": tushare_conflict},
    )

    assert result.status is ProviderPolicyStatus.QUARANTINED
    assert result.selected_batch is None
    assert result.selected_provider_id is None
    assert len(result.trace.conflicts) == 1
    conflict = result.trace.conflicts[0]
    assert conflict.field_name == "close"
    assert conflict.primary_key == {"instrument_id": "600519.XSHG", "date": "2026-07-22"}
    assert conflict.provider_values == {"akshare": 1688.0, "tushare": 1700.0}
    assert conflict.threshold_bps == 5.0
    assert conflict.observed_diff_bps > 5.0
    assert result.trace.attempts[-1].status == "quarantined"
    assert result.trace.to_record()["conflicts"][0]["resolution"] == "quarantine"


def test_policy_rejects_dataset_mismatch_before_selecting_provider() -> None:
    catalog = default_provider_contract_fixture_catalog()
    policy = _cn_daily_policy()
    akshare = _case(catalog.success_cases(), "akshare").to_data_batch()
    request = ProviderSelectionRequest(
        market=Market.CN,
        capability=ProviderCapability.DAILY_BARS,
        dataset_name="fundamentals_pit",
        required_fields=("open", "high", "low", "close", "volume"),
        evaluation_time=NOW,
    )

    with pytest.raises(ProviderPolicyError, match="dataset_name must match policy dataset"):
        ProviderPolicyEngine(policy).select(request, provider_results={"akshare": akshare})


def _cn_daily_policy(
    *,
    cross_check_provider_id: str | None = None,
    max_close_diff_bps: float | None = None,
) -> ProviderPolicy:
    return ProviderPolicy.from_mapping(
        {
            "policy_id": "cn-bars-fixture-policy",
            "market": "cn",
            "dataset": "bars_1d",
            "priority": ["akshare", "efinance", "tushare", "baostock"],
            "sources": {
                "akshare": {"markets": ["cn"], "capabilities": ["daily_bars"], "quality_score": 0.95},
                "efinance": {"markets": ["cn"], "capabilities": ["daily_bars"], "quality_score": 0.90},
                "tushare": {"markets": ["cn"], "capabilities": ["daily_bars"], "quality_score": 0.92},
                "baostock": {"markets": ["cn"], "capabilities": ["daily_bars"], "quality_score": 0.85},
            },
            "validation": {
                "cross_check_provider": cross_check_provider_id,
                "max_close_diff_bps": max_close_diff_bps,
            },
        }
    )


def _daily_request(
    required_fields: tuple[str, ...] = ("open", "high", "low", "close", "volume"),
    *,
    quality_status_by_provider: dict[str, DataQualityStatus] | None = None,
) -> ProviderSelectionRequest:
    return ProviderSelectionRequest(
        market=Market.CN,
        capability=ProviderCapability.DAILY_BARS,
        dataset_name="bars_1d",
        required_fields=required_fields,
        evaluation_time=NOW,
        trace_id="trace-policy-001",
        run_id="run-policy-001",
        stage_id="stage-provider-policy",
        quality_status_by_provider=quality_status_by_provider or {"baostock": DataQualityStatus.WARNING},
    )


def _case(
    cases: tuple[ProviderContractFixtureCase, ...],
    provider_id: str,
) -> ProviderContractFixtureCase:
    return next(case for case in cases if case.provider_id == provider_id and case.market is Market.CN)


def _stale(batch: DataBatch) -> DataBatch:
    return DataBatch(
        records=batch.records,
        schema_name=batch.schema_name,
        schema_version=batch.schema_version,
        provenance=batch.provenance,
        fresh_until=NOW - timedelta(minutes=1),
        warnings=batch.warnings,
    )


def _with_close(batch: DataBatch, *, close: float) -> DataBatch:
    records = []
    for record in batch.records:
        updated = dict(record)
        updated["close"] = close
        records.append(updated)
    return DataBatch(
        records=tuple(records),
        schema_name=batch.schema_name,
        schema_version=batch.schema_version,
        provenance=batch.provenance,
        fresh_until=batch.fresh_until,
        warnings=batch.warnings,
    )
