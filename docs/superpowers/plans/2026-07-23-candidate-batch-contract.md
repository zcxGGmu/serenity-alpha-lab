# CandidateBatch Contract Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete `SAL-P3-004` by defining the platform `Candidate` / `CandidateBatch` contract with immutable candidates, layer scores, reasons, sources, rank and deterministic serialization.

**Architecture:** Add `src/serenity_alpha_lab/application/candidate_batch.py` as the stable application-layer contract that sits after `ScreeningProvider` raw results and before future ScreenDefinition/Factor work. The contract carries concrete Dataset Version ids, strategy/snapshot/discovery metadata, L1/L2 deterministic scores, optional L3 LLM overlay scores, reason codes and source lineage without invoking AlphaSift, Quant Core, formal backtests, Evidence Agent or real providers.

**Tech Stack:** Python dataclasses, `StrEnum`, existing `InstrumentId`, existing `DatasetVersionRef` validation, `ScreeningResult` metadata reuse, pytest contract tests.

---

### Task 1: Red CandidateBatch Contract Tests

**Files:**
- Create: `tests/application/test_candidate_batch_contract.py`

- [ ] **Step 1: Write failing tests**

Add tests that import `Candidate`, `CandidateBatch`, `CandidateLayerScore`, `CandidateReason`, `CandidateSource`, `CandidateScoreLayer`, `CandidateSourceType`, `CandidateBatchError`, `CANDIDATE_BATCH_SCHEMA_NAME` and `candidate_batch_from_screening_result`.

The tests must prove:

- A batch stores concrete dataset versions, strategy version, `discovered_at`, `source_snapshot_at`, L1/L2/L3 score records, final rank, reason codes and sources.
- LLM overlay is independent: `l2_deterministic` score remains unchanged when `l3_llm_overlay` exists.
- Nested batch records are immutable and `to_record()` is deterministic and JSON-friendly.
- Invalid `latest` dataset versions, duplicate ranks, missing L1/L2 scores, L3 score without `llm_overlay_enabled`, invalid source dataset versions and impossible timestamps raise `CandidateBatchError`.
- `candidate_batch_from_screening_result()` copies `ScreeningResult` trace/run/stage/provider metadata and consumes only already-standardized candidates.

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --extra core --extra dev python -m pytest tests/application/test_candidate_batch_contract.py -q`

Expected: FAIL with missing `serenity_alpha_lab.application.candidate_batch`.

### Task 2: CandidateBatch Contract Implementation

**Files:**
- Create: `src/serenity_alpha_lab/application/candidate_batch.py`
- Modify: `src/serenity_alpha_lab/application/__init__.py`

- [ ] **Step 1: Implement immutable DTOs**

Create:

- `CandidateBatchError(ValueError)`
- `CandidateScoreLayer`: `L1_PROVIDER`, `L2_DETERMINISTIC`, `L3_LLM_OVERLAY`
- `CandidateSourceType`: `SCREENING_PROVIDER`, `DATASET`, `RULE`, `LLM_OVERLAY`, `RAW_PAYLOAD`
- `CandidateSource`: source lineage with optional concrete `dataset_version`, `provider_id`, `artifact_uri`, `observed_at`, immutable metadata
- `CandidateReason`: stable reason code, layer, message, direction, optional weight, source ids, immutable details
- `CandidateLayerScore`: layer score normalized to `0..100`, optional raw value/weight/source/reason code metadata
- `Candidate`: canonical `InstrumentId`, positive rank, final score, layer score mapping, reasons, source ids, optional name and raw payload
- `CandidateBatch`: strategy/provider/dataset/snapshot metadata, immutable candidates/sources, LLM overlay flags, trace/run/stage ids, deterministic `to_record()`

- [ ] **Step 2: Implement validations**

Validate:

- Dataset versions use existing `DatasetVersionRef.version()` and reject `latest`.
- Batch timestamps are timezone-aware and `discovered_at >= source_snapshot_at`, `received_at >= requested_at` when present.
- Candidate ranks are positive, unique and in ascending order.
- Every candidate has `L1_PROVIDER` and `L2_DETERMINISTIC`.
- `L3_LLM_OVERLAY` is allowed only when `llm_overlay_enabled=True`.
- Scores are finite and normalized `0..100`; weights are finite and non-negative.
- Reason codes/source ids are non-empty strings; candidate source ids must exist in batch sources when batch sources are supplied.

- [ ] **Step 3: Add ScreeningResult bridge**

Implement `candidate_batch_from_screening_result(result, *, candidates, source_snapshot_at, sources=(), batch_id=None, metadata=None)` that requires a `ScreeningResult`, carries provider/strategy/market/dataset/trace metadata, and does not parse raw provider candidates.

- [ ] **Step 4: Export symbols**

Add the new contract symbols to `src/serenity_alpha_lab/application/__init__.py`.

- [ ] **Step 5: Run target test**

Run: `uv run --extra core --extra dev python -m pytest tests/application/test_candidate_batch_contract.py -q`

Expected: PASS.

### Task 3: Documentation and Status Sync

**Files:**
- Create: `docs/candidate-batch-contract.md`
- Modify: `docs/development-progress-checklist.md`
- Modify: `docs/development-status.md`
- Modify: `tasks/todo.md`

- [ ] **Step 1: Add evidence document**

Document schema fields, validation rules, ScreeningProvider bridge, non-goals and verification evidence in `docs/candidate-batch-contract.md`.

- [ ] **Step 2: Update progress/state**

Mark only `SAL-P3-004` as `DONE`, move P3 progress to `4/17`, total progress to `53/129`, set `SAL-P3-005` as next `READY`, keep Gate G3 not passed, and keep all prohibitions explicit.

- [ ] **Step 3: Add DEC/AEV entries**

Add `DEC-051` for the CandidateBatch contract and `AEV-053` for test/verification evidence.

- [ ] **Step 4: Update review**

Update this task review in `tasks/todo.md` with Red/Green evidence, scope retained, verification commands and checkpoint placeholder.

### Task 4: Verification and Checkpoint

**Files:**
- No new files unless verification reveals a necessary correction.

- [ ] **Step 1: Run verification**

Run:

```bash
uv run --extra core --extra dev python -m pytest tests/application/test_candidate_batch_contract.py -q
uv run --extra core --extra dev python -m pytest tests/application/test_candidate_batch_contract.py tests/application/test_screening_provider_contract.py tests/integrations/test_alphasift_screening_adapter.py tests/architecture/test_architecture_boundaries.py -q
uv run --extra core --extra dev python -m pytest -q
uv run --extra core --extra dev python -m compileall src tests
scripts/verify-python-dependency-lock.sh
git diff --check
git rev-parse upstream/dsa-v3.26.1
```

Expected: target and related tests pass, full pytest remains green, compile/lock/diff checks pass, and immutable tag remains `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`.

- [ ] **Step 2: Commit**

Stage only `SAL-P3-004` files and create a Chinese checkpoint commit:

```bash
git add src/serenity_alpha_lab/application/candidate_batch.py src/serenity_alpha_lab/application/__init__.py tests/application/test_candidate_batch_contract.py docs/candidate-batch-contract.md docs/development-progress-checklist.md docs/development-status.md docs/superpowers/plans/2026-07-23-candidate-batch-contract.md tasks/todo.md
git commit -m "feat(P3): 定义 CandidateBatch 候选契约" -m "完成内容：
- ...

兼容性与风险：
- ...

验证：
- ...

关联任务：SAL-P3-004, Gate G3"
```
