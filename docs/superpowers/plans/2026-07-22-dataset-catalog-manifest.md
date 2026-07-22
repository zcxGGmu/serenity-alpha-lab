# Dataset Catalog And Manifest Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete `SAL-P2-011` by adding a Dataset Catalog and Manifest layer that records immutable dataset versions, lineage, file hashes, and mutable `latest` aliases.

**Architecture:** Add a dataset-layer catalog module that wraps already-published `ArtifactManifest` values and frozen `DatasetSchemaDeclaration` values into immutable `DatasetVersionManifest` records. Provide an in-memory/local repository with manifest-last JSON persistence for catalog metadata and explicit alias updates, while preserving the rule that formal runs must resolve to concrete dataset versions instead of `latest`.

**Tech Stack:** Python 3.11 dataclasses, stdlib JSON/hash/pathlib, existing P1 `ArtifactManifest` / `LocalArtifactStore` semantics, P2 `ArrowSchemaRegistry`, pytest.

---

### Task 1: Red Tests For Catalog Contract

**Files:**
- Create: `tests/datasets/test_dataset_catalog.py`
- Modify: none

- [ ] **Step 1: Write failing immutable publish test**

```python
def test_catalog_publishes_immutable_version_manifest_and_latest_alias(tmp_path) -> None:
    catalog = LocalDatasetCatalog(tmp_path / "catalog", schema_registry=default_dataset_schema_registry())
    published = catalog.publish_version(...)
    assert published.version_id.startswith("dsv_")
    assert catalog.resolve_latest("dataset.bars_1d_raw", "cn") == published.version_id
```

- [ ] **Step 2: Write failing lineage and hash tests**

```python
def test_manifest_records_artifact_hashes_schema_hash_lineage_and_previous_version(tmp_path) -> None:
    first = catalog.publish_version(...)
    second = catalog.publish_version(..., previous_version_id=first.version_id, input_versions=[first.version_id])
    assert second.previous_version_id == first.version_id
    assert first.version_id in second.input_version_ids
    assert second.file_hashes[0].sha256 == artifact.sha256
```

- [ ] **Step 3: Write failing latest-scope guard tests**

```python
def test_formal_resolution_rejects_latest_alias(tmp_path) -> None:
    with pytest.raises(DatasetCatalogError, match="latest alias cannot be used"):
        catalog.resolve_for_run(DatasetVersionRef.latest("dataset.bars_1d_raw", "cn"), purpose=DatasetReferencePurpose.FORMAL_EXPERIMENT)
```

- [ ] **Step 4: Run tests to confirm Red**

Run: `uv run --extra core --extra dev python -m pytest tests/datasets/test_dataset_catalog.py -q`
Expected: FAIL during collection because `serenity_alpha_lab.datasets.catalog` does not exist.

### Task 2: Implement Manifest Domain Objects

**Files:**
- Create: `src/serenity_alpha_lab/datasets/catalog.py`
- Modify: `src/serenity_alpha_lab/datasets/__init__.py`
- Test: `tests/datasets/test_dataset_catalog.py`

- [ ] **Step 1: Add immutable file and lineage DTOs**

```python
@dataclass(frozen=True, slots=True)
class DatasetFileManifest:
    artifact_id: str
    uri: str
    sha256: str
    size_bytes: int
    content_type: str
    row_count: int
```

- [ ] **Step 2: Add dataset version manifest**

```python
@dataclass(frozen=True, slots=True)
class DatasetVersionManifest:
    dataset_name: str
    version_id: str
    schema_name: str
    schema_version: str
    schema_hash: str
    created_at: datetime
    files: tuple[DatasetFileManifest, ...]
    input_version_ids: tuple[str, ...] = ()
    previous_version_id: str | None = None
```

- [ ] **Step 3: Validate immutability keys and hashes**

Reject empty dataset/schema/run IDs, missing files, non-SHA256 hashes, negative row counts, duplicate artifact IDs, duplicate file hashes, invalid previous/input version IDs, and manifests whose schema hash does not match the registry declaration.

- [ ] **Step 4: Run target tests**

Run: `uv run --extra core --extra dev python -m pytest tests/datasets/test_dataset_catalog.py -q`
Expected: remaining failures point to repository/alias behavior not yet implemented.

### Task 3: Implement Local Catalog Repository

**Files:**
- Modify: `src/serenity_alpha_lab/datasets/catalog.py`
- Test: `tests/datasets/test_dataset_catalog.py`

- [ ] **Step 1: Add repository APIs**

```python
class LocalDatasetCatalog:
    def publish_version(..., update_latest: bool = True) -> DatasetVersionManifest: ...
    def get_version(self, version_id: str) -> DatasetVersionManifest: ...
    def list_versions(self, dataset_name: str | None = None) -> tuple[DatasetVersionManifest, ...]: ...
    def resolve_latest(self, dataset_name: str, alias_scope: str) -> DatasetVersionManifest: ...
```

- [ ] **Step 2: Persist manifest JSON before alias JSON**

Write version manifest records under `versions/<version_id>.json` with deterministic sorted JSON and update `aliases/<dataset>/<scope>/latest.json` only after the version manifest is durable.

- [ ] **Step 3: Enforce immutable publish semantics**

If `versions/<version_id>.json` already exists, load it and require byte-equivalent manifest content; reject attempts to republish a different manifest under the same version ID.

- [ ] **Step 4: Run target tests**

Run: `uv run --extra core --extra dev python -m pytest tests/datasets/test_dataset_catalog.py -q`
Expected: PASS.

### Task 4: Documentation And Status Evidence

**Files:**
- Create: `docs/dataset-catalog-manifest.md`
- Modify: `docs/development-progress-checklist.md`
- Modify: `docs/development-status.md`
- Modify: `tasks/todo.md`

- [ ] **Step 1: Document catalog scope**

Record immutable version semantics, manifest fields, lineage, file hash handling, latest alias rules, and explicit non-goals: no quality engine, fallback policy, real Provider calls, Worker runtime, Quant Core, formal backtest, or Evidence Agent.

- [ ] **Step 2: Update progress and decisions**

Mark `SAL-P2-011` done only after verification, advance P2 to `11/20`, total to `40/129`, add decision/evidence rows, and make `SAL-P2-012` the next ready task.

- [ ] **Step 3: Add review evidence**

Append Red/Green verification, exact commands, guardrails, and checkpoint hashes to `tasks/todo.md`.

### Task 5: Verification And Checkpoint

**Files:**
- All files changed above

- [ ] **Step 1: Run target verification**

Run: `uv run --extra core --extra dev python -m pytest tests/datasets/test_dataset_catalog.py -q`
Expected: PASS.

- [ ] **Step 2: Run related verification**

Run: `uv run --extra core --extra quant --extra dev python -m pytest tests/datasets tests/domain/test_artifacts.py tests/repositories/test_local_artifact_store.py tests/architecture/test_architecture_boundaries.py -q`
Expected: PASS.

- [ ] **Step 3: Run full root verification**

Run: `uv run --extra core --extra dev python -m pytest -q`
Expected: PASS without requiring real Provider/LLM/network access.

- [ ] **Step 4: Run static guard checks**

Run:
```bash
uv run --extra core --extra dev python -m compileall -q src/serenity_alpha_lab tests
scripts/verify-python-dependency-lock.sh
git diff --check
git rev-parse upstream/dsa-v3.26.1
```
Expected: all commands exit 0; immutable tag still resolves to the frozen DSA baseline.

- [ ] **Step 5: Create checkpoint commit**

Run:
```bash
git status --short
git add src/serenity_alpha_lab/datasets tests/datasets docs/dataset-catalog-manifest.md docs/development-progress-checklist.md docs/development-status.md tasks/todo.md docs/superpowers/plans/2026-07-22-dataset-catalog-manifest.md
git commit -m "feat(P2): 实现 Dataset Catalog 与 Manifest"
```

Commit body must mention completed content, compatibility/risk handling, verification, and `SAL-P2-011, Gate G2`.
