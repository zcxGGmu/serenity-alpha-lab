# BacktestRun Orchestration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement `SAL-P4-017` BacktestRun orchestration as a pure application use case that validates and finalizes an already-produced formal portfolio backtest chain.

**Architecture:** Add an application boundary module that accepts one `BacktestSpec`, explicit Qlib/strategy engine evidence, a `PortfolioLedger`, `RiskPolicyResult`, `BacktestBiasAuditReport`, `BacktestPerformanceMetricReport`, and `BacktestArtifactBundle`. The use case creates deterministic `Run` / `Stage` lifecycle records, publishes a compact BacktestRun summary artifact, enforces idempotency and successful-run reuse, and prevents dirty-code formal promotion by rejecting or downgrading to preview. It must not implement resource controls, API routes, Quant Lab, Worker loop, real Provider/LLM calls, or a live Qlib runtime run.

**Tech Stack:** Python dataclasses, existing `serenity_alpha_lab.domain.run_lifecycle`, `ArtifactStore`, `LocalArtifactStore`, existing P4 quant/backtest DTOs, pytest.

---

## File Structure

- Create: `src/serenity_alpha_lab/application/backtest_run.py`
  - Owns `BacktestRunRequest`, `BacktestRunRecord`, `BacktestRunStageRecord`, `InMemoryBacktestRunRepository`, and `BacktestRunOrchestrator`.
  - Validates cross-layer bindings and publishes a compact run summary artifact.
- Modify: `src/serenity_alpha_lab/application/__init__.py`
  - Exports the BacktestRun application symbols.
- Create: `tests/application/test_backtest_run_orchestration.py`
  - Contract tests for stage orchestration, idempotency/reuse, dirty-code handling, mismatch rejection, and import boundaries.
- Create: `docs/backtest-run-orchestration.md`
  - Evidence document for SAL-P4-017 scope, stage chain, idempotency/reuse, dirty-code rules, non-goals, and verification.
- Modify later during status sync: `tasks/todo.md`, `docs/development-progress-checklist.md`, and `docs/development-status.md`.

## Scope Guard

- Do not start formal portfolio backtest execution beyond registering/finalizing supplied deterministic outputs.
- Do not implement `SAL-P4-018` resource limits/cancel/checkpoint, `SAL-P4-020` API, `SAL-P4-021` Quant Lab, Evidence Agent, real Provider/LLM calls, Worker loop, or legacy `/api/v1/backtest/*` changes.
- Do not name legacy Signal Evaluation, AlphaSift T+N evaluation, Screen result, Qlib internal evidence, or Dataset conversion artifacts as formal portfolio backtest.
- Qlib evidence remains engine evidence only; platform `BacktestSpec`, `Run/Stage/Event`, Ledger, Risk, Audit, Metrics, and BacktestArtifact descriptors stay authoritative.

### Task 1: Red Contract Tests

**Files:**
- Create: `tests/application/test_backtest_run_orchestration.py`

- [ ] **Step 1: Write failing tests**

Add tests that import the new module and assert:

```python
from serenity_alpha_lab.application.backtest_run import (
    BACKTEST_RUN_ORCHESTRATOR_CONTRACT_VERSION,
    BacktestRunCodeState,
    BacktestRunMode,
    BacktestRunOrchestrator,
    BacktestRunOrchestratorError,
    BacktestRunRequest,
    InMemoryBacktestRunRepository,
)
```

Test cases:

- A clean formal request finalizes a completed `Run` with stages in this exact order: `spec`, `engine`, `ledger`, `risk`, `audit`, `metrics`, `artifacts`, `summary`.
- The published summary artifact is compact and references IDs/hashes/URIs only; it must not embed rows/dataframes.
- Same idempotency key + same request replays the same record.
- Different idempotency key + same `spec_hash + dataset_hashes + engine_version` reuses the previous successful run.
- Same idempotency key + different request raises `BacktestRunOrchestratorError`.
- Dirty formal code without a patch hash is rejected.
- Dirty formal code with a `sha256:*` patch hash is downgraded to preview and is not ranking-eligible.
- Cross-layer mismatches for spec hash/run id are rejected.
- `application/backtest_run.py` imports no `qlib`, `pyqlib`, `fastapi`, `sqlalchemy`, `litellm`, or DSA runtime modules.

- [ ] **Step 2: Run Red test**

Run:

```bash
uv run --extra core --extra dev python -m pytest tests/application/test_backtest_run_orchestration.py -q
```

Expected: fails with `ModuleNotFoundError: serenity_alpha_lab.application.backtest_run`.

### Task 2: Implement Application Use Case

**Files:**
- Create: `src/serenity_alpha_lab/application/backtest_run.py`
- Modify: `src/serenity_alpha_lab/application/__init__.py`

- [ ] **Step 1: Implement DTOs and repository**

Create immutable DTOs:

- `BacktestRunMode`: `preview`, `formal`
- `BacktestRunCodeState`: `clean`, `dirty`
- `BacktestRunStatus`: `succeeded`
- `BacktestRunStageRecord`: stage id/name/status/timestamps/artifact ids/output ids
- `BacktestRunRequest`: run id, trace id, idempotency key, submitted_at, spec, engine evidence record, ledger, risk report, audit report, metrics report, artifact bundle, requested mode, code state, optional patch hash, engine version
- `BacktestRunRecord`: summary of effective mode, ranking eligibility, warnings, reuse key, lifecycle, stage records, output IDs, artifact bundle manifest, and run summary manifest
- `InMemoryBacktestRunRepository`: indexes by idempotency key and reuse key.

- [ ] **Step 2: Implement orchestrator validation**

`BacktestRunOrchestrator.finalize(request)` must:

- Reject non-`BacktestRunRequest` inputs.
- Reject dirty formal requests without a patch hash.
- Downgrade dirty formal requests with a patch hash to preview and add a warning.
- Derive `request_hash` and `reuse_key` from canonical JSON.
- Replay same idempotency key + same request.
- Raise conflict for same idempotency key + different request.
- Return existing successful record for matching reuse key.
- Validate all supplied records bind the same `spec_id`, `spec_hash`, `run_id`, and expected stage ids where available.
- Reject formal promotion if `RiskPolicyResult.status == block`, `BacktestBiasAuditReport.status == invalid`, or `BacktestArtifactBundle.state != formal`.
- Publish a compact summary artifact using `ArtifactStore.put_bytes(...)`.
- Use `Run.start(...)`, `start_stage(...)`, `record_stage_event(...)`, `complete_stage(...)`, and `complete(...)` to create lifecycle evidence.

- [ ] **Step 3: Export symbols**

Export all new public symbols from `src/serenity_alpha_lab/application/__init__.py`.

- [ ] **Step 4: Run focused Green test**

Run:

```bash
uv run --extra core --extra dev python -m pytest tests/application/test_backtest_run_orchestration.py -q
```

Expected: all tests pass.

### Task 3: Evidence Documentation

**Files:**
- Create: `docs/backtest-run-orchestration.md`
- Modify: `tasks/todo.md`

- [ ] **Step 1: Add evidence doc**

Document:

- Contract version and module/test paths.
- Stage chain and platform authority.
- Idempotency/reuse semantics.
- Dirty-code formal-run policy.
- Ranking eligibility guards.
- Non-goals and explicit prohibited scopes.
- Verification commands and results.

- [ ] **Step 2: Update task review**

Append a `SAL-P4-017` review section to `tasks/todo.md`, including the subagent fallback caused by host schema wrapper failures.

### Task 4: Verification And Status Sync

**Files:**
- Modify: `docs/development-progress-checklist.md`
- Modify: `docs/development-status.md`

- [ ] **Step 1: Run related verification**

Run:

```bash
uv run --extra core --extra dev python -m pytest tests/application/test_backtest_run_orchestration.py tests/integrations/test_qlib_quant_engine_adapter.py tests/quant/test_backtest_artifact.py tests/quant/test_backtest_performance_metrics.py tests/quant/test_backtest_bias_audit.py tests/quant/test_risk_policy.py tests/quant/test_portfolio_ledger.py tests/quant/test_backtest_spec.py tests/architecture/test_architecture_boundaries.py -q
```

Expected: pass.

- [ ] **Step 2: Run full verification**

Run:

```bash
uv run --extra core --extra dev python -m pytest -q
uv run --extra core --extra dev python -m compileall -q src tests
scripts/verify-python-dependency-lock.sh
scripts/apply-dsa-baseline-patches.sh --check-only
git rev-parse upstream/dsa-v3.26.1
git diff --check
```

Expected: all pass and immutable upstream tag remains `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`.

- [ ] **Step 3: Sync status docs**

Update status to:

- P4 `17/22`
- Total `83/129`
- Recent task `SAL-P4-017` BacktestRun orchestration
- Next task `SAL-P4-018` resource limits, cancel, checkpoint
- Gate G4 remains not passed.

- [ ] **Step 4: Commit**

Stage only SAL-P4-017 files and create a Chinese checkpoint commit:

```bash
git add src/serenity_alpha_lab/application/backtest_run.py src/serenity_alpha_lab/application/__init__.py tests/application/test_backtest_run_orchestration.py docs/backtest-run-orchestration.md docs/development-progress-checklist.md docs/development-status.md tasks/todo.md docs/superpowers/plans/2026-07-26-backtest-run-orchestration.md
git commit -m "feat(P4): 实现 BacktestRun 编排"
```
