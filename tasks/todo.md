# P0 Database Schema Baseline Plan

> Started: 2026-07-19
> Scope: Complete `SAL-P0-009` only: freeze the locked DSA SQLite schema and create a sanitized migration fixture. Do not start P1, Quant Core, or broad DSA source migration.

## Checklist

- [x] Review `AGENTS.md`, project lessons, development status, progress checklist, development plan, upstream baseline selection, Git status, and recent commits.
- [x] Confirm current Phase/Gate at session start: P0, Gate G0 not passed; `SAL-P0-009`, `SAL-P0-010`, and `SAL-P0-012` were READY.
- [x] Inspect DSA SQLite model/DDL creation paths in `.worktrees/dsa-v3.26.1` and identify required fixture coverage.
- [x] Add a reproducible script that materializes the locked DSA worktree, applies registered P0 patches, creates a sanitized SQLite fixture, dumps schema/index metadata, and writes content hashes.
- [x] Commit only stable baseline artifacts under `docs/baselines/dsa-v3.26.1/database/`, excluding `.cache`, `.worktrees`, generated runtime DBs, `node_modules`, `static`, pycache, and Playwright artifacts.
- [x] Write `docs/database-schema-baseline.md` with commands, environment, fixture coverage, schema summary, hashes, limitations, and non-goals.
- [x] Update `docs/development-progress-checklist.md` for `SAL-P0-009`, evidence registry, decisions/risks if needed, and P0 progress from 9/13 to 10/13 only after verification passes.
- [x] Update `docs/development-status.md` with completed/unfinished tasks, next actions, latest checkpoint placeholders, and a fresh next-start prompt.
- [x] Add this task's review section to `tasks/todo.md`.
- [x] Run verification: schema baseline script, fixture integrity checks, `git diff --check`, and targeted consistency scans.
- [x] Stage only relevant files and create a Chinese checkpoint commit for `SAL-P0-009`.

## Guardrails

- Gate G0 remains not passed until `SAL-P0-013`.
- `SAL-P0-010`, `SAL-P0-012`, and `SAL-P0-013` remain incomplete unless separately implemented and verified.
- The DSA source remains isolated in `.worktrees/dsa-v3.26.1`; do not copy upstream runtime source into the project tree.
- The sanitized SQLite fixture must not contain secrets, cookies, personal data, real tokens, or local machine paths.
- Prefer runtime-introspected schema and deterministic JSON artifacts over hand-authored table lists.

## Review

- Added `scripts/run-dsa-database-baseline.sh`, which validates the locked DSA baseline tag/worktree, applies registered P0 patches, creates a sanitized SQLite fixture, dumps schema/index metadata, and compares committed SQL/JSON snapshots.
- Added review hardening in the baseline script: repository-relative path guards for destructive/copy destinations, DSA worktree dirty-state validation against registered patch paths and known generated caches, deterministic SQL trailing-whitespace normalization, and `fixture.sql` restore round-trip validation with `PRAGMA foreign_key_check`, row-count comparison, and per-table content hash comparison.
- Added stable database baseline artifacts under `docs/baselines/dsa-v3.26.1/database/`: `schema.sql`, `schema-metadata.json`, `fixture.sql`, `fixture-summary.json`, `content-hashes.json`, and `summary.json`.
- Wrote `docs/database-schema-baseline.md` with fixture coverage, hashes, verification commands, limitations, and the decision not to commit runtime `fixture.sqlite` because identical content can still produce unstable SQLite binary bytes.
- Updated `docs/development-progress-checklist.md`: `SAL-P0-009` is `DONE`, P0 is 10/13, total progress is 10/129, and `AEV-010` / `DEC-008` document evidence and artifact strategy.
- Updated `docs/development-status.md`: current tasks are now `SAL-P0-010` and `SAL-P0-012`; Gate G0 remains not passed; `SAL-P0-013` remains TODO.
- Verification completed: target command first failed before script creation; `scripts/run-dsa-database-baseline.sh --update-snapshots` generated snapshots; multiple `scripts/run-dsa-database-baseline.sh` runs matched committed snapshots; `bash -n scripts/run-dsa-database-baseline.sh`, `git diff --check`, stale-progress scans, committed-fixture guard, and `summary.json` assertions passed.
- Final checkpoint scope is limited to `SAL-P0-009` files: database baseline script, database baseline evidence/snapshots, development status/checklist, and `tasks/todo.md`.
