# SAL-P5-014 Agent Tool Security Implementation Plan

> Scope: Complete only `SAL-P5-014` by adding an offline Agent tool authorization boundary for default-deny tool access, runtime parameter schema validation, SSRF/URL host restrictions and prompt-injection rejection. Do not jump to report rendering or later P5 tasks. Do not start real Provider/LLM calls, Worker loops, Qlib runtime, production scheduling, report generation or formal backtest promotion.

## Checklist

- [x] Re-read `AGENTS.md`, `tasks/lessons.md`, current development status/progress docs and required P5 evidence/Agent docs.
- [x] Confirm actual git state with `git status --short --branch` and `git log -8 --oneline`.
- [x] Write SAL-P5-014 implementation plan in `docs/superpowers/plans/2026-07-28-agent-tool-security.md`.
- [x] Add failing contract tests and architecture guard for Agent tool security.
- [x] Run focused Red test and record the expected missing-module failure.
- [x] Implement `application.agent_tool_security` as a pure offline guard with no tool execution.
- [x] Run focused Green test.
- [x] Update SAL-P5-014 evidence doc, progress checklist, development status and review notes.
- [x] Run related P5/security suite, full pytest, compileall, dependency lock, immutable tag and diff hygiene checks.
- [x] Create Chinese checkpoint commit for `SAL-P5-014`.

## Recovery Anchors

- Phase: P5 证据化 Agent、报告与成本治理.
- Gate: G4 已通过；G5 未通过.
- Completed after task: `SAL-P5-001..014`.
- Current READY task: `SAL-P5-015` 可信 ResearchReport 与 Renderer.
- Implementation checkpoint: `1840f173 feat(P5): 实现 Agent 工具安全`.
- Previous implementation checkpoint: `dfd82553 feat(P5): 实现 Citation Validator`.
- Latest status-sync checkpoint: `57c6eb6d docs: 同步 SAL-P5-014 checkpoint hash`.
- Latest status-sync hash-anchor: this `docs: 记录 SAL-P5-014 状态同步 hash` commit; confirm with `git log -1 --oneline` after commit.
- Latest final anchor entering task: `84424467 docs: 记录 SAL-P5-013 最终锚点`.
- Latest status review checkpoint entering task: `acceebab docs: 复核 SAL-P5-013 最新开发状态与恢复提示`.
- Latest status review hash-anchor entering task: `31a0dabe docs: 记录 SAL-P5-013 状态复核 hash`.
- Latest status review solidification checkpoint entering task: `1a0dd32a docs: 固化 SAL-P5-013 状态复核 hash-anchor`.

## Implementation Notes

- Target module: `src/serenity_alpha_lab/application/agent_tool_security.py`.
- Target tests: `tests/application/test_agent_tool_security.py` and `tests/architecture/test_architecture_boundaries.py`.
- Expected contract: `research.agent_tool_security@1.0.0`.
- Allowed dependencies: Python standard library and `serenity_alpha_lab.evidence.prompt_registry`; no runtime Provider/LLM/Worker/Qlib/DSA Agent imports.
- Subagent dispatch note: read-only subagent exploration was attempted at task start, but wrapper payload validation repeatedly rejected `items`/`message` combinations. Per prior project lessons, retries stopped and local senior review continues with fresh verification.

## Review

- Red: `uv run --extra core --extra dev python -m pytest tests/application/test_agent_tool_security.py -q` failed during collection with `ModuleNotFoundError: No module named 'serenity_alpha_lab.application.agent_tool_security'`.
- Green focused: `uv run --extra core --extra dev python -m pytest tests/application/test_agent_tool_security.py -q` -> `4 passed`.
- Architecture guard: `uv run --extra core --extra dev python -m pytest tests/architecture/test_architecture_boundaries.py::test_agent_tool_security_stays_offline_and_runtime_free -q` -> `1 passed`.
- Related P5/security suite: `uv run --extra core --extra dev python -m pytest tests/application/test_agent_tool_security.py tests/evidence/test_prompt_schema_registry.py tests/evidence/test_source_trust_cleaning.py tests/application/test_model_routing_cache_budget.py tests/repositories/test_agent_stage_store.py tests/architecture/test_architecture_boundaries.py -q` -> `47 passed`.
- Full suite: `uv run --extra core --extra dev python -m pytest -q` -> `479 passed, 3 skipped`.
- Compile: `uv run --extra core --extra dev python -m compileall -q src/serenity_alpha_lab tests` -> PASS.
- Dependency lock: `scripts/verify-python-dependency-lock.sh` -> PASS, `Resolved 298 packages`.
- Immutable upstream tag: `git rev-parse upstream/dsa-v3.26.1` -> `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`.
- Diff hygiene: `git diff --check` -> PASS.
- Code-review subagent dispatch was attempted after implementation, but the tool wrapper kept submitting both `items` and `message`; retries stopped and local review plus fresh verification was used.
