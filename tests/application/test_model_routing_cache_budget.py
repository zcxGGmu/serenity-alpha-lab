from __future__ import annotations

from datetime import UTC, datetime

import pytest

from serenity_alpha_lab.application.evidence_bundle_builder import (
    EvidenceBundle,
    EvidenceBundleBudget,
    EvidenceBundleItem,
    EvidenceBundleRequest,
    EvidenceBundleRole,
    EvidenceBundleStatus,
)
from serenity_alpha_lab.application.model_routing import (
    ModelBudgetPolicy,
    ModelBudgetUsage,
    ModelInvocationParameters,
    ModelInvocationPlanner,
    ModelInvocationRequest,
    ModelInvocationStatus,
    ModelPricePoint,
    ModelPriceTable,
    ModelRouteCandidate,
)
from serenity_alpha_lab.evidence.prompt_registry import (
    AgentPromptRole,
    PromptRunBinding,
    PromptRunBindingRequest,
    default_prompt_schema_registry,
)
from serenity_alpha_lab.evidence.schema import (
    EvidenceEvaluationScope,
    EvidenceKind,
    EvidenceRecord,
    EvidenceSource,
    EvidenceTrustLevel,
)


NOW = datetime(2026, 7, 28, 10, 0, tzinfo=UTC)
HASH = "sha256:" + "a" * 64
ARTIFACT_HASH = "sha256:" + "b" * 64
RECEIPT_HASH = "sha256:" + "9" * 64


def test_model_invocation_planner_builds_exact_cache_key_and_reuses_successful_receipt() -> None:
    request = _request()
    route = _route("primary-json", priority=1, model_family="serenity-ci-small")
    price = _price(route, input_usd_per_1k_tokens="0.010000", output_usd_per_1k_tokens="0.020000")
    planner = ModelInvocationPlanner(ModelPriceTable(price_points=(price,)), routes=(route,))

    first = planner.plan(
        request,
        budget_policy=ModelBudgetPolicy(
            invocation_budget_usd="0.100000",
            run_budget_usd="1.000000",
            daily_budget_usd="5.000000",
        ),
        usage=ModelBudgetUsage(),
        cached_receipts=(),
    )
    receipt = {
        "request_hash": first.request_hash,
        "prompt_binding_hash": first.prompt_binding_hash,
        "provider_family": route.provider_family,
        "model_family": route.model_family,
        "receipt_hash": RECEIPT_HASH,
    }

    replay = planner.plan(
        request,
        budget_policy=ModelBudgetPolicy(
            invocation_budget_usd="0.000001",
            run_budget_usd="0.000001",
            daily_budget_usd="0.000001",
        ),
        usage=ModelBudgetUsage(run_spent_usd="99.000000", daily_spent_usd="99.000000"),
        cached_receipts=(receipt,),
    )

    cache_record = first.cache_key.to_record()
    assert first.status is ModelInvocationStatus.READY
    assert first.request_hash == first.cache_key.cache_key_hash
    assert cache_record["evidence_bundle_hash"].startswith("sha256:")
    assert cache_record["prompt_binding_hash"] == request.prompt_binding.binding_hash
    assert cache_record["output_schema_hash"] == request.prompt_binding.output_schema.schema_hash
    assert cache_record["provider_family"] == "litellm"
    assert cache_record["model_family"] == "serenity-ci-small"
    assert cache_record["model_version"] == "2026-07-28"
    assert cache_record["parameter_version"] == "1.0.0"
    assert cache_record["parameter_hash"] == request.parameters.parameter_hash

    assert replay.status is ModelInvocationStatus.CACHE_HIT
    assert replay.selected_route_id == "primary-json"
    assert replay.estimated_cost_usd == "0.000000"
    assert replay.cache_receipt_hash == RECEIPT_HASH
    assert replay.partial_reason is None


def test_budget_policy_enforces_invocation_run_and_daily_caps_without_silent_continue() -> None:
    request = _request(max_output_tokens=400)
    primary = _route("primary-json", priority=1, model_family="serenity-ci-large")
    fallback = _route("fallback-json", priority=2, model_family="serenity-ci-small")
    primary_price = _price(primary, input_usd_per_1k_tokens="0.100000", output_usd_per_1k_tokens="0.200000")
    fallback_price = _price(fallback, input_usd_per_1k_tokens="0.001000", output_usd_per_1k_tokens="0.002000")
    planner = ModelInvocationPlanner(
        ModelPriceTable(price_points=(primary_price, fallback_price)),
        routes=(primary, fallback),
    )

    degraded = planner.plan(
        request,
        budget_policy=ModelBudgetPolicy(
            invocation_budget_usd="0.005000",
            run_budget_usd="1.000000",
            daily_budget_usd="5.000000",
        ),
        usage=ModelBudgetUsage(),
        cached_receipts=(),
    )
    exhausted = planner.plan(
        request,
        budget_policy=ModelBudgetPolicy(
            invocation_budget_usd="0.000001",
            run_budget_usd="1.000000",
            daily_budget_usd="5.000000",
        ),
        usage=ModelBudgetUsage(),
        cached_receipts=(),
    )
    run_exhausted = planner.plan(
        request,
        budget_policy=ModelBudgetPolicy(
            invocation_budget_usd="1.000000",
            run_budget_usd="0.001000",
            daily_budget_usd="5.000000",
        ),
        usage=ModelBudgetUsage(run_spent_usd="0.000950"),
        cached_receipts=(),
    )
    daily_exhausted = planner.plan(
        request,
        budget_policy=ModelBudgetPolicy(
            invocation_budget_usd="1.000000",
            run_budget_usd="5.000000",
            daily_budget_usd="0.001000",
        ),
        usage=ModelBudgetUsage(daily_spent_usd="0.000950"),
        cached_receipts=(),
    )

    assert degraded.status is ModelInvocationStatus.DEGRADED
    assert degraded.selected_route_id == "fallback-json"
    assert degraded.partial_reason == "fallback_budget"
    assert degraded.skipped_routes["primary-json"] == "invocation_budget_exceeded"

    assert exhausted.status is ModelInvocationStatus.BUDGET_EXHAUSTED
    assert exhausted.selected_route_id is None
    assert exhausted.partial_reason == "budget_exhausted"
    assert set(exhausted.skipped_routes.values()) == {"invocation_budget_exceeded"}

    assert run_exhausted.status is ModelInvocationStatus.BUDGET_EXHAUSTED
    assert run_exhausted.partial_reason == "budget_exhausted"
    assert "run_budget_exceeded" in set(run_exhausted.skipped_routes.values())

    assert daily_exhausted.status is ModelInvocationStatus.BUDGET_EXHAUSTED
    assert daily_exhausted.partial_reason == "budget_exhausted"
    assert "daily_budget_exceeded" in set(daily_exhausted.skipped_routes.values())


def test_rate_limit_fallback_is_explicit_and_returns_partial_when_all_routes_are_saturated() -> None:
    request = _request()
    primary = _route("primary-json", priority=1, model_family="serenity-ci-large", max_calls_per_minute=1)
    fallback = _route("fallback-json", priority=2, model_family="serenity-ci-small", max_calls_per_minute=2)
    planner = ModelInvocationPlanner(
        ModelPriceTable(
            price_points=(
                _price(primary, input_usd_per_1k_tokens="0.010000", output_usd_per_1k_tokens="0.020000"),
                _price(fallback, input_usd_per_1k_tokens="0.001000", output_usd_per_1k_tokens="0.002000"),
            )
        ),
        routes=(primary, fallback),
    )
    budget = ModelBudgetPolicy(
        invocation_budget_usd="1.000000",
        run_budget_usd="5.000000",
        daily_budget_usd="10.000000",
    )

    fallback_plan = planner.plan(
        request,
        budget_policy=budget,
        usage=ModelBudgetUsage(recent_calls_by_route={"primary-json": 1}),
        cached_receipts=(),
    )
    saturated = planner.plan(
        request,
        budget_policy=budget,
        usage=ModelBudgetUsage(recent_calls_by_route={"primary-json": 1, "fallback-json": 2}),
        cached_receipts=(),
    )

    assert fallback_plan.status is ModelInvocationStatus.DEGRADED
    assert fallback_plan.selected_route_id == "fallback-json"
    assert fallback_plan.partial_reason == "fallback_rate_limited"
    assert fallback_plan.skipped_routes["primary-json"] == "rate_limited"

    assert saturated.status is ModelInvocationStatus.RATE_LIMITED
    assert saturated.selected_route_id is None
    assert saturated.partial_reason == "rate_limited"
    assert set(saturated.skipped_routes.values()) == {"rate_limited"}


def test_model_routing_rejects_prompt_binding_context_mismatch_and_latest_parameters() -> None:
    request = _request()

    with pytest.raises(ValueError, match="stage_id"):
        ModelInvocationRequest(
            run_id=request.run_id,
            stage_id="stage_other",
            trace_id=request.trace_id,
            evidence_bundle=request.evidence_bundle,
            prompt_binding=request.prompt_binding,
            parameters=request.parameters,
        )

    with pytest.raises(ValueError, match="semantic version"):
        ModelInvocationParameters(parameter_version="latest", max_output_tokens=128)


def _request(*, max_output_tokens: int = 256) -> ModelInvocationRequest:
    registry = default_prompt_schema_registry()
    prompt = registry.default_prompt_for_role(AgentPromptRole.DECISION)
    stage_id = "stage_model_routing"
    binding = registry.resolve_for_run(
        PromptRunBindingRequest(
            run_id="run-model-routing-001",
            stage_id=stage_id,
            trace_id="trace-model-routing-001",
            role=AgentPromptRole.DECISION,
            prompt_id=prompt.prompt_id,
            prompt_version=prompt.prompt_version,
            resolved_at=NOW,
        )
    )
    return ModelInvocationRequest(
        run_id="run-model-routing-001",
        stage_id=stage_id,
        trace_id="trace-model-routing-001",
        evidence_bundle=_bundle(),
        prompt_binding=binding,
        parameters=ModelInvocationParameters(
            parameter_version="1.0.0",
            temperature="0.20",
            top_p="0.90",
            max_output_tokens=max_output_tokens,
            response_format="json_schema",
        ),
    )


def _bundle() -> EvidenceBundle:
    request = EvidenceBundleRequest(
        tenant_id="tenant-a",
        team_id="team-alpha",
        owner_user_id="user-1",
        instrument_id="600519.XSHG",
        decision_time=NOW,
        role=EvidenceBundleRole.DECISION,
        budget=EvidenceBundleBudget(max_prompt_tokens=2_000),
    )
    evidence = EvidenceRecord(
        evidence_id="ev_metric",
        kind=EvidenceKind.BACKTEST_PERFORMANCE_METRICS,
        evaluation_scope=EvidenceEvaluationScope.FORMAL_PORTFOLIO_BACKTEST,
        title="Performance metrics",
        summary="Formal backtest metrics are available for decision synthesis.",
        source=EvidenceSource(
            source_id="src_metric",
            source_type="artifact",
            schema_name="quant.backtest.performance_metrics",
            schema_version="1.0.0",
        ),
        available_at=NOW,
        content_hash=HASH,
        trust=EvidenceTrustLevel.AUTHORITATIVE,
        dataset_versions={"bars": "dsv_" + "1" * 32},
        instrument_id="600519.XSHG",
        run_id="run-model-routing-001",
        stage_id="stage-risk",
        artifact_id="artifact-metrics",
        artifact_hash=ARTIFACT_HASH,
        metadata={"llm_recompute_allowed": False},
    )
    return EvidenceBundle(
        bundle_id="bundle-model-routing",
        request=request,
        schema_instructions="Use only included evidence.",
        status=EvidenceBundleStatus.COMPLETE,
        items=(
            EvidenceBundleItem(
                evidence=evidence,
                priority_score=100,
                priority_reasons=("role:decision:backtest_performance_metrics",),
                estimated_tokens=600,
            ),
        ),
        excluded_items=(),
        estimated_tokens=600,
        schema_instruction_tokens=32,
    )


def _route(
    route_id: str,
    *,
    priority: int,
    model_family: str,
    max_calls_per_minute: int = 10,
) -> ModelRouteCandidate:
    return ModelRouteCandidate(
        route_id=route_id,
        route_version="1.0.0",
        provider_family="litellm",
        model_family=model_family,
        model_version="2026-07-28",
        priority=priority,
        supports_json_schema=True,
        max_context_tokens=8_192,
        max_output_tokens=1_024,
        max_calls_per_minute=max_calls_per_minute,
    )


def _price(
    route: ModelRouteCandidate,
    *,
    input_usd_per_1k_tokens: str,
    output_usd_per_1k_tokens: str,
) -> ModelPricePoint:
    return ModelPricePoint(
        provider_family=route.provider_family,
        model_family=route.model_family,
        model_version=route.model_version,
        price_version="1.0.0",
        input_usd_per_1k_tokens=input_usd_per_1k_tokens,
        output_usd_per_1k_tokens=output_usd_per_1k_tokens,
    )
