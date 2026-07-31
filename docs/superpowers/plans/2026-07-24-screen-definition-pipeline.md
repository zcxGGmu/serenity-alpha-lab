# ScreenDefinition Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `SAL-P3-012` ScreenDefinition and deterministic L0-L4 screening pipeline so published screen definitions combine Historical Universe, provider candidates, factor ranks, optional LLM overlay and simple portfolio/risk gates without bypassing hard filters.

**Architecture:** Add a pure `quant.screening.pipeline` module that consumes existing immutable contracts: `UniverseSnapshot`, `CandidateBatch`, `CrossSectionPostProcessingResult`, `ArtifactStore` and concrete Dataset Version ids. The module freezes versioned `ScreenDefinition` records, derives stable definition ids when weights/filters/constraints change, executes deterministic in-memory stage planning, and publishes a pipeline artifact. It does not add APIs, UI, Worker runtime, real Provider/LLM calls, Quant Core/Qlib execution, formal backtests, Evidence Agent or DSA source migration.

**Tech Stack:** Python dataclasses/enums, existing `DatasetVersionRef`, `InstrumentId`, `CandidateBatch`, `UniverseSnapshot`, factor post-processing DTOs, deterministic JSON/hash helpers, `LocalArtifactStore`, and pytest.

---

### Task 1: Contract Tests

**Files:**
- Create: `tests/quant/test_screen_definition_pipeline.py`
- Modify: `tasks/todo.md`

- [ ] **Step 1: Add Red contract tests**

Cover:
- `ScreenDefinition` requires concrete `dsv_*` dataset versions and `published` lifecycle for formal runs.
- Changing provider/factor/LLM weights, hard filters or risk constraints produces a new stable definition version id.
- `run_screen_pipeline()` applies L0 Historical Universe before L1 provider, L2 factor, L3 overlay and L4 constraints.
- LLM overlay cannot reintroduce an instrument excluded by L0, L1 or L2 hard filters.
- L4 top-N and max-per-industry constraints exclude candidates with structured stage reasons.
- `publish_screen_pipeline_snapshot()` publishes deterministic JSON artifacts.

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/quant/test_screen_definition_pipeline.py -q`

Expected Red: collection fails with missing `serenity_alpha_lab.quant.screening.pipeline`.

### Task 2: Pipeline Module

**Files:**
- Create: `src/serenity_alpha_lab/quant/screening/pipeline.py`
- Modify: `src/serenity_alpha_lab/quant/screening/__init__.py`
- Test: `tests/quant/test_screen_definition_pipeline.py`

- [ ] **Step 1: Implement immutable definition and stage contracts**

Implement:
- `ScreenDefinition`
- `ScreenDefinitionStatus`
- `ScreenProviderStageSpec`
- `ScreenFactorSpec`
- `ScreenFactorStageSpec`
- `ScreenLlmOverlayStageSpec`
- `ScreenRiskGateSpec`
- `ScreenPipelineStage`
- `ScreenPipelineStageTrace`
- `ScreenPipelineCandidate`
- `ScreenPipelineExclusion`
- `ScreenPipelineSnapshot`

- [ ] **Step 2: Implement deterministic pipeline execution**

Implement `run_screen_pipeline()`:
- require published definitions
- validate market, as-of date, universe version and candidate batch metadata
- reject `latest` aliases everywhere
- L0: enforce Historical Universe membership first
- L1: require provider candidates and preserve provider scores
- L2: combine post-processed factor values with configured weights
- L3: apply optional overlay only to already surviving candidates
- L4: enforce top-N and max-per-industry risk gates

- [ ] **Step 3: Implement artifact publication and exports**

Implement `publish_screen_pipeline_snapshot()` and export all public symbols from `serenity_alpha_lab.quant.screening`.

- [ ] **Step 4: Run target tests**

Run: `.venv/bin/python -m pytest tests/quant/test_screen_definition_pipeline.py -q`

Expected Green: target tests pass.

### Task 3: Documentation And Status

**Files:**
- Create: `docs/screen-definition-pipeline.md`
- Modify: `docs/development-progress-checklist.md`
- Modify: `docs/development-status.md`
- Modify: `tasks/todo.md`

- [ ] **Step 1: Document ScreenDefinition and L0-L4 semantics**

Document definition versioning, concrete Dataset Version guards, stage semantics, scoring, risk gate constraints, LLM overlay boundary, artifact payload and explicit non-goals.

- [ ] **Step 2: Update progress and evidence**

Mark `SAL-P3-012` done, add `DEC-059` and `AEV-061`, update P3 progress to `12/17`, total progress to `61/129`, and move `SAL-P3-013` to `READY`.

- [ ] **Step 3: Update recovery status**

Update `docs/development-status.md` and the next-session prompt to include `docs/screen-definition-pipeline.md`, latest implementation checkpoint, latest status-sync checkpoint and strict no-go boundaries.

### Task 4: Verification And Commit

**Files:**
- All files above

- [ ] **Step 1: Run verification**

Run target, related P3 screening/factor suite, full pytest, compileall, dependency lock guard, `git diff --check`, and immutable tag check.

- [ ] **Step 2: Review changes**

Attempt independent code-review subagent. If unavailable due client payload validation, record that limitation and perform local senior review of stage ordering, hard-filter semantics, definition version hashing, artifact determinism, docs/status consistency and no-go boundaries.

- [ ] **Step 3: Commit**

Stage only `SAL-P3-012` files and create a Chinese checkpoint commit. Then update recovery docs with the actual implementation checkpoint hash and create a status-sync checkpoint if needed.
