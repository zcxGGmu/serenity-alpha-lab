# Evidence Provenance Index Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generate a memo-pack-level `sources.md` file that centralizes primary evidence provenance across generated memos.

**Architecture:** Extend `MemoPackMemo` to retain retrieved evidence alongside rendered markdown. Add a provenance renderer that extracts primary/fact evidence from generated memos, groups it by ticker, and writes `sources.md` during `write_memo_pack()`.

**Tech Stack:** Python dataclasses, markdown rendering, pytest.

---

### Task 1: Add Provenance Index Tests

**Files:**
- Modify: `tests/test_memo_pack.py`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Write failing renderer test**

Add a test that builds a pack with a primary evidence item containing `source_excerpt`, calls `render_memo_pack_sources(pack)`, and asserts:

```python
assert "# Evidence Provenance Index" in sources
assert "aaoi-memo.md" in sources
assert "Source excerpt" in sources
```

- [ ] **Step 2: Write failing write test**

Add a test that calls `write_memo_pack(pack, out_dir)` and asserts `out_dir / "sources.md"` exists.

- [ ] **Step 3: Write failing CLI test update**

Extend `test_cli_generate_pack_writes_ready_memos_and_index` to assert `sources.md` exists.

- [ ] **Step 4: Run red check**

Run:

```bash
python3 -m pytest tests/test_memo_pack.py tests/test_cli.py::test_cli_generate_pack_writes_ready_memos_and_index -q
```

Expected: FAIL because `render_memo_pack_sources` and `sources.md` output do not exist.

### Task 2: Implement Provenance Index

**Files:**
- Modify: `src/serenity_alpha_lab/memo_pack.py`

- [ ] **Step 1: Store matched evidence in `MemoPackMemo`**

Add `evidence: List[EvidenceItem]` and populate it from `retrieve()`.

- [ ] **Step 2: Render `sources.md`**

Add `render_memo_pack_sources(pack)` that lists primary/fact evidence by ticker with memo filename, source title, URL, claim, summary, and source excerpt when present.

- [ ] **Step 3: Write `sources.md`**

Update `write_memo_pack()` to write both `index.md` and `sources.md`.

- [ ] **Step 4: Run target tests**

Run:

```bash
python3 -m pytest tests/test_memo_pack.py tests/test_cli.py::test_cli_generate_pack_writes_ready_memos_and_index -q
```

Expected: PASS.

### Task 3: Regenerate Pack And Verify

**Files:**
- Modify: `output/packs/cpo-guarded/sources.md`
- Modify: `tasks/todo.md`

- [ ] **Step 1: Regenerate guarded pack**

Run:

```bash
PYTHONPATH=src python3 -m serenity_alpha_lab.cli generate-pack --data data/enriched/github_plus_primary.jsonl data/enriched/manual_intake_guarded.jsonl --query "CPO laser bottleneck revenue profitability" --tickers AAOI LITE COHR AXTI SIVE NVDA --out-dir output/packs/cpo-guarded --limit 16
```

- [ ] **Step 2: Verify SIVE provenance**

Check `output/packs/cpo-guarded/sources.md` contains `official-report:SIVE:net-sales-2025`, `sive-memo.md`, and `Source excerpt`.

- [ ] **Step 3: Run full tests**

Run:

```bash
python3 -m pytest tests -q
```

Expected: all tests pass.
