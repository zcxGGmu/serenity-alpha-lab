# SAL-P5-008 Technical Agent Evidence Adapter Plan

> Scope: Add an offline Technical Agent compatibility boundary that consumes only technical/screen/factor EvidenceBundle records, validates structured cited output, and produces DSA-compatible technical dashboard fields. This task must not call real Providers or LLMs, start Worker loops, initialize Qlib runtime, schedule production work, render reports, validate final report citations, or promote formal portfolio backtests.

## Checklist

- [x] Re-read `AGENTS.md`, `tasks/lessons.md`, current status/checklist, P5 evidence docs, Prompt Registry, Agent Stage persistence, current Git state and DSA Technical Agent compatibility fields.
- [x] Attempt read-only subagent scope review; wrapper rejected both attempts (`reasoning_effort must not be empty`, then `full-history forked agents inherit the parent agent type`), so follow project lesson and use local senior review plus fresh verification fallback.
- [x] Red: add `tests/application/test_technical_agent_evidence_adapter.py` proving Technical Agent prompt payload uses only technical/screen/factor evidence, rejects formal backtest evidence, requires cited numeric claims, and maps to legacy DSA dashboard/opinion fields.
- [x] Green: add `src/serenity_alpha_lab/application/technical_agent.py` with offline prompt request/payload, structured output, result validation and DSA compatibility mapping.
- [x] Export public Technical Agent adapter symbols from `src/serenity_alpha_lab/application/__init__.py`.
- [x] Add architecture guard proving the Technical Agent boundary has no concrete DSA Agent, Provider/LLM, Worker, Qlib, FastAPI, SQLAlchemy or report renderer imports.
- [x] Add `docs/technical-agent-evidence-adapter.md` with contract table, evidence allowlist, citation rules, DSA compatibility fields, non-goals and verification evidence.
- [x] Update `docs/development-progress-checklist.md` with `SAL-P5-008` done, P5 `8/18`, total `96/129`, new DEC/AEV rows and next-step status.
- [x] Update `docs/development-status.md` with latest task/checkpoint anchors, completion range and next startup prompt for `SAL-P5-009`.
- [x] Run focused Technical Agent tests, related EvidenceBundle/QuantEvidence/PromptRegistry/AgentStage/Architecture suite, full pytest, compileall, dependency lock guard, immutable tag check and `git diff --check`.
- [x] Review changes, stage only `SAL-P5-008` files and create required Chinese checkpoint commit, then status/hash-anchor docs commit if needed.

## File Targets

- Create: `src/serenity_alpha_lab/application/technical_agent.py` for offline Technical Agent evidence adapter and DSA compatibility result mapping.
- Create: `tests/application/test_technical_agent_evidence_adapter.py` for Red/Green contract coverage.
- Modify: `src/serenity_alpha_lab/application/__init__.py` to export public Technical Agent symbols.
- Modify: `tests/architecture/test_architecture_boundaries.py` to lock runtime-free imports.
- Create: `docs/technical-agent-evidence-adapter.md` for SAL-P5-008 evidence record.
- Modify: `docs/development-status.md` and `docs/development-progress-checklist.md` only during task status sync.

## Scope Guard

- The adapter prepares prompt payloads and validates already-produced structured output only; it never invokes a model, runs tools, fetches quotes/history, calculates indicators, reads Evidence bodies, writes Evidence Store, renders reports or starts workers.
- Technical Agent input is limited to `screen_snapshot`, `screen_pipeline_snapshot`, `factor_evaluation` and `factor_cache_manifest` evidence. Formal portfolio backtest, risk, bias audit, API lineage and UI lineage evidence are rejected for this role.
- Numeric claims must use `deterministic_evidence`, include unit/formula version, and cite output citations whose `evidence_id` exists in the current EvidenceBundle.
- DSA compatibility is a mapping layer only: it returns `agent_name=technical`, `signal`, `confidence`, `reasoning`, `key_levels`, raw structured payload, and dashboard fields such as `technical_analysis`, `trend_analysis`, `ma_analysis`, `volume_analysis` and `pattern_analysis`.
- Later tasks still own Intel/Risk/Decision Agent rewrites, model routing/cache/budget, Citation Validator, report renderer and final G5 research report publication.

## Review Notes

- Red target: `1 error`, missing `serenity_alpha_lab.application.technical_agent`.
- Review regression Red target: `3 failed, 4 passed`, proving missing evidence scope/recompute guard, numeric citation mismatch guard and DSA `data_perspective` compatibility block.
- Focused target: `7 passed`.
- Technical Agent architecture guard: `1 passed`.
- Related TechnicalAgent / EvidenceBundle / QuantEvidenceAdapter / PromptRegistry / AgentStageStore / Architecture suite: `41 passed`.
- Full pytest: `445 passed, 3 skipped`.
- Compileall PASS; immutable tag stayed `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`.
- Added explicit prompt binding run/stage context guard so Technical Agent payloads cannot be prepared with a mismatched concrete `PromptRunBinding`.
- Code-review subagent reported HIGH evidence allowlist and numeric citation lineage gaps plus MEDIUM DSA dashboard/documentation mismatches; fixed by enforcing kind+scope+`llm_recompute_allowed=false`, evidence/citation dataset/run/stage/artifact lineage, numeric claim value/unit/formula/dataset/run/artifact consistency and nested `data_perspective` compatibility.
- Dependency lock guard PASS with `Resolved 298 packages`; `git diff --check` PASS.
- Subagent scope review attempted twice but wrapper rejected payloads; local senior review confirmed `technical_agent` imports only offline application/evidence dependencies and performs no Provider/LLM/Worker/Qlib/FastAPI/SQLAlchemy/DSA Agent runtime work.
- Implementation checkpoint: `74701974 feat(P5): 改造 Technical Agent`; status-sync checkpoint: `7b0d572a docs: 同步 SAL-P5-008 checkpoint hash`; hash-anchor checkpoint: `cc1b327e docs: 记录 SAL-P5-008 状态同步 hash`; final docs solidification checkpoint: `e35b0612 docs: 固化 SAL-P5-008 hash-anchor checkpoint`.
