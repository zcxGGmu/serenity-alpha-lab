# Run / Stage / Event 领域模型记录

> Task: `SAL-P1-006` 实现 Run/Stage/Event 领域模型<br>
> Date: 2026-07-20<br>
> Scope: Pure domain lifecycle model only; no persistence, TaskBackend, ArtifactStore, Trace middleware, Quant Core, PIT Dataset, or formal backtest implementation.

## Summary

`src/serenity_alpha_lab/domain/run_lifecycle.py` defines the first durable execution lifecycle model for later Artifact, TaskBackend, Trace, and worker recovery work.

## Model

| Type | Role |
|---|---|
| `Run` | Root aggregate for one deterministic or research execution attempt. |
| `Stage` | Named unit of work within a run; each retry creates a new run attempt rather than mutating the failed run. |
| `RunEvent` | Append-only audit/event record with monotonic per-run `sequence`. |
| `RunStatus` / `StageStatus` | Explicit active and terminal states. |
| `EventKind` | Stable event taxonomy for lifecycle and informational events. |
| `InvalidTransition` | Raised for illegal terminal-state rollback or invalid stage operations. |
| `IdempotencyConflict` | Raised when the same idempotency key is reused for a different run request. |

## Rules

- A run starts in `RUNNING` and emits `run.started` with sequence `1`.
- Events are append-only; public accessors return tuples, and every new event receives the next sequence.
- Terminal runs (`completed`, `failed`, `cancelled`) cannot start stages, fail again, complete again, or otherwise move back to active state.
- Stages can complete or fail only from `running`.
- Completing a run is rejected while any stage is still running.
- Retry is explicit: only failed/cancelled runs can create a new run with `attempt + 1`, `parent_run_id`, the same `run_type`, and the same idempotency key.
- Idempotency compares `idempotency_key + run_type`; same key with different run type raises a conflict.

## Verification

- `tests/domain/test_run_lifecycle.py` covers append-only monotonic event IDs, terminal transition rejection, retry attempt creation, and idempotency conflict detection.
- Architecture tests continue to enforce that the domain package does not import FastAPI, SQLAlchemy, Pandas, Qlib, LiteLLM, AKShare, repositories, services, or integrations.
