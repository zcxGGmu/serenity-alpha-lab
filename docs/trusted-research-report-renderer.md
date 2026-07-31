# Trusted ResearchReport Renderer

> Task: `SAL-P5-015` Trusted ResearchReport And Renderer<br>
> Date: 2026-07-29<br>
> Status: `APPROVED FOR SAL-P5-016 INPUT ONLY`

## Conclusion

`SAL-P5-015` adds a pure offline trusted report rendering boundary:

```text
src/serenity_alpha_lab/evidence/report_renderer.py
tests/evidence/test_report_renderer.py
```

The renderer consumes an already-constructed `ResearchReport` and either validates it with `CitationValidator` or uses a caller-supplied `CitationValidationResult`. It emits a canonical JSON envelope as the sole authoritative report source, plus derived Markdown and HTML display strings. Markdown and HTML are never parsed back into source data and cannot become the authority.

## Contracts

| Item | Contract |
|---|---|
| Renderer contract | `research.report_renderer@1.0.0` |
| Trusted report schema | `research.trusted_research_report` / `1.0.0` |
| Rendering schema | `research.report_rendering` / `1.0.0` |
| Default template | `research.trusted_report.markdown_html@1.0.0` |
| Renderer | `TrustedResearchReportRenderer` |
| Render context | `ResearchReportRenderContext` |
| Trusted envelope | `TrustedResearchReport` |
| Rendered output | `RenderedResearchReport` |
| Error | `ReportRendererError` |

## Authority Rules

- `TrustedResearchReport.authoritative_json` is the authority and declares `authority=canonical_json`.
- `authoritative_json_hash` is a deterministic SHA-256 hash over canonical JSON.
- `RenderedResearchReport.markdown_source` and `html_source` are both `derived_from_authoritative_json`.
- `TrustedResearchReportRenderer.render()` accepts only `ResearchReport` objects, not Markdown strings or other presentation payloads.
- Caller-supplied validation results must match the input report id.

## Display Rules

Derived Markdown and HTML include:

- report level and as-of / decision time;
- generated time when present;
- authoritative JSON hash and template version;
- Dataset versions;
- model provider, model name and model version;
- prompt versions and cost metadata in the canonical JSON context;
- risk summary and disclaimer;
- claims, citations, evidence lineage and validation issues;
- warnings for partial or insufficient-evidence reports.

HTML output escapes text before rendering and does not include script execution or active UI behavior.

## Report Levels

The renderer preserves `verified`, `partial` and `insufficient_evidence` report levels from `CitationValidator`:

- consistent verified reports remain `verified`;
- invalid citation graphs are downgraded to `partial` and display validation issues;
- reports with no surviving claims render as `insufficient_evidence` and are not promoted to verified.

## Non-Goals

- No UI page, citation expansion UI, notification workflow, transactional outbox or publication flow.
- No real Provider calls, real LLM calls, LiteLLM imports, Agent stage execution or DSA Agent runtime invocation.
- No Evidence Store writes, Evidence body reads, EvidenceBundle construction or Quant Evidence Adapter execution.
- No Agent tool execution, Citation Validator repair loop, Worker runtime, Qlib runtime, production scheduling or formal portfolio backtest promotion.

## Verification

| Check | Result |
|---|---|
| Red target | `uv run --extra core --extra dev python -m pytest tests/evidence/test_report_renderer.py -q` initially failed with `ModuleNotFoundError: No module named 'serenity_alpha_lab.evidence.report_renderer'` |
| Focused target | `uv run --extra core --extra dev python -m pytest tests/evidence/test_report_renderer.py -q` -> `4 passed` |
| Architecture guard | `uv run --extra core --extra dev python -m pytest tests/architecture/test_architecture_boundaries.py::test_report_renderer_stays_offline_and_runtime_free -q` -> `1 passed` |
| Related P5 renderer suite | `uv run --extra core --extra dev python -m pytest tests/evidence/test_report_renderer.py tests/evidence/test_citation_validator.py tests/evidence/test_evidence_schema_contract.py tests/evidence/test_quant_evidence_adapter.py tests/application/test_technical_agent_evidence_adapter.py tests/application/test_intel_agent_evidence_adapter.py tests/application/test_risk_portfolio_agent_evidence_adapter.py tests/application/test_decision_agent_counterargument_synthesis.py tests/application/test_model_routing_cache_budget.py tests/application/test_agent_tool_security.py tests/architecture/test_architecture_boundaries.py -q` -> `73 passed` |
| Full suite | `uv run --extra core --extra dev python -m pytest -q` -> `484 passed, 3 skipped` |
| Compile | `uv run --extra core --extra dev python -m compileall -q src/serenity_alpha_lab tests` -> PASS |
| Dependency lock | `scripts/verify-python-dependency-lock.sh` -> PASS, `Resolved 298 packages` |
| Immutable upstream tag | `git rev-parse upstream/dsa-v3.26.1` -> `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a` |
| Diff hygiene | `git diff --check` -> PASS |

## Approval Record

This record approves trusted offline ResearchReport rendering as input to `SAL-P5-016` citation UI and notification Outbox. Later P5 tasks must still implement UI/notification surfaces, Agent regression evaluation and Gate G5 review before trusted research can enter RC.
