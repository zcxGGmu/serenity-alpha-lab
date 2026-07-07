# Serenity Alpha Lab Batch Readiness Scanner Plan

## Goal

Add a batch readiness scanner that runs source coverage checks across multiple tickers and ranks which candidates are ready for deeper memo generation.

## Scope

- Reuse existing retrieval and `source_coverage` logic.
- Add a pure `readiness` module for batch assessment and Markdown rendering.
- Add a `scan-readiness` CLI subcommand.
- Keep output deterministic and local-only.

## CLI Contract

```bash
PYTHONPATH=src python3 -m serenity_alpha_lab.cli scan-readiness \
  --data data/enriched/github_plus_primary.jsonl \
  --query "CPO laser bottleneck revenue profitability" \
  --tickers AAOI LITE COHR AXTI SIVE NVDA \
  --out output/reports/cpo-readiness.md \
  --limit 16
```

## Readiness Rules

- `ready`: no critical flags and at least one primary/fact item plus risk coverage.
- `needs_work`: no critical flags, but warning flags exist.
- `blocked`: at least one critical flag.

## TDD Plan

- Add failing tests for candidate status calculation and ranking.
- Add failing tests for Markdown table rendering.
- Add failing CLI test for `scan-readiness`.
- Implement minimal scanner.
- Generate real CPO readiness report.
- Run targeted tests and full suite.
