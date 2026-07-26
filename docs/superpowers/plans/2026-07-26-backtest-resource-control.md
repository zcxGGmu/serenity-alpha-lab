# Backtest Resource Control Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement `SAL-P4-018` resource limits, cancellation and checkpointing for formal BacktestRun supervision.

**Architecture:** Add a pure application-layer supervisor that records resource policy, observed isolated-child-process state, cooperative cancellation requests, timeout/OOM/failed classifications and checkpoint artifacts. Successful child snapshots may finalize through the existing `BacktestRunOrchestrator`; timeout, cancel and OOM paths must publish partial checkpoint artifacts and never create `BacktestRunStatus.SUCCEEDED`.

**Tech Stack:** Python dataclasses, StrEnum, injected clock, existing `ArtifactStore`, existing `BacktestRunOrchestrator`, `QlibRuntimeIsolationPolicy`, pytest.

---

### Task 1: Contract Tests

**Files:**
- Create: `tests/application/test_backtest_resource_control.py`
- Read: `tests/application/test_backtest_run_orchestration.py`

- [ ] **Step 1: Write failing tests**

Add tests for:

```python
def test_supervisor_records_resource_policy_and_successfully_finalizes_child_result(tmp_path): ...
def test_supervisor_timeout_publishes_partial_checkpoint_and_never_succeeds(tmp_path): ...
def test_supervisor_cancel_request_publishes_partial_checkpoint_and_terminates_child(tmp_path): ...
def test_supervisor_oom_classification_publishes_partial_checkpoint_and_never_succeeds(tmp_path): ...
def test_resource_control_contract_stays_outside_api_worker_and_provider_boundaries(): ...
```

- [ ] **Step 2: Run Red target**

Run: `uv run --extra core --extra dev python -m pytest tests/application/test_backtest_resource_control.py -q`

Expected: fail with missing `serenity_alpha_lab.application.backtest_resource_control`.

### Task 2: Resource Supervisor

**Files:**
- Create: `src/serenity_alpha_lab/application/backtest_resource_control.py`
- Modify: `src/serenity_alpha_lab/application/__init__.py`

- [ ] **Step 1: Implement minimal contract**

Add:

```python
BacktestRunResourcePolicy
BacktestRunExecutionStatus
BacktestRunChildProcessStatus
BacktestRunChildProcessSnapshot
BacktestRunCheckpoint
BacktestRunExecutionRecord
InMemoryBacktestRunExecutionRepository
BacktestRunResourceSupervisor
```

Reuse `default_qlib_runtime_policy()` for defaults. Do not import Qlib, FastAPI, Celery, Redis, SQLAlchemy, Provider or LLM modules.

- [ ] **Step 2: Implement checkpoint publication**

Checkpoint artifacts use:

```text
schema_name = quant.backtest_run_checkpoint
schema_version = 1.0.0
content_type = application/vnd.serenity.quant.backtest-run-checkpoint+json
```

Timeout/cancel/OOM checkpoints must include `artifact_state=partial`, resource usage, process id, reason, current stage and resume hint.

- [ ] **Step 3: Export symbols**

Add lazy exports from `src/serenity_alpha_lab/application/__init__.py`.

### Task 3: Evidence And State

**Files:**
- Create: `docs/backtest-resource-control.md`
- Modify: `docs/development-progress-checklist.md`
- Modify: `docs/development-status.md`
- Modify: `tasks/todo.md`

- [ ] **Step 1: Document SAL-P4-018**

Record scope, resource defaults, cancellation semantics, timeout/OOM partial checkpoint behavior, non-goals and verification.

- [ ] **Step 2: Update project status**

Mark `SAL-P4-018` done only after verification; set P4 to `18/22`, total to `84/129`, add `DEC-082` and `AEV-084`, and make `SAL-P4-019` READY without starting it.

### Task 4: Verification And Commit

**Files:**
- Stage only SAL-P4-018 implementation, tests and docs.

- [ ] **Step 1: Run verification**

Run:

```bash
uv run --extra core --extra dev python -m pytest tests/application/test_backtest_resource_control.py -q
uv run --extra core --extra dev python -m pytest tests/application/test_backtest_resource_control.py tests/application/test_backtest_run_orchestration.py tests/integrations/test_qlib_quant_engine_adapter.py tests/repositories/test_persistent_task_backend.py tests/services/test_task_event_stream.py tests/quant/test_backtest_artifact.py tests/architecture/test_architecture_boundaries.py -q
uv run --extra core --extra dev python -m pytest -q
uv run --extra core --extra dev python -m compileall -q src/serenity_alpha_lab tests
scripts/verify-python-dependency-lock.sh
git diff --check
```

- [ ] **Step 2: Commit**

Create a Chinese checkpoint commit:

```bash
git commit -m "feat(P4): 实现回测资源控制与 checkpoint" \
  -m "完成内容：" \
  -m "- 新增 BacktestRun 资源策略、取消、超时、OOM 和 partial checkpoint 契约" \
  -m "- 保持正式 API、Quant Lab、Evidence Agent、Worker loop 和真实 Provider/LLM 出界" \
  -m "" \
  -m "兼容性与风险：" \
  -m "- 不改变 legacy Signal Evaluation 和 SAL-P4-017 成功 finalization 语义" \
  -m "" \
  -m "验证：" \
  -m "- pytest focused/related/full, compileall, lock guard, diff check" \
  -m "" \
  -m "关联任务：SAL-P4-018, Gate G4"
```

## Guardrails

- Do not start formal API routes, Quant Lab, Evidence Agent, Worker loop, real Provider calls, real LLM calls or Qlib runtime.
- Do not name legacy DSA Signal Evaluation, AlphaSift T+N evaluation, Screen result, Qlib internal evidence or Dataset conversion as formal portfolio backtest.
- Timeout, cancel and OOM outcomes must never publish `BacktestRunStatus.SUCCEEDED`.
- Partial checkpoints must be explicit and auditable.
