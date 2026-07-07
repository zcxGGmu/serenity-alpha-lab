# Source Claim Traceability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Require manually ingested evidence to record a source excerpt so a valid URL cannot be used as unsupported claim cover.

**Architecture:** Add an optional `source_excerpt` field to the evidence schema while keeping existing JSONL backward-compatible. Enforce `source_excerpt` at manual intake time before append/refresh, and audit legacy/manual evidence that still lacks traceability.

**Tech Stack:** Python dataclasses, argparse CLI, pytest, JSONL evidence files.

---

### Task 1: Add Source Excerpt Contract Tests

**Files:**
- Modify: `tests/test_evidence_intake.py`
- Modify: `tests/test_cli.py`
- Modify: `tests/test_evidence_audit.py`

- [ ] **Step 1: Write failing intake unit tests**

```python
def test_build_intake_evidence_requires_source_excerpt():
    try:
        build_intake_evidence(
            item_id="manual:NVDA:risk:cpo-sourcing",
            source_title="Manual NVDA risk note",
            source_url="https://data.sec.gov/api/xbrl/companyfacts/CIK0001045810.json",
            published_at="2026-07-04",
            claim="NVDA faces CPO sourcing risk if optical component supply tightens.",
            summary="Manual intake captures a negative/risk item for NVDA CPO sourcing.",
            tickers=["NVDA"],
            themes=["CPO", "risk", "manual-intake"],
            supply_chain_layer="AI accelerator customer",
            direction="negative",
            strength="derived",
            confidence=0.72,
            factor_impacts={"evidence_quality": 8},
            claim_type="risk",
            source_excerpt="",
        )
    except ValueError as exc:
        assert "source excerpt" in str(exc).lower()
    else:
        raise AssertionError("manual intake should require source excerpt")
```

- [ ] **Step 2: Write failing CLI guardrail test**

```python
def test_cli_ingest_task_evidence_rejects_missing_source_excerpt_before_refresh(tmp_path):
    intake = tmp_path / "manual_intake.jsonl"
    readiness = tmp_path / "readiness.md"
    pack_dir = tmp_path / "pack"

    try:
        main([... valid ingest-task-evidence args without --source-excerpt ...])
    except ValueError as exc:
        assert "source excerpt" in str(exc).lower()
    else:
        raise AssertionError("missing source excerpt should be rejected")

    assert not intake.exists()
    assert not readiness.exists()
    assert not (pack_dir / "index.md").exists()
```

- [ ] **Step 3: Write failing audit traceability test**

```python
def test_audit_flags_manual_intake_without_source_excerpt():
    report = audit_evidence([make_item("manual:NVDA:risk:cpo-sourcing", tickers=("NVDA",))])
    assert any(flag.code == "manual_intake_missing_source_excerpt" for flag in report.flags)
```

- [ ] **Step 4: Run tests to verify red**

Run:

```bash
python3 -m pytest tests/test_evidence_intake.py tests/test_cli.py::test_cli_ingest_task_evidence_rejects_missing_source_excerpt_before_refresh tests/test_evidence_audit.py::test_audit_flags_manual_intake_without_source_excerpt -q
```

Expected: FAIL because `source_excerpt` is not supported and audit does not flag missing traceability.

### Task 2: Implement Traceability Guardrail

**Files:**
- Modify: `src/serenity_alpha_lab/evidence.py`
- Modify: `src/serenity_alpha_lab/evidence_intake.py`
- Modify: `src/serenity_alpha_lab/cli.py`
- Modify: `src/serenity_alpha_lab/evidence_audit.py`

- [ ] **Step 1: Extend evidence schema compatibly**

Add `source_excerpt: str = ""` to `EvidenceItem`, parse optional `source_excerpt`, and write it only when non-empty.

- [ ] **Step 2: Enforce source excerpt in intake**

Add `validate_source_excerpt(source_excerpt)` and call it from `build_intake_evidence()` before schema parsing. Require at least 24 non-whitespace characters.

- [ ] **Step 3: Add CLI argument**

Add required `--source-excerpt` to `ingest-task-evidence` and pass it into `build_intake_evidence()`.

- [ ] **Step 4: Add audit flag**

Flag manual intake evidence whose id starts with `manual:` or theme contains `manual-intake` when `source_excerpt` is empty.

- [ ] **Step 5: Run target tests to verify green**

Run:

```bash
python3 -m pytest tests/test_evidence_intake.py tests/test_cli.py::test_cli_ingest_task_evidence_rejects_missing_source_excerpt_before_refresh tests/test_cli.py::test_cli_ingest_task_evidence_writes_intake_and_refreshes_outputs tests/test_evidence_audit.py::test_audit_flags_manual_intake_without_source_excerpt -q
```

Expected: PASS.

### Task 3: Regenerate Guarded Outputs And Verify

**Files:**
- Modify: `data/enriched/manual_intake_guarded.jsonl`
- Modify: `output/reports/cpo-readiness-guarded.md`
- Modify: `output/packs/cpo-guarded/`
- Modify: `tasks/todo.md`

- [ ] **Step 1: Re-run guarded intake with source excerpt**

Run:

```bash
PYTHONPATH=src python3 -m serenity_alpha_lab.cli ingest-task-evidence ... --source-excerpt "Trace note: SEC companyfacts URL validates the issuer identity; manual risk claim requires analyst verification against filings or cited market sources."
```

- [ ] **Step 2: Run full tests**

Run:

```bash
python3 -m pytest tests -q
```

Expected: all tests pass.

- [ ] **Step 3: Record review evidence**

Append red/green/full verification outputs to `tasks/todo.md`.
