# Gate G3 Screen Factor Review Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete `SAL-P3-017` by approving or blocking P3 Screen/Factor outputs as P4 backtest inputs.

**Architecture:** Add a Gate G3 review document and executable gate test that reuses the existing P3 contracts instead of adding new runtime behavior. The gate must prove AlphaSift intake, factor definitions/evaluation, ScreenDefinition Pipeline, ScreenSnapshot, Quant Screening API, Screen Lab, performance/reproducibility, Dataset Manifest, ProblemDetails, Trace, Artifact, and Run/Stage/Event boundaries are all represented before P4 opens.

**Tech Stack:** Python 3.11, pytest, Serenity domain/application/quant contracts, local ArtifactStore, project markdown evidence.

---

### Task 1: Gate G3 Contract Test

**Files:**
- Create: `tests/gates/test_gate_g3_screen_factor_review.py`

- [x] **Step 1: Write failing gate test**

Create a test that checks `docs/gate-g3-screen-factor-review.md` exists and contains `GO with accepted risks`, `SAL-P3-001` through `SAL-P3-016`, `APPROVED FOR P4`, and the strict no-go phrases for Quant Core, formal backtest, Evidence Agent, real Provider/LLM, Worker loop, and DSA runtime migration boundaries.

- [x] **Step 2: Add executable contract assertions**

In the same test file, build a synthetic offline factor/screen flow using existing P3 DTOs: base factor catalog count, Factor Evaluation report, ScreenDefinition Pipeline, ScreenSnapshot, Quant Screening API idempotent task submission, ProblemDetails validation mapping, Screen performance report, and deterministic Artifact publication.

- [x] **Step 3: Run red test**

Run: `.venv/bin/python -m pytest tests/gates/test_gate_g3_screen_factor_review.py -q`
Expected: fail because `docs/gate-g3-screen-factor-review.md` does not exist.

### Task 2: Gate G3 Review Evidence

**Files:**
- Create: `docs/gate-g3-screen-factor-review.md`
- Modify: `docs/development-progress-checklist.md`

- [x] **Step 1: Write gate review document**

Document the Gate G3 conclusion, pass/fail checklist, P3 task evidence matrix, accepted risks, P4 entry constraints, local verification commands, and final approval scope.

- [x] **Step 2: Update progress ledger**

Mark `SAL-P3-017` as `DONE`, update P3 to `17/17`, total to `66/129`, set P4 state to `READY`, add `DEC-064` and `AEV-066`, and keep P4 entries untouched except for the next task readiness.

- [x] **Step 3: Run gate test green**

Run: `.venv/bin/python -m pytest tests/gates/test_gate_g3_screen_factor_review.py -q`
Expected: pass.

### Task 3: State Sync And Checkpoint

**Files:**
- Modify: `docs/development-status.md`
- Modify: `tasks/todo.md`

- [x] **Step 1: Update recovery status**

Set current Phase to P4, Gate G3 passed with accepted risks, completed range through `SAL-P3-017`, current READY task `SAL-P4-001`, and preserve no-go constraints for Quant Core/formal backtest/Evidence Agent until their P4/P5 tasks explicitly start.

- [x] **Step 2: Run full verification**

Run target gate test, related P3 gate suite, full pytest, compileall, dependency lock guard, DSA patch check, immutable tag check, status-anchor scan, and `git diff --check`.

- [x] **Step 3: Commit checkpoint**

Stage only `SAL-P3-017` files and create a Chinese checkpoint commit with verification evidence and accepted risks.
