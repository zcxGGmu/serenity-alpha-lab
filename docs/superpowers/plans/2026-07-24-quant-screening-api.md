# Quant Screening API Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the SAL-P3-014 Quant Screening API contract for factor/screen definitions, asynchronous screen runs, paginated results, and snapshot comparison.

**Architecture:** Add a narrow `application.quant_screening_api` module that exposes framework-neutral request/response DTOs, a small in-memory repository, route metadata, and a service facade over existing P3 contracts. It must reuse `ScreenSnapshot`, `ScreenDefinition`, `CandidateBatch`, `FactorDefinition`, Dataset Version guards, `TaskBackend`, `ProblemDetails`, `TraceContext`, `ArtifactStore`, and Run/Stage ids without starting real Provider/LLM calls or Worker execution.

**Tech Stack:** Python 3.11 dataclasses, existing application/domain/quant DTOs, `InMemoryTaskBackend`, pytest contract tests, deterministic pagination and JSON-friendly records.

---

### Task 1: API Contract Tests

**Files:**
- Create: `tests/application/test_quant_screening_api.py`
- Read: `tests/quant/test_screen_snapshot.py`
- Read: `tests/quant/test_screen_definition_pipeline.py`
- Read: `tests/application/test_task_backend_contract.py`

- [ ] **Step 1: Write failing imports**

```python
from serenity_alpha_lab.application.quant_screening_api import (
    QUANT_SCREENING_API_ROUTES,
    QuantScreeningApiService,
    QuantScreeningRunRequest,
)
```

- [ ] **Step 2: Assert route metadata**

```python
paths = {(route.method, route.path) for route in QUANT_SCREENING_API_ROUTES}
assert ("POST", "/api/v1/quant/screen-definitions") in paths
assert ("POST", "/api/v1/quant/screen-runs") in paths
assert ("GET", "/api/v1/quant/screen-runs/{run_id}/results") in paths
```

- [ ] **Step 3: Assert Idempotency-Key and 202 run response**

```python
response = service.create_screen_run(request, idempotency_key="screen:quality:20260724")
assert response.status_code == 202
assert response.headers["Location"] == f"/api/v1/quant/screen-runs/{response.body['run_id']}"
assert service.create_screen_run(request, idempotency_key="screen:quality:20260724").body == response.body
```

- [ ] **Step 4: Assert stable paginated results**

```python
page = service.get_screen_run_results(response.body["run_id"], page_size=2)
assert page.body["as_of"] == "2026-07-24"
assert page.body["dataset_versions"]["universe"].startswith("dsv_")
assert page.body["schema"]["name"] == "quant.screen_snapshot"
assert page.body["pagination"]["next_cursor"] is not None
```

- [ ] **Step 5: Assert comparison and ProblemDetails mapping**

```python
comparison = service.compare_screen_runs(previous_run_id, current_run_id)
assert comparison.body["schema"]["name"] == "quant.screen_snapshot_comparison"
with pytest.raises(ValueError, match="Idempotency-Key"):
    service.create_screen_run(request, idempotency_key="")
```

- [ ] **Step 6: Run Red test**

Run: `.venv/bin/python -m pytest tests/application/test_quant_screening_api.py -q`
Expected: FAIL with missing `serenity_alpha_lab.application.quant_screening_api`.

### Task 2: Quant Screening API Service

**Files:**
- Create: `src/serenity_alpha_lab/application/quant_screening_api.py`
- Modify: `src/serenity_alpha_lab/application/__init__.py`

- [ ] **Step 1: Define route and response DTOs**

```python
@dataclass(frozen=True, slots=True)
class QuantApiRoute:
    method: str
    path: str
    operation_id: str
    response_status: int
```

Add route metadata for factor definitions, screen definitions, screen runs, run results, result row lookup, and comparison endpoints under `/api/v1/quant`.

- [ ] **Step 2: Add request and repository DTOs**

Create `FactorDefinitionCreateRequest`, `ScreenDefinitionCreateRequest`, `QuantScreeningRunRequest`, `QuantScreeningRunRecord`, `QuantScreeningPage`, and `InMemoryQuantScreeningRepository`. Require concrete `dsv_*` Dataset Versions, `fdv_*` factor versions, `sdv_*` screen definition versions, trace/run/stage ids, and timezone-aware timestamps where applicable.

- [ ] **Step 3: Implement definition endpoints**

`create_factor_definition()` stores and returns a `FactorDefinition.to_record()` payload. `create_screen_definition()` stores and returns a `ScreenDefinition.to_record()` payload. Draft/published state is preserved; no factor execution or screen pipeline execution happens here.

- [ ] **Step 4: Implement async run response**

`create_screen_run()` validates `Idempotency-Key`, accepts an existing `ScreenSnapshot` artifact/result for the preview run, submits an `InMemoryTaskBackend` command with task type `quant.screen.run`, and returns status `202`, `Location`, `trace_id`, `run_id`, `stage_id`, concrete Dataset Versions and Artifact metadata if present.

- [ ] **Step 5: Implement result and comparison queries**

`get_screen_run_results()` returns stable cursor pagination over `ScreenSnapshot.results`, sorted by the snapshot contract. Include `as_of`, `dataset_versions`, `schema`, `trace`, `artifact`, `pagination`, and rows. `get_screen_run_result()` returns one row by canonical `InstrumentId`. `compare_screen_runs()` uses `compare_screen_snapshots()`.

### Task 3: Documentation And Status

**Files:**
- Create: `docs/quant-screening-api.md`
- Modify: `docs/development-progress-checklist.md`
- Modify: `docs/development-status.md`
- Modify: `tasks/todo.md`

- [ ] **Step 1: Document API contract**

Record route metadata, request/response semantics, Idempotency-Key behavior, pagination cursor, as-of/dataset/schema/trace output, ProblemDetails boundary, non-goals and verification evidence.

- [ ] **Step 2: Update progress and status**

Move `SAL-P3-014` to DONE after verification, update P3 progress to `14/17`, total progress to `63/129`, and move `SAL-P3-015` to READY while keeping G3 unpassed.

- [ ] **Step 3: Add evidence row**

Add `AEV-063` with Red/Green target, related suite, full pytest, compileall, lock, diff, immutable tag evidence and the implementation checkpoint.

- [ ] **Step 4: Update next-session prompt**

Point the next task to `SAL-P3-015` Screen Lab and preserve strict no-go boundaries.

### Task 4: Verification And Checkpoint

**Files:**
- No additional implementation files.

- [ ] **Step 1: Run target tests**

Run: `.venv/bin/python -m pytest tests/application/test_quant_screening_api.py -q`
Expected: PASS.

- [ ] **Step 2: Run related tests**

Run: `.venv/bin/python -m pytest tests/application/test_quant_screening_api.py tests/quant/test_screen_snapshot.py tests/quant/test_screen_definition_pipeline.py tests/quant/test_factor_evaluation.py tests/quant/test_factor_definition_contract.py tests/application/test_task_backend_contract.py tests/application/test_api_errors.py tests/application/test_trace_context.py tests/architecture/test_architecture_boundaries.py -q`
Expected: PASS.

- [ ] **Step 3: Run full verification**

Run full pytest, compileall, dependency lock guard, `git diff --check`, and immutable upstream tag check.

- [ ] **Step 4: Review and commit**

Perform a local senior review if subagent tooling is unavailable. Stage only SAL-P3-014 files and create a Chinese checkpoint commit.
