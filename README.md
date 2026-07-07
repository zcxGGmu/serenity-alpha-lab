# Serenity Alpha Lab

`serenity-alpha-lab` is a local-first Serenity investment research system for stock, industry, sector, and theme analysis.

It combines:

- evidence-backed claim storage
- claim-type classification for fact, methodology, inference, risk, catalyst, and invalidation evidence
- deterministic retrieval
- transparent Serenity-style scoring
- skeptic review and invalidation checks
- source-backed local financial context where evidence exists
- bilingual Chinese and English dashboard/report generation
- a user-facing report library with drawer-based report reading
- markdown memo generation

It is not an investment adviser and does not generate buy/sell/hold instructions, target prices, or position sizing. Every output is a research artifact that must be independently verified before any capital decision.

## Quick Start

```bash
cd serenity-alpha-lab
python3 -m pip install -e .
make smoke
make verify
```

Source-tree fallback:

```bash
python3 -m pytest tests -q
python3 -m pytest tests/test_ui_http_e2e.py -q
PYTHONPATH=src python3 -m serenity_alpha_lab.cli doctor
PYTHONPATH=src python3 -m serenity_alpha_lab.cli run-cpo-pack --allow-skipped
PYTHONPATH=src python3 -m serenity_alpha_lab.cli build-financial-metrics \
  --data data/enriched/github_plus_primary.jsonl data/primary/sive_official_report_evidence.jsonl \
  --out config/financial_metrics.json
PYTHONPATH=src python3 -m serenity_alpha_lab.cli build-ui --language both
PYTHONPATH=src python3 -m serenity_alpha_lab.cli scan-report-safety \
  --reports output/packs/cpo-guarded/*-memo.md \
  --out output/reports/report-safety-scan.md
PYTHONPATH=src python3 -m serenity_alpha_lab.cli build-coverage-matrix \
  --data data/enriched/github_plus_primary.jsonl data/enriched/manual_intake_guarded.jsonl \
  --stock-universe config/stock_universe.json \
  --query "存储芯片" \
  --out output/reports/universe-coverage-matrix.md
```

The product pipeline regenerates:

- `data/enriched/github_plus_primary.jsonl`
- `output/reports/cpo-readiness-guarded.md`
- `output/packs/cpo-guarded/index.md`
- `output/packs/cpo-guarded/sources.md`
- one memo per ready ticker in `output/packs/cpo-guarded/`
- `config/financial_metrics.json` when source-backed metrics are rebuilt
- `output/reports/universe-coverage-matrix.md` when stock-universe coverage is checked
- `output/ui/index.html` and `output/ui/index.zh.html` when the local UI builder is run
- generated analysis pages under `output/ui/analyses/<slug>/` when users launch new industry, theme, sector, or ticker research

The default CPO pack currently evaluates `AAOI`, `LITE`, `COHR`, `AXTI`, `SIVE`, and `NVDA` using local evidence, SEC companyfacts snapshots, official report excerpts, and guarded manual intake evidence.

## Stable Product Run

Check local inputs without generating outputs:

```bash
PYTHONPATH=src python3 -m serenity_alpha_lab.cli doctor
```

Use this command when handing the project to another user:

```bash
PYTHONPATH=src python3 -m serenity_alpha_lab.cli run-cpo-pack --allow-skipped
```

Rebuild source-backed financial metrics from local evidence:

```bash
PYTHONPATH=src python3 -m serenity_alpha_lab.cli build-financial-metrics \
  --data data/enriched/github_plus_primary.jsonl data/primary/sive_official_report_evidence.jsonl \
  --out config/financial_metrics.json
```

Build the bilingual dashboard UI after generating the pack and metrics:

```bash
PYTHONPATH=src python3 -m serenity_alpha_lab.cli build-ui --language both
```

Scan generated reports for product-authored investment advice before handoff:

```bash
PYTHONPATH=src python3 -m serenity_alpha_lab.cli scan-report-safety \
  --reports output/packs/cpo-guarded/*-memo.md \
  --out output/reports/report-safety-scan.md
```

The safety scanner ignores quoted source evidence lines, so raw external excerpts can contain phrases such as `buy / sell / hold` without being confused with Serenity Alpha Lab's own generated guidance.

Build a stock-universe coverage matrix before expanding an industry page:

```bash
PYTHONPATH=src python3 -m serenity_alpha_lab.cli build-coverage-matrix \
  --data data/enriched/github_plus_primary.jsonl data/enriched/manual_intake_guarded.jsonl \
  --stock-universe config/stock_universe.json \
  --query "存储芯片" \
  --out output/reports/universe-coverage-matrix.md
```

The matrix ranks matched universe candidates by missing evidence, primary/fact coverage, risk coverage, priority, and the next source-search prompt. Use it before trusting a theme page as representative of the full industry candidate pool. When the UI is rebuilt, the matrix is also published to `output/ui/reports/universe-coverage-matrix.md` and appears in the homepage report library as a drawer-readable `Open Coverage Matrix` / `打开覆盖矩阵` entry.

Each UI-launched industry, sector, theme, or ticker analysis also writes its own operational reports under `output/ui/analyses/<slug>/reports/`:

- `universe-coverage-matrix.md` for the exact query that was launched.
- `evidence-acquisition-queue.md` with the next primary-source, risk, and invalidation evidence tasks for the generated candidate set.

When the analysis is launched from the Chinese UI, both operational report bodies are localized in Chinese, not just the drawer buttons.

Start the local product server:

```bash
PYTHONPATH=src python3 -m serenity_alpha_lab.cli serve-ui \
  --host 127.0.0.1 \
  --port 8767 \
  --language both
```

Then open:

- Chinese UI: `http://127.0.0.1:8767/index.zh.html`
- English UI: `http://127.0.0.1:8767/index.html`

The UI is a bilingual research dashboard with readiness status, report history, explicit analysis launch controls, search, status filtering, candidate comparison, ticker-focused memo previews, source coverage, risk previews, invalidation checks, primary-source provenance, and drawer-based report reading.

Default UI outputs:

- `output/ui/index.html` for English.
- `output/ui/index.zh.html` for Chinese.
- `output/ui/metrics.json` for dashboard financial metrics copied from the canonical metrics catalog.
- `output/ui/analyses/manifest.json` for generated report history.

Use the `Start analysis` / `启动分析` form to create a new local industry, sector, theme, or ticker dashboard, such as `存储芯片`, `HBM`, `半导体设备`, or `AAOI`. The form writes a fresh readiness report, memo pack, and bilingual dashboard under `output/ui/analyses/`. The page search box is only for filtering the currently open dashboard.

## User Workflow

For Chinese users:

1. Start the server and open `http://127.0.0.1:8767/index.zh.html`.
2. In `启动分析`, enter an industry, sector, theme, or ticker, for example `存储芯片` or `HBM`.
3. Wait for the generated analysis page under `output/ui/analyses/<slug>/`.
4. Read `候选对比` first to compare tickers by Serenity score, rating, confidence, key gaps, evidence coverage, and financial context.
5. Use `查看报告` to open the right-side report drawer instead of leaving the dashboard.
6. Review `证据补齐行动清单` before trusting or promoting a candidate; it explains which primary, demand, invalidation, and crowding evidence still needs to be collected.
7. Open `覆盖矩阵` from the generated analysis page to confirm the theme-specific candidate universe and evidence gaps.
8. Open `证据采集队列` from the generated analysis page to see which filings, official materials, risk evidence, or invalidation evidence should be collected next.
9. Use `最近报告` on the homepage to reopen generated reports later.

For English users, use the same flow from `http://127.0.0.1:8767/index.html`.

## UI E2E Smoke

Run the HTTP-level UI smoke test after changing dashboard, launcher, report drawer, or local server behavior:

```bash
python3 -m pytest tests/test_ui_http_e2e.py -q
```

The test starts a local ephemeral HTTP server, opens the Chinese homepage, calls `/analyze?query=存储芯片&language=zh`, follows the generated analysis page, and verifies the Chinese memo file used by the report drawer.

Release notes and handoff checks:

- `INSTALL.md`
- `CHANGELOG.md`
- `docs/RELEASE_CHECKLIST.md`

Optional output overrides:

```bash
PYTHONPATH=src python3 -m serenity_alpha_lab.cli run-cpo-pack \
  --combined-out data/enriched/github_plus_primary.jsonl \
  --readiness-out output/reports/cpo-readiness-guarded.md \
  --pack-out-dir output/packs/cpo-guarded
```

Dashboard output overrides:

```bash
PYTHONPATH=src python3 -m serenity_alpha_lab.cli build-ui \
  --readiness output/reports/cpo-readiness-guarded.md \
  --pack-dir output/packs/cpo-guarded \
  --out output/ui/index.html \
  --language both
```

Financial metrics output override:

```bash
PYTHONPATH=src python3 -m serenity_alpha_lab.cli build-financial-metrics \
  --data data/enriched/github_plus_primary.jsonl data/primary/sive_official_report_evidence.jsonl \
  --out config/financial_metrics.json
```

## Import Serenity GitHub Projects

The GitHub importer reads a curated repo manifest, fetches public markdown files, extracts Serenity-style supply-chain claims, and writes them as auditable evidence JSONL.

```bash
PYTHONPATH=src python3 -m serenity_alpha_lab.cli import-github \
  --repos imports/github_repos.json \
  --out data/imported/github_evidence.jsonl
```

Then generate a memo from both the hand-curated seed evidence and imported GitHub evidence:

```bash
PYTHONPATH=src python3 -m serenity_alpha_lab.cli \
  --data data/seed/evidence.jsonl data/imported/github_evidence.jsonl \
  --query "CPO laser bottleneck" \
  --ticker SIVE \
  --out output/memos/sive-cpo-enriched.md
```

Imported evidence remains third-party research context. It should be treated as derived or speculative unless independently confirmed by primary filings, transcripts, customer disclosures, or direct archived posts.

The scorer discounts generic methodology and prompt-template evidence so it can explain the research framework without dominating the thesis score. Risk and invalidation claims are weighted toward downside and disconfirmation factors.

## MVP Outputs

The generated memo includes:

- research question
- scorecard
- Serenity rating, confidence tier, and key evidence gaps
- industry structure map by supply-chain layer
- catalyst timeline from dated fact and catalyst evidence
- evidence gap priority table with next evidence actions
- claim-type mix
- thesis summary
- supporting evidence
- skeptic review
- invalidation conditions
- evidence action plan
- next research tasks
- research-only disclaimer

Chinese generated reports also include investment-analysis sections such as `投资分析结论`, `Serenity 选股因子`, `关键跟踪指标`, and `证据补齐行动清单`.
