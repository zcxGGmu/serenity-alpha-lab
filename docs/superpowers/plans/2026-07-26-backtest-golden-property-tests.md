# Backtest Golden And Property Tests Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build SAL-P4-019 fixed-data golden and property-style tests for the P4 formal portfolio backtest component chain.

**Architecture:** Add a pure `quant.backtest.golden` fixture harness that composes existing BacktestSpec, Order, A-share execution, CostModel, PortfolioLedger, corporate action posting and performance metrics on a hand-computable synthetic A-share sample. The harness stays offline and deterministic, supports full and chunked fixture reads, and labels outputs as golden validation evidence rather than a promoted production backtest.

**Tech Stack:** Python 3.11 dataclasses/enums/Decimal/hashlib/json, existing P4 backtest DTOs, pytest offline tests, no Hypothesis dependency and no Qlib/API/Worker runtime.

---

### Task 1: Red Golden Tests

**Files:**
- Create: `tests/quant/test_backtest_golden_property.py`
- Read: `src/serenity_alpha_lab/quant/backtest/*`

- [x] **Step 1: Add failing tests**

```python
from serenity_alpha_lab.quant.backtest.golden import default_backtest_golden_fixture

def test_placeholder_red():
    assert default_backtest_golden_fixture()
```

- [x] **Step 2: Run target Red**

Run: `uv run --extra core --extra dev python -m pytest tests/quant/test_backtest_golden_property.py -q`

Expected: FAIL with `ModuleNotFoundError: No module named 'serenity_alpha_lab.quant.backtest.golden'`.

### Task 2: Golden Fixture Harness

**Files:**
- Create: `src/serenity_alpha_lab/quant/backtest/golden.py`
- Modify: `src/serenity_alpha_lab/quant/backtest/__init__.py`
- Test: `tests/quant/test_backtest_golden_property.py`

- [x] **Step 1: Implement immutable fixture records**

Define `BacktestGoldenBar`, `BacktestGoldenFixture`, `BacktestGoldenResult` and `BacktestGoldenRunner`.

- [x] **Step 2: Build the default fixture**

The default fixture must contain 3 instruments and 20 trading days. Events must include:

```text
600519.XSHG buy fill, T+1 restricted sell, cash dividend, later sell fill
000001.XSHE suspended buy rejection
300750.XSHE limit-up buy expiration
```

- [x] **Step 3: Support chunked reads**

`BacktestGoldenFixture.iter_bar_chunks(chunk_size)` must reject non-positive chunk sizes and flatten to the same ordered bars as a full read.

- [x] **Step 4: Compose existing components**

The runner must create orders through `Order`, execute fills/rejections with `AShareExecutionModel`, post filled trades to `PortfolioLedger`, apply one cash dividend through `CorporateActionLedgerProcessor`, compute daily equity points and calculate `BacktestPerformanceMetricReport`.

### Task 3: Verification And Documentation

**Files:**
- Create: `docs/backtest-golden-property-tests.md`
- Modify: `docs/development-progress-checklist.md`
- Modify: `docs/development-status.md`
- Modify: `tasks/todo.md`

- [x] **Step 1: Document scope and expected values**

Record fixture coverage, key expected values and non-goals.

- [x] **Step 2: Run focused and related tests**

Run focused, related P4 backtest suites, full pytest, compileall, dependency lock guard, DSA patch check, immutable tag check and `git diff --check`.

- [x] **Step 3: Update status and checkpoint**

Mark SAL-P4-019 complete, P4 progress `19/22`, total `85/129`, and set SAL-P4-020 as READY but not started before creating the Chinese checkpoint commit.
