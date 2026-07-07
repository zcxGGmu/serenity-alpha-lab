# SIVE Primary Source Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add real Sivers Semiconductors primary evidence so SIVE no longer fails the `missing_primary_source` readiness gate.

**Architecture:** Create a small official-report evidence importer for extracted annual-report text. The importer reads a JSON manifest with source metadata and traceable fact specs, validates each source excerpt against the local report text, emits primary `fact` evidence, and merges it into the combined evidence corpus.

**Tech Stack:** Python dataclasses, argparse CLI, JSON manifests, JSONL evidence files, pytest.

---

### Task 1: Add Official Report Import Tests

**Files:**
- Create: `tests/fixtures/sivers_annualreport_excerpt.txt`
- Create: `tests/fixtures/official_report_sources.json`
- Create: `tests/test_official_report.py`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Write fixture text**

Create `tests/fixtures/sivers_annualreport_excerpt.txt` with the exact source excerpts used by tests:

```text
Annual revenues increased by 40% YoY to a new record of SEK 307 m.
The Group’s net sales amounted to SEK 306.6 (219.2) million, an increase of SEK 87.4 million or 40% compared with the previous year.
Our serviceable market and opportunity pipeline has expanded to include pluggable optical interconnects as well as scale-up and scale-out architectures for co-packaged optics (CPO).
```

- [ ] **Step 2: Write manifest fixture**

Create `tests/fixtures/official_report_sources.json` with a SIVE official annual-report spec for revenue and CPO-market evidence.

- [ ] **Step 3: Write failing unit tests**

Add tests that expect:
- `load_official_report_specs()` resolves text paths relative to the manifest.
- `official_report_specs_to_evidence()` emits primary `fact` items for SIVE.
- importer rejects a source excerpt missing from the text file.

- [ ] **Step 4: Write failing CLI test**

Add `test_cli_import_official_report_writes_primary_evidence_jsonl`.

- [ ] **Step 5: Run red check**

Run:

```bash
python3 -m pytest tests/test_official_report.py tests/test_cli.py::test_cli_import_official_report_writes_primary_evidence_jsonl -q
```

Expected: FAIL because `serenity_alpha_lab.official_report` and the CLI subcommand do not exist.

### Task 2: Implement Official Report Importer

**Files:**
- Create: `src/serenity_alpha_lab/official_report.py`
- Modify: `src/serenity_alpha_lab/cli.py`

- [ ] **Step 1: Add dataclasses**

Create `OfficialReportFactSpec` and `OfficialReportSourceSpec` with source title, URL, published date, ticker, local text path, and fact specs.

- [ ] **Step 2: Add manifest loader**

Parse a JSON array and resolve relative `text_path` values against the manifest parent.

- [ ] **Step 3: Add evidence conversion**

Validate each `source_excerpt` exists in the normalized local report text, then emit `EvidenceItem` records with `strength="primary"`, `claim_type="fact"`, and `source_excerpt`.

- [ ] **Step 4: Add CLI subcommand**

Add `import-official-report --sources <manifest> --out <jsonl>` that writes deduped evidence JSONL.

- [ ] **Step 5: Run target tests**

Run:

```bash
python3 -m pytest tests/test_official_report.py tests/test_cli.py::test_cli_import_official_report_writes_primary_evidence_jsonl -q
```

Expected: PASS.

### Task 3: Import Real SIVE Primary Evidence And Verify Readiness

**Files:**
- Create: `config/official_report_sources.json`
- Create/Modify: `data/primary/raw/sivers_annualreport_2025_final.pdf`
- Create/Modify: `data/primary/raw/sivers_annualreport_2025_final.txt`
- Create: `data/primary/sive_official_report_evidence.jsonl`
- Modify: `data/enriched/github_plus_primary.jsonl`
- Modify: `output/reports/cpo-readiness-guarded.md`
- Modify: `output/packs/cpo-guarded/`
- Modify: `tasks/todo.md`

- [ ] **Step 1: Add real Sivers manifest**

Use the official Sivers Semiconductors 2025 Annual Report PDF URL and extracted text file. Include fact specs for 2025 net sales and CPO opportunity pipeline.

- [ ] **Step 2: Import SIVE official evidence**

Run:

```bash
PYTHONPATH=src python3 -m serenity_alpha_lab.cli import-official-report --sources config/official_report_sources.json --out data/primary/sive_official_report_evidence.jsonl
```

- [ ] **Step 3: Rebuild combined corpus**

Merge GitHub/SEC/manual/SIVE official evidence into `data/enriched/github_plus_primary.jsonl`.

- [ ] **Step 4: Regenerate readiness and memo pack**

Run `scan-readiness` and `generate-pack` with the guarded manual intake file included.

- [ ] **Step 5: Run full verification**

Run:

```bash
python3 -m pytest tests -q
```

Expected: all tests pass, SIVE is no longer blocked for `missing_primary_source`.
