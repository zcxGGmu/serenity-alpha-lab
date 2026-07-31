# Backtest Performance Metrics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `SAL-P4-016` unified performance metrics for formal portfolio backtest outputs without starting a formal backtest run.

**Architecture:** Add a pure `quant.backtest.metrics` module that consumes an existing `BacktestSpec`, explicit equity/benchmark/cost/turnover/trade/exposure observations, and emits immutable metric reports with formula-version metadata. The module computes portfolio, risk, drawdown, trading, cost, benchmark and industry-exposure metrics, but it does not orchestrate BacktestRun, mutate Ledger/Risk/Audit, call Qlib, expose APIs, or start Worker runtime.

**Tech Stack:** Python dataclasses, `Decimal`, pytest, existing `BacktestSpec` and `CostBreakdown` contracts.

---

### Task 1: Red Contract Tests

**Files:**
- Create: `tests/quant/test_backtest_performance_metrics.py`
- Create: `docs/superpowers/plans/2026-07-26-backtest-performance-metrics.md`

- [ ] **Step 1: Write failing tests**

Create tests for:
- metric registry formula versions and sample metadata
- return/risk/drawdown metrics
- win rate, profit/loss ratio, turnover and cost ratios
- benchmark tracking error / information ratio
- industry exposure summaries
- bad input and import-boundary guards

- [ ] **Step 2: Run Red target**

Run: `uv run --extra core --extra dev python -m pytest tests/quant/test_backtest_performance_metrics.py -q`

Expected: FAIL with missing `serenity_alpha_lab.quant.backtest.metrics`.

### Task 2: Metrics Module

**Files:**
- Create: `src/serenity_alpha_lab/quant/backtest/metrics.py`
- Modify: `src/serenity_alpha_lab/quant/backtest/__init__.py`

- [ ] **Step 1: Implement immutable DTOs**

Add `BacktestPerformanceMetricPolicy`, `BacktestEquityPoint`, `BacktestTurnoverObservation`, `BacktestTradeOutcome`, `BacktestIndustryExposurePoint`, `BacktestMetricDefinition`, `BacktestMetricRegistry` and `BacktestPerformanceMetricReport`.

- [ ] **Step 2: Implement calculator**

Add `BacktestPerformanceMetricCalculator.calculate(...)` using explicit formula versions:
- cumulative return = ending equity / starting equity - 1
- annualized return = `(1 + cumulative_return) ** (annualization_days / period_count) - 1`
- annualized volatility = sample standard deviation of period returns times `sqrt(annualization_days)`
- Sharpe = `(annualized_return - risk_free_rate) / annualized_volatility`
- Sortino = `(annualized_return - risk_free_rate) / annualized_downside_deviation`
- Calmar = annualized return / max drawdown
- max drawdown = maximum peak-to-trough loss
- turnover rate = average `(buy_notional + sell_notional) / equity`
- cost ratio = total transaction cost / total gross traded amount
- tracking error = sample standard deviation of active returns times `sqrt(annualization_days)`
- information ratio = active annualized return / tracking error

- [ ] **Step 3: Export symbols**

Add metrics symbols to `quant.backtest.__init__`.

### Task 3: Evidence And Verification

**Files:**
- Create: `docs/backtest-performance-metrics.md`
- Modify: `docs/development-progress-checklist.md`
- Modify: `docs/development-status.md`
- Modify: `tasks/todo.md`

- [ ] **Step 1: Document scope and formulas**

Record metric definitions, input requirements, sample/frequency metadata, non-goals and verification evidence.

- [ ] **Step 2: Run verification**

Run focused, related, full pytest, compileall, dependency lock guard, DSA patch check, immutable tag check and `git diff --check`.

- [ ] **Step 3: Commit**

Stage only `SAL-P4-016` files and create a Chinese checkpoint commit.
