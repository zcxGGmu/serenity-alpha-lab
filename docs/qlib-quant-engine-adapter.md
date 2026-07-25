# Qlib QuantEngine Adapter

> Task: `SAL-P4-007` Qlib QuantEngine Adapter
> Date: 2026-07-25
> Status: `APPROVED FOR ENGINE ADAPTER EVIDENCE ONLY`

## Conclusion

`SAL-P4-007` adds the Qlib QuantEngine Adapter boundary:

```text
src/serenity_alpha_lab/integrations/qlib/quant_engine_adapter.py
tests/integrations/test_qlib_quant_engine_adapter.py
```

The adapter wraps four engine operations: `train`, `predict`, `backtest` and
`evaluate_factor`. Each operation builds a controlled config record from
platform `BacktestSpec`, Dataset-to-Qlib conversion artifacts, runtime policy
and platform trace context, calls an injected Qlib facade, maps Qlib Recorder
metadata, and publishes compact deterministic evidence artifacts.

This task does not start a formal portfolio backtest. Qlib internal backtest
evidence remains `engine_scope=qlib_quant_engine_adapter` until later P4 tasks
create orders, executions, ledger, fees, risk, metrics and audit outputs.

## Controlled Templates

`QlibQuantEngineConfig` accepts only approved template IDs:

| Template | Purpose |
|---|---|
| `lightgbm_daily_rebalance@1.0.0` | Controlled daily-rebalance model/research template |
| `linear_factor_evaluation@1.0.0` | Controlled factor evaluation template |

The config validator rejects caller-provided arbitrary Python module path fields
such as `module_path`, `module`, `class`, `class_name` and `import_path`.
Unknown template IDs are rejected before any facade call.

## Worker Boundary

`QlibQuantEngineAdapter` requires:

- persisted `run_id`, `stage_id` and `trace_id`
- concrete `BacktestSpec.spec_hash`
- concrete Dataset Versions from `BacktestSpec.dataset`
- `QlibDatasetConversionArtifacts` from `SAL-P4-006`
- `QlibRuntimeIsolationPolicy` with `allow_arbitrary_module_path=False`

The module imports no Qlib runtime at import time. `LazyQlibQuantEngineFacade`
uses `importlib.import_module("qlib")` only inside method bodies and still
requires a dedicated Quant Worker runner for real execution. Contract tests use
an injected fake facade, so default CI does not install, initialize or run Qlib.

## Recorder Mapping

Each operation maps Qlib Recorder-like output into `QlibRecorderSnapshot`:

- `experiment_id`
- `recorder_id`
- `uri`
- tags augmented with `platform_run_id`, `platform_stage_id`,
  `platform_trace_id` and `backtest_spec_hash`

Recorder is engine evidence only. Platform `Run/Stage/Event`, `BacktestSpec`
and later `BacktestArtifact` remain authoritative.

## Output Artifacts

| Artifact | Schema | Content type | Contents |
|---|---|---|---|
| Step evidence | `integration.qlib.quant_engine_step@1.0.0` | `application/vnd.serenity.integration.qlib.quant-engine-step+json` | One operation, controlled config, Dataset conversion descriptors, Recorder snapshot, facade output summary and runtime scope flags |
| Run report | `integration.qlib.quant_engine_run_report@1.0.0` | `application/vnd.serenity.integration.qlib.quant-engine-run-report+json` | Compact list of operation artifacts, output hashes, Recorder mappings and platform trace context |

Both artifacts set:

```json
{
  "engine_scope": "qlib_quant_engine_adapter",
  "runtime": {
    "formal_portfolio_backtest_started": false,
    "ledger_started": false,
    "risk_started": false,
    "worker_loop_started": false
  }
}
```

## Non-Goals

- No formal portfolio backtest run.
- No order generation, fill matching, Portfolio Ledger, fees/slippage, A-share
  execution rules, corporate-action ledger, RiskPolicy, metrics or audit.
- No Quant Lab, Evidence Agent, Worker loop, real Provider call or real LLM call.
- No FastAPI/desktop import-time Qlib initialization.
- No legacy `/api/v1/backtest/*` changes.

Legacy DSA Signal Evaluation, AlphaSift T+N evaluation, Screen result and
Dataset conversion artifacts remain outside the formal portfolio backtest
namespace.

## Verification

| Check | Result |
|---|---|
| Red target | `uv run --extra core --extra dev python -m pytest tests/integrations/test_qlib_quant_engine_adapter.py -q` initially failed with `ModuleNotFoundError: serenity_alpha_lab.integrations.qlib.quant_engine_adapter` |
| Focused target | `4 passed` |
| Related suite | `23 passed` across Qlib Adapter/Conversion/Isolation, BacktestSpec and BacktestArtifact |
| Full suite | `347 passed, 3 skipped` |
| Compile | `uv run --extra core --extra dev python -m compileall -q src tests` PASS |
| Dependency lock | `scripts/verify-python-dependency-lock.sh` PASS, `Resolved 298 packages` |
| DSA patches | `scripts/apply-dsa-baseline-patches.sh --check-only` PASS, patches `0001` through `0005` already applied |
| Immutable upstream tag | `upstream/dsa-v3.26.1` remained `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a` |
| Runtime boundary | AST import guard confirms adapter imports no `qlib`, `pyqlib`, `fastapi` or `sqlalchemy` |

## Scope Guard

`SAL-P4-008` can now implement the order state machine. Subsequent P4 tasks
must still implement Ledger, costs, A-share execution rules, corporate actions,
rebalance policies, deterministic RiskPolicy, bias audit and metrics before any
formal portfolio backtest can be promoted or shown in Quant Lab.
