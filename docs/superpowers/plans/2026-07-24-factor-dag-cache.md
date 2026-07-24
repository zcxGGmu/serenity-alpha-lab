# Factor DAG Cache Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `SAL-P3-010` Factor calculation DAG/cache so compiled factor plans produce deterministic dependency graphs, cache keys, partition plans, incremental recompute plans and quality-gated cache artifact publication.

**Architecture:** Add a pure `quant.factors.engine` module that consumes published `FactorDefinition`/`FactorExpressionPlan` metadata and explicit dataset/universe versions. The module produces JSON-friendly DAG/cache DTOs, deduplicates shared expression nodes across factors, plans time-series and cross-section partitions, blocks `latest` aliases, and publishes cache manifests only after a passed quality gate. It does not execute factor math, query providers, build Historical Universe, call Qlib, run backtests or start screen workflows.

**Tech Stack:** Python dataclasses/enums, hashlib/json for deterministic cache keys and CSE hashes, existing `DatasetVersionRef`, `FactorDefinition`, `FactorExpressionPlan`, `ArtifactStore`, `LocalArtifactStore`, and pytest.

---

### Task 1: Contract Tests

**Files:**
- Create: `tests/quant/test_factor_dag_cache.py`
- Create: `docs/superpowers/plans/2026-07-24-factor-dag-cache.md`
- Modify: `tasks/todo.md`

- [x] **Step 1: Add Red contract tests**

Cover:
- `FactorDagBuildSpec` requires concrete dataset versions, `fdv_*` factor versions, concrete universe version and engine version.
- `build_factor_dag()` compiles two factors with a shared subexpression and emits one shared DAG node for the common expression.
- cache keys include dataset versions, factor version, universe version, date range, engine version and partition id.
- partition plan distinguishes time-series partitions by instrument and cross-section partitions by trade date.
- incremental recompute only schedules partitions affected by changed dataset versions, changed factors and lookback windows.
- `publish_factor_cache_manifest()` refuses failed quality gates and publishes deterministic JSON artifacts for passed runs.

- [x] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/quant/test_factor_dag_cache.py -q`

Expected Red: collection fails with missing `serenity_alpha_lab.quant.factors.engine`.

### Task 2: DAG And Cache Module

**Files:**
- Create: `src/serenity_alpha_lab/quant/factors/engine.py`
- Modify: `src/serenity_alpha_lab/quant/factors/__init__.py`
- Test: `tests/quant/test_factor_dag_cache.py`

- [x] **Step 1: Implement immutable contracts**

Implement DTOs:
- `FactorDagBuildSpec`
- `FactorDagNode`
- `FactorDag`
- `FactorCachePartition`
- `FactorCacheKey`
- `FactorPartitionPlan`
- `FactorIncrementalChangeSet`
- `FactorIncrementalRecomputePlan`
- `FactorCacheQualityGate`
- `FactorCacheManifest`

- [x] **Step 2: Implement planning functions**

Implement functions:
- `build_factor_dag()`
- `plan_factor_cache_partitions()`
- `plan_incremental_factor_recompute()`
- `publish_factor_cache_manifest()`

- [x] **Step 3: Export public symbols**

Add Factor DAG/cache constants, DTOs and functions to `serenity_alpha_lab.quant.factors.__all__`.

- [x] **Step 4: Run target tests**

Run: `.venv/bin/python -m pytest tests/quant/test_factor_dag_cache.py -q`

Expected Green: target tests pass.

### Task 3: Documentation And Status

**Files:**
- Create: `docs/factor-dag-cache.md`
- Modify: `docs/development-progress-checklist.md`
- Modify: `docs/development-status.md`
- Modify: `tasks/todo.md`

- [x] **Step 1: Document DAG/cache contract**

Document scope, DTOs, graph/CSE semantics, cache key fields, partition policy, incremental recompute policy, quality-gated cache publication, performance metrics and explicit non-goals.

- [x] **Step 2: Update progress**

Mark `SAL-P3-010` done, add `DEC-057` and `AEV-059`, update P3 progress to `10/17`, total progress to `59/129`, and keep `SAL-P3-011` as current READY work.

- [x] **Step 3: Update status**

Update `docs/development-status.md` to name `SAL-P3-010` as the latest task, list `SAL-P3-011` as current READY work, and include `docs/factor-dag-cache.md` in the next-session prompt.

### Task 4: Verification And Commit

**Files:**
- All files above

- [x] **Step 1: Run verification**

Run target, factor-related, P3/architecture, full pytest, compileall, dependency lock guard, `git diff --check`, and immutable tag check.

- [x] **Step 2: Review changes**

Attempt independent code-review subagent. If unavailable, record the tool failure and perform a local senior review of DAG semantics, cache key completeness, quality gate, docs/status consistency and no-go boundaries.

- [x] **Step 3: Commit**

Stage only `SAL-P3-010` files and create a Chinese checkpoint commit. Then update recovery docs with the actual implementation checkpoint hash and create a status-sync checkpoint if needed.
