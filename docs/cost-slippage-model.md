# Cost And Slippage Model

> Task: `SAL-P4-010` 费用与滑点模型<br>
> Date: 2026-07-25<br>
> Status: `APPROVED FOR SAL-P4-011 EXECUTION RULE INPUT ONLY`

## Conclusion

`SAL-P4-010` adds a pure deterministic formal backtest cost model:

```text
src/serenity_alpha_lab/quant/backtest/costs.py
tests/quant/test_cost_slippage_model.py
```

The model consumes `BacktestCostSpec` plus an `Order` fill event and returns an
immutable `CostBreakdown`. The breakdown is intentionally ledger-neutral:
callers pass `CostBreakdown.total_cost` into `PortfolioLedger.record_execution`
as an explicit transaction cost. The cost model does not mutate orders, create
ledger events, enforce A-share execution rules, process corporate actions,
compute risk/metrics/audit, expose APIs or start Worker runtime.

## Contract

| Item | Contract |
|---|---|
| Contract version | `quant.cost_model@1.0.0` |
| Schema | `quant.backtest.cost_model@1.0.0` |
| Model version | `cn_a_share_cost_model@1.0.0` |
| Parameter source | `BacktestCostSpec` |
| Order input | `Order` plus a fill `OrderEvent` from the same event history |
| Liquidity input | `market_volume` in shares for participation-rate checks |

Every calculation binds the same concrete `sha256:*` `BacktestSpec.spec_hash`
as the order. A mismatched spec hash, non-fill event, fill event not present in
the order history, non-positive market volume or participation breach is
rejected before cost calculation.

## Formulas

For each fill:

```text
gross_amount = quantity * fill_price
commission = max(gross_amount * commission_bps / 10000, min_commission)
stamp_tax = gross_amount * stamp_tax_bps / 10000, sell fills only
transfer_fee = gross_amount * transfer_fee_bps / 10000
slippage = gross_amount * slippage_bps / 10000
impact = gross_amount * impact_bps / 10000
total_cost = commission + stamp_tax + transfer_fee + slippage + impact
```

Effective execution price is deterministic and side-aware:

```text
buy_effective_price = fill_price + fill_price * (slippage_bps + impact_bps) / 10000
sell_effective_price = fill_price - fill_price * (slippage_bps + impact_bps) / 10000
```

The model keeps `Decimal` values unrounded internally and emits stringified
Decimals in `to_record()`. Broker-specific cash rounding remains a future
explicit policy if needed; this task freezes deterministic platform math rather
than a specific broker settlement convention.

## Buy / Sell Asymmetry

| Cost | Buy | Sell |
|---|---:|---:|
| Commission | yes, with minimum commission | yes, with minimum commission |
| Stamp tax | no | yes |
| Transfer fee | yes | yes |
| Slippage | yes | yes |
| Impact | yes | yes |

The `CostBreakdown` keeps every line item even when an amount is zero, so
cost-before and cost-after records are comparable between buy and sell fills.

## Ledger Boundary

`CostModel` does not import or mutate the ledger. Ledger integration remains
explicit:

```text
cost = CostModel(...).calculate(order=order, fill_event=fill, market_volume=...)
ledger.record_execution(..., transaction_cost=cost.total_cost)
```

This preserves the `SAL-P4-009` invariant that cash, receivables, payables,
position lots and equity are driven only by explicit ledger events.

## Non-Goals

- No formal portfolio backtest run.
- No A-share T+1, lot-size rounding, suspension, limit-up/down or unfilled
  order policy enforcement; those remain `SAL-P4-011`.
- No corporate-action processor, RiskPolicy, performance metrics, bias audit,
  Quant Lab, Evidence Agent, Worker loop, real Provider call or real LLM call.
- No Qlib runtime import, `qlib.init` or legacy `/api/v1/backtest/*` change.

Legacy DSA Signal Evaluation, AlphaSift T+N evaluation, Screen result, Dataset
conversion artifacts and Qlib internal backtest evidence remain outside the
formal portfolio backtest namespace.

## Verification

| Check | Result |
|---|---|
| Red target | `uv run --extra core --extra dev python -m pytest tests/quant/test_cost_slippage_model.py -q` initially failed with `ModuleNotFoundError: serenity_alpha_lab.quant.backtest.costs` |
| Focused target | `4 passed` |
| Related suite | `29 passed` across CostModel, Portfolio Ledger, Order State Machine, BacktestSpec and architecture boundaries |
| Full suite | `359 passed, 3 skipped` |
| Compile | `uv run --extra core --extra dev python -m compileall -q src tests` PASS |
| Dependency lock | `scripts/verify-python-dependency-lock.sh` PASS, `Resolved 298 packages` |
| DSA patches | `scripts/apply-dsa-baseline-patches.sh --check-only` PASS, patches `0001` through `0005` already applied |
| Immutable upstream tag | `upstream/dsa-v3.26.1` remained `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a` |
| Diff hygiene | `git diff --check` PASS |
| Scope guard | AST import guard confirms `costs.py` imports no `qlib`, `pyqlib`, `fastapi` or `sqlalchemy` |

## Scope Guard

This record only approves deterministic transaction-cost and effective-price
calculation as input to later execution and ledger tasks. `SAL-P4-011` must
still implement A-share execution rules, `SAL-P4-012` must still process
corporate actions, and subsequent P4 tasks must still implement rebalance,
risk, audit, metrics, orchestration, resources, API and Quant Lab before any
formal portfolio backtest can be promoted.
