# Data Quality Rule Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `SAL-P2-012` as an offline Dataset quality rule engine that evaluates rows, classifies failures as warning/quarantine/blocking, publishes deterministic reports, and exposes manifest metadata.

**Architecture:** Add `src/serenity_alpha_lab/datasets/quality.py` inside the existing Dataset boundary. The module evaluates `QualityDatasetSnapshot` values produced from schema declarations and Dataset records, emits immutable `DataQualityReport` DTOs, and leaves latest-alias blocking/atomic quarantine transactions to `SAL-P2-013`.

**Tech Stack:** Python stdlib dataclasses/enums/protocols, existing `ArrowSchemaRegistry`, `ArtifactStore`, Dataset record `to_record()` payloads, and pytest offline fixtures.

---

### Task 1: Red Tests

**Files:**
- Create: `tests/datasets/test_data_quality.py`

- [ ] **Step 1: Add failing tests**

```python
from serenity_alpha_lab.datasets.quality import DataQualityEngine
```

Cover schema/type checks, duplicate primary keys, OHLC validity, non-negative volume/amount, null-ratio drift, continuity gaps, return/volume outliers, adjustment factor jumps, deterministic report publishing, manifest metadata, and `ValueError -> ProblemDetails` mapping.

- [ ] **Step 2: Run target test and confirm red**

Run: `uv run --extra core --extra dev python -m pytest tests/datasets/test_data_quality.py -q`

Expected: FAIL during collection because `serenity_alpha_lab.datasets.quality` does not exist.

### Task 2: Quality Engine

**Files:**
- Create: `src/serenity_alpha_lab/datasets/quality.py`
- Modify: `src/serenity_alpha_lab/datasets/__init__.py`

- [ ] **Step 1: Implement DTOs**

Create `DataQualitySeverity`, `DataQualityStatus`, `QualityDatasetSnapshot`, `DataQualityIssue`, and `DataQualityReport`. Each issue must include dataset name, dataset version, rule id/version, severity, partition, primary key, field name, observed/expected values, message and sample.

- [ ] **Step 2: Implement rule protocol and engine**

Create `DataQualityRule` and `DataQualityEngine.evaluate()`. The engine collects rule issues, sorts them deterministically, and derives final status by highest severity.

- [ ] **Step 3: Implement built-in rules**

Add `SchemaFieldRule`, `UniquePrimaryKeyRule`, `OhlcRelationshipRule`, `NonNegativeFieldRule`, `NullRatioDriftRule`, `TradingContinuityRule`, `ReturnOutlierRule`, `VolumeSpikeRule`, and `AdjustmentFactorJumpRule`.

- [ ] **Step 4: Add report publishing and manifest metadata**

`DataQualityReport.publish()` writes deterministic JSON to `ArtifactStore`; `manifest_metadata()` returns string metadata including quality status, rule set version, issue counts and optional report artifact id.

- [ ] **Step 5: Export symbols**

Expose public quality engine symbols from `serenity_alpha_lab.datasets`.

### Task 3: Evidence And Verification

**Files:**
- Create: `docs/data-quality-rule-engine.md`
- Modify: `docs/development-progress-checklist.md`
- Modify: `docs/development-status.md`
- Modify: `tasks/todo.md`

- [ ] **Step 1: Run target and related tests**

Run:
`uv run --extra core --extra dev python -m pytest tests/datasets/test_data_quality.py -q`
`uv run --extra core --extra dev python -m pytest tests/datasets tests/architecture tests/application/test_api_errors.py tests/domain/test_artifacts.py tests/repositories/test_local_artifact_store.py -q`

- [ ] **Step 2: Run full and static verification**

Run:
`uv run --extra core --extra dev python -m pytest -q`
`uv run --extra core --extra dev python -m compileall -q src/serenity_alpha_lab tests`
`scripts/verify-python-dependency-lock.sh`
`git diff --check`
`git rev-parse upstream/dsa-v3.26.1`

- [ ] **Step 3: Update status and commit**

Update evidence, progress, status, `tasks/todo.md` review and next-session prompt, then commit with a Chinese checkpoint message for `SAL-P2-012`.
