# Formal Backtest API Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement `SAL-P4-020` by adding a framework-neutral formal portfolio backtest API facade for `/api/v1/quant/backtest-runs`.

**Architecture:** Add an application-layer API module that mirrors the existing Quant Screening API style while binding to the already-built BacktestRun orchestrator, resource supervisor and ArtifactStore contracts. The API creates a queued task and resource-control record, then exposes compact status, metrics/audit descriptors, cursor-paginated artifact table reads, cancel requests and explicit artifact-download authorization without running worker loops or external integrations.

**Tech Stack:** Python dataclasses, existing `TaskBackend`, `BacktestRunResourceSupervisor`, `BacktestRunOrchestrator`, `BacktestArtifactBundle`, `ArtifactStore`, pytest.

---

## File Structure

- Create: `src/serenity_alpha_lab/application/backtest_api.py`
  - Owns SAL-P4-020 route metadata, response DTOs, in-memory repository, idempotent create, status/cancel methods, artifact pagination and download authorization.
- Create: `tests/application/test_backtest_api.py`
  - Defines the Red/Green API contract using real `LocalArtifactStore` payloads and existing P4 BacktestRun fixtures.
- Create: `docs/backtest-api.md`
  - Records route contract, response semantics, artifact authorization, non-goals and verification evidence.
- Modify: `src/serenity_alpha_lab/application/__init__.py`
  - Lazily exports the new API facade symbols without importing FastAPI or worker integrations at package import time.
- Modify: `docs/development-progress-checklist.md`
  - Marks `SAL-P4-020` done, advances P4 to `20/22`, total progress to `86/129`, adds `DEC-084` and `AEV-086`, and makes `SAL-P4-021` READY.
- Modify: `docs/development-status.md`
  - Updates current task, checkpoints, completion scope and next startup prompt.
- Modify: `tasks/todo.md`
  - Tracks Red/Green/verification/review and records subagent fallback.

## Task 1: Red API Contract Test

**Files:**
- Create: `tests/application/test_backtest_api.py`

- [ ] **Step 1: Add route and service import test**

```python
from serenity_alpha_lab.application.backtest_api import (
    FORMAL_BACKTEST_API_ROUTES,
    FORMAL_BACKTEST_TASK_TYPE,
    FormalBacktestApiService,
)


def test_formal_backtest_api_declares_expected_routes_and_no_legacy_signal_namespace() -> None:
    paths = {(route.method, route.path, route.response_status) for route in FORMAL_BACKTEST_API_ROUTES}
    assert ("POST", "/api/v1/quant/backtest-runs", 202) in paths
    assert ("GET", "/api/v1/quant/backtest-runs/{run_id}", 200) in paths
    assert ("GET", "/api/v1/quant/backtest-runs/{run_id}/orders", 200) in paths
    assert all("/api/v1/backtest" not in route.path for route in FORMAL_BACKTEST_API_ROUTES)
    assert FORMAL_BACKTEST_TASK_TYPE == "quant.backtest.run"
```

- [ ] **Step 2: Add behavior tests**

Cover:
- Idempotency-Key required and replayed.
- Create response is `202 Accepted`, compact, and points to `/api/v1/quant/backtest-runs/{run_id}`.
- Status response separates `task_status`, `execution_status`, `effective_mode`, `spec_hash`, artifacts and runtime flags.
- Metrics and audit responses read the immutable Artifact payloads.
- Orders and positions use cursor pagination over artifact rows.
- Artifact download requires a subject with explicit run and artifact permission.
- Import boundary excludes FastAPI, Qlib runtime, Celery, Redis, SQLAlchemy, LLM and legacy DSA modules.

- [ ] **Step 3: Run Red**

Run:

```bash
uv run --extra core --extra dev python -m pytest tests/application/test_backtest_api.py -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'serenity_alpha_lab.application.backtest_api'`.

## Task 2: Green API Facade

**Files:**
- Create: `src/serenity_alpha_lab/application/backtest_api.py`
- Modify: `src/serenity_alpha_lab/application/__init__.py`

- [ ] **Step 1: Implement API DTOs**

Define:
- `BACKTEST_API_CONTRACT_VERSION = "application.formal_backtest_api@1.0.0"`
- `FORMAL_BACKTEST_TASK_TYPE = "quant.backtest.run"`
- `BACKTEST_API_RUN_SCHEMA_NAME = "quant.backtest_api_run"`
- `BacktestApiRoute`, `BacktestApiResponse`, `BacktestApiError`
- `BacktestArtifactAccessSubject`, `BacktestArtifactAccessPolicy`

- [ ] **Step 2: Implement repository and create path**

Implement `InMemoryBacktestApiRepository` and `FormalBacktestApiService.create_backtest_run()`:
- Validate `idempotency_key`.
- Compute deterministic request hash from `BacktestRunRequest.request_payload()`.
- Replay same idempotency key and reject conflicting reuse.
- Submit `TaskCommand` with compact payload.
- Start `BacktestRunResourceSupervisor` tracking without running a child process or worker loop.
- Return `202` with `Location` and `Idempotency-Key`.

- [ ] **Step 3: Implement status, cancel and artifact methods**

Implement:
- `get_backtest_run()`
- `observe_backtest_run()` for tests/worker boundary adapters to attach child snapshots without creating a worker loop.
- `cancel_backtest_run()`
- `get_backtest_metrics()`
- `get_backtest_audit()`
- `list_backtest_orders()`
- `list_backtest_positions()`
- `download_backtest_artifact()`

Keep status compact. Read large table rows only from the relevant `BacktestArtifactKind` output descriptor.

- [ ] **Step 4: Export lazily**

Add the new symbols to `src/serenity_alpha_lab/application/__init__.py` lazy export map.

- [ ] **Step 5: Run Green**

Run:

```bash
uv run --extra core --extra dev python -m pytest tests/application/test_backtest_api.py -q
```

Expected: PASS.

## Task 3: Evidence and State Sync

**Files:**
- Create: `docs/backtest-api.md`
- Modify: `docs/development-progress-checklist.md`
- Modify: `docs/development-status.md`
- Modify: `tasks/todo.md`

- [ ] **Step 1: Add evidence doc**

Record:
- Route table and contract version.
- Status/metrics/orders/positions/audit/cancel behavior.
- Cursor pagination and artifact authorization semantics.
- Explicit legacy Signal Evaluation separation.
- Non-goals: no Quant Lab, Evidence Agent, Worker loop, real Provider/LLM, Qlib runtime or legacy route changes.

- [ ] **Step 2: Update progress and state**

Mark `SAL-P4-020` as `DONE`, set P4 to `20/22`, total to `86/129`, add decision/evidence rows, make `SAL-P4-021` READY, and update the next startup prompt.

- [ ] **Step 3: Final verification**

Run:

```bash
uv run --extra core --extra dev python -m pytest tests/application/test_backtest_api.py -q
uv run --extra core --extra dev python -m pytest tests/application/test_backtest_api.py tests/application/test_backtest_run_orchestration.py tests/application/test_backtest_resource_control.py tests/quant/test_backtest_golden_property.py tests/quant/test_backtest_artifact.py tests/architecture/test_architecture_boundaries.py -q
uv run --extra core --extra dev python -m pytest -q
uv run --extra core --extra dev python -m compileall -q src/serenity_alpha_lab tests
scripts/verify-python-dependency-lock.sh
scripts/apply-dsa-baseline-patches.sh --check-only
git rev-parse upstream/dsa-v3.26.1
git diff --check
```

Expected: all commands exit 0; immutable tag remains `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`.

## Scope Guard

- Do not modify legacy DSA `/api/v1/backtest/*` Signal Evaluation routes or schemas.
- Do not name Qlib internal evidence, Dataset conversion, Screen result or AlphaSift T+N evaluation as formal portfolio backtest output.
- Do not add FastAPI route wiring in this task; the service is the framework-neutral API contract boundary.
- Do not start Quant Lab, Evidence Agent, Worker loop, real Provider/LLM calls or Qlib runtime.
- Do not inline orders/positions/audit large lists in create/status responses.
