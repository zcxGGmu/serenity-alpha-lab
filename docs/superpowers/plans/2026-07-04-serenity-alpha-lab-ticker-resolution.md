# Serenity Alpha Lab Ticker Resolution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reduce placeholder `SERENITY` ticker usage by adding auditable, rule-based enrichment that maps generic Serenity evidence to concrete ticker coverage only when explicit keyword evidence supports the linkage.

**Architecture:** Add a pure `ticker_resolution` module that loads JSON rule specs, applies them to `EvidenceItem` objects, and writes enriched evidence through the existing JSONL writer. The resolver must preserve original evidence fields, append resolved tickers without duplicates, and add traceable enrichment themes that can be audited later.

**Tech Stack:** Python stdlib, existing `EvidenceItem` model, JSON rule manifest, argparse CLI, pytest.

---

### Task 1: Resolver Model And Tests

**Files:**
- Create: `src/serenity_alpha_lab/ticker_resolution.py`
- Create: `tests/test_ticker_resolution.py`
- Create: `tests/fixtures/ticker_rules.json`

- [ ] **Step 1: Write failing resolver tests**

Create tests proving that rules add a ticker when evidence text matches rule keywords, preserve existing tickers, avoid duplicates, and leave unmatched evidence unchanged.

- [ ] **Step 2: Run resolver tests to verify failure**

Run: `python3 -m pytest tests/test_ticker_resolution.py -q`
Expected: FAIL because `serenity_alpha_lab.ticker_resolution` does not exist.

- [ ] **Step 3: Implement resolver module**

Implement `TickerResolutionRule`, `load_ticker_resolution_rules()`, and `resolve_evidence_tickers()`.

- [ ] **Step 4: Run resolver tests**

Run: `python3 -m pytest tests/test_ticker_resolution.py -q`
Expected: PASS.

### Task 2: CLI Enrichment Command

**Files:**
- Modify: `src/serenity_alpha_lab/cli.py`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Write failing CLI test**

Add a test for `resolve-tickers --data <fixture> --rules <rules> --out <jsonl>`.

- [ ] **Step 2: Run CLI test to verify failure**

Run: `python3 -m pytest tests/test_cli.py::test_cli_resolve_tickers_writes_enriched_jsonl -q`
Expected: FAIL because `resolve-tickers` is not implemented.

- [ ] **Step 3: Implement CLI command**

Route `resolve-tickers` before memo mode, load evidence and rules, resolve tickers, and write JSONL.

- [ ] **Step 4: Run CLI test**

Run: `python3 -m pytest tests/test_cli.py::test_cli_resolve_tickers_writes_enriched_jsonl -q`
Expected: PASS.

### Task 3: Real Enrichment And Verification

**Files:**
- Create: `config/ticker_resolution_rules.json`
- Create: `data/enriched/github_evidence_resolved.jsonl`
- Create: `output/reports/evidence-audit-resolved.md`
- Modify: `tasks/todo.md`

- [ ] **Step 1: Create conservative real rules**

Start with rules for CPO / optical / laser evidence mapped to `SIVE`, `LITE`, `COHR`, `AAOI`, and `AXTI` only when matching explicit keywords appear.

- [ ] **Step 2: Generate enriched evidence**

Run: `PYTHONPATH=src python3 -m serenity_alpha_lab.cli resolve-tickers --data data/imported/github_evidence.jsonl --rules config/ticker_resolution_rules.json --out data/enriched/github_evidence_resolved.jsonl`

- [ ] **Step 3: Generate refreshed audit**

Run: `PYTHONPATH=src python3 -m serenity_alpha_lab.cli audit-evidence --data data/enriched/github_evidence_resolved.jsonl --ticker SIVE --out output/reports/evidence-audit-resolved.md`

- [ ] **Step 4: Run full verification**

Run: `python3 -m pytest tests -q`
Expected: all tests pass.

- [ ] **Step 5: Record review notes**

Append exact command outputs and audit delta to `tasks/todo.md`.
