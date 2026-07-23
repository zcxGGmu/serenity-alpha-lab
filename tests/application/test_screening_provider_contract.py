from __future__ import annotations

from datetime import UTC, datetime

import pytest

from serenity_alpha_lab.application.tracing import TraceContext, use_trace_context
from serenity_alpha_lab.application.screening_provider import (
    FakeScreeningProvider,
    ScreeningProvider,
    ScreeningProviderError,
    ScreeningProviderErrorCategory,
    ScreeningRequest,
    ScreeningStrategy,
)


NOW = datetime(2026, 7, 23, 9, 30, tzinfo=UTC)
DATASET_VERSIONS = {
    "raw_daily_bars": "dsv_" + "a" * 32,
    "instrument_master": "dsv_" + "b" * 32,
}


def test_fake_provider_matches_protocol_and_returns_immutable_screening_result() -> None:
    provider = FakeScreeningProvider(
        clock=lambda: NOW,
        strategies=(
            ScreeningStrategy(
                strategy_id="quality_momentum",
                name="Quality Momentum",
                description="Deterministic smoke strategy",
                version="1.0.0",
                category="quality",
                tags=("quality", "momentum"),
                market_scope=("cn",),
            ),
        ),
        candidates={
            "quality_momentum": (
                {
                    "rank": 1,
                    "code": "600519",
                    "name": "贵州茅台",
                    "score": 98.5,
                    "reason": "fixture candidate",
                },
                {"rank": 2, "code": "000001", "name": "平安银行", "score": 88.0},
            )
        },
    )

    request = ScreeningRequest(
        strategy_id="quality_momentum",
        market="cn",
        dataset_versions=DATASET_VERSIONS,
        max_results=1,
    )
    with use_trace_context(TraceContext(trace_id="trace-screen", run_id="run-screen", stage_id="stage-l1")):
        result = provider.screen(request)

    assert isinstance(provider, ScreeningProvider)
    assert provider.status().provider_id == "fake_screening"
    assert provider.status().available is True
    assert [strategy.strategy_id for strategy in provider.list_strategies()] == ["quality_momentum"]
    assert result.provider_id == "fake_screening"
    assert result.strategy_id == "quality_momentum"
    assert result.strategy_version == "1.0.0"
    assert result.market == "cn"
    assert result.dataset_versions == DATASET_VERSIONS
    assert result.candidate_count == 1
    assert result.candidates == (
        {
            "rank": 1,
            "code": "600519",
            "name": "贵州茅台",
            "score": 98.5,
            "reason": "fixture candidate",
        },
    )
    assert result.llm_overlay_enabled is False
    assert result.requested_at == NOW
    assert result.received_at == NOW
    assert result.trace_id == "trace-screen"
    assert result.platform_run_id == "run-screen"
    assert result.stage_id == "stage-l1"

    with pytest.raises(TypeError):
        result.dataset_versions["raw_daily_bars"] = "dsv_" + "c" * 32  # type: ignore[index]
    with pytest.raises(TypeError):
        result.candidates[0]["score"] = 0  # type: ignore[index]


def test_screening_request_requires_concrete_dataset_versions() -> None:
    for invalid_versions in (
        {},
        {"raw_daily_bars": "latest"},
        {"raw_daily_bars": "dsv_not_hex"},
        {"": "dsv_" + "a" * 32},
    ):
        with pytest.raises(ScreeningProviderError) as error:
            ScreeningRequest(
                strategy_id="quality_momentum",
                market="cn",
                dataset_versions=invalid_versions,
            )
        assert error.value.category is ScreeningProviderErrorCategory.INVALID_REQUEST
        assert "concrete Dataset Version" in str(error.value) or "required" in str(error.value)


def test_fake_provider_uses_unified_error_semantics_for_unknown_strategy_and_market() -> None:
    provider = FakeScreeningProvider(
        clock=lambda: NOW,
        strategies=(
            ScreeningStrategy(
                strategy_id="cn_only",
                name="CN Only",
                description="fixture",
                version="1.0.0",
                market_scope=("cn",),
            ),
        ),
    )

    with pytest.raises(ScreeningProviderError) as unknown:
        provider.screen(
            ScreeningRequest(
                strategy_id="missing",
                market="cn",
                dataset_versions=DATASET_VERSIONS,
            )
        )
    assert unknown.value.provider_id == "fake_screening"
    assert unknown.value.operation == "screen"
    assert unknown.value.category is ScreeningProviderErrorCategory.INVALID_REQUEST
    assert unknown.value.is_retryable is False

    with pytest.raises(ScreeningProviderError) as unsupported_market:
        provider.screen(
            ScreeningRequest(
                strategy_id="cn_only",
                market="us",
                dataset_versions=DATASET_VERSIONS,
            )
        )
    assert unsupported_market.value.category is ScreeningProviderErrorCategory.INVALID_REQUEST
