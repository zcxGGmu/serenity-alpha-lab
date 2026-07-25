# Portfolio Ledger

> Task: `SAL-P4-009` Portfolio Ledger<br>
> Date: 2026-07-25<br>
> Status: `APPROVED FOR COST / EXECUTION / CORPORATE-ACTION INPUT ONLY`

## Conclusion

`SAL-P4-009` adds a pure formal backtest Portfolio Ledger:

```text
src/serenity_alpha_lab/quant/backtest/ledger.py
tests/quant/test_portfolio_ledger.py
```

The module defines immutable ledger events, FIFO position lots, execution
records, settlement balances, valuation snapshots and deterministic replay. It
consumes the `Order` / fill `OrderEvent` contract from `SAL-P4-008`; it does not
generate orders, match fills, calculate fees/slippage, enforce A-share execution
rules, process corporate actions, compute risk/metrics/audit, run Qlib, expose
APIs or start Worker runtime.

## Accounting Model

The ledger freezes these balances:

| Balance | Semantics |
|---|---|
| `cash_balance` | Settled base-currency cash |
| `receivables` | Unsettled sale proceeds or future cash inflows |
| `payables` | Unsettled purchase payments or future cash outflows |
| `position_lots` | FIFO lots created from buy executions and reduced by sell executions |
| `valuation_prices` | Explicit mark-to-market prices for all open positions |

Equity is always reconciled as:

```text
equity = cash + position_market_value + receivables - payables
```

Buy executions create a position lot and increase payables by `gross_amount +
transaction_cost`; cash changes only when the payable is settled. Sell
executions reduce FIFO lots and increase receivables by `gross_amount -
transaction_cost`; cash changes only when the receivable is settled.

## Event Replay

`PortfolioLedger.replay(...)` replays the same `LedgerEvent` contract used by
live methods. Duplicate `event_id` values are idempotent only when the payload
is identical; a duplicate ID with different payload raises
`PortfolioLedgerError`. Replaying the same event stream produces the same
`PortfolioLedger.to_record()` snapshot.

## Contract Guards

The ledger validates:

- concrete `sha256:*` `BacktestSpec` hash binding;
- `Order` run/stage/spec binding before accepting fill events;
- fill-event type and order-event history membership;
- positive quantities, prices and settlement amounts;
- FIFO lot availability before sell executions;
- non-negative receivables and payables;
- valuation prices for every open position;
- contiguous event sequences and conflicting duplicate event IDs.

## Non-Goals

- No formal portfolio backtest run.
- No strategy-to-order generation, target-weight rebalance policy or fill
  matching.
- No fee/slippage calculation, A-share T+1/lot/limit/suspension execution rules,
  corporate-action processing, RiskPolicy, metrics, audit or Quant Lab.
- No Evidence Agent, Worker loop, real Provider call or real LLM call.
- No Qlib runtime import, `qlib.init` or legacy `/api/v1/backtest/*` change.

Legacy DSA Signal Evaluation, AlphaSift T+N evaluation, Screen result, Dataset
conversion artifacts and Qlib internal backtest evidence remain outside the
formal portfolio backtest namespace.

## Verification

| Check | Result |
|---|---|
| Red target | `uv run --extra core --extra dev python -m pytest tests/quant/test_portfolio_ledger.py -q` initially failed with `ModuleNotFoundError: serenity_alpha_lab.quant.backtest.ledger` |
| Focused target | `3 passed` |
| Related suite | `28 passed` across Portfolio Ledger, Order State Machine, BacktestSpec, BacktestArtifact and architecture boundaries |
| Full suite | `355 passed, 3 skipped` |
| Compile | `uv run --extra core --extra dev python -m compileall -q src tests` PASS |
| Dependency lock | `scripts/verify-python-dependency-lock.sh` PASS, `Resolved 298 packages` |
| DSA patches | `scripts/apply-dsa-baseline-patches.sh --check-only` PASS, patches `0001` through `0005` already applied |
| Immutable upstream tag | `upstream/dsa-v3.26.1` remained `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a` |
| Diff hygiene | `git diff --check` PASS |
| Import boundary | AST test confirms no `qlib`, `pyqlib`, `fastapi` or `sqlalchemy` import in `ledger.py` |

## Scope Guard

This record only approves deterministic ledger replay as an input to later P4
tasks. `SAL-P4-010` must still implement fees/slippage, `SAL-P4-011` must still
implement A-share execution rules, `SAL-P4-012` must still process corporate
actions, and subsequent P4 tasks must still implement rebalance, risk, audit,
metrics, orchestration, resources, API and Quant Lab before any formal portfolio
backtest can be promoted.
