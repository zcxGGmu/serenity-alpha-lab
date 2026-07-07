# Provenance Usage Map Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deduplicate `sources.md` primary evidence and show which memo files use each evidence item.

**Architecture:** Keep `MemoPackMemo.evidence` as the source of truth. Build an in-memory evidence usage map keyed by evidence id, retaining first-seen evidence metadata plus sorted memo filenames and tickers, then render a single `## Primary Evidence` section.

**Tech Stack:** Python dataclasses, markdown rendering, pytest.

---

### Task 1: Add Usage Map Tests

**Files:**
- Modify: `tests/test_memo_pack.py`

- [ ] **Step 1: Update provenance renderer test**

Expect `render_memo_pack_sources(pack)` to include `## Primary Evidence` and `**Used in memos:** aaoi-memo.md`.

- [ ] **Step 2: Add duplicate evidence test**

Build a pack where one primary evidence item is used by both `AAOI` and `SIVE`; assert the evidence id appears once and `**Used in memos:** aaoi-memo.md, sive-memo.md` appears.

- [ ] **Step 3: Run red check**

Run:

```bash
python3 -m pytest tests/test_memo_pack.py::test_render_memo_pack_sources_lists_primary_evidence_provenance tests/test_memo_pack.py::test_render_memo_pack_sources_deduplicates_shared_evidence_usage -q
```

Expected: FAIL because `sources.md` currently renders evidence under each ticker memo and does not include `Used in memos`.

### Task 2: Implement Deduplicated Usage Map

**Files:**
- Modify: `src/serenity_alpha_lab/memo_pack.py`

- [ ] **Step 1: Add usage accumulator**

Collect primary evidence by id, preserving first-seen item metadata and accumulating memo filenames and tickers.

- [ ] **Step 2: Render single evidence section**

Render:

```markdown
## Primary Evidence

- **evidence-id** [Source](url) (...)
  - **Tickers:** ...
  - **Used in memos:** ...
  - **Claim:** ...
  - **Summary:** ...
  - **Source excerpt:** ...
```

- [ ] **Step 3: Run target tests**

Run:

```bash
python3 -m pytest tests/test_memo_pack.py -q
```

Expected: PASS.

### Task 3: Regenerate Product Outputs

**Files:**
- Modify: `output/packs/cpo-guarded/sources.md`
- Modify: `tasks/todo.md`

- [ ] **Step 1: Run product pipeline**

Run:

```bash
PYTHONPATH=src python3 -m serenity_alpha_lab.cli run-cpo-pack
```

- [ ] **Step 2: Verify dedupe**

Check `official-report:SIVE:net-sales-2025` appears once in `sources.md` and lists all memo files that use it.

- [ ] **Step 3: Run full tests**

Run:

```bash
python3 -m pytest tests -q
```

Expected: all tests pass.
