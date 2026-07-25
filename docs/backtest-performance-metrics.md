# Backtest Performance Metrics

> Task: `SAL-P4-016` unified performance metrics<br>
> Date: 2026-07-26<br>
> Status: `APPROVED FOR SAL-P4-017 BACKTESTRUN INPUT ONLY`

## Conclusion

`SAL-P4-016` adds a pure deterministic performance metric layer for formal portfolio backtests:

```text
src/serenity_alpha_lab/quant/backtest/metrics.py
tests/quant/test_backtest_performance_metrics.py
```

The calculator consumes an existing `BacktestSpec`, explicit equity/benchmark points, turnover observations, closed trade outcomes, `CostBreakdown` records and industry exposure points. It returns an immutable `BacktestPerformanceMetricReport` with formula versions, sample metadata and JSON-friendly metric sections. It does not start a formal portfolio backtest, orchestrate `BacktestRun`, mutate Ledger/Risk/Audit, expose API/UI, initialize Qlib or start Worker runtime.

## Contract

| Item | Contract |
|---|---|
| Contract version | `quant.backtest_performance_metrics@1.0.0` |
| Schema | `quant.backtest.performance_metrics@1.0.0` |
| Engine version | `cn_a_share_performance_metric_calculator@1.0.0` |
| Metric set version | `backtest_performance_metrics@1.0.0` |
| Primary spec source | `BacktestSpec` |
| Output | `BacktestPerformanceMetricReport` |

Public DTOs include `BacktestPerformanceMetricPolicy`, `BacktestMetricRegistry`, `BacktestMetricDefinition`, `BacktestEquityPoint`, `BacktestTurnoverObservation`, `BacktestTradeOutcome`, `BacktestIndustryExposurePoint`, `BacktestPerformanceMetricReport` and `BacktestPerformanceMetricCalculator`.

## Formula Versions

| Metric | Formula version | Formula |
|---|---|---|
| `cumulative_return` | `cumulative_return@1.0.0` | `ending_equity / starting_equity - 1` |
| `annualized_return` | `annualized_return@1.0.0` | `(1 + cumulative_return) ** (annualization_days / period_count) - 1` |
| `annualized_volatility` | `annualized_volatility@1.0.0` | sample stdev of period returns times `sqrt(annualization_days)` |
| `sharpe_ratio` | `sharpe_ratio@1.0.0` | `(annualized_return - risk_free_rate) / annualized_volatility` |
| `sortino_ratio` | `sortino_ratio@1.0.0` | `(annualized_return - risk_free_rate) / annualized downside deviation` |
| `max_drawdown` | `max_drawdown@1.0.0` | maximum running peak-to-trough equity loss |
| `calmar_ratio` | `calmar_ratio@1.0.0` | `annualized_return / max_drawdown` |
| `win_rate` | `win_rate@1.0.0` | profitable closed trades divided by closed trade count |
| `profit_loss_ratio` | `profit_loss_ratio@1.0.0` | average winning trade divided by absolute average losing trade |
| `turnover_rate` | `turnover_rate@1.0.0` | mean `(buy_notional + sell_notional) / equity` |
| `cost_ratio` | `cost_ratio@1.0.0` | total transaction cost divided by gross traded amount |
| `tracking_error` | `tracking_error@1.0.0` | sample stdev of active returns times `sqrt(annualization_days)` |
| `information_ratio` | `information_ratio@1.0.0` | annualized active return divided by tracking error |
| `industry_exposure` | `industry_exposure@1.0.0` | average and maximum supplied industry weights |

The report always records `sample_start`, `sample_end`, frequency, annualization days, risk-free rate, period count and the full `metric_formula_versions` mapping. Third-party report libraries may consume the output series and report records later, but cannot redefine these platform metric formulas.

## Scope Guard

This task computes metrics only from explicit observations supplied by later orchestration. It does not generate returns from a strategy, execute orders, settle cash, mutate `PortfolioLedger`, re-run RiskPolicy or BiasAudit, publish BacktestArtifact bundles, expose `/api/v1/quant/backtest-runs`, start Quant Lab, start Evidence Agent, call real Provider/LLM, import Qlib or change legacy `/api/v1/backtest/*` Signal Evaluation behavior.

Legacy DSA Signal Evaluation, AlphaSift T+N evaluation, Screen result, Dataset conversion artifacts and Qlib internal evidence remain outside the formal portfolio backtest namespace.

## Verification

| Check | Result |
|---|---|
| Red target | `uv run --extra core --extra dev python -m pytest tests/quant/test_backtest_performance_metrics.py -q` initially failed with `ModuleNotFoundError: serenity_alpha_lab.quant.backtest.metrics` |
| Focused target | `uv run --extra core --extra dev python -m pytest tests/quant/test_backtest_performance_metrics.py -q` -> `3 passed` |
| Related suite | `uv run --extra core --extra dev python -m pytest tests/quant/test_backtest_performance_metrics.py tests/quant/test_backtest_bias_audit.py tests/quant/test_risk_policy.py tests/quant/test_cost_slippage_model.py tests/quant/test_portfolio_ledger.py tests/quant/test_backtest_spec.py tests/architecture/test_architecture_boundaries.py -q` -> `34 passed` |
| Full suite | `uv run --extra core --extra dev python -m pytest -q` -> `382 passed, 3 skipped` |
| Compile | `uv run --extra core --extra dev python -m compileall -q src tests` -> PASS |
| Dependency lock | `scripts/verify-python-dependency-lock.sh` -> PASS with `Resolved 298 packages` |
| DSA patches | `scripts/apply-dsa-baseline-patches.sh --check-only` -> patches `0001..0005` already applied |
| Immutable upstream tag | `git rev-parse upstream/dsa-v3.26.1` -> `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a` |
| Diff hygiene | `git diff --check` -> PASS |

## Next Scope

`SAL-P4-017` may now consume `BacktestPerformanceMetricReport` as one input to BacktestRun orchestration. BacktestRun must still wire Spec, Qlib/strategy evidence, orders, Ledger, RiskPolicy, BiasAudit, Metrics and Artifact descriptors before any result can be promoted as a formal portfolio backtest.
