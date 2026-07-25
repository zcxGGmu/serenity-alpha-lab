# Qlib Dataset Conversion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `SAL-P4-006` Dataset-to-Qlib conversion without initializing Qlib runtime.

**Architecture:** Add a pure integration-boundary converter under `src/serenity_alpha_lab/integrations/qlib/` that consumes already-published, passed `DatasetVersionManifest` records plus in-memory platform Dataset objects. It emits deterministic calendar, instrument, feature and field-mapping artifacts through `ArtifactStore`, while recording source Dataset versions, hashes and bidirectional lineage. No Qlib import, `qlib.init`, adapter runtime, formal backtest run, ledger, risk or Worker loop is introduced.

**Tech Stack:** Python 3.11 dataclasses, existing Dataset DTOs, `DatasetVersionManifest`, `ArtifactStore`, pytest, deterministic JSON/text bytes.

---

### Task 1: Red Contract Tests

**Files:**
- Create: `tests/integrations/test_qlib_dataset_conversion.py`
- Modify: none

- [ ] **Step 1: Write tests for conversion outputs**
  - Build synthetic CN `TradingCalendarDataset`, `InstrumentMasterDataset` and `AdjustedDailyBarsDataset`.
  - Build passed/published `DatasetVersionManifest` fixtures for `dataset.trading_calendar`, `dataset.instrument_master` and `dataset.bars_1d_adjusted`.
  - Assert conversion returns `calendar`, `instruments`, `features` and `field_mapping` outputs with deterministic ordering, Qlib CN symbols (`SH600519`, `SZ000001`), concrete `dsv_*` lineage and platform-to-Qlib / Qlib-to-platform mappings.

- [ ] **Step 2: Write tests for guards**
  - Assert warning/held/quarantined manifests are rejected.
  - Assert schema/name mismatches are rejected.
  - Assert converter module imports no `qlib`, `pyqlib`, `fastapi` or `sqlalchemy`.

- [ ] **Step 3: Write tests for artifact publication**
  - Publish the conversion bundle twice to `LocalArtifactStore`.
  - Assert calendar/instrument/feature/mapping/summary manifests are deterministic and summary references compact descriptors, not full row payloads.

- [ ] **Step 4: Run target test and confirm Red**
  - Run: `uv run --extra core --extra dev python -m pytest tests/integrations/test_qlib_dataset_conversion.py -q`
  - Expected: FAIL because `serenity_alpha_lab.integrations.qlib.dataset_converter` does not exist yet.

### Task 2: Converter Implementation

**Files:**
- Create: `src/serenity_alpha_lab/integrations/qlib/dataset_converter.py`
- Modify: `src/serenity_alpha_lab/integrations/qlib/__init__.py`

- [ ] **Step 1: Add immutable DTOs**
  - Add `QlibDatasetConversionSpec`, `QlibConvertedDatasetBundle`, `QlibOutputArtifact`, `QlibFieldMapping`, `QlibDatasetConversionArtifacts` and `QlibDatasetConversionError`.
  - Validate market/date range, concrete Dataset manifests, passed/published quality metadata, required schemas and run/stage trace metadata.

- [ ] **Step 2: Convert calendar and instruments**
  - Generate trading-day calendar lines from `TradingCalendarDataset.trading_days()`.
  - Generate instrument lines from effective Instrument Master rows and adjusted feature coverage.
  - Map CN platform IDs to Qlib symbols with explicit exchange prefixes.

- [ ] **Step 3: Convert features**
  - Use adjusted daily bars only for the requested adjustment mode, provider filter and trading dates.
  - Emit stable feature rows with Qlib fields `$open`, `$high`, `$low`, `$close`, `$volume`, `$amount`, `$factor`.
  - Do not fill missing bars; record explicit warnings in summary metadata.

- [ ] **Step 4: Publish artifacts**
  - Publish calendar, instrument, feature, field-mapping and compact summary artifacts through `ArtifactStore`.
  - Use deterministic bytes and content-addressed manifests; summary includes descriptors and source lineage only.

- [ ] **Step 5: Export symbols**
  - Update `integrations.qlib.__init__` to export the converter symbols without importing Qlib runtime.

### Task 3: Evidence And Status

**Files:**
- Create: `docs/qlib-dataset-conversion.md`
- Modify: `docs/development-progress-checklist.md`
- Modify: `docs/development-status.md`
- Modify: `tasks/todo.md`
- Modify: `tasks/lessons.md` if a new correction or recurring pattern appears

- [ ] **Step 1: Document SAL-P4-006**
  - Record scope, source Dataset requirements, calendar/instrument/feature output schemas, field lineage, Qlib runtime non-goals and verification evidence.

- [ ] **Step 2: Update progress and evidence registers**
  - Mark `SAL-P4-006` DONE only after verification.
  - Register `DEC-070` and `AEV-072`; set P4 to `6/22` and total to `72/129`.
  - Keep `SAL-P4-007` READY but not started.

- [ ] **Step 3: Update current status and restart prompt**
  - Refresh `docs/development-status.md` with new completion range, checkpoints, no-go boundaries and copyable prompt.
  - Append `tasks/todo.md` review with tests, scope retained and checkpoint placeholders.

### Task 4: Verification And Checkpoint

**Files:**
- No additional implementation files unless verification exposes defects.

- [ ] **Step 1: Run target and related tests**
  - `uv run --extra core --extra dev python -m pytest tests/integrations/test_qlib_dataset_conversion.py -q`
  - Related suite covering Qlib isolation and Dataset primitives.

- [ ] **Step 2: Run broad verification**
  - `uv run --extra core --extra dev python -m pytest -q`
  - `uv run --extra core --extra dev python -m compileall -q src tests`
  - `scripts/verify-python-dependency-lock.sh`
  - `scripts/apply-dsa-baseline-patches.sh --check-only`
  - `git rev-parse upstream/dsa-v3.26.1`
  - `git diff --check`

- [ ] **Step 3: Review and commit**
  - Review diffs for no Qlib runtime import and no forbidden scope.
  - Stage only SAL-P4-006 files.
  - Commit with a Chinese checkpoint message using the project template.
