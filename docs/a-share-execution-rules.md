# A-Share Execution Rules

> Task: `SAL-P4-011` A-share execution rules<br>
> Date: 2026-07-25<br>
> Status: `APPROVED FOR SAL-P4-012 CORPORATE-ACTION INPUT ONLY`

## Conclusion

`SAL-P4-011` adds a pure deterministic formal-backtest A-share execution model:

```text
src/serenity_alpha_lab/quant/backtest/execution.py
tests/quant/test_a_share_execution_rules.py
```

The model consumes `BacktestExecutionSpec`, an `Order`, an A-share market
snapshot, optional T+1 position availability and the existing `CostModel`. It
returns an immutable `AShareExecutionResult` with the updated order, optional
fill event, optional cost breakdown and structured audit records.

This task does not generate strategy orders, mutate the Portfolio Ledger,
process corporate actions, compute risk/metrics/audit, expose APIs, start a
Worker loop, initialize Qlib or run a formal portfolio backtest.

## Contract

| Item | Contract |
|---|---|
| Contract version | `quant.a_share_execution_model@1.0.0` |
| Schema | `quant.backtest.a_share_execution_model@1.0.0` |
| Model version | `cn_a_share_execution_model@1.0.0` |
| Parameter source | `BacktestExecutionSpec` |
| Order input | `Order` snapshots from `SAL-P4-008` |
| Cost input | `CostModel` from `SAL-P4-010` |

All inputs must bind the same concrete `sha256:*` `BacktestSpec.spec_hash`.
The market snapshot instrument and trade date must match the order. Sell
orders must provide `ASharePositionAvailability`; buys do not require a
position availability record.

## Rules

| Rule ID | Behavior |
|---|---|
| `signal_available_before_execution` | Close or after-close signals must execute on a later trade date; same-date close execution is rejected |
| `trade_unit_lot_size` | Remaining order quantity must be a multiple of `BacktestExecutionSpec.lot_size` |
| `market_tradable_status` | Suspended or non-trading snapshots are unfillable and follow `suspended_security_policy` |
| `t_plus_one_sellable_quantity` | Sell quantity cannot exceed T+1 sellable quantity |
| `limit_up_down_executable` | Buy orders at limit-up and sell orders at limit-down are unfillable |
| `order_limit_price_crosses_execution_price` | Limit buys must cross or equal the execution price; limit sells must cross or equal the execution price |
| `cost_model_participation` | Order quantity must remain within the CostModel maximum participation rate |

Every rule writes an `AShareExecutionAuditRecord` with rule ID, outcome,
reason, order ID, canonical instrument, trade date, timestamp and optional
metadata. Audit records are deterministic and JSON-friendly.

## Unfilled Policy

Unfillable orders are resolved with explicit policies:

| Policy | Result |
|---|---|
| `expire_after_rebalance` | Accepts the order if needed, then expires it with the blocking reason |
| `keep_open_until_cancelled` | Accepts the order if needed and leaves it open with audit evidence |
| `reject_order` | Rejects an unfilled order when it has not been partially filled; partially filled orders expire remaining quantity |

Unsupported policies raise `AShareExecutionError`. The model does not silently
fallback to another policy.

## Cost Boundary

When an order is fillable, `AShareExecutionModel` accepts created orders, fills
the remaining quantity at `AShareMarketSnapshot.price_for(execution_price_field)`
and calls:

```python
CostModel.calculate(order=filled_order, fill_event=fill_event, market_volume=snapshot.volume)
```

The resulting `CostBreakdown` is returned on the execution result. Ledger
integration remains explicit in later orchestration: callers must pass
`CostBreakdown.total_cost` into `PortfolioLedger.record_execution(...)`.

## Non-Goals

- No formal portfolio backtest run.
- No strategy-to-order generation, target-weight rebalance policy or portfolio
  orchestration.
- No Portfolio Ledger mutation or cash/position event creation.
- No corporate-action processor, RiskPolicy, performance metrics, bias audit,
  Quant Lab, Evidence Agent, Worker loop, real Provider call or real LLM call.
- No Qlib runtime import, `qlib.init` or legacy `/api/v1/backtest/*` change.

Legacy DSA Signal Evaluation, AlphaSift T+N evaluation, Screen result, Dataset
conversion artifacts and Qlib internal backtest evidence remain outside the
formal portfolio backtest namespace.

## Verification

| Check | Result |
|---|---|
| Red target | `uv run --extra core --extra dev python -m pytest tests/quant/test_a_share_execution_rules.py -q` initially failed with `ModuleNotFoundError: serenity_alpha_lab.quant.backtest.execution` |
| Focused target | `uv run --extra core --extra dev python -m pytest tests/quant/test_a_share_execution_rules.py -q` -> `6 passed` |
| Related suite | `uv run --extra core --extra dev python -m pytest tests/quant/test_a_share_execution_rules.py tests/quant/test_cost_slippage_model.py tests/quant/test_order_state_machine.py tests/quant/test_portfolio_ledger.py tests/quant/test_backtest_spec.py tests/architecture/test_architecture_boundaries.py -q` -> `35 passed` |
| Full suite | `uv run --extra core --extra dev python -m pytest -q` -> `365 passed, 3 skipped` |
| Compile | `uv run --extra core --extra dev python -m compileall -q src tests` -> PASS |
| Dependency lock | `scripts/verify-python-dependency-lock.sh` -> PASS with `Resolved 298 packages` |
| DSA patches | `scripts/apply-dsa-baseline-patches.sh --check-only` -> patches `0001..0005` already applied |
| Immutable upstream tag | `git rev-parse upstream/dsa-v3.26.1` -> `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a` |
| Diff hygiene | `git diff --check` -> PASS |

## Scope Guard

This record only approves deterministic A-share order execution as input to
later P4 tasks. `SAL-P4-012` must still process company actions, and subsequent
P4 tasks must still implement rebalance, risk, audit, metrics, orchestration,
resources, API and Quant Lab before any formal portfolio backtest can be
promoted.
