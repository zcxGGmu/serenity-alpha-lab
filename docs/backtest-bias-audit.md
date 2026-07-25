# Backtest Bias Audit

> Task: `SAL-P4-015` backtest bias audit<br>
> Date: 2026-07-26<br>
> Status: `APPROVED FOR SAL-P4-016 METRIC INPUT ONLY`

## Conclusion

`SAL-P4-015` adds a pure deterministic bias-audit layer for formal portfolio backtests:

```text
src/serenity_alpha_lab/quant/backtest/audit.py
tests/quant/test_backtest_bias_audit.py
```

The auditor consumes `BacktestSpec`, explicit point-in-time audit observations and explicit cost-sensitivity scenario summaries. It returns an immutable `BacktestBiasAuditReport` with hard failures, warnings, deterministic report IDs and promotion guards. It does not run a formal portfolio backtest, compute performance metrics, mutate Ledger/Risk, expose API/UI, initialize Qlib or start Worker runtime.

## Contract

| Item | Contract |
|---|---|
| Contract version | `quant.backtest_bias_audit@1.0.0` |
| Schema | `quant.backtest.bias_audit@1.0.0` |
| Auditor version | `cn_a_share_backtest_bias_auditor@1.0.0` |
| Primary spec source | `BacktestSpec` |
| Observation input | `BacktestBiasAuditObservation` |
| Cost input | `CostSensitivityScenario` |
| Report output | `BacktestBiasAuditReport` |

Public DTOs include `BacktestBiasAuditObservation`, `CostSensitivityScenario`, `BacktestBiasAuditPolicy`, `BiasAuditRuleOutcome`, `BacktestBiasAuditReport`, `BacktestBiasAuditStatus`, `BiasAuditRuleStatus` and `BacktestBiasAuditor`.

## Rule Coverage

| Rule ID | Behavior |
|---|---|
| `lookahead_bias` | `block` when any observation uses data with `data_available_at > decision_time` |
| `survivorship_bias` | `block` when universe membership is not `historical_as_of` or `universe_as_of > trade_date` |
| `pit_data_availability` | `block` when PIT availability is missing, later than `decision_time`, or temporal confidence is not `known` |
| `sample_overlap` | `warn` when strategy/return sample overlap is below policy minimum; optional hard threshold can block |
| `cost_sensitivity` | `warn` or `block` when cost-scenario return degradation exceeds configured thresholds |

`not_evaluable` outcomes are treated as invalid because formal backtests cannot be promoted when required audit evidence is absent.

## Promotion Guard

Any hard failure or not-evaluable audit rule sets:

```json
{
  "status": "invalid",
  "eligible_for_ranking": false,
  "agent_strong_conclusion_allowed": false
}
```

Warning-only reports remain eligible but surface `warning_rule_ids`, so later Metric, BacktestRun, API, Quant Lab and Agent tasks can display or gate them explicitly. Invalid reports must not enter strategy leaderboards or Agent strong conclusions.

## Determinism

`BacktestBiasAuditReport.report_id` is derived from canonical JSON of `spec_id`, `spec_hash`, run/stage, policy record, status and ordered rule outcomes. Identical inputs produce identical report records. Decimal values are preserved internally and stringified in `to_record()`.

## Non-Goals

- No formal portfolio backtest run.
- No performance metric calculation, returns series generation, benchmark calculation or Metric Registry.
- No order execution, fill matching, Ledger mutation, corporate-action posting or RiskPolicy mutation.
- No BacktestRun orchestration, resource/cancel/checkpoint handling, API, Quant Lab or Evidence Agent.
- No Worker loop, real Provider call, real LLM call, Qlib runtime import or `qlib.init`.
- No legacy `/api/v1/backtest/*` Signal Evaluation behavior change.

Legacy DSA Signal Evaluation, AlphaSift T+N evaluation, Screen result, Dataset conversion artifacts and Qlib internal evidence remain outside the formal portfolio backtest namespace.

## Verification

| Check | Result |
|---|---|
| Red target | `uv run --extra core --extra dev python -m pytest tests/quant/test_backtest_bias_audit.py -q` initially failed with `ModuleNotFoundError: serenity_alpha_lab.quant.backtest.audit` |
| Focused target | `uv run --extra core --extra dev python -m pytest tests/quant/test_backtest_bias_audit.py -q` -> `3 passed` |
| Related suite | `uv run --extra core --extra dev python -m pytest tests/quant/test_backtest_bias_audit.py tests/quant/test_risk_policy.py tests/quant/test_backtest_spec.py tests/architecture/test_architecture_boundaries.py -q` -> `24 passed` |

Additional full-suite, compile, dependency lock, DSA patch, immutable tag and diff hygiene checks are recorded in `tasks/todo.md` and the progress checklist for `AEV-081`.

## Scope Guard

This record only approves deterministic bias audit as input to `SAL-P4-016` unified performance metrics. Later P4 tasks must still implement metrics, BacktestRun orchestration, resource controls, formal API, Quant Lab and Gate G4 before any formal portfolio backtest can be promoted.
