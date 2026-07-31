# Qlib QuantEngine Adapter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement `SAL-P4-007` by adding a Qlib QuantEngine Adapter boundary that wraps train, predict, backtest, evaluate_factor and Recorder metadata without starting a formal portfolio backtest.

**Architecture:** Add an integration-boundary adapter under `src/serenity_alpha_lab/integrations/qlib/` with immutable DTOs, controlled template IDs and an injectable Qlib facade. The default facade lazy-loads Qlib only inside explicit Quant Worker execution methods, while tests use a fake facade so core/CI runs never import or initialize Qlib.

**Tech Stack:** Python 3.11 dataclasses, Protocol injection, existing `BacktestSpec`, `QlibDatasetConversionArtifacts`, `ArtifactStore`, `QlibRuntimeIsolationPolicy`, pytest contract tests.

---

## Files

- Create: `src/serenity_alpha_lab/integrations/qlib/quant_engine_adapter.py` for DTOs, adapter methods, Recorder mapping and deterministic Artifact publication.
- Modify: `src/serenity_alpha_lab/integrations/qlib/__init__.py` to export adapter symbols without importing Qlib runtime.
- Create: `tests/integrations/test_qlib_quant_engine_adapter.py` for Red/Green contract tests.
- Modify: `docs/development-progress-checklist.md`, `docs/development-status.md`, `tasks/todo.md` and add `docs/qlib-quant-engine-adapter.md` during task closeout.

## Task 1: Red Contract Tests

**Files:**
- Create: `tests/integrations/test_qlib_quant_engine_adapter.py`

- [ ] **Step 1: Write failing tests**
  - Test controlled `QlibQuantEngineConfig` rejects arbitrary module paths and unknown template IDs.
  - Test adapter requires `run_id`, `stage_id`, `trace_id`, concrete `BacktestSpec.spec_hash`, dataset conversion artifacts and `QlibRuntimeIsolationPolicy`.
  - Test `train`, `predict`, `backtest` and `evaluate_factor` call the injected fake facade in order and publish compact step/Recorder evidence artifacts.
  - Test the adapter module AST imports no `qlib`, `pyqlib`, `fastapi` or `sqlalchemy`.

- [ ] **Step 2: Run Red**
  - Run: `uv run --extra core --extra dev python -m pytest tests/integrations/test_qlib_quant_engine_adapter.py -q`
  - Expected: FAIL with `ModuleNotFoundError: serenity_alpha_lab.integrations.qlib.quant_engine_adapter`.

## Task 2: Adapter Implementation

**Files:**
- Create: `src/serenity_alpha_lab/integrations/qlib/quant_engine_adapter.py`
- Modify: `src/serenity_alpha_lab/integrations/qlib/__init__.py`

- [ ] **Step 1: Add immutable contract DTOs**
  - Define `QlibQuantEngineTemplate` enum with approved template IDs only.
  - Define `QlibQuantEngineConfig`, `QlibQuantEngineRequest`, `QlibQuantEngineStepResult`, `QlibRecorderSnapshot` and `QlibQuantEngineRunReport`.
  - Validate no config/input contains keys such as `module_path`, `class`, `module`, `import_path`, or dotted arbitrary paths from caller payloads.

- [ ] **Step 2: Add facade boundary**
  - Define `QlibQuantEngineFacade` Protocol with `train`, `predict`, `backtest`, `evaluate_factor`.
  - Add `LazyQlibQuantEngineFacade` that imports Qlib only inside method bodies and never at module import time.
  - Keep real facade minimal and side-effect-light; tests use fake facade.

- [ ] **Step 3: Add adapter methods**
  - Implement `QlibQuantEngineAdapter.train/predict/backtest/evaluate_factor`.
  - Each method builds a controlled config record from platform DTOs, calls the facade, records platform `run_id`, `stage_id`, `trace_id`, `spec_hash`, dataset conversion artifact IDs and Recorder experiment/recorder IDs.
  - Publish deterministic step evidence artifacts to `ArtifactStore`.

- [ ] **Step 4: Export symbols safely**
  - Export adapter DTOs and adapter class from `integrations.qlib.__init__`.
  - Do not export or instantiate any Qlib runtime object at import time.

- [ ] **Step 5: Run Green**
  - Run: `uv run --extra core --extra dev python -m pytest tests/integrations/test_qlib_quant_engine_adapter.py -q`
  - Expected: PASS.

## Task 3: Docs, Status and Verification

**Files:**
- Create: `docs/qlib-quant-engine-adapter.md`
- Modify: `docs/development-progress-checklist.md`
- Modify: `docs/development-status.md`
- Modify: `tasks/todo.md`

- [ ] **Step 1: Add evidence doc**
  - Document scope, controlled config templates, Recorder mapping, Artifact outputs, non-goals, and ADR-009 constraints.

- [ ] **Step 2: Update progress/state**
  - Mark `SAL-P4-007` done only after verification.
  - Move P4 progress from `6/22` to `7/22`, total from `72/129` to `73/129`.
  - Add decision/evidence rows for Qlib Adapter and make `SAL-P4-008` the next READY task.

- [ ] **Step 3: Run verification**
  - Focused: `uv run --extra core --extra dev python -m pytest tests/integrations/test_qlib_quant_engine_adapter.py -q`
  - Related: Qlib adapter/conversion/isolation, BacktestSpec/Artifact and architecture tests.
  - Full: `uv run --extra core --extra dev python -m pytest -q`
  - Compile: `uv run --extra core --extra dev python -m compileall -q src tests`
  - Guards: `scripts/verify-python-dependency-lock.sh`, `scripts/apply-dsa-baseline-patches.sh --check-only`, `git rev-parse upstream/dsa-v3.26.1`, `git diff --check`.

- [ ] **Step 4: Checkpoint**
  - Stage only SAL-P4-007 files.
  - Commit with Chinese message: `feat(P4): 实现 Qlib QuantEngine Adapter`.

## Guardrails

- Do not start a formal portfolio backtest run, Ledger, Risk, Quant Lab, Evidence Agent, Worker loop, real Provider or real LLM call.
- Do not treat Qlib internal backtest evidence as a formal portfolio `BacktestArtifactBundle`; later tasks own orders, fills, ledger, metrics and audit.
- Do not accept arbitrary Python module paths from API/UI/YAML/strategy payloads.
- Do not import Qlib at module import time or in FastAPI/application/domain/datasets/provider/report paths.
- Do not move `upstream/dsa-v3.26.1` or alter legacy `/api/v1/backtest/*`.
