# EvidenceBundle Builder

> Task: `SAL-P5-003` Implement EvidenceBundle Builder<br>
> Date: 2026-07-26<br>
> Status: `APPROVED FOR SAL-P5-004 / SAL-P5-005 / SAL-P5-006 INPUT ONLY`

## Conclusion

`SAL-P5-003` adds an offline application-layer EvidenceBundle Builder:

```text
src/serenity_alpha_lab/application/evidence_bundle_builder.py
tests/application/test_evidence_bundle_builder.py
```

The builder consumes `SAL-P5-002` `LocalEvidenceStore` metadata and constructs a minimal structured context bundle by tenant/team/user scope, role, instrument, decision time and deterministic token budget. It filters future evidence, limits instrument-specific evidence, dedupes by `content_hash`, ranks evidence by role priority/trust/scope/instrument specificity/recency and trims over-budget records without truncating fixed schema instructions.

This task builds structured context only. It does not execute Evidence Agent stages, call real Providers or LLMs, start Worker loops, initialize Qlib runtime, adapt Quant runtime outputs into evidence, validate or repair report citations, render reports, send notifications, schedule production work or promote formal portfolio backtests.

## Contracts

| Item | Contract |
|---|---|
| Bundle contract | `research.evidence_bundle@1.0.0` |
| Bundle schema | `research.evidence_bundle` / `1.0.0` |
| Builder | `EvidenceBundleBuilder` |
| Request | `EvidenceBundleRequest` |
| Budget | `EvidenceBundleBudget` |
| Roles | `technical`, `intel`, `risk_portfolio`, `decision` |
| Status | `complete`, `trimmed`, `empty`, `budget_exhausted` |
| Token estimate | deterministic UTF-8 byte length / 4 ceiling |

## Bundle Rules

`EvidenceBundleBuilder.build()` requires:

- visible evidence records from `LocalEvidenceStore.find_evidence()` for the caller tenant/team/user scope
- timezone-aware `decision_time`
- a positive `max_prompt_tokens`
- fixed schema instructions that fit inside the budget before any evidence is added

The builder excludes:

- evidence with `available_at > decision_time`
- instrument-specific evidence whose `instrument_id` differs from the request instrument
- evidence outside optional requested kind/scope filters
- duplicate evidence with a previously selected `content_hash`
- lower-priority evidence that would exceed token or item budget

Global evidence with `instrument_id=None` remains eligible for instrument-specific bundles.

## Priority Policy

Priority is deterministic and role-specific:

- `risk_portfolio` favors `risk_policy_result`, `backtest_bias_audit`, `backtest_performance_metrics`, `backtest_run_summary` and formal API lineage.
- `technical` favors deterministic metrics, factor evaluation, screen snapshots and formal backtest outputs.
- `decision` favors risk, metrics, bias audit, run summaries, formal API lineage and screening/factor context.
- `intel` currently ranks only existing structured lineage sources; unstructured source trust and cleaning are deferred to `SAL-P5-004`.

Within role priority, the score adds trust level, formal portfolio backtest scope, exact instrument match/global context and recency. Ties resolve by `evidence_id`, so repeated builds are stable.

## Token Budget

The bundle always reserves fixed schema instructions:

```text
EvidenceBundle instructions: use only included evidence_records...
```

If the fixed instructions cannot fit, the builder raises `EvidenceBundleError` instead of truncating them. If evidence records exceed the remaining budget, records are removed by priority and added to `excluded_evidence` with `reason=budget_trimmed`.

The token estimate is intentionally deterministic and provider-free. It is not a provider billing meter and does not call a tokenizer, LLM or external service.

## Prompt Payload

`EvidenceBundle.to_prompt_payload()` emits:

- bundle id, schema, status, role, instrument and decision time
- fixed schema instructions
- included `EvidenceRecord.to_record()` payloads
- excluded evidence ids with reasons and estimated tokens

Evidence body bytes are not embedded. Later Agent stages must cite evidence ids and hashes and must not infer unavailable body content.

## Non-Goals

- No Evidence Agent stage orchestration, model routing, cache or budget execution.
- No real Provider calls, real LLM calls, Worker loop, Qlib runtime or production scheduler.
- No Quant Evidence Adapter that converts P3/P4 runtime objects into `EvidenceRecord` rows.
- No Citation Validator, citation repair loop, report renderer or notification workflow.
- No TrustPolicy for unstructured news/search/social sources; that starts in `SAL-P5-004`.
- No promotion of formal portfolio backtest results beyond the Gate G4-approved evidence input boundary.

## Verification

| Check | Result |
|---|---|
| Red target | `uv run --extra core --extra dev python -m pytest tests/application/test_evidence_bundle_builder.py -q` initially failed with `ModuleNotFoundError: No module named 'serenity_alpha_lab.application.evidence_bundle_builder'` |
| Focused target | `uv run --extra core --extra dev python -m pytest tests/application/test_evidence_bundle_builder.py -q` -> `3 passed` |
| Related suite | `uv run --extra core --extra dev python -m pytest tests/application/test_evidence_bundle_builder.py tests/repositories/test_evidence_store.py tests/evidence/test_evidence_schema_contract.py tests/architecture/test_architecture_boundaries.py -q` -> `27 passed` |
| Full suite | `uv run --extra core --extra dev python -m pytest -q` -> `417 passed, 3 skipped` |
| Compile | `uv run --extra core --extra dev python -m compileall -q src/serenity_alpha_lab tests` -> PASS |
| Dependency lock | `scripts/verify-python-dependency-lock.sh` -> PASS, `Resolved 298 packages` |
| Immutable upstream tag | `git rev-parse upstream/dsa-v3.26.1` -> `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a` |
| Diff hygiene | `git diff --check` -> PASS |

## Approval Record

This record approves offline EvidenceBundle construction as input to `SAL-P5-004` source trust/cleaning, `SAL-P5-005` Quant Evidence Adapter and `SAL-P5-006` Prompt/Output Schema Registry. Later P5 tasks must still implement Quant evidence production, prompt/schema registry, Agent stages, citation validation, model budgeting and renderers before Gate G5 can pass.
