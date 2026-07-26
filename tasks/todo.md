# SAL-P5-004 Source Trust and Unstructured Cleaning Plan

> Scope: Implement an offline source trust and unstructured-content cleaning boundary for announcements, news/search snippets and social text. This task must not fetch external content, execute Evidence Agent stages, call real Providers or LLMs, start Worker loops, initialize Qlib runtime, schedule production work, render reports or promote formal portfolio backtests.

## Checklist

- [x] Re-read `AGENTS.md`, `tasks/lessons.md`, current status/checklist, `docs/evidence-claim-report-schema.md`, `docs/evidence-store.md`, `docs/evidence-bundle-builder.md`, current Evidence schema/store/bundle code and current Git state.
- [x] Attempt read-only subagent review; platform wrapper repeated the known empty optional-field rejection, so follow project lesson and use local senior review plus fresh verification fallback.
- [x] Red: add `tests/evidence/test_source_trust_cleaning.py` proving source classification, URL/body canonical hashes, low-trust strong-claim guard, external-instruction cleaning and time-conflict flags fail before implementation.
- [x] Green: add `src/serenity_alpha_lab/evidence/source_trust.py` with pure offline TrustPolicy, source descriptors, cleaned body output and deterministic hashes.
- [x] Export source trust types from `src/serenity_alpha_lab/evidence/__init__.py`.
- [x] Add architecture guard covering the new evidence module remains free of Provider/LLM/Agent/Worker/Qlib/runtime imports.
- [x] Add `docs/source-trust-unstructured-cleaning.md` with policy semantics, cleaning rules, scope limits and non-goals.
- [x] Update `docs/development-progress-checklist.md` with `SAL-P5-004` done, P5 `4/18`, total `92/129`, `DEC-090`, `AEV-092` and next-step status.
- [x] Update `docs/development-status.md` with latest task/checkpoint anchors, completion range and next startup prompt for `SAL-P5-005` / `SAL-P5-006`.
- [x] Run focused source trust tests, related Evidence/Store/Bundle/Architecture suite, full pytest, compileall, dependency lock guard, immutable tag check and `git diff --check`.
- [x] Review changes, record subagent fallback, stage only `SAL-P5-004` files and create required Chinese checkpoint commit.

## Scope Guard

- Trust policy is deterministic and local. It consumes caller-provided source metadata and raw text only.
- URL canonicalization and hashing must not perform DNS, HTTP, browser, search, Provider SDK or LLM calls.
- Cleaning removes external instructions from prompt/tool surfaces while retaining redacted markers and issue metadata for audit.
- Low/untrusted sources cannot alone support strong conclusions; output must expose a machine-readable `strong_claim_allowed=false` and corroboration requirement.
- Published/observed/available timestamp conflicts must be explicit warnings, not silently normalized.
- The module must live under `serenity_alpha_lab.evidence` and import only stdlib plus existing Evidence schema types.
- This task does not add Evidence Agent stages, Quant Evidence Adapter, Prompt Registry, Citation Validator, report renderer, Worker runtime, Qlib runtime or production scheduling.

## Review Notes

- Started 2026-07-26 from clean branch `codex/p0-baseline-status`, ahead of origin, with latest log starting `9bd5584e`, `ae703bba`, `c1b34935`, `59196858`.
- Subagent dispatch failed with `reasoning_effort must not be empty` because the wrapper populated empty optional fields; per `tasks/lessons.md`, no further retry. Fallback is local senior review plus fresh verification.
- Red target: `1 error`, missing `serenity_alpha_lab.evidence.source_trust`.
- Focused target: `5 passed`.
- Related SourceTrust / Architecture suite: `21 passed`.
- Related SourceTrust / Evidence Store / EvidenceBundle / Evidence Schema / Architecture suite: `33 passed`.
- Full pytest: `423 passed, 3 skipped`.
- Compileall PASS; dependency lock guard PASS (`Resolved 298 packages`); immutable tag stayed `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`; `git diff --check` PASS.
- Local senior review confirmed `evidence.source_trust` depends only on stdlib + P5 evidence schema, performs no network/fetch/Agent/Provider/LLM/Worker/Qlib work, emits prompt-safe records without raw body, and keeps low-trust/time-conflict/malicious-instruction guards explicit for later P5 stages.
- Resume cleanup confirmed latest hash-anchor `00c81f28 docs: 记录 SAL-P5-004 状态同步 hash`; updated `docs/development-status.md` and `docs/development-progress-checklist.md` to remove pending hash-anchor placeholders before moving to `SAL-P5-005` / `SAL-P5-006`.
- Read-only subagent scope review for `SAL-P5-005` / `SAL-P5-006` was attempted once in this resume and rejected by wrapper argument validation (`reasoning_effort must not be empty`, then `Provide either message or items` on minimal retry); per project lesson, no further retries, local senior review fallback remains in effect.
