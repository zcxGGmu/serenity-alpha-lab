# DSA Signal Evaluation Characterization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete `SAL-P4-001` by freezing the current DSA Signal Evaluation behavior and legacy API surface before any formal portfolio backtest work starts.

**Architecture:** Add a standalone P4 characterization baseline under `docs/baselines/dsa-v3.26.1/signal-evaluation-characterization/` and a deterministic script that regenerates it from the locked DSA worktree. The baseline extends the P0 report/signal goldens with negated recommendation text, missing OHLC data, structured DecisionSignal evaluation, `/api/v1/backtest/*` schema metadata, and Agent read-tool payload surfaces. It does not rename the legacy DSA code, migrate to `SignalEvaluationEngine`, define `BacktestSpec`, run formal portfolio backtests, call real Provider/LLM, or start Evidence Agent.

**Tech Stack:** Bash, Python 3.11, locked DSA worktree `.worktrees/dsa-v3.26.1`, DSA `BacktestEngine`, FastAPI route/schema introspection, JSON fixtures, pytest.

---

### Task 1: Red Characterization Tests

**Files:**
- Create: `tests/architecture/test_dsa_signal_evaluation_characterization.py`

- [ ] **Step 1: Write failing tests for P4 baseline files**

```python
def test_signal_evaluation_characterization_baseline_exists() -> None:
    baseline = Path("docs/baselines/dsa-v3.26.1/signal-evaluation-characterization")
    assert (baseline / "summary.json").exists()
```

- [ ] **Step 2: Assert required behavior cases and API surface**

```python
def test_signal_evaluation_characterization_covers_p4_required_cases() -> None:
    evaluations = json.loads((BASELINE / "engine-evaluations.json").read_text())["items"]
    assert {"negated_buy_wait_cash", "negated_sell_hold_long", "missing_end_close", "missing_high_low"} <= {item["case"] for item in evaluations}
```

- [ ] **Step 3: Run target test and confirm Red**

Run: `.venv/bin/python -m pytest tests/architecture/test_dsa_signal_evaluation_characterization.py -q`

Expected: FAIL because the test and baseline do not exist yet.

### Task 2: Deterministic Baseline Generator

**Files:**
- Create: `scripts/run-dsa-signal-evaluation-characterization.sh`

- [ ] **Step 1: Add locked-worktree shell wrapper**

Use the same tag, worktree, cache root, patch root, path normalization, registered-patch verification and `--update-snapshots` flow as `scripts/run-dsa-report-signal-baseline.sh`.

- [ ] **Step 2: Generate engine and DecisionSignal fixtures**

Create fixed inputs for buy/sell/hold/watch, stop-loss/take-profit, ambiguous same-day targets, insufficient bars, negated buy/sell text and missing OHLC fields. Evaluate with `BacktestEngine.evaluate_single()` and `BacktestEngine.evaluate_decision_signal()`.

- [ ] **Step 3: Generate API and Agent read-tool surface fixtures**

Introspect DSA `api.v1.endpoints.backtest.router`, `api.v1.schemas.backtest` Pydantic schemas and `src.agent.tools.backtest_tools.ALL_BACKTEST_TOOLS`. Record legacy `/api/v1/backtest/*` names as Signal Evaluation compatibility surfaces, not formal portfolio backtest APIs.

- [ ] **Step 4: Write stable JSON outputs and compare snapshots**

Write `inputs.json`, `engine-evaluations.json`, `decision-signal-evaluations.json`, `signal-evaluation-summary.json`, `api-surface.json`, `content-hashes.json` and `summary.json`; default mode diffs against committed snapshots, `--update-snapshots` replaces them.

### Task 3: Evidence Docs And Progress

**Files:**
- Create: `docs/dsa-signal-evaluation-characterization.md`
- Modify: `docs/development-progress-checklist.md`
- Modify: `docs/development-status.md`
- Modify: `tasks/todo.md`

- [ ] **Step 1: Document semantics**

Explain that DSA `BacktestEngine` currently evaluates report/DecisionSignal direction over T+N bars, simulates only a long/cash recommendation with stop-loss/take-profit checks, and is not a formal portfolio backtest.

- [ ] **Step 2: Update task ledger**

Move `SAL-P4-001` to `DONE`, set P4 progress to `1/22`, total progress to `67/129`, add `DEC-065` and `AEV-067`, and move `SAL-P4-002` to `READY`.

- [ ] **Step 3: Update recovery status**

Refresh `docs/development-status.md` and `tasks/todo.md` review with actual verification evidence, implementation checkpoint placeholder and next-session prompt. Keep `SAL-P4-003` and formal BacktestSpec blocked until `SAL-P4-002`.

### Task 4: Verification And Checkpoint

**Files:**
- Modify: `tasks/todo.md`

- [ ] **Step 1: Run focused Red/Green and baseline script**

Run target test before and after implementation. Run `scripts/run-dsa-signal-evaluation-characterization.sh --update-snapshots`, then `scripts/run-dsa-signal-evaluation-characterization.sh`.

- [ ] **Step 2: Run related and full verification**

Run architecture target, signal/report baseline script, full pytest, compileall, dependency lock guard, DSA patch check, immutable tag check, status-anchor scan and `git diff --check`.

- [ ] **Step 3: Commit**

Stage only `SAL-P4-001` files and create a Chinese checkpoint commit with completion, risk, verification and task ID.
