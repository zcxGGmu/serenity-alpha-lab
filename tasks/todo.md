# SAL-P4-020 Formal Backtest API Plan

> Scope: Complete `SAL-P4-020` by adding a framework-neutral formal portfolio backtest API facade for `/api/v1/quant/backtest-runs`. It must expose create/status/metrics/orders/positions/audit/cancel/artifact query behavior, keep large result rows behind Artifact reads with cursor pagination, and remain clearly separated from legacy DSA Signal Evaluation. Do not start Quant Lab, Evidence Agent, real Provider/LLM calls, Qlib runtime, or a Worker loop.

## Checklist

- [x] Re-read `AGENTS.md`, `tasks/lessons.md`, current status/checklist, development plan, P4 evidence docs, current Git status and recent commits.
- [x] Attempt read-only subagent exploration for SAL-P4-020 boundaries; platform wrapper injected empty optional fields again, so fallback local senior review is active per project lessons.
- [x] Write implementation plan at `docs/superpowers/plans/2026-07-26-formal-backtest-api.md`.
- [x] Red: add `tests/application/test_backtest_api.py` covering route metadata, idempotent creation, status/metrics/audit responses, cursor-paginated orders/positions, artifact authorization and boundary imports.
- [x] Green: implement `src/serenity_alpha_lab/application/backtest_api.py` with route DTOs, API service, in-memory repository, task submission, resource-supervisor integration and artifact access policy.
- [x] Add `docs/backtest-api.md` with route contract, response semantics, artifact pagination/authorization, legacy separation, non-goals and verification evidence.
- [x] Update progress checklist/status docs with `SAL-P4-020` done, P4 `20/22`, total `86/129`, decision/evidence rows and `SAL-P4-021` READY but not started.
- [x] Run focused, related and full verification plus compile/lock/patch/tag/diff checks.
- [ ] Review, stage only `SAL-P4-020` files and create the required Chinese checkpoint commit.

## Scope Guard

- The formal API namespace is `/api/v1/quant/backtest-runs`; legacy `/api/v1/backtest/*` remains Signal Evaluation and must not be renamed or reused.
- API create submits metadata and starts resource-supervisor tracking only; it must not run a Worker loop or execute real Provider/LLM/Qlib runtime work.
- Metrics, orders, positions and audit outputs are read from formal `BacktestArtifactBundle` descriptors and immutable Artifact content; no large rows are embedded in create/status responses.
- Artifact download/query must require an explicit access subject and authorization policy.
- Legacy DSA Signal Evaluation, AlphaSift T+N evaluation, Screen result, Qlib internal evidence and Dataset conversion artifacts remain outside the formal portfolio backtest namespace.

## Review Notes

- Red target initially failed with `ModuleNotFoundError: No module named 'serenity_alpha_lab.application.backtest_api'`.
- Green focused target `uv run --extra core --extra dev python -m pytest tests/application/test_backtest_api.py -q` passed with `7 passed`.
- Related suite passed with `37 passed`; full suite passed with `402 passed, 3 skipped`.
- Compileall, dependency lock guard, DSA patch check, immutable `upstream/dsa-v3.26.1` tag check and `git diff --check` passed.
- Subagent exploration dispatch was attempted but rejected twice by wrapper schema validation; per lessons, review fell back to local diff inspection plus fresh verification.
- Implementation checkpoint: pending commit.
