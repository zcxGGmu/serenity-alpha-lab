# SAL-P5-003 EvidenceBundle Builder Plan

> Scope: Implement an offline EvidenceBundle Builder that constructs minimal, role-scoped context from `SAL-P5-002` Evidence Store records by instrument, decision time and token budget. This task must not start Evidence Agent, real Provider/LLM calls, Worker loop, Qlib runtime, production scheduling, report rendering, Citation Validator, Quant Evidence Adapter or formal portfolio backtest promotion.

## Checklist

- [x] Re-read `AGENTS.md`, `tasks/lessons.md`, current status/checklist, `docs/evidence-claim-report-schema.md`, `docs/evidence-store.md`, current Evidence schema/store code and current Git state.
- [x] Attempt read-only subagent review; platform rejected payload shape after retries, so follow project lesson and use local senior review plus fresh verification fallback.
- [x] Write implementation plan at `docs/superpowers/plans/2026-07-26-evidence-bundle-builder.md`.
- [x] Red: add `tests/application/test_evidence_bundle_builder.py` proving decision-time filtering, instrument scoping, content-hash dedupe, role priority, budget trimming and schema-instruction budget guard fail before implementation.
- [x] Green: add `src/serenity_alpha_lab/application/evidence_bundle_builder.py` with request/budget/item/bundle DTOs and an offline builder over `LocalEvidenceStore`.
- [x] Export EvidenceBundle Builder types from `src/serenity_alpha_lab/application/__init__.py`.
- [x] Add `docs/evidence-bundle-builder.md` with bundle semantics, priority policy, token estimate policy, scope limits and non-goals.
- [x] Update `docs/development-progress-checklist.md` with `SAL-P5-003` done, P5 `3/18`, total `91/129`, `AEV-091`, `DEC-089` and next-step status.
- [x] Update `docs/development-status.md` with latest task/checkpoint placeholders, completion range and next startup prompt for `SAL-P5-004` / `SAL-P5-005` as allowed by dependencies.
- [x] Run focused EvidenceBundle tests, related Evidence/Store/Architecture suite, full pytest, compileall, dependency lock guard, immutable tag check and `git diff --check`.
- [x] Review changes, record subagent fallback, stage only `SAL-P5-003` files and create required Chinese checkpoint commit.

## Scope Guard

- Builder may read accessible `EvidenceRecord` metadata through the local Evidence Store and assemble deterministic context payloads only.
- Builder must exclude evidence with `available_at > decision_time`.
- When `instrument_id` is provided, Builder may include matching instrument evidence and global evidence only; different instrument evidence must be excluded.
- Duplicate `content_hash` records are deduped deterministically, keeping the highest-priority record.
- Token estimates are deterministic approximations. The fixed schema instructions are never truncated; if the budget cannot fit them, the builder fails fast.
- Over-budget evidence is trimmed by priority and recorded as excluded metadata; it must not silently disappear.
- Builder APIs must stay offline and local; no Provider SDK, LiteLLM, Qlib, Worker, scheduler, renderer, FastAPI router, SQLAlchemy database or DSA runtime import.

## Review Notes

- Started 2026-07-26 from clean branch `codex/p0-baseline-status`, ahead of origin, with latest log starting `13b4985e`, `dd4dac78`, `bb02d84e`.
- Subagent dispatch attempts failed due wrapper payload validation (`reasoning_effort must not be empty`; then message/items exclusivity despite empty `message`). Per project lesson, no further retry. Fallback is local senior review plus fresh verification.
- Red target: `1 error`, missing `serenity_alpha_lab.application.evidence_bundle_builder`.
- Focused target: `3 passed`.
- Related EvidenceBundle / Evidence Store / Evidence Schema / Architecture suite: `27 passed`.
- Full pytest: `417 passed, 3 skipped`.
- Compileall PASS; dependency lock guard PASS (`Resolved 298 packages`); immutable tag stayed `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`; `git diff --check` PASS.
- Local senior review confirmed `application.evidence_bundle_builder` depends only on stdlib + P5 schema + P5 Evidence Store, preserves schema instructions before evidence trimming, excludes future and different-instrument evidence, dedupes by `content_hash`, records budget exclusions, and does not import or start Evidence Agent, Provider/LLM, Worker, Qlib, FastAPI, SQLAlchemy or DSA runtime.
