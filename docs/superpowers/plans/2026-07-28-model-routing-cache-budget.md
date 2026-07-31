# Model Routing Cache Budget Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement `SAL-P5-012` as an offline model invocation planner that selects routes, computes exact cache keys, estimates costs from versioned price tables, enforces invocation/run/day budgets, handles rate-limit fallback and returns explicit partial states.

**Architecture:** Add a pure application-layer module that consumes existing `EvidenceBundle` and `PromptRunBinding` records plus caller-provided route, price, budget and receipt metadata. The planner produces deterministic `ModelInvocationPlan` records only; it never imports LiteLLM, calls providers, starts workers, fetches evidence bodies or writes reports.

**Tech Stack:** Python dataclasses/enums/Decimal, existing P5 EvidenceBundle and PromptRegistry contracts, pytest, architecture import guards.

---

### Task 1: Red Tests For Routing, Cache, Budget And Rate Limits

**Files:**
- Create: `tests/application/test_model_routing_cache_budget.py`

- [ ] **Step 1: Write cache-key and cache-hit test**

```python
def test_model_invocation_planner_builds_exact_cache_key_and_reuses_successful_receipt() -> None:
    request, route, price, policy = fixture_request_route_price_and_budget()
    planner = ModelInvocationPlanner(ModelPriceTable(price_points=(price,)), routes=(route,))
    first = planner.plan(request, budget_policy=policy, usage=ModelBudgetUsage(), cached_receipts=())
    receipt = {"request_hash": first.cache_key.cache_key_hash, "prompt_binding_hash": first.prompt_binding_hash, "provider_family": route.provider_family, "model_family": route.model_family, "receipt_hash": "sha256:" + "9" * 64}
    replay = planner.plan(request, budget_policy=policy, usage=ModelBudgetUsage(), cached_receipts=(receipt,))
    assert replay.status is ModelInvocationStatus.CACHE_HIT
    assert replay.estimated_cost_usd == "0.000000"
```

- [ ] **Step 2: Write budget-exhausted and fallback tests**

```python
def test_model_invocation_budget_enforces_invocation_run_and_daily_caps_without_silent_continue() -> None:
    request, expensive, cheap, expensive_price, cheap_price = fixture_two_routes()
    planner = ModelInvocationPlanner(ModelPriceTable(price_points=(expensive_price, cheap_price)), routes=(expensive, cheap))
    plan = planner.plan(request, budget_policy=ModelBudgetPolicy(invocation_budget_usd="0.000001", run_budget_usd="1", daily_budget_usd="1"), usage=ModelBudgetUsage(), cached_receipts=())
    assert plan.status is ModelInvocationStatus.BUDGET_EXHAUSTED
    assert plan.partial_reason == "budget_exhausted"
```

- [ ] **Step 3: Write architecture guard test**

```python
def test_model_routing_stays_offline_and_runtime_free() -> None:
    target = PACKAGE_ROOT / "application" / "model_routing.py"
    assert target.exists()
    assert "litellm" not in imported_modules(target)
```

- [ ] **Step 4: Run Red target**

Run: `uv run --extra core --extra dev python -m pytest tests/application/test_model_routing_cache_budget.py -q`

Expected: FAIL during collection with `ModuleNotFoundError: No module named 'serenity_alpha_lab.application.model_routing'`.

### Task 2: Implement Offline Model Invocation Planner

**Files:**
- Create: `src/serenity_alpha_lab/application/model_routing.py`
- Modify: `src/serenity_alpha_lab/application/__init__.py`

- [ ] **Step 1: Add dataclass contracts**

Implement:
- `MODEL_ROUTING_CONTRACT_VERSION = "research.model_routing@1.0.0"`
- `ModelInvocationStatus`
- `ModelRoutingError`
- `ModelInvocationParameters`
- `ModelRouteCandidate`
- `ModelPricePoint`
- `ModelPriceTable`
- `ModelBudgetPolicy`
- `ModelBudgetUsage`
- `ModelInvocationRequest`
- `ModelInvocationCacheKey`
- `ModelInvocationPlan`
- `ModelInvocationPlanner`

- [ ] **Step 2: Implement deterministic hash helpers**

Use canonical JSON with `sort_keys=True`, ASCII output and compact separators. Hashes must be `sha256:<64 lowercase hex chars>`.

- [ ] **Step 3: Implement cache-key construction**

Cache key record must include:
- `evidence_bundle_id`
- `evidence_bundle_hash`
- `prompt_binding_hash`
- `output_schema_hash`
- `provider_family`
- `model_family`
- `model_version`
- `model_capability_hash`
- `parameter_version`
- `parameter_hash`
- `route_version`
- `price_version`

- [ ] **Step 4: Implement planning rules**

Rules:
- Cache hit if a receipt record matches `request_hash`, `prompt_binding_hash`, provider and model; cost becomes zero.
- Skip routes that cannot fit prompt/output context.
- Skip saturated routes by `max_calls_per_minute`.
- Estimate cost using versioned price table and prompt/output token counts.
- Enforce invocation, run and daily budgets before returning `ready`.
- Choose explicit lower-priority fallback as `degraded` when the primary route is budget/rate limited and a fallback fits.
- Return `budget_exhausted` or `rate_limited` with `partial_reason` when no route is usable.

- [ ] **Step 5: Export public symbols**

Add imports and `__all__` entries in `src/serenity_alpha_lab/application/__init__.py`.

- [ ] **Step 6: Run focused Green target**

Run: `uv run --extra core --extra dev python -m pytest tests/application/test_model_routing_cache_budget.py -q`

Expected: PASS.

### Task 3: Documentation And Architecture Guard

**Files:**
- Modify: `tests/architecture/test_architecture_boundaries.py`
- Create: `docs/model-routing-cache-budget.md`

- [ ] **Step 1: Add architecture guard**

Allow only stdlib modules plus:
- `serenity_alpha_lab.application.evidence_bundle_builder`
- `serenity_alpha_lab.evidence.prompt_registry`

Forbidden roots include `litellm`, `fastapi`, `sqlalchemy`, `qlib`, `akshare`, `tushare`, `yfinance`, `baostock`, `efinance`.

- [ ] **Step 2: Add evidence document**

Document:
- contract and schema names
- cache key composition
- budget policy
- rate-limit fallback/degrade behavior
- non-goals and strict runtime boundary
- verification table

- [ ] **Step 3: Run related suite**

Run: `uv run --extra core --extra dev python -m pytest tests/application/test_model_routing_cache_budget.py tests/evidence/test_prompt_schema_registry.py tests/application/test_evidence_bundle_builder.py tests/repositories/test_agent_stage_store.py tests/architecture/test_architecture_boundaries.py -q`

Expected: PASS.

### Task 4: Status Sync And Checkpoint

**Files:**
- Modify: `docs/development-progress-checklist.md`
- Modify: `docs/development-status.md`
- Modify: `tasks/todo.md`

- [ ] **Step 1: Run full verification**

Run:
- `uv run --extra core --extra dev python -m pytest -q`
- `uv run --extra core --extra dev python -m compileall -q src/serenity_alpha_lab tests`
- `scripts/verify-python-dependency-lock.sh`
- `git rev-parse upstream/dsa-v3.26.1`
- `git diff --check`

Expected: all pass; upstream tag remains `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`.

- [ ] **Step 2: Update P5 records**

Update `SAL-P5-012` to `DONE`, add AEV-100 and DEC-098 entries, advance total progress to `100/129`, make `SAL-P5-013` the next READY task, and preserve strict no-runtime guardrails.

- [ ] **Step 3: Commit checkpoint**

Run:

```bash
git add src/serenity_alpha_lab/application/model_routing.py src/serenity_alpha_lab/application/__init__.py tests/application/test_model_routing_cache_budget.py tests/architecture/test_architecture_boundaries.py docs/model-routing-cache-budget.md docs/superpowers/plans/2026-07-28-model-routing-cache-budget.md docs/development-progress-checklist.md docs/development-status.md tasks/todo.md
git commit -m "feat(P5): 实现模型路由缓存与预算"
```

Expected: Chinese checkpoint commit created for `SAL-P5-012`.
