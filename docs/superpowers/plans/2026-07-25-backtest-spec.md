# BacktestSpec Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Define the formal `BacktestSpec` contract for SAL-P4-003 without running any portfolio backtest.

**Architecture:** Add an immutable `quant.backtest` spec module that binds concrete Dataset, Universe, Strategy, Execution, Cost and Risk inputs. The module derives a platform-stable `spec_hash` from canonical JSON and keeps legacy DSA Signal Evaluation out of the formal portfolio backtest namespace.

**Tech Stack:** Python dataclasses, `Decimal`, canonical JSON, pytest, existing Dataset/Screen/Factor version guard patterns.

---

### Task 1: Red Contract Tests

**Files:**
- Create: `tests/quant/test_backtest_spec.py`

- [x] **Step 1: Write failing tests for the full spec surface**

```python
def test_backtest_spec_binds_formal_inputs_and_stable_hash():
    spec = _formal_backtest_spec()
    assert spec.spec_hash.startswith("sha256:")
    assert spec.dataset.dataset_versions["adjusted_daily_bars"].startswith("dsv_")
    assert spec.universe.universe_version_id.startswith("dsv_")
    assert spec.strategy.screen_definition_version_id.startswith("sdv_")
    assert spec.execution.signal_timing == "after_close"
    assert spec.costs.commission_bps == Decimal("3.0")
    assert spec.risk.max_weight_per_instrument == Decimal("0.10")
```

- [x] **Step 2: Run Red test**

Run: `.venv/bin/python -m pytest tests/quant/test_backtest_spec.py -q`
Expected: fail with missing `serenity_alpha_lab.quant.backtest.spec`.

### Task 2: BacktestSpec Implementation

**Files:**
- Create: `src/serenity_alpha_lab/quant/backtest/spec.py`
- Modify: `src/serenity_alpha_lab/quant/backtest/__init__.py`

- [ ] **Step 1: Implement immutable component DTOs**

Add `BacktestDatasetSpec`, `BacktestUniverseSpec`, `BacktestStrategySpec`, `BacktestExecutionSpec`, `BacktestCostSpec`, `BacktestRiskSpec` and `BacktestSpec`.

- [ ] **Step 2: Add validation helpers**

Validate concrete `dsv_*`, `sdv_*`, `fdv_*`, `sha256:*`, aware timestamps, date ranges, non-negative cost inputs, positive capital and bounded risk ratios.

- [ ] **Step 3: Add canonical JSON and hash**

Derive `spec_hash = sha256(canonical_json(spec_payload))`, sort mapping keys, serialize `Decimal` as strings, and exclude `spec_hash` itself from the hash payload.

- [ ] **Step 4: Export public API**

Update `quant.backtest.__init__` with constants, DTOs and `BacktestSpecError`.

### Task 3: Documentation And Status

**Files:**
- Create: `docs/backtest-spec.md`
- Modify: `docs/development-progress-checklist.md`
- Modify: `docs/development-status.md`
- Modify: `tasks/todo.md`

- [ ] **Step 1: Document formal scope**

Document Dataset/Universe/Strategy/Execution/Cost/Risk input groups, canonical hash semantics, legacy Signal Evaluation separation and non-goals.

- [ ] **Step 2: Update progress and recovery docs**

Mark `SAL-P4-003` done only after verification; set P4 `3/22`, total `69/129`, and move `SAL-P4-004` to READY.

- [ ] **Step 3: Add review evidence**

Append `AEV-069` and `DEC-067` with Red/Green evidence and no-go boundary confirmation.

### Task 4: Verification And Checkpoint

**Files:**
- No new files beyond Task 1-3

- [ ] **Step 1: Run focused tests**

Run: `.venv/bin/python -m pytest tests/quant/test_backtest_spec.py -q`
Expected: pass.

- [ ] **Step 2: Run related suites**

Run: `.venv/bin/python -m pytest tests/quant/test_backtest_spec.py tests/architecture/test_dsa_signal_evaluation_engine_migration.py tests/architecture/test_dsa_signal_evaluation_characterization.py -q`
Expected: pass.

- [ ] **Step 3: Run final guards**

Run compileall, dependency lock guard, immutable tag check, status-anchor scan and `git diff --check`.

- [ ] **Step 4: Commit**

Create a Chinese checkpoint commit for `SAL-P4-003`.
