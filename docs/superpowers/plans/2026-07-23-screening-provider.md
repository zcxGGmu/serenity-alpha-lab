# ScreeningProvider Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete `SAL-P3-003` by defining a platform `ScreeningProvider` contract, a deterministic fake provider, and an AlphaSift adapter that keeps AlphaSift internals out of platform application/domain code.

**Architecture:** Add the application-layer port in `src/serenity_alpha_lab/application/screening_provider.py`, including immutable DTOs, unified screening errors, concrete Dataset Version requirements, and `FakeScreeningProvider`. Add `src/serenity_alpha_lab/integrations/alphasift/provider_adapter.py` as the only module that lazily imports `alphasift.dsa_adapter`, with injected-client tests and runtime profile guard. Keep `CandidateBatch` standardization for `SAL-P3-004`; this task returns a raw screening result DTO with stable fields and candidate mappings.

**Tech Stack:** Python 3.11, dataclasses, Protocol, pytest, existing RuntimeSettings/ProfilePolicy, TraceContext, ProblemDetails.

---

### Task 1: Application ScreeningProvider Contract

**Files:**
- Create: `src/serenity_alpha_lab/application/screening_provider.py`
- Modify: `src/serenity_alpha_lab/application/__init__.py`
- Test: `tests/application/test_screening_provider_contract.py`

- [x] **Step 1: Write failing contract tests**

Create tests that assert:

```python
from serenity_alpha_lab.application.screening_provider import (
    FakeScreeningProvider,
    ScreeningProvider,
    ScreeningProviderError,
    ScreeningRequest,
)

def test_fake_provider_matches_protocol_and_requires_concrete_dataset_versions():
    request = ScreeningRequest(
        strategy_id="quality_momentum",
        market="cn",
        dataset_versions={"raw_daily_bars": "dsv_" + "a" * 32},
        max_results=2,
    )
    provider = FakeScreeningProvider(...)
    assert isinstance(provider, ScreeningProvider)
    assert provider.screen(request).dataset_versions["raw_daily_bars"].startswith("dsv_")

def test_screening_request_rejects_latest_alias():
    with pytest.raises(ScreeningProviderError, match="concrete Dataset Version"):
        ScreeningRequest(strategy_id="x", market="cn", dataset_versions={"raw_daily_bars": "latest"})
```

- [x] **Step 2: Run target test to confirm Red**

Run:

```bash
uv run --extra core --extra dev python -m pytest tests/application/test_screening_provider_contract.py -q
```

Expected: FAIL with missing `serenity_alpha_lab.application.screening_provider`.

- [x] **Step 3: Implement contract and fake provider**

Add immutable DTOs: `ScreeningProviderStatus`, `ScreeningStrategy`, `ScreeningRequest`, `ScreeningResult`, `ScreeningProviderErrorCategory`, `ScreeningProviderError`, `ScreeningProvider` Protocol, and `FakeScreeningProvider`. Validate non-empty strategy/market, positive `max_results`, `timeout_seconds`, concrete `dsv_*` Dataset Version ids, and immutable/frozen nested records.

- [x] **Step 4: Run target test to confirm Green**

Run the same target test. Expected: PASS.

### Task 2: AlphaSift Adapter

**Files:**
- Create: `src/serenity_alpha_lab/integrations/alphasift/__init__.py`
- Create: `src/serenity_alpha_lab/integrations/alphasift/provider_adapter.py`
- Test: `tests/integrations/test_alphasift_screening_adapter.py`
- Modify: `src/serenity_alpha_lab/application/api_errors.py`
- Modify: `tests/architecture/test_architecture_boundaries.py`

- [x] **Step 1: Write failing adapter tests**

Test with an injected fake AlphaSift client:

```python
adapter = AlphaSiftScreeningAdapter(client=fake_client, settings=RuntimeSettings(profile=RuntimeProfile.CI))
status = adapter.status()
strategies = adapter.list_strategies()
result = adapter.screen(ScreeningRequest(..., use_llm_overlay=False))
```

Assert status/strategy/result mapping, trace propagation, `use_llm=False`, timeout/error mapping to `ScreeningProviderError`, and `problem_from_exception()` maps screening errors to provider-style ProblemDetails.

- [x] **Step 2: Run adapter test to confirm Red**

Run:

```bash
uv run --extra core --extra dev python -m pytest tests/integrations/test_alphasift_screening_adapter.py -q
```

Expected: FAIL with missing `integrations.alphasift`.

- [x] **Step 3: Implement adapter**

Implement `AlphaSiftScreeningAdapter` with injected client first, lazy `alphasift.dsa_adapter` import only when no client is injected, CI/profile guard for real calls, normalized `status`, `list_strategies`, and `screen`, and no direct provider/LLM calls in tests.

- [x] **Step 4: Run target test to confirm Green**

Expected: PASS.

### Task 3: Evidence, Status, and Verification

**Files:**
- Create: `docs/screening-provider-contract.md`
- Modify: `docs/development-progress-checklist.md`
- Modify: `docs/development-status.md`
- Modify: `tasks/todo.md`

- [x] **Step 1: Add evidence doc**

Document contract fields, AlphaSift isolation, Dataset Version requirement, fake provider, profile guard, errors/timeouts, and non-goals.

- [x] **Step 2: Update progress and status**

Mark only `SAL-P3-003` as DONE after tests pass; set `SAL-P3-004` READY; keep G3 not passed and all later tasks incomplete.

- [x] **Step 3: Run verification**

Run:

```bash
uv run --extra core --extra dev python -m pytest tests/application/test_screening_provider_contract.py tests/integrations/test_alphasift_screening_adapter.py tests/architecture/test_architecture_boundaries.py -q
uv run --extra core --extra dev python -m pytest -q
uv run --extra core --extra dev python -m compileall src tests
scripts/verify-python-dependency-lock.sh
git diff --check
git rev-parse upstream/dsa-v3.26.1
```

- [x] **Step 4: Commit**

Stage only `SAL-P3-003` files and commit in Chinese with the required body sections.
