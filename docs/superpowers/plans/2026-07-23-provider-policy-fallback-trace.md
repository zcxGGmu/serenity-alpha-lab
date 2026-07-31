# Provider Policy Fallback Trace Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete `SAL-P2-015` by adding an offline Provider Policy and fallback trace layer that selects Provider results by capability, freshness, field completeness, quality status, and cross-provider conflict rules.

**Architecture:** Add a narrow `integrations/data/provider_policy.py` module that consumes already-normalized Provider `DataBatch` values and `ProviderError` values. The policy layer does not call Provider SDKs, does not publish Datasets, and does not mutate the fixture corpus. It records deterministic diagnostics for every attempted source, selected source, fallback reason, and cross-provider conflict so later Worker/Run Diagnostics can persist the trace.

**Tech Stack:** Python 3.11, frozen dataclasses, stdlib-only YAML-compatible mappings, pytest, existing Provider domain contracts, Provider contract fixtures, `DataQualityStatus`, and TraceContext scalar IDs.

---

### Task 1: Red Tests For Provider Policy

**Files:**
- Create: `tests/integrations/test_provider_policy.py`

- [x] **Step 1: Write failing tests**

```python
def test_policy_selects_first_fresh_complete_provider_and_records_trace() -> None:
    ...

def test_policy_falls_back_from_stale_or_missing_field_successes() -> None:
    ...

def test_policy_records_provider_errors_and_exhaustion_without_real_calls() -> None:
    ...

def test_policy_quarantines_cross_provider_close_conflict_without_averaging() -> None:
    ...

def test_policy_rejects_dataset_mismatch_before_selecting_provider() -> None:
    ...
```

- [x] **Step 2: Run tests to verify Red**

Run: `uv run --extra core --extra dev python -m pytest tests/integrations/test_provider_policy.py -q`
Expected: FAIL during collection with missing `serenity_alpha_lab.integrations.data.provider_policy`.

### Task 2: Implement Provider Policy And Trace DTOs

**Files:**
- Create: `src/serenity_alpha_lab/integrations/data/provider_policy.py`
- Modify: `src/serenity_alpha_lab/integrations/data/__init__.py`

- [x] **Step 1: Add policy request/config DTOs**

Implement frozen `ProviderPolicy`, `ProviderPolicySource`, `ProviderPolicyRequirement`, and `ProviderSelectionRequest` with YAML-compatible `from_mapping()` / `to_record()` helpers.

- [x] **Step 2: Add trace/result DTOs**

Implement `ProviderFallbackAttempt`, `ProviderConflictRecord`, `ProviderFallbackTrace`, `ProviderPolicyStatus`, and `ProviderSelectionResult` with deterministic `to_record()` output.

- [x] **Step 3: Add selection engine**

Implement `ProviderPolicyEngine.select()` over injected offline `DataBatch` / `ProviderError` results. It must reject unsupported, stale, missing-field, and quarantined/blocked-quality results; it must stop on the first fresh complete source unless cross-check conflict exceeds threshold.

- [x] **Step 4: Run target tests**

Run: `uv run --extra core --extra dev python -m pytest tests/integrations/test_provider_policy.py -q`
Expected: PASS.

### Task 3: Documentation, Status Sync, And Verification

**Files:**
- Create: `docs/provider-policy-fallback-trace.md`
- Modify: `docs/development-progress-checklist.md`
- Modify: `docs/development-status.md`
- Modify: `tasks/todo.md`

- [x] **Step 1: Add evidence document**

Document selection rules, fallback categories, cross-provider conflict/quarantine behavior, trace schema, Red/Green evidence, and explicit exclusions.

- [x] **Step 2: Update ledgers**

Mark only `SAL-P2-015` as `DONE`, advance P2 to `15/20`, total progress to `44/129`, add decision/evidence entries, update current next task to `SAL-P2-016`, and refresh the next-session prompt.

- [x] **Step 3: Run verification**

Run:

```bash
uv run --extra core --extra dev python -m pytest tests/integrations/test_provider_policy.py -q
uv run --extra core --extra dev python -m pytest tests/integrations/test_provider_policy.py tests/integrations/test_provider_contract_fixtures.py tests/domain/test_provider_contract.py tests/datasets/test_data_quality.py tests/datasets/test_dataset_publication.py tests/application/test_api_errors.py tests/architecture/test_architecture_boundaries.py -q
uv run --extra core --extra dev python -m pytest -q
uv run --extra core --extra dev python -m compileall -q src/serenity_alpha_lab tests
scripts/verify-python-dependency-lock.sh
git diff --check
git rev-parse upstream/dsa-v3.26.1
```

Expected: all checks pass; immutable tag remains `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`.
