# Factor Evaluation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `SAL-P3-009` Factor Evaluation so platform factor values can be evaluated offline with deterministic coverage, IC/ICIR, group return, monotonicity, turnover, exposure and artifact outputs.

**Architecture:** Add a pure `quant.factors.evaluation` module that consumes already-produced factor/forward-return observations and a versioned evaluation spec. The evaluator performs PIT and sample-overlap guards, computes JSON-friendly report DTOs, and publishes deterministic report JSON through the existing `ArtifactStore`. It does not compute factor values, call Qlib, run portfolio backtests or start screen workflows.

**Tech Stack:** Python dataclasses/enums, NumPy for deterministic numeric operations, existing `DatasetVersionRef`, `InstrumentId`, `ArtifactStore`, `LocalArtifactStore`, and pytest.

---

### Task 1: Contract Tests

**Files:**
- Create: `tests/quant/test_factor_evaluation.py`
- Create: `docs/superpowers/plans/2026-07-24-factor-evaluation.md`
- Modify: `tasks/todo.md`

- [x] **Step 1: Add Red contract tests**

Cover:
- `FactorEvaluationSpec` with concrete `dsv_*` guards and versioned `FutureReturnWindow`
- PIT rejection when `factor_available_at > decision_time`
- coverage and overlap counts
- per-date Spearman IC, IC summary and ICIR annualization
- quantile group returns and monotonicity
- top-quantile turnover
- exposure mean and factor correlation
- deterministic JSON artifact publication

- [x] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/quant/test_factor_evaluation.py -q`

Expected Red: collection fails with missing `serenity_alpha_lab.quant.factors.evaluation`.

### Task 2: Evaluation Module

**Files:**
- Create: `src/serenity_alpha_lab/quant/factors/evaluation.py`
- Modify: `src/serenity_alpha_lab/quant/factors/__init__.py`
- Test: `tests/quant/test_factor_evaluation.py`

- [x] **Step 1: Implement minimal evaluator**

Implement immutable DTOs:
- `FutureReturnWindow`
- `FactorEvaluationSpec`
- `FactorEvaluationObservation`
- `FactorCoverageSummary`
- `FactorIcMetric` / `FactorIcSummary`
- `FactorGroupReturnBucket` / `FactorGroupReturnSummary`
- `FactorMonotonicityMetric`
- `FactorTurnoverMetric` / `FactorTurnoverSummary`
- `FactorExposureMetric` / `FactorExposureSummary`
- `FactorEvaluationReport`

Implement functions:
- `evaluate_factor()`
- `publish_factor_evaluation_report()`

- [x] **Step 2: Export public symbols**

Add Factor Evaluation constants, DTOs and functions to `serenity_alpha_lab.quant.factors.__all__`.

- [x] **Step 3: Run target tests**

Run: `.venv/bin/python -m pytest tests/quant/test_factor_evaluation.py -q`

Expected Green: `4 passed`.

### Task 3: Documentation And Status

**Files:**
- Create: `docs/factor-evaluation.md`
- Modify: `docs/development-progress-checklist.md`
- Modify: `docs/development-status.md`
- Modify: `tasks/todo.md`

- [ ] **Step 1: Document metric contract**

Document scope, DTOs, metric definitions, PIT/sample-overlap guards, artifact output and explicit non-goals.

- [ ] **Step 2: Update progress**

Mark `SAL-P3-009` done, add `DEC-056` and `AEV-058`, update P3 progress to `9/17`, total progress to `58/129`, and move `SAL-P3-010` / `SAL-P3-011` to `READY`.

- [ ] **Step 3: Update status**

Update `docs/development-status.md` to name `SAL-P3-009` as the latest task, list `SAL-P3-010` / `SAL-P3-011` as current READY work, and include `docs/factor-evaluation.md` in the next-session prompt.

### Task 4: Verification And Commit

**Files:**
- All files above

- [ ] **Step 1: Run verification**

Run target, related, full pytest, compileall, dependency lock guard, `git diff --check`, and immutable tag check.

- [ ] **Step 2: Review changes**

Attempt an independent code-review subagent. If unavailable, record the tool failure and perform a local senior review of metric semantics, guardrails, docs and no-go boundaries.

- [ ] **Step 3: Commit**

Stage only `SAL-P3-009` files and create a Chinese checkpoint commit. Then update recovery docs with the actual implementation checkpoint hash and create a status-sync checkpoint if needed.
