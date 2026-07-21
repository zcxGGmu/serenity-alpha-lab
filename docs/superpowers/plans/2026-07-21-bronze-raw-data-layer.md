# Bronze Raw Data Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `SAL-P2-004` Bronze storage for sanitized raw Provider responses and request metadata.

**Architecture:** Implement a repository-layer `BronzeRawStore` that writes deterministic JSON envelopes compressed with gzip through the existing `ArtifactStore` contract. The store reuses `Provenance`, `TraceContext`, Run/Stage attribution, content-addressed artifact manifests and local manifest scanning for traceability, while explicitly avoiding Dataset/PIT/fallback or real Provider calls.

**Tech Stack:** Python stdlib, existing `ArtifactStore` / `LocalArtifactStore`, Provider `Provenance`, pytest.

---

## Files

- Create: `src/serenity_alpha_lab/repositories/bronze_raw_store.py`
- Modify: `src/serenity_alpha_lab/repositories/__init__.py`
- Modify: `tests/architecture/test_architecture_boundaries.py`
- Create: `tests/repositories/test_bronze_raw_store.py`
- Create: `docs/bronze-raw-data-layer.md`
- Modify: `docs/development-progress-checklist.md`
- Modify: `docs/development-status.md`
- Modify: `tasks/todo.md`

## Task 1: Red Tests

- [ ] **Step 1: Add Bronze store tests**

Create `tests/repositories/test_bronze_raw_store.py` covering:

- publishing a sanitized raw response through `LocalArtifactStore`
- gzip payload and deterministic content-addressed hash
- envelope includes provider, operation, request parameters, requested/fetched timestamps, source raw hash, sanitized raw hash, trace/run/stage IDs and retention tier
- `find_raw_artifacts()` filters by provider, operation and requested time
- API keys, authorization, Cookie/Set-Cookie, e-mail, phone/mobile and identity fields are absent from bytes on disk
- missing Run attribution is rejected

- [ ] **Step 2: Run Red test**

Run: `uv run --extra core --extra dev python -m pytest tests/repositories/test_bronze_raw_store.py -q`

Expected: FAIL because `serenity_alpha_lab.repositories.bronze_raw_store` does not exist yet.

## Task 2: Implementation

- [ ] **Step 1: Add `BronzeRawStore`**

Implement:

- `BRONZE_RAW_SCHEMA_NAME = "bronze.raw_response"`
- `BRONZE_RAW_SCHEMA_VERSION = "1.0.0"`
- `BRONZE_RAW_CONTENT_TYPE = "application/vnd.serenity.bronze.raw-response+json+gzip"`
- `BronzeRawStoreError`
- immutable `BronzeRawArtifact`
- `BronzeRawStore.put_raw_response(...)`
- `BronzeRawStore.get_envelope(artifact_id)`
- `BronzeRawStore.find_raw_artifacts(...)`

- [ ] **Step 2: Sanitization and compression**

Use recursive sanitization before serialization. Redact sensitive keys and free-form string patterns, then canonicalize JSON and compress via `gzip.compress(..., mtime=0)`.

- [ ] **Step 3: Exports and architecture**

Export Bronze symbols from `src/serenity_alpha_lab/repositories/__init__.py`, and add an architecture assertion that repository code does not import concrete DSA provider runtime modules.

## Task 3: Verification and Evidence

- [ ] **Step 1: Run target and related tests**

Run:

```bash
uv run --extra core --extra dev python -m pytest tests/repositories/test_bronze_raw_store.py -q
uv run --extra core --extra dev python -m pytest tests/repositories tests/domain/test_provider_contract.py tests/application/test_trace_context.py tests/architecture/test_architecture_boundaries.py -q
```

- [ ] **Step 2: Run full verification**

Run:

```bash
uv run --extra core --extra dev python -m pytest -q
uv run --extra core --extra dev python -m compileall -q src/serenity_alpha_lab tests
scripts/verify-python-dependency-lock.sh
git diff --check
git rev-parse upstream/dsa-v3.26.1
```

- [ ] **Step 3: Document evidence**

Create `docs/bronze-raw-data-layer.md` and update progress/status/checkpoint docs with Red/Green evidence and the explicit scope exclusions.
