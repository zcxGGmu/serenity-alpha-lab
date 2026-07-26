# Gate G4 Backtest And Risk Review Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete `SAL-P4-022` by adding the Gate G4 review record, executable gate test and project status updates that approve P4 formal backtest evidence for P5 input.

**Architecture:** Gate G4 is a review and evidence task, not a new runtime capability. The new gate test should combine document assertions with a compact executable chain over existing P4 contracts: golden fixture, BacktestRun finalization, formal API route metadata, runtime flags and semantic separation from legacy Signal Evaluation. Documentation updates should advance P4 to `22/22` and make `SAL-P5-001` the next allowed entry while preserving the real Provider/LLM and Worker-loop guards.

**Tech Stack:** Python 3.11, pytest, existing `serenity_alpha_lab` P4 modules, Markdown evidence docs, Git checkpoint workflow.

---

### Task 1: Gate G4 Red Test

**Files:**
- Create: `tests/gates/test_gate_g4_backtest_risk_review.py`
- Read: `tests/gates/test_gate_g3_screen_factor_review.py`
- Read: `tests/quant/test_backtest_golden_property.py`
- Read: `tests/application/test_backtest_run_orchestration.py`
- Read: `tests/application/test_backtest_api.py`

- [ ] **Step 1: Write the failing document test**

```python
def test_gate_g4_review_document_approves_p4_evidence_without_expanding_scope() -> None:
    text = Path("docs/gate-g4-backtest-risk-review.md").read_text(encoding="utf-8")
    assert "GO with accepted risks" in text
```

- [ ] **Step 2: Add executable contract coverage**

```python
def test_gate_g4_executable_contract_links_golden_run_risk_api_and_runtime_boundaries(tmp_path: Path) -> None:
    golden = BacktestGoldenRunner(default_backtest_golden_fixture()).run()
    assert golden.result_hash == "sha256:76e9c93b060bdec6cc05497a477efa2de870168f20d18f349e2a78393d4e78d1"
```

- [ ] **Step 3: Run test to verify Red**

Run: `uv run --extra core --extra dev python -m pytest tests/gates/test_gate_g4_backtest_risk_review.py -q`

Expected: FAIL with `FileNotFoundError` for `docs/gate-g4-backtest-risk-review.md`.

### Task 2: Gate G4 Review Document

**Files:**
- Create: `docs/gate-g4-backtest-risk-review.md`
- Read: `docs/gate-g3-screen-factor-review.md`
- Read: `docs/backtest-api.md`
- Read: `docs/quant-lab.md`

- [ ] **Step 1: Write Gate conclusion**

Include:
- `任务：SAL-P4-022`
- `评审结论：GO with accepted risks`
- P4 completion `22/22`
- Project total `88/129`
- Approval limited to P5 evidence-schema input.

- [ ] **Step 2: Write pass-condition matrix**

Cover:
- Signal/Factor/Portfolio semantics separation.
- BacktestSpec, Artifact, Qlib boundary, order/ledger/cost/execution/corporate actions/rebalance.
- RiskPolicy, BiasAudit, Metrics, BacktestRun, ResourceControl, Golden, API and Quant Lab.

- [ ] **Step 3: Write accepted risks and P5 constraints**

State that real Provider/LLM calls, Evidence Agent execution, Worker loop, Qlib runtime execution and production promotion remain blocked until later explicit tasks.

- [ ] **Step 4: Run target test to verify Green**

Run: `uv run --extra core --extra dev python -m pytest tests/gates/test_gate_g4_backtest_risk_review.py -q`

Expected: PASS.

### Task 3: Status And Progress Sync

**Files:**
- Modify: `docs/development-progress-checklist.md`
- Modify: `docs/development-status.md`
- Modify: `tasks/todo.md`

- [ ] **Step 1: Update task status**

Mark `SAL-P4-022` as `[DONE]`, set actual effort/date, add result/scope/evidence lines and make `SAL-P5-001` the next `READY` task.

- [ ] **Step 2: Add decision/evidence rows**

Add:
- `DEC-086` for Gate G4 review.
- `AEV-088` for Gate G4 executable test and evidence record.

- [ ] **Step 3: Update status snapshot**

Set Gate G4 passed, P4 `22/22`, total `88/129`, recent task `SAL-P4-022`, next task `SAL-P5-001`, and update the next startup prompt.

- [ ] **Step 4: Update task review**

Record subagent fallback, red/green evidence, verification commands and checkpoint placeholders.

### Task 4: Verification And Commit

**Files:**
- Verify: `tests/gates/test_gate_g4_backtest_risk_review.py`
- Verify: P4 related tests
- Verify: status docs

- [ ] **Step 1: Run focused and related tests**

Run:
```bash
uv run --extra core --extra dev python -m pytest tests/gates/test_gate_g4_backtest_risk_review.py -q
uv run --extra core --extra dev python -m pytest tests/gates/test_gate_g4_backtest_risk_review.py tests/application/test_backtest_api.py tests/application/test_backtest_run_orchestration.py tests/application/test_backtest_resource_control.py tests/quant/test_backtest_golden_property.py tests/quant/test_backtest_performance_metrics.py tests/quant/test_backtest_bias_audit.py tests/quant/test_risk_policy.py tests/architecture/test_qlib_version_isolation.py -q
```

- [ ] **Step 2: Run full validation**

Run:
```bash
uv run --extra core --extra dev python -m pytest -q
uv run --extra core --extra dev python -m compileall -q src/serenity_alpha_lab tests
scripts/verify-python-dependency-lock.sh
scripts/apply-dsa-baseline-patches.sh --check-only
git rev-parse upstream/dsa-v3.26.1
git diff --check
```

- [ ] **Step 3: Commit**

Stage only `SAL-P4-022` files and commit:

```bash
git commit -m "docs(P4): 通过 Gate G4 回测与风控评审"
```
