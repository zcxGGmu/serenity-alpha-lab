# Backtest Golden And Property Tests

> Task: `SAL-P4-019` backtest golden and property-style tests<br>
> Date: 2026-07-26<br>
> Status: `APPROVED FOR SAL-P4-020 API INPUT ONLY`

## Conclusion

`SAL-P4-019` adds a deterministic, hand-computable golden validation harness for the P4 formal portfolio backtest component chain:

```text
src/serenity_alpha_lab/quant/backtest/golden.py
tests/quant/test_backtest_golden_property.py
```

The fixture covers 3 A-share instruments across 20 trading days and 60 daily bars. It composes the existing `BacktestSpec`, `Order`, A-share execution model, `CostModel`, `PortfolioLedger`, corporate action ledger processor and performance metric calculator on fixed synthetic data. The full-read and chunked-read paths consume the same ordered records and produce identical result records and hashes.

This task creates golden validation evidence only. It does not expose formal API routes, start Quant Lab, start Evidence Agent, start Worker loop, call real Providers, call real LLMs, initialize Qlib runtime or change legacy DSA `/api/v1/backtest/*` Signal Evaluation behavior.

## Contract

| Item | Contract |
|---|---|
| Contract version | `quant.backtest_golden_fixture@1.0.0` |
| Schema | `quant.backtest.golden_fixture@1.0.0` |
| Runner version | `cn_a_share_backtest_golden_runner@1.0.0` |
| Fixture ID | `btg_cn_a_share_hand_computable_v1` |
| Scope | `formal_portfolio_backtest_golden_fixture` |
| Result hash | `sha256:76e9c93b060bdec6cc05497a477efa2de870168f20d18f349e2a78393d4e78d1` |

Public DTOs include `BacktestGoldenBar`, `BacktestGoldenFixture`, `BacktestGoldenResult`, `BacktestGoldenRunner` and `BacktestGoldenOrderRole`.

## Fixture Shape

| Item | Value |
|---|---:|
| Instruments | `3` |
| Trading days | `20` |
| Bars | `60` |
| Starting cash | `10000.000` |
| Final cash | `10246.600` |
| Final equity | `10246.600` |
| Total transaction cost | `3.400` |
| Realized P&L | `196.600` |
| Cumulative return | `0.024660` |

The fixture uses:

- `600519.XSHG`: initial buy, same-day T+1 sell probe, cash dividend, final sell and settlement.
- `000001.XSHE`: suspended buy rejection.
- `300750.XSHE`: limit-up buy expiration.

## Rule Coverage

| Rule | Evidence |
|---|---|
| Fees | 10 bps buy commission, 10 bps sell commission and 10 bps sell stamp tax produce total cost `3.400`. |
| T+1 | Same-day sell after the initial buy has `sellable_quantity=0` and expires. |
| Suspension | Suspended `000001.XSHE` buy is rejected. |
| Limit up/down | `300750.XSHE` limit-up market buy is unfilled and expires. |
| Corporate action | `600519.XSHG` cash dividend `0.5` per share creates and settles receivable cash. |
| Rebalance | Initial and final rebalance orders drive the buy and sell lifecycle. |
| Chunked reads | `chunk_size=1` and `chunk_size=7` match the full-read result record and result hash. |

Expected order statuses:

| Order | Status |
|---|---|
| `ord-golden-buy-600519` | `filled` |
| `ord-golden-tplus-one-sell-600519` | `expired` |
| `ord-golden-suspended-buy-000001` | `rejected` |
| `ord-golden-limit-up-buy-300750` | `expired` |
| `ord-golden-sell-600519` | `filled` |

## Property Checks

The property-style tests assert:

- Every equity point is positive, date-unique and strictly increasing by valuation date.
- First equity equals starting cash and final equity equals the ledger equity.
- The ledger reconciliation formula remains `cash + position_market_value + receivables - payables`.
- All positions, receivables and payables are flat after final settlement.
- Result records are JSON serializable and chunked result hashes are stable.
- The module import boundary stays offline and does not import Qlib, FastAPI, Celery, Redis, SQLAlchemy, LLM or legacy DSA provider/API modules.

## Non-Goals

- No `/api/v1/quant/backtest-runs` create/status/artifact/cancel routes.
- No Quant Lab UI.
- No Evidence Agent, report agent, citation validation or model budgeting.
- No Worker loop, Celery task handler, Redis queue consumption or process spawning implementation.
- No real Provider, real LLM or external network call.
- No Qlib runtime initialization or `qlib.init`.
- No change to legacy DSA Signal Evaluation routes, schemas or naming.

Legacy DSA Signal Evaluation, AlphaSift T+N evaluation, Screen results, Qlib internal evidence and Dataset conversion artifacts remain outside the formal portfolio backtest namespace.

## Verification

| Check | Result |
|---|---|
| Red target | `uv run --extra core --extra dev python -m pytest tests/quant/test_backtest_golden_property.py -q` initially failed with `ModuleNotFoundError: No module named 'serenity_alpha_lab.quant.backtest.golden'` |
| Focused target | `uv run --extra core --extra dev python -m pytest tests/quant/test_backtest_golden_property.py -q` -> `4 passed` |
| Related suite | `uv run --extra core --extra dev python -m pytest tests/quant/test_backtest_golden_property.py tests/quant/test_a_share_execution_rules.py tests/quant/test_portfolio_ledger.py tests/quant/test_corporate_action_ledger.py tests/quant/test_rebalance_target_weights.py tests/quant/test_backtest_performance_metrics.py tests/application/test_backtest_run_orchestration.py tests/application/test_backtest_resource_control.py tests/architecture/test_architecture_boundaries.py -q` -> `46 passed` |
| Full suite | `uv run --extra core --extra dev python -m pytest -q` -> `395 passed, 3 skipped` |
| Compile | `uv run --extra core --extra dev python -m compileall -q src/serenity_alpha_lab tests` -> PASS |
| Lock guard | `scripts/verify-python-dependency-lock.sh` -> PASS, `Resolved 298 packages` |
| DSA patches | `scripts/apply-dsa-baseline-patches.sh --check-only` -> `0001..0005` already applied |
| Immutable tag | `git rev-parse upstream/dsa-v3.26.1` -> `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a` |
| Diff hygiene | `git diff --check` -> PASS |

## Scope Guard

This record approves the fixed-data golden and property-style validation harness as input to `SAL-P4-020` only. Later tasks must still implement formal API routes, Quant Lab and Gate G4 before any portfolio backtest result can be promoted beyond this golden fixture contract.
