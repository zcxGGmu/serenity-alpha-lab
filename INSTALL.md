# Install

Use this path when validating Serenity Alpha Lab from a fresh local checkout.

## Requirements

- Python 3.9 or newer.
- Local evidence snapshots under `data/`.
- Local source manifests under `config/`.

## Editable Install

From the project root:

```bash
python3 -m pip install -e .
make smoke
make verify
```

`make smoke` exercises the installed console script:

```bash
serenity-alpha-lab doctor
serenity-alpha-lab run-cpo-pack --allow-skipped
```

Expected result:

- `doctor` reports `required inputs: ok`.
- `run-cpo-pack --allow-skipped` generates the guarded readiness report and memo pack for the default CPO pack.

## Source-Tree Fallback

If you do not want to install the package, run the same checks through the source tree:

```bash
PYTHONPATH=src python3 -m serenity_alpha_lab.cli doctor
PYTHONPATH=src python3 -m serenity_alpha_lab.cli run-cpo-pack --allow-skipped
PYTHONPATH=src python3 -m serenity_alpha_lab.cli build-financial-metrics \
  --data data/enriched/github_plus_primary.jsonl data/primary/sive_official_report_evidence.jsonl \
  --out config/financial_metrics.json
PYTHONPATH=src python3 -m serenity_alpha_lab.cli build-ui --language both
```

To run the interactive local UI:

```bash
PYTHONPATH=src python3 -m serenity_alpha_lab.cli serve-ui \
  --host 127.0.0.1 \
  --port 8767 \
  --language both
```

Open `http://127.0.0.1:8767/index.zh.html` for Chinese or `http://127.0.0.1:8767/index.html` for English.

In the UI, use `启动分析` / `Start analysis` for new industry, sector, theme, or ticker reports. The page search box only filters the currently open dashboard.

## Release Gate

Before handing the project to another user, run:

```bash
make verify
```

This runs the test suite, the local input health check, and the default product pipeline.

For the current user-facing product surface, also run:

```bash
PYTHONPATH=src python3 -m serenity_alpha_lab.cli build-financial-metrics \
  --data data/enriched/github_plus_primary.jsonl data/primary/sive_official_report_evidence.jsonl \
  --out config/financial_metrics.json
PYTHONPATH=src python3 -m serenity_alpha_lab.cli build-ui --language both
```

Then start `serve-ui` and smoke test the Chinese homepage plus at least one generated analysis page.
