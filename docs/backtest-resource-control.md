# Backtest Resource Control

> Task: `SAL-P4-018` resource limits, cancellation and checkpoint<br>
> Date: 2026-07-26<br>
> Status: `APPROVED FOR SAL-P4-019 GOLDEN TEST INPUT ONLY`

## Conclusion

`SAL-P4-018` adds a pure application-layer BacktestRun resource supervisor:

```text
src/serenity_alpha_lab/application/backtest_resource_control.py
tests/application/test_backtest_resource_control.py
```

The supervisor records resource policy, isolated child-process snapshots,
cooperative cancellation, wall-clock timeout classification, OOM classification
and checkpoint artifacts. A successful child snapshot delegates to the existing
`BacktestRunOrchestrator.finalize()` contract. Timeout, cancellation, OOM and
failed child-process states publish explicit partial checkpoints and never
create a `BacktestRunStatus.SUCCEEDED` finalization record.

This task does not expose formal API routes, start Quant Lab, start Evidence
Agent, start Worker loop, call real Providers, call real LLMs, initialize Qlib
runtime or change legacy DSA `/api/v1/backtest/*` Signal Evaluation behavior.

## Contract

| Item | Contract |
|---|---|
| Contract version | `application.backtest_resource_control@1.0.0` |
| Supervisor version | `cn_a_share_backtest_resource_supervisor@1.0.0` |
| Checkpoint schema | `quant.backtest_run_checkpoint@1.0.0` |
| Checkpoint content type | `application/vnd.serenity.quant.backtest-run-checkpoint+json` |
| Default queue | `worker-quant` |
| Isolation mode | `dedicated_process` |

Public DTOs include `BacktestRunResourcePolicy`,
`BacktestRunChildProcessSnapshot`, `BacktestRunChildProcessStatus`,
`BacktestRunExecutionStatus`, `BacktestRunCheckpoint`,
`BacktestRunExecutionRecord`, `InMemoryBacktestRunExecutionRepository` and
`BacktestRunResourceSupervisor`.

## Resource Policy

The default `BacktestRunResourcePolicy` is derived from ADR-009
`QlibRuntimeIsolationPolicy` without importing or initializing Qlib runtime:

| Field | Default |
|---|---:|
| `queue_name` | `worker-quant` |
| `process_isolation` | `dedicated_process` |
| `max_cpu_cores` | `2` |
| `max_memory_mb` | `4096` |
| `wall_clock_timeout_seconds` | `3600` |
| `heartbeat_interval_seconds` | `15` |
| `checkpoint_interval_seconds` | `300` |
| `max_output_bytes` | `536870912` |

The policy is a contract for later Worker/API tasks. `SAL-P4-018` itself does
not start a Worker loop or spawn Qlib.

## Supervisor Semantics

`BacktestRunResourceSupervisor.start()` stores a non-blocking execution record
for a supplied `BacktestRunRequest`. Later `observe()` calls accept a compact
`BacktestRunChildProcessSnapshot` from an isolated child process boundary.

Observed outcomes:

| Child state | Platform execution state | Finalization |
|---|---|---|
| `succeeded` | `succeeded` | delegates to `BacktestRunOrchestrator.finalize()` |
| running past timeout | `timed_out` | checkpoint only, no succeeded final record |
| cancel requested | `cancelled` | checkpoint only, termination requested |
| `oom_killed` | `oom_killed` | checkpoint only, no succeeded final record |
| `failed` | `failed` | checkpoint only, no succeeded final record |

This keeps the API contract non-blocking: API tasks can submit and observe
compact state later, while heavy computation remains outside the API process.

## Checkpoints

Checkpoint artifacts include:

- run, trace and idempotency identifiers
- process id, current stage, progress and observed time
- status and reason (`timeout`, `user_requested_cancel`, `oom_killed`, etc.)
- resource policy and observed resource usage
- partial output artifact IDs when available
- `artifact_state=partial` for timeout, cancel, OOM and failure paths
- resume hint: `resume.next_allowed_stage_id`
- runtime boundary flags proving no API route, Worker loop, Provider, LLM or
  Qlib runtime started in this task

Partial checkpoints are intentionally separate from successful BacktestRun
summary artifacts. They are audit/recovery evidence, not formal successful
portfolio backtest results.

## Non-Goals

- No `/api/v1/quant/backtest-runs` create/status/artifact/cancel routes.
- No Worker loop, Celery task handler, Redis queue consumption or process
  spawning implementation.
- No Quant Lab UI.
- No Evidence Agent, report agent, citation validation or model budgeting.
- No real Provider, real LLM or external network call.
- No Qlib runtime initialization or `qlib.init`.
- No change to legacy DSA Signal Evaluation routes, schemas or naming.

Legacy DSA Signal Evaluation, AlphaSift T+N evaluation, Screen results, Qlib
internal evidence and Dataset conversion artifacts remain outside the formal
portfolio backtest namespace.

## Verification

| Check | Result |
|---|---|
| Red target | `uv run --extra core --extra dev python -m pytest tests/application/test_backtest_resource_control.py -q` initially failed with `ModuleNotFoundError: serenity_alpha_lab.application.backtest_resource_control` |
| Focused target | `uv run --extra core --extra dev python -m pytest tests/application/test_backtest_resource_control.py -q` -> `5 passed` |
| Related suite | `uv run --extra core --extra dev python -m pytest tests/application/test_backtest_resource_control.py tests/application/test_backtest_run_orchestration.py tests/integrations/test_qlib_quant_engine_adapter.py tests/repositories/test_persistent_task_backend.py tests/services/test_task_event_stream.py tests/quant/test_backtest_artifact.py tests/architecture/test_architecture_boundaries.py -q` -> `43 passed` |
| Full suite | `uv run --extra core --extra dev python -m pytest -q` -> `391 passed, 3 skipped` |
| Compile | `uv run --extra core --extra dev python -m compileall -q src/serenity_alpha_lab tests` -> PASS |
| Lock guard | `scripts/verify-python-dependency-lock.sh` -> PASS, `Resolved 298 packages` |
| DSA patches | `scripts/apply-dsa-baseline-patches.sh --check-only` -> `0001..0005` already applied |
| Immutable tag | `git rev-parse upstream/dsa-v3.26.1` -> `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a` |
| Diff hygiene | `git diff --check` -> PASS |

## Scope Guard

This record only approves resource-control and checkpoint artifacts as input to
`SAL-P4-019` golden/property tests. Later tasks must still implement fixed
formal backtest goldens, formal API routes, Quant Lab and Gate G4 before formal
portfolio backtests can be promoted beyond this contract.
