# Arrow Schema Registry Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete `SAL-P2-010` by adding a versioned Arrow Schema Registry for instrument master, raw daily bars, corporate actions, adjusted daily bars, and fundamentals.

**Architecture:** Add a dataset-layer registry module that stores immutable schema declarations, lazily converts them to PyArrow schemas, and enforces semantic-version compatibility rules. Register the P2 frozen dataset schemas without creating Dataset Catalog/latest aliases, fallback policy, real Provider calls, Quant Core, formal backtest, or Evidence behavior.

**Tech Stack:** Python 3.11 dataclasses, lazy optional `pyarrow` from the existing `quant` extra, pytest, existing P1/P2 `ArtifactStore` and Dataset constants.

---

### Task 1: Red Tests For Schema Registry

**Files:**
- Create: `tests/datasets/test_arrow_schema_registry.py`
- Modify: none

- [ ] **Step 1: Write failing registry tests**

```python
def test_registry_contains_p2_dataset_schemas_and_arrow_metadata() -> None:
    registry = default_dataset_schema_registry()
    declaration = registry.get("dataset.bars_1d_raw", "1.0.0")
    arrow_schema = declaration.to_pyarrow_schema()
    assert arrow_schema.metadata[b"serenity:schema_name"] == b"dataset.bars_1d_raw"
    assert arrow_schema.field("trade_date").type == pa.date32()
```

- [ ] **Step 2: Write failing compatibility tests**

```python
def test_minor_version_may_add_nullable_field_but_not_change_existing_type() -> None:
    base = DatasetSchemaDeclaration(...)
    compatible = base.with_version("1.1.0").with_added_field(DatasetSchemaField("extra", "utf8", nullable=True))
    breaking = base.with_version("1.1.0").with_replaced_field(DatasetSchemaField("close", "int64"))
    assert base.compare_compatibility(compatible).is_backward_compatible
    assert not base.compare_compatibility(breaking).is_backward_compatible
```

- [ ] **Step 3: Run tests to confirm Red**

Run: `uv run --extra core --extra quant --extra dev python -m pytest tests/datasets/test_arrow_schema_registry.py -q`
Expected: FAIL during collection because `serenity_alpha_lab.datasets.schema_registry` does not exist.

### Task 2: Implement Registry Core

**Files:**
- Create: `src/serenity_alpha_lab/datasets/schema_registry.py`
- Modify: `src/serenity_alpha_lab/datasets/__init__.py`
- Test: `tests/datasets/test_arrow_schema_registry.py`

- [ ] **Step 1: Add immutable schema DTOs**

```python
@dataclass(frozen=True, slots=True)
class DatasetSchemaField:
    name: str
    logical_type: str
    nullable: bool = True
    meaning: str | None = None
```

- [ ] **Step 2: Add declaration and registry APIs**

```python
@dataclass(frozen=True, slots=True)
class DatasetSchemaDeclaration:
    schema_name: str
    schema_version: str
    fields: tuple[DatasetSchemaField, ...]
    primary_key: tuple[str, ...]
    partition_keys: tuple[str, ...] = ()
    content_type: str | None = None

    def to_pyarrow_schema(self): ...
    def compare_compatibility(self, candidate: "DatasetSchemaDeclaration") -> SchemaCompatibilityReport: ...
```

- [ ] **Step 3: Add default P2 registrations**

Use existing P2 schema constants for raw daily bars, corporate actions, adjusted bars, and fundamentals. Add an explicit instrument master field schema and partition key so master data is covered by the registry.

- [ ] **Step 4: Run target tests**

Run: `uv run --extra core --extra quant --extra dev python -m pytest tests/datasets/test_arrow_schema_registry.py -q`
Expected: PASS.

### Task 3: Wire Existing Dataset Metadata

**Files:**
- Modify: `src/serenity_alpha_lab/datasets/instrument_master.py`
- Modify: `src/serenity_alpha_lab/datasets/__init__.py`
- Test: `tests/datasets/test_instrument_master.py`
- Test: `tests/datasets/test_arrow_schema_registry.py`

- [ ] **Step 1: Add instrument master constants**

Add `INSTRUMENT_MASTER_PARTITION_KEYS = ("market",)` and `INSTRUMENT_MASTER_FIELD_SCHEMA` with Arrow-compatible logical types for top-level fields plus nested industries/provider mappings.

- [ ] **Step 2: Include field schema in deterministic JSON**

Update `InstrumentMasterDataset.to_json_bytes()` to include `partition_keys` and `field_schema`, matching the later P2 dataset artifact pattern.

- [ ] **Step 3: Export new public symbols**

Export registry DTOs and instrument master schema constants through `serenity_alpha_lab.datasets`.

- [ ] **Step 4: Run related tests**

Run: `uv run --extra core --extra quant --extra dev python -m pytest tests/datasets/test_instrument_master.py tests/datasets/test_arrow_schema_registry.py -q`
Expected: PASS.

### Task 4: Documentation And Status Evidence

**Files:**
- Create: `docs/arrow-schema-registry.md`
- Modify: `docs/development-progress-checklist.md`
- Modify: `docs/development-status.md`
- Modify: `tasks/todo.md`

- [ ] **Step 1: Document scope and compatibility rules**

Record registered schemas, version rules, PyArrow optional dependency behavior, and explicit non-goals.

- [ ] **Step 2: Update progress and status**

Mark `SAL-P2-010` as `DONE`, advance P2 to `10/20`, total to `39/129`, and make `SAL-P2-011` the next ready task only after verification passes.

- [ ] **Step 3: Add review evidence**

Append Red/Green verification, exact commands, and guardrail notes to `tasks/todo.md`.

### Task 5: Verification And Checkpoint

**Files:**
- All files changed above

- [ ] **Step 1: Run target verification**

Run: `uv run --extra core --extra quant --extra dev python -m pytest tests/datasets/test_arrow_schema_registry.py -q`
Expected: PASS.

- [ ] **Step 2: Run related verification**

Run: `uv run --extra core --extra quant --extra dev python -m pytest tests/datasets tests/domain/test_provider_contract.py tests/application/test_api_errors.py tests/architecture/test_architecture_boundaries.py -q`
Expected: PASS.

- [ ] **Step 3: Run full root verification**

Run: `uv run --extra core --extra dev python -m pytest -q`
Expected: PASS without requiring `pyarrow`, proving registry imports remain safe outside the quant extra.

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
git add src/serenity_alpha_lab/datasets tests/datasets docs/arrow-schema-registry.md docs/development-progress-checklist.md docs/development-status.md tasks/todo.md
git commit -m "feat(P2): 建立 Arrow Schema Registry"
```

Commit body must mention completed content, compatibility/risk handling, verification, and `SAL-P2-010, Gate G2`.
