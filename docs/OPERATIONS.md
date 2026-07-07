# Serenity Alpha Lab Operations

This guide is for repeatable local operation of the productized Serenity stock, industry, sector, and theme research workflow.

## Prerequisites

- Python 3.9 or newer.
- Project dependencies installed from `pyproject.toml` if running as an installed package.
- Local evidence snapshots under `data/` and manifests under `config/`.

## Verify The Project

Run the full test suite before and after changing evidence or code:

```bash
python3 -m pytest tests -q
```

Expected result: all tests pass.

Run the HTTP-level UI E2E smoke test when changing the dashboard, launcher, report drawer, or local server:

```bash
python3 -m pytest tests/test_ui_http_e2e.py -q
```

Expected result: the test starts a local ephemeral HTTP server, opens the Chinese homepage, calls `/analyze?query=存储芯片&language=zh`, follows the generated analysis page, and verifies the Chinese memo asset used by the report drawer.

## Check Local Inputs

Run a read-only health check before generating outputs:

```bash
PYTHONPATH=src python3 -m serenity_alpha_lab.cli doctor
```

Expected result: required inputs report `ok`. Missing guarded manual intake is reported as optional and does not block the product run.

## Run The Product Pipeline

From the project root:

```bash
PYTHONPATH=src python3 -m serenity_alpha_lab.cli run-cpo-pack --allow-skipped
```

If installed as a package, the console script is:

```bash
serenity-alpha-lab run-cpo-pack --allow-skipped
```

The default run writes:

- `data/enriched/github_plus_primary.jsonl`
- `output/reports/cpo-readiness-guarded.md`
- `output/packs/cpo-guarded/index.md`
- `output/packs/cpo-guarded/sources.md`
- `output/packs/cpo-guarded/*-memo.md`

## Build Source-Backed Metrics

Rebuild the local metrics catalog after refreshing evidence:

```bash
PYTHONPATH=src python3 -m serenity_alpha_lab.cli build-financial-metrics \
  --data data/enriched/github_plus_primary.jsonl data/primary/sive_official_report_evidence.jsonl \
  --out config/financial_metrics.json
```

The catalog writes comparable dashboard fields such as revenue context, profitability momentum, and cycle position when the local evidence supports them. Unknown fields remain `n/a`; do not fill missing financial data with unsupported estimates.

## Build Universe Coverage Matrix

Before treating a new industry, sector, or theme page as complete, build a coverage matrix against the maintained stock universe:

```bash
PYTHONPATH=src python3 -m serenity_alpha_lab.cli build-coverage-matrix \
  --data data/enriched/github_plus_primary.jsonl data/enriched/manual_intake_guarded.jsonl \
  --stock-universe config/stock_universe.json \
  --query "存储芯片" \
  --out output/reports/universe-coverage-matrix.md
```

Expected result: `output/reports/universe-coverage-matrix.md` lists matched universe candidates, evidence counts, primary/fact counts, risk counts, coverage gaps, priority, and the next source-search prompt. Use this report to decide which companies need filings, official reports, risk evidence, or alias coverage before promotion in the UI.

After rebuilding the UI, the same report is copied to `output/ui/reports/universe-coverage-matrix.md` and appears in the homepage report library as `Open Coverage Matrix` / `打开覆盖矩阵`, opening in the same right-side report drawer as generated memos.

When a user launches a new analysis from the UI, the generated analysis directory gets its own operational reports:

- `reports/universe-coverage-matrix.md` for that exact query.
- `reports/evidence-acquisition-queue.md` for the next evidence collection tasks.

Both reports appear as drawer-readable buttons in the generated analysis page, so users can inspect coverage and acquisition gaps without guessing file paths.
For Chinese-launched analyses, these operational report bodies use Chinese headings, table labels, priority labels, gap names, and source-target descriptions.

## Build The Local UI

After the product pipeline and metrics build succeed, build the bilingual dashboard:

```bash
PYTHONPATH=src python3 -m serenity_alpha_lab.cli build-ui --language both
```

The dashboard summarizes readiness, report history, candidate comparison, source coverage, report drawer links, risk previews, invalidation checks, financial metrics, and primary-source provenance. It is research only.

## Scan Report Safety

Before handing reports to users, scan generated memo text for product-authored investment advice:

```bash
PYTHONPATH=src python3 -m serenity_alpha_lab.cli scan-report-safety \
  --reports output/packs/cpo-guarded/*-memo.md \
  --out output/reports/report-safety-scan.md
```

For generated industry/theme/ticker analysis packs:

```bash
PYTHONPATH=src python3 -m serenity_alpha_lab.cli scan-report-safety \
  --reports output/ui/analyses/*/pack/*-memo.md \
  --out output/reports/report-safety-scan-analyses.md
```

Expected result: `**Findings:** 0`. The scanner ignores quoted source evidence lines and flags only generated report prose that contains direct recommendation phrasing, target-price language, or position-sizing language.

Default language outputs:

- `output/ui/index.html` for English.
- `output/ui/index.zh.html` for Chinese.

Generate one language explicitly when needed:

```bash
PYTHONPATH=src python3 -m serenity_alpha_lab.cli build-ui --language zh --out output/ui/index.zh.html
```

For the interactive local product server:

```bash
PYTHONPATH=src python3 -m serenity_alpha_lab.cli serve-ui \
  --host 127.0.0.1 \
  --port 8767 \
  --language both
```

Then open:

- Chinese: `http://127.0.0.1:8767/index.zh.html`
- English: `http://127.0.0.1:8767/index.html`

Use HTTP server mode for generated analysis launches. The `/analyze` route creates fresh dashboards and reports under `output/ui/analyses/`.

For a new industry, sector, theme, or ticker, enter the term in `Start analysis` / `启动分析` instead of the page search box. The launcher generates a new readiness report, memo pack, and bilingual dashboard under `output/ui/analyses/`; the search box only filters the current dashboard.

Current smoke examples:

- `存储芯片` -> `output/ui/analyses/topic-602483dcf3/index.zh.html`
- `HBM` -> `output/ui/analyses/hbm-6f259a8f14/index.zh.html`
- `半导体设备` -> `output/ui/analyses/topic-9fce51e13c/index.zh.html`
- `AAOI` -> `output/ui/analyses/aaoi-5622b4c1f7/index.zh.html`

## User-Facing Analysis Flow

For a Chinese user:

1. Open `http://127.0.0.1:8767/index.zh.html`.
2. Use `启动分析` to enter an industry, sector, theme, or ticker.
3. Review `候选对比` before opening individual reports.
4. Click `查看报告` to read the generated report in the right-side drawer.
5. Use `证据补齐行动清单` to decide which evidence must be collected next.
6. Return to `最近报告` on the homepage to reopen prior generated reports.

For English users, follow the same workflow from `index.html`.

## Make Targets

```bash
make test
make e2e
make doctor
make run-cpo-pack
make coverage-matrix
make ui
make serve-ui
make verify
make clean-pack
```

`make e2e` runs the HTTP UI smoke test for the Chinese analysis generation and report drawer asset flow. `make doctor` runs the read-only input health check. `make coverage-matrix` builds `output/reports/universe-coverage-matrix.md` for the default memory theme. `make ui` builds `output/ui/index.html` from the current guarded report and memo pack. `make serve-ui` builds the dashboard and serves it locally. `make verify` runs tests, `doctor`, the default product pipeline, and the coverage matrix. `make clean-pack` removes only the guarded pack directory and guarded readiness report. It does not remove raw evidence snapshots.

## Inputs

- Base evidence: `data/enriched/github_evidence_resolved_summaries.jsonl`
- SEC source manifest: `config/sec_companyfacts_sources.json`
- Official report source manifest: `config/official_report_sources.json`
- Guarded manual intake: `data/enriched/manual_intake_guarded.jsonl`

Override paths with `run-cpo-pack` flags when testing alternate data:

```bash
PYTHONPATH=src python3 -m serenity_alpha_lab.cli run-cpo-pack \
  --base-data data/enriched/github_evidence_resolved_summaries.jsonl \
  --sec-sources config/sec_companyfacts_sources.json \
  --official-sources config/official_report_sources.json \
  --manual-data data/enriched/manual_intake_guarded.jsonl \
  --pack-out-dir output/packs/cpo-guarded
```

## Output Contract

After a successful default run:

- `output/reports/cpo-readiness-guarded.md` lists readiness status and coverage flags for each ticker.
- `output/reports/universe-coverage-matrix.md` lists stock-universe candidate coverage gaps and next evidence prompts for the checked theme.
- `output/ui/reports/universe-coverage-matrix.md` is the served copy used by the homepage coverage-matrix drawer button.
- `output/ui/analyses/<slug>/reports/universe-coverage-matrix.md` is the generated analysis page's query-specific coverage report.
- `output/ui/analyses/<slug>/reports/evidence-acquisition-queue.md` is the generated analysis page's evidence task queue.
- `output/packs/cpo-guarded/index.md` lists generated memo files and skipped candidates.
- `output/packs/cpo-guarded/sources.md` lists primary evidence provenance and source excerpts.
- Generated memo files include an industry structure map, catalyst timeline, evidence gap priority table, evidence action plan, invalidation conditions, and research-only disclaimer.
- Stale generated memo files are removed before new pack files are written.
- `output/ui/index.html` is generated by `build-ui` or `make ui` for user-facing review.
- `output/ui/index.zh.html` is generated when `--language both` or `--language zh` is used.
- `output/ui/metrics.json` is copied from `config/financial_metrics.json`.
- `output/ui/analyses/manifest.json` records generated report history for the homepage report library.
- Analysis subdirectories contain bilingual dashboard files, `metrics.json`, `readiness.md`, and served memo assets.

## Troubleshooting

- If a ticker is `blocked`, inspect the flags in `output/reports/cpo-readiness-guarded.md`.
- If an industry page under-covers relevant candidates, run `build-coverage-matrix` for that query and update `config/stock_universe.json` aliases or evidence inputs.
- If `missing_primary_source` appears, add or refresh a primary source manifest entry.
- If manual intake fails, confirm `--source-url` is not a placeholder and `--source-excerpt` explains how the source supports the claim.
- If outputs look stale, run `make clean-pack` and then `make run-cpo-pack`.
- If the UI loads but `启动分析` appears unresponsive, check `output/ui/serve-ui.log`, confirm the server is running on `127.0.0.1:8767`, and use the explicit `/analyze?query=<term>&language=zh` route to reproduce.
- If report links 404, rebuild the UI so memo assets are copied into the served `output/ui/pack/` or analysis directory.
- If Chinese pages show English report bodies, regenerate the analysis from the Chinese launcher or run the analysis generation path with `language=zh`.
- If `scan-report-safety` returns exit code `4`, inspect the generated Markdown scan report and remove product-authored recommendation wording. Do not rewrite quoted source evidence merely because an external source contains buy/sell/hold language.

## Safety Note

Generated memos are research artifacts only. They are not investment advice and should be independently verified before any capital decision. Do not add buy/sell/hold recommendations, target prices, or position-sizing instructions.
