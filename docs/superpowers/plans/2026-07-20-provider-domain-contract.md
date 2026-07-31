# Provider Domain Contract Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Define the pure-domain Provider contract required by `SAL-P2-001`, including capabilities, immutable batches and provenance, stable failure categories, and the existing Problem Details boundary.

**Architecture:** Add a synchronous, stdlib-only `MarketDataProvider` Protocol under `domain`, with generic `DataBatch[T]` values and immutable metadata. Keep Profile and Trace enforcement at application/integration boundaries, expose only scalar trace/run/stage correlation IDs in provenance, and map domain Provider failures to the frozen P1 `provider_error` Problem Details response.

**Tech Stack:** Python 3.11, dataclasses, `StrEnum`, `Protocol`, pytest.

---

## File Structure

- Create `src/serenity_alpha_lab/domain/providers.py`: Provider capabilities, provenance, batches, warnings, failures, and Protocol.
- Modify `src/serenity_alpha_lab/domain/__init__.py`: export the stable Provider contract.
- Create `tests/domain/test_provider_contract.py`: pure-domain behavior and fake-provider contract tests.
- Modify `src/serenity_alpha_lab/application/api_errors.py`: map `ProviderError` to the existing sanitized `ProviderProblem`.
- Modify `tests/application/test_api_errors.py`: verify Provider failure mapping and redaction.
- Modify `tests/architecture/test_architecture_boundaries.py`: pin the Provider contract's dependency direction.
- Create `docs/provider-domain-contract.md`: acceptance evidence and follow-on boundaries.
- Modify `docs/development-progress-checklist.md`, `docs/development-status.md`, and `tasks/todo.md`: update the authoritative task state after verification.

### Task 1: Define Provider Contract Tests

- [ ] **Step 1: Write failing domain tests**

Create `tests/domain/test_provider_contract.py` with fixed UTC times and a fake provider. Cover:

```python
def test_data_batch_preserves_provenance_freshness_and_warnings() -> None:
    provenance = Provenance(
        provider_id="fixture",
        provider_version="1.0",
        operation=ProviderCapability.DAILY_BARS,
        request_parameters={"instruments": ["600519.XSHG"]},
        requested_at=REQUESTED_AT,
        fetched_at=FETCHED_AT,
        raw_response_sha256=RAW_SHA256,
        field_lineage={"close": "fixture.close"},
        trace_id="trace-001",
        run_id="run-001",
        stage_id="stage-provider",
    )
    batch = DataBatch(
        records=[{"instrument_id": "600519.XSHG", "close": "1688.00"}],
        schema_name="market.daily_bars",
        schema_version="1.0.0",
        provenance=provenance,
        fresh_until=FRESH_UNTIL,
        warnings=[ProviderWarning(code="partial_fields", message="turnover is absent", fields=("turnover",))],
    )
    assert batch.is_stale(at=FRESH_UNTIL) is False
    assert batch.is_stale(at=FRESH_UNTIL + timedelta(microseconds=1)) is True
```

Also cover all six `ProviderErrorCategory` values, retryability, rate-limit retry-after, SHA-256 and timezone validation, capability support, external collection mutation isolation, legal empty batches, and runtime Protocol conformance.

- [ ] **Step 2: Run the target test and confirm Red**

Run:

```bash
uv run --python /Users/zq/.local/bin/python3.11 --with pytest pytest tests/domain/test_provider_contract.py -q
```

Expected: collection fails because `serenity_alpha_lab.domain.providers` does not exist.

### Task 2: Implement the Pure-Domain Contract

- [ ] **Step 1: Add minimal domain implementation**

Create `src/serenity_alpha_lab/domain/providers.py` with:

```python
class ProviderCapability(StrEnum):
    INSTRUMENTS = "instruments"
    TRADING_CALENDAR = "trading_calendar"
    DAILY_BARS = "daily_bars"
    FUNDAMENTALS = "fundamentals"

class ProviderErrorCategory(StrEnum):
    RETRYABLE = "retryable"
    RATE_LIMITED = "rate_limited"
    AUTH = "auth"
    SCHEMA_DRIFT = "schema_drift"
    DATA_INVALID = "data_invalid"
    PERMANENT = "permanent"
```

Define immutable `Capability`, `ProviderCapabilities`, `ProviderWarning`, `Provenance`, and generic `DataBatch[T]`. Normalize collections to tuple/frozenset/copied mappings, require timezone-aware datetimes, validate SHA-256 using `ArtifactUri.for_sha256`, accept empty batches, and make staleness evaluation explicit via `is_stale(at=...)`.

Define `ProviderError(RuntimeError)` with `category`, `provider_id`, `operation`, optional `retry_after_seconds`, and an `is_retryable` property. Define runtime-checkable synchronous `MarketDataProvider` with `provider_id`, `capabilities`, `list_instruments`, `get_calendar`, `get_daily_bars`, and `get_fundamentals`; operation results remain generic records so P2-005/006/007/009 DTOs are not implemented early.

- [ ] **Step 2: Export the contract**

Update `src/serenity_alpha_lab/domain/__init__.py` to export every stable Provider symbol without introducing application/integration imports.

- [ ] **Step 3: Run domain tests and refactor under Green**

Run:

```bash
uv run --python /Users/zq/.local/bin/python3.11 --with pytest pytest tests/domain/test_provider_contract.py tests/domain -q
```

Expected: all Provider and existing domain tests pass.

### Task 3: Reuse Problem Details and Enforce Boundaries

- [ ] **Step 1: Write failing application and architecture tests**

Add an API error test that passes a `ProviderError` containing a path and token through `problem_from_exception()` and expects status `502`, code `provider_error`, the existing trace ID, and redacted detail. Add a targeted architecture assertion that `domain/providers.py` imports neither `application` nor `integrations`.

- [ ] **Step 2: Run the tests and confirm Red**

Run:

```bash
uv run --python /Users/zq/.local/bin/python3.11 --with pytest --with pydantic-settings --with alembic pytest tests/application/test_api_errors.py tests/architecture/test_architecture_boundaries.py -q
```

Expected: the Provider failure is not yet mapped to `ProviderProblem`.

- [ ] **Step 3: Implement the minimal error mapping**

Import `ProviderError` in `application/api_errors.py` and map it before the general `ValueError`/fallback branches:

```python
if isinstance(exc, ProviderError):
    return ProviderProblem(str(exc)).to_problem_detail(
        trace_context=trace_context,
        instance=instance,
    )
```

Do not add new public API error codes; the six domain categories remain available for retry/fallback policy while clients retain the P1 `provider_error` contract.

- [ ] **Step 4: Run target and related suites**

Run:

```bash
uv run --python /Users/zq/.local/bin/python3.11 --with pytest --with pydantic-settings --with alembic pytest tests/domain tests/application tests/architecture -q
```

Expected: all tests pass.

### Task 4: Record Evidence and Complete the Checkpoint

- [ ] **Step 1: Write evidence**

Create `docs/provider-domain-contract.md` documenting the frozen symbols, invariants, P1 contract reuse, no-real-call scope, Red/Green evidence, follow-on tasks, and rollback.

- [ ] **Step 2: Update authoritative task state**

After implementation verification, mark only `SAL-P2-001` done, advance P2 to `1/20` and total to `30/129`, promote `SAL-P2-002` to `READY`, add `DEC-028` and `AEV-030`, keep `RSK-004` open, keep G2 not passed, and refresh the next-session prompt.

- [ ] **Step 3: Run complete verification**

Run:

```bash
uv run --python /Users/zq/.local/bin/python3.11 --with pytest --with pydantic-settings --with alembic pytest -q
uv run --python /Users/zq/.local/bin/python3.11 python -m py_compile src/serenity_alpha_lab/domain/providers.py src/serenity_alpha_lab/domain/__init__.py src/serenity_alpha_lab/application/api_errors.py tests/domain/test_provider_contract.py tests/application/test_api_errors.py tests/architecture/test_architecture_boundaries.py
scripts/verify-python-dependency-lock.sh
git diff --check
git rev-parse upstream/dsa-v3.26.1
git status --short
```

Expected: full pytest passes; compile, lock, whitespace, and immutable tag checks pass; status contains only `SAL-P2-001` files plus ignored local environment state.

- [ ] **Step 4: Review and commit**

Request independent specification and code-quality reviews, resolve all Critical/Important findings, then stage only the Provider contract checkpoint and commit with the required Chinese message body referencing `SAL-P2-001, Gate G2`.
