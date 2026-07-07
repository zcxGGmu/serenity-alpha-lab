# Serenity Alpha Lab Summary Quality Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Improve evidence summary quality without changing source claims, and remove false short-summary audit flags caused by Chinese text that lacks whitespace.

**Architecture:** Add a deterministic `summary_enrichment` module that detects weak summaries and replaces only clearly weak summaries with a concise summary derived from the claim, source, tickers, and themes. Update evidence audit to use a multilingual weak-summary heuristic rather than English-only word count.

**Tech Stack:** Python stdlib, existing `EvidenceItem` model, argparse CLI, pytest.

---

### Task 1: Multilingual Short Summary Heuristic

**Files:**
- Modify: `src/serenity_alpha_lab/evidence_audit.py`
- Modify: `tests/test_evidence_audit.py`

- [ ] **Step 1: Write failing audit test**

Add a test proving a meaningful Chinese summary such as `基于 Serenity 推文提炼的产业链分析框架。` is not flagged as `short_summary`, while ` ``` ` is flagged.

- [ ] **Step 2: Run audit test to verify failure**

Run: `python3 -m pytest tests/test_evidence_audit.py -q`
Expected: FAIL because the current audit uses `summary.split()` and treats Chinese text as one word.

- [ ] **Step 3: Implement multilingual weak-summary heuristic**

Add `is_weak_summary()` and use it in `_quality_flags()`. Treat placeholders, code fences, and very short text as weak; treat Chinese text with enough CJK characters as meaningful.

- [ ] **Step 4: Run audit tests**

Run: `python3 -m pytest tests/test_evidence_audit.py -q`
Expected: PASS.

### Task 2: Summary Enrichment Module

**Files:**
- Create: `src/serenity_alpha_lab/summary_enrichment.py`
- Create: `tests/test_summary_enrichment.py`

- [ ] **Step 1: Write failing enrichment tests**

Test that weak summaries are replaced with a deterministic summary, existing good summaries are preserved, and enriched items gain `summary-enriched` theme.

- [ ] **Step 2: Run enrichment tests to verify failure**

Run: `python3 -m pytest tests/test_summary_enrichment.py -q`
Expected: FAIL because the module does not exist.

- [ ] **Step 3: Implement module**

Implement `enrich_evidence_summaries()` and `build_enriched_summary()` using existing item fields only.

- [ ] **Step 4: Run enrichment tests**

Run: `python3 -m pytest tests/test_summary_enrichment.py -q`
Expected: PASS.

### Task 3: CLI And Real Corpus

**Files:**
- Modify: `src/serenity_alpha_lab/cli.py`
- Modify: `tests/test_cli.py`
- Create: `data/enriched/github_evidence_resolved_summaries.jsonl`
- Create: `output/reports/evidence-audit-summary-enriched.md`
- Modify: `tasks/todo.md`

- [ ] **Step 1: Write failing CLI test**

Add a test for `enrich-summaries --data <fixture> --out <jsonl>`.

- [ ] **Step 2: Run CLI test to verify failure**

Run: `python3 -m pytest tests/test_cli.py::test_cli_enrich_summaries_writes_jsonl -q`
Expected: FAIL because the subcommand is not implemented.

- [ ] **Step 3: Implement CLI command**

Route `enrich-summaries` before memo mode, load evidence, enrich summaries, and write JSONL.

- [ ] **Step 4: Generate real enriched corpus and audit**

Run:
`PYTHONPATH=src python3 -m serenity_alpha_lab.cli enrich-summaries --data data/enriched/github_evidence_resolved.jsonl --out data/enriched/github_evidence_resolved_summaries.jsonl`

Then:
`PYTHONPATH=src python3 -m serenity_alpha_lab.cli audit-evidence --data data/enriched/github_evidence_resolved_summaries.jsonl --ticker SIVE --out output/reports/evidence-audit-summary-enriched.md`

- [ ] **Step 5: Run full verification**

Run: `python3 -m pytest tests -q`
Expected: all tests pass.
