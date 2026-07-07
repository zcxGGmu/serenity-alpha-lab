# Serenity Alpha Lab Acquisition Queue Plan

## Goal

Convert readiness gaps into concrete evidence acquisition tasks so weak candidates can be repaired systematically.

## Scope

- Reuse `assess_batch_readiness`.
- Add an `acquisition_queue` module that maps coverage flags to source tasks.
- Add a CLI command that writes a Markdown queue report.
- Keep tasks deterministic and local-only.

## CLI Contract

```bash
PYTHONPATH=src python3 -m serenity_alpha_lab.cli build-acquisition-queue \
  --data data/enriched/github_plus_primary.jsonl \
  --query "CPO laser bottleneck revenue profitability" \
  --tickers AAOI LITE COHR AXTI SIVE NVDA \
  --out output/reports/cpo-acquisition-queue.md \
  --limit 16
```

## Task Mapping

- `missing_primary_source`: collect primary filing, company release, or audited financial fact.
- `missing_risk_coverage`: collect negative/risk/invalidation evidence from filings, earnings calls, or credible third-party sources.
- `methodology_concentration`: collect non-methodology company-specific evidence.
- `placeholder_concentration`: resolve placeholder evidence into concrete ticker/source records.

## TDD Plan

- Add failing tests for task generation from readiness flags.
- Add failing tests for Markdown queue rendering.
- Add failing CLI test for `build-acquisition-queue`.
- Implement module and CLI.
- Generate real CPO queue report.
- Run targeted tests and full suite.
