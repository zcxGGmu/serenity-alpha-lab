# Agent Stage Persistence

> Task: `SAL-P5-007` Implement Agent Stage Persistence<br>
> Date: 2026-07-27<br>
> Status: `APPROVED FOR SAL-P5-008 / SAL-P5-009 / SAL-P5-010 / SAL-P5-012 INPUT ONLY`

## Conclusion

`SAL-P5-007` adds an offline SQLAlchemy-backed Agent Stage persistence boundary:

```text
src/serenity_alpha_lab/repositories/agent_stage_store.py
tests/repositories/test_agent_stage_store.py
```

The store persists deterministic stage definitions, Prompt Registry run bindings, stage checkpoints, model-call receipts and resume/cancel/failure-policy decisions. It is designed to let later Agent implementations resume from the last successful checkpoint and avoid duplicate model charges when a successful model-call receipt already exists.

This task persists metadata only. It does not execute Evidence Agent stages, call real Providers or LLMs, start Worker loops, initialize Qlib runtime, schedule production work, render reports, validate citations, send notifications or promote formal portfolio backtests.

## Contracts

| Item | Contract |
|---|---|
| Store contract | `research.agent_stage_store@1.0.0` |
| Checkpoint schema | `research.agent_stage_checkpoint` / `1.0.0` |
| Model-call receipt schema | `research.agent_model_call_receipt` / `1.0.0` |
| Resume plan schema | `research.agent_run_resume_plan` / `1.0.0` |
| Store implementation | `AgentStageStore` |
| Stage definition | `AgentStageDefinition` |
| Stage checkpoint | `AgentStageCheckpoint` |
| Model-call receipt | `AgentModelCallReceipt` |
| Resume plan | `AgentRunResumePlan` |

## Stage Rules

`deterministic_agent_stage_id()` computes `stage_id` from `run_id`, `stage_name`, `input_hash` and concrete `prompt_version`. `latest` aliases are rejected, and `input_hash` must be `sha256:<64 lowercase hex>`.

`AgentStageDefinition` records:

- `run_id`, `stage_name`, `role`, `input_hash`, `prompt_version` and deterministic `stage_id`.
- execution limits: `max_input_tokens`, `max_output_tokens`, `timeout_seconds` and `max_retries`.
- explicit `failure_policy`: `degrade`, `skip` or `fail_run`.
- tool allowlist names only; no tool execution occurs in this store.

`register_stage()` requires a `PromptRunBinding` or equivalent binding record whose run id, stage id, role and prompt version match the stage definition. This binds stage checkpoints to the concrete Prompt/Schema/Tool/Model versions and hashes from `SAL-P5-006`.

## Resume Rules

`AgentStageStore.resume_plan(run_id)` returns deterministic actions ordered by stage sequence:

| Persisted state | Resume action |
|---|---|
| `succeeded`, `degraded`, `skipped` | `skip_reused` |
| `running` with successful model-call receipt | `reuse_model_call` |
| `pending` or `running` without reusable receipt | `run` |
| `cancelled` | `stop_cancelled` |
| `failed` | `stop_failed` |

The resume plan is advisory metadata for later worker/Agent code. This task does not run the next stage or invoke a model.

## Model-Call Receipts

`record_model_call_success()` stores a caller-provided successful receipt:

- idempotency key and call id
- provider/model family identifiers
- prompt binding hash
- request and response hashes
- prompt/completion/total tokens
- cost, latency and completion timestamp
- canonical receipt hash

Replaying the same `idempotency_key` with identical immutable metadata is idempotent. Reusing the key with a different response hash, request hash, prompt binding hash, model metadata, token count, cost or latency raises `AgentStageStoreConflict`.

## Failure and Cancel Policy

`record_stage_failure()` applies the persisted failure policy rather than guessing at runtime:

- `degrade` -> stage status `degraded`
- `skip` -> stage status `skipped`
- `fail_run` -> stage status `failed`

`request_cancel()` marks pending/running stages for a run as `cancelled` and records the reason. It does not execute cleanup hooks, revoke queue messages or contact external services.

## Non-Goals

- No Agent stage execution, role Agent rewrites, prompt rendering or model invocation.
- No real Provider calls, real LLM calls, Worker loop, Qlib runtime or production scheduler.
- No Evidence Store writes, EvidenceBundle construction, Quant Evidence Adapter execution or evidence body reads.
- No model routing, cache policy, budget enforcement or price table; those start in `SAL-P5-012`.
- No Citation Validator, citation repair loop, report renderer, notification workflow or report publication.
- No change to legacy DSA `/api/v1/backtest/*` Signal Evaluation behavior.

## Verification

| Check | Result |
|---|---|
| Red target | `uv run --extra core --extra dev python -m pytest tests/repositories/test_agent_stage_store.py -q` initially failed with `ModuleNotFoundError: No module named 'serenity_alpha_lab.repositories.agent_stage_store'` |
| Focused target | `uv run --extra core --extra dev python -m pytest tests/repositories/test_agent_stage_store.py -q` -> `4 passed` |
| Architecture guard | `uv run --extra core --extra dev python -m pytest tests/architecture/test_architecture_boundaries.py::test_agent_stage_store_stays_persistence_only_and_runtime_free -q` -> `1 passed` |
| Related suite | `uv run --extra core --extra dev python -m pytest tests/repositories/test_agent_stage_store.py tests/repositories/test_persistent_task_backend.py tests/services/test_task_event_stream.py tests/domain/test_run_lifecycle.py tests/evidence/test_prompt_schema_registry.py tests/application/test_research_orchestrator_contract.py tests/integrations/test_dsa_research_orchestrator_facade.py tests/architecture/test_architecture_boundaries.py -q` -> `54 passed` |
| Full suite | `uv run --extra core --extra dev python -m pytest -q` -> `437 passed, 3 skipped` |
| Compile | `uv run --extra core --extra dev python -m compileall -q src/serenity_alpha_lab tests` -> PASS |
| Dependency lock | `scripts/verify-python-dependency-lock.sh` -> PASS, `Resolved 298 packages` |
| Immutable upstream tag | `git rev-parse upstream/dsa-v3.26.1` -> `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a` |
| Diff hygiene | `git diff --check` -> PASS |

## Approval Record

This record approves offline Agent Stage persistence as input to later role Agent rewrites and `SAL-P5-012` model routing/cache/budget work. Later P5 tasks must still implement Agent execution, model routing, budget/cache enforcement, citation validation, tool runtime security and renderers before Gate G5 can pass.
