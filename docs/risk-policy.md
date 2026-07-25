# Deterministic RiskPolicy

> Task: `SAL-P4-014` deterministic RiskPolicy<br>
> Date: 2026-07-26<br>
> Status: `APPROVED FOR SAL-P4-015 BIAS AUDIT INPUT ONLY`

## Conclusion

`SAL-P4-014` adds a pure deterministic RiskPolicy layer for formal portfolio backtests:

```text
src/serenity_alpha_lab/quant/backtest/risk.py
tests/quant/test_risk_policy.py
```

The evaluator consumes `BacktestSpec`, `PortfolioLedger`, optional `RebalancePlan`, explicit instrument risk profiles and high-water-mark equity. It returns immutable pass/warn/block/not-evaluable rule outcomes and an overall decision. It does not execute orders, mutate the Ledger, calculate metrics, run bias audit, expose API/UI, initialize Qlib or start a formal portfolio backtest.

## Contract

| Item | Contract |
|---|---|
| Contract version | `quant.risk_policy@1.0.0` |
| Schema | `quant.backtest.risk_policy@1.0.0` |
| Evaluator version | `cn_a_share_deterministic_risk_policy@1.0.0` |
| Primary rule source | `BacktestRiskSpec` |
| Portfolio input | `PortfolioLedger` |
| Planned portfolio input | `RebalancePlan` target weights and planned buy/sell notionals |
| Explicit risk inputs | `InstrumentRiskProfile` and high-water-mark equity |

Public DTOs include `DeterministicRiskPolicy`, `InstrumentRiskProfile`, `RiskRuleOutcome`, `RiskPolicyResult`, `RiskDecisionStatus`, `RiskRuleStatus` and `RiskPolicyEvaluator`.

## Rule Coverage

| Rule ID | Status behavior |
|---|---|
| `risk_profile_available` | `not_evaluable` when any target instrument lacks a profile; this blocks the overall result |
| `max_weight_per_instrument` | `block` when target or current weight exceeds `BacktestRiskSpec.max_weight_per_instrument` |
| `max_weight_per_industry` | `block` when summed industry weight exceeds `BacktestRiskSpec.max_weight_per_industry` |
| `style_exposure:<style>` | `warn` or `block` when absolute weighted style exposure exceeds policy limits |
| `liquidity_floor` | `block` when average daily amount is below `BacktestRiskSpec.liquidity_floor_amount` |
| `max_turnover_per_rebalance` | `block` when planned buy + sell notional divided by equity exceeds `BacktestRiskSpec.max_turnover_per_rebalance` |
| `max_drawdown` | `block` when drawdown from explicit high-water mark exceeds `DeterministicRiskPolicy.max_drawdown_pct` |

`not_evaluable` is deliberately treated as a blocking condition in the overall `RiskPolicyResult.status`. The result explicitly sets `agent_override_allowed=false`; later UI or Agent flows may explain the block or request a new rule-version rerun, but cannot override the deterministic gate.

## Determinism

`RiskPolicyResult.result_id` is derived from canonical JSON of `spec_id`, `spec_hash`, run/stage, policy record, final status and ordered rule outcomes. Re-evaluating identical inputs produces identical result records. `Decimal` values remain exact internally and are stringified in `to_record()`.

## Non-Goals

- No formal portfolio backtest run.
- No order execution, fill matching, Ledger mutation or corporate-action posting.
- No performance metrics, bias audit, BacktestRun orchestration, resource/cancel/checkpoint handling, API, Quant Lab or Evidence Agent.
- No Worker loop, real Provider call, real LLM call, Qlib runtime import or `qlib.init`.
- No legacy `/api/v1/backtest/*` Signal Evaluation behavior change.

Legacy DSA Signal Evaluation, AlphaSift T+N evaluation, Screen result, Dataset conversion artifacts and Qlib internal evidence remain outside the formal portfolio backtest namespace.

## Verification

| Check | Result |
|---|---|
| Red target | `uv run --extra core --extra dev python -m pytest tests/quant/test_risk_policy.py -q` initially failed with `ModuleNotFoundError: serenity_alpha_lab.quant.backtest.risk` |
| Focused target | `uv run --extra core --extra dev python -m pytest tests/quant/test_risk_policy.py -q` -> `4 passed` |
| Related suite | `uv run --extra core --extra dev python -m pytest tests/quant/test_risk_policy.py tests/quant/test_rebalance_target_weights.py tests/quant/test_a_share_execution_rules.py tests/quant/test_cost_slippage_model.py tests/quant/test_portfolio_ledger.py tests/quant/test_order_state_machine.py tests/quant/test_backtest_spec.py tests/architecture/test_architecture_boundaries.py -q` -> `43 passed` |
| Full suite | `uv run --extra core --extra dev python -m pytest -q` -> `376 passed, 3 skipped` |
| Compile | `uv run --extra core --extra dev python -m compileall -q src tests` -> PASS |
| Dependency lock | `scripts/verify-python-dependency-lock.sh` -> PASS with `Resolved 298 packages` |
| DSA patches | `scripts/apply-dsa-baseline-patches.sh --check-only` -> patches `0001..0005` already applied |
| Immutable upstream tag | `git rev-parse upstream/dsa-v3.26.1` -> `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a` |

## Scope Guard

This record only approves deterministic RiskPolicy evaluation as input to `SAL-P4-015` bias audit. Later P4 tasks must still implement bias audit, unified performance metrics, BacktestRun orchestration, resource controls, formal API, Quant Lab and Gate G4 before any formal portfolio backtest can be promoted.
