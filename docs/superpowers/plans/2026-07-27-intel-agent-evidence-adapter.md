# Intel Agent Evidence Adapter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an offline Intel Agent adapter that consumes source-trust-backed EvidenceBundle records, validates structured cited event output, and emits DSA-compatible news/intel fields.

**Architecture:** Reuse the SAL-P5-008 role-agent adapter pattern: a request binds an Intel EvidenceBundle to a concrete PromptRunBinding, a prompt payload records allowed evidence/source trust metadata, and finalization validates already-produced structured output. Source Trust remains the only cleaning/trust boundary; the adapter never fetches web/news/social content or calls a model.

**Tech Stack:** Python dataclasses, Pydantic evidence schema, EvidenceBundle Builder, Prompt Registry, SourceTrust metadata, pytest architecture guards.

---

### Task 1: Red Contract Tests

**Files:**
- Create: `tests/application/test_intel_agent_evidence_adapter.py`

- [x] **Step 1: Write failing tests**

Add contract coverage for Intel prompt payload construction, source trust metadata exposure, duplicate/stale/malicious handling, low-trust strong-event rejection, unknown evidence rejection, and DSA-compatible output mapping.

- [x] **Step 2: Run test to verify failure**

Run: `uv run --extra core --extra dev python -m pytest tests/application/test_intel_agent_evidence_adapter.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'serenity_alpha_lab.application.intel_agent'`.

### Task 2: Offline Intel Adapter

**Files:**
- Create: `src/serenity_alpha_lab/application/intel_agent.py`
- Modify: `src/serenity_alpha_lab/evidence/schema.py`
- Modify: `src/serenity_alpha_lab/application/evidence_bundle_builder.py`

- [x] **Step 1: Add evidence enum/scope**

Add `EvidenceKind.UNSTRUCTURED_SOURCE` and `EvidenceEvaluationScope.MARKET_INTELLIGENCE` so source-trust-backed Intel evidence has a first-class P5 representation.

- [x] **Step 2: Implement prompt payload preparation**

Validate Intel bundle role, Intel prompt binding, run/stage match, source trust metadata, event/published/observed/available times, duplicate source hashes, staleness and malicious prompt-injection flags.

- [x] **Step 3: Implement structured output finalization**

Validate current-bundle citations, claim citation ids, event source evidence ids and strong-event trust requirements. Reject Intel `numeric_metric` claims so the role cannot invent metrics.

- [x] **Step 4: Add DSA compatibility mapping**

Return legacy-style `agent_name=intel`, `signal`, `sentiment_score`, `news_summary`, `key_events`, source quality counts and citation records.

### Task 3: Public Exports And Guards

**Files:**
- Modify: `src/serenity_alpha_lab/application/__init__.py`
- Modify: `tests/architecture/test_architecture_boundaries.py`

- [x] **Step 1: Export adapter symbols**

Expose public Intel constants, request/payload/output/result classes, enums, error and adapter from the application boundary.

- [x] **Step 2: Add architecture guard**

Lock `application/intel_agent.py` to offline application/evidence imports only; forbid concrete DSA Agent runtime, Provider/LLM, Worker, Qlib, FastAPI, SQLAlchemy, repositories and services imports.

### Task 4: Verification And Status Sync

**Files:**
- Create: `docs/intel-agent-evidence-adapter.md`
- Modify: `docs/development-progress-checklist.md`
- Modify: `docs/development-status.md`
- Modify: `tasks/todo.md`

- [ ] **Step 1: Run focused and related tests**

Run focused Intel, EvidenceBundle, SourceTrust, PromptRegistry, AgentStage and architecture suites. Record exact PASS counts in task evidence.

- [ ] **Step 2: Run full verification**

Run full pytest, compileall, dependency lock guard, immutable tag check and `git diff --check` before claiming completion.

- [ ] **Step 3: Sync status and commit**

Update status/checklist/evidence/decision/task review and create the required Chinese checkpoint commit for SAL-P5-009.
