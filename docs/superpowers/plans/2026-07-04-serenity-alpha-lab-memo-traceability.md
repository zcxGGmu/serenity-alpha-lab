# Memo Traceability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Show source excerpts in memo primary evidence so key conclusions can be traced directly to source text.

**Architecture:** Keep the existing memo structure and only specialize the Primary Source Evidence formatter. Primary/fact items with `source_excerpt` render an indented trace line below the evidence bullet; items without excerpts keep the existing compact output for backward compatibility.

**Tech Stack:** Python, markdown string rendering, pytest.

---

### Task 1: Add Memo Traceability Tests

**Files:**
- Modify: `tests/test_memo.py`

- [ ] **Step 1: Write failing primary excerpt test**

Add a test that builds a primary `EvidenceItem` with `source_excerpt`, calls `generate_memo()`, and asserts:

```python
assert "**Source excerpt:**" in memo
assert "The Group’s net sales amounted to SEK 306.6" in memo
```

- [ ] **Step 2: Write compatibility test**

Add a test that builds a primary `EvidenceItem` without `source_excerpt`, calls `generate_memo()`, and asserts it still renders in `## Primary Source Evidence`.

- [ ] **Step 3: Run red check**

Run:

```bash
python3 -m pytest tests/test_memo.py::test_generate_memo_includes_source_excerpt_for_primary_evidence tests/test_memo.py::test_generate_memo_keeps_primary_evidence_without_source_excerpt -q
```

Expected: first test fails because primary evidence currently omits `source_excerpt`.

### Task 2: Implement Primary Evidence Trace Lines

**Files:**
- Modify: `src/serenity_alpha_lab/memo.py`

- [ ] **Step 1: Add primary-specific formatter**

Update `_format_primary_evidence()` to format each item with the existing evidence bullet plus an indented source excerpt line when `item.source_excerpt` is non-empty.

- [ ] **Step 2: Preserve supporting evidence behavior**

Leave `_format_evidence()` unchanged so Supporting Evidence does not become noisy.

- [ ] **Step 3: Run target tests**

Run:

```bash
python3 -m pytest tests/test_memo.py -q
```

Expected: PASS.

### Task 3: Regenerate Memo Pack And Verify

**Files:**
- Modify: `output/packs/cpo-guarded/`
- Modify: `tasks/todo.md`

- [ ] **Step 1: Regenerate guarded memo pack**

Run:

```bash
PYTHONPATH=src python3 -m serenity_alpha_lab.cli generate-pack --data data/enriched/github_plus_primary.jsonl data/enriched/manual_intake_guarded.jsonl --query "CPO laser bottleneck revenue profitability" --tickers AAOI LITE COHR AXTI SIVE NVDA --out-dir output/packs/cpo-guarded --limit 16
```

- [ ] **Step 2: Verify SIVE memo contains trace lines**

Run a grep/check for `**Source excerpt:**` in `output/packs/cpo-guarded/sive-memo.md`.

- [ ] **Step 3: Run full tests**

Run:

```bash
python3 -m pytest tests -q
```

Expected: all tests pass.
