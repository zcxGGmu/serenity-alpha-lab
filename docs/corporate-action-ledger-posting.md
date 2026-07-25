# Corporate Action Ledger Posting

> Task: `SAL-P4-012` corporate action ledger posting<br>
> Date: 2026-07-25<br>
> Status: `APPROVED FOR SAL-P4-013 REBALANCE INPUT ONLY`

## Conclusion

`SAL-P4-012` adds deterministic corporate-action ledger posting for formal
portfolio backtests:

```text
src/serenity_alpha_lab/quant/backtest/corporate_actions.py
src/serenity_alpha_lab/quant/backtest/ledger.py
tests/quant/test_corporate_action_ledger.py
```

The processor consumes P2 `CorporateAction` records for cash dividends,
bonus/split shares and rights issues, and accepts an explicit delisting
liquidation fixture until a later Dataset source exists. It appends immutable
`LedgerEventType.CORPORATE_ACTION` events and records deterministic
`CorporateActionRecord` rows in `PortfolioLedger`.

This task does not generate strategy orders, execute market fills, compute
fees/slippage, compute risk/metrics/audit, mutate raw or adjusted Dataset
prices, expose APIs, start a Worker loop, initialize Qlib or run a formal
portfolio backtest.

## Contract

| Item | Contract |
|---|---|
| Processor contract | `quant.corporate_action_ledger_processor@1.0.0` |
| Processor schema | `quant.backtest.corporate_action_ledger_processor@1.0.0` |
| Processor version | `cn_a_share_corporate_action_ledger_processor@1.0.0` |
| Ledger event type | `corporate_action` |
| Dataset source schema | `dataset.corporate_actions@1.0.0` |
| Explicit delisting source schema | `quant.backtest.delisting_liquidation@1.0.0` |

All postings append to the existing `PortfolioLedger` event stream and remain
replayable. Duplicate `event_id` handling continues to use the ledger's
existing idempotent replay rule: the same payload is ignored, conflicting
payloads are rejected.

## Accounting Rules

| Action | Ledger effect |
|---|---|
| `cash_dividend` | Creates a receivable equal to current position quantity times cash per share; settlement uses the existing cash-settlement flow |
| `bonus_share` | Increases open lot quantities pro rata and keeps total cost basis unchanged |
| `share_split` | Scales open lot quantities pro rata and keeps total cost basis unchanged; reverse splits are rejected if they would remove all shares |
| `rights_issue` | Adds a payable equal to entitlement shares times rights price and creates a new cost-basis lot for subscribed shares |
| `delisting_liquidation` | Removes all open lots for the instrument, creates a liquidation receivable and records FIFO realized P&L |

Equity remains governed by the existing ledger invariant:

```text
equity = cash + position_market_value + receivables - payables
```

For cash dividends, economic value around the ex-date is only neutral when the
valuation price is separately marked to the ex-dividend price. The processor
does not infer or apply adjusted prices.

## Double-Counting Guard

`CorporateActionLedgerProcessor` imports and consumes only
`datasets.corporate_actions.CorporateAction` for Dataset-backed actions. It
does not import `AdjustedDailyBar`, read adjustment factors or consume
forward/backward adjusted OHLC values. Price continuity and factor derivation
remain the P2 Dataset responsibility; P4 ledger posting records only cash,
share and liquidation flows.

## Non-Goals

- No formal portfolio backtest run.
- No strategy-to-order generation, target-weight rebalance policy or order orchestration.
- No fee/slippage calculation, A-share execution matching, RiskPolicy, performance metrics, bias audit or Quant Lab.
- No raw or adjusted Dataset mutation and no re-computation of adjustment factors.
- No Evidence Agent, Worker loop, real Provider call or real LLM call.
- No Qlib runtime import, `qlib.init` or legacy `/api/v1/backtest/*` change.

Legacy DSA Signal Evaluation, AlphaSift T+N evaluation, Screen result, Dataset
conversion artifacts and Qlib internal backtest evidence remain outside the
formal portfolio backtest namespace.

## Verification

| Check | Result |
|---|---|
| Red target | `uv run --extra core --extra dev python -m pytest tests/quant/test_corporate_action_ledger.py -q` initially failed with `ModuleNotFoundError: serenity_alpha_lab.quant.backtest.corporate_actions` |
| Focused target | `uv run --extra core --extra dev python -m pytest tests/quant/test_corporate_action_ledger.py -q` -> `3 passed` |
| Related suite | `uv run --extra core --extra dev python -m pytest tests/quant/test_corporate_action_ledger.py tests/quant/test_portfolio_ledger.py tests/datasets/test_corporate_actions_adjustments.py tests/quant/test_a_share_execution_rules.py tests/quant/test_cost_slippage_model.py tests/quant/test_order_state_machine.py tests/quant/test_backtest_spec.py tests/architecture/test_architecture_boundaries.py -q` -> `41 passed` |
| Full suite | `uv run --extra core --extra dev python -m pytest -q` -> `368 passed, 3 skipped` |
| Compile | `uv run --extra core --extra dev python -m compileall -q src tests` -> PASS |

Additional lock, DSA patch, immutable tag and diff hygiene checks are recorded
in `tasks/todo.md` and the progress checklist for `AEV-078`.

## Scope Guard

This record only approves deterministic corporate-action ledger posting as an
input to later P4 tasks. `SAL-P4-013` must still implement rebalance and target
weights, and later tasks must still implement risk, metrics, audit,
orchestration, resources, API and Quant Lab before any formal portfolio
backtest can be promoted.
