# RiskPolicy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement `SAL-P4-014` deterministic RiskPolicy for formal portfolio backtests.

**Architecture:** Add a pure backtest risk module that consumes `BacktestSpec`, `PortfolioLedger`, `RebalancePlan`, explicit exposure/liquidity/drawdown inputs and returns immutable pass/warn/block/not-evaluable results. The module must not mutate orders, ledgers, datasets, APIs, UI, Qlib, Worker runtime or legacy DSA backtest compatibility surfaces.

**Tech Stack:** Python dataclasses, Decimal math, pytest, existing P4 BacktestSpec/Ledger/Rebalance contracts.

---

### Task 1: Contract Tests

**Files:**
- Create: `tests/quant/test_risk_policy.py`
- Read: `tests/quant/test_rebalance_target_weights.py`
- Read: `tests/quant/test_portfolio_ledger.py`

- [x] **Step 1: Write failing tests**

```python
def test_risk_policy_blocks_weight_and_industry_breaches():
    result = RiskPolicyEvaluator(spec=spec).evaluate(...)
    assert result.status is RiskDecisionStatus.BLOCK
```

- [x] **Step 2: Run test to verify it fails**

Run: `uv run --extra core --extra dev python -m pytest tests/quant/test_risk_policy.py -q`
Expected: FAIL with `ModuleNotFoundError: serenity_alpha_lab.quant.backtest.risk`

### Task 2: Risk Module

**Files:**
- Create: `src/serenity_alpha_lab/quant/backtest/risk.py`
- Modify: `src/serenity_alpha_lab/quant/backtest/__init__.py`

- [x] **Step 1: Implement DTOs**

Create immutable DTOs for `DeterministicRiskPolicy`, `RiskDecisionStatus`, `RiskRuleStatus`, `RiskRuleOutcome`, `InstrumentRiskProfile` and `RiskPolicyResult`.

- [x] **Step 2: Implement evaluator**

Implement `RiskPolicyEvaluator.evaluate(...)` for individual weight, industry exposure, style exposure, liquidity floor, turnover and drawdown rules using `BacktestRiskSpec` as the primary rule source.

- [x] **Step 3: Keep not-evaluable blocking**

Missing required prices, exposure profiles, liquidity, turnover inputs or drawdown inputs must return `not_evaluable` rule outcomes and an overall `block` result.

- [x] **Step 4: Export symbols**

Update `quant.backtest.__init__` to export the RiskPolicy contract symbols.

### Task 3: Evidence And Status

**Files:**
- Create: `docs/risk-policy.md`
- Modify: `docs/development-progress-checklist.md`
- Modify: `docs/development-status.md`
- Modify: `tasks/todo.md`

- [ ] **Step 1: Document scope and verification**

Record rules, status semantics, non-goals and verification evidence in `docs/risk-policy.md`.

- [ ] **Step 2: Update recovery docs**

Mark `SAL-P4-014` done, set P4 to `14/22`, total to `80/129`, and make `SAL-P4-015` the only next READY task.

- [ ] **Step 3: Verify**

Run focused, related and full pytest; compileall; dependency lock guard; DSA patch check; upstream tag check; status anchor scan; `git diff --check`.

- [ ] **Step 4: Commit**

Stage only SAL-P4-014 files and create a Chinese checkpoint commit.
