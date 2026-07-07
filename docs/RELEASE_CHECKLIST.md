# Release Checklist

Use this checklist before handing Serenity Alpha Lab to another user or tagging a release.

## Verification

- Run `python3 -m pytest tests -q` from the project root.
- Run `python3 -m pytest tests/test_ui_http_e2e.py -q` from the project root.
- Run `make verify` from the project root.
- Confirm the command runs tests, `doctor`, and `run-cpo-pack`.
- Confirm the HTTP E2E test opens the Chinese homepage, follows `/analyze?query=存储芯片&language=zh`, and verifies the generated Chinese memo asset.
- Confirm the default product pipeline generates the guarded readiness report and memo pack.
- Rebuild source-backed metrics:

```bash
PYTHONPATH=src python3 -m serenity_alpha_lab.cli build-financial-metrics \
  --data data/enriched/github_plus_primary.jsonl data/primary/sive_official_report_evidence.jsonl \
  --out config/financial_metrics.json
```

- Rebuild the bilingual UI:

```bash
PYTHONPATH=src python3 -m serenity_alpha_lab.cli build-ui --language both
```

- Scan generated reports for product-authored investment advice:

```bash
PYTHONPATH=src python3 -m serenity_alpha_lab.cli scan-report-safety \
  --reports output/packs/cpo-guarded/*-memo.md \
  --out output/reports/report-safety-scan.md
```

- Build the universe coverage matrix for at least one representative industry/theme:

```bash
PYTHONPATH=src python3 -m serenity_alpha_lab.cli build-coverage-matrix \
  --data data/enriched/github_plus_primary.jsonl data/enriched/manual_intake_guarded.jsonl \
  --stock-universe config/stock_universe.json \
  --query "存储芯片" \
  --out output/reports/universe-coverage-matrix.md
```

- If generated analysis packs exist, scan them as well:

```bash
PYTHONPATH=src python3 -m serenity_alpha_lab.cli scan-report-safety \
  --reports output/ui/analyses/*/pack/*-memo.md \
  --out output/reports/report-safety-scan-analyses.md
```

## Output Review

- Inspect `output/packs/cpo-guarded/index.md` and confirm all expected default ticker memos are generated.
- Inspect `output/packs/cpo-guarded/sources.md` and confirm primary evidence provenance and source excerpts are present.
- Inspect `output/reports/cpo-readiness-guarded.md` and confirm no default ticker has blocking flags.
- Inspect `output/reports/universe-coverage-matrix.md` and confirm important theme candidates have explicit priority, gaps, and next source-search prompts.
- Inspect `config/financial_metrics.json` and confirm source-backed metrics are present for locally covered tickers and unsupported fields remain `n/a`.
- Inspect `output/ui/index.html` and `output/ui/index.zh.html` and confirm both include report history, candidate comparison, launch controls, and drawer report controls.
- Confirm the homepage report library includes `Open Coverage Matrix` / `打开覆盖矩阵` and that `/reports/universe-coverage-matrix.md` returns HTTP 200 from the local UI server.
- Confirm at least one generated analysis page includes `Open Coverage Matrix` / `打开覆盖矩阵` and `Open Acquisition Queue` / `打开采集队列`.
- Confirm the generated analysis paths `/analyses/<slug>/reports/universe-coverage-matrix.md` and `/analyses/<slug>/reports/evidence-acquisition-queue.md` return HTTP 200 and match the launched query.
- Confirm Chinese-launched operational reports render Chinese bodies, including `股票池覆盖矩阵`, `证据采集队列`, `查询`, `研究问题`, and localized gap names.
- Inspect `output/ui/analyses/manifest.json` and confirm generated report history has language-aware links.
- Confirm generated memos retain the research only disclaimer and do not contain buy, sell, hold, target price, or position sizing instructions.
- Inspect `output/reports/report-safety-scan.md` and confirm `**Findings:** 0`.
- Inspect `output/reports/report-safety-scan-analyses.md` when generated analysis packs exist and confirm `**Findings:** 0`.
- Confirm generated memos include `Industry Structure Map`, `Catalyst Timeline`, and `Evidence Gap Priority`.
- Confirm Chinese generated reports include `投资分析结论`, `Serenity 选股因子`, `关键跟踪指标`, and `证据补齐行动清单`.
- Confirm Chinese generated reports include `行业结构图`, `催化剂时间线`, and `证据缺口优先级`.
- Confirm drawer rendering is formatted Markdown, not raw `<pre>` report text.

## Local UI Smoke

Start or restart the local product server:

```bash
PYTHONPATH=src python3 -m serenity_alpha_lab.cli serve-ui \
  --host 127.0.0.1 \
  --port 8767 \
  --language both
```

Smoke test these paths:

- `http://127.0.0.1:8767/index.zh.html`
- `http://127.0.0.1:8767/index.html`
- At least one generated Chinese analysis page under `/analyses/<slug>/index.zh.html`
- At least one served memo asset under `/pack/<ticker>-memo.md` or the generated analysis pack path

From the homepage, launch at least one Chinese analysis such as `存储芯片` or `HBM` and confirm it navigates to a generated analysis page.

## Evidence Safety

- Confirm manual intake rows use non-placeholder source URLs.
- Confirm manual intake rows include `source_excerpt` values.
- Keep raw evidence snapshots and manifests under `data/` and `config/` available for local-first operation.
- Confirm any new metrics are grounded in source evidence rather than inferred from label text alone.
- Confirm any safety-scan findings are generated-report text rather than quoted source evidence before editing source material.
