# Risk/Portfolio Agent Evidence Adapter

> Task: `SAL-P5-010` Rewrite Risk/Portfolio Agent<br>
> Date: 2026-07-28<br>
> Status: `APPROVED FOR SAL-P5-011 / SAL-P5-012 / SAL-P5-013 / SAL-P5-015 INPUT ONLY`

## Conclusion

`SAL-P5-010` adds a pure offline Risk/Portfolio Agent evidence adapter:

```text
src/serenity_alpha_lab/application/risk_portfolio_agent.py
tests/application/test_risk_portfolio_agent_evidence_adapter.py
```

The adapter converts a prebuilt `risk_portfolio` `EvidenceBundle` plus concrete `PromptRunBinding` into a deterministic prompt payload, validates already-produced structured Risk/Portfolio output, preserves deterministic hard gates, and maps the result to DSA-compatible risk and portfolio fields.

This task does not call a model, execute DSA Risk/Portfolio tools, run a backtest, recompute risk/metrics/costs, read evidence bodies, write Evidence Store, start Worker loops, initialize Qlib runtime, validate final report citations, render reports, schedule production work or promote formal portfolio backtests.

## Contracts

| Item | Contract |
|---|---|
| Risk/Portfolio Agent contract | `research.agent.risk_portfolio@1.0.0` |
| Prompt payload schema | `research.agent.risk_portfolio_prompt_payload` / `1.0.0` |
| Output adapter schema | `research.agent.risk_portfolio_output_adapter` / `1.0.0` |
| Adapter | `EvidenceScopedRiskPortfolioAgent` |
| Prompt request | `RiskPortfolioAgentPromptRequest` |
| Prompt payload | `RiskPortfolioAgentPromptPayload` |
| Structured output | `RiskPortfolioStructuredOutput` |
| Result wrapper | `RiskPortfolioAgentResult` |
| Error | `RiskPortfolioAgentError` |

## Evidence Allowlist

Risk/Portfolio Agent input is restricted to deterministic formal portfolio evidence:

| Evidence kind | Accepted | Reason |
|---|---:|---|
| `risk_policy_result` | yes | Carries deterministic RiskPolicy hard gate status and rule outcomes |
| `backtest_bias_audit` | yes | Carries hard failure, not-evaluable and ranking eligibility guards |
| `backtest_performance_metrics` | yes | Carries deterministic return/risk/cost metrics for explanation only |
| `backtest_run_summary` | yes | Carries formal run lineage and final status |
| `backtest_artifact_bundle` | yes | Carries formal output artifact lineage |
| `formal_backtest_api_record` | yes | Carries formal API lineage |
| `screen_snapshot` / `factor_evaluation` | no | Owned by Technical/Decision context, not Risk/Portfolio hard gates |
| `unstructured_source` | no | Owned by Intel context, not deterministic portfolio constraints |

Each accepted evidence record must carry `metadata.llm_recompute_allowed=false`. The adapter rejects evidence outside the approved kind/scope allowlist, so Screen/Factor/Intel evidence cannot be relabeled into Risk/Portfolio hard-gate context.

## Hard Gate Rules

`prepare_prompt_payload()` derives a `hard_gate_summary` from Evidence metadata:

- `risk_status=block` remains `block`.
- `risk_status=warn` remains at least `warn`.
- `audit_status=invalid` becomes `block`.
- `eligible_for_ranking=false` becomes `block`.
- `not_evaluable_rule_ids` become `not_evaluable` unless an existing `block` is more severe.
- `agent_strong_conclusion_allowed=false` is preserved for later Decision/Report stages.

`finalize_output()` rejects structured output that upgrades `block` or `not_evaluable` to a less restrictive gate. The Agent may explain and contextualize these deterministic outcomes, but it has no authority to override them.

## Prompt Payload Rules

`prepare_prompt_payload()` requires:

- `bundle.request.role == EvidenceBundleRole.RISK_PORTFOLIO`
- `prompt_binding.request.role == AgentPromptRole.RISK_PORTFOLIO`
- `prompt_binding.request.run_id` and `stage_id` match the explicit request context
- all included EvidenceBundle records pass the formal Risk/Portfolio allowlist
- all accepted evidence records disallow LLM recomputation

The payload records the `EvidenceBundle` prompt payload, `PromptRunBinding` record, allowed evidence ids/hashes, hard-gate summary, forbidden runtime actions and deterministic `payload_hash`.

Forbidden actions include real Provider/LLM calls, DSA Agent tool execution, evidence body reads, Evidence Store writes, formal backtest execution, Qlib runtime initialization, risk/metrics/cost recomputation, hard-gate override, report rendering and trade simulation.

## Structured Output Rules

`finalize_output()` validates caller-provided structured output only:

- every citation references evidence included in the Risk/Portfolio prompt payload
- citation dataset versions, run id, stage id, artifact hash and formula versions match the cited `EvidenceRecord`
- duplicate citation ids are rejected
- numeric claims must use `ClaimComputationPolicy.DETERMINISTIC_EVIDENCE`
- numeric claim value, unit, formula version, dataset versions, run id, stage id and artifact hash must match the deterministic citation
- risk gate claims must be cited and cannot contradict the final `gate_status`
- `block` / `not_evaluable` prompt hard gates cannot be upgraded

These checks make the no-recompute and no-override boundary machine-readable before later model routing, Citation Validator and report rendering tasks.

## DSA Compatibility

`RiskPortfolioAgentResult.to_dsa_compatible_opinion()` returns a legacy-style Risk/Portfolio opinion surface:

```json
{
  "agent_name": "risk_portfolio",
  "signal": "negative",
  "risk_status": "block",
  "portfolio_action": "avoid",
  "confidence": 0.68,
  "reasoning": "...",
  "raw_data": {"claims": [], "citations": [], "hard_gate_summary": {}}
}
```

`RiskPortfolioAgentResult.to_dsa_dashboard_fields()` returns dashboard/report compatibility fields:

- `risk_analysis`
- `portfolio_analysis`
- `risk_status`
- `portfolio_action`
- `hard_gates`
- `risk_factors`
- `portfolio_constraints`
- `warnings` / `limitations`
- cited `citations`

The mapping is a compatibility layer only. It does not patch legacy DSA Agent runtime, register routes, compute weights or execute trades.

## Non-Goals

- No real Provider calls, real LLM calls, model routing, cache, token budget enforcement or price table.
- No Evidence Store writes, Evidence body reads, EvidenceBundle construction or Quant Evidence Adapter execution.
- No DSA Risk/Portfolio Agent runtime execution or legacy route registration.
- No RiskPolicy, BiasAudit, metric, ledger, cost, order or portfolio recomputation.
- No Citation Validator, citation repair loop, report renderer, notification workflow or report publication.
- No Worker loop, Qlib runtime, production scheduler, formal backtest promotion or legacy `/api/v1/backtest/*` behavior changes.

## Verification

| Check | Result |
|---|---|
| Red target | `uv run --extra core --extra dev python -m pytest tests/application/test_risk_portfolio_agent_evidence_adapter.py -q` initially failed with `ModuleNotFoundError: No module named 'serenity_alpha_lab.application.risk_portfolio_agent'` |
| Focused target | `uv run --extra core --extra dev python -m pytest tests/application/test_risk_portfolio_agent_evidence_adapter.py -q` -> `4 passed` |
| Architecture guard | `uv run --extra core --extra dev python -m pytest tests/architecture/test_architecture_boundaries.py::test_risk_portfolio_agent_adapter_stays_offline_and_runtime_free -q` -> `1 passed` |
| Related P5 suite | `uv run --extra core --extra dev python -m pytest tests/application/test_risk_portfolio_agent_evidence_adapter.py tests/application/test_evidence_bundle_builder.py tests/evidence/test_quant_evidence_adapter.py tests/evidence/test_prompt_schema_registry.py tests/repositories/test_agent_stage_store.py tests/architecture/test_architecture_boundaries.py -q` -> `41 passed` |
| Full suite | `uv run --extra core --extra dev python -m pytest -q` -> `456 passed, 3 skipped` |
| Compile | `uv run --extra core --extra dev python -m compileall -q src/serenity_alpha_lab tests` -> PASS |
| Dependency lock | `scripts/verify-python-dependency-lock.sh` -> PASS, `Resolved 298 packages` |
| Immutable upstream tag | `git rev-parse upstream/dsa-v3.26.1` -> `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a` |
| Diff hygiene | `git diff --check` -> PASS |

## Approval Record

This record approves offline Risk/Portfolio Agent evidence adaptation as input to `SAL-P5-011` multi-side counterargument/final synthesis and later model routing, citation validation and report rendering. Later P5 tasks must still implement actual Agent execution, Decision role, model budget/cache enforcement, Citation Validator, tool runtime security and trusted report publication before Gate G5 can pass.
