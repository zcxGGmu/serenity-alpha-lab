# Decision Counterargument Synthesis Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the offline `SAL-P5-011` Decision synthesis adapter that turns cited Technical, Intel and Risk/Portfolio role outputs into bull/bear counterarguments, disagreement summary, invalidation conditions and a final bounded decision.

**Architecture:** Add `application.decision_agent` as an offline boundary. It accepts prior role adapter results plus a decision `EvidenceBundle` and concrete `PromptRunBinding`, prepares a deterministic prompt payload, validates already-produced structured Decision output, preserves Risk/Portfolio hard gates, and emits DSA-compatible final decision fields. It does not execute models, tools, Evidence Store writes, Citation Validator, report rendering, Qlib, Worker loops or live providers.

**Tech Stack:** Python dataclasses, `StrEnum`, existing P5 `EvidenceBundle`, `PromptRunBinding`, `ResearchClaim`, `ReportCitation`, and existing role result DTOs.

---

### Task 1: Red Contract Tests

**Files:**
- Create: `tests/application/test_decision_agent_counterargument_synthesis.py`

- [ ] **Step 1: Write the failing tests**

Create tests that import `EvidenceScopedDecisionAgent`, `DecisionAgentPromptRequest`, `DecisionStructuredOutput`, `DecisionRecommendation`, `DecisionConfidenceLevel` and assert:

```python
def test_prepare_prompt_payload_combines_role_results_without_runtime_tools() -> None:
    payload = EvidenceScopedDecisionAgent().prepare_prompt_payload(
        DecisionAgentPromptRequest(
            run_id="run-decision",
            stage_id="stage-decision",
            bundle=_decision_bundle(),
            prompt_binding=_decision_binding(),
            technical_result=_technical_result(),
            intel_result=_intel_result(),
            risk_portfolio_result=_risk_portfolio_result(),
        )
    )
    record = payload.to_record()
    assert record["schema_name"] == "research.agent.decision_prompt_payload"
    assert record["prompt_binding"]["prompt"]["prompt_id"] == "decision_research"
    assert record["role_result_hashes"]["technical"].startswith("sha256:")
    assert "call_real_llm" in record["forbidden_actions"]
```

Also cover bull/bear distinctness, final decision citation graph, risk gate preservation, and DSA compatibility fields.

- [ ] **Step 2: Run Red test**

Run: `uv run --extra core --extra dev python -m pytest tests/application/test_decision_agent_counterargument_synthesis.py -q`

Expected: FAIL with `ModuleNotFoundError: No module named 'serenity_alpha_lab.application.decision_agent'`.

### Task 2: Decision Adapter

**Files:**
- Create: `src/serenity_alpha_lab/application/decision_agent.py`
- Modify: `src/serenity_alpha_lab/application/__init__.py`

- [ ] **Step 1: Implement public DTOs**

Add frozen dataclasses for request, prompt payload, structured output, bull/bear cases, disagreement summary, invalidation condition, result wrapper, plus typed enums for recommendation and confidence level.

- [ ] **Step 2: Implement prompt payload preparation**

Validate decision role bundle and prompt binding, require run/stage matches, require prior role results of the correct types, compute role result hashes from `to_record()`, collect prior citations, preserve Risk/Portfolio hard gate summary, and list forbidden runtime actions.

- [ ] **Step 3: Implement output validation**

Validate citations against the current decision bundle or prior role output citations; require at least one bull and one bear case; reject bull/bear cases that use identical factor text/citation sets; reject unknown facts/citations; reject final recommendations that upgrade `block` or `not_evaluable`; validate numeric claims as deterministic evidence with exact citation value/unit/formula/dataset/run/stage/artifact matches.

- [ ] **Step 4: Export symbols**

Update `src/serenity_alpha_lab/application/__init__.py` with Decision constants, adapter, request/payload/result/output classes and enums.

- [ ] **Step 5: Run focused Green test**

Run: `uv run --extra core --extra dev python -m pytest tests/application/test_decision_agent_counterargument_synthesis.py -q`

Expected: PASS.

### Task 3: Architecture Guard And Evidence Doc

**Files:**
- Modify: `tests/architecture/test_architecture_boundaries.py`
- Create: `docs/decision-agent-counterargument-synthesis.md`

- [ ] **Step 1: Add offline architecture test**

Add `test_decision_agent_adapter_stays_offline_and_runtime_free`, allowing only stdlib, `application.evidence_bundle_builder`, prior role adapters, `evidence.prompt_registry`, and `evidence.schema`.

- [ ] **Step 2: Add evidence doc**

Document contract `research.agent.decision@1.0.0`, prompt/output schemas, bull/bear/disagreement/final decision rules, hard-gate preservation, DSA compatibility mapping, non-goals and verification results.

- [ ] **Step 3: Run related suite**

Run: `uv run --extra core --extra dev python -m pytest tests/application/test_decision_agent_counterargument_synthesis.py tests/application/test_technical_agent_evidence_adapter.py tests/application/test_intel_agent_evidence_adapter.py tests/application/test_risk_portfolio_agent_evidence_adapter.py tests/application/test_evidence_bundle_builder.py tests/evidence/test_prompt_schema_registry.py tests/repositories/test_agent_stage_store.py tests/architecture/test_architecture_boundaries.py -q`

Expected: PASS.

### Task 4: Status Closeout

**Files:**
- Modify: `docs/development-progress-checklist.md`
- Modify: `docs/development-status.md`
- Modify: `tasks/todo.md`

- [ ] **Step 1: Run final verification**

Run full pytest, compileall, dependency lock, immutable upstream tag check, `git diff --check`, `git status --short --branch`.

- [ ] **Step 2: Update progress and status**

Mark only `SAL-P5-011` as `DONE`, update P5 to `11/18`, total to `99/129`, add decision/evidence records for the Decision synthesis adapter, and set `SAL-P5-012` as next task without starting it.

- [ ] **Step 3: Commit**

Create a Chinese checkpoint commit using the project template and include verification evidence and associated task `SAL-P5-011, Gate G5`.
