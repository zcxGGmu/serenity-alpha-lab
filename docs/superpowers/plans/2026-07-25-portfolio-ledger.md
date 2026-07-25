# Portfolio Ledger Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement `SAL-P4-009` Portfolio Ledger as a deterministic, replayable accounting contract for formal portfolio backtest cash, positions, receivables/payables, executions and valuation snapshots.

**Architecture:** Add a pure `quant.backtest.ledger` module that consumes `Order` / fill `OrderEvent` contracts from `SAL-P4-008` and emits immutable ledger snapshots. The ledger keeps append-only events, FIFO position lots, settlement balances and valuation prices, then verifies `equity = cash + position_market_value + receivables - payables`. It does not calculate fees/slippage, enforce A-share execution rules, process corporate actions, run a formal backtest, expose APIs or invoke Qlib.

**Tech Stack:** Python dataclasses, Decimal accounting, existing `InstrumentId`, existing `quant.backtest.orders`, pytest.

---

### Task 1: Red Contract Tests

**Files:**
- Create: `tests/quant/test_portfolio_ledger.py`

- [ ] **Step 1: Write failing tests**

Add tests for:
- initial cash plus buy execution with payable settlement;
- sell execution with receivable settlement and FIFO lot reduction;
- valuation snapshots and exact equity reconciliation;
- deterministic replay with duplicate-event idempotency and conflict rejection;
- spec/order binding validation and pure import boundary.

- [ ] **Step 2: Run target test to verify Red**

Run: `uv run --extra core --extra dev python -m pytest tests/quant/test_portfolio_ledger.py -q`

Expected: FAIL with `ModuleNotFoundError: serenity_alpha_lab.quant.backtest.ledger`.

### Task 2: Minimal Ledger Implementation

**Files:**
- Create: `src/serenity_alpha_lab/quant/backtest/ledger.py`
- Modify: `src/serenity_alpha_lab/quant/backtest/__init__.py`

- [ ] **Step 1: Implement immutable ledger DTOs**

Create:
- `LedgerEventType`
- `LedgerEvent`
- `PositionLot`
- `ExecutionRecord`
- `PortfolioLedger`
- `PortfolioLedgerError`

Validate non-empty IDs, `sha256:*` spec hash, aware timestamps, positive quantities/prices/costs, concrete `InstrumentId`, and no arbitrary runtime imports.

- [ ] **Step 2: Implement append-only replay**

Add `PortfolioLedger.open()` and `PortfolioLedger.replay()` with contiguous sequence checks and duplicate event id idempotency only when payloads match.

- [ ] **Step 3: Implement execution accounting**

For buy fills:
- create a lot;
- add payable equal to gross amount plus explicit transaction cost;
- keep cash unchanged until settlement.

For sell fills:
- reduce FIFO lots;
- add receivable equal to gross amount minus explicit transaction cost;
- reject sells exceeding current position.

- [ ] **Step 4: Implement settlement and valuation**

Add `settle_payable()`, `settle_receivable()` and `mark_to_market()`; reject over-settlement and missing valuation prices for open positions.

- [ ] **Step 5: Export symbols**

Export ledger constants/classes from `src/serenity_alpha_lab/quant/backtest/__init__.py`.

### Task 3: Verification And Docs

**Files:**
- Create: `docs/portfolio-ledger.md`
- Modify: `docs/development-progress-checklist.md`
- Modify: `docs/development-status.md`
- Modify: `tasks/todo.md`

- [ ] **Step 1: Run focused and related tests**

Run:
- `uv run --extra core --extra dev python -m pytest tests/quant/test_portfolio_ledger.py -q`
- `uv run --extra core --extra dev python -m pytest tests/quant/test_portfolio_ledger.py tests/quant/test_order_state_machine.py tests/quant/test_backtest_artifact.py tests/quant/test_backtest_spec.py tests/architecture/test_architecture_boundaries.py -q`

- [ ] **Step 2: Run broad verification**

Run:
- `uv run --extra core --extra dev python -m pytest -q`
- `uv run --extra core --extra dev python -m compileall -q src tests`
- `scripts/verify-python-dependency-lock.sh`
- `scripts/apply-dsa-baseline-patches.sh --check-only`
- `git rev-parse upstream/dsa-v3.26.1`
- `git diff --check`

- [ ] **Step 3: Document and checkpoint**

Update P4 status docs, `DEC-073`, `AEV-075`, `tasks/todo.md` review, then commit with a Chinese checkpoint message.
