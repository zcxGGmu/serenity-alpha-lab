# Serenity Alpha Lab SEC Companyfacts Connector Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a primary-source SEC companyfacts connector that converts structured SEC facts into first-party evidence items for ticker memos.

**Architecture:** Add a pure `sec_companyfacts` module that reads local SEC companyfacts JSON, extracts selected annual USD facts, and converts them into `EvidenceItem` records with `claim_type="fact"` and `strength="primary"`. Expose it through a CLI command that can operate offline on fixture/local JSON today and can later be paired with a network fetcher.

**Tech Stack:** Python stdlib, SEC companyfacts JSON shape, existing `EvidenceItem` model, argparse CLI, pytest.

---

### Task 1: Parser And Evidence Conversion

**Files:**
- Create: `src/serenity_alpha_lab/sec_companyfacts.py`
- Create: `tests/test_sec_companyfacts.py`
- Create: `tests/fixtures/sec_companyfacts_sive.json`

- [ ] **Step 1: Write failing parser tests**

Test that a fixture with `dei.EntityCommonStockSharesOutstanding`, `us-gaap.Revenues`, and `us-gaap.NetIncomeLoss` converts into primary fact evidence items for ticker `SIVE`.

- [ ] **Step 2: Run parser tests to verify failure**

Run: `python3 -m pytest tests/test_sec_companyfacts.py -q`
Expected: FAIL because `serenity_alpha_lab.sec_companyfacts` does not exist.

- [ ] **Step 3: Implement module**

Implement `CompanyFactSpec`, `load_companyfact_specs()`, `load_companyfacts_json()`, and `companyfacts_to_evidence()`.

- [ ] **Step 4: Run parser tests**

Run: `python3 -m pytest tests/test_sec_companyfacts.py -q`
Expected: PASS.

### Task 2: CLI Command

**Files:**
- Modify: `src/serenity_alpha_lab/cli.py`
- Modify: `tests/test_cli.py`
- Create: `config/sec_companyfacts_sources.json`

- [ ] **Step 1: Write failing CLI test**

Add a test for `import-sec-companyfacts --sources <json> --out <jsonl>`.

- [ ] **Step 2: Run CLI test to verify failure**

Run: `python3 -m pytest tests/test_cli.py::test_cli_import_sec_companyfacts_writes_jsonl -q`
Expected: FAIL because the subcommand is not implemented.

- [ ] **Step 3: Implement CLI command**

Load source specs, convert each local companyfacts JSON file, dedupe evidence, and write JSONL.

- [ ] **Step 4: Run CLI test**

Run: `python3 -m pytest tests/test_cli.py::test_cli_import_sec_companyfacts_writes_jsonl -q`
Expected: PASS.

### Task 3: Real Local Primary Evidence And Audit

**Files:**
- Create: `data/primary/sec_companyfacts_evidence.jsonl`
- Create: `data/enriched/github_plus_primary.jsonl`
- Create: `output/reports/evidence-audit-primary.md`
- Modify: `tasks/todo.md`

- [ ] **Step 1: Generate primary SEC evidence**

Run: `PYTHONPATH=src python3 -m serenity_alpha_lab.cli import-sec-companyfacts --sources config/sec_companyfacts_sources.json --out data/primary/sec_companyfacts_evidence.jsonl`

- [ ] **Step 2: Generate combined audit**

Run: `PYTHONPATH=src python3 -m serenity_alpha_lab.cli audit-evidence --data data/enriched/github_evidence_resolved_summaries.jsonl data/primary/sec_companyfacts_evidence.jsonl --ticker SIVE --out output/reports/evidence-audit-primary.md`

- [ ] **Step 3: Run full verification**

Run: `python3 -m pytest tests -q`
Expected: all tests pass.
