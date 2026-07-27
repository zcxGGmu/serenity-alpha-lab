# SAL-P5-009 Intel Agent Evidence Adapter Plan

> Scope: Add an offline Intel Agent compatibility boundary that consumes prebuilt intel EvidenceBundle records and SourceTrust prompt-safe records, validates structured event/citation output, and produces DSA-compatible intel/news fields. This task must not fetch news/search/social content, call real Providers or LLMs, start Worker loops, initialize Qlib runtime, schedule production work, validate final report citations, render reports, or promote formal portfolio backtests.

## Checklist

- [x] Re-read AGENTS/status/checklist/P5 evidence docs, current Git state, Technical Agent adapter pattern, Prompt Registry, EvidenceBundle Builder and SourceTrust contracts.
- [x] Attempt read-only subagent implementation-map review; wrapper rejected earlier payloads (`reasoning_effort must not be empty`, then `Provide either message or items, but not both`) and no stable native spawn entry was available in the current tool panel, so follow project lesson and proceed with local senior review plus fresh verification fallback.
- [x] Red: add `tests/application/test_intel_agent_evidence_adapter.py` proving Intel prompt payload uses intel bundle + source trust metadata, separates event/published/observed/available times, rejects stale/low-trust/malicious-only strong claims, and maps to DSA-compatible news/intel output.
- [x] Green: add `src/serenity_alpha_lab/application/intel_agent.py` with offline prompt request/payload, structured events/output, result validation and DSA compatibility mapping.
- [x] Export public Intel Agent adapter symbols from `src/serenity_alpha_lab/application/__init__.py`.
- [x] Add architecture guard proving Intel Agent boundary has no concrete DSA Agent, Provider/LLM, Worker, Qlib, FastAPI, SQLAlchemy, repository write or report renderer imports.
- [x] Add `docs/intel-agent-evidence-adapter.md` with contract table, evidence/source trust rules, event time rules, conflict/staleness/malicious handling, DSA compatibility fields, non-goals and verification evidence.
- [x] Update `docs/development-progress-checklist.md` with `SAL-P5-009` done, P5 `9/18`, total `97/129`, AEV/DEC rows and next-step status.
- [x] Update `docs/development-status.md` with latest task/checkpoint anchors, completion range and next startup prompt for `SAL-P5-010`; implementation checkpoint hash has been recorded as `a6974362 feat(P5): 改造 Intel Agent`.
- [x] Run focused Intel tests, architecture guard, related Intel/SourceTrust/EvidenceBundle/PromptRegistry/AgentStage/Architecture suite, full pytest, compileall, dependency lock guard, immutable tag check and `git diff --check`.
- [x] Review changes, stage only SAL-P5-009 files, create required Chinese checkpoint commit, then status/hash-anchor docs commit if needed.

## File Targets

- Create: `src/serenity_alpha_lab/application/intel_agent.py` for offline Intel Agent evidence/source-trust adapter and DSA compatibility result mapping.
- Create: `tests/application/test_intel_agent_evidence_adapter.py` for Red/Green contract coverage.
- Modify: `src/serenity_alpha_lab/application/__init__.py` to export public Intel Agent symbols.
- Modify: `tests/architecture/test_architecture_boundaries.py` to lock runtime-free imports.
- Create: `docs/intel-agent-evidence-adapter.md` for SAL-P5-009 evidence record.
- Modify: `docs/development-status.md`, `docs/development-progress-checklist.md` and `tasks/todo.md` during task status sync.

## Scope Guard

- Intel adapter prepares prompt payloads and validates already-produced structured output only; it never invokes a model, runs search/news tools, fetches webpages, reads Evidence bodies, writes Evidence Store, renders reports or starts workers.
- Intel input is limited to unstructured/source-trust-backed EvidenceBundle records such as company announcements, regulatory/official disclosures, news, wire news, search results, social posts and unknown sources represented by `EvidenceRecord.metadata.source_trust` prompt-safe records.
- Event time, source `published_at`, `observed_at` and evidence `available_at` must remain distinct; stale, duplicated, low-trust, time-conflicted and malicious-instruction records are marked or rejected according to SourceTrust verdict metadata.
- Strong claims require at least one source with `strong_claim_allowed=true` and no unresolved malicious/time-conflict issue; low/untrusted/social/search-only evidence can support watchlist/risk hints, not strong conclusions.
- Later tasks still own Risk/Portfolio Agent, Decision Agent, model routing/cache/budget, Citation Validator, report renderer and final G5 research report publication.

## Review Notes

- Subagent scope review fallback: wrapper rejected earlier payload shapes and the current tool panel did not expose a stable direct spawn entry after discovery; local senior review will cover Technical Agent pattern, Prompt Registry binding, SourceTrust metadata, DSA news/intel compatibility and architecture import boundaries.
- Red target: `uv run --extra core --extra dev python -m pytest tests/application/test_intel_agent_evidence_adapter.py -q` failed with missing `serenity_alpha_lab.application.intel_agent` (`1 error`).
- Focused target after implementation: `4 passed`; Intel architecture guard plus focused target: `5 passed`; TechnicalAgent + SourceTrust regression slice: `12 passed`.
- Related IntelAgent/EvidenceBundle/SourceTrust/PromptRegistry/EvidenceSchema/AgentStageStore/Architecture suite: `47 passed`.
- Full pytest: `451 passed, 3 skipped`; compileall PASS; dependency lock guard PASS with `Resolved 298 packages`; immutable tag stayed `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`; disposable DSA worktree applied patches `0001..0006` without mutating locked `.worktrees/dsa-v3.26.1`; `git diff --check` PASS.
- Local review notes: Intel adapter imports only offline application/evidence modules, rejects non-intel bundle/binding context, enforces `unstructured_source` + `market_intelligence` + `source_trust` + `llm_recompute_allowed=false`, excludes duplicate/malicious sources, prevents stale/low-trust strong events, rejects Intel `numeric_metric` claims and maps DSA-compatible intel/news output.
- Fresh final verification after status docs: related Intel/P5 suite `47 passed`; full pytest `451 passed, 3 skipped`; compileall PASS; dependency lock guard PASS with `Resolved 298 packages`; immutable tag stayed `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`; disposable DSA worktree applied patches `0001..0006` and was removed; `git diff --check` PASS.
- Implementation checkpoint: `a6974362 feat(P5): 改造 Intel Agent`; status-sync checkpoint: `7521d6d9 docs: 同步 SAL-P5-009 checkpoint hash`.
