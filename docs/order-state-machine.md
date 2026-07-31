# Order State Machine

> Task: `SAL-P4-008` Order state machine<br>
> Date: 2026-07-25<br>
> Status: `APPROVED FOR SAL-P4-009 LEDGER INPUT ONLY`

## Conclusion

`SAL-P4-008` adds a pure formal backtest order state machine:

```text
src/serenity_alpha_lab/quant/backtest/orders.py
tests/quant/test_order_state_machine.py
```

The module defines immutable order intents, order events, legal status
transitions, rejection, partial fill, expiration, cancellation and idempotent
event replay. It does not generate orders from strategy signals, match fills,
replay cash/position ledgers, calculate fees/slippage, apply A-share execution
rules, compute metrics, run Qlib, expose APIs or start Worker runtime.

## State Model

Orders use the following states:

| State | Semantics |
|---|---|
| `created` | Order intent has been recorded and has an immutable created event |
| `accepted` | Order passed pre-trade validation and may receive fill events |
| `partially_filled` | One or more executions filled part of the target quantity |
| `filled` | Cumulative fill quantity equals target quantity; terminal |
| `rejected` | Order was rejected before any partial fill; terminal |
| `expired` | Active or partially filled order expired; terminal |
| `cancelled` | Active or partially filled order was cancelled; terminal |

Every state change is represented by an immutable `OrderEvent`. `Order` methods
return new snapshots and preserve the prior snapshot, so state history remains
append-only.

## Event Replay

`Order.replay(intent, events)` replays the same immutable event contract used by
live state transitions. Duplicate `event_id` values are idempotent only when the
payload is identical; a duplicate ID with different payload raises
`OrderStateMachineError`. Replaying the same event stream produces the same
`Order.to_record()` snapshot.

## Contract Guards

The state machine validates:

- concrete `InstrumentId` identity and `sha256:*` `BacktestSpec` hash binding;
- positive target and fill quantities;
- timezone-aware timestamps;
- contiguous event sequence numbers;
- fill events only after acceptance;
- overfill rejection;
- terminal state immutability;
- required reasons for rejected, expired and cancelled terminal events.

## Non-Goals

- No formal portfolio backtest run.
- No strategy-to-order generation, target-weight rebalance policy or A-share
  execution model.
- No Portfolio Ledger, cash, positions, receivables/payables, corporate-action
  processing, fees/slippage, RiskPolicy, metrics or audit computation.
- No Quant Lab, Evidence Agent, Worker loop, real Provider call or real LLM call.
- No Qlib runtime import, `qlib.init` or legacy `/api/v1/backtest/*` change.

Legacy DSA Signal Evaluation, AlphaSift T+N evaluation, Screen result, Dataset
conversion artifacts and Qlib internal backtest evidence remain outside the
formal portfolio backtest namespace.

## Verification

| Check | Result |
|---|---|
| Red target | `uv run --extra core --extra dev python -m pytest tests/quant/test_order_state_machine.py -q` initially failed with `ModuleNotFoundError: serenity_alpha_lab.quant.backtest.orders` |
| Focused target | `5 passed` |
| Related suite | `25 passed` across order state machine, BacktestSpec, BacktestArtifact and architecture boundaries |
| Full suite | `352 passed, 3 skipped` |
| Compile | `uv run --extra core --extra dev python -m compileall -q src tests` PASS |
| Dependency lock | `scripts/verify-python-dependency-lock.sh` PASS, `Resolved 298 packages` |
| DSA patches | `scripts/apply-dsa-baseline-patches.sh --check-only` PASS, patches `0001` through `0005` already applied |
| Immutable upstream tag | `upstream/dsa-v3.26.1` remained `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a` |
| Diff hygiene | `git diff --check` PASS |
| Import boundary | AST test confirms no `qlib`, `pyqlib`, `fastapi` or `sqlalchemy` import in `orders.py` |

## Scope Guard

This record only approves the order/event state machine as an input to
`SAL-P4-009` Portfolio Ledger. Later P4 tasks must still implement ledger
replay, costs, A-share execution rules, corporate actions, risk, bias audit,
metrics, orchestration, resources, API and Quant Lab before any formal
portfolio backtest can be promoted.
