# Screen Snapshot Explanation Trace Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the SAL-P3-013 ScreenSnapshot contract so every screened security has a replayable passed/failed stage, score contribution, rank, and structured explanation trace.

**Architecture:** Add a narrow `quant.screening.snapshot` module that transforms the existing P3-012 `ScreenPipelineSnapshot` into a result-facing snapshot schema. Keep pipeline execution unchanged; ScreenSnapshot is a deterministic, immutable projection with comparison helpers and ArtifactStore publication.

**Tech Stack:** Python 3.11 dataclasses, existing `ArtifactStore`, existing `ScreenPipelineSnapshot`, pytest contract tests, deterministic JSON hashing.

---

### Task 1: Contract Tests

**Files:**
- Create: `tests/quant/test_screen_snapshot.py`
- Read: `tests/quant/test_screen_definition_pipeline.py`

- [ ] **Step 1: Write failing imports and fixture reuse**

```python
from serenity_alpha_lab.quant.screening.snapshot import (
    SCREEN_SNAPSHOT_SCHEMA_NAME,
    ScreenSnapshotStatus,
    build_screen_snapshot,
)
```

- [ ] **Step 2: Assert result-facing snapshot records**

```python
snapshot = build_screen_snapshot(pipeline_snapshot, created_at=NOW)
assert snapshot.schema_name == SCREEN_SNAPSHOT_SCHEMA_NAME
assert snapshot.results[0].status is ScreenSnapshotStatus.PASSED
assert snapshot.results[0].rank == 1
```

- [ ] **Step 3: Assert failed-stage and structured explanation replay**

```python
failed = snapshot.result_for("600090.XSHG")
assert failed.status is ScreenSnapshotStatus.FAILED
assert failed.failed_stage.value == "l0_universe"
assert failed.explanation_steps[0].rule_id == "l0_universe_member"
assert "authoritative" in failed.to_record()["explanation_steps"][0]
```

- [ ] **Step 4: Assert comparison query and deterministic publication**

```python
comparison = compare_screen_snapshots(previous, current)
assert comparison.added == ("600519.XSHG",)
assert comparison.removed == ("600091.XSHG",)
assert publish_screen_snapshot(snapshot, store).artifact_id == publish_screen_snapshot(snapshot, store).artifact_id
```

- [ ] **Step 5: Run Red test**

Run: `.venv/bin/python -m pytest tests/quant/test_screen_snapshot.py -q`
Expected: FAIL with missing `serenity_alpha_lab.quant.screening.snapshot`.

### Task 2: ScreenSnapshot Module

**Files:**
- Create: `src/serenity_alpha_lab/quant/screening/snapshot.py`
- Modify: `src/serenity_alpha_lab/quant/screening/__init__.py`

- [ ] **Step 1: Define immutable DTOs**

```python
class ScreenSnapshotStatus(StrEnum):
    PASSED = "passed"
    FAILED = "failed"

@dataclass(frozen=True, slots=True)
class ScreenExplanationStep:
    stage: ScreenPipelineStage | str
    rule_id: str
    reason: str
    authoritative: bool = True
```

- [ ] **Step 2: Build results from pipeline snapshot**

Create `ScreenSnapshotResult` for both `passed_candidates` and `exclusions`. Passed rows must include rank, scores, factor contributions, reason codes, and an L4 pass explanation. Failed rows must include `failed_stage`, no rank, exclusion rule, scores, factor contributions, and replayable explanation steps.

- [ ] **Step 3: Validate invariants**

Require concrete `dsv_*` Dataset Version ids, contiguous passed ranks, one result per instrument, timezone-aware `created_at`, and `screen_snapshot_id` derived from deterministic JSON. Human-readable `summary` may be present but cannot replace structured `rule_id`/stage/scores.

- [ ] **Step 4: Add publication and comparison helpers**

Implement `publish_screen_snapshot()` with schema `quant.screen_snapshot`, version `1.0.0`, and content type `application/vnd.serenity.quant.screen-snapshot+json`. Implement `compare_screen_snapshots()` returning added, removed, retained, rank changes, status changes, and score deltas.

- [ ] **Step 5: Export symbols**

Update `quant.screening.__init__` to export the new constants, DTOs, builder, publisher, and comparison helper.

### Task 3: Documentation And Status

**Files:**
- Create: `docs/screen-snapshot-explanation-trace.md`
- Modify: `docs/development-progress-checklist.md`
- Modify: `docs/development-status.md`
- Modify: `tasks/todo.md`

- [ ] **Step 1: Document contract**

Record schema, result fields, authoritative structured explanation, comparison semantics, ArtifactStore publication, non-goals, and validation evidence.

- [ ] **Step 2: Update progress and status**

Move `SAL-P3-013` to DONE, update P3 progress to `13/17`, total progress to `62/129`, move `SAL-P3-014` to READY, and keep G3 unpassed.

- [ ] **Step 3: Add evidence row**

Add `AEV-062` with Red/Green target, related suite, full pytest, compileall, lock, diff, and immutable tag evidence after verification.

- [ ] **Step 4: Update next-session prompt**

Point the next task to `SAL-P3-014` Quant Screening API and preserve strict no-go boundaries.

### Task 4: Verification And Checkpoint

**Files:**
- No additional implementation files.

- [ ] **Step 1: Run target tests**

Run: `.venv/bin/python -m pytest tests/quant/test_screen_snapshot.py -q`
Expected: PASS.

- [ ] **Step 2: Run related tests**

Run: `.venv/bin/python -m pytest tests/quant/test_screen_snapshot.py tests/quant/test_screen_definition_pipeline.py tests/quant/test_historical_universe.py tests/quant/test_factor_post_processing.py tests/application/test_candidate_batch_contract.py tests/application/test_screening_provider_contract.py tests/integrations/test_alphasift_screening_adapter.py tests/architecture/test_architecture_boundaries.py -q`
Expected: PASS.

- [ ] **Step 3: Run full verification**

Run full pytest, compileall, dependency lock guard, `git diff --check`, and immutable upstream tag check.

- [ ] **Step 4: Review and commit**

Request code review if tooling works; otherwise record fallback and perform local senior review. Stage only SAL-P3-013 files and create a Chinese checkpoint commit.
