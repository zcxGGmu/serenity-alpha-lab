# SAL-P5-012 Model Routing / Cache / Budget Implementation Plan

> Scope: Complete only `SAL-P5-012` by adding an offline model invocation planner for route selection, exact cache keys, price-table cost estimates, invocation/run/day budgets, rate-limit fallback and explicit partial/budget-exhausted outcomes. Do not jump to Citation Validator, report rendering or later P5 tasks. Do not start real Provider/LLM calls, LiteLLM runtime calls, Worker loops, Qlib runtime, production scheduling, report generation or formal backtest promotion.

## Checklist

- [x] Re-read required project docs and confirm `git status --short --branch` / `git log -8 --oneline`.
- [x] Attempt read-only subagent exploration; fallback locally if tool wrapper rejects dispatch.
- [x] Create `docs/superpowers/plans/2026-07-28-model-routing-cache-budget.md`.
- [x] Write Red tests in `tests/application/test_model_routing_cache_budget.py`.
- [x] Run Red focused test and confirm failure for missing `serenity_alpha_lab.application.model_routing`.
- [x] Implement `src/serenity_alpha_lab/application/model_routing.py` as an offline model invocation planner.
- [x] Export public symbols from `src/serenity_alpha_lab/application/__init__.py`.
- [x] Add architecture guard proving model routing stays offline and runtime-free.
- [x] Add `docs/model-routing-cache-budget.md`.
- [x] Run focused, related and full verification.
- [x] Update `docs/development-progress-checklist.md`, `docs/development-status.md`, evidence/risk/decision records, this review section and next startup prompt.
- [x] Create Chinese checkpoint commit for `SAL-P5-012`: `83ae4310 feat(P5): 实现模型路由缓存与预算`.

## Current State

- Phase: P5 证据化 Agent、报告与成本治理.
- Gate: G4 passed; G5 not passed.
- Completed after implementation: `SAL-P5-001..012`.
- Current READY task after checkpoint: `SAL-P5-013` Citation Validator.
- Implementation checkpoint: `83ae4310 feat(P5): 实现模型路由缓存与预算`.
- Implementation checkpoint entering task: `50e6aa39 feat(P5): 实现多空反证与最终综合`.
- Status-sync checkpoint entering task: `e9e5ad69 docs: 同步 SAL-P5-011 checkpoint hash`.
- Hash-anchor checkpoint entering task: `c675fa0b docs: 记录 SAL-P5-011 状态同步 hash`; latest final anchor: `39ea0445 docs: 固化 SAL-P5-011 状态同步 hash-anchor`.

## Implementation Notes

- New module should be pure offline application logic: no LiteLLM import, no provider clients, no Worker loop, no SQLAlchemy dependency, no Evidence body reads and no DSA runtime calls.
- `ModelInvocationCacheKey` must include EvidenceBundle hash, PromptRunBinding hash, output schema hash, model/provider/version, model capability hash, parameter version/hash and route/price version.
- `ModelInvocationPlanner` should return a deterministic plan: `cache_hit`, `ready`, `degraded`, `budget_exhausted` or `rate_limited`.
- Cache reuse should match caller-provided successful receipt records by `request_hash`, `prompt_binding_hash`, provider/model and model-call receipt hash; cache hits must not consume budget.
- Budget checks must cover invocation, run and daily caps. If no route fits, return explicit partial/budget-exhausted metadata rather than silently continuing.
- Rate-limit checks should skip saturated routes and either choose an explicit fallback or return `rate_limited`; no hidden retry loop.
- Prices are versioned offline configuration/fixtures, not live vendor pricing. This task must not fetch or infer current provider prices.

## Planned Verification

- Red target: `uv run --extra core --extra dev python -m pytest tests/application/test_model_routing_cache_budget.py -q`.
- Focused target after implementation: same command should pass.
- Architecture guard: model routing imports only Python stdlib plus EvidenceBundle/PromptRegistry schema modules.
- Related suite: Model routing + PromptRegistry + EvidenceBundle + AgentStageStore + architecture tests.
- Full suite: `uv run --extra core --extra dev python -m pytest -q`, compileall, dependency lock, immutable upstream tag, `git diff --check`.

## Review

- Subagent exploration fallback: read-only subagent dispatch was attempted with scoped prompts, but the tool wrapper rejected optional argument serialization (`reasoning_effort must not be empty`, then `Provide either message or items, but not both`). Per `tasks/lessons.md`, proceeding with local senior review plus fresh verification instead of repeated retries.
- Red: `uv run --extra core --extra dev python -m pytest tests/application/test_model_routing_cache_budget.py -q` failed during collection with `ModuleNotFoundError: No module named 'serenity_alpha_lab.application.model_routing'`.
- Green focused: `uv run --extra core --extra dev python -m pytest tests/application/test_model_routing_cache_budget.py -q` -> `4 passed`.
- Architecture guard: `uv run --extra core --extra dev python -m pytest tests/architecture/test_architecture_boundaries.py::test_model_routing_stays_offline_and_runtime_free -q` -> `1 passed`.
- Related suite: ModelRouting/PromptRegistry/EvidenceBundle/AgentStageStore/Architecture `40 passed`.
- Full verification: related suite `40 passed`; `uv run --extra core --extra dev python -m pytest -q` -> `466 passed, 3 skipped`; compileall PASS; dependency lock PASS (`Resolved 298 packages`); immutable upstream tag remained `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`; `git diff --check` PASS after final status touch.
- Scope review: no real Provider/LLM/LiteLLM call, Worker loop, Qlib runtime, production scheduling, Citation Validator, report rendering or formal backtest promotion was started.
