# Instrument Master Dataset Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete `SAL-P2-005` by implementing a versionable instrument master Dataset with historical validity windows and provider-symbol validity.

**Architecture:** Add a narrow `datasets.instrument_master` module that keeps schema/validation/query logic independent from Provider SDKs, DSA runtime source, PIT data, calendars, and Quant Core. Publish the Dataset as a deterministic ArtifactStore JSON artifact with run/stage attribution and Bronze lineage, while leaving Dataset Catalog/latest alias work to `SAL-P2-011`.

**Tech Stack:** Python 3.11+, dataclasses, pytest, existing `InstrumentId`, `ProviderSymbolMapping`, `ArtifactStore`, `TraceContext` scalar IDs, and local `ProblemDetails` ValueError mapping.

---

### Task 1: Instrument Master Contract Tests

**Files:**
- Create: `tests/datasets/test_instrument_master.py`
- Read: `src/serenity_alpha_lab/domain/instruments.py`
- Read: `src/serenity_alpha_lab/repositories/local_artifact_store.py`

- [ ] **Step 1: Write failing tests**

```python
def test_instrument_master_publishes_artifact_and_queries_as_of(tmp_path):
    # Create current and historical records, publish them through LocalArtifactStore,
    # then assert deterministic artifact metadata, Bronze lineage, run/stage
    # attribution, and as-of lookup for active/delisted states.
```

- [ ] **Step 2: Run tests to verify Red**

Run: `uv run --extra core --extra dev python -m pytest tests/datasets/test_instrument_master.py -q`

Expected: FAIL during collection with missing `serenity_alpha_lab.datasets.instrument_master`.

### Task 2: Minimal Dataset Implementation

**Files:**
- Create: `src/serenity_alpha_lab/datasets/instrument_master.py`
- Modify: `src/serenity_alpha_lab/datasets/__init__.py`

- [ ] **Step 1: Implement immutable schema records**

```python
@dataclass(frozen=True, slots=True)
class InstrumentMasterRecord:
    instrument_id: InstrumentId
    name: str
    currency: str
    listing_status: ListingStatus
    valid_from: date
    valid_to: date | None = None
```

- [ ] **Step 2: Implement validity checks**

Validate unique `(instrument_id.canonical, valid_from)`, non-overlapping record windows per instrument, non-overlapping provider mapping windows per provider/symbol, required Bronze source artifact IDs, and consistent provider mapping instrument IDs.

- [ ] **Step 3: Implement query and publish APIs**

Expose `InstrumentMasterDataset.query_as_of()`, `provider_mapping_as_of()`, `to_json_bytes()`, and `InstrumentMasterDataset.publish()` using existing `ArtifactStore.put_bytes()`.

- [ ] **Step 4: Run target tests**

Run: `uv run --extra core --extra dev python -m pytest tests/datasets/test_instrument_master.py -q`

Expected: PASS.

### Task 3: Evidence, Ledger, And Status

**Files:**
- Create: `docs/instrument-master-dataset.md`
- Modify: `docs/development-progress-checklist.md`
- Modify: `docs/development-status.md`
- Modify: `tasks/todo.md`

- [ ] **Step 1: Record acceptance evidence**

Document scope, schema, lineage, validation rules, verification output, and explicit exclusions: no PIT/fallback policy, real Provider calls, daily bars, Quant Core, formal backtest, Evidence Agent, or DSA runtime migration.

- [ ] **Step 2: Update progress/status ledgers**

Mark `SAL-P2-005` done, set P2 to `5/20`, total to `34/129`, promote `SAL-P2-006` to READY, and refresh next-session prompt.

- [ ] **Step 3: Run verification**

Run target tests, related dataset/domain/provider/artifact/repository/architecture tests, full pytest, py_compile, dependency lock check, immutable tag check, and `git diff --check`.

- [ ] **Step 4: Commit**

Stage only `SAL-P2-005` files and commit with Chinese checkpoint message.
