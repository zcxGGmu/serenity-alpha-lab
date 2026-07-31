# Order State Machine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement `SAL-P4-008` by defining a deterministic formal backtest order state machine with immutable order events, rejection, partial fill and expiration semantics.

**Architecture:** Add a pure `quant.backtest` contract module that owns `Order`, `OrderEvent`, order states and replay logic. The module records append-only state events and deterministic records only; Ledger replay, fees, A-share execution rules, risk, metrics, APIs and worker execution remain later P4 tasks.

**Tech Stack:** Python 3.11 dataclasses, `StrEnum`, `Decimal`, timezone-aware `datetime`, existing `InstrumentId`, pytest contract tests.

---

## Files

- Create: `src/serenity_alpha_lab/quant/backtest/orders.py` for immutable order/event DTOs, state transition validation and idempotent replay.
- Modify: `src/serenity_alpha_lab/quant/backtest/__init__.py` to export order state machine symbols.
- Create: `tests/quant/test_order_state_machine.py` for Red/Green contract tests.
- Create: `docs/order-state-machine.md` for scope, state/event semantics, non-goals and verification evidence.
- Modify: `docs/development-progress-checklist.md`, `docs/development-status.md` and `tasks/todo.md` during closeout.

## Task 1: Red Contract Tests

**Files:**
- Create: `tests/quant/test_order_state_machine.py`

- [ ] **Step 1: Write failing tests**
  - Test an order is created in `created`, accepts into `accepted`, partially fills with cumulative quantity and fills once target quantity is reached.
  - Test invalid transitions are rejected, including fill before accept, accepting a terminal order, overfill and cancelling a filled order.
  - Test explicit rejection and expiration store reasons and make terminal states immutable.
  - Test replaying the same event stream twice produces the same order snapshot and duplicate event IDs are ignored idempotently.
  - Test `to_record()` serializes order intent, status, cumulative fill, last event and event records without Ledger/cash/position output.

- [ ] **Step 2: Run Red**
  - Run: `uv run --extra core --extra dev python -m pytest tests/quant/test_order_state_machine.py -q`
  - Expected: FAIL with `ModuleNotFoundError: serenity_alpha_lab.quant.backtest.orders`.

## Task 2: Order State Machine Implementation

**Files:**
- Create: `src/serenity_alpha_lab/quant/backtest/orders.py`
- Modify: `src/serenity_alpha_lab/quant/backtest/__init__.py`

- [ ] **Step 1: Add immutable DTOs**
  - Define `OrderSide`, `OrderType`, `OrderStatus`, `OrderEventType`, `TimeInForce`, `OrderIntent`, `OrderEvent` and `Order`.
  - Validate required IDs, canonical `InstrumentId`, positive quantities, finite prices, timezone-aware timestamps and lowercase `sha256:*` spec hashes.

- [ ] **Step 2: Add transitions**
  - Allow `created -> accepted -> partially_filled -> filled`.
  - Allow `created/accepted/partially_filled -> rejected`, `expired` or `cancelled` where semantically valid.
  - Reject transitions out of terminal states and reject fills that exceed target quantity.

- [ ] **Step 3: Add replay and idempotency**
  - Implement `Order.create()` and `Order.replay(intent, events)`.
  - Make duplicate `event_id` replay idempotent when payload is identical.
  - Raise `OrderStateMachineError` for duplicate event IDs with conflicting payload.

- [ ] **Step 4: Export symbols**
  - Export order DTOs and constants from `quant.backtest.__init__`.
  - Keep the module pure: no Qlib, FastAPI, SQLAlchemy, Provider, LLM, Ledger or Worker imports.

- [ ] **Step 5: Run Green**
  - Run: `uv run --extra core --extra dev python -m pytest tests/quant/test_order_state_machine.py -q`
  - Expected: PASS.

## Task 3: Docs, Status and Verification

**Files:**
- Create: `docs/order-state-machine.md`
- Modify: `docs/development-progress-checklist.md`
- Modify: `docs/development-status.md`
- Modify: `tasks/todo.md`

- [ ] **Step 1: Add evidence doc**
  - Document state/event semantics, idempotent replay, rejection/partial fill/expiration behavior, non-goals and verification evidence.

- [ ] **Step 2: Update progress/state**
  - Mark `SAL-P4-008` done only after verification.
  - Move P4 progress from `7/22` to `8/22`, total from `73/129` to `74/129`.
  - Add decision/evidence rows for the order state machine and make `SAL-P4-009` the next READY task.

- [ ] **Step 3: Run verification**
  - Focused: `uv run --extra core --extra dev python -m pytest tests/quant/test_order_state_machine.py -q`
  - Related: `uv run --extra core --extra dev python -m pytest tests/quant/test_order_state_machine.py tests/quant/test_backtest_spec.py tests/quant/test_backtest_artifact.py tests/architecture/test_architecture_boundaries.py -q`
  - Full: `uv run --extra core --extra dev python -m pytest -q`
  - Compile: `uv run --extra core --extra dev python -m compileall -q src tests`
  - Guards: `scripts/verify-python-dependency-lock.sh`, `scripts/apply-dsa-baseline-patches.sh --check-only`, `git rev-parse upstream/dsa-v3.26.1`, `git diff --check`.

- [ ] **Step 4: Checkpoint**
  - Stage only `SAL-P4-008` files.
  - Commit with Chinese message: `feat(P4): 实现订单状态机`.

## Guardrails

- Do not start formal portfolio backtest runs or produce formal `BacktestArtifactBundle` results.
- Do not implement Ledger, fees/slippage, A-share execution rules, corporate actions, RiskPolicy, metrics, BacktestRun orchestration, API, Quant Lab, Evidence Agent, Worker loop, real Provider calls or real LLM calls.
- Do not treat Qlib internal backtest evidence, Dataset conversion artifacts, legacy DSA Signal Evaluation, AlphaSift T+N evaluation or Screen results as formal portfolio backtests.
- Do not import Qlib at module import time or accept arbitrary Python module paths.
- Keep `upstream/dsa-v3.26.1` immutable and do not submit `.worktrees`, `.cache`, `.venv`, `node_modules`, `static`, Playwright artifacts, pycache or unrelated files.
