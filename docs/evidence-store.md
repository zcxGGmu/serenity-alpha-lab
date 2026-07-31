# Evidence Store

> Task: `SAL-P5-002` Implement Evidence Store<br>
> Date: 2026-07-26<br>
> Status: `APPROVED FOR SAL-P5-003 EVIDENCEBUNDLE INPUT ONLY`

## Conclusion

`SAL-P5-002` adds an offline repository-backed Evidence Store:

```text
src/serenity_alpha_lab/repositories/evidence_store.py
tests/repositories/test_evidence_store.py
```

The store persists immutable `EvidenceRecord` metadata, publishes sanitized content-addressed evidence bodies through the existing P1 `ArtifactStore`, records revision links, and enforces tenant/team/user read scope for local queries. It consumes the schema frozen in `SAL-P5-001` and does not build EvidenceBundles, adapt Quant runtime objects into evidence, validate report citations, execute Agent stages, call real Providers or LLMs, start Worker loops, initialize Qlib runtime, render reports or send notifications.

## Contracts

| Item | Contract |
|---|---|
| Body schema | `research.evidence_body` / `1.0.0` |
| Body content type | `application/vnd.serenity.evidence.body+json` |
| Store implementation | `LocalEvidenceStore` |
| Persisted metadata | `PersistedEvidence` |
| Revision metadata | `EvidenceRevisionRecord` |
| Access scopes | `private`, `team`, `public` |
| Revision reasons | `correction`, `source_revision`, `policy_reclassification`, `redaction` |

## Storage Semantics

Evidence bodies are decoded, recursively sanitized and serialized as canonical JSON with sorted keys and compact separators before publication to `ArtifactStore`. The resulting SHA-256 is written back into the persisted `EvidenceRecord.content_hash` and `artifact_hash` as `sha256:<64 hex>`, while `artifact_id` points to the body artifact manifest.

Local metadata layout:

```text
records/<tenant_id>/<evidence_id>.json
revisions/<tenant_id>/<revision_id>.json
tmp/<atomic-write-token>.tmp
```

The body bytes live under the configured `ArtifactStore`, so the Evidence Store keeps small query metadata separate from content-addressed body storage.

## Immutability

`put_evidence()` is idempotent only when the existing record has the same evidence metadata, tenant/team/user scope, body artifact, body hash and retention tier. Reusing an existing `evidence_id` with different immutable metadata raises `EvidenceStoreConflict`.

Corrections use `revise_evidence()`, which persists a replacement `EvidenceRecord` and appends an `EvidenceRevisionRecord` linking `previous_evidence_id` to `replacement_evidence_id`. Previous evidence metadata remains readable and is not modified in place.

## Access Scope

| Scope | Query rule |
|---|---|
| `public` | Visible within the same tenant. |
| `team` | Requires matching `team_id`. |
| `private` | Requires matching `team_id` when present and matching `owner_user_id`. |

This task implements local scoped queries only. It does not implement authentication, authorization middleware, database row-level security or object-store policies.

## Sanitization

The store redacts obvious sensitive keys such as `api_key`, `token`, `secret`, `password`, `authorization`, `cookie`, `credential`, `private_body`, `raw_prompt` and related variants before any bytes are handed to `ArtifactStore`. The canonical body hash therefore represents the stored sanitized body, not an unredacted source payload.

## Non-Goals

- No EvidenceBundle Builder, role-specific context construction, token budgeting or prioritization.
- No Quant Evidence Adapter that converts P3/P4 runtime objects into `EvidenceRecord` rows.
- No Citation Validator, report renderer, notification outbox or report publication workflow.
- No Prompt/Output Schema Registry, Agent checkpoint, model routing, cache, budget execution or stage orchestration.
- No real Provider calls, real LLM calls, Worker loop, Qlib runtime, production scheduling or DSA runtime migration.
- No change to legacy DSA `/api/v1/backtest/*` Signal Evaluation behavior.

## Verification

| Check | Result |
|---|---|
| Red target | `uv run --extra core --extra dev python -m pytest tests/repositories/test_evidence_store.py -q` initially failed with `ModuleNotFoundError: No module named 'serenity_alpha_lab.repositories.evidence_store'` |
| Focused target | `uv run --extra core --extra dev python -m pytest tests/repositories/test_evidence_store.py -q` -> `4 passed` |
| Related suite | `uv run --extra core --extra dev python -m pytest tests/repositories/test_evidence_store.py tests/evidence/test_evidence_schema_contract.py tests/repositories/test_local_artifact_store.py tests/architecture/test_architecture_boundaries.py -q` -> `28 passed` |
| Full suite | `uv run --extra core --extra dev python -m pytest -q` -> `414 passed, 3 skipped` |
| Compile | `uv run --extra core --extra dev python -m compileall -q src/serenity_alpha_lab tests` -> PASS |
| Dependency lock | `scripts/verify-python-dependency-lock.sh` -> PASS, `Resolved 298 packages` |
| Immutable upstream tag | `git rev-parse upstream/dsa-v3.26.1` -> `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a` |
| Diff hygiene | `git diff --check` -> PASS |

## Approval Record

This record approves local Evidence Store persistence as input to `SAL-P5-003` EvidenceBundle Builder. Later P5 tasks must implement bundle construction, source trust policy, Quant evidence adapters, Agent stages, citation validation, model budgeting and renderers before Gate G5 can pass.
