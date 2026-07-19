# SAL-P0-006 Desktop/CLI/Bot Smoke Plan

> Started: 2026-07-19
> Scope: Continue P0 only. Gate G0 is not passed, so this task must not start P1, Quant Core, or broad DSA refactoring.

## Checklist

- [x] Confirm actual Git/worktree state and restore DSA baseline refs only if needed.
- [x] Materialize or validate `.worktrees/dsa-v3.26.1` at `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`.
- [x] Inspect DSA Desktop, CLI, and Bot entrypoints without modifying upstream source.
- [x] Run or classify Desktop smoke path using locked baseline and local cache.
- [x] Run or classify CLI smoke path using offline/stub-safe inputs.
- [x] Run or classify at least one Bot command smoke path using offline/stub-safe inputs.
- [x] Record commands, environment, pass/fail/blocked status, and evidence in a new P0 evidence document.
- [x] Update `docs/development-progress-checklist.md` for `SAL-P0-006`.
- [x] Update `docs/development-status.md` with current task result and next recovery prompt.
- [x] Verify documentation consistency and Git status.
- [x] Create a Chinese checkpoint commit if the result is reviewable.

## Guardrails

- Do not mark `SAL-P0-006` as `DONE` unless Desktop, CLI, and Bot smoke acceptance criteria are actually satisfied.
- Do not mark `SAL-P0-004`, `SAL-P0-005`, or `SAL-P0-011` complete.
- Do not commit generated dependency/build/cache files such as `node_modules`, `dist`, `.pyc`, `.cache`, or `.worktrees`.
- If a smoke depends on AlphaSift Git access, missing secrets, Docker daemon, or unavailable OS GUI, classify it as `BLOCKED` with concrete evidence.

## Review

- Result: `SAL-P0-006` is documented as `DONE` with Desktop, CLI, API health, and Bot offline smoke evidence.
- Validation: fresh P0-006 smoke rerun passed: Desktop `npm test` 47/47 and combined pytest 121/121, followed by `git diff --check`.
- Follow-up: Gate G0 remains open; next executable task is `SAL-P0-007` Docker baseline, with `SAL-P0-004` backend gate/offline-tests available for separate rerun.
