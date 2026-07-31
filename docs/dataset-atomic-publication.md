# Dataset 隔离区与原子发布记录

> 任务：`SAL-P2-013` 实现隔离区与原子发布<br>
> 日期：2026-07-23<br>
> Phase：P2 数据版本、Provider 收口与持久任务<br>
> Gate：G2 未通过

## Summary

`SAL-P2-013` adds a quality-gated Dataset publication layer under `serenity_alpha_lab.datasets`. It composes the existing `LocalDatasetCatalog`, `DataQualityReport` metadata, and `ArtifactStore` without starting Provider fallback, real Provider calls, Worker runtime, Quant Core, formal backtest, or Evidence Agent work.

The publication sequence is:

1. Publish the deterministic data quality report through `ArtifactStore`.
2. Write an immutable Dataset Version Manifest with quality metadata and `update_latest=False`.
3. Promote only `DataQualityStatus.PASSED` versions to the mutable `latest` alias.
4. Persist warning/quarantine/blocking decisions as quarantine records while leaving the previous latest alias unchanged.
5. On publish failure, clean only explicit temporary roots and propagate the failure so no successful result is returned.

## Implemented Components

- `DatasetPublicationRequest`: immutable request DTO carrying files, quality report, run/stage/trace attribution, lineage and caller metadata.
- `DatasetPublicationStatus`: `published`, `held`, `quarantined`, `blocked`.
- `DatasetPublicationResult`: returned manifest, quality report Artifact, latest update flag and optional quarantine record.
- `QualityGatedDatasetPublisher`: quality-aware publisher that layers over `LocalDatasetCatalog`.
- `cleanup_temporary_paths()`: bounded cleanup helper for `tmp` roots only.
- `LocalDatasetCatalog.promote_to_latest()`: explicit latest promotion for an already published version.
- `LocalDatasetCatalog.record_quarantine()` / `list_quarantine_records()`: deterministic held/quarantine/blocking record persistence.

## Quality Gate Semantics

| Quality status | Publication status | Latest behavior |
|---|---|---|
| `passed` | `published` | Promotes the version to `latest` |
| `warning` | `held` | Keeps old `latest`; writes a held record |
| `quarantine` | `quarantined` | Keeps old `latest`; writes a quarantine record |
| `blocking` | `blocked` | Keeps old `latest`; writes a blocked record |

This deliberately applies the stricter plan rule that only `passed` may become `latest`; warning versions remain discoverable by concrete `dataset_version` but are not silently promoted.

## Red / Green Evidence

- Red: `uv run --extra core --extra dev python -m pytest tests/datasets/test_dataset_publication.py -q` failed during collection with `ModuleNotFoundError: No module named 'serenity_alpha_lab.datasets.publication'`.
- Green target: `uv run --extra core --extra dev python -m pytest tests/datasets/test_dataset_publication.py -q` passed with `5 passed`.
- Related suite: `uv run --extra core --extra dev python -m pytest tests/datasets tests/architecture tests/application/test_api_errors.py tests/domain/test_artifacts.py tests/repositories/test_local_artifact_store.py -q` passed with `66 passed`.
- Full suite: `uv run --extra core --extra dev python -m pytest -q` passed with `199 passed`.
- Static checks:
  - `uv run --extra core --extra dev python -m compileall -q src/serenity_alpha_lab tests` passed.
  - `scripts/verify-python-dependency-lock.sh` passed.
  - `git diff --check` passed.
  - `git rev-parse upstream/dsa-v3.26.1` returned `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`.

## Scope Guardrails

- No fallback policy, Provider selection or cross-provider averaging.
- No Provider fixture/probe and no real Provider/LLM/network call.
- No PersistentTaskBackend, Worker runtime, Quant Core, formal backtest or Evidence Agent.
- No DSA runtime source migration and no movement of `upstream/dsa-v3.26.1`.
- Temporary cleanup is limited to explicit catalog/artifact `tmp` directories and does not delete immutable blobs, manifests, aliases or unrelated directories.
