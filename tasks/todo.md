# SAL-P5-006 Prompt and Output Schema Registry Plan

> Scope: Build an offline, versioned registry for role prompts, output schemas, tool declarations, model capability declarations and run prompt bindings. This task must not execute Evidence Agent stages, call real Providers/LLMs, start Worker loops, initialize Qlib runtime, schedule production work, render reports or promote formal portfolio backtests.

## Checklist

- [x] Re-read `AGENTS.md`, `tasks/lessons.md`, current status/checklist, P5 evidence docs, Source Trust doc, Quant Evidence Adapter doc, current Git state and relevant registry/schema patterns.
- [x] Attempt read-only subagent scope review; wrapper rejected payloads (`reasoning_effort must not be empty`, then `Provide either message or items`), so follow project lesson and use local senior review plus fresh verification fallback.
- [x] Red: add `tests/evidence/test_prompt_schema_registry.py` proving published prompt immutability, output schema compatibility, tool/model capability declarations and run prompt binding version capture.
- [x] Green: add `src/serenity_alpha_lab/evidence/prompt_registry.py` with pure offline registry, canonical hashes, semver compatibility checks and default role prompt declarations.
- [x] Export registry types from `src/serenity_alpha_lab/evidence/__init__.py`.
- [x] Add architecture guard showing `evidence.prompt_registry` remains free of Provider/LLM/Agent/Worker/Qlib/SQLAlchemy/FastAPI/runtime imports.
- [x] Add `docs/prompt-output-schema-registry.md` with contract table, registry rules, non-goals and verification evidence.
- [x] Update `docs/development-progress-checklist.md` with `SAL-P5-006` done, P5 `6/18`, total `94/129`, new DEC/AEV rows and next-step status.
- [x] Update `docs/development-status.md` with latest task/checkpoint anchors, completion range and next startup prompt for `SAL-P5-007`.
- [x] Run focused registry tests, related Evidence/Bundle/Quant/Architecture suite, full pytest, compileall, dependency lock guard, immutable tag check and `git diff --check`.
- [x] Review changes, stage only `SAL-P5-006` files and create required Chinese checkpoint commit, then status/hash-anchor docs commit.

## File Targets

- Create: `src/serenity_alpha_lab/evidence/prompt_registry.py` for offline prompt/schema/tool/model registry.
- Create: `tests/evidence/test_prompt_schema_registry.py` for Red/Green contract coverage.
- Modify: `src/serenity_alpha_lab/evidence/__init__.py` to export public registry symbols.
- Modify: `tests/architecture/test_architecture_boundaries.py` to lock runtime-free imports.
- Create: `docs/prompt-output-schema-registry.md` for SAL-P5-006 evidence record.
- Modify: `docs/development-status.md` and `docs/development-progress-checklist.md` only during task status sync.

## Scope Guard

- Registry stores metadata and hashes only; it does not invoke models, execute tools, call Providers, read Evidence bodies, persist Evidence Store records, build reports or start stages.
- Published prompt versions are immutable; same `prompt_id + version` cannot be overwritten with changed content.
- Run bindings must capture concrete prompt/schema/tool/model versions and hashes; `latest` aliases are rejected.
- Default role prompts must preserve P5 evidence rules: use only included EvidenceBundle records, cite evidence ids/hashes, never recompute deterministic quant metrics, and respect source trust/risk hard gates.
- Tool declarations must be explicit about read-only/no-side-effect permissions; shell, trading and database-write tool categories remain forbidden in this registry.



## Review Notes

- Red target: `1 error`, missing `serenity_alpha_lab.evidence.prompt_registry`.
- Focused target: `4 passed`.
- Prompt registry architecture guard: `1 passed`.
- Related PromptRegistry / Evidence schema / SourceTrust / QuantAdapter / EvidenceBundle / Architecture suite: `38 passed`.
- Full pytest: `432 passed, 3 skipped`.
- Compileall PASS; dependency lock guard PASS (`Resolved 298 packages`); immutable tag stayed `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`.
- Subagent scope review attempted but wrapper rejected payloads; local senior review confirmed `evidence.prompt_registry` imports only stdlib, registers metadata only, rejects `latest` and unsafe tool scopes, and performs no Provider/LLM/Worker/Qlib/FastAPI/SQLAlchemy/DSA runtime work.
- Diff hygiene PASS; implementation checkpoint is `cccc1416 feat(P5): 实现 Prompt 与输出 Schema Registry`; status-sync checkpoint is `49a8cd23 docs: 同步 SAL-P5-006 checkpoint hash`; hash-anchor checkpoint is `252189c3 docs: 记录 SAL-P5-006 状态同步 hash`; final docs solidification is this commit.
