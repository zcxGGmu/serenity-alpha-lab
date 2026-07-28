# Citation Validator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement `SAL-P5-013` as an offline Citation Validator that verifies claim/citation/evidence consistency, enforces mandatory citations for deterministic facts, and downgrades/removes still-broken claims after one repair attempt.

**Architecture:** Add a pure evidence-layer module that consumes existing `ResearchReport`, `ResearchClaim`, `ReportCitation` and `EvidenceRecord` objects. The validator produces a deterministic validation result plus a structured report copy; it does not read Evidence bodies, call models, repair with LLMs, render reports or start runtime workflows.

**Tech Stack:** Python dataclasses/enums, existing P5 Evidence schema models, pytest, architecture import guards.

---

### Task 1: Red Tests For Mandatory Citations And Consistency

**Files:**
- Create: `tests/evidence/test_citation_validator.py`

- [ ] **Step 1: Write verified-report pass test**

```python
def test_citation_validator_accepts_verified_report_with_consistent_claims() -> None:
    report = _report(claims=(_numeric_claim(), _temporal_claim()), citations=(_metric_citation(), _temporal_citation()))
    result = CitationValidator().validate(report)
    assert result.report_level is ResearchReportLevel.VERIFIED
    assert result.issue_count == 0
    assert [claim.claim_id for claim in result.validated_report.claims] == ["cl_metric", "cl_temporal"]
```

- [ ] **Step 2: Write mandatory-citation and value mismatch tests**

```python
def test_citation_validator_downgrades_missing_temporal_or_mismatched_numeric_claims() -> None:
    report = _report(claims=(_numeric_claim(value="0.99"), _temporal_claim(citation_ids=())), citations=(_metric_citation(),))
    result = CitationValidator().validate(report)
    assert result.report_level is ResearchReportLevel.PARTIAL
    assert {issue.code for issue in result.issues} == {CitationValidationIssueCode.VALUE_MISMATCH, CitationValidationIssueCode.MISSING_CITATION}
    assert all(claim.verification_status is not ClaimVerificationStatus.VERIFIED for claim in result.failed_claims)
```

- [ ] **Step 3: Write one-attempt repair deletion test**

```python
def test_citation_validator_removes_claim_after_one_failed_repair_attempt() -> None:
    original = _report(claims=(_numeric_claim(value="0.99"), _risk_claim()), citations=(_metric_citation(), _risk_citation()))
    repaired = _report(claims=(_numeric_claim(value="0.88"), _risk_claim()), citations=(_metric_citation(), _risk_citation()))
    result = CitationValidator().validate_with_repair(original, repair_attempt=repaired)
    assert result.removed_claim_ids == ("cl_metric",)
    assert [claim.claim_id for claim in result.validated_report.claims] == ["cl_risk"]
    assert result.validated_report.report_level is ResearchReportLevel.PARTIAL
```

- [ ] **Step 4: Run Red target**

Run: `uv run --extra core --extra dev python -m pytest tests/evidence/test_citation_validator.py -q`

Expected: FAIL during collection with `ModuleNotFoundError: No module named 'serenity_alpha_lab.evidence.citation_validator'`.

### Task 2: Implement Offline Citation Validator

**Files:**
- Create: `src/serenity_alpha_lab/evidence/citation_validator.py`
- Modify: `src/serenity_alpha_lab/evidence/__init__.py`

- [ ] **Step 1: Add dataclass contracts**

Implement:
- `CITATION_VALIDATOR_CONTRACT_VERSION = "research.citation_validator@1.0.0"`
- `CitationValidationIssueCode`
- `CitationValidationSeverity`
- `CitationValidationIssue`
- `CitationValidationResult`
- `CitationValidator`
- `CitationValidatorError`

- [ ] **Step 2: Implement report scan**

Rules:
- every citation references included evidence
- evidence `available_at <= report.decision_time`
- `numeric_metric`, `temporal_fact`, `risk_gate` and `lineage_fact` require citation ids
- every claim citation id exists
- citation dataset versions, run id, stage id and artifact hash must match evidence lineage when present
- numeric claims use `deterministic_evidence` and match citation value/unit/formula/dataset/run/stage/artifact
- value-bearing temporal/risk/lineage/qualitative claims match citation `cited_value` when present

- [ ] **Step 3: Implement downgrade and repair result building**

Rules:
- `validate(report)` returns a report copy where failed claims are no longer `verified`; report level is `verified`, `partial` or `insufficient_evidence` based on surviving verified claims and failures.
- `validate_with_repair(report, repair_attempt=...)` validates the original, validates one repair attempt if needed, and removes still-failing claims from the final report.
- removed claim ids and issue records must be deterministic and sorted by claim/report order.

- [ ] **Step 4: Export public symbols**

Add imports and `__all__` entries in `src/serenity_alpha_lab/evidence/__init__.py`.

- [ ] **Step 5: Run focused Green target**

Run: `uv run --extra core --extra dev python -m pytest tests/evidence/test_citation_validator.py -q`

Expected: PASS.

### Task 3: Documentation And Architecture Guard

**Files:**
- Modify: `tests/architecture/test_architecture_boundaries.py`
- Create: `docs/citation-validator.md`

- [ ] **Step 1: Add architecture guard**

Allow only stdlib modules plus:
- `serenity_alpha_lab.evidence.schema`

Forbidden roots include `litellm`, `fastapi`, `sqlalchemy`, `qlib`, `akshare`, `tushare`, `yfinance`, `baostock`, `efinance`.

- [ ] **Step 2: Add evidence document**

Document:
- contract and schema names
- mandatory citation policy
- consistency checks
- one-attempt repair and deletion behavior
- non-goals and strict runtime boundary
- verification table

- [ ] **Step 3: Run related suite**

Run: `uv run --extra core --extra dev python -m pytest tests/evidence/test_citation_validator.py tests/evidence/test_evidence_schema_contract.py tests/evidence/test_quant_evidence_adapter.py tests/application/test_technical_agent_evidence_adapter.py tests/application/test_intel_agent_evidence_adapter.py tests/application/test_risk_portfolio_agent_evidence_adapter.py tests/application/test_decision_agent_counterargument_synthesis.py tests/architecture/test_architecture_boundaries.py -q`

Expected: PASS.

### Task 4: Status Sync And Checkpoint

**Files:**
- Modify: `docs/development-progress-checklist.md`
- Modify: `docs/development-status.md`
- Modify: `tasks/todo.md`

- [ ] **Step 1: Run full verification**

Run:
- `uv run --extra core --extra dev python -m pytest -q`
- `uv run --extra core --extra dev python -m compileall -q src/serenity_alpha_lab tests`
- `scripts/verify-python-dependency-lock.sh`
- `git rev-parse upstream/dsa-v3.26.1`
- `git diff --check`

Expected: all pass; upstream tag remains `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`.

- [ ] **Step 2: Update P5 records**

Update `SAL-P5-013` to `DONE`, add AEV-101 and DEC-099 entries, advance total progress to `101/129`, make `SAL-P5-014` the next READY task, and preserve strict no-runtime guardrails.

- [ ] **Step 3: Commit checkpoint**

Run:

```bash
git add src/serenity_alpha_lab/evidence/citation_validator.py src/serenity_alpha_lab/evidence/__init__.py tests/evidence/test_citation_validator.py tests/architecture/test_architecture_boundaries.py docs/citation-validator.md docs/superpowers/plans/2026-07-28-citation-validator.md docs/development-progress-checklist.md docs/development-status.md tasks/todo.md
git commit -m "feat(P5): 实现 Citation Validator"
```

Expected: Chinese checkpoint commit created for `SAL-P5-013`.
