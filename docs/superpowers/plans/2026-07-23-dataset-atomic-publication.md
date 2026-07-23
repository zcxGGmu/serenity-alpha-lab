# Dataset Atomic Publication Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete `SAL-P2-013` by adding a quality-gated Dataset publication path that publishes immutable Dataset versions first, promotes only `passed` quality reports to `latest`, records held/quarantined/blocking decisions, and cleans temporary files after failed publication attempts.

**Architecture:** Keep `LocalDatasetCatalog` as the immutable manifest and latest-alias repository. Add a narrow `datasets.publication` layer that composes `LocalDatasetCatalog`, `DataQualityReport`, and `ArtifactStore` without importing repository implementations or starting Provider/Worker/Quant behavior. Publication writes quality report Artifact metadata into the Dataset Manifest, persists the version with `update_latest=False`, then atomically promotes to `latest` only when the quality status is `passed`.

**Tech Stack:** Python 3.11, dataclasses, pathlib, pytest, existing `ArtifactStore`, `LocalDatasetCatalog`, `DataQualityReport`, and offline synthetic fixtures.

---

### Task 1: Red Tests For Quality-Gated Publication

**Files:**
- Create: `tests/datasets/test_dataset_publication.py`

- [ ] **Step 1: Write failing tests**

```python
def test_passed_quality_promotes_version_to_latest_and_records_metadata(tmp_path: Path) -> None:
    ...

def test_warning_quarantine_and_blocking_versions_do_not_replace_latest(tmp_path: Path) -> None:
    ...

def test_failed_publication_keeps_old_latest_and_cleans_tmp_files(tmp_path: Path, monkeypatch) -> None:
    ...
```

- [ ] **Step 2: Run tests to verify Red**

Run: `uv run --extra core --extra dev python -m pytest tests/datasets/test_dataset_publication.py -q`
Expected: FAIL during collection with missing `serenity_alpha_lab.datasets.publication` exports.

### Task 2: Implement Publication Gate

**Files:**
- Create: `src/serenity_alpha_lab/datasets/publication.py`
- Modify: `src/serenity_alpha_lab/datasets/catalog.py`
- Modify: `src/serenity_alpha_lab/datasets/__init__.py`

- [ ] **Step 1: Add public catalog helpers**

Add `promote_to_latest(version_id, alias_scope)` and `record_quarantine(...)` to `LocalDatasetCatalog`, preserving existing immutable manifest behavior.

- [ ] **Step 2: Add publication DTOs and publisher**

Implement `DatasetPublicationStatus`, `DatasetPublicationResult`, `DatasetPublicationError`, `DatasetPublicationRequest`, `QualityGatedDatasetPublisher`, and `cleanup_temporary_paths`.

- [ ] **Step 3: Run target tests**

Run: `uv run --extra core --extra dev python -m pytest tests/datasets/test_dataset_publication.py -q`
Expected: PASS.

### Task 3: Documentation, Evidence, And Verification

**Files:**
- Create: `docs/dataset-atomic-publication.md`
- Modify: `docs/development-progress-checklist.md`
- Modify: `docs/development-status.md`
- Modify: `tasks/todo.md`

- [ ] **Step 1: Add evidence document**

Document Red/Green evidence, quality promotion semantics, quarantine records, temp cleanup, and explicit scope exclusions.

- [ ] **Step 2: Update project ledgers**

Mark only `SAL-P2-013` as `DONE`, advance P2 to `13/20`, total progress to `42/129`, add DEC/AEV entries, update current next task to `SAL-P2-014`, and refresh the next-session prompt.

- [ ] **Step 3: Run verification**

Run:

```bash
uv run --extra core --extra dev python -m pytest tests/datasets/test_dataset_publication.py -q
uv run --extra core --extra dev python -m pytest tests/datasets tests/architecture tests/application/test_api_errors.py tests/domain/test_artifacts.py tests/repositories/test_local_artifact_store.py -q
uv run --extra core --extra dev python -m pytest -q
uv run --extra core --extra dev python -m compileall -q src/serenity_alpha_lab tests
scripts/verify-python-dependency-lock.sh
git diff --check
git rev-parse upstream/dsa-v3.26.1
```

Expected: all tests/checks pass; immutable tag remains `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`.
