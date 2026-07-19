# SAL-P0-004 Backend Offline Gate Plan

> Started: 2026-07-19
> Scope: Continue P0 only. Gate G0 is not passed, so this task must not start P1, Quant Core, or broad DSA refactoring.

## Checklist

- [x] Review project lessons, current P0 status, and SAL-P0-004 acceptance criteria.
- [x] Confirm locked DSA worktree and reusable Python 3.11 CI environment.
- [x] Run backend syntax gate via `scripts/ci_gate.sh syntax`.
- [x] Run flake8 critical gate via `scripts/ci_gate.sh flake8`.
- [x] Run deterministic local checks via `scripts/ci_gate.sh deterministic`.
- [x] Run offline pytest suite via `scripts/ci_gate.sh offline-tests`.
- [x] Record test counts, duration, pass/fail classification, and artifacts.
- [x] Update P0 checklist/status/evidence truthfully.
- [x] Verify Git status and prepare a Chinese checkpoint commit if reviewable.

## Guardrails

- Do not modify DSA upstream source unless a backend gate failure exposes a concrete script/config defect and the root cause is verified.
- Do not mark `SAL-P0-004` as `DONE` unless syntax, flake8, deterministic, and offline pytest gates all pass or failures are correctly classified as upstream/environment blockers.
- Do not mark `SAL-P0-005`, `SAL-P0-011`, or Gate G0 complete.
- Do not stage generated DSA source mirrors, pytest caches, `.cache`, `.worktrees`, `.pyc`, or test artifacts.

## Review

- Added registered local upstream patch `DSA-PATCH-001` after reproducing the backend offline failure as mutable proxy-default pollution in `IntelligenceService`.
- Added `scripts/apply-dsa-baseline-patches.sh` and wired `scripts/run-dsa-backend-offline-baseline.sh` to apply patches before running gate phases.
- Verified red/green: new regression failed before the fix, then passed after the one-line `dict(_DISABLE_REQUEST_PROXIES)` fix.
- Full backend gate passed: syntax 0s, flake8 4s, deterministic 3s, collect 8s, offline-tests 145s.
- Final offline pytest count: `4455 passed, 4 deselected, 48 warnings, 416 subtests passed in 142.10s`.
- `SAL-P0-004` is DONE; Gate G0 remains open because `SAL-P0-005`, `SAL-P0-011`, and downstream P0 baselines are still incomplete.
