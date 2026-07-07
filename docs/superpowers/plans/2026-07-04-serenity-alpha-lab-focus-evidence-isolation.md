# Focus Evidence Isolation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Keep direct ticker primary evidence separate from cross-ticker primary sector context in generated memos.

**Architecture:** Memo generation already identifies primary/fact evidence globally. This change keeps that classifier, then partitions primary evidence by whether the requested focus ticker appears in the item tickers. Focus-matching primary items remain under `## Primary Source Evidence`; non-focus primary items move to a new `## Sector Context Evidence` section and are still excluded from generic supporting evidence.

**Tech Stack:** Python 3, pytest, existing `EvidenceItem`, `generate_memo()`, and markdown rendering helpers.

---

## Files

- Modify: `tests/test_memo.py`
  - Add a regression test proving AAOI memos do not present SIVE annual-report facts as AAOI primary source evidence.
- Modify: `src/serenity_alpha_lab/memo.py`
  - Add focus ticker normalization and primary evidence partition helpers.
  - Render `## Sector Context Evidence` between primary evidence and supporting evidence.
- Modify: `tasks/todo.md`
  - Track red/green/product verification and final review notes for this phase.

### Task 1: Track The Phase

**Files:**
- Modify: `tasks/todo.md`

- [ ] **Step 1: Add phase checklist**

Append a new section:

```markdown
# Serenity Alpha Lab Focus Evidence Isolation Phase

- [ ] Create focus evidence isolation implementation plan.
- [ ] Add failing memo test for cross-ticker primary evidence separation.
- [ ] Implement focus primary and sector-context evidence rendering.
- [ ] Regenerate product outputs.
- [ ] Run full verification.
```

- [ ] **Step 2: Verify tracker contains the phase**

Run: `rg -n "Focus Evidence Isolation Phase" tasks/todo.md`

Expected: one matching heading.

### Task 2: Add Failing Memo Test

**Files:**
- Modify: `tests/test_memo.py`

- [ ] **Step 1: Write the failing test**

Add this test after `test_generate_memo_lists_primary_source_evidence_before_supporting_evidence`:

```python
def test_generate_memo_separates_cross_ticker_primary_evidence_from_focus_primary_section():
    aaoi_primary = EvidenceItem(...)
    sive_primary = EvidenceItem(...)
    aaoi_inference = EvidenceItem(...)
    score = score_research_question([aaoi_primary, sive_primary, aaoi_inference])

    memo = generate_memo(
        query="CPO revenue",
        ticker="AAOI",
        evidence=[aaoi_primary, sive_primary, aaoi_inference],
        score=score,
    )

    primary_section = memo.split("## Primary Source Evidence", 1)[1].split("## Sector Context Evidence", 1)[0]
    sector_context_section = memo.split("## Sector Context Evidence", 1)[1].split("## Supporting Evidence", 1)[0]
    supporting_section = memo.split("## Supporting Evidence", 1)[1].split("## Skeptic Review", 1)[0]

    assert "sec-companyfacts:AAOI:revenue" in primary_section
    assert "official-report:SIVE:net-sales-2025" not in primary_section
    assert "official-report:SIVE:net-sales-2025" in sector_context_section
    assert "official-report:SIVE:net-sales-2025" not in supporting_section
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_memo.py::test_generate_memo_separates_cross_ticker_primary_evidence_from_focus_primary_section -q`

Expected: FAIL because `## Sector Context Evidence` does not exist yet.

### Task 3: Implement Memo Evidence Partitioning

**Files:**
- Modify: `src/serenity_alpha_lab/memo.py`

- [ ] **Step 1: Add helpers**

Implement:

```python
def _normalize_ticker(ticker: str) -> str:
    return ticker.upper().lstrip("$")

def _focus_primary_evidence(items: List[EvidenceItem], ticker: str | None) -> List[EvidenceItem]:
    primary_items = _primary_evidence(items)
    if not ticker:
        return primary_items
    focus = _normalize_ticker(ticker)
    return [item for item in primary_items if focus in {_normalize_ticker(value) for value in item.tickers}]

def _sector_context_primary_evidence(items: List[EvidenceItem], ticker: str | None) -> List[EvidenceItem]:
    if not ticker:
        return []
    focus_ids = {item.id for item in _focus_primary_evidence(items, ticker)}
    return [item for item in _primary_evidence(items) if item.id not in focus_ids]
```

- [ ] **Step 2: Render sections**

In `generate_memo()`:

- Use `focus_primary_items` for `## Primary Source Evidence`.
- Render `sector_context_primary_items` under `## Sector Context Evidence`.
- Keep `primary_ids` as the union of both sections so supporting evidence does not duplicate primary/fact items.

- [ ] **Step 3: Run focused memo tests**

Run: `python3 -m pytest tests/test_memo.py -q`

Expected: all memo tests pass.

### Task 4: Regenerate And Verify Product Output

**Files:**
- Generated: `output/packs/cpo-guarded/*.md`
- Generated: `output/reports/cpo-readiness-guarded.md`

- [ ] **Step 1: Regenerate product pack**

Run: `PYTHONPATH=src python3 -m serenity_alpha_lab.cli run-cpo-pack`

Expected: `combined 182 evidence items; ready memos 6; skipped 0`.

- [ ] **Step 2: Verify AAOI memo partition**

Run a small Python/grep check confirming:

- `official-report:SIVE:net-sales-2025` is absent from AAOI `## Primary Source Evidence`.
- `official-report:SIVE:net-sales-2025` is present in AAOI `## Sector Context Evidence`.

- [ ] **Step 3: Run full test suite**

Run: `python3 -m pytest tests -q`

Expected: all tests pass.

### Task 5: Record Review

**Files:**
- Modify: `tasks/todo.md`

- [ ] **Step 1: Mark checklist complete**

Update the focus evidence isolation checklist to checked status.

- [ ] **Step 2: Append review notes**

Record:

- Red test command and failure reason.
- Focused green test command.
- Product run result.
- AAOI memo partition check result.
- Full suite result.
