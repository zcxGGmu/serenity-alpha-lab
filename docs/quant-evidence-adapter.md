# Quant Evidence Adapter

> Task: `SAL-P5-005` Implement Quant Evidence Adapter<br>
> Date: 2026-07-26<br>
> Status: `APPROVED FOR SAL-P5-006 INPUT ONLY`

## Conclusion

`SAL-P5-005` adds a pure offline Quant Evidence Adapter:

```text
src/serenity_alpha_lab/evidence/quant_adapter.py
tests/evidence/test_quant_evidence_adapter.py
```

The adapter converts already-produced Screen, Factor, Backtest Metrics, Risk Policy and Bias Audit DTOs into P5 `EvidenceRecord` metadata plus deterministic `ReportCitation` values. It preserves concrete Dataset Version ids, Artifact id/hash, source schema, run/stage/trace lineage, formula versions and deterministic citation paths so later LLM stages can cite evidence instead of recomputing metrics.

This task maps existing DTOs only. It does not run Qlib, compute factors or backtests, call Providers or LLMs, start Worker loops, persist to Evidence Store, build EvidenceBundles, validate report citations, render reports, schedule production work or promote formal portfolio backtests.

## Contracts

| Item | Contract |
|---|---|
| Adapter contract | `research.quant_evidence_adapter@1.0.0` |
| Adapter schema | `research.quant_evidence_adapter` / `1.0.0` |
| Adapter | `QuantEvidenceAdapter.default()` |
| Output wrapper | `QuantEvidenceAdapterRecord` |
| Error | `QuantEvidenceAdapterError` |
| Required trace input | caller-provided `ArtifactManifest` whose SHA-256 matches canonical DTO body JSON |

## Mapping

| Source DTO | Evidence kind | Scope | Source schema | Numeric citation policy |
|---|---|---|---|---|
| `ScreenSnapshot` | `screen_snapshot` | `screening` | `quant.screen_snapshot` | Passed instrument `final_score` paths include `score` unit and `screen_definition:<version>` formula |
| `FactorEvaluationReport` | `factor_evaluation` | `factor_evaluation` | `quant.factor_evaluation` | IC, ICIR, long/short return, monotonicity and turnover paths use metric set / future-return versions |
| `BacktestPerformanceMetricReport` | `backtest_performance_metrics` | `formal_portfolio_backtest` | `quant.backtest.performance_metrics` | Scalar returns, risk, drawdown, trading, cost and benchmark metrics use registry formula versions |
| `RiskPolicyResult` | `risk_policy_result` | `formal_portfolio_backtest` | `quant.backtest.risk_policy` | Status and rule observed/limit values cite deterministic risk evaluator and policy version |
| `BacktestBiasAuditReport` | `backtest_bias_audit` | `formal_portfolio_backtest` | `quant.backtest.bias_audit` | Status and rule observed/limit values cite deterministic bias auditor and policy version |

Screen and Factor outputs remain outside `formal_portfolio_backtest`. Formal scope remains limited to Gate G4-approved Backtest Metrics, Risk Policy and Bias Audit records.

## Traceability

Every adapter method requires an `ArtifactManifest` and verifies that `manifest.sha256` matches the canonical JSON body produced from `to_record()`. The resulting `EvidenceRecord.content_hash` and `artifact_hash` use the same `sha256:<digest>` value, while `artifact_id`, source URI, run/stage ids and trace ids remain attached for downstream Evidence Store and report citation workflows.

`ReportCitation` values use stable `body...` field paths and carry dataset versions, artifact hash, run id, stage id, unit and formula version where applicable. Adapter metadata sets `llm_recompute_allowed=false` to make the no-recompute boundary machine-readable.

## Non-Goals

- No Evidence Store writes, body persistence, revision handling or access control.
- No EvidenceBundle construction, role-specific ranking, token budgeting or prompt payload generation.
- No Prompt/Output Schema Registry, Agent stage, model routing, cache, budget execution or citation repair loop.
- No Qlib runtime, factor/backtest calculation, Provider/LLM calls, Worker loop, production scheduler, report renderer or notification workflow.
- No relabeling of Screen, Factor, Qlib internal evidence, Dataset conversion artifacts, AlphaSift T+N evaluation or legacy Signal Evaluation as formal portfolio backtest output.

## Verification

| Check | Result |
|---|---|
| Red target | `uv run --extra core --extra dev python -m pytest tests/evidence/test_quant_evidence_adapter.py -q` initially failed with `ModuleNotFoundError: No module named 'serenity_alpha_lab.evidence.quant_adapter'`; later audit coverage failed with missing `from_backtest_bias_audit_report` |
| Focused target | `uv run --extra core --extra dev python -m pytest tests/evidence/test_quant_evidence_adapter.py -q` -> `3 passed` |
| Related suite | `uv run --extra core --extra dev python -m pytest tests/evidence/test_quant_evidence_adapter.py tests/evidence/test_evidence_schema_contract.py tests/evidence/test_source_trust_cleaning.py tests/repositories/test_evidence_store.py tests/application/test_evidence_bundle_builder.py tests/architecture/test_architecture_boundaries.py -q` -> `37 passed` |
| Full suite | `uv run --extra core --extra dev python -m pytest -q` -> `427 passed, 3 skipped` |
| Compile | `uv run --extra core --extra dev python -m compileall -q src/serenity_alpha_lab tests` -> PASS |
| Dependency lock | `scripts/verify-python-dependency-lock.sh` -> PASS, `Resolved 298 packages` |
| Immutable upstream tag | `git rev-parse upstream/dsa-v3.26.1` -> `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a` |
| Diff hygiene | `git diff --check` -> PASS |

## Approval Record

This record approves offline Quant evidence mapping as input to `SAL-P5-006` Prompt/Output Schema Registry and later Citation Validator work. Later P5 tasks must still implement prompt/schema registry, Agent stages, citation validation, model budgeting and renderers before Gate G5 can pass.
