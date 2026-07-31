# Trusted ResearchReport Renderer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement `SAL-P5-015` trusted ResearchReport rendering with canonical JSON as the authority and Markdown/HTML as derived display formats.

**Architecture:** Add an offline `evidence.report_renderer` boundary that consumes existing `ResearchReport` objects and `CitationValidator` output. The renderer validates or accepts a caller-provided validation result, emits a canonical JSON envelope with deterministic hash, then renders Markdown/HTML from that envelope only.

**Tech Stack:** Python 3.11, dataclasses, Pydantic schema objects from `evidence.schema`, offline `CitationValidator`, pytest architecture guards.

---

## Files

- Create: `src/serenity_alpha_lab/evidence/report_renderer.py` for renderer contracts, canonical JSON envelope and Markdown/HTML rendering.
- Modify: `src/serenity_alpha_lab/evidence/__init__.py` to export renderer contracts.
- Create: `tests/evidence/test_report_renderer.py` for Red/Green contract coverage.
- Modify: `tests/architecture/test_architecture_boundaries.py` to keep renderer offline and runtime-free.
- Create: `docs/trusted-research-report-renderer.md` for evidence/approval record.
- Modify: `docs/development-progress-checklist.md`, `docs/development-status.md` and `tasks/todo.md` during closeout.

### Task 1: Red Contract Tests

**Files:**
- Create: `tests/evidence/test_report_renderer.py`
- Modify: `tests/architecture/test_architecture_boundaries.py`

- [ ] **Step 1: Write failing renderer tests**

```python
from serenity_alpha_lab.evidence.report_renderer import (
    ReportRendererError,
    ResearchReportRenderContext,
    TrustedResearchReportRenderer,
)
```

Assert that renderer output includes canonical JSON authority, deterministic hash, report level, as-of time, Dataset versions, model/cost/risk/disclaimer metadata, claim/citation/evidence lineage, and derived Markdown/HTML.

- [ ] **Step 2: Write architecture guard**

```python
def test_report_renderer_stays_offline_and_runtime_free() -> None:
    target = PACKAGE_ROOT / "evidence" / "report_renderer.py"
    ...
```

Allowed imports are standard library rendering/hash helpers plus `evidence.schema` and `evidence.citation_validator`.

- [ ] **Step 3: Run focused Red test**

Run: `uv run --extra core --extra dev python -m pytest tests/evidence/test_report_renderer.py -q`

Expected: FAIL during collection with `ModuleNotFoundError: No module named 'serenity_alpha_lab.evidence.report_renderer'`.

### Task 2: Renderer Implementation

**Files:**
- Create: `src/serenity_alpha_lab/evidence/report_renderer.py`
- Modify: `src/serenity_alpha_lab/evidence/__init__.py`

- [ ] **Step 1: Implement dataclass contracts**

```python
REPORT_RENDERER_CONTRACT_VERSION = "research.report_renderer@1.0.0"
TRUSTED_RESEARCH_REPORT_SCHEMA_NAME = "research.trusted_research_report"
REPORT_RENDERING_SCHEMA_NAME = "research.report_rendering"
```

Add `ResearchReportRenderContext`, `TrustedResearchReport`, `RenderedResearchReport`, `TrustedResearchReportRenderer` and `ReportRendererError`.

- [ ] **Step 2: Implement canonical JSON authority**

Build a deterministic envelope containing the validated `ResearchReport`, citation validation summary, rendering context, `authority="canonical_json"` and `authoritative_json_hash`.

- [ ] **Step 3: Implement derived Markdown/HTML**

Render report level, decision/as-of time, Dataset versions, model metadata, total cost, risk summary, disclaimer, claims, citations, evidence and validation issues. Escape HTML text; do not accept Markdown as input.

- [ ] **Step 4: Export public contracts**

Update `src/serenity_alpha_lab/evidence/__init__.py` with renderer imports and `__all__` entries.

### Task 3: Verification And Closeout

**Files:**
- Create: `docs/trusted-research-report-renderer.md`
- Modify: `docs/development-progress-checklist.md`
- Modify: `docs/development-status.md`
- Modify: `tasks/todo.md`

- [ ] **Step 1: Run focused Green tests**

Run: `uv run --extra core --extra dev python -m pytest tests/evidence/test_report_renderer.py -q`

Expected: PASS.

- [ ] **Step 2: Run related P5 renderer suite**

Run: `uv run --extra core --extra dev python -m pytest tests/evidence/test_report_renderer.py tests/evidence/test_citation_validator.py tests/evidence/test_evidence_schema_contract.py tests/evidence/test_quant_evidence_adapter.py tests/application/test_technical_agent_evidence_adapter.py tests/application/test_intel_agent_evidence_adapter.py tests/application/test_risk_portfolio_agent_evidence_adapter.py tests/application/test_decision_agent_counterargument_synthesis.py tests/application/test_model_routing_cache_budget.py tests/application/test_agent_tool_security.py tests/architecture/test_architecture_boundaries.py -q`

Expected: PASS.

- [ ] **Step 3: Run full verification**

Run:

```bash
uv run --extra core --extra dev python -m pytest -q
uv run --extra core --extra dev python -m compileall -q src/serenity_alpha_lab tests
scripts/verify-python-dependency-lock.sh
git rev-parse upstream/dsa-v3.26.1
git diff --check
```

Expected: all pass and immutable upstream tag remains `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`.

- [ ] **Step 4: Update status docs and checkpoint**

Record AEV-103, DEC-101, task status, current recovery anchors and next task `SAL-P5-016` without starting UI/notification work. Commit with a Chinese checkpoint message.
