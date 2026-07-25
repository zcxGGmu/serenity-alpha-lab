# Backtest Bias Audit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement `SAL-P4-015` backtest bias audit for formal portfolio backtests.

**Architecture:** Add a pure `quant.backtest.audit` module that consumes `BacktestSpec`, explicit point-in-time audit observations and cost sensitivity scenarios, then returns an immutable deterministic `BacktestBiasAuditReport`. The audit layer only classifies hard failures and warnings; it must not run a formal backtest, compute performance metrics, mutate Ledger/Risk, expose API/UI, start Worker runtime, initialize Qlib or touch legacy DSA `/api/v1/backtest/*`.

**Tech Stack:** Python dataclasses, StrEnum, Decimal math, timezone-aware datetime checks, pytest, existing P4 BacktestSpec contracts.

---

### Task 1: Contract Tests

**Files:**
- Create: `tests/quant/test_backtest_bias_audit.py`
- Read: `tests/quant/test_backtest_spec.py`
- Read: `tests/quant/test_risk_policy.py`

- [ ] **Step 1: Write the failing test for hard bias failures**

```python
def test_bias_audit_blocks_known_lookahead_survivor_and_pit_leaks():
    report = BacktestBiasAuditor(spec=spec, policy=policy).evaluate(
        run_id="run-bias-audit",
        stage_id="stage-bias-audit",
        observations=leaky_observations,
        cost_scenarios=stable_cost_scenarios,
    )
    assert report.status is BacktestBiasAuditStatus.INVALID
    assert report.eligible_for_ranking is False
    assert report.agent_strong_conclusion_allowed is False
    assert report.rule_status("lookahead_bias") is BiasAuditRuleStatus.BLOCK
    assert report.rule_status("survivorship_bias") is BiasAuditRuleStatus.BLOCK
    assert report.rule_status("pit_data_availability") is BiasAuditRuleStatus.BLOCK
```

- [ ] **Step 2: Write the failing test for warnings and deterministic output**

```python
def test_bias_audit_warns_on_sample_overlap_and_cost_sensitivity():
    first = auditor.evaluate(...low_overlap_observations..., ...cost_sensitive_scenarios...)
    second = auditor.evaluate(...low_overlap_observations..., ...cost_sensitive_scenarios...)
    assert first.status is BacktestBiasAuditStatus.WARN
    assert first.rule_status("sample_overlap") is BiasAuditRuleStatus.WARN
    assert first.rule_status("cost_sensitivity") is BiasAuditRuleStatus.WARN
    assert first.to_record() == second.to_record()
    assert first.report_id.startswith("audit_")
```

- [ ] **Step 3: Write the failing test for boundaries**

```python
def test_bias_audit_rejects_bad_bindings_and_stays_pure():
    with pytest.raises(BacktestBiasAuditError, match="dataset version"):
        auditor.evaluate(observations=(bad_dataset_observation,), cost_scenarios=stable_cost_scenarios, ...)
    source = Path("src/serenity_alpha_lab/quant/backtest/audit.py").read_text()
    imported_roots = imported_module_roots(source)
    assert not {"qlib", "pyqlib", "fastapi", "sqlalchemy"}.intersection(imported_roots)
```

- [ ] **Step 4: Run tests to verify Red**

Run: `uv run --extra core --extra dev python -m pytest tests/quant/test_backtest_bias_audit.py -q`

Expected: FAIL with `ModuleNotFoundError: serenity_alpha_lab.quant.backtest.audit`.

### Task 2: Audit Module

**Files:**
- Create: `src/serenity_alpha_lab/quant/backtest/audit.py`
- Modify: `src/serenity_alpha_lab/quant/backtest/__init__.py`

- [ ] **Step 1: Implement public constants, errors and enums**

```python
BACKTEST_BIAS_AUDIT_CONTRACT_VERSION = "quant.backtest_bias_audit@1.0.0"
BACKTEST_BIAS_AUDIT_SCHEMA_NAME = "quant.backtest.bias_audit"
BACKTEST_BIAS_AUDIT_SCHEMA_VERSION = "1.0.0"
BACKTEST_BIAS_AUDITOR_VERSION = "cn_a_share_backtest_bias_auditor@1.0.0"

class BacktestBiasAuditStatus(StrEnum):
    PASS = "pass"
    WARN = "warn"
    INVALID = "invalid"

class BiasAuditRuleStatus(StrEnum):
    PASS = "pass"
    WARN = "warn"
    BLOCK = "block"
    NOT_EVALUABLE = "not_evaluable"
```

- [ ] **Step 2: Implement immutable input DTOs**

```python
@dataclass(frozen=True, slots=True)
class BacktestBiasAuditObservation:
    instrument_id: InstrumentId | str
    trade_date: date
    decision_time: datetime
    data_available_at: datetime
    pit_available_at: datetime | None
    universe_as_of: date
    universe_source: str
    in_strategy_sample: bool
    in_return_sample: bool
    dataset_versions: Mapping[str, str]
    temporal_confidence: str = "known"
```

```python
@dataclass(frozen=True, slots=True)
class CostSensitivityScenario:
    scenario_id: str
    cost_multiplier: Decimal | int | str
    total_return: Decimal | int | str
    is_baseline: bool = False
```

- [ ] **Step 3: Implement policy, rule outcome and report DTOs**

```python
@dataclass(frozen=True, slots=True)
class BacktestBiasAuditPolicy:
    policy_id: str
    policy_version: str
    minimum_sample_overlap_ratio: Decimal | int | str = Decimal("0.80")
    cost_sensitivity_warning_threshold: Decimal | int | str = Decimal("0.0500")
    cost_sensitivity_block_threshold: Decimal | int | str = Decimal("0.1500")
```

`BiasAuditRuleOutcome.to_record()` and `BacktestBiasAuditReport.to_record()` must emit JSON-friendly records with stringified `Decimal` values, sorted hard failure/warning/not-evaluable rule ids, `eligible_for_ranking=false` when status is `invalid`, and `agent_strong_conclusion_allowed=false` when status is `invalid`.

- [ ] **Step 4: Implement `BacktestBiasAuditor.evaluate(...)`**

Implement these rule methods and order the outcomes deterministically:

```text
lookahead_bias: block when any data_available_at > decision_time
survivorship_bias: block when universe_source != historical_as_of or universe_as_of > trade_date
pit_data_availability: block when pit_available_at is missing, pit_available_at > decision_time, or temporal_confidence != known
sample_overlap: warn/block from overlap(strategy_sample, return_sample) / union(strategy_sample, return_sample)
cost_sensitivity: warn/block when baseline total_return minus worst non-baseline total_return crosses policy thresholds
```

- [ ] **Step 5: Export symbols**

Add audit constants, DTOs, enums, error and auditor exports to `src/serenity_alpha_lab/quant/backtest/__init__.py`.

- [ ] **Step 6: Run focused target to verify Green**

Run: `uv run --extra core --extra dev python -m pytest tests/quant/test_backtest_bias_audit.py -q`

Expected: PASS.

### Task 3: Evidence And Status

**Files:**
- Create: `docs/backtest-bias-audit.md`
- Modify: `docs/development-progress-checklist.md`
- Modify: `docs/development-status.md`
- Modify: `tasks/todo.md`

- [ ] **Step 1: Document scope and verification**

Create `docs/backtest-bias-audit.md` with: task, conclusion, public contract table, rule semantics, invalid-run promotion guard, non-goals and verification record.

- [ ] **Step 2: Update progress docs**

Mark `SAL-P4-015` done, set P4 to `15/22`, total to `81/129`, add decision/evidence rows, and make `SAL-P4-016` unified performance metrics the next `READY` task. Keep the strict guard that formal BacktestRun, Quant Lab, Evidence Agent, real Provider/LLM and Worker loop remain out of scope.

- [ ] **Step 3: Run related validation**

Run:

```bash
uv run --extra core --extra dev python -m pytest tests/quant/test_backtest_bias_audit.py tests/quant/test_risk_policy.py tests/quant/test_backtest_spec.py tests/architecture/test_architecture_boundaries.py -q
uv run --extra core --extra dev python -m compileall -q src tests
scripts/verify-python-dependency-lock.sh
scripts/apply-dsa-baseline-patches.sh --check-only
git rev-parse upstream/dsa-v3.26.1
git diff --check
```

Expected: all commands exit 0; upstream tag remains `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`.

- [ ] **Step 4: Run full validation and commit**

Run `uv run --extra core --extra dev python -m pytest -q`. If it passes, stage only SAL-P4-015 files and create a Chinese checkpoint commit with `feat(P4): 实现回测偏差审计`.

