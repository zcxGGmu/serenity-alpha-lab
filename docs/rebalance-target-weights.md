# Rebalance And Target Weights

> Task: `SAL-P4-013` rebalance and target weights<br>
> Date: 2026-07-25<br>
> Status: `APPROVED FOR SAL-P4-014 RISKPOLICY INPUT ONLY`

## Conclusion

`SAL-P4-013` adds a pure deterministic rebalance planning layer for formal portfolio backtests:

```text
src/serenity_alpha_lab/quant/backtest/rebalance.py
tests/quant/test_rebalance_target_weights.py
```

The module converts approved `ScreenSnapshot` rows and explicit model signal targets into target weights and created `Order` snapshots. It reads `BacktestSpec`, `PortfolioLedger`, explicit rebalance prices, cash buffer, max instrument weight, lot size and minimum order notional, but it does not execute orders, mutate the ledger, compute risk, compute metrics, run audit, expose APIs, initialize Qlib or start a formal portfolio backtest.

## Contract

| Item | Contract |
|---|---|
| Policy contract | `quant.rebalance_policy@1.0.0` |
| Schema | `quant.backtest.rebalance_policy@1.0.0` |
| Generator version | `cn_a_share_rebalance_order_generator@1.0.0` |
| Strategy inputs | `ScreenSnapshot` or `ModelSignal` |
| Portfolio input | `PortfolioLedger` valued with explicit prices |
| Order output | created `Order` snapshots and `OrderIntent`s from `SAL-P4-008` |

Public DTOs include `RebalancePolicy`, `WeightingPolicy`, `ModelSignal`, `TargetWeight`, `SkippedRebalanceOrder`, `RebalancePlan` and `RebalanceOrderGenerator`.

## Target Weight Rules

- `ScreenSnapshot` inputs must match `BacktestSpec.strategy.screen_snapshot_id` and use passed rows only, sorted by rank.
- Model inputs use immutable `ModelSignal` rows with concrete `model_version_id` values and explicit `target_weight`, score weighting or equal weighting; `latest` model bindings are rejected.
- Equal weighting and score weighting allocate only investable weight after `BacktestRiskSpec.cash_buffer_pct`.
- Explicit model target weights must sum to no more than investable weight after cash buffer.
- Every target is capped by `BacktestRiskSpec.max_weight_per_instrument`; capped residual stays in cash and is not redistributed by this task.
- Target weights are deterministic and JSON-friendly, with `Decimal` values emitted as strings.

## Order Generation Rules

`RebalanceOrderGenerator.build_plan()` reads ledger state and explicit rebalance prices, then computes:

```text
cash_buffer_amount = ledger.equity * BacktestRiskSpec.cash_buffer_pct
available_buy_cash = max(ledger.cash_balance - ledger.payables - cash_buffer_amount, 0)
current_notional = current_quantity * explicit_rebalance_price
target_notional = ledger.equity * target_weight
delta_notional = target_notional - current_notional
```

Generated quantities are floored to `BacktestExecutionSpec.lot_size`. Zero-lot deltas, orders below `RebalancePolicy.min_order_notional` and buys that cannot fit settled cash after buffer are recorded as deterministic `SkippedRebalanceOrder` rows. Sell orders are emitted before buy orders; within a side, orders are sorted by canonical instrument ID. Receivables and same-rebalance sell proceeds are not counted as available buy cash.

The generator creates only `OrderStatus.CREATED` order snapshots via `Order.create(...)`. Stable `plan_id`, `order_id` and created event IDs are derived from canonical JSON inputs, so identical inputs produce identical order records.

## Scope Guard

This task does not start a formal portfolio backtest run. It does not accept, fill, expire or cancel orders; it does not call `AShareExecutionModel`; it does not mutate `PortfolioLedger`; it does not process corporate actions; it does not implement `RiskPolicy`, performance metrics or bias audit; it does not expose API/UI, start Quant Lab, start Evidence Agent, start Worker loop, call real Provider/LLM, import Qlib or change legacy `/api/v1/backtest/*` Signal Evaluation behavior.

Legacy DSA Signal Evaluation, AlphaSift T+N evaluation, Screen results, Dataset conversion artifacts and Qlib internal evidence remain outside the formal portfolio backtest namespace.

## Verification

| Check | Result |
|---|---|
| Red target | `uv run --extra core --extra dev python -m pytest tests/quant/test_rebalance_target_weights.py -q` initially failed with `ModuleNotFoundError: serenity_alpha_lab.quant.backtest.rebalance` |
| Focused target | `uv run --extra core --extra dev python -m pytest tests/quant/test_rebalance_target_weights.py -q` -> `4 passed` |
| Related suite | `uv run --extra core --extra dev python -m pytest tests/quant/test_rebalance_target_weights.py tests/quant/test_a_share_execution_rules.py tests/quant/test_cost_slippage_model.py tests/quant/test_portfolio_ledger.py tests/quant/test_order_state_machine.py tests/quant/test_backtest_spec.py tests/quant/test_screen_snapshot.py tests/architecture/test_architecture_boundaries.py -q` -> `42 passed` |
| Full suite | `uv run --extra core --extra dev python -m pytest -q` -> `372 passed, 3 skipped` |
| Compile | `uv run --extra core --extra dev python -m compileall -q src tests` -> PASS |
| Dependency lock | `scripts/verify-python-dependency-lock.sh` -> PASS with `Resolved 298 packages` |
| DSA patches | `scripts/apply-dsa-baseline-patches.sh --check-only` -> patches `0001..0005` already applied |
| Immutable upstream tag | `git rev-parse upstream/dsa-v3.26.1` -> `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a` |
| Diff hygiene | `git diff --check` -> PASS |

## Next Scope

`SAL-P4-014` must still implement deterministic `RiskPolicy`. The rebalance plan may provide target weights and created orders as input, but risk pass/warn/block/not-evaluable semantics remain a separate task.
