# Gate G2 Data Task Review Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete `SAL-P2-020` by proving that P2 Dataset, Provider and persistent task foundations are ready to enter P3 screening development.

**Architecture:** Gate G2 is a review checkpoint, not a new product subsystem. The implementation adds one offline integration test that stitches existing P2 modules together, then records the Gate decision and updates project state documents. All evidence must stay within offline fixture, profile guard, Artifact, Dataset Catalog and database-authoritative task boundaries.

**Tech Stack:** Python 3.11, pytest, SQLAlchemy/SQLite, Serenity `serenity_alpha_lab` package, LocalArtifactStore, LocalDatasetCatalog, Provider fixture/policy modules, PersistentTaskBackend and task event stream services.

---

### Task 1: Gate G2 Offline Integration Test

**Files:**
- Create: `tests/gates/test_gate_g2_data_task_review.py`
- Read: `tests/datasets/test_dataset_publication.py`
- Read: `tests/integrations/test_provider_policy.py`
- Read: `tests/services/test_task_event_stream.py`

- [ ] **Step 1: Write the failing test module**

Create `tests/gates/test_gate_g2_data_task_review.py` with tests that:

```python
def test_gate_g2_publishes_traceable_a_share_dataset_from_offline_provider_fixture(tmp_path):
    # Use default_provider_contract_fixture_catalog(), ProviderPolicyEngine,
    # LocalArtifactStore, QualityGatedDatasetPublisher and LocalDatasetCatalog.
    # Assert the selected A-share Provider batch publishes a concrete immutable
    # Dataset version, updates latest for alias_scope="cn", preserves schema hash,
    # file hash, quality_status, trace_id, run_id, stage_id and provider trace metadata.
```

```python
def test_gate_g2_blocks_provider_conflict_and_recovers_task_events_after_restart(tmp_path):
    # Use ProviderPolicyEngine with cross_check_provider_id="tushare" to quarantine
    # a close-price conflict. Then use PersistentTaskBackend with a SQLite engine,
    # submit a data.sync.daily task, restart the backend, replay events through
    # TaskEventStreamService and assert queued state plus Last-Event-ID recovery.
```

```python
def test_gate_g2_dsa_single_stock_compatibility_path_uses_injected_offline_manager():
    # Use DsaProviderCompatibilityAdapter with RuntimeProfile.CI and an injected
    # fake DSA manager. Assert one 600519.XSHG daily-bar request returns immutable
    # DataBatch records and never constructs the real DSA Provider manager.
```

- [ ] **Step 2: Run the new test to verify failure or pass**

Run: `uv run --extra core --extra dev python -m pytest tests/gates/test_gate_g2_data_task_review.py -q`

Expected: If imports or helper assumptions are wrong, fail before documentation updates; otherwise pass and become the new Gate evidence.

- [ ] **Step 3: Adjust the test only against existing public module contracts**

Use existing constructors and helpers from P2 modules. Do not add new production behavior unless the integration test exposes a real P2 contract defect.

- [ ] **Step 4: Re-run the target Gate test**

Run: `uv run --extra core --extra dev python -m pytest tests/gates/test_gate_g2_data_task_review.py -q`

Expected: `3 passed`.

### Task 2: Gate G2 Review Document

**Files:**
- Create: `docs/gate-g2-data-task-review.md`
- Modify: `docs/development-progress-checklist.md`
- Modify: `docs/development-status.md`
- Modify: `tasks/todo.md`

- [ ] **Step 1: Create the Gate review record**

Create `docs/gate-g2-data-task-review.md` with:

```markdown
# Gate G2 数据与任务评审

> 任务：`SAL-P2-020` Gate G2：数据与任务评审
> 评审日期：2026-07-23
> Phase：P2 数据与持久任务
> 评审结论：`GO with accepted risks`
```

Include sections for Gate conclusion, condition matrix, P2 delivery checklist, accepted risks/constraints, local verification and P3 entry constraints.

- [ ] **Step 2: Update the progress checklist**

Mark `SAL-P2-020` as `[DONE]`, update P2 and total progress from `19/20`, `48/129` to `20/20`, `49/129`, add Decision/Evidence rows for Gate G2, and keep P3 as the next phase with `SAL-P3-001` ready.

- [ ] **Step 3: Update development status**

Set current Gate to G2 passed with accepted risks, latest phase task to `SAL-P2-020`, completed range to `SAL-P2-001..020`, current executable task to `SAL-P3-001`, and update the next-start prompt.

- [ ] **Step 4: Update `tasks/todo.md` review**

Mark the Gate G2 checklist complete and add verification summaries after fresh commands have been run.

### Task 3: Verification and Checkpoint

**Files:**
- Verify only unless a validation result requires documentation correction.

- [ ] **Step 1: Run target Gate test**

Run: `uv run --extra core --extra dev python -m pytest tests/gates/test_gate_g2_data_task_review.py -q`

Expected: `3 passed`.

- [ ] **Step 2: Run related P2 suite**

Run:

```bash
uv run --extra core --extra dev python -m pytest \
  tests/gates/test_gate_g2_data_task_review.py \
  tests/datasets/test_dataset_catalog.py \
  tests/datasets/test_data_quality.py \
  tests/datasets/test_dataset_publication.py \
  tests/integrations/test_provider_contract_fixtures.py \
  tests/integrations/test_provider_policy.py \
  tests/integrations/test_dsa_provider_adapter.py \
  tests/services/test_data_sync.py \
  tests/repositories/test_database_profile.py \
  tests/repositories/test_repository_contract.py \
  tests/repositories/test_persistent_task_backend.py \
  tests/services/test_task_event_stream.py \
  tests/application/test_api_errors.py \
  tests/application/test_tracing.py \
  tests/architecture/test_architecture_boundaries.py \
  -q
```

Expected: all selected tests pass; optional live PostgreSQL tests may remain skipped without `SERENITY_TEST_POSTGRES_URL`.

- [ ] **Step 3: Run full and structural verification**

Run:

```bash
uv run --extra core --extra dev python -m pytest -q
uv run --extra core --extra dev python -m compileall src tests
scripts/verify-python-dependency-lock.sh
git diff --check
git rev-parse upstream/dsa-v3.26.1
```

Expected: pytest and compile/lock/diff pass; tag hash remains `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`.

- [ ] **Step 4: Commit**

Run:

```bash
git status --short
git add tests/gates/test_gate_g2_data_task_review.py docs/gate-g2-data-task-review.md docs/development-progress-checklist.md docs/development-status.md tasks/todo.md
git commit -m "docs(P2): 完成 Gate G2 数据与任务评审"
```

Use the required Chinese body with completed content, compatibility/risk handling, verification and associated task `SAL-P2-020, Gate G2`.
