# Serenity Alpha Lab Primary Retrieval Boost Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make primary-source evidence visible and preferentially ranked in ticker-focused memos after SEC companyfacts are imported.

**Architecture:** Update retrieval scoring to boost `primary` / `fact` / `primary-source` evidence only when it is relevant through query overlap or the requested ticker. Update memo rendering to add a dedicated primary-source evidence section before general supporting evidence.

**Tech Stack:** Python stdlib, existing retrieval/scoring/memo modules, pytest.

---

### Task 1: Retrieval Ranking Boost

**Files:**
- Create: `tests/test_retrieval.py`
- Modify: `src/serenity_alpha_lab/retrieval.py`

- [ ] **Step 1: Write failing retrieval tests**

Test that focus-ticker primary fact evidence outranks methodology evidence when both match a ticker-focused memo, and that unrelated primary facts do not beat focus-ticker evidence.

- [ ] **Step 2: Run retrieval tests to verify failure**

Run: `python3 -m pytest tests/test_retrieval.py -q`
Expected: FAIL because retrieval does not yet boost primary facts.

- [ ] **Step 3: Implement retrieval scoring boost**

Add relevance-gated boosts for `strength == "primary"`, `claim_type == "fact"`, and `primary-source` themes. Penalize generic methodology evidence slightly.

- [ ] **Step 4: Run retrieval tests**

Run: `python3 -m pytest tests/test_retrieval.py -q`
Expected: PASS.

### Task 2: Memo Primary Section

**Files:**
- Modify: `src/serenity_alpha_lab/memo.py`
- Modify: `tests/test_memo.py`

- [ ] **Step 1: Write failing memo test**

Test that a memo with primary evidence contains `## Primary Source Evidence` and lists primary fact evidence before general supporting evidence.

- [ ] **Step 2: Run memo test to verify failure**

Run: `python3 -m pytest tests/test_memo.py -q`
Expected: FAIL because memo currently has no primary section.

- [ ] **Step 3: Implement memo section**

Render primary evidence items in a dedicated section, then keep supporting evidence for non-negative items as before.

- [ ] **Step 4: Run memo tests**

Run: `python3 -m pytest tests/test_memo.py -q`
Expected: PASS.

### Task 3: Real Memo And Verification

**Files:**
- Create: `output/memos/aaoi-cpo-primary.md`
- Modify: `tasks/todo.md`

- [ ] **Step 1: Generate primary-boosted memo**

Run: `PYTHONPATH=src python3 -m serenity_alpha_lab.cli --data data/enriched/github_plus_primary.jsonl --query "CPO laser bottleneck revenue profitability" --ticker AAOI --out output/memos/aaoi-cpo-primary.md --limit 16`

- [ ] **Step 2: Run full verification**

Run: `python3 -m pytest tests -q`
Expected: all tests pass.

- [ ] **Step 3: Record review notes**

Append exact verification outputs and memo path to `tasks/todo.md`.
