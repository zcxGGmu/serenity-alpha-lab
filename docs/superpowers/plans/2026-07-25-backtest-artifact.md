# BacktestArtifact Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Define the formal `BacktestArtifact` output contract for SAL-P4-004 without running a portfolio backtest.

**Architecture:** Add immutable output DTOs under `quant.backtest` that standardize large-result artifacts for orders, executions, positions, cash, equity, metrics and audit records. The contract binds each output to a `BacktestSpec.spec_hash`, content-addressed artifact manifests and explicit `preview` / `formal` / `partial` / `invalid` states so APIs can pass URIs instead of embedding full DataFrames.

**Tech Stack:** Python dataclasses, `StrEnum`, canonical JSON, existing `ArtifactManifest` / `ArtifactStore`, pytest, BacktestSpec contract fixtures.

---

### Task 1: Red Contract Tests

**Files:**
- Create: `tests/quant/test_backtest_artifact.py`

- [ ] **Step 1: Write failing test for bundle surfaces**

Test that a `BacktestArtifactBundle` records `orders`, `executions`, `positions`, `cash`, `equity_curve`, `metrics` and `audit` outputs; each output exposes schema name/version, row count, content hash, `artifact://sha256/*` URI and `ArtifactManifest`; `to_record()` is JSON serializable and contains `spec_hash` but no embedded rows.

- [ ] **Step 2: Write failing test for deterministic summary Artifact publication**

Test `publish_backtest_artifact_bundle()` writes only the compact bundle summary to `ArtifactStore`, produces deterministic bytes, and does not inline large table payloads.

- [ ] **Step 3: Write failing validation test**

Test the contract rejects `latest`, missing required output kinds, invalid `preview/formal/partial/invalid` states, mismatched manifest/content hash, negative row counts and `legacy_signal_evaluation` engine scope.

- [ ] **Step 4: Run Red test**

Run: `.venv/bin/python -m pytest tests/quant/test_backtest_artifact.py -q`
Expected: fail with missing `serenity_alpha_lab.quant.backtest.artifacts`.

### Task 2: BacktestArtifact Contract

**Files:**
- Create: `src/serenity_alpha_lab/quant/backtest/artifacts.py`
- Modify: `src/serenity_alpha_lab/quant/backtest/__init__.py`

- [ ] **Step 1: Define constants and enums**

Add `BACKTEST_ARTIFACT_CONTRACT_VERSION`, bundle schema/content-type constants, `BacktestArtifactKind` and `BacktestArtifactState`.

- [ ] **Step 2: Implement immutable output descriptors**

Add `BacktestOutputArtifact` with kind, schema name/version, artifact manifest, row count, content hash, optional partition keys and `to_record()`.

- [ ] **Step 3: Implement artifact bundle**

Add `BacktestArtifactBundle` binding run/spec/engine/version metadata, required output kinds, status, created timestamp, warnings/errors, and `to_json_bytes()` / `publish()` helpers.

- [ ] **Step 4: Add helpers and exports**

Add `publish_backtest_artifact_bundle()` and export all public symbols from `quant.backtest.__init__`.

### Task 3: Documentation And Status

**Files:**
- Create: `docs/backtest-artifact.md`
- Modify: `docs/development-progress-checklist.md`
- Modify: `docs/development-status.md`
- Modify: `tasks/todo.md`

- [ ] **Step 1: Document artifact schemas and states**

Document required output schemas, URI-only large outputs, `preview/formal/partial/invalid`, non-goals and compatibility boundary.

- [ ] **Step 2: Update progress and recovery docs**

Mark `SAL-P4-004` done only after verification; set P4 `4/22`, total `70/129`, and move `SAL-P4-005` to READY.

- [ ] **Step 3: Add review evidence**

Append `DEC-068` and `AEV-070` with Red/Green evidence and no-go boundary confirmation.

### Task 4: Verification And Checkpoint

**Files:**
- No new files beyond Task 1-3

- [ ] **Step 1: Run focused tests**

Run: `.venv/bin/python -m pytest tests/quant/test_backtest_artifact.py -q`
Expected: pass.

- [ ] **Step 2: Run related suites**

Run: `.venv/bin/python -m pytest tests/quant/test_backtest_artifact.py tests/quant/test_backtest_spec.py tests/architecture/test_dsa_signal_evaluation_engine_migration.py tests/architecture/test_dsa_signal_evaluation_characterization.py -q`
Expected: pass.

- [ ] **Step 3: Run final guards**

Run full pytest, compileall, dependency lock guard, DSA patch check, immutable tag check, status-anchor scan and `git diff --check`.

- [ ] **Step 4: Commit**

Create a Chinese checkpoint commit for `SAL-P4-004`, then create a follow-up status-sync checkpoint if the implementation commit needs actual hash anchors.
