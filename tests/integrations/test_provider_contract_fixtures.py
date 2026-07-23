from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from serenity_alpha_lab.datasets import RAW_DAILY_BARS_SCHEMA_NAME, RAW_DAILY_BARS_SCHEMA_VERSION
from serenity_alpha_lab.datasets.schema_registry import default_dataset_schema_registry
from serenity_alpha_lab.domain.instruments import Market
from serenity_alpha_lab.domain.providers import DataBatch, ProviderError, ProviderErrorCategory, ProviderCapability
from serenity_alpha_lab.integrations.data.provider_contract_fixtures import (
    ProviderFixtureStatus,
    default_provider_contract_fixture_catalog,
    write_provider_fixture_snapshots,
)


SDK_MODULES = {"akshare", "efinance", "tushare", "baostock", "yfinance"}
FORBIDDEN_TEXT = ("secret", "token=", "api_key", "cookie", "/Users/", "C:\\")


def test_default_fixture_catalog_covers_required_providers_and_markets_without_sdk_imports() -> None:
    before_imports = set(sys.modules)

    catalog = default_provider_contract_fixture_catalog()

    assert catalog.provider_ids == ("akshare", "baostock", "efinance", "tushare", "yfinance")
    assert SDK_MODULES.isdisjoint(sys.modules)
    assert SDK_MODULES.isdisjoint(set(sys.modules) - before_imports)
    assert {case.provider_id for case in catalog.success_cases()} == set(catalog.provider_ids)
    assert all(case.capability is ProviderCapability.DAILY_BARS for case in catalog.success_cases())
    assert any(case.provider_id == "akshare" and case.market is Market.CN for case in catalog.success_cases())
    assert any(case.provider_id == "yfinance" and case.market is Market.US for case in catalog.success_cases())
    assert any(case.provider_id == "yfinance" and case.market is Market.HK for case in catalog.success_cases())


def test_success_fixtures_convert_to_immutable_data_batches_with_schema_hash_and_lineage() -> None:
    catalog = default_provider_contract_fixture_catalog()
    raw_bars_schema = default_dataset_schema_registry().get(
        RAW_DAILY_BARS_SCHEMA_NAME,
        RAW_DAILY_BARS_SCHEMA_VERSION,
    )

    for case in catalog.success_cases():
        batch = case.to_data_batch(trace_id="trace-p2-014", run_id="run-p2-014", stage_id="stage-provider")

        assert isinstance(batch, DataBatch)
        assert case.schema.dataset_schema_hash == raw_bars_schema.schema_hash
        assert batch.schema_name == case.schema.schema_name
        assert batch.schema_version == case.schema.schema_version
        assert batch.provenance.provider_id == f"fixture:{case.provider_id}"
        assert batch.provenance.provider_version == case.provider_version
        assert batch.provenance.operation == ProviderCapability.DAILY_BARS.value
        assert batch.provenance.raw_response_sha256 == case.raw_response_sha256
        assert batch.provenance.trace_id == "trace-p2-014"
        assert batch.provenance.run_id == "run-p2-014"
        assert batch.provenance.stage_id == "stage-provider"
        assert batch.provenance.field_lineage["close"] == f"fixture:{case.provider_id}.close"
        assert batch.provenance.request_parameters["provider_symbol"] == case.request_parameters["provider_symbol"]
        assert batch.records
        assert batch.records[0]["instrument_id"] == case.records[0]["instrument_id"]

        with pytest.raises(TypeError):
            batch.records[0]["close"] = 0.0  # type: ignore[index]


def test_error_fixtures_cover_timeout_empty_and_schema_drift_categories() -> None:
    catalog = default_provider_contract_fixture_catalog()
    categories = {case.status: case.expected_error_category for case in catalog.error_cases()}

    assert categories[ProviderFixtureStatus.TIMEOUT] is ProviderErrorCategory.RETRYABLE
    assert categories[ProviderFixtureStatus.EMPTY] is ProviderErrorCategory.DATA_INVALID
    assert categories[ProviderFixtureStatus.SCHEMA_DRIFT] is ProviderErrorCategory.SCHEMA_DRIFT

    for case in catalog.error_cases():
        with pytest.raises(ProviderError) as error:
            case.to_data_batch(trace_id="trace-error")
        assert error.value.category is case.expected_error_category
        assert error.value.provider_id == f"fixture:{case.provider_id}"
        assert error.value.operation == ProviderCapability.DAILY_BARS.value
        assert all(forbidden not in error.value.message.lower() for forbidden in FORBIDDEN_TEXT)


def test_fixture_snapshot_materialization_is_deterministic_and_sanitized(tmp_path: Path) -> None:
    catalog = default_provider_contract_fixture_catalog()

    first = write_provider_fixture_snapshots(catalog, tmp_path)
    first_payloads = {path.name: path.read_text(encoding="utf-8") for path in first}
    second = write_provider_fixture_snapshots(catalog, tmp_path)
    second_payloads = {path.name: path.read_text(encoding="utf-8") for path in second}

    assert first_payloads == second_payloads
    assert {path.name for path in first} == {"index.json", *(f"{case.case_id}.json" for case in catalog.cases)}

    index = json.loads((tmp_path / "index.json").read_text(encoding="utf-8"))
    assert index["providers"] == list(catalog.provider_ids)
    assert index["case_count"] == len(catalog.cases)
    assert index["dataset_schema_hash"] == default_dataset_schema_registry().get(
        RAW_DAILY_BARS_SCHEMA_NAME,
        RAW_DAILY_BARS_SCHEMA_VERSION,
    ).schema_hash

    combined_text = "\n".join(first_payloads.values()).lower()
    assert all(forbidden.lower() not in combined_text for forbidden in FORBIDDEN_TEXT)
