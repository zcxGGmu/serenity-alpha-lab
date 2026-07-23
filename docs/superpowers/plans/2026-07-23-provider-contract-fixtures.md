# Provider Contract Fixtures Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete `SAL-P2-014` by adding an offline Provider contract fixture corpus for AKShare, efinance, Tushare, BaoStock, and YFinance, covering sanitized responses, schema bindings, timeout, empty-data, and field-drift cases.

**Architecture:** Keep fixtures in the `integrations/data` boundary because they model external Provider payloads without importing Provider SDKs or DSA runtime source. Fixture cases convert successful offline payloads into the frozen Provider `DataBatch` contract, map failure fixtures to `ProviderErrorCategory`, and bind normalized records to the existing Arrow Schema Registry hash for downstream Dataset consumers. Snapshot materialization writes deterministic JSON evidence without making network calls.

**Tech Stack:** Python 3.11, dataclasses, pathlib, deterministic JSON, pytest, existing `MarketDataProvider` domain values, `InstrumentId`, `TraceContext` scalar IDs, and `default_dataset_schema_registry()`.

---

### Task 1: Red Tests For Offline Provider Fixture Corpus

**Files:**
- Create: `tests/integrations/test_provider_contract_fixtures.py`

- [ ] **Step 1: Write failing tests**

```python
def test_default_fixture_catalog_covers_required_providers_and_markets_without_sdk_imports() -> None:
    catalog = default_provider_contract_fixture_catalog()
    assert catalog.provider_ids == ("akshare", "baostock", "efinance", "tushare", "yfinance")

def test_success_fixtures_convert_to_immutable_data_batches_with_schema_hash_and_lineage() -> None:
    ...

def test_error_fixtures_cover_timeout_empty_and_schema_drift_categories() -> None:
    ...

def test_fixture_snapshot_materialization_is_deterministic_and_sanitized(tmp_path: Path) -> None:
    ...
```

- [ ] **Step 2: Run tests to verify Red**

Run: `uv run --extra core --extra dev python -m pytest tests/integrations/test_provider_contract_fixtures.py -q`
Expected: FAIL during collection with missing `serenity_alpha_lab.integrations.data.provider_contract_fixtures`.

### Task 2: Implement Fixture Catalog And Snapshot Writer

**Files:**
- Create: `src/serenity_alpha_lab/integrations/data/provider_contract_fixtures.py`
- Modify: `src/serenity_alpha_lab/integrations/data/__init__.py`

- [ ] **Step 1: Add fixture DTOs**

Implement `ProviderFixtureStatus`, `ProviderFixtureSchema`, `ProviderContractFixtureCase`, and `ProviderContractFixtureCatalog` as frozen dataclasses with defensive JSON freezing, secret-token scanning, schema validation, and deterministic SHA-256 hashing.

- [ ] **Step 2: Add default corpus**

Create success fixtures for AKShare, efinance, Tushare, BaoStock, YFinance US, and YFinance HK daily-bar paths; create timeout, empty-data, and schema-drift fixtures mapped to `retryable`, `data_invalid`, and `schema_drift`.

- [ ] **Step 3: Add contract conversion and snapshot materialization**

Implement `to_data_batch()`, `to_provider_error()`, `default_provider_contract_fixture_catalog()`, and `write_provider_fixture_snapshots()`.

- [ ] **Step 4: Run target tests**

Run: `uv run --extra core --extra dev python -m pytest tests/integrations/test_provider_contract_fixtures.py -q`
Expected: PASS.

### Task 3: Documentation, Status Sync, And Verification

**Files:**
- Create: `docs/provider-contract-fixtures.md`
- Modify: `docs/development-progress-checklist.md`
- Modify: `docs/development-status.md`
- Modify: `tasks/todo.md`

- [ ] **Step 1: Add evidence document**

Document fixture coverage by provider, markets, schemas, error categories, Red/Green evidence, deterministic snapshot behavior, and explicit non-goals.

- [ ] **Step 2: Update ledgers**

Mark only `SAL-P2-014` as `DONE`, advance P2 to `14/20`, total progress to `43/129`, add decision/evidence entries, update current next task to `SAL-P2-015`, and refresh the next-session prompt.

- [ ] **Step 3: Run verification**

Run:

```bash
uv run --extra core --extra dev python -m pytest tests/integrations/test_provider_contract_fixtures.py -q
uv run --extra core --extra dev python -m pytest tests/integrations/test_provider_contract_fixtures.py tests/integrations/test_dsa_provider_adapter.py tests/domain/test_provider_contract.py tests/datasets/test_arrow_schema_registry.py tests/application/test_api_errors.py tests/architecture/test_architecture_boundaries.py -q
uv run --extra core --extra dev python -m pytest -q
uv run --extra core --extra dev python -m compileall -q src/serenity_alpha_lab tests
scripts/verify-python-dependency-lock.sh
git diff --check
git rev-parse upstream/dsa-v3.26.1
```

Expected: all checks pass; immutable tag remains `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`.
