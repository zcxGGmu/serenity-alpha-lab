# SignalEvaluationEngine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete `SAL-P4-002` by migrating legacy DSA signal assessment semantics to `SignalEvaluationEngine` while keeping `SAL-P4-001` snapshots byte-for-byte identical.

**Architecture:** Add a Serenity-owned pure quant `SignalEvaluationEngine` as the semantic model for T+N signal evaluation. Keep legacy DSA `/api/v1/backtest/*` paths and schemas as compatibility surfaces, add a DSA patch that introduces `src.core.signal_evaluation_engine` and updates DSA service/UI naming without defining formal `BacktestSpec` or starting portfolio backtests.

**Tech Stack:** Python 3.11 dataclasses/stdlib, pytest, DSA patch workflow, React/Vitest in isolated DSA worktree.

---

### Task 1: Root SignalEvaluationEngine Contract

**Files:**
- Create: `tests/quant/test_signal_evaluation_engine.py`
- Create: `src/serenity_alpha_lab/quant/signal_evaluation.py`
- Modify: `src/serenity_alpha_lab/quant/__init__.py`

- [ ] **Step 1: Write failing behavior parity tests**

Use `docs/baselines/dsa-v3.26.1/signal-evaluation-characterization/inputs.json`, `engine-evaluations.json`, `decision-signal-evaluations.json`, and `signal-evaluation-summary.json`.

Assert:
- `SignalEvaluationEngine.evaluate_single()` matches every `SAL-P4-001` engine case exactly after stable normalization.
- `SignalEvaluationEngine.evaluate_decision_signal()` matches every structured signal case exactly.
- `SignalEvaluationEngine.compute_summary()` matches the frozen summary.
- `SignalEvaluationConfig.evaluation_type == "signal"` and `engine.semantic_scope == "legacy_signal_evaluation"`.
- `SignalEvaluationEngine` docs and constants do not call itself a formal backtest.

- [ ] **Step 2: Run Red test**

Run:

```bash
.venv/bin/python -m pytest tests/quant/test_signal_evaluation_engine.py -q
```

Expected: FAIL with missing `serenity_alpha_lab.quant.signal_evaluation`.

- [ ] **Step 3: Implement minimal pure engine**

Implement `SignalEvaluationConfig`, `SignalResultLike`, `DailyBarLike`, `SignalEvaluationEngine`, `OVERALL_SENTINEL_CODE`, and public constants. Port the P4-001 semantics without importing DSA runtime source, Provider, LLM, Qlib, repositories, or formal backtest modules.

- [ ] **Step 4: Run Green test**

Run:

```bash
.venv/bin/python -m pytest tests/quant/test_signal_evaluation_engine.py -q
```

Expected: PASS.

### Task 2: DSA Compatibility Patch

**Files:**
- Create/update in worktree: `.worktrees/dsa-v3.26.1/src/core/signal_evaluation_engine.py`
- Modify in worktree: `.worktrees/dsa-v3.26.1/src/services/backtest_service.py`
- Modify in worktree: `.worktrees/dsa-v3.26.1/src/services/decision_signal_outcome_service.py`
- Modify in worktree: `.worktrees/dsa-v3.26.1/apps/dsa-web/src/api/backtest.ts`
- Modify in worktree: `.worktrees/dsa-v3.26.1/apps/dsa-web/src/types/backtest.ts`
- Modify in worktree: `.worktrees/dsa-v3.26.1/apps/dsa-web/src/locales/featureText.ts`
- Modify in worktree: `.worktrees/dsa-v3.26.1/apps/dsa-web/src/i18n/uiText.ts`
- Modify in worktree: `.worktrees/dsa-v3.26.1/apps/dsa-web/src/pages/BacktestPage.tsx`
- Modify in worktree: `.worktrees/dsa-v3.26.1/apps/dsa-web/src/pages/__tests__/BacktestPage.test.tsx`
- Modify in worktree: `.worktrees/dsa-v3.26.1/apps/dsa-web/e2e/smoke.spec.ts`
- Create: `patches/dsa/v3.26.1/0005-migrate-signal-evaluation-engine.patch`
- Modify: `docs/upstream-patches.md`

- [ ] **Step 1: Write failing architecture test for patch presence**

Create a test that fails until patch `0005` exists and contains:
- `src/core/signal_evaluation_engine.py`
- `class SignalEvaluationEngine`
- `evaluation_type`
- UI text `信号评价` and `Signal Evaluation`
- No `/api/v1/quant/backtest-runs`

- [ ] **Step 2: Run Red test**

Run:

```bash
.venv/bin/python -m pytest tests/architecture/test_dsa_signal_evaluation_engine_migration.py -q
```

Expected: FAIL because patch `0005` does not exist.

- [ ] **Step 3: Implement worktree changes**

Add a DSA `SignalEvaluationEngine` compatibility module that reuses the current legacy behavior exactly. Update DSA service imports to use the new name, keep legacy `BacktestEngine` API compatibility, and add `diagnostics["evaluation_type"] = "signal"` without changing legacy route paths or Pydantic schema fields.

Update Web copy so visible UI labels describe signal evaluation rather than strategy/portfolio backtesting, while retaining `/backtest` as the legacy route.

- [ ] **Step 4: Generate patch**

Run:

```bash
git -C .worktrees/dsa-v3.26.1 diff -- src/core/signal_evaluation_engine.py src/services/backtest_service.py src/services/decision_signal_outcome_service.py apps/dsa-web/src/api/backtest.ts apps/dsa-web/src/types/backtest.ts apps/dsa-web/src/locales/featureText.ts apps/dsa-web/src/i18n/uiText.ts apps/dsa-web/src/pages/BacktestPage.tsx apps/dsa-web/src/pages/__tests__/BacktestPage.test.tsx apps/dsa-web/e2e/smoke.spec.ts > patches/dsa/v3.26.1/0005-migrate-signal-evaluation-engine.patch
```

- [ ] **Step 5: Run patch test**

Run:

```bash
.venv/bin/python -m pytest tests/architecture/test_dsa_signal_evaluation_engine_migration.py -q
```

Expected: PASS.

### Task 3: Snapshot And Web Verification

**Files:**
- Modify: `scripts/run-dsa-signal-evaluation-characterization.sh` only if needed to assert new alias without changing generated snapshot payloads.
- No changes to `docs/baselines/dsa-v3.26.1/signal-evaluation-characterization/*.json` unless a deliberate failure proves accidental drift.

- [ ] **Step 1: Verify P4-001 snapshots remain identical**

Run:

```bash
scripts/run-dsa-signal-evaluation-characterization.sh
```

Expected: PASS and no baseline JSON diff.

- [ ] **Step 2: Run DSA patch check**

Run:

```bash
scripts/apply-dsa-baseline-patches.sh --check-only
```

Expected: `0001..0005` are already applied or cleanly applicable.

- [ ] **Step 3: Run focused DSA Web tests**

Run from `.worktrees/dsa-v3.26.1/apps/dsa-web`:

```bash
npm run test -- src/pages/__tests__/BacktestPage.test.tsx src/App.test.tsx src/components/layout/__tests__/SidebarNav.test.tsx
```

Expected: PASS.

### Task 4: Documentation, Status, And Checkpoint

**Files:**
- Create: `docs/signal-evaluation-engine.md`
- Modify: `docs/development-progress-checklist.md`
- Modify: `docs/development-status.md`
- Modify: `tasks/todo.md`

- [ ] **Step 1: Document migration**

Record semantic boundaries, DSA compatibility layer, `evaluation_type=signal`, unchanged P4-001 snapshots, UI/API wording changes, non-goals, and verification evidence.

- [ ] **Step 2: Update progress/status**

Mark `SAL-P4-002` DONE, move P4 to `2/22`, total to `68/129`, add `DEC-066` and `AEV-068`, and set `SAL-P4-003` READY but not started.

- [ ] **Step 3: Run final verification**

Run target tests, related architecture/quant tests, full pytest, compileall, dependency lock guard, DSA patch check, immutable tag check, status-anchor scan, and `git diff --check`.

- [ ] **Step 4: Commit**

Stage only `SAL-P4-002` files and commit with a Chinese checkpoint message.
