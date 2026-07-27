# Technical Agent Evidence Adapter

> Task: `SAL-P5-008` Rewrite Technical Agent<br>
> Date: 2026-07-27<br>
> Status: `APPROVED FOR SAL-P5-009 / SAL-P5-012 / SAL-P5-013 / SAL-P5-015 INPUT ONLY`

## Conclusion

`SAL-P5-008` adds a pure offline Technical Agent evidence adapter:

```text
src/serenity_alpha_lab/application/technical_agent.py
tests/application/test_technical_agent_evidence_adapter.py
```

The adapter converts a prebuilt technical `EvidenceBundle` plus concrete `PromptRunBinding` into a deterministic Technical Agent prompt payload, then validates an already-produced structured technical output and maps it to DSA-compatible Technical Agent opinion/dashboard fields.

This task does not call a model. It does not fetch realtime quotes, historical bars, indicators, chip distribution, chart patterns or any Provider data. It validates cited structured output only, so later model routing/cache/budget work can execute against a fixed contract without letting the model recompute technical or factor metrics.

## Contracts

| Item | Contract |
|---|---|
| Technical Agent contract | `research.agent.technical@1.0.0` |
| Prompt payload schema | `research.agent.technical_prompt_payload` / `1.0.0` |
| Output adapter schema | `research.agent.technical_output_adapter` / `1.0.0` |
| Adapter | `EvidenceScopedTechnicalAgent` |
| Prompt request | `TechnicalAgentPromptRequest` |
| Prompt payload | `TechnicalAgentPromptPayload` |
| Structured output | `TechnicalAgentStructuredOutput` |
| Result wrapper | `TechnicalAgentResult` |
| Error | `TechnicalAgentError` |

## Evidence Allowlist

Technical Agent input is restricted to deterministic technical, screening and factor evidence:

| Evidence kind | Accepted | Reason |
|---|---:|---|
| `screen_snapshot` | yes | Carries deterministic ranked screen result and final scores |
| `screen_pipeline_snapshot` | yes | Carries deterministic L0-L4 screen trace |
| `factor_evaluation` | yes | Carries factor IC/ICIR/group return/turnover metrics with formulas |
| `factor_cache_manifest` | yes | Carries factor computation lineage and cache identity |
| `backtest_performance_metrics` | no | Belongs to formal portfolio backtest, not Technical Agent |
| `risk_policy_result` | no | Owned by later Risk/Portfolio Agent rewrite |
| `backtest_bias_audit` | no | Owned by formal backtest/risk review, not Technical Agent |
| `formal_backtest_api_record` | no | API lineage only, not a technical signal input |

The adapter raises `TechnicalAgentError` if a Technical Agent bundle includes formal portfolio backtest evidence. This preserves the Gate G4 boundary: Screen/Factor evidence can inform technical analysis, while formal backtest/risk evidence remains separate until later Risk/Decision stages.

## Prompt Payload Rules

`prepare_prompt_payload()` requires:

- `bundle.request.role == EvidenceBundleRole.TECHNICAL`
- `prompt_binding.request.role == AgentPromptRole.TECHNICAL`
- `prompt_binding.request.run_id` and `prompt_binding.request.stage_id` match the explicit Technical Agent request context
- included EvidenceBundle records all pass the Technical Agent evidence allowlist
- accepted evidence kinds also match the expected evaluation scope and carry `metadata.llm_recompute_allowed=false`
- prompt/bundle metadata remains concrete; no `latest` alias is introduced

The payload records:

- `bundle.to_prompt_payload()` output
- `PromptRunBinding.to_record()` output with prompt/schema/tool/model hashes
- allowed evidence ids and content hashes
- explicit forbidden actions such as provider calls, model calls, DSA tool execution, indicator recomputation, worker loops, Qlib initialization, report rendering and trading
- deterministic `payload_hash`

## Structured Output Rules

`finalize_output()` validates a caller-provided `TechnicalAgentStructuredOutput`:

- `signal`, `confidence`, `trend_score`, MA alignment and volume status are typed and bounded
- every output citation references an evidence id included in the current EvidenceBundle
- duplicate citation ids are rejected
- citation dataset versions, run id, stage id and artifact hash must match the cited EvidenceRecord lineage
- numeric claims must use `ClaimComputationPolicy.DETERMINISTIC_EVIDENCE`
- numeric claim citations must include unit and formula version
- numeric claim value, unit, formula version, dataset versions, run id and artifact hash must match the cited deterministic citation

This makes the no-recompute rule machine-checkable before later Citation Validator and report rendering stages.

## DSA Compatibility

`TechnicalAgentResult.to_dsa_compatible_opinion()` returns the legacy Technical Agent opinion surface:

```json
{
  "agent_name": "technical",
  "signal": "buy",
  "confidence": 0.82,
  "reasoning": "...",
  "key_levels": {"support": 1600.0, "resistance": 1800.0, "stop_loss": 1550.0},
  "raw_data": {"claims": [], "citations": [], "allowed_evidence_ids": []}
}
```

`TechnicalAgentResult.to_dsa_dashboard_fields()` returns compatibility fields used by existing DSA dashboard/report adapters:

- `technical_analysis`
- `trend_analysis`
- `ma_analysis`
- `volume_analysis`
- `pattern_analysis`
- `key_levels`
- `trend_status`
- `volume_status`
- cited `citations`

The mapping is intentionally a compatibility layer. It does not modify `.worktrees/dsa-v3.26.1`, does not patch legacy Agent runtime and does not register FastAPI routes.

For DSA dashboard compatibility, the adapter also returns a nested `data_perspective` block with `trend_status`, `price_position` and object-shaped `volume_analysis`. Missing realtime-only values remain `null` because this adapter does not fetch quotes or recompute indicators.

## Non-Goals

- No real Provider calls, realtime quotes, historical K-line fetches or DSA Technical Agent tool execution.
- No real LLM calls, model routing, model cache, token budget enforcement or price table.
- No Evidence Store writes, EvidenceBundle construction, Quant Evidence Adapter execution or evidence body reads.
- No Intel/Risk/Portfolio/Decision Agent rewrite.
- No Citation Validator, citation repair loop, report renderer, notification workflow or report publication.
- No Worker loop, Qlib runtime, production scheduler, formal backtest promotion or legacy `/api/v1/backtest/*` behavior changes.

## Verification

| Check | Result |
|---|---|
| Red target | `uv run --extra core --extra dev python -m pytest tests/application/test_technical_agent_evidence_adapter.py -q` initially failed with `ModuleNotFoundError: No module named 'serenity_alpha_lab.application.technical_agent'` |
| Focused target | `uv run --extra core --extra dev python -m pytest tests/application/test_technical_agent_evidence_adapter.py -q` -> `7 passed` |
| Architecture guard | `uv run --extra core --extra dev python -m pytest tests/architecture/test_architecture_boundaries.py::test_technical_agent_adapter_stays_offline_and_runtime_free -q` -> `1 passed` |
| Related suite | `uv run --extra core --extra dev python -m pytest tests/application/test_technical_agent_evidence_adapter.py tests/application/test_evidence_bundle_builder.py tests/evidence/test_quant_evidence_adapter.py tests/evidence/test_prompt_schema_registry.py tests/repositories/test_agent_stage_store.py tests/architecture/test_architecture_boundaries.py -q` -> `41 passed` |
| Full suite | `uv run --extra core --extra dev python -m pytest -q` -> `445 passed, 3 skipped` |
| Compile | `uv run --extra core --extra dev python -m compileall -q src/serenity_alpha_lab tests` -> PASS |
| Immutable upstream tag | `git rev-parse upstream/dsa-v3.26.1` -> `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a` |
| Dependency lock | `scripts/verify-python-dependency-lock.sh` -> PASS, `Resolved 298 packages` |
| Diff hygiene | `git diff --check` -> PASS |

## Approval Record

This record approves offline Technical Agent evidence adaptation as input to `SAL-P5-009` Intel Agent rewrite and later model routing, citation validation and report rendering. Later P5 tasks must still implement actual Agent execution, Intel/Risk/Decision roles, model budget/cache enforcement, Citation Validator, tool runtime security and trusted report publication before Gate G5 can pass.
