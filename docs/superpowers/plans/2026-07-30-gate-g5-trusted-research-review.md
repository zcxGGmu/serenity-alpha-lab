# Gate G5 Trusted Research Review Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete `SAL-P5-018` by adding the Gate G5 review record, executable gate test and project status updates that approve the offline trusted research chain for RC input.

**Architecture:** Gate G5 is a review and evidence task, not a new runtime capability. The gate test combines document assertions with compact executable checks over existing P5 contracts: citation validation, trusted report rendering, report delivery UI payloads, Agent golden scoring, model cache/budget planning and tool-security denial. Documentation advances P5 to `18/18`, marks Gate G5 as `GO with accepted risks`, and makes `SAL-P6-001` the next allowed entry while preserving the real Provider/LLM, Worker-loop, Qlib runtime, production scheduling and formal-backtest promotion guards.

**Tech Stack:** Python 3.11, pytest, existing `serenity_alpha_lab` P5 modules, Markdown evidence docs, Git checkpoint workflow.

---

### Task 1: Gate G5 Red Test

**Files:**
- Create: `tests/gates/test_gate_g5_trusted_research_review.py`
- Read: `tests/gates/test_gate_g4_backtest_risk_review.py`
- Read: `tests/application/test_agent_golden_regression_evaluation.py`
- Read: `tests/evidence/test_report_renderer.py`
- Read: `tests/application/test_report_delivery_ui.py`
- Read: `tests/application/test_model_routing_cache_budget.py`
- Read: `tests/application/test_agent_tool_security.py`

- [x] **Step 1: Write the failing document test**

```python
def test_gate_g5_review_document_approves_trusted_research_for_rc_without_runtime_scope() -> None:
    text = Path("docs/gate-g5-trusted-research-review.md").read_text(encoding="utf-8")
    assert "GO with accepted risks" in text
    assert "APPROVED FOR P6 RC HARDENING INPUT ONLY" in text
```

- [x] **Step 2: Add executable trusted-report and evaluation checks**

```python
def test_gate_g5_executable_contract_links_report_evaluation_budget_security_and_boundaries() -> None:
    rendered = TrustedResearchReportRenderer().render(_verified_report(), context=_context())
    page = ResearchReportPagePresenter().build(rendered)
    assert page.to_record()["authority"] == "canonical_json"
```

- [x] **Step 3: Run test to verify Red**

Run:

```bash
uv run --extra core --extra dev python -m pytest tests/gates/test_gate_g5_trusted_research_review.py -q
```

Expected: FAIL with `FileNotFoundError` for `docs/gate-g5-trusted-research-review.md`; executable checks should not require real Provider/LLM, Worker loop, Qlib runtime, sender or scheduler.

### Task 2: Gate G5 Review Document

**Files:**
- Create: `docs/gate-g5-trusted-research-review.md`
- Read: `docs/gate-g4-backtest-risk-review.md`
- Read: `docs/evidence-claim-report-schema.md`
- Read: `docs/evidence-store.md`
- Read: `docs/evidence-bundle-builder.md`
- Read: `docs/source-trust-unstructured-cleaning.md`
- Read: `docs/quant-evidence-adapter.md`
- Read: `docs/prompt-output-schema-registry.md`
- Read: `docs/agent-stage-persistence.md`
- Read: `docs/technical-agent-evidence-adapter.md`
- Read: `docs/intel-agent-evidence-adapter.md`
- Read: `docs/risk-portfolio-agent-evidence-adapter.md`
- Read: `docs/decision-agent-counterargument-synthesis.md`
- Read: `docs/model-routing-cache-budget.md`
- Read: `docs/citation-validator.md`
- Read: `docs/agent-tool-security.md`
- Read: `docs/trusted-research-report-renderer.md`
- Read: `docs/research-report-delivery-ui-outbox.md`
- Read: `docs/agent-golden-regression-evaluation.md`

- [x] **Step 1: Write Gate conclusion**

Include:
- `任务：SAL-P5-018`
- `评审结论：GO with accepted risks`
- P5 completion `18/18`
- Project total `106/129`
- Approval limited to `APPROVED FOR P6 RC HARDENING INPUT ONLY`
- Statement that trusted research may enter RC hardening, not production runtime.

- [x] **Step 2: Write pass-condition matrix**

Cover:
- Evidence/Claim/Report schema, Evidence Store, EvidenceBundle and source trust.
- Quant Evidence Adapter and no LLM recomputation of deterministic facts.
- Prompt/schema registry, Agent Stage persistence and model cache/budget planning.
- Technical, Intel, Risk/Portfolio and Decision adapters with citation and hard-gate preservation.
- Citation Validator, Agent Tool Security, trusted renderer, delivery UI, Outbox and Agent golden evaluation.

- [x] **Step 3: Write accepted risks and P6 constraints**

State that real Provider/LLM calls, Agent execution, Worker loop, Qlib runtime execution, sender runtime, production scheduling, formal portfolio backtest promotion and investment-advice claims remain blocked until later explicit P6 tasks and profile guards.

- [x] **Step 4: Run target test to verify Green**

Run:

```bash
uv run --extra core --extra dev python -m pytest tests/gates/test_gate_g5_trusted_research_review.py -q
```

Expected: PASS.

### Task 3: Status And Progress Sync

**Files:**
- Modify: `docs/development-progress-checklist.md`
- Modify: `docs/development-status.md`
- Modify: `tasks/todo.md`

- [x] **Step 1: Update task status**

Mark `SAL-P5-018` as `[DONE]`, set actual effort/date, add result/scope/evidence lines and make `SAL-P6-001` the next `READY` task.

- [x] **Step 2: Add decision/evidence rows**

Add:
- `DEC-104` for Gate G5 trusted research review.
- `AEV-106` for Gate G5 executable test and evidence record.

- [x] **Step 3: Update status snapshot**

Set Gate G5 passed with accepted risks, P5 `18/18`, total `106/129`, recent task `SAL-P5-018`, next task `SAL-P6-001`, and update the next startup prompt.

- [x] **Step 4: Update task review**

Record Red/Green evidence, focused/related/full validation commands, checkpoint placeholders and strict boundary preservation.

### Task 4: Verification And Commit

**Files:**
- Verify: `tests/gates/test_gate_g5_trusted_research_review.py`
- Verify: P5 related tests
- Verify: status docs

- [x] **Step 1: Run focused and related tests**

Run:

```bash
uv run --extra core --extra dev python -m pytest tests/gates/test_gate_g5_trusted_research_review.py -q
uv run --extra core --extra dev python -m pytest \
  tests/gates/test_gate_g5_trusted_research_review.py \
  tests/application/test_agent_golden_regression_evaluation.py \
  tests/application/test_technical_agent_evidence_adapter.py \
  tests/application/test_intel_agent_evidence_adapter.py \
  tests/application/test_risk_portfolio_agent_evidence_adapter.py \
  tests/application/test_decision_agent_counterargument_synthesis.py \
  tests/application/test_model_routing_cache_budget.py \
  tests/application/test_agent_tool_security.py \
  tests/evidence/test_citation_validator.py \
  tests/evidence/test_report_renderer.py \
  tests/application/test_report_delivery_ui.py \
  tests/repositories/test_notification_outbox.py \
  tests/architecture/test_architecture_boundaries.py -q
```

- [x] **Step 2: Run full validation**

Run:

```bash
uv run --extra core --extra dev python -m pytest -q
uv run --extra core --extra dev python -m compileall -q src/serenity_alpha_lab tests
scripts/verify-python-dependency-lock.sh
scripts/apply-dsa-baseline-patches.sh --check-only
git rev-parse upstream/dsa-v3.26.1
git diff --check
```

- [x] **Step 3: Commit**

Stage only `SAL-P5-018` files and commit:

```bash
git commit -m "docs(P5): 通过 Gate G5 可信研究评审"
```

Commit body must mention completed content, compatibility/risk handling, verification and associated task `SAL-P5-018, Gate G5`.
