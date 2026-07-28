# Citation Validator

> Task: `SAL-P5-013` Implement Citation Validator<br>
> Date: 2026-07-28<br>
> Status: `APPROVED FOR SAL-P5-014 / SAL-P5-015 INPUT ONLY`

## Conclusion

`SAL-P5-013` adds a pure offline citation validation boundary:

```text
src/serenity_alpha_lab/evidence/citation_validator.py
tests/evidence/test_citation_validator.py
```

The validator consumes already-constructed `ResearchReport`, `ResearchClaim`, `ReportCitation` and `EvidenceRecord` schema objects. It verifies the report reference graph, mandatory citations, deterministic numeric lineage, decision-time availability and one-attempt repair behavior. If a claim still fails after the single caller-supplied repair attempt, the claim is removed from the validated report and the report is downgraded.

This task does not read Evidence bodies, call Providers or LLMs, run Agent stages, write Evidence Store, start Worker loops, initialize Qlib, render reports, schedule production work or promote formal portfolio backtests.

## Contracts

| Item | Contract |
|---|---|
| Citation Validator contract | `research.citation_validator@1.0.0` |
| Result schema | `research.citation_validation_result` / `1.0.0` |
| Validator | `CitationValidator` |
| Result wrapper | `CitationValidationResult` |
| Issue record | `CitationValidationIssue` |
| Issue codes | `CitationValidationIssueCode` |
| Error | `CitationValidatorError` |

## Mandatory Citation Policy

The validator requires citations for deterministic or value-bearing claim kinds:

- `numeric_metric`
- `temporal_fact`
- `risk_gate`
- `lineage_fact`

`numeric_metric` claims must use `ClaimComputationPolicy.DETERMINISTIC_EVIDENCE`. LLM narrative remains disallowed for numeric metrics by the base schema and is also rejected by the validator if a caller constructs an invalid object through another path.

## Consistency Checks

The validator checks:

- every citation references evidence included in the same report
- cited evidence `available_at` is no later than report `decision_time`
- every claim citation id exists in the report citations
- citation dataset versions, run id, stage id and artifact hash match the cited EvidenceRecord when those lineage fields are present
- citation formula version belongs to cited EvidenceRecord formula versions when evidence declares formulas
- numeric claim value, unit, formula version, dataset versions, run id, stage id and artifact hash match the deterministic citation
- risk, temporal, lineage and qualitative claims match citation `cited_value` when both sides expose a value

Failed claims are downgraded to a non-verified status such as `citation_missing`, `value_mismatch`, `insufficient_evidence` or `rejected`. Failed claims are never left as `verified`.

## Repair Behavior

`CitationValidator.validate(report)` performs a single offline validation pass and returns:

- a validated `ResearchReport` copy
- deterministic issue records
- downgraded failed claims
- final report level

`CitationValidator.validate_with_repair(report, repair_attempt=...)` first validates the original report. If the original has failures and the caller provides exactly one repaired report attempt, the validator evaluates that repaired report. Claims still failing after that attempt are removed from the final validated report and recorded in `removed_claim_ids`; the report level is downgraded to `partial` or `insufficient_evidence`.

The validator does not generate the repair attempt. Later runtime layers may decide how to produce one, but this boundary only evaluates caller-provided structured reports.

## Non-Goals

- No LLM repair loop, model invocation, LiteLLM import, Provider call or live search/news fetch.
- No Evidence Store writes, Evidence body reads, EvidenceBundle construction or Quant Evidence Adapter execution.
- No Agent stage execution, AgentStageStore receipt writes or Worker runtime.
- No report renderer, Markdown/HTML generation, notification workflow or publication.
- No Qlib runtime, production scheduling or formal portfolio backtest promotion.

## Verification

| Check | Result |
|---|---|
| Red target | `uv run --extra core --extra dev python -m pytest tests/evidence/test_citation_validator.py -q` initially failed with `ModuleNotFoundError: No module named 'serenity_alpha_lab.evidence.citation_validator'` |
| Initial focused target | `uv run --extra core --extra dev python -m pytest tests/evidence/test_citation_validator.py -q` -> `3 passed` |
| Review regression Red | `uv run --extra core --extra dev python -m pytest tests/evidence/test_citation_validator.py -q` -> `1 failed, 4 passed`, proving citation/evidence lineage issues were not yet attached to consuming claims |
| Focused target | `uv run --extra core --extra dev python -m pytest tests/evidence/test_citation_validator.py -q` -> `7 passed` |
| Architecture guard | `uv run --extra core --extra dev python -m pytest tests/architecture/test_architecture_boundaries.py::test_citation_validator_stays_offline_and_runtime_free -q` -> `1 passed` |
| Related P5 suite | `uv run --extra core --extra dev python -m pytest tests/evidence/test_citation_validator.py tests/evidence/test_evidence_schema_contract.py tests/evidence/test_quant_evidence_adapter.py tests/application/test_technical_agent_evidence_adapter.py tests/application/test_intel_agent_evidence_adapter.py tests/application/test_risk_portfolio_agent_evidence_adapter.py tests/application/test_decision_agent_counterargument_synthesis.py tests/architecture/test_architecture_boundaries.py -q` -> `59 passed` |
| Full suite | `uv run --extra core --extra dev python -m pytest -q` -> `474 passed, 3 skipped` |
| Compile | `uv run --extra core --extra dev python -m compileall -q src/serenity_alpha_lab tests` -> PASS |
| Dependency lock | `scripts/verify-python-dependency-lock.sh` -> PASS, `Resolved 298 packages` |
| Immutable upstream tag | `git rev-parse upstream/dsa-v3.26.1` -> `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a` |
| Diff hygiene | `git diff --check` -> PASS |

## Approval Record

This record approves offline citation validation, deterministic issue reporting, claim downgrading and one-attempt repair deletion as input to `SAL-P5-014` Agent tool security and `SAL-P5-015` trusted ResearchReport rendering. Later P5 tasks must still implement tool runtime security, trusted report rendering, UI/notification surfaces and Worker runtime before Gate G5 can pass.
