# Serenity Alpha Lab Check Coverage CLI Plan

## Goal

Add an independent `check-coverage` command that retrieves evidence for a query/ticker pair and writes a standalone source coverage report.

## Scope

- Reuse existing retrieval and `source_coverage` logic.
- Write a Markdown report that can be run before memo generation.
- Keep memo generation behavior unchanged.
- Keep implementation local-only and deterministic.

## CLI Contract

```bash
PYTHONPATH=src python3 -m serenity_alpha_lab.cli check-coverage \
  --data data/enriched/github_plus_primary.jsonl \
  --query "CPO laser bottleneck revenue profitability" \
  --ticker AAOI \
  --out output/reports/aaoi-cpo-coverage.md \
  --limit 16
```

## Expected Report

- Title: `# Source Coverage Report`
- Query and ticker metadata.
- Retrieved evidence count.
- Existing source coverage Markdown body.
- Actionable flags and recommendations when coverage is weak.

## TDD Plan

- Add a failing CLI test for `check-coverage`.
- Confirm it currently routes to memo mode or rejects the command.
- Implement parser and command branch.
- Generate the real AAOI report.
- Run targeted tests and full suite.
