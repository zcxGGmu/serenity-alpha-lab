# Corporate Action Ledger Posting Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete `SAL-P4-012` by posting corporate actions into the formal portfolio ledger for cash dividends, bonus/split shares, rights issues and delisting liquidation.

**Architecture:** Extend the pure `quant.backtest.ledger` event model with a `corporate_action` ledger event and deterministic corporate action records. Add a narrow `quant.backtest.corporate_actions` processor that consumes P2 `CorporateAction` records or explicit delisting liquidation inputs and posts them to `PortfolioLedger`; it must not start a formal backtest run, mutate raw/adjusted Dataset prices, compute Risk/Metric/Audit, call Qlib, or invoke real Provider/LLM.

**Tech Stack:** Python dataclasses, `Decimal`, existing `PortfolioLedger`, existing P2 `datasets.corporate_actions`, pytest.

---

### Task 1: Red Contract Tests

**Files:**
- Create: `tests/quant/test_corporate_action_ledger.py`
- Modify: `tasks/todo.md`

- [ ] **Step 1: Add failing tests**

```python
def test_corporate_actions_post_cash_dividend_bonus_rights_and_delisting_to_ledger():
    # Build a ledger with one settled buy lot, then post:
    # cash dividend -> receivable, bonus share -> quantity up/cost basis unchanged,
    # rights issue -> payable/new lot, delisting liquidation -> remove position/receivable.
```

- [ ] **Step 2: Run Red target**

Run: `uv run --extra core --extra dev python -m pytest tests/quant/test_corporate_action_ledger.py -q`
Expected: FAIL with missing `serenity_alpha_lab.quant.backtest.corporate_actions`.

### Task 2: Ledger Event Extension

**Files:**
- Modify: `src/serenity_alpha_lab/quant/backtest/ledger.py`
- Modify: `src/serenity_alpha_lab/quant/backtest/__init__.py`

- [ ] **Step 1: Add corporate action ledger types**

Add `CorporateActionLedgerType`, `CorporateActionRecord`, `LedgerEventType.CORPORATE_ACTION`, event fields for `corporate_action_id`, `corporate_action_type` and signed `share_delta`.

- [ ] **Step 2: Add posting methods**

Add explicit `PortfolioLedger.record_cash_dividend()`, `record_bonus_share()`, `record_share_split()`, `record_rights_issue()` and `record_delisting_liquidation()` methods. Each method appends one immutable ledger event, preserves deterministic replay and rejects missing positions or invalid amounts.

- [ ] **Step 3: Keep accounting invariant**

Corporate action events must update only ledger cash/receivable/payable/lots:
cash dividends create receivables, bonus/split shares increase lot quantities without changing total cost basis, rights issues create payables and a new cost-basis lot, delisting liquidation removes lots and creates receivables. Equity remains `cash + position_market_value + receivables - payables`.

### Task 3: Processor Boundary

**Files:**
- Create: `src/serenity_alpha_lab/quant/backtest/corporate_actions.py`
- Modify: `src/serenity_alpha_lab/quant/backtest/__init__.py`

- [ ] **Step 1: Implement processor**

Implement `CorporateActionLedgerProcessor` with `apply()` for P2 `CorporateAction` records and `apply_delisting_liquidation()` for explicit delisting liquidation fixtures. Derive stable action IDs from instrument/ex-date/type/provider and never read `AdjustedDailyBar` prices or factors.

- [ ] **Step 2: Export symbols**

Export processor and ledger corporate action symbols from `quant.backtest`.

### Task 4: Documentation And Status

**Files:**
- Create: `docs/corporate-action-ledger-posting.md`
- Modify: `docs/development-progress-checklist.md`
- Modify: `docs/development-status.md`
- Modify: `tasks/todo.md`

- [ ] **Step 1: Add evidence doc**

Document the contract version, event semantics, economic value checks, raw/adjusted price non-double-counting guard, non-goals and verification evidence.

- [ ] **Step 2: Update progress and status**

Mark `SAL-P4-012` complete only after verification; update P4 progress to `12/22`, total to `78/129`, add `DEC-076` and `AEV-078`, and make `SAL-P4-013` READY without starting it.

### Task 5: Verification And Checkpoint

**Files:**
- Verify all modified source/docs/tests.

- [ ] **Step 1: Run focused and related tests**

Run focused target plus related `PortfolioLedger`, P2 corporate actions Dataset, A-share execution, cost, order, BacktestSpec and architecture boundary suites.

- [ ] **Step 2: Run full verification**

Run full pytest, compileall, dependency lock guard, DSA patch check, immutable upstream tag check, status-anchor scan and `git diff --check`.

- [ ] **Step 3: Commit**

Stage only SAL-P4-012 files and create the required Chinese checkpoint commit.
