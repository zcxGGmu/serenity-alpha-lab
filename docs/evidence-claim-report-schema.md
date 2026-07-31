# Evidence / Claim / Report Schema

> Task: `SAL-P5-001` Define Evidence / Claim / Report Schema<br>
> Date: 2026-07-26<br>
> Status: `APPROVED FOR SAL-P5-002 EVIDENCE STORE INPUT ONLY`

## Conclusion

`SAL-P5-001` freezes the first P5 schema boundary for evidence-based research:

```text
src/serenity_alpha_lab/evidence/schema.py
tests/evidence/test_evidence_schema_contract.py
```

The contract defines versioned `EvidenceRecord`, `ReportCitation`, `ResearchClaim` and `ResearchReport` Pydantic models with JSON Schema export helpers while preserving the project’s existing JSON-friendly `to_record()` semantics. It maps P3 Screen/Factor outputs and P4 formal backtest/risk outputs into explicit evidence kinds so later Evidence Store, EvidenceBundle Builder, Quant Evidence Adapter, Agent stages and Citation Validator can share one reference graph.

This task defines schema only. It does not persist evidence, build bundles, adapt Quant records into evidence rows, run Evidence Agent stages, call real Providers or LLMs, start Worker loops, initialize Qlib runtime, render reports or send notifications.

## Contracts

| Item | Contract |
|---|---|
| Evidence contract | `research.evidence@1.0.0` |
| Evidence schema | `research.evidence` / `1.0.0` |
| Claim contract | `research.claim@1.0.0` |
| Claim schema | `research.claim` / `1.0.0` |
| Report contract | `research.report@1.0.0` |
| Report schema | `research.report` / `1.0.0` |
| Citation schema | `research.report_citation` / `1.0.0` |
| JSON Schema helper | `evidence_json_schemas()` |
| Quant source matrix | `quant_evidence_source_matrix()` |

## Evidence Rules

`EvidenceRecord` requires:

- `source`: source id, source type, schema name/version and optional contract/source URI.
- `available_at`: timezone-aware timestamp used by later bundle/report decision-time checks.
- `content_hash`: `sha256:<64 lowercase hex>` hash of the referenced content or normalized payload.
- `trust`: `authoritative`, `high`, `medium`, `low` or `untrusted`.
- `dataset_versions`: concrete `dsv_*` versions only; `latest` is rejected.
- Optional lineage: `instrument_id`, `as_of`, `run_id`, `stage_id`, `trace_id`, `artifact_id`, `artifact_hash` and `formula_versions`.

Evidence with `evaluation_scope=formal_portfolio_backtest` may only use formal P4 output kinds:

- `backtest_run_summary`
- `backtest_artifact_bundle`
- `risk_policy_result`
- `backtest_bias_audit`
- `backtest_performance_metrics`
- `formal_backtest_api_record`

`screen_snapshot`, `factor_evaluation`, `quant_screening_api_record`, `historical_universe`, `factor_cache_manifest`, `screen_pipeline_snapshot` and `quant_lab_lineage` stay in their own scopes and cannot be relabeled as formal portfolio backtest output.

## Quant Source Mapping

| Evidence kind | Scope | Source schema | Approved from | Formal output |
|---|---|---|---|---|
| `historical_universe` | `dataset_lineage` | `quant.historical_universe_snapshot` | `SAL-P3-011` | No |
| `factor_cache_manifest` | `dataset_lineage` | `quant.factor_cache_manifest` | `SAL-P3-010` | No |
| `factor_evaluation` | `factor_evaluation` | `quant.factor_evaluation` | `SAL-P3-009` | No |
| `screen_pipeline_snapshot` | `screening` | `quant.screen_pipeline_snapshot` | `SAL-P3-012` | No |
| `screen_snapshot` | `screening` | `quant.screen_snapshot` | `SAL-P3-013` | No |
| `quant_screening_api_record` | `api_lineage` | `application.quant_screening_api` | `SAL-P3-014` | No |
| `backtest_run_summary` | `formal_portfolio_backtest` | `quant.backtest_run` | `SAL-P4-017` | Yes |
| `backtest_artifact_bundle` | `formal_portfolio_backtest` | `quant.backtest_artifact_bundle` | `SAL-P4-004` | Yes |
| `risk_policy_result` | `formal_portfolio_backtest` | `quant.backtest.risk_policy` | `SAL-P4-014` | Yes |
| `backtest_bias_audit` | `formal_portfolio_backtest` | `quant.backtest.bias_audit` | `SAL-P4-015` | Yes |
| `backtest_performance_metrics` | `formal_portfolio_backtest` | `quant.backtest.performance_metrics` | `SAL-P4-016` | Yes |
| `formal_backtest_api_record` | `formal_portfolio_backtest` | `application.formal_backtest_api` | `SAL-P4-020` | Yes |
| `quant_lab_lineage` | `ui_lineage` | `dsa.quant_lab` | `SAL-P4-021` | No |

The matrix deliberately excludes `legacy_signal_evaluation`, `qlib_internal_evidence`, `alphasift_tn_evaluation`, Dataset conversion artifacts and raw Screen result aliases from the formal portfolio backtest namespace.

## Claim Rules

`ResearchClaim` requires `claim_id`, `kind`, `statement`, `verification_status` and explicit `citation_ids`.

Numeric metric claims additionally require:

- at least one citation id
- `unit`
- `formula_version`
- `computation_policy=deterministic_evidence`

`computation_policy=llm_narrative` is rejected for `numeric_metric` claims. LLM-authored claims may summarize cited facts or provide qualitative narrative, but cannot compute or rewrite returns, risk, drawdown, cost, orders, ledger state or deterministic gate outcomes.

## Report Rules

`ResearchReport` validates the reference graph:

- every citation references an included evidence id
- every claim citation id exists in the report
- evidence `available_at` cannot be later than report `decision_time`
- report-level `verified` requires at least one claim and all claims `verification_status=verified`
- report-levels are limited to `verified`, `partial`, `insufficient_evidence` and `blocked`

Markdown/HTML rendering remains out of scope. Later renderers must consume this structured report schema as authority; Markdown must not become the authoritative data source.

## Non-Goals

- No `EvidenceStore` persistence, content-addressed body storage, access control or revision records.
- No `EvidenceBundle` Builder, token budgeting, prioritization or decision-time retrieval.
- No Quant Evidence Adapter that transforms P3/P4 runtime objects into `EvidenceRecord` rows.
- No Prompt/Output Schema Registry, Agent checkpoint, model routing, cache or budget execution.
- No Citation Validator repair loop or report renderer.
- No real Provider calls, real LLM calls, Worker loop, Qlib runtime or production report generation.
- No change to legacy DSA `/api/v1/backtest/*` Signal Evaluation behavior.

## Verification

| Check | Result |
|---|---|
| Red target | `uv run --extra core --extra dev python -m pytest tests/evidence/test_evidence_schema_contract.py -q` initially failed with `ModuleNotFoundError: No module named 'serenity_alpha_lab.evidence.schema'` |
| Focused target | `uv run --extra core --extra dev python -m pytest tests/evidence/test_evidence_schema_contract.py -q` -> `5 passed` |
| Related architecture suite | `uv run --extra core --extra dev python -m pytest tests/evidence/test_evidence_schema_contract.py tests/architecture/test_architecture_boundaries.py -q` -> `20 passed` |
| Full suite | `uv run --extra core --extra dev python -m pytest -q` -> `410 passed, 3 skipped` |
| Compile | `uv run --extra core --extra dev python -m compileall -q src/serenity_alpha_lab tests` -> PASS |
| Dependency lock | `scripts/verify-python-dependency-lock.sh` -> PASS, `Resolved 298 packages` |
| Immutable upstream tag | `git rev-parse upstream/dsa-v3.26.1` -> `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a` |
| Diff hygiene | `git diff --check` -> PASS |

## Approval Record

This record approves the schema boundary as input to `SAL-P5-002` Evidence Store. Later P5 tasks must implement persistence, bundle construction, Quant evidence adapters, Agent stages, citation validation, model budgeting and renderers before Gate G5 can pass.
