# FactorDefinition Version Model Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement SAL-P3-005 by adding a versioned FactorDefinition contract with draft/published/retired lifecycle, immutable publication and auditable local repository behavior.

**Architecture:** Keep FactorDefinition under `src/serenity_alpha_lab/quant/factors/` because it is Quant contract state, not Application orchestration. Reuse P2 `DatasetVersionRef.version()` validation for concrete Dataset Version ids, mirror existing immutable dataclass and local-manifest repository patterns, and store retirement separately so published manifests remain immutable.

**Tech Stack:** Python dataclasses, pathlib JSON persistence, existing `uv run --extra core --extra dev python -m pytest` verification, no external runtime dependencies.

---

### Task 1: Contract Tests

**Files:**
- Create: `tests/quant/test_factor_definition_contract.py`

- [x] **Step 1: Write the failing tests**

Add tests that require complete factor specs, concrete Dataset Version references, immutable nested data, repository publication conflicts, retirement records and audit events.

- [x] **Step 2: Run tests to verify failure**

Run: `uv run --extra core --extra dev python -m pytest tests/quant/test_factor_definition_contract.py -q`

Expected: FAIL with `ModuleNotFoundError: No module named 'serenity_alpha_lab.quant.factors.definitions'`.

### Task 2: FactorDefinition Model

**Files:**
- Create: `src/serenity_alpha_lab/quant/factors/definitions.py`
- Modify: `src/serenity_alpha_lab/quant/factors/__init__.py`

- [x] **Step 1: Implement minimal immutable DTOs**

Add `FactorDefinition`, `FactorFormula`, `FactorInput`, `FactorWindow`, `MissingValuePolicy`, `PostProcessingStep`, lifecycle/status enums, validation helpers and JSON-friendly `to_record()` / `from_record()` methods.

- [x] **Step 2: Run target tests**

Run: `uv run --extra core --extra dev python -m pytest tests/quant/test_factor_definition_contract.py -q`

Expected: remaining repository tests fail until Task 3.

### Task 3: Local Repository And Audit

**Files:**
- Modify: `src/serenity_alpha_lab/quant/factors/definitions.py`

- [x] **Step 1: Implement local repository**

Add `LocalFactorDefinitionRepository` with `save_draft()`, `get_draft()`, `publish_draft()`, `get_version()`, `retire_version()`, `version_status()` and `list_audit_events()`.

- [x] **Step 2: Run target tests**

Run: `uv run --extra core --extra dev python -m pytest tests/quant/test_factor_definition_contract.py -q`

Expected: PASS.

### Task 4: Evidence And State Sync

**Files:**
- Create: `docs/factor-definition-version-model.md`
- Modify: `docs/development-progress-checklist.md`
- Modify: `docs/development-status.md`
- Modify: `tasks/todo.md`

- [x] **Step 1: Add evidence document and progress updates**

Record lifecycle, schema, non-goals, verification evidence, updated P3 progress and next READY task.

- [x] **Step 2: Run verification**

Run target/related/full pytest, compileall, dependency lock guard, `git diff --check`, and `git rev-parse upstream/dsa-v3.26.1`.

Expected: all verification commands pass and immutable tag remains `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`.
