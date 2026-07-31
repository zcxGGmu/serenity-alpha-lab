from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from enum import StrEnum
from types import MappingProxyType
from typing import Any

from serenity_alpha_lab.application.evidence_bundle_builder import EvidenceBundle
from serenity_alpha_lab.evidence.prompt_registry import PromptRunBinding


MODEL_ROUTING_CONTRACT_VERSION = "research.model_routing@1.0.0"
MODEL_INVOCATION_SCHEMA_NAME = "research.model_invocation"
MODEL_INVOCATION_SCHEMA_VERSION = "1.0.0"
MODEL_INVOCATION_CACHE_KEY_SCHEMA_NAME = "research.model_invocation_cache_key"
MODEL_INVOCATION_CACHE_KEY_SCHEMA_VERSION = "1.0.0"
MODEL_PRICE_TABLE_SCHEMA_NAME = "research.model_price_table"
MODEL_PRICE_TABLE_SCHEMA_VERSION = "1.0.0"

_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_SEMVER_RE = re.compile(r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")
_MONEY_QUANT = Decimal("0.000001")


class ModelRoutingError(ValueError):
    """Raised when model routing, cache or budget metadata is unsafe."""


class ModelInvocationStatus(StrEnum):
    READY = "ready"
    CACHE_HIT = "cache_hit"
    DEGRADED = "degraded"
    BUDGET_EXHAUSTED = "budget_exhausted"
    RATE_LIMITED = "rate_limited"


@dataclass(frozen=True, slots=True)
class ModelInvocationParameters:
    parameter_version: str
    max_output_tokens: int
    temperature: Decimal | str = "0.00"
    top_p: Decimal | str = "1.00"
    response_format: str = "json_schema"
    metadata: Mapping[str, str] = field(default_factory=dict)
    contract_version: str = MODEL_ROUTING_CONTRACT_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "parameter_version", _required_semver("parameter_version", self.parameter_version))
        object.__setattr__(self, "max_output_tokens", _positive_int("max_output_tokens", self.max_output_tokens))
        object.__setattr__(self, "temperature", _decimal_string("temperature", self.temperature))
        object.__setattr__(self, "top_p", _decimal_string("top_p", self.top_p))
        object.__setattr__(self, "response_format", _required_string("response_format", self.response_format))
        object.__setattr__(self, "metadata", MappingProxyType(_string_mapping("metadata", self.metadata)))
        object.__setattr__(self, "contract_version", _required_string("contract_version", self.contract_version))

    @property
    def parameter_hash(self) -> str:
        return _hash_record(self.to_record(include_hash=False))

    def to_record(self, *, include_hash: bool = True) -> dict[str, Any]:
        record = {
            "contract_version": self.contract_version,
            "parameter_version": self.parameter_version,
            "temperature": self.temperature,
            "top_p": self.top_p,
            "max_output_tokens": self.max_output_tokens,
            "response_format": self.response_format,
            "metadata": dict(self.metadata),
        }
        if include_hash:
            record["parameter_hash"] = self.parameter_hash
        return record


@dataclass(frozen=True, slots=True)
class ModelRouteCandidate:
    route_id: str
    route_version: str
    provider_family: str
    model_family: str
    model_version: str
    priority: int
    supports_json_schema: bool
    max_context_tokens: int
    max_output_tokens: int
    max_calls_per_minute: int
    metadata: Mapping[str, str] = field(default_factory=dict)
    contract_version: str = MODEL_ROUTING_CONTRACT_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "route_id", _required_string("route_id", self.route_id))
        object.__setattr__(self, "route_version", _required_semver("route_version", self.route_version))
        object.__setattr__(self, "provider_family", _required_string("provider_family", self.provider_family))
        object.__setattr__(self, "model_family", _required_string("model_family", self.model_family))
        object.__setattr__(self, "model_version", _required_string("model_version", self.model_version))
        object.__setattr__(self, "priority", _positive_int("priority", self.priority))
        object.__setattr__(self, "supports_json_schema", _required_bool("supports_json_schema", self.supports_json_schema))
        object.__setattr__(self, "max_context_tokens", _positive_int("max_context_tokens", self.max_context_tokens))
        object.__setattr__(self, "max_output_tokens", _positive_int("max_output_tokens", self.max_output_tokens))
        object.__setattr__(self, "max_calls_per_minute", _positive_int("max_calls_per_minute", self.max_calls_per_minute))
        object.__setattr__(self, "metadata", MappingProxyType(_string_mapping("metadata", self.metadata)))
        object.__setattr__(self, "contract_version", _required_string("contract_version", self.contract_version))

    def to_record(self) -> dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "route_id": self.route_id,
            "route_version": self.route_version,
            "provider_family": self.provider_family,
            "model_family": self.model_family,
            "model_version": self.model_version,
            "priority": self.priority,
            "supports_json_schema": self.supports_json_schema,
            "max_context_tokens": self.max_context_tokens,
            "max_output_tokens": self.max_output_tokens,
            "max_calls_per_minute": self.max_calls_per_minute,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True, slots=True)
class ModelPricePoint:
    provider_family: str
    model_family: str
    model_version: str
    price_version: str
    input_usd_per_1k_tokens: Decimal | str
    output_usd_per_1k_tokens: Decimal | str
    contract_version: str = MODEL_ROUTING_CONTRACT_VERSION
    schema_name: str = MODEL_PRICE_TABLE_SCHEMA_NAME
    schema_version: str = MODEL_PRICE_TABLE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "provider_family", _required_string("provider_family", self.provider_family))
        object.__setattr__(self, "model_family", _required_string("model_family", self.model_family))
        object.__setattr__(self, "model_version", _required_string("model_version", self.model_version))
        object.__setattr__(self, "price_version", _required_semver("price_version", self.price_version))
        object.__setattr__(
            self,
            "input_usd_per_1k_tokens",
            _decimal_string("input_usd_per_1k_tokens", self.input_usd_per_1k_tokens),
        )
        object.__setattr__(
            self,
            "output_usd_per_1k_tokens",
            _decimal_string("output_usd_per_1k_tokens", self.output_usd_per_1k_tokens),
        )
        object.__setattr__(self, "contract_version", _required_string("contract_version", self.contract_version))
        object.__setattr__(self, "schema_name", _required_string("schema_name", self.schema_name))
        object.__setattr__(self, "schema_version", _required_semver("schema_version", self.schema_version))

    def estimate_cost_usd(self, *, prompt_tokens: int, completion_tokens: int) -> str:
        prompt_cost = Decimal(prompt_tokens) * Decimal(self.input_usd_per_1k_tokens) / Decimal(1000)
        completion_cost = Decimal(completion_tokens) * Decimal(self.output_usd_per_1k_tokens) / Decimal(1000)
        return _money_string(prompt_cost + completion_cost)

    def to_record(self) -> dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "schema_name": self.schema_name,
            "schema_version": self.schema_version,
            "provider_family": self.provider_family,
            "model_family": self.model_family,
            "model_version": self.model_version,
            "price_version": self.price_version,
            "input_usd_per_1k_tokens": self.input_usd_per_1k_tokens,
            "output_usd_per_1k_tokens": self.output_usd_per_1k_tokens,
        }


@dataclass(frozen=True, slots=True)
class ModelPriceTable:
    price_points: Sequence[ModelPricePoint]
    contract_version: str = MODEL_ROUTING_CONTRACT_VERSION
    schema_name: str = MODEL_PRICE_TABLE_SCHEMA_NAME
    schema_version: str = MODEL_PRICE_TABLE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        points = tuple(self.price_points)
        if not points:
            raise ModelRoutingError("price_points are required")
        keys: set[tuple[str, str, str, str]] = set()
        for point in points:
            if type(point) is not ModelPricePoint:
                raise ModelRoutingError("price_points must contain ModelPricePoint objects")
            key = (point.provider_family, point.model_family, point.model_version, point.price_version)
            if key in keys:
                raise ModelRoutingError("duplicate model price point")
            keys.add(key)
        object.__setattr__(self, "price_points", points)
        object.__setattr__(self, "contract_version", _required_string("contract_version", self.contract_version))
        object.__setattr__(self, "schema_name", _required_string("schema_name", self.schema_name))
        object.__setattr__(self, "schema_version", _required_semver("schema_version", self.schema_version))

    def price_for(self, route: ModelRouteCandidate) -> ModelPricePoint:
        matches = [
            point
            for point in self.price_points
            if point.provider_family == route.provider_family
            and point.model_family == route.model_family
            and point.model_version == route.model_version
        ]
        if not matches:
            raise ModelRoutingError(f"missing price point for route {route.route_id}")
        return sorted(matches, key=lambda point: _parse_semver(point.price_version))[-1]

    def to_record(self) -> dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "schema_name": self.schema_name,
            "schema_version": self.schema_version,
            "price_points": [point.to_record() for point in self.price_points],
        }


@dataclass(frozen=True, slots=True)
class ModelBudgetPolicy:
    invocation_budget_usd: Decimal | str
    run_budget_usd: Decimal | str
    daily_budget_usd: Decimal | str
    contract_version: str = MODEL_ROUTING_CONTRACT_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "invocation_budget_usd", _decimal_string("invocation_budget_usd", self.invocation_budget_usd))
        object.__setattr__(self, "run_budget_usd", _decimal_string("run_budget_usd", self.run_budget_usd))
        object.__setattr__(self, "daily_budget_usd", _decimal_string("daily_budget_usd", self.daily_budget_usd))
        object.__setattr__(self, "contract_version", _required_string("contract_version", self.contract_version))

    def to_record(self) -> dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "invocation_budget_usd": self.invocation_budget_usd,
            "run_budget_usd": self.run_budget_usd,
            "daily_budget_usd": self.daily_budget_usd,
        }


@dataclass(frozen=True, slots=True)
class ModelBudgetUsage:
    run_spent_usd: Decimal | str = "0.000000"
    daily_spent_usd: Decimal | str = "0.000000"
    recent_calls_by_route: Mapping[str, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "run_spent_usd", _decimal_string("run_spent_usd", self.run_spent_usd))
        object.__setattr__(self, "daily_spent_usd", _decimal_string("daily_spent_usd", self.daily_spent_usd))
        object.__setattr__(self, "recent_calls_by_route", MappingProxyType(_int_mapping("recent_calls_by_route", self.recent_calls_by_route)))

    def to_record(self) -> dict[str, Any]:
        return {
            "run_spent_usd": self.run_spent_usd,
            "daily_spent_usd": self.daily_spent_usd,
            "recent_calls_by_route": dict(self.recent_calls_by_route),
        }


@dataclass(frozen=True, slots=True)
class ModelInvocationRequest:
    run_id: str
    stage_id: str
    trace_id: str
    evidence_bundle: EvidenceBundle
    prompt_binding: PromptRunBinding
    parameters: ModelInvocationParameters
    estimated_prompt_tokens: int | None = None
    contract_version: str = MODEL_ROUTING_CONTRACT_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "run_id", _required_string("run_id", self.run_id))
        object.__setattr__(self, "stage_id", _required_string("stage_id", self.stage_id))
        object.__setattr__(self, "trace_id", _required_string("trace_id", self.trace_id))
        if type(self.evidence_bundle) is not EvidenceBundle:
            raise ModelRoutingError("evidence_bundle must be an EvidenceBundle")
        if type(self.prompt_binding) is not PromptRunBinding:
            raise ModelRoutingError("prompt_binding must be a PromptRunBinding")
        if type(self.parameters) is not ModelInvocationParameters:
            raise ModelRoutingError("parameters must be ModelInvocationParameters")
        if self.prompt_binding.request.run_id != self.run_id:
            raise ModelRoutingError("prompt binding run_id must match model invocation request")
        if self.prompt_binding.request.stage_id != self.stage_id:
            raise ModelRoutingError("prompt binding stage_id must match model invocation request")
        if self.prompt_binding.request.trace_id != self.trace_id:
            raise ModelRoutingError("prompt binding trace_id must match model invocation request")
        if self.estimated_prompt_tokens is not None:
            object.__setattr__(self, "estimated_prompt_tokens", _positive_int("estimated_prompt_tokens", self.estimated_prompt_tokens))
        object.__setattr__(self, "contract_version", _required_string("contract_version", self.contract_version))

    @property
    def prompt_tokens(self) -> int:
        if self.estimated_prompt_tokens is not None:
            return self.estimated_prompt_tokens
        return _positive_int("evidence_bundle.estimated_tokens", self.evidence_bundle.estimated_tokens)


@dataclass(frozen=True, slots=True)
class ModelInvocationCacheKey:
    evidence_bundle_id: str
    evidence_bundle_hash: str
    prompt_binding_hash: str
    output_schema_hash: str
    provider_family: str
    model_family: str
    model_version: str
    model_capability_hash: str
    parameter_version: str
    parameter_hash: str
    route_id: str
    route_version: str
    price_version: str
    contract_version: str = MODEL_ROUTING_CONTRACT_VERSION
    schema_name: str = MODEL_INVOCATION_CACHE_KEY_SCHEMA_NAME
    schema_version: str = MODEL_INVOCATION_CACHE_KEY_SCHEMA_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "evidence_bundle_id", _required_string("evidence_bundle_id", self.evidence_bundle_id))
        object.__setattr__(self, "evidence_bundle_hash", _sha256("evidence_bundle_hash", self.evidence_bundle_hash))
        object.__setattr__(self, "prompt_binding_hash", _sha256("prompt_binding_hash", self.prompt_binding_hash))
        object.__setattr__(self, "output_schema_hash", _sha256("output_schema_hash", self.output_schema_hash))
        object.__setattr__(self, "provider_family", _required_string("provider_family", self.provider_family))
        object.__setattr__(self, "model_family", _required_string("model_family", self.model_family))
        object.__setattr__(self, "model_version", _required_string("model_version", self.model_version))
        object.__setattr__(self, "model_capability_hash", _sha256("model_capability_hash", self.model_capability_hash))
        object.__setattr__(self, "parameter_version", _required_semver("parameter_version", self.parameter_version))
        object.__setattr__(self, "parameter_hash", _sha256("parameter_hash", self.parameter_hash))
        object.__setattr__(self, "route_id", _required_string("route_id", self.route_id))
        object.__setattr__(self, "route_version", _required_semver("route_version", self.route_version))
        object.__setattr__(self, "price_version", _required_semver("price_version", self.price_version))
        object.__setattr__(self, "contract_version", _required_string("contract_version", self.contract_version))
        object.__setattr__(self, "schema_name", _required_string("schema_name", self.schema_name))
        object.__setattr__(self, "schema_version", _required_semver("schema_version", self.schema_version))

    @property
    def cache_key_hash(self) -> str:
        return _hash_record(self.to_record(include_hash=False))

    def to_record(self, *, include_hash: bool = True) -> dict[str, Any]:
        record = {
            "contract_version": self.contract_version,
            "schema_name": self.schema_name,
            "schema_version": self.schema_version,
            "evidence_bundle_id": self.evidence_bundle_id,
            "evidence_bundle_hash": self.evidence_bundle_hash,
            "prompt_binding_hash": self.prompt_binding_hash,
            "output_schema_hash": self.output_schema_hash,
            "provider_family": self.provider_family,
            "model_family": self.model_family,
            "model_version": self.model_version,
            "model_capability_hash": self.model_capability_hash,
            "parameter_version": self.parameter_version,
            "parameter_hash": self.parameter_hash,
            "route_id": self.route_id,
            "route_version": self.route_version,
            "price_version": self.price_version,
        }
        if include_hash:
            record["cache_key_hash"] = self.cache_key_hash
        return record


@dataclass(frozen=True, slots=True)
class ModelInvocationPlan:
    status: ModelInvocationStatus
    run_id: str
    stage_id: str
    trace_id: str
    prompt_binding_hash: str
    request_hash: str | None
    cache_key: ModelInvocationCacheKey | None
    selected_route_id: str | None
    provider_family: str | None
    model_family: str | None
    estimated_prompt_tokens: int
    max_output_tokens: int
    estimated_cost_usd: str
    budget_policy: ModelBudgetPolicy
    budget_usage: ModelBudgetUsage
    skipped_routes: Mapping[str, str] = field(default_factory=dict)
    partial_reason: str | None = None
    cache_receipt_hash: str | None = None
    contract_version: str = MODEL_ROUTING_CONTRACT_VERSION
    schema_name: str = MODEL_INVOCATION_SCHEMA_NAME
    schema_version: str = MODEL_INVOCATION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "status", ModelInvocationStatus(self.status))
        object.__setattr__(self, "run_id", _required_string("run_id", self.run_id))
        object.__setattr__(self, "stage_id", _required_string("stage_id", self.stage_id))
        object.__setattr__(self, "trace_id", _required_string("trace_id", self.trace_id))
        object.__setattr__(self, "prompt_binding_hash", _sha256("prompt_binding_hash", self.prompt_binding_hash))
        if self.request_hash is not None:
            object.__setattr__(self, "request_hash", _sha256("request_hash", self.request_hash))
        if self.cache_key is not None and type(self.cache_key) is not ModelInvocationCacheKey:
            raise ModelRoutingError("cache_key must be a ModelInvocationCacheKey")
        object.__setattr__(self, "selected_route_id", _optional_string(self.selected_route_id))
        object.__setattr__(self, "provider_family", _optional_string(self.provider_family))
        object.__setattr__(self, "model_family", _optional_string(self.model_family))
        object.__setattr__(self, "estimated_prompt_tokens", _positive_int("estimated_prompt_tokens", self.estimated_prompt_tokens))
        object.__setattr__(self, "max_output_tokens", _positive_int("max_output_tokens", self.max_output_tokens))
        object.__setattr__(self, "estimated_cost_usd", _decimal_string("estimated_cost_usd", self.estimated_cost_usd))
        if type(self.budget_policy) is not ModelBudgetPolicy:
            raise ModelRoutingError("budget_policy must be a ModelBudgetPolicy")
        if type(self.budget_usage) is not ModelBudgetUsage:
            raise ModelRoutingError("budget_usage must be a ModelBudgetUsage")
        object.__setattr__(self, "skipped_routes", MappingProxyType(_string_mapping("skipped_routes", self.skipped_routes)))
        object.__setattr__(self, "partial_reason", _optional_string(self.partial_reason))
        if self.cache_receipt_hash is not None:
            object.__setattr__(self, "cache_receipt_hash", _sha256("cache_receipt_hash", self.cache_receipt_hash))
        object.__setattr__(self, "contract_version", _required_string("contract_version", self.contract_version))
        object.__setattr__(self, "schema_name", _required_string("schema_name", self.schema_name))
        object.__setattr__(self, "schema_version", _required_semver("schema_version", self.schema_version))

    @property
    def invocation_allowed(self) -> bool:
        return self.status in {ModelInvocationStatus.READY, ModelInvocationStatus.DEGRADED}

    def to_record(self) -> dict[str, Any]:
        return _drop_none(
            {
                "contract_version": self.contract_version,
                "schema_name": self.schema_name,
                "schema_version": self.schema_version,
                "status": self.status.value,
                "run_id": self.run_id,
                "stage_id": self.stage_id,
                "trace_id": self.trace_id,
                "prompt_binding_hash": self.prompt_binding_hash,
                "request_hash": self.request_hash,
                "cache_key": self.cache_key.to_record() if self.cache_key is not None else None,
                "selected_route_id": self.selected_route_id,
                "provider_family": self.provider_family,
                "model_family": self.model_family,
                "estimated_prompt_tokens": self.estimated_prompt_tokens,
                "max_output_tokens": self.max_output_tokens,
                "estimated_cost_usd": self.estimated_cost_usd,
                "budget_policy": self.budget_policy.to_record(),
                "budget_usage": self.budget_usage.to_record(),
                "skipped_routes": dict(self.skipped_routes),
                "partial_reason": self.partial_reason,
                "cache_receipt_hash": self.cache_receipt_hash,
            }
        )


class ModelInvocationPlanner:
    """Plan model invocations without calling providers or model runtimes."""

    def __init__(self, price_table: ModelPriceTable, *, routes: Sequence[ModelRouteCandidate]) -> None:
        if type(price_table) is not ModelPriceTable:
            raise ModelRoutingError("price_table must be a ModelPriceTable")
        normalized_routes = tuple(routes)
        if not normalized_routes:
            raise ModelRoutingError("routes are required")
        route_ids: set[str] = set()
        for route in normalized_routes:
            if type(route) is not ModelRouteCandidate:
                raise ModelRoutingError("routes must contain ModelRouteCandidate objects")
            if route.route_id in route_ids:
                raise ModelRoutingError(f"duplicate route_id: {route.route_id}")
            route_ids.add(route.route_id)
        self._price_table = price_table
        self._routes = tuple(sorted(normalized_routes, key=lambda route: (route.priority, route.route_id)))

    def plan(
        self,
        request: ModelInvocationRequest,
        *,
        budget_policy: ModelBudgetPolicy,
        usage: ModelBudgetUsage,
        cached_receipts: Sequence[Mapping[str, Any]] = (),
    ) -> ModelInvocationPlan:
        if type(request) is not ModelInvocationRequest:
            raise ModelRoutingError("request must be a ModelInvocationRequest")
        if type(budget_policy) is not ModelBudgetPolicy:
            raise ModelRoutingError("budget_policy must be a ModelBudgetPolicy")
        if type(usage) is not ModelBudgetUsage:
            raise ModelRoutingError("usage must be a ModelBudgetUsage")

        skipped: dict[str, str] = {}
        saw_budget_skip = False
        saw_rate_skip = False

        for route in self._routes:
            price = self._price_table.price_for(route)
            static_reason = _route_static_rejection(route, request)
            if static_reason is not None:
                skipped[route.route_id] = static_reason
                continue

            recent_calls = usage.recent_calls_by_route.get(route.route_id, 0)
            if recent_calls >= route.max_calls_per_minute:
                skipped[route.route_id] = "rate_limited"
                saw_rate_skip = True
                continue

            cache_key = _cache_key_for(request, route=route, price=price)
            receipt_hash = _matching_receipt_hash(cached_receipts, cache_key=cache_key, request=request, route=route)
            if receipt_hash is not None:
                return _plan(
                    request,
                    budget_policy=budget_policy,
                    usage=usage,
                    status=ModelInvocationStatus.CACHE_HIT,
                    route=route,
                    cache_key=cache_key,
                    estimated_cost_usd="0.000000",
                    skipped_routes=skipped,
                    cache_receipt_hash=receipt_hash,
                )

            estimated_cost = price.estimate_cost_usd(
                prompt_tokens=request.prompt_tokens,
                completion_tokens=request.parameters.max_output_tokens,
            )
            budget_reason = _budget_rejection(estimated_cost, budget_policy=budget_policy, usage=usage)
            if budget_reason is not None:
                skipped[route.route_id] = budget_reason
                saw_budget_skip = True
                continue

            status = ModelInvocationStatus.READY
            partial_reason = None
            if skipped:
                status = ModelInvocationStatus.DEGRADED
                partial_reason = _fallback_reason(skipped)
            return _plan(
                request,
                budget_policy=budget_policy,
                usage=usage,
                status=status,
                route=route,
                cache_key=cache_key,
                estimated_cost_usd=estimated_cost,
                skipped_routes=skipped,
                partial_reason=partial_reason,
            )

        if saw_budget_skip:
            status = ModelInvocationStatus.BUDGET_EXHAUSTED
            partial_reason = "budget_exhausted"
        elif saw_rate_skip:
            status = ModelInvocationStatus.RATE_LIMITED
            partial_reason = "rate_limited"
        else:
            status = ModelInvocationStatus.RATE_LIMITED
            partial_reason = "no_route_available"
        return _plan(
            request,
            budget_policy=budget_policy,
            usage=usage,
            status=status,
            route=None,
            cache_key=None,
            estimated_cost_usd="0.000000",
            skipped_routes=skipped,
            partial_reason=partial_reason,
        )


def _plan(
    request: ModelInvocationRequest,
    *,
    budget_policy: ModelBudgetPolicy,
    usage: ModelBudgetUsage,
    status: ModelInvocationStatus,
    route: ModelRouteCandidate | None,
    cache_key: ModelInvocationCacheKey | None,
    estimated_cost_usd: str,
    skipped_routes: Mapping[str, str],
    partial_reason: str | None = None,
    cache_receipt_hash: str | None = None,
) -> ModelInvocationPlan:
    return ModelInvocationPlan(
        status=status,
        run_id=request.run_id,
        stage_id=request.stage_id,
        trace_id=request.trace_id,
        prompt_binding_hash=request.prompt_binding.binding_hash,
        request_hash=cache_key.cache_key_hash if cache_key is not None else None,
        cache_key=cache_key,
        selected_route_id=route.route_id if route is not None else None,
        provider_family=route.provider_family if route is not None else None,
        model_family=route.model_family if route is not None else None,
        estimated_prompt_tokens=request.prompt_tokens,
        max_output_tokens=request.parameters.max_output_tokens,
        estimated_cost_usd=estimated_cost_usd,
        budget_policy=budget_policy,
        budget_usage=usage,
        skipped_routes=dict(skipped_routes),
        partial_reason=partial_reason,
        cache_receipt_hash=cache_receipt_hash,
    )


def _cache_key_for(
    request: ModelInvocationRequest,
    *,
    route: ModelRouteCandidate,
    price: ModelPricePoint,
) -> ModelInvocationCacheKey:
    return ModelInvocationCacheKey(
        evidence_bundle_id=request.evidence_bundle.bundle_id,
        evidence_bundle_hash=_hash_record(request.evidence_bundle.to_record()),
        prompt_binding_hash=request.prompt_binding.binding_hash,
        output_schema_hash=request.prompt_binding.output_schema.schema_hash,
        provider_family=route.provider_family,
        model_family=route.model_family,
        model_version=route.model_version,
        model_capability_hash=request.prompt_binding.model_capability.capability_hash,
        parameter_version=request.parameters.parameter_version,
        parameter_hash=request.parameters.parameter_hash,
        route_id=route.route_id,
        route_version=route.route_version,
        price_version=price.price_version,
    )


def _route_static_rejection(route: ModelRouteCandidate, request: ModelInvocationRequest) -> str | None:
    if request.parameters.response_format == "json_schema" and not route.supports_json_schema:
        return "json_schema_unsupported"
    if request.parameters.max_output_tokens > route.max_output_tokens:
        return "output_tokens_exceeded"
    if request.prompt_tokens + request.parameters.max_output_tokens > route.max_context_tokens:
        return "context_tokens_exceeded"
    if (
        request.prompt_binding.model_capability.supports_json_schema
        and request.parameters.response_format == "json_schema"
        and not route.supports_json_schema
    ):
        return "json_schema_unsupported"
    return None


def _budget_rejection(
    estimated_cost_usd: str,
    *,
    budget_policy: ModelBudgetPolicy,
    usage: ModelBudgetUsage,
) -> str | None:
    cost = Decimal(estimated_cost_usd)
    if cost > Decimal(budget_policy.invocation_budget_usd):
        return "invocation_budget_exceeded"
    if Decimal(usage.run_spent_usd) + cost > Decimal(budget_policy.run_budget_usd):
        return "run_budget_exceeded"
    if Decimal(usage.daily_spent_usd) + cost > Decimal(budget_policy.daily_budget_usd):
        return "daily_budget_exceeded"
    return None


def _fallback_reason(skipped: Mapping[str, str]) -> str:
    reasons = set(skipped.values())
    if "rate_limited" in reasons:
        return "fallback_rate_limited"
    if reasons & {"invocation_budget_exceeded", "run_budget_exceeded", "daily_budget_exceeded"}:
        return "fallback_budget"
    return "fallback_route_unavailable"


def _matching_receipt_hash(
    receipts: Sequence[Mapping[str, Any]],
    *,
    cache_key: ModelInvocationCacheKey,
    request: ModelInvocationRequest,
    route: ModelRouteCandidate,
) -> str | None:
    for receipt in receipts:
        if not isinstance(receipt, Mapping):
            continue
        if receipt.get("request_hash") != cache_key.cache_key_hash:
            continue
        if receipt.get("prompt_binding_hash") != request.prompt_binding.binding_hash:
            continue
        if receipt.get("provider_family") != route.provider_family:
            continue
        if receipt.get("model_family") != route.model_family:
            continue
        receipt_hash = receipt.get("receipt_hash")
        if type(receipt_hash) is str and _SHA256_RE.fullmatch(receipt_hash):
            return receipt_hash
    return None


def _required_string(field_name: str, value: str) -> str:
    if type(value) is not str or not value.strip():
        raise ModelRoutingError(f"{field_name} is required")
    return value


def _optional_string(value: str | None) -> str | None:
    if value is None:
        return None
    return _required_string("optional string", value)


def _required_semver(field_name: str, value: str) -> str:
    value = _required_string(field_name, value)
    if not _SEMVER_RE.fullmatch(value):
        raise ModelRoutingError(f"{field_name} must be a semantic version")
    return value


def _parse_semver(value: str) -> tuple[int, int, int]:
    value = _required_semver("version", value)
    major, minor, patch = value.split(".")
    return int(major), int(minor), int(patch)


def _required_bool(field_name: str, value: bool) -> bool:
    if type(value) is not bool:
        raise ModelRoutingError(f"{field_name} must be a bool")
    return value


def _positive_int(field_name: str, value: int) -> int:
    if type(value) is not int or value <= 0:
        raise ModelRoutingError(f"{field_name} must be a positive integer")
    return value


def _decimal_string(field_name: str, value: Decimal | str) -> str:
    try:
        decimal = value if type(value) is Decimal else Decimal(_required_string(field_name, value))
    except Exception as exc:  # noqa: BLE001 - normalize arbitrary Decimal parse failures.
        raise ModelRoutingError(f"{field_name} must be a decimal string") from exc
    if decimal < Decimal("0"):
        raise ModelRoutingError(f"{field_name} must be non-negative")
    return _money_string(decimal)


def _money_string(value: Decimal) -> str:
    return str(value.quantize(_MONEY_QUANT, rounding=ROUND_HALF_UP))


def _sha256(field_name: str, value: str) -> str:
    value = _required_string(field_name, value)
    if not _SHA256_RE.fullmatch(value):
        raise ModelRoutingError(f"{field_name} must match sha256:<64 lowercase hex chars>")
    return value


def _string_mapping(field_name: str, value: Mapping[str, str]) -> dict[str, str]:
    if not isinstance(value, Mapping):
        raise ModelRoutingError(f"{field_name} must be a mapping")
    normalized: dict[str, str] = {}
    for key, item in value.items():
        normalized[_required_string(f"{field_name} key", key)] = _required_string(f"{field_name} value", item)
    return dict(sorted(normalized.items()))


def _int_mapping(field_name: str, value: Mapping[str, int]) -> dict[str, int]:
    if not isinstance(value, Mapping):
        raise ModelRoutingError(f"{field_name} must be a mapping")
    normalized: dict[str, int] = {}
    for key, item in value.items():
        if type(item) is not int or item < 0:
            raise ModelRoutingError(f"{field_name} values must be non-negative integers")
        normalized[_required_string(f"{field_name} key", key)] = item
    return dict(sorted(normalized.items()))


def _copy_json_value(value: Any) -> Any:
    return json.loads(_canonical_json(_plain_json_value(value)))


def _plain_json_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _plain_json_value(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_plain_json_value(item) for item in value]
    if isinstance(value, list):
        return [_plain_json_value(item) for item in value]
    return value


def _canonical_json(value: Any) -> str:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    except TypeError as exc:
        raise ModelRoutingError("value must be JSON serializable") from exc


def _hash_record(record: Mapping[str, Any]) -> str:
    payload = _canonical_json(_copy_json_value(record)).encode("utf-8")
    return f"sha256:{hashlib.sha256(payload).hexdigest()}"


def _drop_none(record: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in record.items() if value is not None}
