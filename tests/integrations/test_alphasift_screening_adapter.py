from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest

from serenity_alpha_lab.application.api_errors import ApiErrorCode, problem_from_exception
from serenity_alpha_lab.application.config_profiles import (
    ConfigProfileError,
    RuntimeProfile,
    RuntimeSettings,
)
from serenity_alpha_lab.application.screening_provider import (
    ScreeningProvider,
    ScreeningProviderError,
    ScreeningProviderErrorCategory,
    ScreeningRequest,
)
from serenity_alpha_lab.application.tracing import TraceContext, use_trace_context
from serenity_alpha_lab.integrations.alphasift.provider_adapter import (
    ALPHASIFT_PROVIDER_ID,
    AlphaSiftScreeningAdapter,
)


NOW = datetime(2026, 7, 23, 10, 15, tzinfo=UTC)
DATASET_VERSIONS = {
    "raw_daily_bars": "dsv_" + "a" * 32,
    "instrument_master": "dsv_" + "b" * 32,
}


class FakeAlphaSiftClient:
    def __init__(
        self,
        *,
        status_error: Exception | None = None,
        strategies_error: Exception | None = None,
        screen_error: Exception | None = None,
    ) -> None:
        self.status_error = status_error
        self.strategies_error = strategies_error
        self.screen_error = screen_error
        self.status_contexts: list[dict[str, Any] | None] = []
        self.strategy_contexts: list[dict[str, Any] | None] = []
        self.screen_calls: list[dict[str, Any]] = []

    def get_status(self, context: dict[str, Any] | None = None) -> dict[str, Any]:
        self.status_contexts.append(context)
        if self.status_error is not None:
            raise self.status_error
        return {
            "available": True,
            "version": "0.2.0",
            "contract_version": "1",
            "strategy_count": 1,
        }

    def list_strategies(self, context: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        self.strategy_contexts.append(context)
        if self.strategies_error is not None:
            raise self.strategies_error
        return [
            {
                "id": "quality_momentum",
                "name": "Quality Momentum",
                "description": "AlphaSift fixture strategy",
                "version": "1.0.0",
                "category": "quality",
                "tags": ["quality", "momentum"],
                "market_scope": ["cn"],
            }
        ]

    def screen(
        self,
        strategy: str,
        *,
        market: str,
        max_results: int,
        use_llm: bool,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self.screen_calls.append(
            {
                "strategy": strategy,
                "market": market,
                "max_results": max_results,
                "use_llm": use_llm,
                "context": context,
            }
        )
        if self.screen_error is not None:
            raise self.screen_error
        return {
            "source": "alphasift",
            "contract_version": "1",
            "run_id": "alpha-run-001",
            "strategy": strategy,
            "strategy_version": "1.0.0",
            "strategy_category": "quality",
            "market": market,
            "snapshot_count": 2800,
            "after_filter_count": 120,
            "candidate_count": 1,
            "llm_ranked": use_llm,
            "llm_coverage": 0.0 if not use_llm else 0.8,
            "candidates": [
                {
                    "rank": 1,
                    "code": "600519",
                    "name": "贵州茅台",
                    "score": 98.5,
                    "reason": "AlphaSift fixture",
                    "raw": {"final_score": 98.5},
                }
            ],
            "warnings": ["offline fixture"],
            "source_errors": [],
        }


def _adapter(client: FakeAlphaSiftClient) -> AlphaSiftScreeningAdapter:
    return AlphaSiftScreeningAdapter(
        client=client,
        settings=RuntimeSettings(profile=RuntimeProfile.CI),
        clock=lambda: NOW,
    )


def test_adapter_maps_status_strategies_and_screen_without_exposing_alphasift_models() -> None:
    client = FakeAlphaSiftClient()
    adapter = _adapter(client)

    with use_trace_context(TraceContext(trace_id="trace-alpha", run_id="run-alpha", stage_id="stage-alpha")):
        status = adapter.status()
        strategies = adapter.list_strategies()
        result = adapter.screen(
            ScreeningRequest(
                strategy_id="quality_momentum",
                market="cn",
                dataset_versions=DATASET_VERSIONS,
                max_results=5,
            )
        )

    assert isinstance(adapter, ScreeningProvider)
    assert status.provider_id == ALPHASIFT_PROVIDER_ID
    assert status.available is True
    assert status.provider_version == "0.2.0"
    assert status.strategy_count == 1
    assert status.trace_id == "trace-alpha"
    assert [strategy.strategy_id for strategy in strategies] == ["quality_momentum"]
    assert strategies[0].market_scope == ("cn",)

    assert client.screen_calls == [
        {
            "strategy": "quality_momentum",
            "market": "cn",
            "max_results": 5,
            "use_llm": False,
            "context": {
                "dataset_versions": DATASET_VERSIONS,
                "trace_id": "trace-alpha",
                "run_id": "run-alpha",
                "stage_id": "stage-alpha",
                "timeout_seconds": 30.0,
            },
        }
    ]
    assert result.provider_id == ALPHASIFT_PROVIDER_ID
    assert result.provider_version == "0.2.0"
    assert result.provider_run_id == "alpha-run-001"
    assert result.strategy_id == "quality_momentum"
    assert result.strategy_version == "1.0.0"
    assert result.dataset_versions == DATASET_VERSIONS
    assert result.snapshot_count == 2800
    assert result.after_filter_count == 120
    assert result.candidate_count == 1
    assert result.candidates[0]["code"] == "600519"
    assert result.warnings == ("offline fixture",)
    assert result.llm_overlay_enabled is False
    assert result.trace_id == "trace-alpha"
    assert result.platform_run_id == "run-alpha"
    assert result.stage_id == "stage-alpha"


def test_adapter_blocks_uninjected_real_client_in_ci_profile() -> None:
    adapter = AlphaSiftScreeningAdapter(settings=RuntimeSettings(profile=RuntimeProfile.CI))

    with pytest.raises(ConfigProfileError, match="CI profile forbids real AlphaSift provider calls"):
        adapter.status()


def test_adapter_blocks_llm_overlay_when_model_calls_are_not_allowed() -> None:
    adapter = _adapter(FakeAlphaSiftClient())

    with pytest.raises(ConfigProfileError, match="forbids AlphaSift LLM overlay"):
        adapter.screen(
            ScreeningRequest(
                strategy_id="quality_momentum",
                market="cn",
                dataset_versions=DATASET_VERSIONS,
                use_llm_overlay=True,
            )
        )


def test_adapter_maps_timeouts_and_provider_errors_to_problem_details() -> None:
    adapter = _adapter(FakeAlphaSiftClient(screen_error=TimeoutError("timeout token=super-secret")))

    with use_trace_context(TraceContext(trace_id="trace-timeout")):
        with pytest.raises(ScreeningProviderError) as error:
            adapter.screen(
                ScreeningRequest(
                    strategy_id="quality_momentum",
                    market="cn",
                    dataset_versions=DATASET_VERSIONS,
                )
            )
        problem = problem_from_exception(error.value)

    assert error.value.category is ScreeningProviderErrorCategory.TIMEOUT
    assert error.value.provider_id == ALPHASIFT_PROVIDER_ID
    assert error.value.operation == "screen"
    assert error.value.is_retryable is True
    assert problem.code is ApiErrorCode.PROVIDER_ERROR
    assert problem.status == 502
    assert problem.trace_id == "trace-timeout"
    assert "super-secret" not in problem.detail


def test_adapter_maps_malformed_strategy_payload_to_schema_drift() -> None:
    class BadStrategiesClient(FakeAlphaSiftClient):
        def list_strategies(self, context: dict[str, Any] | None = None) -> list[dict[str, Any]]:
            return [{"id": "broken", "version": "1.0.0"}]

    adapter = _adapter(BadStrategiesClient())

    with pytest.raises(ScreeningProviderError) as error:
        adapter.list_strategies()

    assert error.value.category is ScreeningProviderErrorCategory.SCHEMA_DRIFT
    assert error.value.operation == "strategies"
