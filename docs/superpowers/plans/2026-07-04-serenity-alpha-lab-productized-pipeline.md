# Productized Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Provide a stable one-command local pipeline that regenerates the CPO memo pack, readiness report, combined evidence corpus, and provenance index.

**Architecture:** Add a `run-cpo-pack` CLI subcommand that composes existing importers and pack builders. The command uses conservative defaults from `config/` and `data/`, writes deterministic outputs, validates final readiness, and prints a concise run summary.

**Tech Stack:** Python argparse, existing JSONL evidence APIs, pytest, markdown outputs.

---

### Task 1: Add Productized Pipeline Tests

**Files:**
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Write failing pipeline test**

Add `test_cli_run_cpo_pack_regenerates_product_outputs` that runs:

```python
main([
    "run-cpo-pack",
    "--base-data", str(github_evidence),
    "--sec-sources", str(sec_sources),
    "--official-sources", str(official_sources),
    "--manual-data", str(manual_intake),
    "--combined-out", str(combined),
    "--readiness-out", str(readiness),
    "--pack-out-dir", str(pack_dir),
    "--limit", "8",
])
```

Assert that combined evidence, readiness report, `index.md`, `sources.md`, and at least one memo are written.

- [ ] **Step 2: Write failing readiness assertion**

Assert the generated readiness output contains `SIVE` and does not contain `missing_primary_source` for `SIVE`.

- [ ] **Step 3: Run red check**

Run:

```bash
python3 -m pytest tests/test_cli.py::test_cli_run_cpo_pack_regenerates_product_outputs -q
```

Expected: FAIL because `run-cpo-pack` is not implemented.

### Task 2: Implement `run-cpo-pack`

**Files:**
- Modify: `src/serenity_alpha_lab/cli.py`

- [ ] **Step 1: Add parser**

Add `build_run_cpo_pack_parser()` with defaults:
- `--base-data data/enriched/github_evidence_resolved_summaries.jsonl`
- `--sec-sources config/sec_companyfacts_sources.json`
- `--official-sources config/official_report_sources.json`
- `--manual-data data/enriched/manual_intake_guarded.jsonl`
- `--combined-out data/enriched/github_plus_primary.jsonl`
- `--readiness-out output/reports/cpo-readiness-guarded.md`
- `--pack-out-dir output/packs/cpo-guarded`
- `--query "CPO laser bottleneck revenue profitability"`
- `--tickers AAOI LITE COHR AXTI SIVE NVDA`
- `--limit 16`

- [ ] **Step 2: Compose existing importers**

Load base data, import SEC companyfacts from manifest, import official reports from manifest, optionally include manual intake if present, dedupe, and write combined evidence.

- [ ] **Step 3: Write product outputs**

Generate readiness markdown and memo pack from combined + manual evidence.

- [ ] **Step 4: Print summary**

Print combined item count, ready/skipped counts, readiness path, and pack directory.

- [ ] **Step 5: Run target test**

Run:

```bash
python3 -m pytest tests/test_cli.py::test_cli_run_cpo_pack_regenerates_product_outputs -q
```

Expected: PASS.

### Task 3: Document Stable Usage And Verify

**Files:**
- Modify: `README.md`
- Modify: `tasks/todo.md`

- [ ] **Step 1: Update README quick start**

Add a product quick start showing `python3 -m pytest tests -q` and `PYTHONPATH=src python3 -m serenity_alpha_lab.cli run-cpo-pack`.

- [ ] **Step 2: Regenerate default product outputs**

Run default `run-cpo-pack`.

- [ ] **Step 3: Run full tests**

Run:

```bash
python3 -m pytest tests -q
```

Expected: all tests pass.
