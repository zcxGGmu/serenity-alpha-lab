# SAL-P5-010 Risk/Portfolio Agent Implementation Plan

> Scope: Complete only `SAL-P5-010` by adding an offline Risk/Portfolio Agent evidence adapter. Do not jump to Model routing, Citation Validator, report rendering or later P5 tasks. Do not start real Provider/LLM calls, Worker loops, Qlib runtime, production scheduling or formal backtest promotion.

## Checklist

- [x] Re-read required project docs and confirm `git status --short --branch` / `git log -8 --oneline`.
- [x] Create `docs/superpowers/plans/2026-07-28-risk-portfolio-agent-evidence-adapter.md`.
- [x] Write Red tests in `tests/application/test_risk_portfolio_agent_evidence_adapter.py`.
- [x] Run Red focused test and confirm failure for missing `serenity_alpha_lab.application.risk_portfolio_agent`.
- [x] Implement `src/serenity_alpha_lab/application/risk_portfolio_agent.py` as an offline adapter over `EvidenceBundle` and `PromptRunBinding`.
- [x] Export public symbols from `src/serenity_alpha_lab/application/__init__.py`.
- [x] Add architecture guard proving the adapter stays runtime-free and offline.
- [x] Add `docs/risk-portfolio-agent-evidence-adapter.md`.
- [x] Run focused, related and full verification.
- [x] Update `docs/development-progress-checklist.md`, `docs/development-status.md`, evidence/risk/decision records, this review section and next startup prompt.
- [ ] Create Chinese checkpoint commit for `SAL-P5-010`.

## Current State

- Phase: P5 证据化 Agent、报告与成本治理.
- Gate: G4 passed; G5 not passed.
- Completed: `SAL-P5-001..009`.
- Current READY task: `SAL-P5-010` Risk/Portfolio Agent 改造.
- Latest implementation checkpoint: `a6974362 feat(P5): 改造 Intel Agent`.
- Latest status sync/hash anchors: `7521d6d9`, `c2da5fe8`, `ec5208de`, `f18d1b6e`.

## Implementation Notes

- Reuse the `technical_agent.py` / `intel_agent.py` pattern: prepare a deterministic prompt payload, validate already-produced structured output, then map to DSA-compatible opinion/dashboard fields.
- Accept only formal portfolio backtest evidence kinds for this role: risk policy result, bias audit, performance metrics, backtest run summary, backtest artifact bundle and formal backtest API record.
- Require `metadata.llm_recompute_allowed=false`; reject Screen/Factor/Intel evidence and any evidence outside `formal_portfolio_backtest` or approved lineage scope.
- Preserve hard gates: risk `block`, audit `invalid`, `eligible_for_ranking=false`, `agent_strong_conclusion_allowed=false` and `not_evaluable` rule metadata cannot be upgraded by agent output.
- Validate citation graph and deterministic numeric claims; qualitative risk explanations may summarize cited evidence but may not recompute returns, risk, drawdown, costs, orders, ledger state or gate outcomes.

## Review

- Red: `uv run --extra core --extra dev python -m pytest tests/application/test_risk_portfolio_agent_evidence_adapter.py -q` failed with missing `serenity_alpha_lab.application.risk_portfolio_agent`.
- Green focused: Risk/Portfolio target `4 passed`; architecture guard `1 passed`.
- Related suite: RiskPortfolioAgent/EvidenceBundle/QuantEvidenceAdapter/PromptRegistry/AgentStageStore/Architecture `41 passed`.
- Full verification: pytest `456 passed, 3 skipped`; compileall PASS; dependency lock PASS (`Resolved 298 packages`); upstream tag remained `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`; `git diff --check` PASS.
- Scope review: no real Provider/LLM, Worker loop, Qlib runtime, production scheduling, report rendering, Citation Validator or formal backtest promotion was started.
- Commit: pending Chinese checkpoint commit and follow-up status hash sync.
