# BacktestRun Orchestration

> Task: `SAL-P4-017` BacktestRun orchestration<br>
> Date: 2026-07-26<br>
> Status: `APPROVED FOR SAL-P4-018 RESOURCE CONTROL INPUT ONLY`

## Conclusion

`SAL-P4-017` adds a pure BacktestRun finalization and orchestration use case:

```text
src/serenity_alpha_lab/application/backtest_run.py
tests/application/test_backtest_run_orchestration.py
```

The use case validates one formal portfolio backtest chain: `BacktestSpec`,
Qlib/strategy engine evidence, `PortfolioLedger`, `RiskPolicyResult`,
`BacktestBiasAuditReport`, `BacktestPerformanceMetricReport` and
`BacktestArtifactBundle`. It creates deterministic `Run` / `Stage` lifecycle
records, publishes a compact BacktestRun summary Artifact and enforces
idempotency/reuse plus dirty-code formal-run guardrails.

This task finalizes supplied deterministic outputs. It does not launch Qlib,
generate orders, execute fills, mutate the Ledger, re-run Risk/Audit/Metrics,
expose API routes, build Quant Lab, start Worker loop, implement resource
controls, call real Providers or call real LLMs.

## Contract

| Item | Contract |
|---|---|
| Contract version | `application.backtest_run_orchestrator@1.0.0` |
| Summary schema | `quant.backtest_run@1.0.0` |
| Summary content type | `application/vnd.serenity.quant.backtest-run+json` |
| Orchestrator version | `cn_a_share_backtest_run_orchestrator@1.0.0` |
| Run type | `formal_portfolio_backtest` |
| Repository | `InMemoryBacktestRunRepository` for deterministic contract/local use |

Public DTOs include `BacktestRunRequest`, `BacktestRunRecord`,
`BacktestRunStageRecord`, `BacktestRunMode`, `BacktestRunCodeState`,
`BacktestRunStatus`, `BacktestRunOrchestrator` and
`InMemoryBacktestRunRepository`.

## Stage Chain

BacktestRun finalization records these stages in order:

| Stage | Input authority |
|---|---|
| `spec` | `BacktestSpec.spec_hash`, concrete Dataset versions and Dataset hashes |
| `engine` | Qlib/strategy engine evidence with platform `run_id`, `trace_id` and `spec_hash` |
| `ledger` | `PortfolioLedger` replay/accounting snapshot |
| `risk` | deterministic `RiskPolicyResult` |
| `audit` | deterministic `BacktestBiasAuditReport` |
| `metrics` | deterministic `BacktestPerformanceMetricReport` |
| `artifacts` | URI-only `BacktestArtifactBundle` descriptors |
| `summary` | compact BacktestRun summary Artifact |

Every layer must bind the same `spec_id`, `spec_hash` and `run_id`. The
artifact bundle must also match the exact Dataset versions from the spec.
Engine evidence may reference Qlib Adapter records, but Qlib Recorder is only
engine evidence; platform Run/Stage/Event, Spec, Ledger, Risk, Audit, Metrics
and Artifact descriptors remain authoritative.

## Idempotency And Reuse

`BacktestRunOrchestrator.finalize()` derives:

- `request_hash`: canonical hash of the submitted request identity.
- `reuse_key`: canonical hash of `spec_hash + dataset_hashes + engine_version + effective_mode + code_state + patch_hash`.

The same `Idempotency-Key` with the same request returns the same record. The
same key with a different request is rejected. A later request with a different
idempotency key but the same successful reuse key returns the existing
successful run as a reused record instead of creating a duplicate run.

## Dirty-Code Policy

Formal requests require clean code. If `code_state=dirty` and no patch hash is
provided, the request is rejected before finalization. If dirty code includes a
concrete `sha256:*` patch hash, the effective mode is downgraded to `preview`,
`dirty_code_downgraded_to_preview` is recorded, and the run is not eligible for
ranking.

## Promotion Guards

A BacktestRun is ranking-eligible only when all conditions hold:

- Effective mode is `formal`.
- Code state is `clean`.
- RiskPolicy status is not `block`.
- BiasAudit status is not `invalid` and is ranking-eligible.
- BacktestArtifactBundle state is `formal`.
- All records bind the same formal Spec/run context.

Risk blocks, invalid bias audits and non-formal artifact bundles prevent formal
promotion. Later API/UI/Agent tasks must surface those states instead of
overriding them.

## Non-Goals

- No `SAL-P4-018` resource limits, cancel handling, checkpointing, timeout or
  OOM behavior.
- No `/api/v1/quant/backtest-runs` route, status endpoint, artifact query or
  pagination.
- No Quant Lab, Evidence Agent, Worker loop, real Provider call or real LLM call.
- No Qlib runtime initialization, `qlib.init` or arbitrary module path loading.
- No mutation of prior Ledger/Risk/Audit/Metrics outputs.
- No legacy `/api/v1/backtest/*` Signal Evaluation behavior change.

Legacy DSA Signal Evaluation, AlphaSift T+N evaluation, Screen results, Qlib
internal evidence and Dataset conversion artifacts remain outside the formal
portfolio backtest namespace.

## Verification

| Check | Result |
|---|---|
| Red target | `uv run --extra core --extra dev python -m pytest tests/application/test_backtest_run_orchestration.py -q` initially failed with `ModuleNotFoundError: serenity_alpha_lab.application.backtest_run` |
| Focused target | `uv run --extra core --extra dev python -m pytest tests/application/test_backtest_run_orchestration.py -q` -> `4 passed` |
| Related suite | `uv run --extra core --extra dev python -m pytest tests/application/test_backtest_run_orchestration.py tests/integrations/test_qlib_quant_engine_adapter.py tests/quant/test_backtest_artifact.py tests/quant/test_backtest_performance_metrics.py tests/quant/test_backtest_bias_audit.py tests/quant/test_risk_policy.py tests/quant/test_portfolio_ledger.py tests/quant/test_backtest_spec.py tests/architecture/test_architecture_boundaries.py -q` -> `41 passed` |

Full-suite, compile, dependency lock, DSA patch, immutable tag and diff hygiene
checks are recorded in `tasks/todo.md` and the progress checklist for
`AEV-083`.

## Scope Guard

This record only approves BacktestRun finalization as input to `SAL-P4-018`
resource limits, cancellation and checkpointing. Later P4 tasks must still
implement resource controls, fixed backtest goldens, formal API, Quant Lab and
Gate G4 before formal portfolio backtests can be promoted beyond this contract.
