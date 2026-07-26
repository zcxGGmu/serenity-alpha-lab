# Formal Backtest API

> Task: `SAL-P4-020` formal portfolio backtest API<br>
> Date: 2026-07-26<br>
> Status: `APPROVED FOR SAL-P4-021 QUANT LAB INPUT ONLY`

## Conclusion

`SAL-P4-020` adds a framework-neutral API contract facade for formal portfolio backtest runs:

```text
src/serenity_alpha_lab/application/backtest_api.py
tests/application/test_backtest_api.py
```

The API namespace is `/api/v1/quant/backtest-runs`. It is deliberately separate from legacy DSA `/api/v1/backtest/*`, which remains `legacy_signal_evaluation` only. The facade submits compact task metadata, starts resource-supervisor tracking, exposes compact run status, reads metrics/audit/orders/positions from immutable `BacktestArtifactBundle` outputs, supports cursor pagination, and requires explicit artifact-download authorization.

This task creates the formal API contract and service layer only. It does not implement Quant Lab UI, Evidence Agent, full Worker loop, real Provider/LLM calls, Qlib runtime initialization, or legacy DSA Backtest route/schema changes.

## Contract

| Item | Contract |
|---|---|
| Contract version | `application.formal_backtest_api@1.0.0` |
| API run schema | `quant.backtest_api_run@1.0.0` |
| Task type | `quant.backtest.run` |
| Run type | `formal_portfolio_backtest` |
| Evaluation type | `portfolio_backtest` |
| Primary implementation | `FormalBacktestApiService` |
| Repository | `InMemoryBacktestApiRepository` |
| Artifact auth | `BacktestArtifactAccessSubject` + `BacktestArtifactAccessPolicy` |

## Routes

| Method | Path | Operation | Status |
|---|---|---|---:|
| `POST` | `/api/v1/quant/backtest-runs` | `createFormalBacktestRun` | `202` |
| `GET` | `/api/v1/quant/backtest-runs/{run_id}` | `getFormalBacktestRun` | `200` |
| `GET` | `/api/v1/quant/backtest-runs/{run_id}/metrics` | `getFormalBacktestMetrics` | `200` |
| `GET` | `/api/v1/quant/backtest-runs/{run_id}/orders` | `listFormalBacktestOrders` | `200` |
| `GET` | `/api/v1/quant/backtest-runs/{run_id}/positions` | `listFormalBacktestPositions` | `200` |
| `GET` | `/api/v1/quant/backtest-runs/{run_id}/audit` | `getFormalBacktestAudit` | `200` |
| `GET` | `/api/v1/quant/backtest-runs/{run_id}/artifacts/{artifact_kind}` | `downloadFormalBacktestArtifact` | `200` |
| `POST` | `/api/v1/quant/backtest-runs/{run_id}/cancel` | `cancelFormalBacktestRun` | `202` |

## Semantics

- Create requires `Idempotency-Key`; identical request hash replays the same `202 Accepted` response, while conflicting reuse is rejected.
- Create responses are compact and include `run_id`, `task_id`, `task_status`, `execution_status`, `spec_hash`, concrete Dataset versions/hashes, resource policy, trace and runtime boundary flags.
- `FormalBacktestApiService` calls `TaskBackend.submit()` and `BacktestRunResourceSupervisor.start()` but does not start a child process, Worker loop or Qlib runtime.
- Successful child observations are accepted through `observe_backtest_run()` as the boundary for future Worker adapters; only then does the service expose finalized `BacktestRunRecord` artifacts.
- Metrics and audit endpoints read their immutable Artifact payloads from the finalized `BacktestArtifactBundle` descriptors.
- Orders and positions are cursor-paginated from Artifact rows; create/status responses never inline large row lists.
- Artifact download requires a `BacktestArtifactAccessSubject` explicitly authorized for both the run id and artifact id, unless the subject is admin.
- Cancel requests update the task backend and resource supervisor termination reason without marking a formal run succeeded.

## Boundary Guarantees

Runtime flags in API status explicitly report:

```json
{
  "formal_backtest_api_started": true,
  "resource_controls_started": true,
  "quant_lab_started": false,
  "evidence_agent_started": false,
  "worker_loop_started": false,
  "real_provider_calls_started": false,
  "real_llm_calls_started": false,
  "qlib_runtime_started": false,
  "legacy_signal_evaluation_started": false
}
```

The module import-boundary test confirms `backtest_api.py` does not import FastAPI, Qlib, Celery, Redis, SQLAlchemy, LiteLLM, legacy `api.`, `bot.`, `data_provider`, or DSA stock/LLM service modules.

## Non-Goals

- No FastAPI router registration in this task.
- No Quant Lab UI.
- No Evidence Agent, citation validator, report agent or model budget execution.
- No full Worker loop, Celery/Redis consumption, process spawning or real child execution.
- No real Provider, real LLM or external network call.
- No Qlib runtime initialization or `qlib.init`.
- No legacy DSA `/api/v1/backtest/*` Signal Evaluation route/schema changes.
- No promotion of Qlib internal evidence, Dataset conversion artifacts, Screen results or AlphaSift T+N evaluation as formal portfolio backtest output.

## Verification

| Check | Result |
|---|---|
| Red target | `uv run --extra core --extra dev python -m pytest tests/application/test_backtest_api.py -q` initially failed with `ModuleNotFoundError: No module named 'serenity_alpha_lab.application.backtest_api'` |
| Focused target | `uv run --extra core --extra dev python -m pytest tests/application/test_backtest_api.py -q` -> `7 passed` |
| Related suite | `uv run --extra core --extra dev python -m pytest tests/application/test_backtest_api.py tests/application/test_backtest_run_orchestration.py tests/application/test_backtest_resource_control.py tests/quant/test_backtest_golden_property.py tests/quant/test_backtest_artifact.py tests/architecture/test_architecture_boundaries.py -q` -> `37 passed` |
| Full suite | `uv run --extra core --extra dev python -m pytest -q` -> `402 passed, 3 skipped` |
| Compile smoke | `uv run --extra core --extra dev python -m compileall -q src/serenity_alpha_lab tests` -> PASS |
| Dependency lock | `scripts/verify-python-dependency-lock.sh` -> PASS with `Resolved 298 packages` |
| DSA patch check | `scripts/apply-dsa-baseline-patches.sh --check-only` -> `0001..0005` already applied |
| Immutable tag | `git rev-parse upstream/dsa-v3.26.1` -> `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a` |
| Diff hygiene | `git diff --check` -> PASS |

## Scope Guard

This record approves the formal API facade as input to `SAL-P4-021` Quant Lab only. Gate G4 is still not passed; later work must still implement Quant Lab and Gate review before any formal portfolio backtest result can feed Evidence Agent or downstream reports.
