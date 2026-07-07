# Serenity Alpha Lab Auto Memo Pack Plan

## Goal

Add an auto memo pack command that generates full memos for `ready` tickers and a gap report for `needs_work` or `blocked` tickers.

## Scope

- Reuse `assess_batch_readiness`, `retrieve`, `score_research_question`, and `generate_memo`.
- Add a pure `memo_pack` module for pack generation and Markdown index rendering.
- Add a `generate-pack` CLI subcommand.
- Keep output deterministic and local-only.

## CLI Contract

```bash
PYTHONPATH=src python3 -m serenity_alpha_lab.cli generate-pack \
  --data data/enriched/github_plus_primary.jsonl \
  --query "CPO laser bottleneck revenue profitability" \
  --tickers AAOI LITE COHR AXTI SIVE NVDA \
  --out-dir output/packs/cpo \
  --limit 16
```

## Expected Output

- `index.md` with ready memo links and skipped ticker gap reasons.
- One memo file per `ready` ticker.
- No formal memo for `needs_work` or `blocked` tickers.

## TDD Plan

- Add failing module tests for memo generation and skipped gap reporting.
- Add failing CLI test for `generate-pack`.
- Implement minimal module and CLI.
- Generate real CPO pack.
- Run targeted tests and full suite.
