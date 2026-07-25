# ADR-009: Qlib Adapter Boundary And Version Upgrade Strategy

> Status: Approved<br>
> Date: 2026-07-25<br>
> Related tasks: `SAL-P4-005`, `SAL-P4-006`, `SAL-P4-007`, `SAL-P4-017`, `SAL-P4-018`, Gate G4<br>
> Review by: Gate G4 or the first Qlib upgrade request, whichever comes first

## Context

P4 has frozen formal `BacktestSpec` and `BacktestArtifact` contracts, but the project has not yet converted Serenity Dataset Versions into Qlib input files, initialized Qlib runtime, or run formal portfolio backtests. Qlib is a heavy quant stack with global initialization behavior, experiment state, optional data workflows, and runtime dependencies such as `mlflow`, `redis`, `pymongo`, `lightgbm`, `cvxpy`, `jupyter`, and `matplotlib`.

FastAPI, Desktop core, domain, application, datasets, provider, reports, and DSA compatibility paths must stay free of Qlib global state. The only acceptable direction is an isolated Quant Worker Adapter that receives platform `run_id` / `stage_id` context and writes compact platform Artifacts.

## Decision

Serenity Alpha Lab will lock Qlib as:

```text
pyqlib==0.9.7
```

Qlib is approved only for the optional `quant` extra and a dedicated Quant Worker process. It is not approved for FastAPI import-time initialization, Desktop core installation, DSA runtime compatibility facades, or arbitrary Python module path loading from API/UI/config payloads.

The Qlib boundary is:

```text
BacktestSpec
  -> SAL-P4-006 Dataset-to-Qlib converter
  -> SAL-P4-007 Qlib Adapter in Quant Worker
  -> BacktestArtifact descriptors and ArtifactStore manifests
```

The platform `Run/Stage/Event` and later resource/cancel/checkpoint layer remain authoritative. Qlib Recorder may be used as internal engine evidence, but it is not the platform run authority.

## Worker Boundary

The default policy is encoded in `src/serenity_alpha_lab/integrations/qlib/runtime_policy.py`; these resource limits are policy defaults, not proof that a Qlib runtime run has occurred:

| Field | Value |
|---|---|
| Package | `pyqlib==0.9.7` |
| Runtime scope | `quant_worker_only` |
| Queue | `worker-quant` |
| Process isolation | `dedicated_process` |
| Resource limits | `2` CPU cores, `4096` MB memory, `3600` second wall-clock timeout |
| Heartbeat/checkpoint | `15` second heartbeat, `300` second checkpoint interval |

Rules:

1. FastAPI must not import or initialize Qlib.
2. Domain/application/datasets/provider/report paths must not import Qlib.
3. Adapter code must lazy import Qlib inside the Quant Worker execution boundary.
4. API/UI/config input must not accept arbitrary Python module path.
5. Worker execution must require persisted `run_id`, `stage_id`, `trace_id`, concrete Dataset Version and `BacktestSpec.spec_hash`.
6. Cancellation, heartbeat, timeout and checkpoint behavior belongs to `SAL-P4-018`; this ADR only freezes the required policy.

## Version And Platform Policy

`pyqlib 0.9.7` is MIT licensed and publishes CPython 3.11/3.12 wheels for macOS universal2, manylinux2014 x86_64 and Windows amd64. Production Quant Worker images are initially Linux x86_64 only; macOS is for local development, and Windows remains non-default until later Worker/profile validation.

`requirements.txt` must continue to exclude `pyqlib`; only `uv run --extra quant` or the future Quant Worker image may install it.

## Upgrade Strategy

Any Qlib upgrade must be treated as a controlled dependency and engine behavior change:

1. Pin the exact new `pyqlib==x.y.z` version.
2. Record wheel hashes, license metadata, direct dependency diff, Python/platform classifiers and any removed wheels.
3. Refresh `uv.lock` and prove production/Desktop requirements still exclude Qlib.
4. Generate or refresh Quant Worker SBOM, license inventory and vulnerability report.
5. Re-run fixed-data golden tests for Dataset conversion, Qlib Adapter, prediction hash, orders, equity curve, metrics and audit Artifact tolerances.
6. Re-run resource tests covering timeout, OOM, cancellation, checkpoint and retry.
7. Record the upgrade in the decision/evidence registers before Gate approval.

## Stop-Use Conditions

These stop-use conditions block Qlib usage or release promotion until fixed or formally waived.

Stop Qlib usage or block the release if any condition holds:

- Qlib enters FastAPI startup/import path.
- Qlib enters domain, application, datasets or provider modules.
- Qlib config accepts arbitrary Python module path.
- `pyqlib` appears in production/Desktop `requirements.txt`.
- Qlib output bypasses `BacktestSpec`, `BacktestArtifact`, Dataset Version, Run/Stage/Event or ArtifactStore.
- License, vulnerability, platform or resource risks cannot be fixed or waived before Gate G4/G6.
- Qlib, legacy Signal Evaluation, AlphaSift T+N evaluation or Screen result is misrepresented as formal portfolio backtest evidence without the P4 formal contract chain.

## Alternatives Considered

### Import Qlib Directly In FastAPI

Rejected. It risks global state contamination, heavy dependency load, slower startup, harder cancellation, and API outages during quant jobs.

### Keep Qlib As A CLI Sidecar With Loose Files

Rejected. It weakens `Run/Stage/Event`, Dataset Version, ArtifactStore and resource control. The worker can use subprocess/process isolation later, but still needs platform authority and typed Artifacts.

### Dedicated Quant Worker Adapter

Accepted. It matches the development plan and ADR-002 service split criteria, keeping the core product responsive while allowing Qlib to be swapped or upgraded behind a protocol.

## Consequences

- P4 can proceed to `SAL-P4-006` Dataset conversion without starting Qlib runtime.
- Qlib dependency weight is contained to the `quant` extra and future Quant Worker image.
- Later implementation must add stronger adapter/golden/resource tests before any formal portfolio backtest run can be trusted.
- The platform must maintain its own `BacktestSpec`, `BacktestArtifact`, ledger, risk, metric and audit authority instead of deferring those semantics entirely to Qlib.

## Rollback

If Qlib integration causes startup, dependency, resource or correctness regressions:

1. Disable the Quant Worker Qlib adapter feature flag.
2. Keep `BacktestSpec` and `BacktestArtifact` records intact; mark affected runs invalid or partial with errors.
3. Revert only Qlib adapter/converter changes, not the formal contract definitions.
4. Re-run dependency lock guard, architecture tests, fixed-data goldens and status-anchor checks.
5. Record rollback evidence in `docs/development-progress-checklist.md` and `docs/development-status.md`.

## Verification Requirements

Before this ADR is considered satisfied:

- `pyproject.toml` pins `pyqlib==0.9.7` under `quant`.
- `requirements.txt` excludes `pyqlib`.
- `tests/architecture/test_qlib_version_isolation.py` passes.
- `uv lock --check` and `scripts/verify-python-dependency-lock.sh` pass.
- No Qlib runtime is started by `SAL-P4-005`.
