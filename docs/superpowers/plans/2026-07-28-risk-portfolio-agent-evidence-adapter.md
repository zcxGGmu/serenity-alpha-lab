# Risk/Portfolio Agent Evidence Adapter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete `SAL-P5-010` by adding an offline Risk/Portfolio Agent adapter that consumes deterministic formal backtest/risk evidence, preserves hard gates, validates cited structured output, and emits DSA-compatible risk/portfolio fields.

**Architecture:** Reuse the SAL-P5-008/009 role adapter pattern. A request binds a risk_portfolio `EvidenceBundle` to a concrete `PromptRunBinding`; prompt payload construction records allowed formal evidence and hard-gate metadata; finalization validates already-produced output without executing models or quant runtime. The adapter never imports quant modules, repositories, services, DSA runtime, Provider SDKs, LiteLLM, Qlib, FastAPI or SQLAlchemy.

**Tech Stack:** Python dataclasses, existing P5 `EvidenceBundle`, `PromptRunBinding`, `EvidenceRecord`, `ResearchClaim`, `ReportCitation`, pytest and architecture import guards.

---

### Task 1: Red Contract Tests

**Files:**
- Create: `tests/application/test_risk_portfolio_agent_evidence_adapter.py`

- [ ] **Step 1: Write failing tests**

Add tests that import `EvidenceScopedRiskPortfolioAgent`, `RiskPortfolioAgentPromptRequest`, `RiskPortfolioStructuredOutput`, `RiskPortfolioAgentError`, `RiskPortfolioGateStatus` and `RiskPortfolioAction` from `serenity_alpha_lab.application.risk_portfolio_agent`.

Cover:
- `prepare_prompt_payload()` accepts a risk_portfolio `EvidenceBundle` and prompt binding, exposes allowed evidence ids and hard gate status, and includes forbidden override/runtime actions.
- `prepare_prompt_payload()` rejects Screen/Factor/Intel evidence and formal evidence that allows LLM recompute.
- `finalize_output()` rejects output that upgrades `block` or `not_evaluable` hard gates.
- `finalize_output()` validates current-bundle citations and numeric deterministic citation consistency.
- Result mapping returns legacy DSA-compatible risk/portfolio opinion and dashboard fields without invoking DSA runtime.

- [ ] **Step 2: Run Red target**

Run:

```bash
uv run --extra core --extra dev python -m pytest tests/application/test_risk_portfolio_agent_evidence_adapter.py -q
```

Expected: fail with missing `serenity_alpha_lab.application.risk_portfolio_agent`.

### Task 2: Implement Offline Risk/Portfolio Adapter

**Files:**
- Create: `src/serenity_alpha_lab/application/risk_portfolio_agent.py`

- [ ] **Step 1: Add public contract types**

Implement:
- `RISK_PORTFOLIO_AGENT_CONTRACT_VERSION = "research.agent.risk_portfolio@1.0.0"`
- `RiskPortfolioAgentError`
- `RiskPortfolioGateStatus` with `pass`, `warn`, `block`, `not_evaluable`
- `RiskPortfolioAction` with `eligible`, `watchlist`, `reduce`, `avoid`, `insufficient_evidence`
- `RiskPortfolioAgentPromptRequest`
- `RiskPortfolioAgentPromptPayload`
- `RiskPortfolioStructuredOutput`
- `RiskPortfolioAgentResult`
- `EvidenceScopedRiskPortfolioAgent`

- [ ] **Step 2: Implement prompt payload validation**

`prepare_prompt_payload()` must require:
- `bundle.request.role == EvidenceBundleRole.RISK_PORTFOLIO`
- `prompt_binding.request.role == AgentPromptRole.RISK_PORTFOLIO`
- run/stage context match the request
- included evidence kind and scope match the Risk/Portfolio allowlist
- every accepted evidence has `metadata.llm_recompute_allowed=false`
- hard-gate summary preserves risk status, audit status, ranking eligibility, strong conclusion permission and not-evaluable rule ids

- [ ] **Step 3: Implement structured output validation**

`finalize_output()` must require:
- output gate status and portfolio action are typed
- output cannot upgrade prompt hard gate status (`block` or `not_evaluable`)
- every citation references an included evidence id
- citation dataset/run/stage/artifact lineage matches the cited evidence
- numeric claims use `ClaimComputationPolicy.DETERMINISTIC_EVIDENCE`
- numeric claim value/unit/formula/dataset/run/artifact match the deterministic citation
- risk gate claims are cited and cannot claim a less severe gate than the prompt payload

- [ ] **Step 4: Implement DSA compatibility mapping**

`RiskPortfolioAgentResult.to_dsa_compatible_opinion()` should return `agent_name`, `signal`, `risk_status`, `portfolio_action`, `confidence`, `reasoning` and `raw_data`.

`RiskPortfolioAgentResult.to_dsa_dashboard_fields()` should return `risk_analysis`, `portfolio_analysis`, `risk_status`, `portfolio_action`, `hard_gates`, `risk_factors`, `portfolio_constraints`, `warnings`, `limitations` and `citations`.

### Task 3: Exports And Architecture Guard

**Files:**
- Modify: `src/serenity_alpha_lab/application/__init__.py`
- Modify: `tests/architecture/test_architecture_boundaries.py`

- [ ] **Step 1: Export symbols**

Expose public constants, request/payload/output/result classes, enums, error and adapter from the application package.

- [ ] **Step 2: Add architecture test**

Add `test_risk_portfolio_agent_adapter_stays_offline_and_runtime_free()` allowing only standard library plus:
- `serenity_alpha_lab.application.evidence_bundle_builder`
- `serenity_alpha_lab.evidence.prompt_registry`
- `serenity_alpha_lab.evidence.schema`

Reject `serenity_alpha_lab.quant`, repositories, services, integrations, DSA agent runtime, Provider SDKs, LiteLLM, Qlib, FastAPI and SQLAlchemy imports.

### Task 4: Documentation And Status

**Files:**
- Create: `docs/risk-portfolio-agent-evidence-adapter.md`
- Modify: `docs/development-progress-checklist.md`
- Modify: `docs/development-status.md`
- Modify: `tasks/todo.md`

- [ ] **Step 1: Add evidence doc**

Document the contract, evidence allowlist, hard gate preservation, prompt payload rules, structured output rules, DSA compatibility mapping, non-goals and verification results.

- [ ] **Step 2: Update progress checklist**

Mark only `SAL-P5-010` as `DONE`, update P5 to `10/18`, total to `98/129`, add decision/evidence rows for Risk/Portfolio Agent, and set `SAL-P5-011` as next TODO/READY only after this task completes.

- [ ] **Step 3: Update status snapshot**

Update current task, completion range, checkpoint placeholders and next startup prompt to point to `SAL-P5-011`; keep G5 as not passed and preserve all strict non-goals.

### Task 5: Verification And Commit

**Files:**
- Verify all changed files.

- [ ] **Step 1: Run focused test**

```bash
uv run --extra core --extra dev python -m pytest tests/application/test_risk_portfolio_agent_evidence_adapter.py -q
```

- [ ] **Step 2: Run related suite**

```bash
uv run --extra core --extra dev python -m pytest tests/application/test_risk_portfolio_agent_evidence_adapter.py tests/application/test_evidence_bundle_builder.py tests/evidence/test_quant_evidence_adapter.py tests/evidence/test_prompt_schema_registry.py tests/repositories/test_agent_stage_store.py tests/architecture/test_architecture_boundaries.py -q
```

- [ ] **Step 3: Run full verification**

```bash
uv run --extra core --extra dev python -m pytest -q
uv run --extra core --extra dev python -m compileall -q src/serenity_alpha_lab tests
scripts/verify-python-dependency-lock.sh
git rev-parse upstream/dsa-v3.26.1
git diff --check
```

- [ ] **Step 4: Commit**

Stage only SAL-P5-010 files and commit:

```bash
git commit -m "feat(P5): 改造 Risk Portfolio Agent"
```

Commit body must mention completed content, compatibility/risk handling, verification and `SAL-P5-010, Gate G5`.
