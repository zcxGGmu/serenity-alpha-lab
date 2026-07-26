# Evidence Store Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement `SAL-P5-002` by adding an offline Evidence Store repository that persists immutable evidence metadata, content-addressed bodies, revision records and scoped queries.

**Architecture:** Add `serenity_alpha_lab.repositories.evidence_store` as a local filesystem repository layered on top of the existing P1 `ArtifactStore` port. Evidence body payloads are sanitized and canonicalized before publication through `ArtifactStore`; metadata records are JSON files keyed by stable evidence id and access scope. Corrections never mutate existing evidence; they append a revision record linking old and replacement evidence. Keep P5 Agent execution, bundle building, Quant adapters, citation validation, real Provider/LLM calls, Worker loops, Qlib runtime and report rendering out of scope.

**Tech Stack:** Python 3.11 stdlib dataclasses/enums/pathlib/json/hashlib, existing Pydantic `EvidenceRecord`, existing `ArtifactStore` / `LocalArtifactStore`, pytest.

---

### Task 1: Red Evidence Store Tests

**Files:**
- Create: `tests/repositories/test_evidence_store.py`

- [ ] **Step 1: Write failing tests for store behavior**

```python
from __future__ import annotations

from datetime import UTC, datetime

import pytest

from serenity_alpha_lab.domain.artifacts import ArtifactRetentionTier
from serenity_alpha_lab.evidence.schema import (
    EvidenceEvaluationScope,
    EvidenceKind,
    EvidenceRecord,
    EvidenceSource,
    EvidenceTrustLevel,
)
from serenity_alpha_lab.repositories.evidence_store import (
    EvidenceAccessScope,
    EvidenceRevisionReason,
    EvidenceStoreAccessDenied,
    EvidenceStoreConflict,
    LocalEvidenceStore,
)
from serenity_alpha_lab.repositories.local_artifact_store import LocalArtifactStore


NOW = datetime(2026, 7, 26, 16, 0, tzinfo=UTC)
HASH = "sha256:" + "a" * 64


def _store(tmp_path):
    artifact_store = LocalArtifactStore(tmp_path / "artifacts")
    return LocalEvidenceStore(tmp_path / "evidence", artifact_store=artifact_store), artifact_store


def _evidence(evidence_id: str = "ev_metric_001") -> EvidenceRecord:
    return EvidenceRecord(
        evidence_id=evidence_id,
        kind=EvidenceKind.BACKTEST_PERFORMANCE_METRICS,
        evaluation_scope=EvidenceEvaluationScope.FORMAL_PORTFOLIO_BACKTEST,
        title="Backtest metric report",
        summary="Metric report summary",
        source=EvidenceSource(
            source_id="btm_001",
            source_type="artifact",
            schema_name="quant.backtest.performance_metrics",
            schema_version="1.0.0",
        ),
        available_at=NOW,
        content_hash=HASH,
        trust=EvidenceTrustLevel.AUTHORITATIVE,
        dataset_versions={"bars": "dsv_" + "1" * 32},
        run_id="run-001",
        stage_id="stage-metrics",
    )


def test_store_publishes_sanitized_body_and_queryable_evidence_metadata(tmp_path) -> None:
    store, artifact_store = _store(tmp_path)
    body = {"metric": "cumulative_return", "value": "0.024660", "api_key": "secret"}

    persisted = store.put_evidence(
        _evidence(),
        body,
        tenant_id="tenant-a",
        team_id="team-alpha",
        owner_user_id="user-1",
        access_scope=EvidenceAccessScope.TEAM,
        created_at=NOW,
        retention_tier=ArtifactRetentionTier.ARCHIVE,
    )

    assert persisted.evidence.evidence_id == "ev_metric_001"
    assert persisted.evidence.artifact_id is not None
    assert persisted.evidence.artifact_hash == persisted.evidence.content_hash
    assert persisted.body_sha256 == persisted.evidence.content_hash
    assert persisted.access_scope is EvidenceAccessScope.TEAM
    assert artifact_store.get_bytes(persisted.body_artifact_id) == (
        b'{"api_key":"[REDACTED]","metric":"cumulative_return","value":"0.024660"}'
    )
    assert store.get_evidence("ev_metric_001", tenant_id="tenant-a", team_id="team-alpha").evidence == persisted.evidence
    assert [item.evidence.evidence_id for item in store.find_evidence(tenant_id="tenant-a", team_id="team-alpha")] == [
        "ev_metric_001"
    ]


def test_store_deduplicates_same_scope_metadata_and_rejects_conflicting_id(tmp_path) -> None:
    store, _ = _store(tmp_path)
    evidence = _evidence()

    first = store.put_evidence(evidence, {"value": "0.024660"}, tenant_id="tenant-a", team_id="team-alpha", created_at=NOW)
    second = store.put_evidence(evidence, {"value": "0.024660"}, tenant_id="tenant-a", team_id="team-alpha", created_at=NOW)

    assert second == first
    conflicting = evidence.model_copy(update={"summary": "different metadata"})
    with pytest.raises(EvidenceStoreConflict, match="already exists"):
        store.put_evidence(conflicting, {"value": "0.024660"}, tenant_id="tenant-a", team_id="team-alpha", created_at=NOW)


def test_revision_creates_new_evidence_and_preserves_previous_record(tmp_path) -> None:
    store, _ = _store(tmp_path)
    original = store.put_evidence(_evidence("ev_metric_001"), {"value": "0.024660"}, tenant_id="tenant-a", created_at=NOW)
    replacement = _evidence("ev_metric_002").model_copy(update={"summary": "Corrected metric summary"})

    revision = store.revise_evidence(
        previous_evidence_id=original.evidence.evidence_id,
        replacement_evidence=replacement,
        body={"value": "0.024661"},
        tenant_id="tenant-a",
        created_at=NOW,
        reason=EvidenceRevisionReason.CORRECTION,
        note="corrected rounding",
    )

    assert revision.previous_evidence_id == "ev_metric_001"
    assert revision.replacement_evidence_id == "ev_metric_002"
    assert store.get_evidence("ev_metric_001", tenant_id="tenant-a").evidence.summary == "Metric report summary"
    assert store.get_evidence("ev_metric_002", tenant_id="tenant-a").evidence.summary == "Corrected metric summary"
    assert [item.replacement_evidence_id for item in store.list_revisions(tenant_id="tenant-a")] == ["ev_metric_002"]


def test_private_and_team_scopes_are_isolated(tmp_path) -> None:
    store, _ = _store(tmp_path)
    store.put_evidence(
        _evidence("ev_private"),
        {"value": 1},
        tenant_id="tenant-a",
        team_id="team-alpha",
        owner_user_id="user-1",
        access_scope=EvidenceAccessScope.PRIVATE,
        created_at=NOW,
    )

    with pytest.raises(EvidenceStoreAccessDenied):
        store.get_evidence("ev_private", tenant_id="tenant-a", team_id="team-alpha", owner_user_id="user-2")
    with pytest.raises(EvidenceStoreAccessDenied):
        store.get_evidence("ev_private", tenant_id="tenant-a", team_id="team-beta", owner_user_id="user-1")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --extra core --extra dev python -m pytest tests/repositories/test_evidence_store.py -q`

Expected: FAIL with missing `serenity_alpha_lab.repositories.evidence_store`.

### Task 2: Minimal Evidence Store Implementation

**Files:**
- Create: `src/serenity_alpha_lab/repositories/evidence_store.py`
- Modify: `src/serenity_alpha_lab/repositories/__init__.py`

- [ ] **Step 1: Implement repository types and local persistence**

Create immutable dataclasses:

- `EvidenceAccessScope`: `private`, `team`, `public`.
- `EvidenceRevisionReason`: `correction`, `source_revision`, `policy_reclassification`, `redaction`.
- `PersistedEvidence`: evidence record, artifact id/hash, body hash, tenant/team/user scope, created_at.
- `EvidenceRevisionRecord`: revision id, tenant, previous evidence id, replacement evidence id, reason, note, created_at.

Create `LocalEvidenceStore` with:

- `put_evidence()`: sanitize body, canonicalize JSON bytes, publish through `ArtifactStore`, update `EvidenceRecord` with artifact id/hash/content hash, write metadata record atomically and dedupe identical records.
- `revise_evidence()`: verify previous record is readable, persist replacement evidence, append revision link, leave previous metadata untouched.
- `get_evidence()`, `find_evidence()`, `list_revisions()`.
- file layout `records/<tenant>/<evidence_id>.json`, `revisions/<tenant>/<revision_id>.json`, `tmp/`.

- [ ] **Step 2: Export store types**

Add `LocalEvidenceStore`, error classes and enum/dataclass exports to `src/serenity_alpha_lab/repositories/__init__.py`.

- [ ] **Step 3: Run target tests**

Run: `uv run --extra core --extra dev python -m pytest tests/repositories/test_evidence_store.py -q`

Expected: PASS.

### Task 3: Documentation And Status Evidence

**Files:**
- Create: `docs/evidence-store.md`
- Modify: `docs/development-progress-checklist.md`
- Modify: `docs/development-status.md`
- Modify: `tasks/todo.md`

- [ ] **Step 1: Document Evidence Store semantics**

Document:

- Artifact-backed body storage and canonical sanitization.
- Immutable metadata and revision records.
- Dedupe keys.
- tenant/team/user access scope.
- explicit non-goals: no Agent execution, EvidenceBundle Builder, Quant Evidence Adapter, Citation Validator, real Provider/LLM, Worker loop, Qlib runtime or report rendering.

- [ ] **Step 2: Update progress checklist**

Mark only `SAL-P5-002` as `DONE`, update P5 to `2/18`, total to `90/129`, add `DEC-088` and `AEV-090`, and set next READY task to `SAL-P5-003`.

- [ ] **Step 3: Update status snapshot**

Update current task, completion range, checkpoint placeholders and next startup prompt to point to `SAL-P5-003`; keep G5 as not passed and preserve all Gate G4/P5 constraints.

### Task 4: Verification And Commit

**Files:**
- No new files beyond Tasks 1-3.

- [ ] **Step 1: Run focused and related tests**

Run:

```bash
uv run --extra core --extra dev python -m pytest tests/repositories/test_evidence_store.py -q
uv run --extra core --extra dev python -m pytest tests/repositories/test_evidence_store.py tests/evidence/test_evidence_schema_contract.py tests/repositories/test_local_artifact_store.py tests/architecture/test_architecture_boundaries.py -q
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

Stage only SAL-P5-002 files and commit:

```bash
git add tasks/todo.md docs/superpowers/plans/2026-07-26-evidence-store.md tests/repositories/test_evidence_store.py src/serenity_alpha_lab/repositories/evidence_store.py src/serenity_alpha_lab/repositories/__init__.py docs/evidence-store.md docs/development-progress-checklist.md docs/development-status.md
git commit -m "feat(P5): 实现 Evidence Store"
```
