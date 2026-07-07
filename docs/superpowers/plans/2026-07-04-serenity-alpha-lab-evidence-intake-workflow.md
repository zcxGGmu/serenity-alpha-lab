# Serenity Alpha Lab Evidence Intake Workflow Plan

## Goal

Add an intake workflow that appends newly collected evidence to JSONL using the canonical evidence schema and can refresh readiness plus memo-pack outputs in one run.

## Scope

- Add an `evidence_intake` module for creating, appending, and validating one new evidence item.
- Add an `ingest-task-evidence` CLI command.
- Support optional refresh outputs for readiness report and memo pack.
- Keep the workflow deterministic and local-only.

## CLI Contract

```bash
PYTHONPATH=src python3 -m serenity_alpha_lab.cli ingest-task-evidence \
  --out data/enriched/manual_intake.jsonl \
  --id manual:NVDA:risk:cpo-sourcing \
  --source-title "Manual NVDA risk note" \
  --source-url https://example.com/nvda-risk \
  --published-at 2026-07-04 \
  --claim "NVDA faces CPO sourcing risk if optical component supply tightens." \
  --summary "Manual intake captures a negative/risk item for NVDA CPO sourcing." \
  --tickers NVDA \
  --themes CPO risk manual-intake \
  --supply-chain-layer "AI accelerator customer" \
  --direction negative \
  --strength derived \
  --claim-type risk \
  --confidence 0.72 \
  --factor-impact evidence_quality=8 \
  --factor-impact supply_elasticity=-5 \
  --refresh-data data/enriched/github_plus_primary.jsonl data/enriched/manual_intake.jsonl \
  --refresh-query "CPO laser bottleneck revenue profitability" \
  --refresh-tickers AAOI LITE COHR AXTI SIVE NVDA \
  --readiness-out output/reports/cpo-readiness-refreshed.md \
  --pack-out-dir output/packs/cpo-refreshed \
  --limit 16
```

## TDD Plan

- Add failing tests for parsing factor impacts and building a valid `EvidenceItem`.
- Add failing tests for appending JSONL evidence.
- Add failing CLI test that writes intake evidence and refreshes readiness plus memo pack outputs.
- Implement the minimal module and CLI branch.
- Generate sample intake evidence and refreshed outputs.
- Run targeted tests and full suite.
