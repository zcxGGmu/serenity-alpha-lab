# P0 API And Config Contract Baseline Plan

> Started: 2026-07-19
> Scope: Complete `SAL-P0-008` without starting P1, Quant Core, or large DSA source migration.

## Checklist

- [x] Review `AGENTS.md`, project lessons, development status, progress checklist, development plan, upstream baseline selection, Git status, and recent commits.
- [x] Confirm current branch and untracked generated directories before editing.
- [x] Inspect locked DSA baseline API/config sources in `.worktrees/dsa-v3.26.1`.
- [x] Add a reproducible contract baseline script that applies registered DSA patches, verifies the locked upstream SHA, exports OpenAPI, inventories environment/config fields, and compares committed snapshots.
- [x] Commit OpenAPI and config inventory snapshots under a stable docs baseline path.
- [x] Add `SAL-P0-008` evidence documentation covering artifacts, field classes, verification commands, limitations, and CI usage.
- [x] Update `docs/development-progress-checklist.md` with `SAL-P0-008` result and evidence while leaving unfinished P0 tasks incomplete.
- [x] Update `docs/development-status.md` with current progress, remaining blockers, latest checkpoint placeholder, and next-session prompt.
- [x] Add this task's review notes at the end of this file.
- [x] Run fresh verification commands and inspect outputs.
- [x] Stage only relevant tracked/new baseline files and create a Chinese checkpoint commit.

## Guardrails

- Do not mark Gate G0 complete.
- Do not begin `SAL-P0-009`, `SAL-P0-010`, `SAL-P0-012`, P1, Quant Core, or broad DSA migration in this checkpoint.
- Do not stage `.worktrees`, `.cache`, `node_modules`, generated `static`, Playwright artifacts, pycache, or unrelated untracked directories.
- Do not move `upstream/dsa-v3.26.1`; the expected SHA remains `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`.
- Treat committed snapshots as CI-facing contracts; generated runtime artifacts stay under `.cache/dsa-p0`.

## Review

- Added `scripts/run-dsa-api-config-baseline.sh` as the reproducible SAL-P0-008 gate. It validates the locked DSA tag/worktree SHA, applies registered baseline patches, generates OpenAPI/config snapshots from an empty env, and compares them with committed snapshots by default.
- Added committed contract snapshots under `docs/baselines/dsa-v3.26.1/api-config/`: runtime OpenAPI, config schema, config/env inventory, and summary hashes.
- Added `docs/api-config-contract-baseline.md` with evidence, field classification rules, server-masked fields, limitations, and CI usage. The record explicitly uses runtime FastAPI OpenAPI as the authority because upstream `docs/architecture/api_spec.json` is stale.
- Updated `docs/development-progress-checklist.md` and `docs/development-status.md`: `SAL-P0-008` is `DONE`, P0 progress is `9/13`, total progress is `9/129`, and next tasks remain `SAL-P0-009`, `SAL-P0-010`, `SAL-P0-012`, then `SAL-P0-013`.
- Updated `.gitignore` to keep pycache, Playwright artifacts, generated static assets, and other local output out of status/staging.
- Verification: `bash -n scripts/run-dsa-api-config-baseline.sh` passed; `scripts/run-dsa-api-config-baseline.sh` passed with all four snapshots matched; `jq` checks confirmed OpenAPI 105 paths / 119 operations / 186 schemas, config schema 179 fields, config inventory 386 fields, secret 81, server_masked 5; narrow leakage scan found no local absolute paths, smoke password, or temporary artifact path in committed snapshots; `git diff --check` passed.
