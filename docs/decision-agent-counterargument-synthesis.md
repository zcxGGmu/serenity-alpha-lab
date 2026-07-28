# Decision Agent Counterargument and Final Synthesis

> Task: `SAL-P5-011` Implement Multi-side Counterargument and Final Synthesis<br>
> Date: 2026-07-28<br>
> Status: `APPROVED FOR SAL-P5-012 / SAL-P5-013 / SAL-P5-015 INPUT ONLY`

## Conclusion

`SAL-P5-011` adds a pure offline Decision Agent synthesis adapter:

```text
src/serenity_alpha_lab/application/decision_agent.py
tests/application/test_decision_agent_counterargument_synthesis.py
```

The adapter consumes already-validated Technical, Intel and Risk/Portfolio Agent results, plus a prebuilt decision `EvidenceBundle` and concrete `PromptRunBinding`. It prepares a deterministic Decision prompt payload, validates already-produced structured Decision output, requires distinct bull/bear cases with citations, preserves Risk/Portfolio hard gates, and maps the result to DSA-compatible final decision fields.

This task does not call a model, execute DSA tools, fetch market/news data, read evidence bodies, write Evidence Store, run Citation Validator, render reports, start Worker loops, initialize Qlib runtime, schedule production work or promote formal portfolio backtests.

## Contracts

| Item | Contract |
|---|---|
| Decision Agent contract | `research.agent.decision@1.0.0` |
| Prompt payload schema | `research.agent.decision_prompt_payload` / `1.0.0` |
| Output adapter schema | `research.agent.decision_output_adapter` / `1.0.0` |
| Adapter | `EvidenceScopedDecisionAgent` |
| Prompt request | `DecisionAgentPromptRequest` |
| Prompt payload | `DecisionAgentPromptPayload` |
| Structured output | `DecisionStructuredOutput` |
| Bull/Bear case | `DecisionCase` |
| Disagreement summary | `DecisionDisagreementSummary` |
| Invalidation condition | `DecisionInvalidationCondition` |
| Result wrapper | `DecisionAgentResult` |
| Error | `DecisionAgentError` |

## Input Rules

`prepare_prompt_payload()` requires:

- `bundle.request.role == EvidenceBundleRole.DECISION`
- `prompt_binding.request.role == AgentPromptRole.DECISION`
- `prompt_binding.request.run_id` and `stage_id` match the explicit Decision request
- prior role results are exact `TechnicalAgentResult`, `IntelAgentResult` and `RiskPortfolioAgentResult`
- every Decision bundle evidence item sets `metadata.llm_recompute_allowed=false`

The payload records:

- current Decision `EvidenceBundle.to_prompt_payload()`
- concrete `PromptRunBinding.to_record()`
- prior role result records and deterministic role result hashes
- prior role citation evidence ids by role
- allowed evidence ids/hashes for evidence cited by prior role outputs
- preserved Risk/Portfolio `hard_gate_summary`
- forbidden runtime actions such as provider calls, model calls, DSA tool execution, Evidence body reads, Evidence Store writes, metric recomputation, Qlib initialization, Worker loops, report rendering and trade simulation

## Output Rules

`finalize_output()` validates caller-provided structured Decision output only:

- bull and bear cases are both required and must be distinct in thesis, factors and citation sets
- every bull/bear/disagreement/invalidation citation id exists in the structured citation list
- every structured citation references evidence included in the current Decision EvidenceBundle
- every structured citation must reference evidence already cited by at least one prior role output
- case `source_roles` must align with the prior role that cited the underlying evidence
- numeric claims must use `ClaimComputationPolicy.DETERMINISTIC_EVIDENCE`
- numeric claim value, unit, formula version, dataset versions, run id, stage id and artifact hash must match the deterministic citation
- Risk gate claims cannot contradict the preserved hard gate summary
- final recommendations cannot upgrade deterministic `block` or `not_evaluable` hard gates
- `eligible_for_ranking=false` from Risk/Portfolio evidence prevents the final decision from marking ranking eligibility true
- `agent_strong_conclusion_allowed=false` prevents high-confidence or buy/strong-buy final conclusions

These checks make multi-side disagreement and final synthesis machine-readable before later model routing, Citation Validator and report rendering work.

## DSA Compatibility

`DecisionAgentResult.to_dsa_compatible_opinion()` returns a legacy-style Decision opinion surface:

```json
{
  "agent_name": "decision",
  "signal": "negative",
  "recommendation": "blocked",
  "confidence": 0.61,
  "confidence_level": "medium",
  "reasoning": "...",
  "raw_data": {"bull_case": {}, "bear_case": {}, "citations": []}
}
```

`DecisionAgentResult.to_dsa_dashboard_fields()` returns dashboard/report compatibility fields:

- `final_decision`
- `decision_summary`
- `confidence_level`
- `confidence_score`
- `ranking_eligible`
- `bull_case`
- `bear_case`
- `disagreement_summary`
- `invalidation_conditions`
- `risk_gate`
- `warnings` / `limitations`
- cited `citations`

The mapping is a compatibility layer only. It does not patch legacy DSA Agent runtime, register routes or publish reports.

## Non-Goals

- No real Provider calls, real LLM calls, model routing, cache, token budget enforcement or price table.
- No Evidence Store writes, Evidence body reads, EvidenceBundle construction or Quant Evidence Adapter execution.
- No DSA Decision Agent runtime execution, legacy route registration or report generation.
- No Technical/Intel/Risk recomputation and no new facts outside prior role outputs plus current Decision citation graph.
- No Citation Validator, citation repair loop, renderer, notification workflow or report publication.
- No Worker loop, Qlib runtime, production scheduler, formal backtest promotion or legacy `/api/v1/backtest/*` behavior changes.

## Verification

| Check | Result |
|---|---|
| Red target | `uv run --extra core --extra dev python -m pytest tests/application/test_decision_agent_counterargument_synthesis.py -q` initially failed with `ModuleNotFoundError: No module named 'serenity_alpha_lab.application.decision_agent'` |
| Focused target | `uv run --extra core --extra dev python -m pytest tests/application/test_decision_agent_counterargument_synthesis.py -q` -> `4 passed` |
| Architecture guard | `uv run --extra core --extra dev python -m pytest tests/architecture/test_architecture_boundaries.py::test_decision_agent_adapter_stays_offline_and_runtime_free -q` -> `1 passed` |
| Related P5 suite | `uv run --extra core --extra dev python -m pytest tests/application/test_decision_agent_counterargument_synthesis.py tests/application/test_technical_agent_evidence_adapter.py tests/application/test_intel_agent_evidence_adapter.py tests/application/test_risk_portfolio_agent_evidence_adapter.py tests/application/test_evidence_bundle_builder.py tests/evidence/test_prompt_schema_registry.py tests/repositories/test_agent_stage_store.py tests/architecture/test_architecture_boundaries.py -q` -> `54 passed` |
| Full suite | `uv run --extra core --extra dev python -m pytest -q` -> `461 passed, 3 skipped` |
| Compile | `uv run --extra core --extra dev python -m compileall -q src/serenity_alpha_lab tests` -> PASS |
| Dependency lock | `scripts/verify-python-dependency-lock.sh` -> PASS, `Resolved 298 packages` |
| Immutable upstream tag | `git rev-parse upstream/dsa-v3.26.1` -> `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a` |
| Diff hygiene | `git diff --check` -> PASS |

## Approval Record

This record approves offline Decision Agent counterargument and final synthesis as input to `SAL-P5-012` model routing/cache/budget work and `SAL-P5-013` Citation Validator. Later P5 tasks must still implement actual model execution, model budget/cache enforcement, citation validation, tool runtime security and trusted report publication before Gate G5 can pass.
