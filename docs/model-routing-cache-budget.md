# Model Routing, Cache and Budget

> Task: `SAL-P5-012` Complete Model Routing, Cache and Budget<br>
> Date: 2026-07-28<br>
> Status: `APPROVED FOR SAL-P5-013 / SAL-P5-014 / SAL-P5-015 INPUT ONLY`

## Conclusion

`SAL-P5-012` adds a pure offline model invocation planning boundary:

```text
src/serenity_alpha_lab/application/model_routing.py
tests/application/test_model_routing_cache_budget.py
```

The planner consumes a prebuilt `EvidenceBundle`, a concrete `PromptRunBinding`, versioned invocation parameters, caller-provided model routes, an offline price table, budget usage snapshots and successful receipt metadata. It returns a deterministic plan describing whether a later Agent stage should reuse a cached receipt, call a selected route, degrade to an explicit fallback, or stop with `budget_exhausted` / `rate_limited`.

This task does not import LiteLLM, call a Provider or LLM, start Worker loops, read Evidence bodies, write Evidence Store, initialize Qlib, validate citations, render reports, schedule production work or promote formal portfolio backtests.

## Contracts

| Item | Contract |
|---|---|
| Model routing contract | `research.model_routing@1.0.0` |
| Invocation schema | `research.model_invocation` / `1.0.0` |
| Cache key schema | `research.model_invocation_cache_key` / `1.0.0` |
| Price table schema | `research.model_price_table` / `1.0.0` |
| Planner | `ModelInvocationPlanner` |
| Invocation request | `ModelInvocationRequest` |
| Invocation parameters | `ModelInvocationParameters` |
| Route declaration | `ModelRouteCandidate` |
| Price table | `ModelPriceTable` / `ModelPricePoint` |
| Budget policy | `ModelBudgetPolicy` |
| Usage snapshot | `ModelBudgetUsage` |
| Plan | `ModelInvocationPlan` |

## Cache Key Rules

`ModelInvocationCacheKey` is the canonical request hash. It includes:

- Evidence: `EvidenceBundle.bundle_id` and a canonical hash of `EvidenceBundle.to_record()`.
- Prompt: `PromptRunBinding.binding_hash` and output schema hash.
- Model: provider family, model family, model version and model capability hash.
- Parameters: concrete parameter version and parameter hash.
- Routing: route id/version and price version.

A successful cached receipt is reusable only when the caller-provided receipt record matches:

- `request_hash == cache_key_hash`
- `prompt_binding_hash`
- provider family
- model family
- valid receipt hash

Cache hits return `status=cache_hit`, `estimated_cost_usd=0.000000` and do not consume invocation, run or daily budget. The planner only matches caller-provided receipt metadata; it does not query persistence or write receipt rows.

## Budget Rules

`ModelBudgetPolicy` enforces three limits before any route is considered runnable:

- per-invocation budget
- per-run budget
- per-day budget

Cost estimates use the offline versioned `ModelPriceTable`:

```text
prompt_tokens * input_usd_per_1k_tokens / 1000
+ max_output_tokens * output_usd_per_1k_tokens / 1000
```

If the primary route exceeds budget but a lower-priority fallback fits, the plan returns `status=degraded` and `partial_reason=fallback_budget`. If no route fits, the plan returns `status=budget_exhausted` and `partial_reason=budget_exhausted`; later execution layers must surface a partial/budget-exhausted result rather than silently continuing.

The price table is configuration evidence, not live pricing. This task does not fetch, infer or refresh real vendor prices.

## Rate Limit Rules

Each route declares `max_calls_per_minute`. `ModelBudgetUsage.recent_calls_by_route` is caller-supplied and immutable for a planning call.

- Saturated primary route -> explicit fallback if another route fits.
- All routes saturated -> `status=rate_limited` and `partial_reason=rate_limited`.
- No hidden retry loop or background backoff is started.

## Non-Goals

- No LiteLLM import, Provider/LLM call, API route, Worker loop or queue dispatch.
- No Agent stage execution or stage checkpoint persistence writes.
- No Evidence Store writes, Evidence body reads, EvidenceBundle construction or Quant Evidence Adapter execution.
- No Citation Validator, citation repair loop, renderer, notification workflow or report publication.
- No tool runtime security enforcement; that remains `SAL-P5-014`.
- No production scheduling or formal portfolio backtest promotion.

## Verification

| Check | Result |
|---|---|
| Red target | `uv run --extra core --extra dev python -m pytest tests/application/test_model_routing_cache_budget.py -q` initially failed with `ModuleNotFoundError: No module named 'serenity_alpha_lab.application.model_routing'` |
| Focused target | `uv run --extra core --extra dev python -m pytest tests/application/test_model_routing_cache_budget.py -q` -> `4 passed` |
| Architecture guard | `uv run --extra core --extra dev python -m pytest tests/architecture/test_architecture_boundaries.py::test_model_routing_stays_offline_and_runtime_free -q` -> `1 passed` |
| Related P5 suite | `uv run --extra core --extra dev python -m pytest tests/application/test_model_routing_cache_budget.py tests/evidence/test_prompt_schema_registry.py tests/application/test_evidence_bundle_builder.py tests/repositories/test_agent_stage_store.py tests/architecture/test_architecture_boundaries.py -q` -> `40 passed` |
| Full suite | `uv run --extra core --extra dev python -m pytest -q` -> `466 passed, 3 skipped` |
| Compile | `uv run --extra core --extra dev python -m compileall -q src/serenity_alpha_lab tests` -> PASS |
| Dependency lock | `scripts/verify-python-dependency-lock.sh` -> PASS, `Resolved 298 packages` |
| Immutable upstream tag | `git rev-parse upstream/dsa-v3.26.1` -> `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a` |
| Diff hygiene | `git diff --check` -> PASS |

## Approval Record

This record approves offline model routing, exact cache key construction, versioned price-table cost estimation, invocation/run/day budget checks and explicit rate-limit fallback as input to `SAL-P5-013` Citation Validator and later trusted report work. Later P5 tasks must still implement actual model execution, citation validation, tool runtime security and trusted report publication before Gate G5 can pass.
