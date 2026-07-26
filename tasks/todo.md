# SAL-P5-002 Evidence Store Plan

> Scope: Implement a local Evidence Store repository that persists immutable `EvidenceRecord` metadata, content-addressed sanitized evidence bodies, revision links, ownership scope and deterministic query semantics. This task must not start Evidence Agent, EvidenceBundle Builder, Quant Evidence Adapter, Citation Validator, real Provider/LLM calls, Worker loop, Qlib runtime, production scheduling or report rendering.

## Checklist

- [x] Re-read `AGENTS.md`, `tasks/lessons.md`, current status/checklist, `docs/evidence-claim-report-schema.md`, `docs/ai-stock-quant-platform-development-plan.md`, P1 ArtifactStore docs/code and current Git state.
- [x] Attempt subagent read-only review once; platform rejected empty optional fields, so follow project lesson and use local senior review plus fresh verification fallback.
- [x] Write implementation plan at `docs/superpowers/plans/2026-07-26-evidence-store.md`.
- [x] Red: add `tests/repositories/test_evidence_store.py` proving body publication, metadata persistence, dedupe, revisions and ownership isolation fail before implementation.
- [x] Green: add `src/serenity_alpha_lab/repositories/evidence_store.py` with local repository, immutable metadata records, content-addressed body publication through `ArtifactStore`, revision history and query helpers.
- [x] Export Evidence Store types from `src/serenity_alpha_lab/repositories/__init__.py`.
- [x] Add `docs/evidence-store.md` with semantics, storage layout, access-scope rules, revision behavior and non-goals.
- [x] Update `docs/development-progress-checklist.md` with `SAL-P5-002` done, P5 `2/18`, total `90/129`, `AEV-090`, `DEC-088` and next-step status.
- [x] Update `docs/development-status.md` with latest task/checkpoint placeholders, completion range and next startup prompt for `SAL-P5-003`.
- [x] Run focused Evidence Store tests, related Evidence/Repository/Architecture suite, full pytest, compileall, dependency lock guard, immutable tag check and `git diff --check`.
- [ ] Review changes, record subagent fallback, stage only `SAL-P5-002` files and create required Chinese checkpoint commit.

## Scope Guard

- Store may persist `EvidenceRecord` metadata and body artifacts only; it may not build bundles, adapt Quant outputs into evidence, validate report citations, invoke models, render reports or schedule work.
- Evidence metadata remains immutable. Any correction creates a new `EvidenceRecord` and a `EvidenceRevisionRecord` linking previous to replacement evidence.
- Body bytes are normalized to deterministic JSON, redacted for obvious sensitive fields, published via P1 `ArtifactStore`, and referenced by `artifact_id`, `artifact_hash` and `content_hash`.
- Same tenant/team/user plus same body hash and same Evidence metadata identity must dedupe to the existing persisted record.
- Private evidence queries must require owner user match; team evidence must require team match; public evidence can be queried across scopes.
- Store APIs must stay offline and local; no SQLAlchemy, FastAPI, Provider SDK, LiteLLM, Qlib, Worker or DSA runtime import.

## Review Notes

- Started 2026-07-26 from clean branch `codex/p0-baseline-status`, ahead of origin, with latest log starting `cc0c000c`, `539b4652`, `25f6ed45`.
- Subagent dispatch rejected by platform wrapper (`reasoning_effort must not be empty`) on full and minimal payload attempts; per `tasks/lessons.md`, no further retry. Fallback is local senior review plus fresh test evidence.
- Red target: `1 error`, missing `serenity_alpha_lab.repositories.evidence_store`.
- Focused target: `4 passed`.
- Related Evidence Store / Evidence Schema / LocalArtifactStore / Architecture suite: `28 passed`.
- Full pytest: `414 passed, 3 skipped`.
- Compileall PASS; dependency lock guard PASS (`Resolved 298 packages`); immutable tag stayed `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`; `git diff --check` PASS.
- Local senior review confirmed `repositories.evidence_store` depends only on stdlib + P1 `ArtifactStore` + P5 schema, stores sanitized canonical body bytes, rejects conflicting immutable metadata, preserves previous records on revision, enforces scope checks, and does not import or start Evidence Agent, Provider/LLM, Worker, Qlib, FastAPI, SQLAlchemy or DSA runtime.
