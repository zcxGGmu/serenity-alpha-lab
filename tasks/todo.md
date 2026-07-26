# SAL-P4-021 Quant Lab Plan

> Scope: Complete `SAL-P4-021` by adding a DSA Web extension patch for Quant Lab on top of the framework-neutral `/api/v1/quant/backtest-runs` contract. Build run creation, progress/status, equity/drawdown, orders/trades, positions, audit and artifact download surfaces. Do not start Evidence Agent, real Provider/LLM calls, Qlib runtime, a Worker loop or Gate G4 promotion.

## Checklist

- [x] Re-read `AGENTS.md`, `tasks/lessons.md`, current status/checklist, development plan, Gate/evidence docs, backtest API/resource/orchestration docs, Screen Lab precedent, ADR-009, current Git status and recent commits.
- [x] Confirm current branch and checkpoints: `codex/p0-baseline-status` is clean and ahead of origin; latest log starts with `750a9388`, `d4ce97d9`, `9c308f2e`, `64346b83`, `c1bb1dcc`.
- [x] Write implementation plan at `docs/superpowers/plans/2026-07-26-quant-lab.md`.
- [x] Red: add DSA Web tests for `quantBacktestApi`, `QuantLabPage`, `/quant-lab` routing and sidebar/i18n registration.
- [x] Green: implement `src/api/quantBacktest.ts` with `/api/v1/quant/backtest-runs` create/status/metrics/orders/positions/audit/artifact/cancel client functions.
- [x] Green: implement `src/pages/QuantLabPage.tsx` with parameter summary, Preview/Formal run creation, compact progress/runtime flags, result tabs, raw tables and artifact download controls.
- [x] Green: wire `QuantLabPage` into `App.tsx`, `SidebarNav.tsx`, route labels and related tests without renaming legacy `/backtest` Signal Evaluation.
- [x] Generate `patches/dsa/v3.26.1/0006-add-quant-lab.patch` and update `docs/upstream-patches.md` with DSA-PATCH-006.
- [x] Add `docs/quant-lab.md` with UI contract, API lineage, non-goals and verification evidence.
- [x] Update progress checklist/status docs with `SAL-P4-021` done, P4 `21/22`, total `87/129`, decision/evidence rows and `SAL-P4-022` READY.
- [x] Run focused web tests, lint/build, Python related checks, compile/lock/patch/tag/diff checks.
- [x] Review, stage only `SAL-P4-021` files and create required Chinese checkpoint commit.

## Scope Guard

- Quant Lab uses `/api/v1/quant/backtest-runs`; legacy `/api/v1/backtest/*` remains Signal Evaluation and keeps the sidebar label “信号评价”.
- Preview/Formal and valid/invalid/ranking eligibility states must be visually distinct and never imply Gate G4 has passed.
- Create/status responses remain compact; large rows are loaded through orders/positions pagination and artifact payload endpoints.
- Every chart/table must surface dataset versions, schema, trace/run/stage and artifact IDs/hashes where available.
- Qlib internal evidence, Dataset conversion artifacts, Screen results, AlphaSift T+N evaluation and legacy Signal Evaluation must not be presented as formal portfolio backtest results.

## Review Notes

- Started 2026-07-26 from clean working tree after `SAL-P4-020`; no user corrections recorded so `tasks/lessons.md` remains unchanged for now.
- Completed Quant Lab implementation as `DSA-PATCH-006` against the DSA Web extension surface; root source remains authoritative for formal API contracts.
- Fresh green evidence: focused web `4 passed files / 27 passed tests`, web lint PASS, web build PASS, related Python suite `34 passed`, compileall PASS, dependency lock guard PASS, clean temp DSA worktree sequential patch apply `0001..0006` PASS, tag/diff checks PASS.
- Default live-worktree `--check-only` was not treated as the patch-chain proof after 0006 because reverse-checking `DSA-PATCH-004` against a final worktree that also contains `DSA-PATCH-006` can fail on shared App/Sidebar/i18n context; clean sequential apply is the replay proof recorded in `docs/quant-lab.md`.
- Subagent attempt failed once due host wrapper optional-field validation (`reasoning_effort must not be empty`); per `tasks/lessons.md`, fallback was local senior review plus fresh verification.
- No user correction occurred in this turn, so `tasks/lessons.md` was not changed.
- Implementation checkpoint created: `643b4452 feat(P4): 实现 Quant Lab`; status sync commit will record this hash.
- Status sync checkpoint created: `70303f8f docs: 同步 SAL-P4-021 checkpoint hash`; this hash-anchor update records it.
- Hash-anchor checkpoint created: `52830c20 docs: 记录 SAL-P4-021 状态同步 hash`; final status review commit will be reported in the handoff.
- Final status review checkpoint created: `6e8bb74a docs: 复核 SAL-P4-021 最新开发状态与恢复提示`; this final hash record commit closes the handoff state.
- Post-handoff user reminder recorded: status docs/checklist remain at `SAL-P4-022` READY with P4 `21/22` and total `87/129`; `tasks/lessons.md` now adds an explicit rule to perform status/checklist/evidence/risk/decision/todo review/lessons/next-prompt sync automatically after each phase task.
