# Prompt and Output Schema Registry

> Task: `SAL-P5-006` Build Prompt and Output Schema Registry<br>
> Date: 2026-07-27<br>
> Status: `APPROVED FOR SAL-P5-007 / SAL-P5-008 / SAL-P5-009 / SAL-P5-010 / SAL-P5-012 / SAL-P5-014 INPUT ONLY`

## Conclusion

`SAL-P5-006` adds a pure offline prompt and output schema registry:

```text
src/serenity_alpha_lab/evidence/prompt_registry.py
tests/evidence/test_prompt_schema_registry.py
```

The registry versions role prompts, output JSON Schemas, read-only tool declarations, model capability declarations and run prompt bindings. It records canonical hashes for every declaration, makes published prompt versions immutable, rejects `latest` aliases, checks output schema compatibility, and resolves a run binding that captures the exact Prompt/Schema/Tool/Model versions and hashes used by a future Agent stage.

This task defines registry metadata only. It does not execute Evidence Agent stages, call real Providers or LLMs, start Worker loops, initialize Qlib runtime, schedule production work, render reports, validate citations, send notifications or promote formal portfolio backtests.

## Contracts

| Item | Contract |
|---|---|
| Registry contract | `research.prompt_registry@1.0.0` |
| Prompt schema | `research.prompt_template` / `1.0.0` |
| Output schema declaration | `research.prompt_output_schema` / `1.0.0` |
| Tool declaration schema | `research.prompt_tool` / `1.0.0` |
| Model capability schema | `research.model_capability` / `1.0.0` |
| Run binding schema | `research.prompt_run_binding` / `1.0.0` |
| Registry | `PromptSchemaRegistry` |
| Default registry | `default_prompt_schema_registry()` |
| Roles | `technical`, `intel`, `risk_portfolio`, `decision` |

## Registry Rules

`PromptSchemaRegistry` stores declaration metadata in memory and returns immutable dataclass records:

- `OutputSchemaDeclaration` versions role output schemas and computes `schema_hash`.
- `ToolDeclaration` versions read-only/no-side-effect tools and computes `tool_hash`.
- `ModelCapabilityDeclaration` versions JSON-Schema-capable model families and computes `capability_hash`.
- `PromptDeclaration` versions role prompt templates and computes `prompt_hash`.
- `PromptRunBinding` records the concrete prompt, output schema, tool and model versions/hashes for a run/stage.

Published prompt versions cannot be overwritten. A duplicate `prompt_id + prompt_version` registration raises `PromptRegistryError`, and publication preserves the prompt content hash so draft-to-published status changes do not alter the immutable prompt body identity.

## Output Schema Compatibility

Output schemas use semantic versions. Minor/patch changes can add optional top-level properties only. Removing properties, changing property schemas, changing `required`, changing `type` or changing `additionalProperties` is breaking and requires a new major version.

`latest` is rejected wherever a concrete semantic version is required. Future stages must persist `PromptRunBinding.to_record()` output rather than storing mutable aliases.

## Default Role Prompts

The default registry publishes four role prompts:

| Prompt id | Role | Output schema |
|---|---|---|
| `technical_research` | `technical` | `research.agent.technical_output@1.0.0` |
| `intel_research` | `intel` | `research.agent.intel_output@1.0.0` |
| `risk_portfolio_research` | `risk_portfolio` | `research.agent.risk_portfolio_output@1.0.0` |
| `decision_research` | `decision` | `research.agent.decision_output@1.0.0` |

All default prompts require included EvidenceBundle records only, citation of evidence ids and hashes, and `no_llm_recompute`. They explicitly prevent LLM recomputation of returns, risk, drawdown, costs, orders, ledger state, gate outcomes and source trust labels.

## Tool and Model Boundary

`ToolDeclaration` currently permits no-side-effect or read-only tools only. Scope categories such as `shell`, `trading`, `trade`, `brokerage`, `database_write`, `db_write` and `filesystem_write` are rejected at declaration time.

The default model capability is `registry_only_json_model@1.0.0`. It describes required model capabilities for later routing but does not bind or call a real provider/model.

## Non-Goals

- No Evidence Agent stage orchestration, checkpoint persistence, retry, cache or budget execution.
- No real Provider calls, real LLM calls, Worker loop, Qlib runtime or production scheduler.
- No Evidence Store writes, EvidenceBundle construction, evidence body reads or Quant Evidence Adapter execution.
- No Citation Validator, citation repair loop, report renderer, notification workflow or report publication.
- No tool allowlist enforcement beyond registry-time declaration safety; deeper runtime security starts in `SAL-P5-014`.
- No change to legacy DSA `/api/v1/backtest/*` Signal Evaluation behavior.

## Verification

| Check | Result |
|---|---|
| Red target | `uv run --extra core --extra dev python -m pytest tests/evidence/test_prompt_schema_registry.py -q` initially failed with `ModuleNotFoundError: No module named 'serenity_alpha_lab.evidence.prompt_registry'` |
| Focused target | `uv run --extra core --extra dev python -m pytest tests/evidence/test_prompt_schema_registry.py -q` -> `4 passed` |
| Architecture guard | `uv run --extra core --extra dev python -m pytest tests/architecture/test_architecture_boundaries.py::test_prompt_registry_stays_offline_and_runtime_free -q` -> `1 passed` |
| Related suite | `uv run --extra core --extra dev python -m pytest tests/evidence/test_prompt_schema_registry.py tests/evidence/test_evidence_schema_contract.py tests/evidence/test_source_trust_cleaning.py tests/evidence/test_quant_evidence_adapter.py tests/application/test_evidence_bundle_builder.py tests/architecture/test_architecture_boundaries.py -q` -> `38 passed` |
| Full suite | `uv run --extra core --extra dev python -m pytest -q` -> `432 passed, 3 skipped` |
| Compile | `uv run --extra core --extra dev python -m compileall -q src/serenity_alpha_lab tests` -> PASS |
| Dependency lock | `scripts/verify-python-dependency-lock.sh` -> PASS, `Resolved 298 packages` |
| Immutable upstream tag | `git rev-parse upstream/dsa-v3.26.1` -> `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a` |
| Diff hygiene | `git diff --check` -> PASS |

## Approval Record

This record approves the offline prompt/schema/tool/model registry as input to `SAL-P5-007` Agent Stage persistence and later role Agent rewrites. Later P5 tasks must still implement Agent stages, model routing, budget/cache execution, citation validation, tool runtime security and renderers before Gate G5 can pass.
