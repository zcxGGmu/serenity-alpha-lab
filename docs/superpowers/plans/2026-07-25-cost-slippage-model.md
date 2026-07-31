# Cost And Slippage Model Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement `SAL-P4-010` as a pure deterministic cost/slippage model for formal portfolio backtests.

**Architecture:** Add a new `quant.backtest.costs` module that reuses `BacktestCostSpec` and `Order` fill events to calculate commission, stamp tax, transfer fee, slippage, impact cost and participation-rate guards. Keep output as immutable records that can be passed into the existing Portfolio Ledger as explicit `transaction_cost` without starting a formal backtest run.

**Tech Stack:** Python dataclasses, Decimal arithmetic, existing `BacktestCostSpec`, existing `Order` / `OrderEvent`, existing `PortfolioLedger`.

---

### Task 1: Cost Model Contract Tests

**Files:**
- Create: `tests/quant/test_cost_slippage_model.py`
- Read: `src/serenity_alpha_lab/quant/backtest/spec.py`
- Read: `src/serenity_alpha_lab/quant/backtest/orders.py`
- Read: `src/serenity_alpha_lab/quant/backtest/ledger.py`

- [ ] **Step 1: Write Red tests for buy/sell fee asymmetry**

Add tests that create a `BacktestCostSpec` with `commission_bps=3.0`, `min_commission=5.00`, `stamp_tax_bps=10.0`, `transfer_fee_bps=0.2`, `slippage_bps=5.0`, `impact_bps=2.0`, `max_participation_rate=0.1000`; use filled buy/sell orders for `600519.XSHG`.

Expected behavior:
- buy fills include commission, transfer fee, slippage cost and impact cost;
- sell fills additionally include stamp tax;
- minimum commission applies per execution when bps commission is lower than the minimum;
- effective price moves up for buys and down for sells by slippage + impact bps.

- [ ] **Step 2: Write Red tests for participation guard and deterministic record**

Add tests that pass market volume and verify:
- notional quantity greater than `market_volume * max_participation_rate` is rejected;
- the model returns stable `to_record()` JSON-friendly output with `schema_name`, `schema_version`, `model_version`, `spec_hash`, line items and `total_cost`.

- [ ] **Step 3: Write Red test for ledger integration boundary**

Add a test that applies the calculated `total_cost` to `PortfolioLedger.record_execution(...)` and verifies buy payable includes transaction cost, without making `CostModel` mutate the ledger itself.

- [ ] **Step 4: Run Red tests**

Run: `uv run --extra core --extra dev python -m pytest tests/quant/test_cost_slippage_model.py -q`

Expected: fail with `ModuleNotFoundError: serenity_alpha_lab.quant.backtest.costs`.

### Task 2: Cost Model Implementation

**Files:**
- Create: `src/serenity_alpha_lab/quant/backtest/costs.py`
- Modify: `src/serenity_alpha_lab/quant/backtest/__init__.py`

- [ ] **Step 1: Implement immutable DTOs**

Create:
- `BACKTEST_COST_MODEL_CONTRACT_VERSION = "quant.cost_model@1.0.0"`
- `BACKTEST_COST_MODEL_SCHEMA_NAME = "quant.backtest.cost_model"`
- `BACKTEST_COST_MODEL_SCHEMA_VERSION = "1.0.0"`
- `BACKTEST_COST_MODEL_VERSION = "cn_a_share_cost_model@1.0.0"`
- `CostModelError`
- `CostLineItem`
- `CostBreakdown`
- `ExecutionCostInput`
- `CostModel`

Use `Decimal(str(value))`, reject bools/non-finite numbers, require timezone-aware fill times, concrete `sha256:*` spec hash, positive quantity/price/market volume and `Order` / `OrderEvent` fill binding.

- [ ] **Step 2: Implement calculations**

Use:
- `gross_amount = quantity * fill_price`
- `commission = max(gross_amount * commission_bps / 10000, min_commission)`
- `stamp_tax = gross_amount * stamp_tax_bps / 10000` only on sell
- `transfer_fee = gross_amount * transfer_fee_bps / 10000`
- `slippage_cost = gross_amount * slippage_bps / 10000`
- `impact_cost = gross_amount * impact_bps / 10000`
- `total_cost = sum(line_items)`
- `effective_price = fill_price + fill_price * (slippage_bps + impact_bps) / 10000` for buy, and subtract the same amount for sell.

Keep values unrounded internally and output Decimal strings; document that venue-specific rounding remains explicit and deterministic here rather than broker-grade cash rounding.

- [ ] **Step 3: Implement exports**

Export all public symbols from `src/serenity_alpha_lab/quant/backtest/__init__.py` without importing Qlib, FastAPI, SQLAlchemy or DSA runtime.

- [ ] **Step 4: Run Green focused tests**

Run: `uv run --extra core --extra dev python -m pytest tests/quant/test_cost_slippage_model.py -q`

Expected: pass.

### Task 3: Documentation And Status

**Files:**
- Create: `docs/cost-slippage-model.md`
- Modify: `docs/development-progress-checklist.md`
- Modify: `docs/development-status.md`
- Modify: `tasks/todo.md`

- [ ] **Step 1: Add evidence document**

Write `docs/cost-slippage-model.md` covering scope, calculation formulas, buy/sell asymmetry, participation guard, ledger integration, non-goals and verification evidence.

- [ ] **Step 2: Update progress/status docs**

Mark `SAL-P4-010` as `DONE`, set P4 progress to `10/22`, total progress to `76/129`, add `DEC-074` and `AEV-076`, and make `SAL-P4-011` the next `READY` task. Do not mark later P4 tasks complete.

- [ ] **Step 3: Update `tasks/todo.md` review**

Record Red/Green evidence, subagent dispatch fallback, verification commands, scope retained and checkpoint placeholders.

### Task 4: Verification And Checkpoint

**Files:**
- Verify only relevant source, test and docs files.

- [ ] **Step 1: Run targeted and related tests**

Run:
- `uv run --extra core --extra dev python -m pytest tests/quant/test_cost_slippage_model.py -q`
- `uv run --extra core --extra dev python -m pytest tests/quant/test_cost_slippage_model.py tests/quant/test_portfolio_ledger.py tests/quant/test_order_state_machine.py tests/quant/test_backtest_spec.py tests/architecture/test_architecture_boundaries.py -q`

- [ ] **Step 2: Run full verification gates**

Run:
- `uv run --extra core --extra dev python -m pytest -q`
- `uv run --extra core --extra dev python -m compileall -q src tests`
- `scripts/verify-python-dependency-lock.sh`
- `scripts/apply-dsa-baseline-patches.sh --check-only`
- `git rev-parse upstream/dsa-v3.26.1`
- `git diff --check`

- [ ] **Step 3: Review and commit**

Check `git status --short`, stage only `SAL-P4-010` files, and create a Chinese checkpoint commit following the project template.
