# SAL-P5-011 Decision Counterargument / Final Synthesis Implementation Plan

> Scope: Complete only `SAL-P5-011` by adding an offline Decision synthesis adapter over already-produced Technical, Intel and Risk/Portfolio adapter outputs. Do not jump to Model routing, Citation Validator, report rendering or later P5 tasks. Do not start real Provider/LLM calls, Worker loops, Qlib runtime, production scheduling, report generation or formal backtest promotion.

## Checklist

- [x] Re-read required project docs and confirm `git status --short --branch` / `git log -8 --oneline`.
- [x] Create `docs/superpowers/plans/2026-07-28-decision-counterargument-synthesis.md`.
- [x] Write Red tests in `tests/application/test_decision_agent_counterargument_synthesis.py`.
- [x] Run Red focused test and confirm failure for missing `serenity_alpha_lab.application.decision_agent`.
- [x] Implement `src/serenity_alpha_lab/application/decision_agent.py` as an offline Decision synthesis adapter over prior role results and a decision `EvidenceBundle` / `PromptRunBinding`.
- [x] Export public symbols from `src/serenity_alpha_lab/application/__init__.py`.
- [x] Add architecture guard proving the Decision adapter stays runtime-free and offline.
- [x] Add `docs/decision-agent-counterargument-synthesis.md`.
- [x] Run focused, related and full verification.
- [x] Update `docs/development-progress-checklist.md`, `docs/development-status.md`, evidence/risk/decision records, this review section and next startup prompt.
- [x] Create Chinese checkpoint commit for `SAL-P5-011`: `50e6aa39 feat(P5): 实现多空反证与最终综合`.

## Current State

- Phase: P5 证据化 Agent、报告与成本治理.
- Gate: G4 passed; G5 not passed.
- Completed: `SAL-P5-001..011`.
- Current READY task after checkpoint: `SAL-P5-012` 模型路由、缓存与预算.
- Implementation checkpoint: `50e6aa39 feat(P5): 实现多空反证与最终综合`.
- Status-sync checkpoint: `e9e5ad69 docs: 同步 SAL-P5-011 checkpoint hash`.
- Previous implementation checkpoint: `22ecff19 feat(P5): 改造 Risk Portfolio Agent`.

## Implementation Notes

- Reuse the `technical_agent.py`, `intel_agent.py` and `risk_portfolio_agent.py` pattern: prepare a deterministic prompt payload, validate caller-provided structured output, then map to DSA-compatible final decision fields.
- Decision input should consume prior role results, not repeat raw analyst summaries. Bull/bear cases must cite current-bundle evidence through prior role result citations and include distinct supporting and opposing factors.
- Final Decision must not introduce facts that are absent from prior role outputs or the current Decision EvidenceBundle citation graph.
- Preserve hard gates from Risk/Portfolio: `block`, `not_evaluable`, `agent_strong_conclusion_allowed=false` and ranking ineligibility cannot be upgraded by the final decision.
- Numeric claims remain deterministic evidence only; qualitative synthesis may use citation summaries but cannot recompute returns, risk, drawdown, costs, orders, ledger state or source trust labels.

## Planned Verification

- Red target: `uv run --extra core --extra dev python -m pytest tests/application/test_decision_agent_counterargument_synthesis.py -q`.
- Focused target after implementation: same command should pass.
- Architecture guard: Decision adapter imports only offline application/evidence/schema modules and Python stdlib.
- Related suite: Decision + Technical + Intel + Risk/Portfolio + EvidenceBundle + PromptRegistry + AgentStageStore + architecture tests.
- Full suite: `uv run --extra core --extra dev python -m pytest -q`, compileall, dependency lock, immutable upstream tag, `git diff --check`.

## Review

- Red: `uv run --extra core --extra dev python -m pytest tests/application/test_decision_agent_counterargument_synthesis.py -q` failed during collection with `ModuleNotFoundError: No module named 'serenity_alpha_lab.application.decision_agent'`.
- Green focused: `uv run --extra core --extra dev python -m pytest tests/application/test_decision_agent_counterargument_synthesis.py -q` -> `4 passed`.
- Architecture guard: `uv run --extra core --extra dev python -m pytest tests/architecture/test_architecture_boundaries.py::test_decision_agent_adapter_stays_offline_and_runtime_free -q` -> `1 passed`.
- Related suite: Decision/Technical/Intel/RiskPortfolio/EvidenceBundle/PromptRegistry/AgentStageStore/Architecture `54 passed`.
- Full verification: `uv run --extra core --extra dev python -m pytest -q` -> `461 passed, 3 skipped`; compileall PASS; dependency lock PASS (`Resolved 298 packages` twice during lock guard); immutable upstream tag remained `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`; `git diff --check` PASS before final todo/status touch and will be rerun before commit.
- Scope review: no real Provider/LLM, Worker loop, Qlib runtime, production scheduling, model routing/cache/budget, Citation Validator, report rendering or formal backtest promotion was started.
- Subagent review note: code-review subagent dispatch was attempted twice but rejected by the tool wrapper on empty optional argument serialization (`reasoning_effort must not be empty` after the historical empty `message/items` issue); per `tasks/lessons.md` fallback rule, proceeding with local senior diff review plus fresh verification.
