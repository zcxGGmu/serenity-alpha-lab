# Evidence Claim Report Schema Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Define the SAL-P5-001 Evidence, Citation, Claim and ResearchReport schema contracts so later Evidence Store, Quant Evidence Adapter, Agent stages and Citation Validator all share one versioned boundary.

**Architecture:** Add a pure `serenity_alpha_lab.evidence.schema` module using Pydantic v2 models for schema generation and runtime validation, while preserving the project’s existing JSON-friendly `to_record()` contract style. Keep the module free of FastAPI, Qlib, LiteLLM, Provider runtimes, Worker code and DSA runtime imports. Encode P3 Screen/Factor and P4 formal backtest source kinds as explicit enums and mapping records so Screen/Factor outputs cannot be mislabeled as formal portfolio backtests.

**Tech Stack:** Python 3.11, Pydantic v2, pytest, existing `ArtifactManifest` and Dataset Version conventions.

---

### Task 1: Red Contract Tests

**Files:**
- Create: `tests/evidence/test_evidence_schema_contract.py`

- [ ] **Step 1: Write failing tests for schema fields and source mapping**

```python
from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from serenity_alpha_lab.evidence.schema import (
    ClaimComputationPolicy,
    ClaimKind,
    ClaimVerificationStatus,
    EvidenceKind,
    EvidenceRecord,
    EvidenceSource,
    EvidenceTrustLevel,
    EvidenceEvaluationScope,
    ResearchReport,
    ResearchReportLevel,
    ReportCitation,
    ResearchClaim,
    quant_evidence_source_matrix,
)


NOW = datetime(2026, 7, 26, 15, 0, tzinfo=UTC)
HASH = "sha256:" + "a" * 64


def test_evidence_record_declares_required_schema_fields_and_json_schema() -> None:
    evidence = EvidenceRecord(
        evidence_id="ev_screen_snapshot_001",
        kind=EvidenceKind.SCREEN_SNAPSHOT,
        evaluation_scope=EvidenceEvaluationScope.SCREENING,
        title="Screen snapshot passed rows",
        summary="ScreenSnapshot includes ranked passed and failed rows.",
        source=EvidenceSource(
            source_id="ssn_11111111111111111111111111111111",
            source_type="artifact",
            schema_name="quant.screen_snapshot",
            schema_version="1.0.0",
        ),
        available_at=NOW,
        content_hash=HASH,
        trust=EvidenceTrustLevel.AUTHORITATIVE,
        dataset_versions={"universe": "dsv_" + "1" * 32},
        run_id="run-screen",
        stage_id="stage-screen",
        artifact_id="art_screen",
        artifact_hash=HASH,
    )

    record = evidence.to_record()
    assert record["schema_name"] == "research.evidence"
    assert record["schema_version"] == "1.0.0"
    assert record["source"]["source"] == "artifact"
    assert record["available_at"] == NOW.isoformat()
    assert record["content_hash"] == HASH
    assert record["trust"] == "authoritative"
    assert record["dataset_versions"] == {"universe": "dsv_" + "1" * 32}
    assert "properties" in EvidenceRecord.model_json_schema()


def test_evidence_rejects_latest_dataset_and_screen_as_formal_backtest() -> None:
    base = {
        "evidence_id": "ev_bad_scope",
        "kind": EvidenceKind.SCREEN_SNAPSHOT,
        "evaluation_scope": EvidenceEvaluationScope.FORMAL_PORTFOLIO_BACKTEST,
        "title": "Bad formal label",
        "summary": "Screen result is not a formal portfolio backtest.",
        "source": EvidenceSource(
            source_id="ssn_22222222222222222222222222222222",
            source_type="artifact",
            schema_name="quant.screen_snapshot",
            schema_version="1.0.0",
        ),
        "available_at": NOW,
        "content_hash": HASH,
        "trust": EvidenceTrustLevel.AUTHORITATIVE,
        "dataset_versions": {"universe": "dsv_" + "2" * 32},
    }

    with pytest.raises(ValidationError, match="formal portfolio backtest"):
        EvidenceRecord(**base)

    latest_payload = dict(base)
    latest_payload["evaluation_scope"] = EvidenceEvaluationScope.SCREENING
    latest_payload["dataset_versions"] = {"universe": "latest"}
    with pytest.raises(ValidationError, match="concrete Dataset Version"):
        EvidenceRecord(**latest_payload)


def test_numeric_claim_requires_citations_unit_formula_and_deterministic_policy() -> None:
    with pytest.raises(ValidationError, match="citation_ids"):
        ResearchClaim(
            claim_id="cl_no_citation",
            kind=ClaimKind.NUMERIC_METRIC,
            statement="The backtest cumulative return was 2.466%.",
            verification_status=ClaimVerificationStatus.VERIFIED,
            citation_ids=[],
            value="0.024660",
            unit="ratio",
            formula_version="cumulative_return@1.0.0",
            computation_policy=ClaimComputationPolicy.DETERMINISTIC_EVIDENCE,
        )

    with pytest.raises(ValidationError, match="LLM"):
        ResearchClaim(
            claim_id="cl_llm_numeric",
            kind=ClaimKind.NUMERIC_METRIC,
            statement="The backtest cumulative return was 2.466%.",
            verification_status=ClaimVerificationStatus.VERIFIED,
            citation_ids=["cit_metric"],
            value="0.024660",
            unit="ratio",
            formula_version="cumulative_return@1.0.0",
            computation_policy=ClaimComputationPolicy.LLM_NARRATIVE,
        )


def test_report_validates_citation_graph_and_decision_time() -> None:
    evidence = EvidenceRecord(
        evidence_id="ev_metric",
        kind=EvidenceKind.BACKTEST_PERFORMANCE_METRICS,
        evaluation_scope=EvidenceEvaluationScope.FORMAL_PORTFOLIO_BACKTEST,
        title="Backtest metric report",
        summary="Cumulative return is sourced from BacktestPerformanceMetricReport.",
        source=EvidenceSource(
            source_id="btm_metric_report",
            source_type="artifact",
            schema_name="quant.backtest.performance_metrics",
            schema_version="1.0.0",
        ),
        available_at=NOW,
        content_hash=HASH,
        trust=EvidenceTrustLevel.AUTHORITATIVE,
        dataset_versions={"bars": "dsv_" + "3" * 32},
        run_id="run-backtest",
        stage_id="stage-metrics",
        artifact_id="art_metrics",
        artifact_hash=HASH,
    )
    citation = ReportCitation(
        citation_id="cit_metric",
        evidence_id=evidence.evidence_id,
        evidence_field_path="metrics.cumulative_return",
        cited_value="0.024660",
        unit="ratio",
        formula_version="cumulative_return@1.0.0",
        artifact_hash=HASH,
    )
    claim = ResearchClaim(
        claim_id="cl_metric",
        kind=ClaimKind.NUMERIC_METRIC,
        statement="The formal portfolio backtest cumulative return was 2.466%.",
        verification_status=ClaimVerificationStatus.VERIFIED,
        citation_ids=[citation.citation_id],
        value="0.024660",
        unit="ratio",
        formula_version="cumulative_return@1.0.0",
        computation_policy=ClaimComputationPolicy.DETERMINISTIC_EVIDENCE,
    )

    report = ResearchReport(
        report_id="rpt_verified",
        report_level=ResearchReportLevel.VERIFIED,
        decision_time=NOW,
        evidence=[evidence],
        citations=[citation],
        claims=[claim],
        dataset_versions={"bars": "dsv_" + "3" * 32},
    )

    assert report.to_record()["report_level"] == "verified"
    assert report.to_record()["claims"][0]["citation_ids"] == ["cit_metric"]

    stale = evidence.model_copy(update={"available_at": datetime(2026, 7, 27, 9, 30, tzinfo=UTC)})
    with pytest.raises(ValidationError, match="available_at"):
        ResearchReport(
            report_id="rpt_stale",
            report_level=ResearchReportLevel.VERIFIED,
            decision_time=NOW,
            evidence=[stale],
            citations=[citation],
            claims=[claim],
            dataset_versions={"bars": "dsv_" + "3" * 32},
        )


def test_quant_evidence_source_matrix_freezes_p3_p4_mapping_and_excludes_legacy() -> None:
    matrix = quant_evidence_source_matrix()
    kinds = {row["kind"] for row in matrix}

    assert "screen_snapshot" in kinds
    assert "factor_evaluation" in kinds
    assert "backtest_run_summary" in kinds
    assert "backtest_artifact_bundle" in kinds
    assert "risk_policy_result" in kinds
    assert "backtest_bias_audit" in kinds
    assert "backtest_performance_metrics" in kinds
    assert "formal_backtest_api_record" in kinds
    assert "quant_lab_lineage" in kinds
    assert "legacy_signal_evaluation" not in kinds
    assert "qlib_internal_evidence" not in kinds
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --extra core --extra dev python -m pytest tests/evidence/test_evidence_schema_contract.py -q`
Expected: FAIL with missing `serenity_alpha_lab.evidence.schema`.

### Task 2: Evidence Schema Implementation

**Files:**
- Create: `src/serenity_alpha_lab/evidence/schema.py`
- Modify: `src/serenity_alpha_lab/evidence/__init__.py`

- [ ] **Step 1: Add Pydantic schema models**

Implement:
- `EvidenceRecord`, `EvidenceSource`, `ReportCitation`, `ResearchClaim`, `ResearchReport`
- enums for evidence kind, evaluation scope, trust, claim kind, verification status, computation policy and report level
- `to_record()` helpers and JSON Schema export helper
- validators for concrete `dsv_*` Dataset Version ids, SHA-256 hashes, timezone-aware `available_at`, formal portfolio backtest source scopes, numeric claim citations/unit/formula version and report citation graph integrity

- [ ] **Step 2: Export public API**

Update `src/serenity_alpha_lab/evidence/__init__.py` to export the schema classes, constants and mapping helper.

- [ ] **Step 3: Run focused test to verify it passes**

Run: `uv run --extra core --extra dev python -m pytest tests/evidence/test_evidence_schema_contract.py -q`
Expected: PASS.

### Task 3: Documentation And Progress State

**Files:**
- Create: `docs/evidence-claim-report-schema.md`
- Modify: `docs/development-progress-checklist.md`
- Modify: `docs/development-status.md`
- Modify: `tasks/todo.md`

- [ ] **Step 1: Document SAL-P5-001 schema**

Record schema names, versions, fields, source mapping, Claim rules, report levels, non-goals and verification evidence in `docs/evidence-claim-report-schema.md`.

- [ ] **Step 2: Update progress checklist**

Mark only `SAL-P5-001` as `DONE`, update P5 to `1/18`, total to `89/129`, add `DEC-087` and `AEV-089`, and set next READY task to `SAL-P5-002`.

- [ ] **Step 3: Update status snapshot**

Update current task, completion range, checkpoint placeholders and next startup prompt to point to `SAL-P5-002`; keep G5 as not passed and preserve all Gate G4 constraints.

- [ ] **Step 4: Update todo review**

Check off completed plan items and append verification results plus subagent fallback note.

### Task 4: Verification And Checkpoint

**Files:**
- No additional source edits expected unless verification exposes a defect.

- [ ] **Step 1: Run focused and related tests**

Run:
- `uv run --extra core --extra dev python -m pytest tests/evidence/test_evidence_schema_contract.py -q`
- `uv run --extra core --extra dev python -m pytest tests/evidence/test_evidence_schema_contract.py tests/architecture/test_architecture_boundaries.py -q`

- [ ] **Step 2: Run project verification**

Run:
- `uv run --extra core --extra dev python -m pytest -q`
- `uv run --extra core --extra dev python -m compileall -q src/serenity_alpha_lab tests`
- `scripts/verify-python-dependency-lock.sh`
- `git rev-parse upstream/dsa-v3.26.1`
- `git diff --check`

- [ ] **Step 3: Review and commit**

Run `git diff --stat`, `git status --short --branch`, stage only SAL-P5-001 files, and commit with Chinese checkpoint message:

```bash
git add src/serenity_alpha_lab/evidence/__init__.py src/serenity_alpha_lab/evidence/schema.py tests/evidence/test_evidence_schema_contract.py docs/evidence-claim-report-schema.md docs/development-progress-checklist.md docs/development-status.md docs/superpowers/plans/2026-07-26-evidence-claim-report-schema.md tasks/todo.md
git commit -m "feat(P5): 定义 Evidence Claim Report Schema" -m "完成内容：
- 冻结 Evidence、Citation、Claim 与 ResearchReport schema
- 建立 P3/P4 量化证据源映射和 JSON Schema 导出
- 同步 SAL-P5-001 状态、证据、风险与下次恢复提示

兼容性与风险：
- 不启动 Evidence Agent、真实 Provider/LLM、Worker loop 或 Qlib runtime
- 保持 Signal Evaluation、Factor Evaluation、Screen result 与 formal portfolio backtest 语义隔离

验证：
- uv run --extra core --extra dev python -m pytest ...
- compileall、dependency lock、immutable tag、diff checks

关联任务：SAL-P5-001, Gate G5"
```
