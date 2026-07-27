# SAL-P5-007 Agent Stage Persistence Plan

> Scope: Add offline Agent Stage persistence for run/stage checkpoints, prompt binding snapshots, model-call receipts and resume/cancel/degrade/fail policy. This task must not execute Evidence Agent stages, call real Providers/LLMs, start Worker loops, initialize Qlib runtime, schedule production work, render reports or promote formal portfolio backtests.

## Checklist

- [x] Re-read `AGENTS.md`, `tasks/lessons.md`, current status/checklist, P5 evidence docs, Prompt Registry doc, current Git state and relevant Run/Task/ResearchOrchestrator patterns.
- [x] Attempt read-only subagent scope review; wrapper rejected payloads with empty optional field errors, so follow project lesson and use local senior review plus fresh verification fallback.
- [x] Red: add `tests/repositories/test_agent_stage_store.py` proving persisted stage definitions, prompt run bindings, model-call receipts, resume from last successful checkpoint, cancel propagation and degrade/fail policy.
- [x] Green: add `src/serenity_alpha_lab/repositories/agent_stage_store.py` with SQLAlchemy-backed stage repository, deterministic `stage_id` helper, checkpoint records and idempotent model-call receipt reuse.
- [x] Export public stage persistence symbols from `src/serenity_alpha_lab/repositories/__init__.py`.
- [x] Add architecture guard proving Agent Stage persistence remains free of concrete DSA Agent, Provider/LLM, Worker, Qlib, FastAPI and report renderer imports.
- [x] Add `docs/agent-stage-persistence.md` with contract table, checkpoint/resume rules, non-goals and verification evidence.
- [ ] Update `docs/development-progress-checklist.md` with `SAL-P5-007` done, P5 `7/18`, total `95/129`, new DEC/AEV rows and next-step status.
- [ ] Update `docs/development-status.md` with latest task/checkpoint anchors, completion range and next startup prompt for `SAL-P5-008`.
- [ ] Run focused stage-store tests, related TaskBackend/RunLifecycle/PromptRegistry/Architecture suite, full pytest, compileall, dependency lock guard, immutable tag check and `git diff --check`.
- [ ] Review changes, stage only `SAL-P5-007` files and create required Chinese checkpoint commit, then status/hash-anchor docs commit if needed.

## File Targets

- Create: `src/serenity_alpha_lab/repositories/agent_stage_store.py` for persisted Agent stage metadata and checkpoints.
- Create: `tests/repositories/test_agent_stage_store.py` for Red/Green contract coverage.
- Modify: `src/serenity_alpha_lab/repositories/__init__.py` to export public stage-store symbols.
- Modify: `tests/architecture/test_architecture_boundaries.py` to lock runtime-free imports.
- Create: `docs/agent-stage-persistence.md` for SAL-P5-007 evidence record.
- Modify: `docs/development-status.md` and `docs/development-progress-checklist.md` only during task status sync.

## Scope Guard

- Stage persistence stores metadata and hashes only; it does not invoke models, execute tools, call Providers, read Evidence bodies, render reports or run Worker loops.
- `stage_id` is deterministic from `run_id`, `stage_name`, `input_hash` and `prompt_version`; callers may also pass a precomputed id for compatibility.
- A completed/degraded stage checkpoint is reusable after process restart and appears as `skip_reused` in a resume plan; failed/skipped stages are not treated as successful model-call cache hits.
- A successful model-call receipt records provider/model identifiers, binding hash, request/response hashes, token/cost/latency metadata and a caller-provided idempotency key; replaying the same receipt is idempotent, while changing immutable receipt fields raises a conflict.
- Failure policy is explicit per stage: `degrade`, `skip` or `fail_run`. Cancel requests mark pending/running stages as cancelled without executing cleanup hooks.
