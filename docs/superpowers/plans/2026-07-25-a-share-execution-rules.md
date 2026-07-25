# A-Share Execution Rules Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement `SAL-P4-011` as a pure deterministic A-share execution model for formal portfolio backtests.

**Architecture:** Add `quant.backtest.execution` as a boundary layer between existing `Order` state transitions and the existing `CostModel`. The module consumes `BacktestExecutionSpec`, an `Order`, a same-instrument market snapshot, optional sellable-position availability and a `CostModel`; it returns an immutable execution result with the updated order, optional fill event, optional cost breakdown and auditable rule records.

**Tech Stack:** Python dataclasses, Decimal arithmetic, existing `BacktestExecutionSpec`, existing `Order` / `OrderEvent`, existing `CostModel` / `CostBreakdown`.

---

### Task 1: A-Share Execution Contract Tests

**Files:**
- Create: `tests/quant/test_a_share_execution_rules.py`
- Read: `src/serenity_alpha_lab/quant/backtest/spec.py`
- Read: `src/serenity_alpha_lab/quant/backtest/orders.py`
- Read: `src/serenity_alpha_lab/quant/backtest/costs.py`

- [x] **Step 1: Write Red tests for T+1 and lot-size rules**

Create a filled-buy/sell-style fixture around `600519.XSHG` and write tests that verify:
- a close/after-close signal cannot execute on the same trade date;
- sell orders cannot exceed `sellable_quantity`;
- buy/sell target quantity must be a positive multiple of `BacktestExecutionSpec.lot_size`;
- failure records contain rule IDs such as `signal_available_before_execution`, `t_plus_one_sellable_quantity` and `trade_unit_lot_size`.

- [x] **Step 2: Write Red tests for suspension and limit-up/down rules**

Write tests with `AShareMarketSnapshot` fixtures:
- suspended securities are rejected under `suspended_security_policy="reject_order"`;
- buy orders at the upper price limit are unfillable;
- sell orders at the lower price limit are unfillable;
- limit-order prices that do not cross the execution price are unfillable.

- [x] **Step 3: Write Red tests for unfilled policy and audit records**

Verify:
- default `unfilled_order_policy="expire_after_rebalance"` expires active unfilled orders;
- `unfilled_order_policy="keep_open_until_cancelled"` leaves a previously accepted order open;
- execution results serialize deterministic audit records with rule ID, outcome, reason, order ID, instrument, trade date and metadata.

- [x] **Step 4: Write Red test for CostModel integration**

Verify a fillable order:
- moves from created to accepted to filled;
- uses `BacktestExecutionSpec.execution_price_field`;
- calls `CostModel.calculate(...)` with market volume;
- returns `CostBreakdown.total_cost`;
- does not mutate Portfolio Ledger or create formal BacktestArtifact output.

- [x] **Step 5: Run Red tests**

Run: `uv run --extra core --extra dev python -m pytest tests/quant/test_a_share_execution_rules.py -q`

Expected: fail with `ModuleNotFoundError: serenity_alpha_lab.quant.backtest.execution`.

### Task 2: A-Share Execution Implementation

**Files:**
- Create: `src/serenity_alpha_lab/quant/backtest/execution.py`
- Modify: `src/serenity_alpha_lab/quant/backtest/__init__.py`

- [x] **Step 1: Implement immutable DTOs**

Create:
- `A_SHARE_EXECUTION_MODEL_CONTRACT_VERSION = "quant.a_share_execution_model@1.0.0"`
- `A_SHARE_EXECUTION_MODEL_SCHEMA_NAME = "quant.backtest.a_share_execution_model"`
- `A_SHARE_EXECUTION_MODEL_SCHEMA_VERSION = "1.0.0"`
- `A_SHARE_EXECUTION_MODEL_VERSION = "cn_a_share_execution_model@1.0.0"`
- `AShareExecutionError`
- `AShareExecutionAuditRecord`
- `AShareExecutionResult`
- `AShareMarketSnapshot`
- `ASharePositionAvailability`
- `AShareExecutionModel`

Use immutable dataclasses with slots, explicit validation, concrete `sha256:*` spec hash binding, timezone-aware timestamps and JSON-friendly `to_record()` output.

- [x] **Step 2: Implement rule evaluation**

Rules:
- order, model and cost model `spec_hash` must match;
- market snapshot instrument and trade date must match the order;
- close/after-close signals execute only on a later trade date;
- target quantity must be a multiple of `BacktestExecutionSpec.lot_size`;
- suspended or non-trading market snapshots are unfillable;
- sell orders require `ASharePositionAvailability.sellable_quantity >= target_quantity`;
- buy at limit up and sell at limit down are unfillable;
- limit orders must cross the execution price.

- [x] **Step 3: Implement unfilled policy**

Map unfilled orders according to `BacktestExecutionSpec.unfilled_order_policy`:
- `expire_after_rebalance`: accept if needed, then expire active orders with an audit reason;
- `keep_open_until_cancelled`: return an accepted/open order with the blocking audit record;
- `reject_order`: reject orders before partial fill when possible.

Raise `AShareExecutionError` for unsupported policies instead of falling back silently.

- [x] **Step 4: Implement fill and cost integration**

For fillable orders:
- accept created orders;
- fill the remaining quantity at `AShareMarketSnapshot.price_for(execution_price_field)`;
- pass the fill event and `market_snapshot.volume` into `CostModel.calculate(...)`;
- return an `AShareExecutionResult` with `status="filled"`, the fill event, cost breakdown and pass audit records.

- [x] **Step 5: Export symbols**

Export all public execution symbols from `src/serenity_alpha_lab/quant/backtest/__init__.py` without importing Qlib, FastAPI, SQLAlchemy or DSA runtime.

### Task 3: Documentation And Status

**Files:**
- Create: `docs/a-share-execution-rules.md`
- Modify: `docs/development-progress-checklist.md`
- Modify: `docs/development-status.md`
- Modify: `tasks/todo.md`

- [x] **Step 1: Add evidence document**

Write `docs/a-share-execution-rules.md` covering scope, T+1 rule, lot-size rule, suspension/limit rules, unfilled policy, cost integration, non-goals and verification evidence.

- [x] **Step 2: Update progress/status docs**

Mark `SAL-P4-011` as `DONE`, set P4 progress to `11/22`, total progress to `77/129`, add decision/evidence rows, and make `SAL-P4-012` the next `READY` task. Do not mark later P4 tasks complete.

- [x] **Step 3: Update `tasks/todo.md` review**

Record Red/Green evidence, subagent dispatch fallback, verification commands, scope retained and checkpoint placeholders.

### Task 4: Verification And Checkpoint

**Files:**
- Verify only relevant source, test and docs files.

- [x] **Step 1: Run focused and related tests**

Run:
- `uv run --extra core --extra dev python -m pytest tests/quant/test_a_share_execution_rules.py -q`
- `uv run --extra core --extra dev python -m pytest tests/quant/test_a_share_execution_rules.py tests/quant/test_cost_slippage_model.py tests/quant/test_order_state_machine.py tests/quant/test_portfolio_ledger.py tests/quant/test_backtest_spec.py tests/architecture/test_architecture_boundaries.py -q`

- [x] **Step 2: Run full verification gates**

Run:
- `uv run --extra core --extra dev python -m pytest -q`
- `uv run --extra core --extra dev python -m compileall -q src tests`
- `scripts/verify-python-dependency-lock.sh`
- `scripts/apply-dsa-baseline-patches.sh --check-only`
- `git rev-parse upstream/dsa-v3.26.1`
- `git diff --check`

- [ ] **Step 3: Review and commit**

Check `git status --short`, stage only `SAL-P4-011` files, and create a Chinese checkpoint commit following the project template.
