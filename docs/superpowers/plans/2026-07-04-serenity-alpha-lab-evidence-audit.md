# Serenity Alpha Lab Evidence Audit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an evidence audit quality gate that summarizes corpus health and flags weak spots before research memo generation.

**Architecture:** Add a pure `evidence_audit` module that accepts loaded `EvidenceItem` objects and returns an auditable report model. Expose the report through an `audit-evidence` CLI subcommand that writes concise Markdown to `output/reports/`.

**Tech Stack:** Python stdlib, existing `EvidenceItem` model, argparse CLI, pytest.

---

### Task 1: Audit Model And Report Tests

**Files:**
- Create: `tests/test_evidence_audit.py`
- Create: `src/serenity_alpha_lab/evidence_audit.py`

- [ ] **Step 1: Write failing audit tests**

```python
from datetime import date

from serenity_alpha_lab.evidence import EvidenceItem
from serenity_alpha_lab.evidence_audit import audit_evidence, render_audit_markdown


def item(
    item_id,
    *,
    tickers=("SERENITY",),
    source_title="repo one",
    claim_type="inference",
    direction="positive",
    strength="derived",
    summary="A sufficiently descriptive evidence summary.",
):
    return EvidenceItem(
        id=item_id,
        source_title=source_title,
        source_url="https://example.com",
        published_at=date(2026, 1, 1),
        claim="Claim",
        summary=summary,
        tickers=tickers,
        themes=("CPO",),
        supply_chain_layer="component",
        direction=direction,
        strength=strength,
        confidence=0.7,
        factor_impacts={"demand_certainty": 1},
        claim_type=claim_type,
    )


def test_audit_counts_distributions_and_flags_quality_issues():
    report = audit_evidence(
        [
            item("a", source_title="repo one", claim_type="methodology", strength="speculative", summary="short"),
            item("b", source_title="repo one", claim_type="methodology"),
            item("c", source_title="repo one", claim_type="risk", direction="negative"),
            item("d", source_title="repo two", tickers=("SIVE",), claim_type="catalyst"),
        ],
        focus_ticker="SIVE",
    )

    assert report.total_count == 4
    assert report.claim_type_counts["methodology"] == 2
    assert report.ticker_counts["SERENITY"] == 3
    assert report.source_counts["repo one"] == 3
    assert any(flag.code == "placeholder_ticker_concentration" for flag in report.flags)
    assert any(flag.code == "source_concentration" for flag in report.flags)
    assert any(flag.code == "short_summary" for flag in report.flags)


def test_render_audit_markdown_includes_next_fixes():
    report = audit_evidence(
        [item("a", claim_type="methodology"), item("b", claim_type="methodology")],
        focus_ticker="SIVE",
    )

    markdown = render_audit_markdown(report)

    assert "# Evidence Audit Report" in markdown
    assert "## Quality Flags" in markdown
    assert "## Next Fixes" in markdown
    assert "SIVE" in markdown
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_evidence_audit.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'serenity_alpha_lab.evidence_audit'`.

- [ ] **Step 3: Implement audit module**

Implement `AuditFlag`, `EvidenceAuditReport`, `audit_evidence()`, and `render_audit_markdown()` in `src/serenity_alpha_lab/evidence_audit.py`.

- [ ] **Step 4: Run audit tests**

Run: `python3 -m pytest tests/test_evidence_audit.py -q`
Expected: PASS.

### Task 2: CLI Subcommand

**Files:**
- Modify: `src/serenity_alpha_lab/cli.py`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Write failing CLI test**

Add a test that calls `main(["audit-evidence", "--data", fixture, "--out", output, "--ticker", "SIVE"])` and asserts the output Markdown contains `Evidence Audit Report`, `Quality Flags`, and `Next Fixes`.

- [ ] **Step 2: Run CLI test to verify it fails**

Run: `python3 -m pytest tests/test_cli.py::test_cli_audit_evidence_writes_report -q`
Expected: FAIL because `audit-evidence` is not implemented.

- [ ] **Step 3: Implement CLI subcommand**

Add `build_audit_parser()` and route `audit-evidence` before memo mode in `main()`.

- [ ] **Step 4: Run CLI test**

Run: `python3 -m pytest tests/test_cli.py::test_cli_audit_evidence_writes_report -q`
Expected: PASS.

### Task 3: Real Report And Verification

**Files:**
- Create: `output/reports/evidence-audit.md`
- Modify: `tasks/todo.md`

- [ ] **Step 1: Generate real audit report**

Run: `PYTHONPATH=src python3 -m serenity_alpha_lab.cli audit-evidence --data data/imported/github_evidence.jsonl --ticker SIVE --out output/reports/evidence-audit.md`
Expected: Markdown report exists and includes corpus distributions plus quality flags.

- [ ] **Step 2: Run full test suite**

Run: `python3 -m pytest tests -q`
Expected: all tests pass.

- [ ] **Step 3: Record review notes**

Append the exact verification command output and the generated report path to `tasks/todo.md`.
