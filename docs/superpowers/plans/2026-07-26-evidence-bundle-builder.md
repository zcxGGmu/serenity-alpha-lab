# EvidenceBundle Builder Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement `SAL-P5-003` by adding an offline EvidenceBundle Builder that creates minimal, role-scoped context from local Evidence Store records using instrument, decision-time and token-budget constraints.

**Architecture:** Add `serenity_alpha_lab.application.evidence_bundle_builder` as an application-layer service because it consumes the P5 Evidence schema and the P5 repository-backed Evidence Store. The builder reads accessible `PersistedEvidence` records, filters future or irrelevant records, dedupes by `content_hash`, ranks by role/trust/scope/instrument specificity/recency, and trims evidence while preserving fixed schema instructions. It returns structured bundle DTOs and a JSON-friendly prompt payload; it does not execute Agent stages, validate citations, adapt Quant runtime outputs, call Providers or LLMs, start Worker loops, initialize Qlib runtime, render reports or schedule production work.

**Tech Stack:** Python 3.11 stdlib dataclasses/enums/json/hashlib/math, existing Pydantic `EvidenceRecord`, existing `LocalEvidenceStore`, pytest.

---

### Task 1: Red EvidenceBundle Builder Tests

**Files:**
- Create: `tests/application/test_evidence_bundle_builder.py`

- [ ] **Step 1: Write failing tests for bundle behavior**

Create tests that:

- create a `LocalEvidenceStore` with formal metrics, risk policy, duplicate content, future evidence, different-instrument evidence and global evidence.
- call `EvidenceBundleBuilder.build()` with `EvidenceBundleRequest`.
- assert future evidence is excluded, different-instrument evidence is excluded, duplicate content hash is excluded, role priority puts risk evidence ahead of metrics for `risk_portfolio`, and budget trimming records excluded items without removing schema instructions.
- assert a budget smaller than fixed schema instructions raises `EvidenceBundleError`.

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --extra core --extra dev python -m pytest tests/application/test_evidence_bundle_builder.py -q`

Expected: FAIL with missing `serenity_alpha_lab.application.evidence_bundle_builder`.

### Task 2: Minimal Builder Implementation

**Files:**
- Create: `src/serenity_alpha_lab/application/evidence_bundle_builder.py`
- Modify: `src/serenity_alpha_lab/application/__init__.py`

- [ ] **Step 1: Implement DTOs and policies**

Implement:

- `EvidenceBundleRole`: `technical`, `intel`, `risk_portfolio`, `decision`.
- `EvidenceBundleStatus`: `complete`, `trimmed`, `empty`, `budget_exhausted`.
- `EvidenceBundleBudget`: `max_prompt_tokens`, `reserved_schema_tokens`, `max_evidence_items`.
- `EvidenceBundleRequest`: tenant/team/user, decision time, role, optional instrument, budget, optional kind/scope filters.
- `EvidenceBundleItem`: evidence, priority score, priority reasons, estimated tokens.
- `EvidenceBundleExcludedItem`: evidence id, reason, estimated tokens, priority score.
- `EvidenceBundle`: stable bundle id, schema instructions, included/excluded items, estimated tokens, status and `to_prompt_payload()`.

- [ ] **Step 2: Implement builder**

Implement `EvidenceBundleBuilder.build(request)` over `LocalEvidenceStore.find_evidence()`:

- validate timezone-aware `decision_time`.
- always compute fixed schema instructions and fail if they alone exceed `max_prompt_tokens`.
- filter inaccessible records through Evidence Store query scope.
- exclude `available_at > decision_time` as `future_available_at`.
- exclude instrument-specific evidence for other instruments as `instrument_mismatch`.
- filter requested kinds/scopes when supplied.
- dedupe by `content_hash`, keeping the highest priority and recording later duplicates as `duplicate_content_hash`.
- rank by role kind weight, trust level, formal scope, instrument match, recency and evidence id for deterministic ties.
- add evidence until budget or max item count is reached; mark excess as `budget_trimmed`.

- [ ] **Step 3: Export public API**

Update `src/serenity_alpha_lab/application/__init__.py` to export builder DTOs and errors without triggering optional runtimes.

- [ ] **Step 4: Run focused test**

Run: `uv run --extra core --extra dev python -m pytest tests/application/test_evidence_bundle_builder.py -q`

Expected: PASS.

### Task 3: Documentation And Status Evidence

**Files:**
- Create: `docs/evidence-bundle-builder.md`
- Modify: `docs/development-progress-checklist.md`
- Modify: `docs/development-status.md`
- Modify: `tasks/todo.md`

- [ ] **Step 1: Document bundle semantics**

Document:

- Evidence Store input boundary.
- decision-time and instrument filtering.
- role priority and content-hash dedupe.
- token estimate and schema-instruction preservation.
- explicit non-goals: no Agent execution, real Provider/LLM, Worker loop, Qlib runtime, production scheduling, citation repair, Quant Evidence Adapter or report rendering.

- [ ] **Step 2: Update progress checklist**

Mark only `SAL-P5-003` as `DONE`, update P5 to `3/18`, total to `91/129`, add `DEC-089` and `AEV-091`, and set next READY task according to dependencies (`SAL-P5-004`, `SAL-P5-005` and `SAL-P5-006` remain the next local P5 prerequisites).

- [ ] **Step 3: Update status snapshot**

Update current task, completion range, checkpoint placeholders and next startup prompt; keep G5 as not passed and preserve Gate G4/P5 strict non-goals.

### Task 4: Verification And Commit

**Files:**
- No new files beyond Tasks 1-3.

- [ ] **Step 1: Run focused and related tests**

Run:

```bash
uv run --extra core --extra dev python -m pytest tests/application/test_evidence_bundle_builder.py -q
uv run --extra core --extra dev python -m pytest tests/application/test_evidence_bundle_builder.py tests/repositories/test_evidence_store.py tests/evidence/test_evidence_schema_contract.py tests/architecture/test_architecture_boundaries.py -q
```

Expected: all pass.

- [ ] **Step 2: Run full verification**

Run:

```bash
uv run --extra core --extra dev python -m pytest -q
uv run --extra core --extra dev python -m compileall -q src/serenity_alpha_lab tests
scripts/verify-python-dependency-lock.sh
git rev-parse upstream/dsa-v3.26.1
git diff --check
```

Expected: full pytest passes with existing skip count, compileall/diff/lock pass, upstream tag remains `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`.

- [ ] **Step 3: Commit**

Stage only SAL-P5-003 files and commit:

```bash
git add tasks/todo.md docs/superpowers/plans/2026-07-26-evidence-bundle-builder.md tests/application/test_evidence_bundle_builder.py src/serenity_alpha_lab/application/evidence_bundle_builder.py src/serenity_alpha_lab/application/__init__.py docs/evidence-bundle-builder.md docs/development-progress-checklist.md docs/development-status.md
git commit -m "feat(P5): 实现 EvidenceBundle Builder"
```
