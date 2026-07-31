# Technical Agent Evidence Adapter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Complete `SAL-P5-008` by adding an offline Technical Agent adapter that consumes only technical/screen/factor EvidenceBundle records and emits cited, DSA-compatible technical output.

**Architecture:** Add a narrow `application.technical_agent` module that sits between existing P5 EvidenceBundle/Prompt Registry and later model execution. It prepares deterministic prompt payload metadata, validates structured output against current bundle citations, and maps the result into legacy DSA Technical Agent dashboard fields without importing or executing DSA Agent runtime.

**Tech Stack:** Python dataclasses, existing P5 `EvidenceBundle`, `PromptRunBinding`, `ResearchClaim`, `ReportCitation`, and architecture AST guards.

---

### Task 1: Red Technical Agent Adapter Tests

**Files:**
- Create: `tests/application/test_technical_agent_evidence_adapter.py`

- [x] **Step 1: Write failing tests**

Add tests that import `EvidenceScopedTechnicalAgent`, `TechnicalAgentPromptRequest`, `TechnicalAgentStructuredOutput`, `TechnicalAgentError`, `TechnicalSignal`, `TechnicalTrendAlignment` and `TechnicalVolumeStatus` from `serenity_alpha_lab.application.technical_agent`.

Cover:
- `prepare_prompt_payload()` accepts a technical `EvidenceBundle` and technical `PromptRunBinding`, returns prompt/bundle metadata, allowed evidence ids and no DSA tool names.
- `prepare_prompt_payload()` rejects formal portfolio backtest evidence for Technical Agent.
- `finalize_output()` requires numeric claims to cite citations whose evidence ids exist in the bundle.
- `finalize_output()` maps structured output to DSA-compatible opinion and dashboard fields.

- [x] **Step 2: Run Red target**

Run:

```bash
uv run --extra core --extra dev python -m pytest tests/application/test_technical_agent_evidence_adapter.py -q
```

Expected: fail with missing `serenity_alpha_lab.application.technical_agent`.

### Task 2: Implement Offline Technical Agent Adapter

**Files:**
- Create: `src/serenity_alpha_lab/application/technical_agent.py`

- [x] **Step 1: Add public contract types**

Implement:
- `TECHNICAL_AGENT_CONTRACT_VERSION = "research.agent.technical@1.0.0"`
- `TechnicalAgentError`
- `TechnicalSignal`
- `TechnicalTrendAlignment`
- `TechnicalVolumeStatus`
- `TechnicalAgentPromptRequest`
- `TechnicalAgentPromptPayload`
- `TechnicalAgentStructuredOutput`
- `TechnicalAgentResult`
- `EvidenceScopedTechnicalAgent`

- [x] **Step 2: Implement prompt payload validation**

`prepare_prompt_payload()` must require:
- `bundle.request.role == EvidenceBundleRole.TECHNICAL`
- `prompt_binding.request.role == AgentPromptRole.TECHNICAL`
- `prompt_binding.request.run_id/stage_id` match the request
- every included evidence kind is one of `SCREEN_SNAPSHOT`, `SCREEN_PIPELINE_SNAPSHOT`, `FACTOR_EVALUATION`, `FACTOR_CACHE_MANIFEST`

The returned payload should include bundle prompt payload, prompt binding record, allowed evidence ids, allowed evidence hashes, forbidden action labels and a deterministic payload hash.

- [x] **Step 3: Implement structured output validation**

`finalize_output()` must require:
- output signal/confidence/trend score/key levels are typed and bounded
- every output citation references an evidence id from the prompt payload
- every numeric claim uses `ClaimComputationPolicy.DETERMINISTIC_EVIDENCE`
- every numeric claim citation id exists in output citations

- [x] **Step 4: Implement DSA compatibility mapping**

`TechnicalAgentResult.to_dsa_compatible_opinion()` should return:
- `agent_name`, `signal`, `confidence`, `reasoning`, `key_levels`, `raw_data`

`TechnicalAgentResult.to_dsa_dashboard_fields()` should return:
- `technical_analysis`, `trend_analysis`, `ma_analysis`, `volume_analysis`, `pattern_analysis`, `key_levels`, `trend_status`, `volume_status`

### Task 3: Exports And Architecture Guard

**Files:**
- Modify: `src/serenity_alpha_lab/application/__init__.py`
- Modify: `tests/architecture/test_architecture_boundaries.py`

- [x] **Step 1: Export symbols**

Import and add `__all__` entries for the new Technical Agent public types.

- [x] **Step 2: Add architecture test**

Add `test_technical_agent_adapter_stays_offline_and_runtime_free()` allowing only standard library plus:
- `serenity_alpha_lab.application.evidence_bundle_builder`
- `serenity_alpha_lab.evidence.prompt_registry`
- `serenity_alpha_lab.evidence.schema`

Reject concrete `src.agent`, Provider SDKs, `litellm`, `qlib`, `fastapi`, `sqlalchemy`, services, integrations and report renderer imports.

### Task 4: Documentation And Status

**Files:**
- Create: `docs/technical-agent-evidence-adapter.md`
- Modify: `docs/development-progress-checklist.md`
- Modify: `docs/development-status.md`

- [x] **Step 1: Add evidence doc**

Document contract, evidence allowlist, prompt payload, structured output rules, DSA compatibility mapping, non-goals and verification results.

- [x] **Step 2: Update progress checklist**

Mark only `SAL-P5-008` as `DONE`, update P5 to `8/18`, total to `96/129`, add `DEC-094` and `AEV-096`, and set `SAL-P5-009` as next `READY`.

- [x] **Step 3: Update status snapshot**

Update current task, completion range, checkpoint placeholders and next startup prompt to point to `SAL-P5-009`; keep G5 as not passed and preserve all strict non-goals.

### Task 5: Verification And Commit

**Files:**
- Verify all changed files.

- [x] **Step 1: Run focused test**

```bash
uv run --extra core --extra dev python -m pytest tests/application/test_technical_agent_evidence_adapter.py -q
```

- [x] **Step 2: Run related suite**

```bash
uv run --extra core --extra dev python -m pytest tests/application/test_technical_agent_evidence_adapter.py tests/application/test_evidence_bundle_builder.py tests/evidence/test_quant_evidence_adapter.py tests/evidence/test_prompt_schema_registry.py tests/repositories/test_agent_stage_store.py tests/architecture/test_architecture_boundaries.py -q
```

- [x] **Step 3: Run full verification**

```bash
uv run --extra core --extra dev python -m pytest -q
uv run --extra core --extra dev python -m compileall -q src/serenity_alpha_lab tests
scripts/verify-python-dependency-lock.sh
git rev-parse upstream/dsa-v3.26.1
git diff --check
```

- [x] **Step 4: Commit**

Stage only SAL-P5-008 files and commit:

```bash
git commit -m "feat(P5): 改造 Technical Agent"
```

Commit body must mention completed content, compatibility/risk handling, verification and `SAL-P5-008, Gate G5`.
