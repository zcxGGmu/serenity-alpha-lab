# Screen Performance Reproducibility Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete `SAL-P3-016` by adding a deterministic screen performance and reproducibility acceptance layer.

**Architecture:** Add a narrow `quant.screening.performance` contract that consumes existing `ScreenSnapshot`, `ScreenPipelineStageTrace`, `ArtifactManifest` and run metadata. The layer records stage timing/memory, capacity budgets, incremental baseline and canonical result hashes without changing ScreenDefinition Pipeline or API behavior. Output is a fixed Run Bundle plus a deterministic JSON performance report Artifact.

**Tech Stack:** Python 3.11 dataclasses/enums, stdlib JSON/hashlib, existing `DatasetVersionRef`, `ScreenSnapshot`, `ScreenPipelineStageTrace`, `ArtifactStore`, pytest.

---

### Task 1: Red Contract Tests

**Files:**
- Create: `tests/quant/test_screen_performance_reproducibility.py`

- [x] **Step 1: Write failing performance/reproducibility contract tests**

Test import should initially fail because `serenity_alpha_lab.quant.screening.performance` does not exist. Cover default A-share SLO budgets, stage sample validation, deterministic result hash independent of run-specific trace IDs, repeated snapshot reproducibility, incremental baseline budget, fixed Run Bundle fields and deterministic ArtifactStore publication.

- [x] **Step 2: Run target test and confirm Red**

Run: `.venv/bin/python -m pytest tests/quant/test_screen_performance_reproducibility.py -q`

Expected: FAIL with missing `serenity_alpha_lab.quant.screening.performance`.

### Task 2: Performance Contract

**Files:**
- Create: `src/serenity_alpha_lab/quant/screening/performance.py`
- Modify: `src/serenity_alpha_lab/quant/screening/__init__.py`

- [x] **Step 1: Implement immutable DTOs**

Add `ScreenPerformanceBudget`, `ScreenStagePerformanceSample`, `ScreenIncrementalBaseline`, `ScreenRunBundle`, `ScreenReproducibilityCheck` and `ScreenPerformanceReport`.

- [x] **Step 2: Implement deterministic helpers**

Add `screen_result_hash(snapshot, code_version, engine_version)`, `build_screen_run_bundle(...)`, `evaluate_screen_reproducibility(...)`, `build_screen_performance_report(...)` and `publish_screen_performance_report(...)`.

- [x] **Step 3: Export symbols**

Update `quant.screening.__init__` so callers can use the acceptance contract from the public screening package.

- [x] **Step 4: Run target test and confirm Green**

Run: `.venv/bin/python -m pytest tests/quant/test_screen_performance_reproducibility.py -q`

Expected: PASS.

### Task 3: Evidence Docs

**Files:**
- Create: `docs/screen-performance-reproducibility.md`
- Modify: `docs/development-progress-checklist.md`
- Modify: `docs/development-status.md`
- Modify: `tasks/todo.md`

- [x] **Step 1: Document SLO and bundle semantics**

Record architecture SLOs (`common screening <= 3s`, cached query <= 500ms), capacity/memory budgets, canonical result hash fields, fixed Run Bundle schema and explicit non-goals.

- [x] **Step 2: Update progress/evidence**

Move `SAL-P3-016` to done only after verification, add `AEV-065`, add `DEC-063`, set P3 progress to `16/17`, total progress to `65/129`, and move `SAL-P3-017` to `READY`.

- [x] **Step 3: Run verification**

Run target, related, full Python, compileall, lock guard, DSA patch check, immutable tag check and `git diff --check`.

- [x] **Step 4: Commit**

Stage only SAL-P3-016 files and create a Chinese checkpoint commit with completion, risk, verification and task ID.
