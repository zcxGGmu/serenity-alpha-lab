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
- [ ] Start `SAL-P0-013` only after all P0 tasks are `DONE`; run Gate G0 review, record Go/No-Go, update status/checklist, and create a Chinese checkpoint commit.

## Guardrails

- Gate G0 remains not passed until `SAL-P0-013` is completed and verified.
- `SAL-P0-010` must use offline fixture/stub inputs only; no real Provider, real LLM, scheduler, webhook, or notification send.
- `SAL-P0-012` must include the actual P0 baseline scripts/artifacts and patch registry, not aspirational CI checks.
- `SAL-P0-013` cannot be marked complete until `SAL-P0-010` and `SAL-P0-012` are complete.
- The DSA source remains isolated in `.worktrees/dsa-v3.26.1`; do not copy upstream runtime source into the project tree.
- Do not submit `.cache`, `.worktrees`, runtime SQLite binaries, `node_modules`, `static`, Playwright artifacts, pycache, or unrelated untracked files.

## SAL-P0-012 Plan

- [x] Create root `UPSTREAM_BASE.md` covering upstream baseline, remote/tag policy, local worktree/cache layout, patch classification, baseline artifacts, sync procedure, and required check names.
- [x] Update `docs/upstream-patches.md` so each local deviation is explicitly classified as `compatible`, `extension`, or `divergence`.
- [x] Add `.github/workflows/p0-required-baselines.yml` with PR/workflow_dispatch required jobs for backend offline, Web build/test/smoke, contract/golden snapshots, Docker smoke, and supply-chain baseline.
- [x] Validate workflow YAML and referenced script paths without running heavyweight CI jobs locally.
- [x] Update `docs/development-progress-checklist.md` and `docs/development-status.md` for `SAL-P0-012`, moving P0 progress to 12/13 while keeping Gate G0 blocked until `SAL-P0-013`.
- [x] Add `SAL-P0-012` review notes here and create a Chinese checkpoint commit.

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
