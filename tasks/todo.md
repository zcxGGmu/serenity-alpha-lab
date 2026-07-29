# SAL-P5-015 Trusted ResearchReport Renderer Implementation Plan

> Scope: Complete only `SAL-P5-015` by adding a trusted offline renderer for validated `ResearchReport` objects. The canonical JSON envelope is the sole authoritative report source; Markdown/HTML are derived display formats. Do not jump to UI/notification, Agent evaluation, Worker runtime, real Provider/LLM calls, Qlib runtime, production scheduling or formal backtest promotion.

## Checklist

- [x] Re-read `AGENTS.md`, `tasks/lessons.md`, current development status/progress docs and required P5 evidence/Agent docs, including `docs/agent-tool-security.md`.
- [x] Confirm actual git state with `git status --short --branch` and `git log -8 --oneline`.
- [x] Write SAL-P5-015 implementation plan in `docs/superpowers/plans/2026-07-29-trusted-research-report-renderer.md`.
- [x] Add failing renderer contract tests and architecture guard.
- [x] Run focused Red test and record the expected missing-module failure.
- [x] Implement `evidence.report_renderer` as a pure offline renderer that consumes structured reports and citation validation results only.
- [x] Run focused Green test.
- [x] Update SAL-P5-015 evidence doc, progress checklist, development status and review notes.
- [x] Run related P5 renderer suite, full pytest, compileall, dependency lock, immutable tag and diff hygiene checks.
- [x] Create Chinese checkpoint commit for `SAL-P5-015`.

## Recovery Anchors

- Phase: P5 证据化 Agent、报告与成本治理.
- Gate: G4 已通过；G5 未通过.
- Completed after task: `SAL-P5-001..015`.
- Current READY task after commit: `SAL-P5-016` 引用 UI 与通知 Outbox.
- Implementation checkpoint: `a816cf72 feat(P5): 实现可信 ResearchReport Renderer`.
- Implementation checkpoint entering task: `1840f173 feat(P5): 实现 Agent 工具安全`.
- Status-sync checkpoint after task: `f9e9c961 docs: 同步 SAL-P5-015 checkpoint hash`.
- Status-sync hash-anchor after task: `65a0e446 docs: 记录 SAL-P5-015 状态同步 hash`.
- Status-review checkpoint after user reminder: `124f69a7 docs: 复核 SAL-P5-015 最新开发状态与恢复提示`.
- Status-review hash-anchor after user reminder: this `docs: 记录 SAL-P5-015 状态复核 hash` commit; confirm hash with `git log -1 --oneline` after commit.
- Latest status-sync checkpoint entering task: `57c6eb6d docs: 同步 SAL-P5-014 checkpoint hash`.
- Latest status-sync hash-anchor entering task: `488f2955 docs: 记录 SAL-P5-014 状态同步 hash`.
- Previous implementation checkpoint: `dfd82553 feat(P5): 实现 Citation Validator`.
- Strict next-task boundary after completion: `SAL-P5-016` 引用 UI 与通知 Outbox; do not start it in this task.

## Implementation Notes

- Target module: `src/serenity_alpha_lab/evidence/report_renderer.py`.
- Target tests: `tests/evidence/test_report_renderer.py` and `tests/architecture/test_architecture_boundaries.py`.
- Expected contract: `research.report_renderer@1.0.0`.
- Trusted input: `ResearchReport` plus optional `CitationValidationResult`.
- Authoritative output: canonical JSON envelope with `authority=canonical_json`; Markdown/HTML must be derived and must not be parsed back as source data.
- Display requirements: report level, as-of/decision time, Dataset versions, model metadata, cost, risk summary, disclaimer, claims, citations, evidence lineage and validation issues.
- Allowed dependencies: Python standard library, `serenity_alpha_lab.evidence.schema`, and `serenity_alpha_lab.evidence.citation_validator`; no Provider/LLM/Worker/Qlib/DSA runtime/UI/notification imports.

## Review

- Red: `uv run --extra core --extra dev python -m pytest tests/evidence/test_report_renderer.py -q` initially failed during collection with `ModuleNotFoundError: No module named 'serenity_alpha_lab.evidence.report_renderer'`.
- Green focused: `uv run --extra core --extra dev python -m pytest tests/evidence/test_report_renderer.py -q` -> `4 passed`.
- Architecture guard: `uv run --extra core --extra dev python -m pytest tests/architecture/test_architecture_boundaries.py::test_report_renderer_stays_offline_and_runtime_free -q` -> `1 passed`.
- Related P5 renderer suite: `uv run --extra core --extra dev python -m pytest tests/evidence/test_report_renderer.py tests/evidence/test_citation_validator.py tests/evidence/test_evidence_schema_contract.py tests/evidence/test_quant_evidence_adapter.py tests/application/test_technical_agent_evidence_adapter.py tests/application/test_intel_agent_evidence_adapter.py tests/application/test_risk_portfolio_agent_evidence_adapter.py tests/application/test_decision_agent_counterargument_synthesis.py tests/application/test_model_routing_cache_budget.py tests/application/test_agent_tool_security.py tests/architecture/test_architecture_boundaries.py -q` -> `73 passed`.
- Full suite: `uv run --extra core --extra dev python -m pytest -q` -> `484 passed, 3 skipped`.
- Compile: `uv run --extra core --extra dev python -m compileall -q src/serenity_alpha_lab tests` -> PASS.
- Dependency lock: `scripts/verify-python-dependency-lock.sh` -> PASS, `Resolved 298 packages`.
- Immutable upstream tag: `git rev-parse upstream/dsa-v3.26.1` -> `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`.
- Diff hygiene: `git diff --check` -> PASS.
- Subagent dispatch note: implementation/code-review subagent attempts were stopped after repeated wrapper schema errors; local review plus fresh verification was used instead, and no UI/notification, Agent evaluation or P5 follow-on work was started.
- Status review: user requested another latest-state sync and reusable startup prompt after `65a0e446`; updated docs/status/checklist/todo/lessons and preserved `SAL-P5-016` as the only next task.
