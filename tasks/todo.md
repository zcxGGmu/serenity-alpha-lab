# SAL-P4-022 Gate G4 Backtest And Risk Review Plan

> Scope: Complete `SAL-P4-022` by adding Gate G4 review evidence for the P4 formal backtest, deterministic risk, audit, metrics, API and Quant Lab chain. This task may approve P4 artifacts as inputs to P5 evidence modeling, but it must not start Evidence Agent, real Provider/LLM calls, Worker loop, Qlib runtime or production promotion.

## Checklist

- [x] Re-read `AGENTS.md`, `tasks/lessons.md`, current status/checklist, development plan, Gate G0/G2/G3 records, P3/P4 evidence docs, ADR-009, current Git status and recent commits.
- [x] Confirm current branch and checkpoints: `codex/p0-baseline-status` is clean, ahead of origin, and latest log starts with `e2e6ef9d`, `8f3cfb79`, `6e8bb74a`, `52830c20`, `70303f8f`, `643b4452`.
- [x] Write implementation plan at `docs/superpowers/plans/2026-07-26-gate-g4-backtest-risk-review.md`.
- [x] Red: add `tests/gates/test_gate_g4_backtest_risk_review.py` that fails while `docs/gate-g4-backtest-risk-review.md` is missing.
- [x] Green: add `docs/gate-g4-backtest-risk-review.md` with Gate conclusion, P4 task matrix, accepted risks, validation evidence and P5 entrance constraints.
- [x] Update `docs/development-progress-checklist.md` with `SAL-P4-022` done, P4 `22/22`, total `88/129`, `AEV-088`, `DEC-086` and P5 next-step status.
- [x] Update `docs/development-status.md` with Gate G4 passed, latest task/checkpoint placeholders, completion range and next startup prompt for `SAL-P5-001`.
- [x] Run focused Gate G4 test, related P4 suite, full pytest, compileall, dependency lock guard, DSA patch/tag checks and `git diff --check`.
- [x] Review changes, record subagent fallback, stage only `SAL-P4-022` files and create required Chinese checkpoint commit.

## Scope Guard

- Gate G4 may approve formal backtest/risk evidence as structured inputs for P5 evidence schema and later Quant Evidence Adapter work.
- Gate G4 must keep Signal Evaluation, Factor Evaluation and Portfolio Backtest as separate evaluation semantics.
- Legacy `/api/v1/backtest/*` remains Signal Evaluation; `/api/v1/quant/backtest-runs` remains the formal portfolio backtest API contract.
- Qlib internal evidence, Dataset conversion artifacts, Screen results, AlphaSift T+N evaluation and legacy Signal Evaluation must not be presented as formal portfolio backtest output.
- Real Provider/LLM calls, full Worker loop, Evidence Agent execution, production release and live portfolio promotion remain out of scope.

## Review Notes

- Started 2026-07-26 from a clean working tree after `SAL-P4-021` final handoff anchors.
- Subagent dispatch attempted and rejected by host wrapper optional-field validation; per `tasks/lessons.md`, fallback is local senior review plus fresh verification.
- Red Gate G4 target: `1 failed, 1 passed`, missing `docs/gate-g4-backtest-risk-review.md`.
- Green focused target: `2 passed in 0.53s`.
- Related P4 suite: `37 passed in 0.50s`.
- Full pytest: `404 passed, 3 skipped in 2.89s`.
- Compileall PASS; dependency lock guard PASS (`Resolved 298 packages`); immutable tag stayed `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`; `git diff --check` PASS.
- Live DSA worktree `--check-only` hit the documented already-applied patch context limitation at `0004-add-screen-lab.patch`; clean temporary worktree replay applied `0001` through `0006` successfully.
