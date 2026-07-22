# Data Quality Rule Engine

> Task: `SAL-P2-012` 实现数据质量规则引擎<br>
> Date: 2026-07-22<br>
> Phase: P2 数据版本、Provider 收口与持久任务<br>
> Gate: G2 未通过

## Summary

`SAL-P2-012` adds an offline Dataset quality rule engine under `serenity_alpha_lab.datasets`. It evaluates schema-bound Dataset snapshots, emits deterministic quality reports, publishes those reports through the existing `ArtifactStore`, and exposes manifest metadata that Dataset Catalog callers can write into immutable Dataset Version metadata.

This task deliberately stops before `SAL-P2-013`: the engine classifies `passed` / `warning` / `quarantine` / `blocking`, but it does not block `latest`, implement quarantine transactions, garbage-collect temporary artifacts, choose Provider fallback, or call real Providers.

## Implemented Components

- `QualityDatasetSnapshot`: schema-bound rows with optional concrete `dataset_version_id`.
- `DataQualityIssue`: rule failure location with dataset, version, partition, field, primary key, observed/expected values and sample payload.
- `DataQualityReport`: deterministic JSON report with final status, issue counts, rule set version, trace/run/stage fields and `ArtifactStore` publishing.
- `DataQualityEngine`: evaluates an ordered rule set and derives final severity.
- Built-in rules:
  - `UniquePrimaryKeyRule`
  - `SchemaFieldRule`
  - `OhlcRelationshipRule`
  - `NonNegativeFieldRule`
  - `NullRatioDriftRule`
  - `TradingContinuityRule`
  - `ReturnOutlierRule`
  - `VolumeSpikeRule`
  - `AdjustmentFactorJumpRule`

## Manifest Metadata

`DataQualityReport.manifest_metadata()` returns string metadata for `LocalDatasetCatalog.publish_version(metadata=...)`:

- `quality_status`
- `quality_rule_set_version`
- `quality_issue_count_warning`
- `quality_issue_count_quarantine`
- `quality_issue_count_blocking`
- `quality_issue_count_total`
- `quality_report_artifact_id` and `quality_report_sha256` when a report artifact is provided

This satisfies the `SAL-P2-012` requirement that rule version and quality result are recorded in Dataset Manifest metadata while preserving the `SAL-P2-011` Catalog transaction semantics.

## Red / Green Evidence

- Red: `uv run --extra core --extra dev python -m pytest tests/datasets/test_data_quality.py -q` failed during collection with `ModuleNotFoundError: No module named 'serenity_alpha_lab.datasets.quality'`.
- Green target: `uv run --extra core --extra dev python -m pytest tests/datasets/test_data_quality.py -q` passed with `4 passed`.
- Related suite: `uv run --extra core --extra dev python -m pytest tests/datasets tests/architecture tests/application/test_api_errors.py tests/domain/test_artifacts.py tests/repositories/test_local_artifact_store.py -q` passed with `61 passed`.
- Full suite: `uv run --extra core --extra dev python -m pytest -q` passed with `194 passed`.
- Static checks:
  - `uv run --extra core --extra dev python -m compileall -q src/serenity_alpha_lab tests` passed.
  - `scripts/verify-python-dependency-lock.sh` passed.
  - `git diff --check` passed.
  - `git rev-parse upstream/dsa-v3.26.1` returned `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`.

## Scope Guardrails

- No `latest` alias blocking or quarantine publish transaction.
- No fallback policy, Provider selection or cross-provider averaging.
- No Provider fixture/probe and no real Provider/LLM/network call.
- No PersistentTaskBackend, Worker runtime, Quant Core, formal backtest or Evidence Agent.
- No DSA runtime source migration and no movement of `upstream/dsa-v3.26.1`.
