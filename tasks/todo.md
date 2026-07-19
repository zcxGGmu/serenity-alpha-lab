# P1 ADR Approval Plan

> Started: 2026-07-20
> Scope: Complete `SAL-P1-001` only. Approve upstream takeover/sync policy and progressive modularization decisions before any Quant Core, PIT Dataset, formal backtesting, or broad DSA source migration.

## Checklist

- [x] Review `AGENTS.md`, `tasks/lessons.md`, development status, progress checklist, development plan, Gate G0 review, Git status, and recent commits.
- [x] Confirm current Phase/Gate at session start: P1 engineering hardening preparation; Gate G0 passed; `SAL-P1-001` is `READY`.
- [x] Write ADR-001 for upstream takeover, immutable tag policy, sync branches, patch classification, candidate commit triage, rollback, and review cadence.
- [x] Write ADR-002 for progressive modularization, Compatibility Facade, module boundaries, service-split conditions, old-path deletion criteria, rollback, and review cadence.
- [x] Update `docs/development-progress-checklist.md` for `SAL-P1-001`, including DONE status, actual effort, decision/evidence entries, risk updates, and next `READY` tasks.
- [x] Update `docs/development-status.md` for current Phase/Gate, completed/unfinished work, next executable tasks, latest checkpoint placeholder, and next-start prompt.
- [x] Add `SAL-P1-001` review notes here after verification.
- [x] Run lightweight ADR verification: required ADR sections, stale status scan, forbidden source migration check, link/path checks, `git diff --check`, and Git status review.
- [x] Stage only relevant `SAL-P1-001` files and create a Chinese checkpoint commit.

## Guardrails

- Do not move, delete, or reuse `upstream/dsa-v3.26.1`.
- Do not copy or merge DSA runtime source into the main working tree in this task.
- Do not start Quant Core, PIT Dataset, formal backtesting, Qlib integration, or large DSA source migration before these ADRs are approved.
- Do not submit `.worktrees`, `.cache`, `node_modules`, `static`, Playwright artifacts, pycache, or unrelated untracked directories.
- Keep accepted G0 risks visible; ADR approval does not make release security risks acceptable.

## Review: SAL-P1-001

- Added `docs/adr/ADR-001-upstream-takeover-sync-and-patch-policy.md`, approving the immutable DSA `v3.26.1` baseline, controlled `sync/dsa-*` branches, patch classification, sync rollback, and candidate commit triage.
- Added `docs/adr/ADR-002-progressive-modularization-and-compatibility-facade.md`, approving progressive modularization, explicit Compatibility Facade boundaries, service-split conditions, old-path deletion criteria, rollback, and Gate G1/2026-08-03 review timing.
- Updated `docs/development-progress-checklist.md`: `SAL-P1-001` is `DONE`, P1 progress is 1/16, total progress is 14/129, `SAL-P1-002` and `SAL-P1-004` are `READY`, `RSK-006` is closed by ADR triage, and `DEC-012` / `DEC-013` / `AEV-014` record decisions and evidence.
- Updated `docs/development-status.md`: current Gate is G1 not passed, latest completed task is `SAL-P1-001`, next executable tasks are `SAL-P1-002` and `SAL-P1-004`, and the next-start prompt reflects the new recovery point.
- Verification completed for `SAL-P1-001`: ADR required sections, immutable tag check, active status anchors, no runtime/cache path changes, and `git diff --check` all passed.

---

# P0 Remaining Gate Baseline Plan

> Started: 2026-07-19
> Scope: Continue P0 only. Complete `SAL-P0-010` first, then `SAL-P0-012`, then run `SAL-P0-013` Gate G0 review. Do not start P1, Quant Core, or broad DSA source migration before G0 passes.

## Checklist

- [x] Review `AGENTS.md`, project lessons, development status, progress checklist, development plan, upstream baseline selection, Git status, and recent commits.
- [x] Confirm current Phase/Gate at session start: P0, Gate G0 not passed; `SAL-P0-010` and `SAL-P0-012` are `READY`; `SAL-P0-013` remains gated by P0 completion.
- [x] Dispatch read-only subagents for report/signal baseline discovery, existing baseline-script pattern discovery, and upstream/CI discovery.
- [x] Run the Red check for `SAL-P0-010`: `scripts/run-dsa-report-signal-baseline.sh` is missing, so report/signal goldens are not yet reproducible.
- [x] Inspect DSA report rendering, report schema, notification report fixtures, DecisionSignal summary, and Backtest/Signal Evaluation metric paths in `.worktrees/dsa-v3.26.1`.
- [x] Add `scripts/run-dsa-report-signal-baseline.sh` using the established baseline pattern: validate tag/worktree, apply registered patches, validate worktree diff, run offline/stub generation, compare committed snapshots, and support `--update-snapshots`.
- [x] Commit stable `SAL-P0-010` snapshots under `docs/baselines/dsa-v3.26.1/report-signal/`, including structured report input/output, Markdown single-stock/aggregate/market-review goldens, signal evaluation input/output, content hashes, and `summary.json`.
- [x] Write `docs/report-signal-golden-baseline.md` with commands, fixture coverage, hashes, limitations, and non-goals.
- [x] Verify `SAL-P0-010`: baseline script update and compare runs, relevant upstream report/backtest tests, `bash -n`, `git diff --check`, committed-fixture guards, and summary assertions.
- [x] Update `docs/development-progress-checklist.md` for `SAL-P0-010`, P0 progress from 10/13 to 11/13, evidence registry, decisions, risks, and dependencies.
- [x] Update `docs/development-status.md` after `SAL-P0-010` with completed/unfinished tasks, next actions, latest checkpoint placeholders, and a fresh next-start prompt.
- [x] Add this task's review section to `tasks/todo.md`.
- [x] Stage only relevant `SAL-P0-010` files and create a Chinese checkpoint commit.
- [x] Start `SAL-P0-012`: create upstream maintenance documentation and CI required checks after the report/signal baseline exists.
- [x] Verify `SAL-P0-012`, update status/checklist/evidence, and create a Chinese checkpoint commit.
- [x] Start `SAL-P0-013` only after all P0 tasks are `DONE`; run Gate G0 review, record Go/No-Go, update status/checklist, and create a Chinese checkpoint commit.

## Guardrails

- Gate G0 is now passed by `SAL-P0-013`; keep the accepted risks visible and do not treat them as release approval.
- `SAL-P0-010` must use offline fixture/stub inputs only; no real Provider, real LLM, scheduler, webhook, or notification send.
- `SAL-P0-012` must include the actual P0 baseline scripts/artifacts and patch registry, not aspirational CI checks.
- `SAL-P1-001` is now complete; follow ADR-001/002 before starting dependent P1 code, and do not start Quant Core, PIT Dataset, formal backtesting, or broad DSA source migration outside the approved task sequence.
- The DSA source remains isolated in `.worktrees/dsa-v3.26.1`; do not copy upstream runtime source into the project tree.
- Do not submit `.cache`, `.worktrees`, runtime SQLite binaries, `node_modules`, `static`, Playwright artifacts, pycache, or unrelated untracked files.

## SAL-P0-012 Plan

- [x] Create root `UPSTREAM_BASE.md` covering upstream baseline, remote/tag policy, local worktree/cache layout, patch classification, baseline artifacts, sync procedure, and required check names.
- [x] Update `docs/upstream-patches.md` so each local deviation is explicitly classified as `compatible`, `extension`, or `divergence`.
- [x] Add `.github/workflows/p0-required-baselines.yml` with PR/workflow_dispatch required jobs for backend offline, Web build/test/smoke, contract/golden snapshots, Docker smoke, and supply-chain baseline.
- [x] Validate workflow YAML and referenced script paths without running heavyweight CI jobs locally.
- [x] Update `docs/development-progress-checklist.md` and `docs/development-status.md` for `SAL-P0-012`, moving P0 progress to 12/13 while keeping Gate G0 blocked until `SAL-P0-013`.
- [x] Add `SAL-P0-012` review notes here and create a Chinese checkpoint commit.

## SAL-P0-013 Plan

- [x] Confirm `SAL-P0-001` through `SAL-P0-012` are `DONE` and that no P0 evidence gaps remain.
- [x] Write `docs/gate-g0-baseline-review.md` with Gate G0 Go/No-Go decision, evidence matrix, accepted risks, and P1 entry constraints.
- [x] Update `docs/development-progress-checklist.md`: mark `SAL-P0-013` `DONE`, move P0 and total progress to `13/13` and `13/129`, and add `DEC-011` / `AEV-013`.
- [x] Update `docs/development-status.md` for Gate G0 passed, next executable task `SAL-P1-001`, accepted risks, and fresh resume prompt.
- [x] Run lightweight Gate G0 verification, update this review section, stage only G0 files, and create a Chinese checkpoint commit.

## Review: SAL-P0-013

- Created `docs/gate-g0-baseline-review.md` with the Gate G0 decision `GO with accepted risks`, evidence matrix, accepted risk register, and P1 entry constraints.
- Updated `docs/development-progress-checklist.md`: P0 is `DONE` at 13/13, total progress is 13/129, `SAL-P0-013` is `DONE`, `SAL-P1-001` is `READY`, and `DEC-011` / `AEV-013` record the Gate decision and evidence.
- Updated `docs/development-status.md`: current phase moves to P1 engineering hardening preparation, Gate G0 is passed, next task is `SAL-P1-001`, and the next-start prompt reflects the new recovery state.
- Accepted but did not fix G0 risks `RSK-006`, `RSK-008`, `RSK-010`, `RSK-011`, and `RSK-012`; these remain assigned to P1/P6 closure paths and do not permit release until closed or formally waived.
- Verification scope for `SAL-P0-013`: locked baseline validation, patch registry check, workflow YAML parse, API/config/database/report-signal summary assertions, stale-status scan, and `git diff --check`.

## Review: SAL-P0-012

- Added `UPSTREAM_BASE.md`, documenting the immutable DSA `v3.26.1` baseline, origin/upstream remotes, isolated worktree/cache layout, sync procedure, local deviation taxonomy, baseline scripts, and required check names.
- Updated `docs/upstream-patches.md` so `DSA-PATCH-001` through `DSA-PATCH-003` are explicitly classified as `compatible`; current P0 has no `divergence`.
- Added `.github/workflows/p0-required-baselines.yml` with four PR/workflow_dispatch check jobs: backend offline, Web baseline, contract/golden snapshots, and Docker/supply-chain baseline.
- Updated `docs/development-progress-checklist.md`: `SAL-P0-012` is `DONE`, P0 is 12/13, total progress is 12/129, `SAL-P0-013` is now `READY`, and `AEV-012` / `DEC-010` document evidence and CI strategy.
- Updated `docs/development-status.md`: current task is now `SAL-P0-013`; Gate G0 remains not passed and P1/Quant Core remain blocked.
- Verification completed for `SAL-P0-012`: workflow YAML parsed, referenced scripts exist, baseline scripts pass `bash -n`, required check names and patch classifications are present, and `git diff --check` passed.

## Review: SAL-P0-010

- Added `scripts/run-dsa-report-signal-baseline.sh`, which validates the locked DSA baseline tag/worktree, applies registered P0 patches, enforces registered worktree diff boundaries, generates offline report/signal fixtures, and compares committed snapshots by default.
- Added stable report/signal baseline artifacts under `docs/baselines/dsa-v3.26.1/report-signal/`: fixed inputs, Stub LLM responses, structured reports, single-stock/aggregate/market-review Markdown, Signal Evaluation details/summary, DecisionSignal summary, content hashes, and `summary.json`.
- Wrote `docs/report-signal-golden-baseline.md` with coverage, hash inventory, CI usage, verification commands, non-goals, and the decision to use offline Stub LLM/Provider-free inputs only.
- Updated `docs/development-progress-checklist.md`: `SAL-P0-010` is `DONE`, P0 is 11/13, total progress is 11/129, and `AEV-011` / `DEC-009` document evidence and artifact strategy.
- Updated `docs/development-status.md`: current task is now `SAL-P0-012`; Gate G0 remains not passed; `SAL-P0-013` remains gated by P0 completion.
- Verification completed for `SAL-P0-010`: baseline script generation and compare runs, `bash -n`, targeted upstream report/backtest tests `137 passed`, `git diff --check`, stale-progress scans, committed-fixture guard, secret/local-path scans, and `summary.json` assertions.

## Previous Review: SAL-P0-009

- Added `scripts/run-dsa-database-baseline.sh`, which validates the locked DSA baseline tag/worktree, applies registered P0 patches, creates a sanitized SQLite fixture, dumps schema/index metadata, and compares committed SQL/JSON snapshots.
- Added stable database baseline artifacts under `docs/baselines/dsa-v3.26.1/database/`: `schema.sql`, `schema-metadata.json`, `fixture.sql`, `fixture-summary.json`, `content-hashes.json`, and `summary.json`.
- Wrote `docs/database-schema-baseline.md` with fixture coverage, hashes, verification commands, limitations, and the decision not to commit runtime `fixture.sqlite`.
- Updated `docs/development-progress-checklist.md`: `SAL-P0-009` is `DONE`, P0 is 10/13, total progress is 10/129, and `AEV-010` / `DEC-008` document evidence and artifact strategy.
- Verification completed for `SAL-P0-009`: baseline script generation and compare runs, `bash -n`, `git diff --check`, stale-progress scans, committed-fixture guard, and `summary.json` assertions.
