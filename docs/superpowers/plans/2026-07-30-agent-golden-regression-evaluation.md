# Agent Golden Regression Evaluation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an offline Agent golden and regression evaluation boundary for `SAL-P5-017`.

**Architecture:** Add an application-layer evaluator that owns golden-case metadata, deterministic stub outputs, scoring rules and report serialization. The evaluator consumes structured `ResearchClaim` / `ReportCitation` records only, so it can measure citation accuracy, unsupported numeric claims and safety regressions without calling Providers, LLMs, Workers or Qlib.

**Tech Stack:** Python dataclasses/enums, existing P5 evidence schema models, pytest, architecture import guards.

---

### Task 1: Golden Evaluation Contract

**Files:**
- Create: `tests/application/test_agent_golden_regression_evaluation.py`
- Create: `src/serenity_alpha_lab/application/agent_evaluation.py`
- Modify: `tests/architecture/test_architecture_boundaries.py`
- Modify: `src/serenity_alpha_lab/application/__init__.py`

- [x] **Step 1: Write failing tests**

```python
def test_default_golden_catalog_has_required_coverage():
    catalog = default_agent_golden_catalog()
    assert len(catalog.cases) >= 50
    assert {case.category for case in catalog.cases} >= {...}
```

- [x] **Step 2: Run Red target**

Run: `uv run --extra core --extra dev python -m pytest tests/application/test_agent_golden_regression_evaluation.py -q`

Expected: FAIL with `ModuleNotFoundError: No module named 'serenity_alpha_lab.application.agent_evaluation'`.

- [x] **Step 3: Implement minimal offline evaluator**

```python
@dataclass(frozen=True, slots=True)
class AgentGoldenCase:
    case_id: str
    category: AgentGoldenCaseCategory
    market: str
    expected_citation_evidence_ids: tuple[str, ...]
```

- [x] **Step 4: Add scorer thresholds**

```python
summary = AgentRegressionEvaluator().evaluate(catalog, predictions)
assert summary.citation_accuracy >= 0.95
assert summary.unsupported_numeric_rate < 0.01
assert summary.safety_core_passed is True
```

- [x] **Step 5: Add regression comparison**

```python
comparison = compare_agent_evaluation_runs(baseline, current)
assert comparison.passed is False
```

- [x] **Step 6: Run Green target**

Run: `uv run --extra core --extra dev python -m pytest tests/application/test_agent_golden_regression_evaluation.py tests/architecture/test_architecture_boundaries.py::test_agent_evaluation_stays_offline_and_runtime_free -q`

Expected: PASS.

### Task 2: Evidence and Status Sync

**Files:**
- Create: `docs/agent-golden-regression-evaluation.md`
- Modify: `docs/development-progress-checklist.md`
- Modify: `docs/development-status.md`
- Modify: `tasks/todo.md`

- [x] **Step 1: Document SAL-P5-017 evidence**

Record contract names, coverage, metric thresholds, non-goals and verification commands.

- [x] **Step 2: Update progress and recovery state**

Mark `SAL-P5-017` as done only after validation, set next task to `SAL-P5-018` Gate G5, and keep Gate G5 unpassed.

- [x] **Step 3: Run final verification**

Run:
```bash
uv run --extra core --extra dev python -m pytest tests/application/test_agent_golden_regression_evaluation.py tests/architecture/test_architecture_boundaries.py::test_agent_evaluation_stays_offline_and_runtime_free -q
uv run --extra core --extra dev python -m pytest -q
uv run --extra core --extra dev python -m compileall -q src/serenity_alpha_lab tests
scripts/verify-python-dependency-lock.sh
git rev-parse upstream/dsa-v3.26.1
git diff --check
```

Expected: all PASS; upstream tag remains `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`.

- [x] **Step 4: Commit**

```bash
git add src/serenity_alpha_lab/application/agent_evaluation.py tests/application/test_agent_golden_regression_evaluation.py tests/architecture/test_architecture_boundaries.py src/serenity_alpha_lab/application/__init__.py docs/agent-golden-regression-evaluation.md docs/development-progress-checklist.md docs/development-status.md tasks/todo.md docs/superpowers/plans/2026-07-30-agent-golden-regression-evaluation.md
git commit -m "feat(P5): 建立 Agent 金标回归评测"
```
